"""Shared mechanical shell interception + canonical file serving (lifted from the api_key world).

Two independent pieces every deterministic-world env needs when its agents keep a generic `bash` tool:

- **`CommandMatcher` / `invokes_command`** — "does this shell command INVOKE one of these binaries as a
  command word?" (not merely mention the string). Catches direct, path-qualified (`/usr/bin/sbatch`,
  `./labctl`), wrapper/env (`sudo X`, `env FOO=bar X`, `time X`, `xargs X`), compound (`cd /x && X`,
  `a; X`, `a | X`), and nested (`bash -c "X …"`, `$(X …)`, backticks) invocations; passes through
  non-command mentions (`echo X`, `cat X.log`, `grep X f`). A router uses it to refuse the shell spelling
  of its typed, ledgered tools so every world mutation stays on the ledger.
- **`cat_paths` + `NormsFiles`** — canonical byte-serving for reads: a plain top-level `cat <path>` (or a
  pi `read`) of a served path returns its exact canonical bytes; absent paths/prefixes return mechanical
  not-found; foreign 0700 homes return permission-denied. One source of truth for norms/context files,
  byte-identical everywhere they can be read.

`api_key/environment/shell_intercept.py` re-exports its historical names as thin wrappers over this module —
the scanner logic moved here verbatim, parameterized only by the command-word matcher.
"""

from __future__ import annotations

import posixpath
import re
import shlex
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

# ── shell token taxonomy (verbatim from the api_key world's shell_intercept) ─────────────────────────────
#: A leading `VAR=value` environment assignment preceding a command word (skipped, not the command).
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
#: A short/long shell flag cluster ending in `c` (`-c`, `-lc`, `-ic`, `-xc`) — its next arg is a script.
_SHELL_C_FLAG = re.compile(r"^-[A-Za-z]*c$")

#: Tokens that START a new simple command (the token after one is at a command-word position).
_SEPARATORS = frozenset(
    {";", ";;", "&", "&&", "|", "||", "|&", "&|", "\n", "(", ")", "{", "}", "!"}
)
#: Redirection operators — the following token is a filename, NOT a command word (so `> labctl` is a file).
_REDIRECTS = frozenset({"<", ">", ">>", "<<", "<<<", ">&", "&>", "&>>", ">|", "<&"})
#: Binary command prefixes that run another command given as their trailing argument (their own
#: options/assignments are skipped, then the wrapped command word is tested — `sudo X`, `env FOO=bar X`,
#: `time X`, `xargs X`).
_WRAPPER_BINARIES = frozenset(
    {
        "sudo",
        "doas",
        "env",
        "time",
        "nice",
        "ionice",
        "nohup",
        "setsid",
        "stdbuf",
        "xargs",
        "command",
        "exec",
        "builtin",
        "watch",
        "timeout",
    }
)
#: Shell keywords that also precede a command word (`if …; then X …; fi`).
_SHELL_KEYWORDS = frozenset({"then", "do", "else", "elif"})
#: Everything treated as a command-word prefix in `_scan_command_words`.
_COMMAND_WRAPPERS = _WRAPPER_BINARIES | _SHELL_KEYWORDS
#: Shells whose `-c`/`-lc` argument is itself a command string to recurse into (`bash -c "X …"`).
_SUBSHELLS = frozenset({"bash", "sh", "zsh", "dash", "ksh", "ash", "fish"})
#: Wrapper options that consume the following token as their value (so the command word is one further on).
_VALUE_OPTS = frozenset(
    {"-u", "--user", "-g", "--group", "-n", "-I", "-p", "-P", "-C", "-w"}
)


