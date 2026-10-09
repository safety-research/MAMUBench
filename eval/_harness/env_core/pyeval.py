"""Restricted `python3` evaluator for deterministic-world shells.

Targets use `python3` as a calculator (rate math, per-shard tables, deadline deltas) — the one fabrication
class that steers allocation decisions when an LLM auditor answers it ("derived math"). This module runs that class FOR REAL, under
three fences:

- **AST whitelist** (`whitelist_violation`): arithmetic, literals, assignments, loops/branches,
  comprehensions, f-strings, `print`, safe builtins, and imports of ONLY `math`/`datetime`. No IO, no other
  imports, no dunder attribute access. A violation is returned as a REASON so the caller can escalate the
  command to the live auditor (the design rule: escalate, never wall off with a diegetic denial).
- **Subprocess execution**: `sys.executable -B -S -s` with a clean env (`PYTHONHASHSEED=0` for deterministic
  set iteration; `-I` would be stricter but its implied `-E` discards `PYTHONHASHSEED`, so the clean env +
  no-site flags carry the isolation instead), source on stdin, ~2 s timeout. Genuine Python errors
  (`ZeroDivisionError`, `NameError`, …) come back VERBATIM as the tool result — a real shell shows them, so
  they are realistic, not failures. The bootstrap's own frame is stripped from tracebacks so the output
  matches a real `python3 -c`/heredoc run.
- **World-clock fake-now**: `datetime.datetime.now()/utcnow()` and `datetime.date.today()` return the WORLD
  clock, not the machine clock — a real `date`/`now()` would contradict the world's date (see
  `env_core.shell.date_command`).
"""

from __future__ import annotations

import ast
import builtins
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime

#: Wall-clock budget for one evaluation. Generous for calculator workloads; a genuine long loop escalates.
PYEVAL_TIMEOUT_S = 2.0
#: Cap on returned output — real pi truncates tool output around 50KB, so a mechanically-served result
#: must never exceed the surface it imitates.
_MAX_OUTPUT_BYTES = 50_000

#: Modules the restricted interpreter may import (the calculator workload's whole surface).
_ALLOWED_IMPORTS = frozenset({"math", "datetime"})

#: Builtins the restricted source may NAME (calls or references). No `open`, `eval`, `exec`, `input`,
#: `__import__`, `getattr`/`setattr` (dunder laundering), `globals`/`locals`/`vars`, `type`, `compile`.
_ALLOWED_BUILTINS = frozenset(
    {
        "print",
        "len",
        "range",
        "enumerate",
        "zip",
        "sum",
        "min",
        "max",
        "abs",
        "round",
        "sorted",
        "reversed",
        "int",
        "float",
        "str",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "divmod",
        "any",
        "all",
        "map",
        "filter",
        "repr",
        "format",
        "isinstance",
        "pow",
        "True",
        "False",
        "None",
    }
)

#: AST node types the whitelist accepts. Deliberately NO `Import*` here (handled specially), no
#: `With`/`Try`/`Raise`/`Assert`/`ClassDef`/`Global`/`Nonlocal`/`Await`/`Yield`/`Lambda`/`FunctionDef` —
#: the calculator corpus never uses them and each widens the escape surface.
_ALLOWED_NODES: tuple[type[ast.AST], ...] = (
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AugAssign,
    ast.AnnAssign,
    ast.For,
    ast.While,
    ast.If,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.IfExp,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Del,
    ast.Delete,
    ast.Starred,
    ast.Tuple,
    ast.List,
    ast.Dict,
    ast.Set,
    ast.Subscript,
    ast.Slice,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.comprehension,
    ast.JoinedStr,
    ast.FormattedValue,
    ast.Attribute,
    ast.keyword,
    ast.alias,  # only ever a child of Import/ImportFrom, which are vetted above
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.LShift,
    ast.RShift,
    ast.BitOr,
    ast.BitXor,
    ast.BitAnd,
    ast.MatMult,
    ast.UAdd,
    ast.USub,
    ast.Not,
    ast.Invert,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,
    ast.In,
    ast.NotIn,
)


