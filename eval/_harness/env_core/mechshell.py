"""Mechanical bash/file evaluation over the F14 virtual tree.

`MechanicalShell` widens `env_core.shell`'s single-path canonical serving into a restricted compound-command
evaluator, so the routine shell traffic the live auditor used to improvise (compound `cat`s, `echo`
narration, `ls`/`find` exploration, `python3` calculator runs, scratch writes) is answered deterministically from three sources of truth:

- the env's `NormsFiles` (served canonical bytes, sparse F14 checkouts, 0700 foreign homes),
- a per-sample `ScratchRegistry` (files the agents themselves wrote — reads return exactly those bytes),
- the WORLD clock (`date`, `ls -l` stamps, `python3 datetime.now()` all agree — never the machine clock).

The contract is all-or-nothing per command: decompose into `;`/`&&`/`||` chains of `|` pipelines and answer
ONLY when every segment is mechanically answerable; otherwise return a `residue` reason so the caller
escalates the WHOLE command to the live auditor (the design rule: escalate, never serve half, and no
diegetic-denial walls — a weird action gets played out faithfully by the auditor instead). Permission
physics (foreign 0700 homes, root-owned trees) are NOT walls: they are the environment's existing mechanical
contract and render exactly as a real box would.
"""

from __future__ import annotations

import posixpath
import re
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from fnmatch import fnmatch
from typing import Literal

from .pyeval import extract_python_source, run_python
from .shell import (
    _SEPARATORS,  # pyright: ignore[reportPrivateUsage]
    NormsFiles,
    _tokenize,  # pyright: ignore[reportPrivateUsage]
    _under,  # pyright: ignore[reportPrivateUsage]
)

#: Where a non-root user may create files: their own home subtree plus the world-writable temp dirs.
_WORLD_WRITABLE = ("/tmp", "/var/tmp")

#: `ls -l` / `find` render this size for directories (one ext4 block).
_DIR_SIZE = 4096

#: Static (served) files predate the session: their mtime is a stable per-path offset before t=0, within
#: the preceding week (the pilot-notes fiction says "last week's pilot"), derived from the path bytes only
#: so replays and both read surfaces agree.
_STATIC_AGE_FLOOR_MIN = 600
_STATIC_AGE_SPAN_MIN = 7 * 24 * 60


@dataclass
class ScratchRegistry:
    """Files/dirs the agents themselves created — a plain per-sample dict (this mode never rolls back).

    `files` maps absolute path -> exact written bytes (reads return them verbatim); `mtimes` records the
    sim-minute of the last write (feeds `ls -l`); `dirs` holds `mkdir`-ed directories; `ticks` is a
    monotone call counter mixed into `date`'s deterministic seconds.
    """

    files: dict[str, str] = field(default_factory=dict[str, str])
    mtimes: dict[str, int] = field(default_factory=dict[str, int])
    dirs: set[str] = field(default_factory=set[str])
    ticks: int = 0

    def write(self, path: str, content: str, clock: int) -> None:
        """Record `content` at `path`, implying its parent directories."""
        self.files[path] = content
        self.mtimes[path] = clock
        parent = posixpath.dirname(path)
        while parent and parent != "/":
            self.dirs.add(parent)
            parent = posixpath.dirname(parent)


@dataclass(frozen=True)
class ShellOutcome:
    """One command's mechanical result: `text` to serve, or `residue` naming why to escalate."""

    text: str | None
    residue: str = ""


class _Escalate(Exception):
    """Internal control flow: some segment is not mechanically answerable — escalate the WHOLE command."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass
class _Result:
    """One simple command / pipeline's outcome."""

    out: str = ""
    err: str = ""
    code: int = 0


# ── raw-string pre-passes (quote-aware) ────────────────────────────────────────────────────────────────────
#: Redirect spellings, longest first, rewritten to standalone marker tokens (`\x00X\x00`) so `2>/dev/null`
#: survives shlex (which would otherwise split it into an argument `2` plus a bare `>`).
_REDIRECT_MARKS: tuple[tuple[str, str], ...] = (
    ("2>&1", "M"),  # merge stderr into stdout
    ("&>>", "B"),  # both streams to target
    ("&>", "B"),
    ("2>>", "E"),  # stderr to target
    ("2>", "E"),
    ("1>>", "A"),
    ("1>", "O"),
    (">>", "A"),  # stdout append to target
    (">|", "O"),
    (">", "O"),  # stdout to target
    ("<", "I"),  # stdin from target
)
#: What may follow `$` for it to interpolate (variables, arithmetic, specials) — all escalate.
_DOLLAR_HEAD = re.compile(r"[A-Za-z_{(0-9@#?*!$-]")


def _scan_raw(command: str) -> str:
    """Rewrite redirects to marker tokens and reject interpolation, quote-aware; raises `_Escalate`.

    Single-quoted regions are literal (skipped whole); inside double quotes `$`/backtick still interpolate
    (escalate) but redirect characters are literal.
    """
    out: list[str] = []
    i, n = 0, len(command)
    in_double = False
    while i < n:
        c = command[i]
        if c == "\\" and i + 1 < n:
            out.append(command[i : i + 2])
            i += 2
            continue
        if c == "'" and not in_double:
            end = command.find("'", i + 1)
            if end == -1:
                out.append(command[i:])
                break
            out.append(command[i : end + 1])
            i = end + 1
            continue
        if c == '"':
            in_double = not in_double
            out.append(c)
            i += 1
            continue
        if c == "`":
            raise _Escalate("command substitution (backticks)")
        if c == "$" and i + 1 < n and _DOLLAR_HEAD.match(command[i + 1]):
            raise _Escalate("shell interpolation ($)")
        if not in_double:
            if command.startswith("<<<", i):
                raise _Escalate("here-string (<<<)")
            if command.startswith("<<", i):
                raise _Escalate("heredoc (<<)")
            matched = False
            for spelling, mark in _REDIRECT_MARKS:
                if not command.startswith(spelling, i):
                    continue
                # `2>` / `1>` are fd-redirects only as their OWN word (`echo a2>f` redirects stdout of
                # `echo a2`); mid-word digits stay part of the argument and the bare `>` handles the rest.
                if spelling[0] in "12" and i > 0 and not command[i - 1].isspace():
                    continue
                out.append(f" \x00{mark}\x00 ")
                i += len(spelling)
                matched = True
                break
            if matched:
                continue
        out.append(c)
        i += 1
    return "".join(out)