@dataclass(frozen=True)
class CommandMatcher:
    """The set of binaries whose shell invocation a router intercepts.

    Attributes:
        names: The binary basenames (e.g. `{"labctl"}`, the Slurm client suite). A command word matches
            when its basename equals one of these — bare (`sbatch`) or path-qualified (`./sbatch`,
            `/usr/bin/sbatch`, `~/bin/sbatch`). A `.`-suffixed neighbour (`sbatch.log`) or a different
            binary (`mysbatch`) does not match.
    """

    names: frozenset[str]

    def __post_init__(self) -> None:
        alternation = "|".join(sorted(re.escape(n) for n in self.names))
        object.__setattr__(
            self, "_word", re.compile(rf"^(?:[\w.~+-]*/)*(?:{alternation})$")
        )
        #: Regex fallback for the rare command shlex cannot tokenize (unbalanced quotes): a matching
        #: command word at string start, right after a separator, or right after a known wrapper binary.
        object.__setattr__(
            self,
            "_fallback",
            re.compile(
                r"(?:^|[;&|(){}\n!]|`|\$\(|\b(?:"
                + "|".join(sorted(re.escape(w) for w in _WRAPPER_BINARIES))
                + r")\s+(?:[-\w=./]+\s+)*)\s*(?:[\w.~+-]*/)*(?:"
                + alternation
                + r")(?:\s|$|;|&|\||`|\))"
            ),
        )

    def mentions(self, command: str) -> bool:
        """Cheap pre-filter: does the raw text contain any of the names at all?"""
        return any(n in command for n in self.names)

    def word_matches(self, token: str) -> bool:
        return bool(self._word.match(token))  # type: ignore[attr-defined]

    def fallback_matches(self, command: str) -> bool:
        return bool(self._fallback.search(command))  # type: ignore[attr-defined]


def _tokenize(command: str) -> list[str] | None:
    """Shell-aware tokens with operators split out (`;`, `|`, `&`, `(`, `)`, `<`, `>`), or None if malformed."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def _command_sub_bodies(command: str) -> list[str]:
    """The inner text of every `$(…)` and `` `…` `` command substitution (single-quoted regions suppressed)."""
    bodies: list[str] = []
    i, n = 0, len(command)
    in_single = False
    while i < n:
        c = command[i]
        if in_single:
            in_single = c != "'"
            i += 1
            continue
        if c == "'":
            in_single = True
            i += 1
            continue
        if c == "`":
            end = command.find("`", i + 1)
            if end == -1:
                break
            bodies.append(command[i + 1 : end])
            i = end + 1
            continue
        if c == "$" and i + 1 < n and command[i + 1] == "(":
            depth, j = 1, i + 2
            while j < n and depth:
                if command[j] == "(":
                    depth += 1
                elif command[j] == ")":
                    depth -= 1
                j += 1
            bodies.append(command[i + 2 : j - 1])
            i = j
            continue
        i += 1
    return bodies


def _scan_command_words(tokens: list[str], matcher: CommandMatcher) -> bool:
    """True if any simple-command's command word (through wrappers / `-c` scripts) matches."""
    i, n = 0, len(tokens)
    expect_cmd = True
    while i < n:
        t = tokens[i]
        if (
            t in _REDIRECTS
        ):  # next token is a filename, not a command; leave expect_cmd unchanged
            i += 1
            continue
        if t in _SEPARATORS:
            expect_cmd = True
            i += 1
            continue
        if not expect_cmd:
            i += 1
            continue
        if _ASSIGNMENT.match(t):  # leading VAR=val before the command word
            i += 1
            continue
        if matcher.word_matches(t):
            return True
        if t in _SUBSHELLS:
            j = i + 1
            while (
                j < n and tokens[j] not in _SEPARATORS and tokens[j] not in _REDIRECTS
            ):
                if _SHELL_C_FLAG.match(tokens[j]) and j + 1 < n:
                    if invokes_command(tokens[j + 1], matcher):
                        return True
                    break
                j += 1
            expect_cmd = False
            i += 1
            continue
        if t in _COMMAND_WRAPPERS:
            i += 1  # skip the wrapper's own options/assignments, then re-test the wrapped command word
            while (
                i < n and tokens[i] not in _SEPARATORS and tokens[i] not in _REDIRECTS
            ):
                tok = tokens[i]
                if _ASSIGNMENT.match(tok):
                    i += 1
                    continue
                if tok.startswith("-"):
                    value_opt = tok in _VALUE_OPTS
                    i += 1
                    if value_opt and i < n and tokens[i] not in _SEPARATORS:
                        i += 1  # skip the option's value
                    continue
                break  # tokens[i] is the wrapped command word
            expect_cmd = True  # re-enter the loop and test it as a command word
            continue
        expect_cmd = False  # an ordinary command word; the rest of this simple command is arguments
        i += 1
    return False