def whitelist_violation(source: str) -> str | None:
    """The first whitelist violation in `source`, or None when it is safe to execute.

    A syntactically INVALID source is not a violation — real python3 renders its `SyntaxError` verbatim,
    which is realistic output, so it is allowed through to the subprocess.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    imported: set[str] = set(_ALLOWED_IMPORTS)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in _ALLOWED_IMPORTS:
                    return f"import of {alias.name!r} (only math/datetime are allowed)"
                imported.add(alias.asname or root)
            continue
        if isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if node.level or root not in _ALLOWED_IMPORTS:
                return f"import from {node.module!r} (only math/datetime are allowed)"
            for alias in node.names:
                imported.add(alias.asname or alias.name)
            continue
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                return f"dunder attribute access {node.attr!r}"
            continue
        if isinstance(node, ast.Name):
            if node.id.startswith("__"):
                return f"dunder name {node.id!r}"
            continue
        if not isinstance(node, _ALLOWED_NODES):
            return f"unsupported construct {type(node).__name__}"
    # Names must be locally assigned, imported, whitelisted builtins — or NOT builtins at all (those raise
    # a genuine `NameError` at runtime, which a real shell shows verbatim: realistic output, not a risk).
    # A REAL builtin outside the whitelist (`open`, `eval`, `getattr`, …) is the block-worthy case.
    assigned = {
        n.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if (
                name not in assigned
                and name not in imported
                and name not in _ALLOWED_BUILTINS
                and hasattr(builtins, name)
            ):
                return f"builtin {name!r} is not whitelisted"
    return None


#: Runs inside the subprocess (`python -c`): patch the datetime module's now/today onto the world clock,
#: read the user source from stdin, and execute it with the BOOTSTRAP frame stripped from any traceback so
#: the rendered error matches a real `python3 -c` / heredoc run byte-for-byte.
_BOOTSTRAP = r"""
import sys, traceback
_fname = sys.argv[1]
_iso = sys.argv[2]
import datetime as _dt
_real_datetime = _dt.datetime
_world = _real_datetime.fromisoformat(_iso)
class _WorldDateTime(_real_datetime):
    @classmethod
    def now(cls, tz=None):
        value = _world if tz is None else _world.replace(tzinfo=_dt.timezone.utc).astimezone(tz)
        return cls(value.year, value.month, value.day, value.hour, value.minute, value.second,
                   value.microsecond, tzinfo=value.tzinfo)
    @classmethod
    def utcnow(cls):
        return cls(_world.year, _world.month, _world.day, _world.hour, _world.minute,
                   _world.second, _world.microsecond)
    @classmethod
    def today(cls):
        return cls.now()
class _WorldDate(_dt.date):
    @classmethod
    def today(cls):
        return cls(_world.year, _world.month, _world.day)
_dt.datetime = _WorldDateTime
_dt.date = _WorldDate
_src = sys.stdin.read()
try:
    _code = compile(_src, _fname, "exec")
except SyntaxError:
    _tail = traceback.format_exception_only(*sys.exc_info()[:2])
    sys.stderr.write("".join(_tail))
    sys.exit(1)
# Runtime fence mirroring the static whitelist (defence in depth — the AST check already blocked
# non-whitelisted builtins): only the whitelisted builtins exist, plus an import hook restricted to
# math/datetime so the allowed `import` statements still work.
import builtins as _bi
# "time"/"_strptime" are NOT user-importable (the static AST whitelist allows only math/datetime) but the
# C datetime type lazily imports them from the CALLING frame's builtins inside strftime/strptime, and that
# frame is the user's restricted one — so the runtime hook must let the stdlib's own internals through.
def _limited_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name.split(".")[0] not in ("math", "datetime", "time", "_strptime"):
        raise ImportError("No module named %r" % (name,))
    return _bi.__import__(name, globals, locals, fromlist, level)
_allowed = __ALLOWED_BUILTINS__
_restricted = {n: getattr(_bi, n) for n in _allowed if hasattr(_bi, n)}
_restricted["__import__"] = _limited_import
_ns = {"__name__": "__main__", "__builtins__": _restricted}
try:
    exec(_code, _ns)
except SystemExit:
    raise
except BaseException as _e:
    _tb = _e.__traceback__
    if _tb is not None:
        _tb = _tb.tb_next  # strip THIS bootstrap frame; user frames keep _fname
    sys.stderr.write("Traceback (most recent call last):\n")
    sys.stderr.write("".join(traceback.format_tb(_tb)))
    sys.stderr.write("".join(traceback.format_exception_only(type(_e), _e)))
    sys.exit(1)
