"""pi process control for the real-harness twin: spawn / one-turn / close.

Ported and generalized from the authors' research harnesses for merge-queue and cluster pi runs (both
validated against pi 0.77.0).
Each seat runs one persistent `pi --mode rpc` process; a turn is one JSON prompt line on stdin answered by
a stream of events on stdout ending in a terminal `agent_end`, whose `messages` are the turn's full
message list (assistant text + tool calls + tool results).

The pi executable is resolved from `EVAL_PI_CMD` (default `pi`) so a local machine can point at a
specific install (e.g. `EVAL_PI_CMD="npx @earendil-works/pi-coding-agent"`); tests point it at
`fake_pi.py` to keep the suite offline and deterministic. personal_assistant's docker tier composes a full
`docker exec` argv instead (`personal_assistant/environment/live_docker.py`) — the turn/kill discipline here
is transport-agnostic: a `PiHandle` carries an optional out-of-band `kill_argv` for processes the host-side
group kill cannot reach.
"""

from __future__ import annotations

import functools
import json
import os
import shlex
import signal
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

#: The reviewed pi version — the RPC event shapes and flags below were validated at exactly this pin.
PI_PIN = "0.77.0"

#: Default per-turn watchdog. A pi turn is a full agentic burst (many bash/read/edit calls), so this is
#: generous; the runner passes its own value from config.
DEFAULT_TURN_TIMEOUT = 300.0


def pi_argv() -> list[str]:
    """The pi launch argv prefix from `EVAL_PI_CMD` (default `pi`)."""
    return shlex.split(os.environ.get("EVAL_PI_CMD", "pi"))


def rpc_argv(
    *, provider: str, model: str, session_dir: Path, context_files: bool = False
) -> list[str]:
    """The pi flags for one hermetic RPC seat (appended to `pi_argv()` or a docker exec prefix).

    `--no-context-files` keeps the launch hermetic (no AGENTS.md auto-load — the operator handoff is the
    first prompt, matching the sim cells' bring-up); `--no-skills`/`--no-prompt-templates` close the other
    ambient-config surfaces the same way the merge_queue live harness does. `--no-extensions` is NOT used:
    the labctl extension in the agent dir is the twin's typed tool surface.

    `context_files=True` (only personal_assistant's supplementary `--context-files on`
    variant passes it) omits that one flag, so pi loads the AGENTS.md in the seat's cwd as a
    `<project_context>` block of its system prompt. The default is every other caller's argv, unchanged.
    """
    return [
        "--mode",
        "rpc",
        "--provider",
        provider,
        "--model",
        model,
        *(() if context_files else ("--no-context-files",)),
        "--no-skills",
        "--no-prompt-templates",
        "--session-dir",
        str(session_dir),
    ]