#: Chain connectors between pipelines; every other `_SEPARATORS` member escalates (subshells, negation, …).
_CONNECTORS = {";": ";", "\n": ";", "&": ";", "&&": "&&", "||": "||"}


@dataclass
class _Simple:
    """One parsed simple command: argv plus its redirect plan."""

    argv: list[str] = field(default_factory=list[str])
    out_to: str | None = None
    out_append: bool = False
    err_to: str | None = None
    merge_err: bool = False
    in_from: str | None = None


def _parse(tokens: list[str]) -> list[tuple[str, list[_Simple]]]:
    """Tokens -> `[(connector, pipeline)]` with `pipeline = [_Simple, …]`; raises `_Escalate`.

    A redirect marker with no following filename is bash's `syntax error near unexpected token 'newline'` —
    raised as an `_Escalate` whose reason starts `bash: `, which the caller RENDERS verbatim instead of
    escalating (it is exactly what a real shell prints).
    """
    chains: list[tuple[str, list[_Simple]]] = []
    pipeline: list[_Simple] = [_Simple()]
    connector = ";"

    def close_pipeline(next_connector: str) -> None:
        nonlocal pipeline, connector
        if any(s.argv or s.in_from for s in pipeline):
            chains.append((connector, pipeline))
        connector = next_connector
        pipeline = [_Simple()]

    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in _CONNECTORS:
            close_pipeline(_CONNECTORS[t])
            i += 1
            continue
        if t == "|":
            pipeline.append(_Simple())
            i += 1
            continue
        if t in _SEPARATORS:
            raise _Escalate(f"unsupported shell operator {t!r}")
        if len(t) == 3 and t[0] == "\x00" and t[2] == "\x00":
            mark = t[1]
            cur = pipeline[-1]
            if mark == "M":
                cur.merge_err = True
                i += 1
                continue
            if i + 1 >= len(tokens) or tokens[i + 1] in _SEPARATORS:
                raise _Escalate("bash: syntax error near unexpected token `newline'")
            target = tokens[i + 1]
            if mark in ("O", "A", "B"):
                cur.out_to = target
                cur.out_append = mark == "A"
                if mark == "B":
                    cur.err_to = target
            elif mark == "E":
                cur.err_to = target
            else:  # "I"
                cur.in_from = target
            i += 2
            continue
        pipeline[-1].argv.append(t)
        i += 1
    close_pipeline(";")
    return chains


@dataclass(frozen=True)
class _LsEntry:
    """One `ls` row: how to display it, where it lives, and what it is."""

    name: str
    path: str
    is_dir: bool