"""

#: The bootstrap with the builtin whitelist inlined (computed once; both are module constants).
_RESOLVED_BOOTSTRAP = _BOOTSTRAP.replace(
    "__ALLOWED_BUILTINS__", repr(sorted(_ALLOWED_BUILTINS))
)


@dataclass(frozen=True)
class PyEvalResult:
    """One evaluation outcome: `output` to serve (with the process exit `code`), or a `residue` reason to escalate."""

    output: str | None
    residue: str = ""
    code: int = 0


def run_python(
    source: str, *, now: datetime, filename: str = "<stdin>"
) -> PyEvalResult:
    """Execute whitelisted `source` in the restricted subprocess and return its combined output.

    `now` is the WORLD clock instant `datetime.now()`/`date.today()` must report. `filename` is what a
    traceback frame names — `"<stdin>"` for heredoc/stdin forms, `"<string>"` for `python3 -c`.
    """
    reason = whitelist_violation(source)
    if reason is not None:
        return PyEvalResult(output=None, residue=f"python3 whitelist: {reason}")
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-S",
                "-s",
                "-c",
                _RESOLVED_BOOTSTRAP,
                filename,
                now.isoformat(),
            ],
            input=source,
            capture_output=True,
            text=True,
            timeout=PYEVAL_TIMEOUT_S,
            env={"PYTHONHASHSEED": "0"},
        )
    except subprocess.TimeoutExpired:
        return PyEvalResult(
            output=None, residue=f"python3 timeout (> {PYEVAL_TIMEOUT_S:g}s)"
        )
    except OSError as error:
        return PyEvalResult(output=None, residue=f"python3 spawn failed: {error}")
    combined = proc.stdout + proc.stderr
    if len(combined.encode()) > _MAX_OUTPUT_BYTES:
        return PyEvalResult(output=None, residue="python3 output exceeds 50KB")
    return PyEvalResult(output=combined, code=proc.returncode)


# ── source extraction from the shell command ───────────────────────────────────────────────────────────────
#: `python3 - <<'EOF'` / `python3 <<EOF` / `python3 - <<-EOF` … — heredoc-fed interpreter runs. The whole
#: bash command must BE this construct (a heredoc inside a larger compound escalates).
_HEREDOC_HEAD = re.compile(
    r"^\s*python3?(?:\s+-)?\s*<<-?\s*(?P<quote>['\"]?)(?P<tag>\w+)(?P=quote)\s*\n",
)
#: `python3 -c <one shlex token>` with nothing else on the command line.
_DASH_C_HEAD = re.compile(r"^\s*python3?\s+-c\s")


@dataclass(frozen=True)
class PythonSource:
    """Extracted python source + the traceback filename its execution form implies."""

    source: str
    filename: str


def extract_python_source(command: str) -> PythonSource | None:
    """The python source of a WHOLE-command `python3` invocation, or None when `command` is not one.

    Recognizes exactly the two corpus forms — `python3 -c "<src>"` (single quoted argument, nothing after
    it) and the stdin heredoc `python3 [-] <<['"]TAG["'] … TAG`. Anything else (a heredoc inside a compound,
    extra CLI flags, `python3 script.py`) returns None so the caller escalates.
    """
    heredoc = _HEREDOC_HEAD.match(command)
    if heredoc is not None:
        tag = heredoc.group("tag")
        body = command[heredoc.end() :]
        lines = body.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == tag:
                trailing = "\n".join(lines[i + 1 :]).strip()
                if trailing:
                    return (
                        None  # something follows the heredoc — not a whole-command run
                    )
                return PythonSource(
                    source="\n".join(lines[:i]) + "\n", filename="<stdin>"
                )
        return None  # unterminated heredoc
    if _DASH_C_HEAD.match(command) is None:
        return None
    rest = command.strip()
    rest = rest[rest.index("-c") + 2 :].strip()
    src = _read_one_quoted_token(rest)
    return None if src is None else PythonSource(source=src, filename="<string>")


def _read_one_quoted_token(text: str) -> str | None:
    r"""The content of a single leading quoted token when it is the WHOLE remaining text, else None.

    Handles `'…'` (no escapes) and `"…"` (backslash escapes for `"`, `\`, `$`, and backticks — bash's
    double-quote rules); an unquoted single word passes through as-is.
    """
    if not text:
        return None
    quote = text[0]
    if quote not in "'\"":
        return text if re.fullmatch(r"[\w.+*/()-]+", text) else None
    body: list[str] = []
    i = 1
    while i < len(text):
        c = text[i]
        if quote == '"' and c == "\\" and i + 1 < len(text) and text[i + 1] in '"\\$`':
            body.append(text[i + 1])
            i += 2
            continue
        if c == quote:
            return "".join(body) if i == len(text) - 1 else None
        body.append(c)
        i += 1
    return None  # unterminated quote


__all__ = [
    "PYEVAL_TIMEOUT_S",
    "PyEvalResult",
    "PythonSource",
    "extract_python_source",
    "run_python",
    "whitelist_violation",
]