@functools.lru_cache(maxsize=None)
def _version_output(argv: tuple[str, ...]) -> str | None:
    """`<argv> --version` output — read stdout OR stderr (pi 0.77/0.78 print the version to stderr).

    Cached per argv: the value cannot change within a run, and the probe spawns a process (against
    fake_pi interactively it even blocks on an inherited tty stdin until the 60s timeout).
    """
    try:
        out = subprocess.run(
            [*argv, "--version"],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return (out.stdout or out.stderr).strip() or None


def pi_version() -> str | None:
    """`pi --version` (stripped), or None if the executable is missing/broken."""
    return _version_output(tuple(pi_argv()))


def node_major(version: str) -> int:
    """The major from a `node --version` string (`v22.1.0` -> 22); raises `ValueError` if unparseable."""
    return int(version.removeprefix("v").split(".", maxsplit=1)[0])


def matches_pin(version: str) -> bool:
    """Whether a pi version string's last token equals `PI_PIN` (handles `pi 0.77.0` and bare forms)."""
    return version.split()[-1].removeprefix("v") == PI_PIN


def validate_runtime() -> None:
    """Require the reviewed host runtime: Node 22+ and pi 0.77.0 exactly.

    Vendored from the merge_queue harness guard (`validate_pi_runtime`). Raises `SystemExit` with an
    actionable message; the docker tier runs its own in-image probe instead (`docker_tier.validate_image`).
    """
    node = _version_output(("node",))
    if node is None:
        raise SystemExit("node not found — the twin needs Node 22+ on PATH to run pi")
    try:
        major = node_major(node)
    except ValueError:
        raise SystemExit(f"could not parse node version {node!r}") from None
    if major < 22:
        raise SystemExit(f"Node 22+ is required; found {node!r}")
    pi = pi_version()
    if pi is None:
        raise SystemExit(
            "pi not found — set EVAL_PI_CMD or put `pi` (0.77.0) + node 22 on PATH"
        )
    if not matches_pin(pi):
        raise SystemExit(
            f"pi {pi!r} found, but the twin is validated against {PI_PIN} exactly "
            "(set EVAL_PI_CMD at your own risk after re-validating)"
        )


def auth_json(provider: str, api_key: str) -> str:
    """The auth-file payload pi's `/login` persists — the ONE place its format is known."""
    return json.dumps({provider: {"type": "api_key", "key": api_key}}) + "\n"


def write_auth_file(agent_dir: Path, *, provider: str, api_key: str) -> None:
    """Store the provider credential in pi's auth file instead of the process env.

    pi resolves API keys from `<agent dir>/auth.json` (`~/.pi/agent/` by default; a
    `PI_CODING_AGENT_DIR` override relocates the auth lookup too, so the twin keeps every seat on the
    default per-home agent dir), taking priority over environment variables. The live key therefore never
    sits in the environment a pi bash subshell inherits — a seat that runs `env` in its real shell must
    not see the vendor key in its transcript (vendored from the merge_queue harness).
    Written `0600`, mirroring how pi's own `/login` persists it.
    """
    agent_dir.mkdir(parents=True, exist_ok=True)
    auth_path = agent_dir / "auth.json"
    auth_path.write_text(auth_json(provider, api_key))
    auth_path.chmod(0o600)


@dataclass
class PiHandle:
    """One live pi seat: the transport process plus how to kill the real agent tree.

    For a host-spawned pi, killing the process group is enough. For a docker-exec'd pi, killing the
    host-side client leaves the in-container agent running (and spending), so `kill_argv` carries the
    out-of-band kill (`docker exec <container> pkill -KILL -u <seat>`), run before the group kill.
    """

    proc: subprocess.Popen[str]
    kill_argv: list[str] | None = None
    #: The argv the process was launched with, kept so an episode can record exactly how its seats
    #: were started. Nothing secret rides in it: seat credentials travel through `env`.
    argv: list[str] = field(default_factory=list[str])


def spawn_agent(
    argv: list[str],
    *,
    cwd: Path | None,
    env: dict[str, str],
    stderr_path: Path,
    kill_argv: list[str] | None = None,
) -> PiHandle:
    """Spawn one persistent RPC agent process from a fully composed argv.

    `env` is the FULL environment the spawned process sees — keep it minimal for host pi (see
    `runner._agent_env`); the docker path passes the client environment and forwards seat vars by name.
    stderr goes to `stderr_path` for post-mortems (host-side, never inside an agent-visible workspace).
    """
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    return PiHandle(
        proc=subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_path.open("w"),
            text=True,
            start_new_session=True,
        ),
        kill_argv=kill_argv,
        argv=list(argv),
    )