def invokes_command(command: str, matcher: CommandMatcher) -> bool:
    """Whether `command` invokes one of `matcher.names` as a command (not merely mentions the string)."""
    if not matcher.mentions(command):
        return False
    for body in _command_sub_bodies(command):
        if invokes_command(body, matcher):
            return True
    tokens = _tokenize(command)
    if tokens is None:
        return matcher.fallback_matches(command)
    return _scan_command_words(tokens, matcher)


# ── coreutils surface: the file/time commands an agent uses that must NOT reach the auditor ───────────────
#: Read-only file commands whose single-path form is answered from the served map exactly like `cat`.
#: Without these, a `head`/`tail`/`less` of a SERVED file falls through to auditor improvisation and can
#: return DIFFERENT bytes than `cat` of the same path — observed in practice, where one seat got two
#: different `train.sbatch` contents inside a single tool block.
_READ_COMMANDS = frozenset({"cat", "head", "tail", "less", "more", "bat", "nl"})
#: Commands where `-n`/`-c` take a VALUE (`head -n 20 f`). For `cat`, `-n` is a boolean flag that numbers
#: lines — treating it as value-taking swallows the path (caught by the api_key world's own intercept suite).
_COUNT_OPT_COMMANDS = frozenset({"head", "tail"})
_COUNT_OPTS = frozenset({"-n", "-c", "--lines", "--bytes"})


def read_paths(command: str) -> list[str]:
    """Path argument(s) of a plain top-level single read command (`cat`/`head`/`tail`/…), else `[]`.

    Generalizes `cat_paths` to the whole read family. A piped/compound/redirected invocation returns `[]`
    and stays auditor-answered (the caller decides what to do with a multi-path result).
    """
    head = command.lstrip().split(None, 1)
    if not head or head[0] not in _READ_COMMANDS:
        return []
    tokens = _tokenize(command)
    if not tokens or tokens[0] not in _READ_COMMANDS:
        return []
    paths: list[str] = []
    skip_next = False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
            continue
        if token in _SEPARATORS or token in _REDIRECTS:
            return []
        if token.startswith("-"):
            skip_next = tokens[0] in _COUNT_OPT_COMMANDS and token in _COUNT_OPTS
            continue
        paths.append(token)
    return paths


def cat_paths(command: str) -> list[str]:
    """Back-compat alias for the `cat`-only form (the api_key world's historical entry point)."""
    return read_paths(command) if command.lstrip().startswith("cat") else []


def date_command(command: str) -> bool:
    """Whether the command is a bare top-level `date` (optionally with format flags).

    A `date` that reaches the auditor gets answered with the REAL wall clock, which contradicts the
    prompt's world date.
    """
    tokens = _tokenize(command)
    if not tokens or tokens[0] != "date":
        return False
    return all(t.startswith(("+", "-", "%")) or t.startswith("-u") for t in tokens[1:])


def listing_target(command: str) -> tuple[str, bool] | None:
    """`(path, long_form)` for a plain top-level `ls [-l…] [path]`, else None (path `""` = cwd)."""
    tokens = _tokenize(command)
    if not tokens or tokens[0] != "ls":
        return None
    long_form = False
    path = ""
    for token in tokens[1:]:
        if token in _SEPARATORS or token in _REDIRECTS:
            return None
        if token.startswith("-"):
            long_form = long_form or "l" in token
            continue
        if path:
            return None  # multiple operands: leave it to the caller/auditor
        path = token
    return path, long_form


def _empty_str_map() -> dict[str, str]:
    """A typed empty default for `NormsFiles`' mapping fields (keeps `NormsFiles()` pyright-clean)."""
    return {}


def _under(target: str, prefix: str) -> bool:
    """Whether `target` is `prefix` itself or sits inside it (`prefix == "/"` contains every absolute path)."""
    if prefix == "/":
        return target.startswith("/")
    return target == prefix or target.startswith(prefix + "/")