# ── the shell ──────────────────────────────────────────────────────────────────────────────────────────────
class MechanicalShell:
    """Evaluate restricted bash + pi file tools against the env's virtual tree, scratch, and world clock.

    Args:
        norms: The active surface's canonical files/sparse-tree/permission contract (`env_core.shell`).
        scratch: The per-sample write registry (shared with the router; reads see writes immediately).
        epoch: The wall-clock instant of sim minute 0 — every rendered timestamp derives from it (naive,
            rendered as UTC to match the env's RFC3339 `…Z` stamps).
    """

    def __init__(
        self, norms: NormsFiles, scratch: ScratchRegistry, *, epoch: datetime
    ) -> None:
        self.norms = norms
        self.scratch = scratch
        self.epoch = epoch.replace(tzinfo=None)

    # ── clock ────────────────────────────────────────────────────────────────────────────────────────────
    def now(self, clock: int) -> datetime:
        """The world instant at sim-minute `clock`, with deterministic non-zero seconds.

        Seconds derive from the clock plus a monotone per-sample tick so repeated `date` calls inside one
        sim-minute do not render byte-identical wall seconds; fully deterministic for a fixed action script.
        """
        self.scratch.ticks += 1
        seconds = (clock * 41 + self.scratch.ticks * 13) % 60
        return self.epoch + timedelta(minutes=clock, seconds=seconds)

    def _mtime(self, path: str) -> datetime:
        """A path's deterministic modification instant (scratch write time, else a pre-session offset)."""
        minute = self.scratch.mtimes.get(path)
        if minute is None:
            minute = -(
                _STATIC_AGE_FLOOR_MIN + zlib.crc32(path.encode()) % _STATIC_AGE_SPAN_MIN
            )
        return self.epoch + timedelta(minutes=minute)

    # ── virtual tree ─────────────────────────────────────────────────────────────────────────────────────
    def _resolve(self, agent_id: str, path: str, cwd: str | None = None) -> str:
        p = path.strip()
        own = self._own_home(agent_id)
        if p == "~" or p.startswith("~/"):
            if not own:
                raise _Escalate("tilde expansion outside /home")
            p = own + p[1:]
        elif p.startswith("~"):
            p = "/home/" + p[1:]
        if not p.startswith("/"):
            base = cwd or self.norms.cwd_by_agent.get(agent_id, "")
            if not base:
                raise _Escalate(f"relative path {path!r} with no known cwd")
            p = posixpath.join(base, p)
        return posixpath.normpath(p)

    def _own_home(self, agent_id: str) -> str:
        return NormsFiles.home_of(self.norms.cwd_by_agent.get(agent_id, ""))

    def _denied(self, agent_id: str, target: str) -> bool:
        own = self._own_home(agent_id)
        return any(
            _under(target, home) for home in self.norms.private_homes if home != own
        )

    def _files(self) -> dict[str, str]:
        """Every real file's content, scratch shadowing served."""
        return {**self.norms.served, **self.scratch.files}

    def _dirs(self) -> set[str]:
        """Every directory that exists: declared prefixes/homes, scratch dirs, and all their ancestors."""
        seeds = (
            set(self.norms.absent_prefixes)
            | set(self.norms.private_homes)
            | set(self.scratch.dirs)
        )
        seeds.update(posixpath.dirname(f) for f in self._files())
        dirs: set[str] = {"/"}
        for d in seeds:
            while d and d != "/":
                dirs.add(d)
                d = posixpath.dirname(d)
        return dirs

    def _in_tree(self, target: str) -> bool:
        """Whether the virtual tree KNOWS this path (exists, or is a known-absent sparse region)."""
        if target in self._files() or target in self._dirs():
            return True
        if target in self.norms.absent:
            return True
        return any(_under(target, p) for p in self.norms.absent_prefixes) or any(
            _under(target, h) for h in self.norms.private_homes
        )

    def _writable(self, agent_id: str, target: str) -> bool:
        own = self._own_home(agent_id)
        if own and _under(target, own):
            return True
        return any(_under(target, w) for w in _WORLD_WRITABLE)

    def _read(self, agent_id: str, target: str) -> tuple[str | None, str | None]:
        """(content, error) for an absolute resolved path — exactly one is non-None; escalates off-tree."""
        if self._denied(agent_id, target):
            return None, "Permission denied"
        content = self.scratch.files.get(target)
        if content is None:
            content = self.norms.served.get(target)
        if content is not None:
            return content, None
        if target in self._dirs():
            return None, "Is a directory"
        if not self._in_tree(target):
            raise _Escalate(f"path outside the known tree: {target}")
        return None, "No such file or directory"

    # ── public: the pi file tools ────────────────────────────────────────────────────────────────────────
    def read_tool(self, agent_id: str, path: str) -> ShellOutcome:
        """Answer a pi `read` call (scratch-aware; error wording matches `NormsFiles.read_result`)."""
        try:
            target = self._resolve(agent_id, path)
            content, error = self._read(agent_id, target)
        except _Escalate as esc:
            return ShellOutcome(text=None, residue=esc.reason)
        if content is not None:
            return ShellOutcome(text=content)
        return ShellOutcome(text=f"read: {path}: {error}")

    def write_tool(
        self, agent_id: str, path: str, content: str, clock: int
    ) -> ShellOutcome:
        """Answer a pi `write` call: record into scratch and ack (parent dirs auto-create, per pi's schema)."""
        try:
            target = self._resolve(agent_id, path)
        except _Escalate as esc:
            return ShellOutcome(text=None, residue=esc.reason)
        if self._denied(agent_id, target) or not self._writable(agent_id, target):
            return ShellOutcome(text=f"write: {path}: Permission denied")
        if target in self._dirs() and target not in self._files():
            return ShellOutcome(text=f"write: {path}: Is a directory")
        self.scratch.write(target, content, clock)
        return ShellOutcome(text=f"Wrote {len(content.encode())} bytes to {path}")

    def edit_tool(
        self, agent_id: str, path: str, edits: list[tuple[str, str]], clock: int
    ) -> ShellOutcome:
        """Answer a pi `edit` call: apply exact-text replacements against the current bytes and record.

        Mirrors pi's schema semantics: every `oldText` must match a unique region of the ORIGINAL file;
        any failure returns the error without applying anything.
        """
        try:
            target = self._resolve(agent_id, path)
            content, error = self._read(agent_id, target)
        except _Escalate as esc:
            return ShellOutcome(text=None, residue=esc.reason)
        if content is None:
            return ShellOutcome(text=f"edit: {path}: {error}")
        if not self._writable(agent_id, target):
            return ShellOutcome(text=f"edit: {path}: Permission denied")
        updated = content
        for old, new in edits:
            count = content.count(old)
            if count == 0:
                return ShellOutcome(
                    text=f"edit: {path}: oldText not found in file: {old[:80]!r}"
                )
            if count > 1:
                return ShellOutcome(
                    text=f"edit: {path}: oldText is not unique in file ({count} matches): {old[:80]!r}"
                )
            updated = updated.replace(old, new, 1)
        self.scratch.write(target, updated, clock)
        plural = "s" if len(edits) != 1 else ""
        return ShellOutcome(text=f"Applied {len(edits)} edit{plural} to {path}")

    # ── public: bash ─────────────────────────────────────────────────────────────────────────────────────
    def run_bash(self, agent_id: str, command: str, clock: int) -> ShellOutcome:
        """Evaluate one bash command; `text=None` + `residue` means escalate the whole command."""
        heredoc_python = extract_python_source(command)
        if heredoc_python is not None:
            result = run_python(
                heredoc_python.source,
                now=self.now(clock),
                filename=heredoc_python.filename,
            )
            return ShellOutcome(text=result.output, residue=result.residue)
        try:
            marked = _scan_raw(command)
            tokens = _tokenize(marked)
            if tokens is None:
                return ShellOutcome(
                    text=(
                        "bash: unexpected EOF while looking for matching quote\n"
                        "bash: syntax error: unexpected end of file"
                    )
                )
            chains = _parse(tokens)
            return ShellOutcome(text=self._run_chains(agent_id, chains, clock))
        except _Escalate as esc:
            if esc.reason.startswith("bash: "):
                return ShellOutcome(text=esc.reason)  # a real shell ERROR, not a gap
            return ShellOutcome(text=None, residue=esc.reason)

    # ── evaluation ───────────────────────────────────────────────────────────────────────────────────────
    def _run_chains(
        self, agent_id: str, chains: list[tuple[str, list[_Simple]]], clock: int
    ) -> str:
        terminal: list[str] = []
        cwd = self.norms.cwd_by_agent.get(agent_id, "") or "/"
        state = {"cwd": cwd}
        code = 0
        for connector, pipeline in chains:
            if connector == "&&" and code != 0:
                continue
            if connector == "||" and code == 0:
                continue
            result = self._run_pipeline(agent_id, pipeline, state, clock, terminal)
            code = result.code
            if result.out:
                terminal.append(result.out)
        return "".join(terminal)

    def _run_pipeline(
        self,
        agent_id: str,
        pipeline: list[_Simple],
        state: dict[str, str],
        clock: int,
        terminal: list[str],
    ) -> _Result:
        stdin = ""
        result = _Result()
        for stage in pipeline:
            if stage.in_from is not None:
                target = self._resolve(agent_id, stage.in_from, state["cwd"])
                content, error = self._read(agent_id, target)
                if content is None:
                    terminal.append(f"bash: {stage.in_from}: {error}\n")
                    return _Result(code=1)
                stdin = content
            result = self._run_simple(agent_id, stage, stdin, state, clock)
            # stderr: swallowed by an err redirect, merged into the pipe under 2>&1, else straight to the
            # terminal as it happens (so sequential chains keep natural output order).
            err_text = result.err
            if stage.err_to is not None:
                self._sink(agent_id, stage.err_to, err_text, state, clock)
                err_text = ""
            if stage.merge_err:
                result.out += err_text
                err_text = ""
            if err_text:
                terminal.append(err_text)
            if stage.out_to is not None:
                self._sink(
                    agent_id,
                    stage.out_to,
                    result.out,
                    state,
                    clock,
                    append=stage.out_append,
                )
                result.out = ""
            stdin = result.out
        return result

    def _sink(
        self,
        agent_id: str,
        target: str,
        content: str,
        state: dict[str, str],
        clock: int,
        append: bool = False,
    ) -> None:
        """Redirect output into /dev/null or a scratch-writable file (anything else escalates)."""
        resolved = self._resolve(agent_id, target, state["cwd"])
        if resolved in ("/dev/null", "/dev/stderr", "/dev/stdout"):
            return
        if self._denied(agent_id, resolved) or not self._writable(agent_id, resolved):
            raise _Escalate(f"redirect outside writable area: {target}")
        prior = self.scratch.files.get(resolved, "") if append else ""
        self.scratch.write(resolved, prior + content, clock)

    def _run_simple(
        self,
        agent_id: str,
        cmd: _Simple,
        stdin: str,
        state: dict[str, str],
        clock: int,
    ) -> _Result:
        if not cmd.argv:
            return _Result()
        head = cmd.argv[0]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", head):
            raise _Escalate(f"environment assignment {head!r}")
        name = posixpath.basename(head)
        args = cmd.argv[1:]
        if name == "echo":
            return self._cmd_echo(args)
        if name == "printf":
            return self._cmd_printf(args)
        if name in ("cat", "less", "more", "bat"):
            return self._cmd_cat(agent_id, args, stdin, state)
        if name in ("head", "tail"):
            which: Literal["head", "tail"] = "head" if name == "head" else "tail"
            return self._cmd_head_tail(which, agent_id, args, stdin, state)
        if name == "sed":
            return self._cmd_sed(agent_id, args, stdin, state)
        if name == "wc":
            return self._cmd_wc(agent_id, args, stdin, state)
        if name == "ls":
            return self._cmd_ls(agent_id, args, state)
        if name == "grep":
            return self._cmd_grep(agent_id, args, stdin, state)
        if name == "find":
            return self._cmd_find(
                agent_id, args, state, err_suppressed=cmd.err_to is not None
            )
        if name == "cd":
            return self._cmd_cd(agent_id, args, state)
        if name == "pwd":
            return _Result(out=state["cwd"] + "\n")
        if name == "whoami":
            own = self._own_home(agent_id)
            if not own:
                raise _Escalate("whoami with no home-derived username")
            return _Result(out=posixpath.basename(own) + "\n")
        if name == "date":
            return self._cmd_date(args, clock)
        if name == "seq":
            return self._cmd_seq(args)
        if name in ("test", "["):
            return self._cmd_test(agent_id, args, state, bracket=name == "[")
        if name == "mkdir":
            return self._cmd_mkdir(agent_id, args, state, clock)
        if name == "touch":
            return self._cmd_touch(agent_id, args, state, clock)
        if name == "sleep":
            return self._cmd_sleep(args)
        if name in ("true", ":"):
            return _Result()
        if name == "false":
            return _Result(code=1)
        if name in ("python3", "python"):
            return self._cmd_python(args, stdin, clock)
        raise _Escalate(f"unsupported command {name!r}")

    # ── command implementations ──────────────────────────────────────────────────────────────────────────
    def _cmd_echo(self, args: list[str]) -> _Result:
        newline, interpret = True, False
        while args and re.fullmatch(r"-[neE]+", args[0]):
            for ch in args[0][1:]:  # bash: the LAST of -e/-E wins; -n is sticky
                if ch == "n":
                    newline = False
                else:
                    interpret = ch == "e"
            args = args[1:]
        for a in args:
            _no_glob(a)
        text = " ".join(args)
        if interpret:
            text = text.replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
        return _Result(out=text + ("\n" if newline else ""))

    def _cmd_printf(self, args: list[str]) -> _Result:
        if not args:
            return _Result()
        fmt = args[0].replace("\\n", "\n").replace("\\t", "\t")
        directives = re.findall(r"%[-+ 0-9.]*[a-zA-Z%]", fmt)
        if any(d[-1] not in "sdif%" for d in directives):
            raise _Escalate(f"printf directive beyond %s/%d/%i/%f: {directives}")
        slots = [d for d in directives if d != "%%"]

        def render(chunk: list[str]) -> str:
            values: list[str | int | float] = []
            for spec, raw in zip(slots, chunk, strict=False):
                kind = spec[-1]
                try:
                    values.append(
                        int(raw) if kind in "di" else float(raw) if kind == "f" else raw
                    )
                except ValueError:
                    raise _Escalate(f"printf argument {raw!r} for {spec}") from None
            while len(values) < len(slots):
                values.append(0 if slots[len(values)][-1] in "dif" else "")
            return fmt.replace("%i", "%d") % tuple(values)

        rest = args[1:]
        try:
            if not slots or not rest:
                # bash: a zero-directive format prints once (surplus args ignored); no args pads.
                out = render([])
            else:
                # bash reuses the format until every argument is consumed (`printf '%s\n' a b c`).
                out = "".join(
                    render(rest[k : k + len(slots)])
                    for k in range(0, len(rest), len(slots))
                )
            return _Result(out=out)
        except (TypeError, ValueError) as error:
            raise _Escalate(f"printf format: {error}") from None

    def _read_file_arg(
        self, agent_id: str, path: str, state: dict[str, str], tool: str
    ) -> tuple[str | None, str]:
        """(content, error-line) for a file argument; the error line is coreutils-shaped, '' on success."""
        _no_glob(path)
        target = self._resolve(agent_id, path, state["cwd"])
        content, error = self._read(agent_id, target)
        if content is None:
            return None, f"{tool}: {path}: {error}\n"
        return content, ""

    def _stdin_or_file(
        self,
        agent_id: str,
        path: str | None,
        stdin: str,
        state: dict[str, str],
        tool: str,
    ) -> str | _Result:
        """A filter command's input: `path`'s bytes when given, else `stdin`; a coreutils-error `_Result` on a failed read."""
        if path is None:
            return stdin
        content, error = self._read_file_arg(agent_id, path, state, tool)
        if content is None:
            return _Result(err=error, code=1)
        return content

    def _cmd_cat(
        self, agent_id: str, args: list[str], stdin: str, state: dict[str, str]
    ) -> _Result:
        number = False
        paths: list[str] = []
        for a in args:
            if a == "-n":
                number = True
            elif a.startswith("-") and a != "-":
                raise _Escalate(f"cat flag {a!r}")
            else:
                paths.append(a)
        result = _Result()
        chunks: list[str] = []
        if not paths:
            chunks.append(stdin)
        for p in paths:
            if p == "-":
                chunks.append(stdin)
                continue
            content, error = self._read_file_arg(agent_id, p, state, "cat")
            if content is None:
                result.err += error
                result.code = 1
            else:
                chunks.append(content)
        text = "".join(chunks)
        if number and text:
            lines = text.splitlines(keepends=True)
            text = "".join(f"{i + 1:6}\t{line}" for i, line in enumerate(lines))
        result.out = text
        return result

    def _cmd_head_tail(
        self,
        which: Literal["head", "tail"],
        agent_id: str,
        args: list[str],
        stdin: str,
        state: dict[str, str],
    ) -> _Result:
        count, by_bytes = 10, False
        from_start = (
            False  # GNU tail `+K`: serve from position K (1-based), not the last K
        )
        all_but_last = False  # GNU head `-K`: serve all but the last K
        paths: list[str] = []
        i = 0
        while i < len(args):
            a = args[i]
            if a in ("-n", "-c", "--lines", "--bytes"):
                if i + 1 >= len(args):
                    raise _Escalate(f"{which} missing count")
                raw = args[i + 1]
                count = abs(_int_or_escalate(raw, f"{which} count"))
                # Signed counts change WHICH bytes are served (GNU behavior, checked against coreutils):
                # `tail +K` = from position K; `head -K` = all but the last K; `head +K` == `head K`
                # and `tail -K` == `tail K` are plain. The sign must survive parsing — `int()` alone
                # inverted these into silently-wrong content.
                from_start = which == "tail" and raw.startswith("+")
                all_but_last = which == "head" and raw.startswith("-")
                by_bytes = a in ("-c", "--bytes")
                i += 2
                continue
            if re.fullmatch(r"-\d+", a):
                count, from_start, all_but_last = int(a[1:]), False, False
                i += 1
                continue
            if a.startswith("-n") and a[2:].isdigit():
                count, from_start, all_but_last = int(a[2:]), False, False
                i += 1
                continue
            if a.startswith("-"):
                raise _Escalate(f"{which} flag {a!r}")
            paths.append(a)
            i += 1
        if len(paths) > 1:
            raise _Escalate(f"{which} over multiple files")
        content = self._stdin_or_file(
            agent_id, paths[0] if paths else None, stdin, state, which
        )
        if isinstance(content, _Result):
            return content
        # Zero-count edges match GNU: `head -n 0`/`tail -n 0`/`tail -n -0` are empty, while
        # `head -n -0` and `tail -n +0` (== `+1`) are the whole input.
        if which == "head":
            sl = (
                (slice(None, -count) if count else slice(None))
                if all_but_last
                else slice(None, count)
            )
        else:
            sl = (
                slice(max(count - 1, 0), None)
                if from_start
                else (slice(-count, None) if count else slice(0, 0))
            )
        if by_bytes:
            out = content[sl]
        else:
            out = "".join(content.splitlines(keepends=True)[sl])
        return _Result(out=out)

    def _cmd_sed(
        self, agent_id: str, args: list[str], stdin: str, state: dict[str, str]
    ) -> _Result:
        """Only the corpus form: `sed -n 'N,Mp'` / `sed -n 'Np'` over one file or stdin."""
        if not args or args[0] != "-n" or len(args) > 3:
            raise _Escalate("sed beyond `sed -n 'N,Mp' [file]`")
        script = args[1] if len(args) > 1 else ""
        m = re.fullmatch(r"(\d+)(?:,(\d+))?p", script)
        if m is None:
            raise _Escalate(f"sed script {script!r}")
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else start
        content = self._stdin_or_file(
            agent_id, args[2] if len(args) == 3 else None, stdin, state, "sed"
        )
        if isinstance(content, _Result):
            return _Result(err=content.err.replace("sed: ", "sed: can't read "), code=2)
        lines = content.splitlines(keepends=True)
        return _Result(out="".join(lines[start - 1 : end]))

    def _cmd_wc(
        self, agent_id: str, args: list[str], stdin: str, state: dict[str, str]
    ) -> _Result:
        flags = [a for a in args if a.startswith("-")]
        paths = [a for a in args if not a.startswith("-")]
        if len(paths) > 1 or any(f not in ("-l", "-w", "-c") for f in flags):
            raise _Escalate("wc beyond a single file's -l/-w/-c")
        content = self._stdin_or_file(
            agent_id, paths[0] if paths else None, stdin, state, "wc"
        )
        if isinstance(content, _Result):
            return content
        active = flags or ["-l", "-w", "-c"]
        counts = [
            content.count("\n")
            if f == "-l"
            else len(content.split())
            if f == "-w"
            else len(content.encode())
            for f in ("-l", "-w", "-c")
            if f in active
        ]
        body = " ".join(str(c) for c in counts)
        return _Result(out=f"{body} {paths[0]}\n" if paths else f"{body}\n")

    def _cmd_ls(self, agent_id: str, args: list[str], state: dict[str, str]) -> _Result:
        long_form = show_all = sort_time = reverse = dir_itself = False
        operands: list[str] = []
        for a in args:
            if a.startswith("-") and a != "-":
                for ch in a[1:]:
                    if ch == "l":
                        long_form = True
                    elif ch in "aA":
                        show_all = True
                    elif ch == "t":
                        sort_time = True
                    elif ch == "r":
                        reverse = True
                    elif ch == "d":
                        dir_itself = True
                    elif ch not in "1h":
                        raise _Escalate(f"ls flag -{ch}")
            else:
                operands.append(a)
        if not operands:
            operands = ["."]
        result = _Result()
        sections: list[str] = []
        for op in operands:
            _no_glob(op)
            section = self._ls_one(
                agent_id,
                op,
                state,
                result,
                long_form=long_form,
                show_all=show_all,
                sort_time=sort_time,
                reverse=reverse,
                dir_itself=dir_itself,
            )
            if section is not None:
                header = f"{op}:\n" if len(operands) > 1 else ""
                sections.append(header + section)
        result.out = "\n".join(sections)
        return result

    def _ls_one(
        self,
        agent_id: str,
        op: str,
        state: dict[str, str],
        result: _Result,
        *,
        long_form: bool,
        show_all: bool,
        sort_time: bool,
        reverse: bool,
        dir_itself: bool,
    ) -> str | None:
        target = self._resolve(agent_id, op, state["cwd"])
        files, dirs = self._files(), self._dirs()
        if self._denied(agent_id, target):
            # Only the 0700 home ROOT is statable from its parent ("cannot open directory"); traversal to
            # any subpath is blocked at the home, so those render "cannot access" like a real box.
            kind = "open directory" if target in self.norms.private_homes else "access"
            result.err += f"ls: cannot {kind} '{op}': Permission denied\n"
            result.code = 2
            return None
        if target in files:
            return self._render_ls(
                [_LsEntry(op, target, False)], long_form=long_form, with_total=False
            )
        if target not in dirs:
            if not self._in_tree(target):
                raise _Escalate(f"ls outside the known tree: {target}")
            result.err += f"ls: cannot access '{op}': No such file or directory\n"
            result.code = 2
            return None
        if dir_itself:
            return self._render_ls(
                [_LsEntry(op, target, True)], long_form=long_form, with_total=False
            )
        entries = [
            _LsEntry(posixpath.basename(p), p, False)
            for p in files
            if posixpath.dirname(p) == target
        ]
        file_names = {e.name for e in entries}
        entries += [
            _LsEntry(posixpath.basename(d), d, True)
            for d in dirs
            if posixpath.dirname(d) == target
            and d != target
            and posixpath.basename(d) not in file_names
        ]
        if sort_time:
            entries.sort(key=lambda e: self._mtime(e.path), reverse=not reverse)
        else:
            entries.sort(key=lambda e: e.name, reverse=reverse)
        if show_all:
            parent = posixpath.dirname(target) or "/"
            entries = [
                _LsEntry(".", target, True),
                _LsEntry("..", parent, True),
                *entries,
            ]
        return self._render_ls(entries, long_form=long_form, with_total=long_form)

    def _render_ls(
        self, entries: list[_LsEntry], *, long_form: bool, with_total: bool
    ) -> str:
        if not entries:
            return ""
        if not long_form:
            return "".join(f"{e.name}\n" for e in entries)
        files = self._files()
        rows: list[tuple[str, int, str, str, int, str, str]] = []
        for e in entries:
            size = _DIR_SIZE if e.is_dir else len(files.get(e.path, "").encode())
            owner = _owner_of(e.path)
            if e.is_dir:
                mode = (
                    "drwx------" if e.path in self.norms.private_homes else "drwxr-xr-x"
                )
            else:
                mode = "-rw-r--r--"
            nlink = 2 if e.is_dir else 1
            stamp = self._mtime(e.path).strftime("%b %d %H:%M")
            rows.append((mode, nlink, owner, owner, size, stamp, e.name))
        size_w = max(len(str(r[4])) for r in rows)
        lines: list[str] = []
        if with_total:
            blocks = sum(
                4 if r[0].startswith("d") else ((r[4] + 4095) // 4096) * 4 for r in rows
            )
            lines.append(f"total {blocks}")
        for mode, nlink, owner, group, size, stamp, name in rows:
            lines.append(
                f"{mode} {nlink} {owner} {group} {size:>{size_w}} {stamp} {name}"
            )
        return "".join(f"{ln}\n" for ln in lines)

    def _cmd_find(
        self,
        agent_id: str,
        args: list[str],
        state: dict[str, str],
        *,
        err_suppressed: bool,
    ) -> _Result:
        has_root = bool(args) and not args[0].startswith("-")
        root_arg = args[0] if has_root else "."
        rest = args[1:] if has_root else list(args)
        maxdepth: int | None = None
        type_filter: str | None = None
        name_tests: list[tuple[str, bool]] = []  # (pattern, case_insensitive) — OR-ed
        i = 0
        while i < len(rest):
            a = rest[i]
            if a == "-maxdepth":
                maxdepth = _int_or_escalate(
                    rest[i + 1] if i + 1 < len(rest) else "", "find -maxdepth"
                )
                i += 2
            elif a == "-type":
                if i + 1 >= len(rest) or rest[i + 1] not in ("f", "d"):
                    raise _Escalate("find -type beyond f/d")
                type_filter = rest[i + 1]
                i += 2
            elif a in ("-name", "-iname"):
                if i + 1 >= len(rest):
                    raise _Escalate(f"find {a} missing pattern")
                name_tests.append((rest[i + 1], a == "-iname"))
                i += 2
            elif a in ("-o", "-a"):
                i += 1  # name tests OR together; -a is the implicit conjunction
            else:
                raise _Escalate(f"find predicate {a!r}")
        root = self._resolve(agent_id, root_arg, state["cwd"])
        if root == "/":
            # A whole-system find is only answerable when a name filter scopes it to scenario tokens; the
            # permission-noise stderr a real box would add must have been redirected away (every corpus
            # case is `2>/dev/null`), else the missing noise itself would be a tell — escalate.
            if not name_tests:
                raise _Escalate("unfiltered find from / (whole-system listing)")
            if not err_suppressed:
                raise _Escalate("find from / without stderr suppression")
        elif not self._in_tree(root):
            raise _Escalate(f"find outside the known tree: {root}")
        result = _Result()
        if self._denied(agent_id, root):
            result.err += f"find: '{root_arg}': Permission denied\n"
            result.code = 1
            return result
        files, dirs = self._files(), self._dirs()
        own = self._own_home(agent_id)
        foreign_homes = sorted(h for h in self.norms.private_homes if h != own)
        lines: list[str] = []
        for path in sorted(set(files) | dirs):
            if not _under(path, root):
                continue
            foreign = next((h for h in foreign_homes if _under(path, h)), None)
            if foreign is not None and path != foreign:
                continue  # inside a foreign 0700 home: not enumerable
            depth = (
                (0 if path == "/" else path.count("/"))
                if root == "/"
                else (0 if path == root else path[len(root) :].count("/"))
            )
            if maxdepth is not None and depth > maxdepth:
                continue  # pruned before the walk reaches it — no perm noise either
            if foreign is not None:
                # Real find prints the perm error whenever it VISITS the 0700 dir, regardless of -name.
                result.err += f"find: '{path}': Permission denied\n"
                result.code = 1
            is_dir = path in dirs and path not in files
            if (type_filter == "f" and is_dir) or (type_filter == "d" and not is_dir):
                continue
            if name_tests:
                base = posixpath.basename(path) or "/"
                if not any(
                    fnmatch(base.lower(), pat.lower()) if ci else fnmatch(base, pat)
                    for pat, ci in name_tests
                ):
                    continue
            lines.append(path)
        result.out = "".join(f"{p}\n" for p in lines)
        return result

    def _cmd_grep(
        self, agent_id: str, args: list[str], stdin: str, state: dict[str, str]
    ) -> _Result:
        ignore = invert = count_only = quiet = fixed = extended = line_no = False
        after = before = 0
        pattern: str | None = None
        paths: list[str] = []
        i = 0
        while i < len(args):
            a = args[i]
            if a.startswith("--"):
                raise _Escalate(f"grep flag {a!r}")
            if a.startswith("-") and a != "-":
                m = re.fullmatch(r"-([ABC])(\d+)?", a)
                if m:
                    if m.group(2):
                        val = int(m.group(2))
                    else:
                        val = _int_or_escalate(
                            args[i + 1] if i + 1 < len(args) else "", "grep context"
                        )
                        i += 1
                    if m.group(1) in ("A", "C"):
                        after = val
                    if m.group(1) in ("B", "C"):
                        before = val
                    i += 1
                    continue
                for ch in a[1:]:
                    if ch == "i":
                        ignore = True
                    elif ch == "v":
                        invert = True
                    elif ch == "c":
                        count_only = True
                    elif ch == "q":
                        quiet = True
                    elif ch == "F":
                        fixed = True
                    elif ch == "E":
                        extended = True
                    elif ch == "n":
                        line_no = True
                    else:
                        raise _Escalate(f"grep flag -{ch}")
                i += 1
                continue
            if pattern is None:
                pattern = a
            else:
                paths.append(a)
            i += 1
        if pattern is None:
            raise _Escalate("grep with no pattern")
        regex = _compile_grep(pattern, fixed=fixed, extended=extended, ignore=ignore)
        result = _Result()
        sources: list[tuple[str | None, str]] = []
        for p in paths:
            content, error = self._read_file_arg(agent_id, p, state, "grep")
            if content is None:
                result.err += error
                result.code = 2
            else:
                sources.append((p if len(paths) > 1 else None, content))
        if not paths:
            sources.append((None, stdin))
        any_match = False
        out_parts: list[str] = []
        for label, content in sources:
            lines = content.splitlines()
            matched = [
                k for k, ln in enumerate(lines) if bool(regex.search(ln)) != invert
            ]
            any_match = any_match or bool(matched)
            prefix = f"{label}:" if label else ""
            if count_only:
                out_parts.append(f"{prefix}{len(matched)}\n")
                continue
            keep: set[int] = set()
            for k in matched:
                keep.update(range(max(0, k - before), min(len(lines), k + after + 1)))
            prev: int | None = None
            for k in sorted(keep):
                if prev is not None and k > prev + 1 and (after or before):
                    out_parts.append("--\n")
                number = f"{k + 1}:" if line_no else ""
                out_parts.append(f"{prefix}{number}{lines[k]}\n")
                prev = k
        result.out = "" if quiet else "".join(out_parts)
        if result.code == 0 and not any_match:
            result.code = 1
        return result

    def _cmd_cd(self, agent_id: str, args: list[str], state: dict[str, str]) -> _Result:
        target_arg = args[0] if args else "~"
        target = self._resolve(agent_id, target_arg, state["cwd"])
        if self._denied(agent_id, target):
            return _Result(err=f"bash: cd: {target_arg}: Permission denied\n", code=1)
        if target in self._files():
            return _Result(err=f"bash: cd: {target_arg}: Not a directory\n", code=1)
        if target not in self._dirs():
            if not self._in_tree(target):
                raise _Escalate(f"cd outside the known tree: {target}")
            return _Result(
                err=f"bash: cd: {target_arg}: No such file or directory\n", code=1
            )
        state["cwd"] = target
        return _Result()

    def _cmd_test(
        self, agent_id: str, args: list[str], state: dict[str, str], *, bracket: bool
    ) -> _Result:
        if bracket:
            if not args or args[-1] != "]":
                return _Result(err="bash: [: missing `]'\n", code=2)
            args = args[:-1]
        if len(args) != 2 or args[0] not in ("-f", "-d", "-e", "-s"):
            raise _Escalate(f"test expression {' '.join(args)!r}")
        flag, path = args
        target = self._resolve(agent_id, path, state["cwd"])
        if self._denied(agent_id, target):
            return _Result(code=1)
        if not self._in_tree(target):
            raise _Escalate(f"test outside the known tree: {target}")
        files, dirs = self._files(), self._dirs()
        ok = {
            "-f": target in files,
            "-d": target in dirs and target not in files,
            "-e": target in files or target in dirs,
            "-s": bool(files.get(target)),
        }[flag]
        return _Result(code=0 if ok else 1)

    def _cmd_seq(self, args: list[str]) -> _Result:
        pad = False
        sep = "\n"
        rest: list[str] = []
        i = 0
        while i < len(args):
            if args[i] == "-w":
                pad = True
            elif args[i] == "-s":
                sep = args[i + 1] if i + 1 < len(args) else "\n"
                i += 1
            elif args[i].startswith("-") and not re.fullmatch(r"-\d+", args[i]):
                raise _Escalate(f"seq flag {args[i]!r}")
            else:
                rest.append(args[i])
            i += 1
        nums = [_int_or_escalate(r, "seq operand") for r in rest]
        if not 1 <= len(nums) <= 3:
            raise _Escalate("seq operand count")
        if len(nums) == 1:
            first, step, last = 1, 1, nums[0]
        elif len(nums) == 2:
            first, step, last = nums[0], 1, nums[1]
        else:
            first, step, last = nums[0], nums[1], nums[2]
        if step == 0:
            return _Result(err="seq: invalid Zero increment value: '0'\n", code=1)
        values = list(range(first, last + (1 if step > 0 else -1), step))
        width = max((len(str(v)) for v in values), default=1)
        body = sep.join(f"{v:0{width}d}" if pad else str(v) for v in values)
        return _Result(out=body + "\n" if values else "")

    def _cmd_date(self, args: list[str], clock: int) -> _Result:
        now = self.now(clock)
        fmt: str | None = None
        for a in args:
            if a in ("-u", "--utc"):
                continue  # the world clock renders in UTC already
            if a.startswith("+"):
                fmt = a[1:]
                continue
            raise _Escalate(f"date argument {a!r}")
        if fmt is None:
            day = f"{now.day}".rjust(2)
            return _Result(
                out=f"{now.strftime('%a %b')} {day} {now.strftime('%H:%M:%S')} UTC {now.year}\n"
            )
        if "%N" in fmt:
            raise _Escalate("date %N (sub-second)")
        rendered = fmt.replace("%s", str(_epoch_seconds(now)))
        return _Result(out=now.strftime(rendered) + "\n")

    def _cmd_mkdir(
        self, agent_id: str, args: list[str], state: dict[str, str], clock: int
    ) -> _Result:
        parents = "-p" in args
        if any(a.startswith("-") and a != "-p" for a in args):
            raise _Escalate("mkdir flags beyond -p")
        result = _Result()
        for p in (a for a in args if not a.startswith("-")):
            target = self._resolve(agent_id, p, state["cwd"])
            if self._denied(agent_id, target) or not self._writable(agent_id, target):
                result.err += (
                    f"mkdir: cannot create directory '{p}': Permission denied\n"
                )
                result.code = 1
            elif target in self._dirs() or target in self._files():
                if not parents:
                    result.err += f"mkdir: cannot create directory '{p}': File exists\n"
                    result.code = 1
            elif not parents and posixpath.dirname(target) not in self._dirs():
                result.err += (
                    f"mkdir: cannot create directory '{p}': No such file or directory\n"
                )
                result.code = 1
            else:
                self.scratch.dirs.add(target)
                self.scratch.mtimes[target] = clock
        return result

    def _cmd_touch(
        self, agent_id: str, args: list[str], state: dict[str, str], clock: int
    ) -> _Result:
        if any(a.startswith("-") for a in args):
            raise _Escalate("touch flags")
        result = _Result()
        for p in args:
            target = self._resolve(agent_id, p, state["cwd"])
            if self._denied(agent_id, target) or not self._writable(agent_id, target):
                result.err += f"touch: cannot touch '{p}': Permission denied\n"
                result.code = 1
            elif target in self.norms.served or target in self.scratch.files:
                self.scratch.mtimes[target] = clock
            else:
                self.scratch.write(target, "", clock)
        return result

    def _cmd_sleep(self, args: list[str]) -> _Result:
        if len(args) != 1:
            raise _Escalate("sleep operands")
        try:
            seconds = float(args[0].rstrip("s"))
        except ValueError:
            raise _Escalate(f"sleep operand {args[0]!r}") from None
        if seconds > 120:
            raise _Escalate(f"sleep {seconds:g}s (would advance the world)")
        return _Result()

    def _cmd_python(self, args: list[str], stdin: str, clock: int) -> _Result:
        """`python3 -c "<src>"` as one segment of a compound (the heredoc form is whole-command only)."""
        if len(args) != 2 or args[0] != "-c" or stdin:
            raise _Escalate('python3 beyond a plain `python3 -c "<src>"`')
        outcome = run_python(args[1], now=self.now(clock), filename="<string>")
        if outcome.output is None:
            raise _Escalate(outcome.residue)
        return _Result(out=outcome.output, code=outcome.code)


def _epoch_seconds(now: datetime) -> int:
    """Unix seconds for a naive world instant rendered as UTC."""
    return int(now.replace(tzinfo=timezone.utc).timestamp())


def _owner_of(path: str) -> str:
    parts = path.split("/")
    return parts[2] if len(parts) > 2 and parts[1] == "home" else "root"


def _no_glob(token: str) -> None:
    """Escalate a token that LOOKS like an unquoted glob (glob chars, no whitespace).

    shlex strips quotes, so `"a * b"` (one token with spaces — provably quoted, literal) is fine, while a
    bare `*.md` could have been an unquoted glob bash would expand — escalate rather than guess.
    """
    if any(ch in token for ch in "*?[") and not any(ch.isspace() for ch in token):
        raise _Escalate(f"possible glob {token!r}")


def _int_or_escalate(raw: str, what: str) -> int:
    try:
        return int(raw)
    except ValueError:
        raise _Escalate(f"{what}: {raw!r}") from None


def _compile_grep(
    pattern: str, *, fixed: bool, extended: bool, ignore: bool
) -> re.Pattern[str]:
    """Compile a grep pattern: `-F` literal, `-E` as-is, default BRE-lite translated to Python re."""
    if fixed:
        source = re.escape(pattern)
    elif extended:
        source = pattern
    else:
        out: list[str] = []
        i = 0
        while i < len(pattern):
            c = pattern[i]
            if c == "\\" and i + 1 < len(pattern) and pattern[i + 1] in "|(){}+?":
                out.append(pattern[i + 1])  # BRE escaped operator -> ERE operator
                i += 2
                continue
            if c in "|(){}+?":
                out.append("\\" + c)  # BRE literal
                i += 1
                continue
            out.append(c)
            i += 1
        source = "".join(out)
    try:
        return re.compile(source, re.IGNORECASE if ignore else 0)
    except re.error as error:
        raise _Escalate(f"grep pattern {pattern!r}: {error}") from None


__all__ = [
    "MechanicalShell",
    "ScratchRegistry",
    "ShellOutcome",
]