def _kill_tree(handle: PiHandle) -> None:
    """SIGKILL the agent's whole tree: the out-of-band kill first, then the host process group."""
    if handle.kill_argv is not None:
        try:
            subprocess.run(handle.kill_argv, capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        os.killpg(os.getpgid(handle.proc.pid), signal.SIGKILL)
    except OSError:
        try:
            handle.proc.kill()
        except OSError:
            pass


def run_turn(
    handle: PiHandle,
    prompt: str,
    *,
    timeout: float = DEFAULT_TURN_TIMEOUT,
) -> list[dict[str, Any]]:
    """Send one prompt, block until the terminal `agent_end`, return its messages.

    A watchdog kills this agent's tree at `timeout` (each agent is its own group/OS user, so a slow seat
    never kills its peers). Raises `TimeoutError` on watchdog fire and `RuntimeError` on a transport
    failure (stdout closed, malformed RPC JSON). The watchdog's SIGKILL can land mid-write and truncate
    an RPC line, so a parse/transport error while the timeout flag is set is classified as the timeout,
    not a crash. On any terminal failure the tree is killed immediately rather than left running (and
    spending) until episode teardown.
    """
    proc = handle.proc
    assert proc.stdin and proc.stdout
    timed_out = threading.Event()

    def _on_timeout() -> None:
        timed_out.set()
        _kill_tree(handle)

    watchdog = threading.Timer(timeout, _on_timeout)
    watchdog.start()
    try:
        try:
            proc.stdin.write(
                json.dumps(
                    {
                        "type": "prompt",
                        "message": prompt,
                        "streamingBehavior": "followUp",
                    }
                )
                + "\n"
            )
            proc.stdin.flush()
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = cast(dict[str, Any], json.loads(line))
                except (json.JSONDecodeError, TypeError) as exc:
                    if timed_out.is_set():
                        raise TimeoutError(f"pi turn exceeded {timeout}s") from exc
                    # pi mixes occasional plain-text stdout warnings into the RPC stream (probed:
                    # 'Model "claude-opus-5" not found for provider "anthropic". Using custom model
                    # id.') — skip them. A pi killed mid-line surfaces as EOF on the next read.
                    continue
                if event.get("type") == "agent_end" and not event.get("willRetry"):
                    return cast(list[dict[str, Any]], event.get("messages") or [])
                if event.get("type") == "response" and event.get("success") is False:
                    # pi rejects a prompt (missing auth, bad model, …) with a failed `response`
                    # event and then idles — fail the turn loudly instead of hanging to the watchdog.
                    raise RuntimeError(
                        f"pi rejected the prompt: {str(event.get('error'))[:300]}"
                    )
        except OSError as exc:
            if timed_out.is_set():
                raise TimeoutError(f"pi turn exceeded {timeout}s") from exc
            raise RuntimeError("pi RPC transport failed") from exc
        if timed_out.is_set():
            raise TimeoutError(f"pi turn exceeded {timeout}s")
        raise RuntimeError("pi stdout closed before a terminal agent_end")
    except (TimeoutError, RuntimeError):
        _kill_tree(handle)
        raise
    finally:
        watchdog.cancel()


def close_agents(handles: list[PiHandle]) -> None:
    """Close a whole fleet: every stdin first (all processes start exiting concurrently), then reap.

    A slow seat's exit then overlaps its peers' instead of serializing N `wait(timeout=10)` calls.
    """
    for handle in handles:
        if handle.proc.stdin:
            try:
                handle.proc.stdin.close()
            except OSError:
                pass
    for handle in handles:
        try:
            close_agent(handle)
        except OSError:
            pass


def close_agent(handle: PiHandle) -> None:
    """Close stdin and reap; escalate to a tree kill if pi won't exit."""
    if handle.proc.stdin:
        try:
            handle.proc.stdin.close()
        except OSError:
            pass
    try:
        handle.proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _kill_tree(handle)
        handle.proc.wait()


def turn_error(messages: list[dict[str, Any]]) -> str | None:
    """The first provider-error stop in a turn's messages, or None for a healthy turn.

    A failed API call (overload/429/5xx) surfaces in pi's message record as an assistant message with
    `stopReason == "error"`; pi retries a few times internally and then ends the turn WITHOUT raising, so
    a storm-hit turn otherwise masquerades as a rendered empty turn (during one Anthropic 529 storm whole
    episodes idled to the horizon as do-nothing baselines).
    """
    for m in messages:
        if m.get("role") == "assistant" and m.get("stopReason") == "error":
            return str(m.get("errorMessage") or "model call errored")[:300]
    return None


#: The block-type spellings pi has used for tool calls in RPC messages — the shape knowledge lives HERE.
_TOOL_CALL_TYPES = ("toolCall", "toolUse", "tool_use")


def had_tool_calls(messages: list[dict[str, Any]]) -> bool:
    """Whether any assistant message in the turn carried a tool call (drives `note_turn`/idle-skip)."""
    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content")
        if not isinstance(content, list):
            continue
        for block in cast("list[Any]", content):
            if (
                isinstance(block, dict)
                and cast("dict[str, Any]", block).get("type") in _TOOL_CALL_TYPES
            ):
                return True
    return False


def turn_text(messages: list[dict[str, Any]]) -> str:
    """The assistant-visible text of a turn (joined assistant message text), for logs/token estimates."""
    parts: list[str] = []
    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in cast("list[Any]", content):
                if (
                    isinstance(block, dict)
                    and cast("dict[str, Any]", block).get("type") == "text"
                ):
                    parts.append(str(cast("dict[str, Any]", block).get("text", "")))
    return "\n".join(p for p in parts if p)


def turn_est_tokens(messages: list[dict[str, Any]]) -> int:
    """Rough output-token estimate for a turn — the fair-clock convention (words x 4/3).

    Mirrors the sim's `note_generation` sizing (visible text + tool-call payloads, provider-neutral)
    so the lockstep twin reports generations on the same basis as the sim cells.
    """
    words = len(turn_text(messages).split())
    for m in messages:
        if m.get("role") != "assistant":
            continue
        content = m.get("content")
        if isinstance(content, list):
            for block in cast("list[Any]", content):
                if (
                    isinstance(block, dict)
                    and cast("dict[str, Any]", block).get("type") in _TOOL_CALL_TYPES
                ):
                    typed = cast("dict[str, Any]", block)
                    payload: Any = typed.get("input") or typed.get("arguments") or {}
                    words += len(json.dumps(payload).split())
    return max(1, round(words * 4 / 3))