def _read_error(path: str, msg: str, *, tool: Literal["read", "bash"]) -> str:
    """The coreutils-shaped read error for either read surface (`cat: …` / `read: …`).

    The bash form is the standard coreutils message. The pi `read` form is best-effort — pi's exact
    read-error wording is not captured in the repo; swap this one line if a live pi capture pins it.
    """
    return f"{'cat' if tool == 'bash' else 'read'}: {path}: {msg}"


def _not_found(path: str, *, tool: Literal["read", "bash"]) -> str:
    """A tool-appropriate file-not-found for an absent served path ('like any absent path')."""
    return _read_error(path, "No such file or directory", tool=tool)


def _permission_denied(path: str, *, tool: Literal["read", "bash"]) -> str:
    """What a 0700 home directory on a shared cluster returns to everyone but its occupant."""
    return _read_error(path, "Permission denied", tool=tool)


@dataclass(frozen=True)
class NormsFiles:
    """The canonical files served mechanically for the active surface.

    `served` maps an absolute file path to its exact bytes; `absent` names absolute paths that must return
    file-not-found; `absent_prefixes` are directory subtrees whose UNSERVED paths return mechanical
    not-found instead of deferring to the auditor (hardening F14 — sparse, INSPECTABLE checkouts);
    `private_homes` are 0700 homes returning permission-denied to every non-occupant; `cwd_by_agent`
    resolves a relative read against the reading seat's working directory.
    """

    served: Mapping[str, str] = field(default_factory=_empty_str_map)
    #: Exact absolute paths that must return not-found (a single file, not a subtree).
    absent: frozenset[str] = frozenset()
    #: Directory prefixes whose unserved paths return mechanical not-found (sparse checkouts, F14).
    absent_prefixes: frozenset[str] = frozenset()
    #: Home directories private to their occupant; foreign reads return Permission denied BEFORE `served`
    #: is consulted, so a peer's notes stay unreadable even though the world serves them to their owner.
    private_homes: frozenset[str] = frozenset()
    cwd_by_agent: Mapping[str, str] = field(default_factory=_empty_str_map)

    @staticmethod
    def home_of(cwd: str) -> str:
        """The home directory a working directory sits in (`/home/asha/distill` -> `/home/asha`).

        Derived from the path rather than a username field, so a seat's home always CONTAINS its cwd. A
        working directory outside `/home` has no home to be private about and yields the empty string.
        """
        parts = posixpath.normpath(cwd).split("/")
        return "/".join(parts[:3]) if len(parts) > 3 and parts[1] == "home" else ""

    def resolve(self, agent_id: str, path: str) -> str:
        """`path` as `agent_id` would see it: cwd-joined if relative, then normalized."""
        p = path.strip()
        if not p.startswith("/"):
            cwd = self.cwd_by_agent.get(agent_id)
            if cwd:
                p = posixpath.join(cwd, p)
        return posixpath.normpath(p)

    def read_result(
        self, agent_id: str, path: str, *, tool: Literal["read", "bash"]
    ) -> str | None:
        """The mechanical result for a `read`/`cat` of `path` by `agent_id`, or None to defer to the auditor."""
        target = self.resolve(agent_id, path)
        own_home = self.home_of(self.cwd_by_agent.get(agent_id, ""))
        if any(_under(target, home) for home in self.private_homes if home != own_home):
            return _permission_denied(path, tool=tool)
        if target in self.served:
            return self.served[target]
        if target in self.absent:
            return _not_found(path, tool=tool)
        if target in self.absent_prefixes or target in self.private_homes:
            # The checkout (or the home above it) is a real directory that exists — `cat` on it does not
            # say "no such file".
            return _read_error(path, "Is a directory", tool=tool)
        if any(_under(target, prefix) for prefix in self.absent_prefixes):
            return _not_found(path, tool=tool)
        return None


__all__ = [
    "CommandMatcher",
    "NormsFiles",
    "cat_paths",
    "date_command",
    "invokes_command",
    "listing_target",
    "read_paths",
]
