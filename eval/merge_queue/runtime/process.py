"""Persistent, hermetic-enough pi RPC process control for live episodes.

This is a four-agent adaptation of the process layer of an earlier harness in the authors'
research code. Each process owns a
workspace, HOME, session directory, actor credential, and process group. The
agent still needs an Anthropic key to generate; GitHub credentials and other
ambient provider secrets are deliberately omitted.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO, cast


@dataclass
class PiProcess:
    """One persistent pi RPC process and its stable identity."""

    actor: str
    workspace: Path
    state_dir: Path
    process: subprocess.Popen[str]
    stderr: TextIO


class PiProcessError(RuntimeError):
    """A contained transport or lifecycle failure in one pi process."""


def validate_pi_runtime(*, pi_bin: str = "pi") -> None:
    """Require the live harness's reviewed Node and pi versions."""
    try:
        node_result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        pi_result = subprocess.run(
            [pi_bin, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise RuntimeError("live episodes require Node 22+ and pi 0.77.0") from exc
    # pi prints `--version` to stderr with an empty stdout (pi 0.77 and 0.78), so
    # read whichever stream carried the version rather than assuming stdout.
    node = (node_result.stdout or node_result.stderr).strip()
    pi = (pi_result.stdout or pi_result.stderr).strip()
    try:
        node_major = int(node.removeprefix("v").split(".", maxsplit=1)[0])
    except ValueError as exc:
        raise RuntimeError(f"could not parse Node version {node!r}") from exc
    if node_major < 22:
        raise RuntimeError(f"Node 22+ is required; found {node!r}")
    if not pi:
        raise RuntimeError(f"could not parse pi version {pi!r}")
    pi_version = pi.split()[-1].removeprefix("v")
    if pi_version != "0.77.0":
        raise RuntimeError(f"pi 0.77.0 is required; found {pi!r}")


def _agent_env(
    *,
    workspace: Path,
    home: Path,
    node_root: Path,
    shim_dir: Path,
) -> dict[str, str]:
    """Return the deliberately small environment exposed to pi and its shell.

    The provider credential is deliberately absent: it lives in pi's auth file
    (`~/.pi/agent/auth.json`, written by `spawn_pi`), not the process env, so an
    in-episode `env` never surfaces the live vendor key that a pi tool subshell
    would otherwise inherit. `GH_HOST` names the in-fiction host
    (`github.internal`), matching the `gh` hosts.yml, rather than the loopback
    address the shim actually talks to. `PI_OFFLINE`/`PI_TELEMETRY` are the only
    `PI_*` vars pi requires and are what a real offline pi session carries.
    """
    env = {
        "GIT_CEILING_DIRECTORIES": str(node_root),
        "HOME": str(home),
        "PATH": f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "GH_HOST": "github.internal",
        "PI_OFFLINE": "1",
        "PI_TELEMETRY": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    # A single-PR seat's workspace is its clone, so `workspace/src` is the
    # importable package root and is baked here. A steward's workspace is the
    # parent `workspaces/` dir holding one clone per PR, with no top-level
    # `src`; baking `workspaces/src` there is a dangling path that broke pytest
    # in every steward episode. The steward's per-clone src is resolved at
    # pytest invocation by the shim (see `driver._install_pytest_shim`) from the
    # clone it has cd'd into, never as a spawn-time value here.
    src = workspace / "src"
    if src.is_dir():
        env["PYTHONPATH"] = str(src)
    for name in (
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    ):
        if value := os.environ.get(name):
            env[name] = value
    return env


def _write_pi_auth_file(home: Path, *, provider: str, api_key: str) -> None:
    """Store the provider credential in pi's auth file instead of the env.

    pi resolves API keys from `~/.pi/agent/auth.json` (taking priority over
    environment variables), keyed by provider id, so the live key never has to
    sit in the environment a pi tool subshell inherits — closing the `env`/procfs
    key leak. Written `0600`, mirroring how pi's own `/login`
    persists it.
    """
    auth_dir = home / ".pi" / "agent"
    auth_dir.mkdir(parents=True, exist_ok=True)
    auth_path = auth_dir / "auth.json"
    auth_path.write_text(
        json.dumps({provider: {"type": "api_key", "key": api_key}}) + "\n",
        encoding="utf-8",
    )
    auth_path.chmod(0o600)


def spawn_pi(
    *,
    actor: str,
    workspace: Path,
    state_dir: Path,
    node_root: Path,
    shim_dir: Path,
    api_key: str,
    model: str = "claude-sonnet-5",
    pi_bin: str = "pi",
    provider: str = "anthropic",
    api_key_var: str = "ANTHROPIC_API_KEY",
    context_files: bool = False,
    thinking: str | None = None,
) -> PiProcess:
    """Spawn one standalone pi 0.77 RPC process in its own process group."""
    home = state_dir / "home"
    sessions = state_dir / "sessions"
    home.mkdir(parents=True, exist_ok=True)
    sessions.mkdir(parents=True, exist_ok=True)
    _write_pi_auth_file(home, provider=provider, api_key=api_key)
    stderr = (state_dir / "stderr.log").open("w")
    argv = [
        pi_bin,
        "--mode",
        "rpc",
        "--provider",
        provider,
        "--model",
        model,
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--session-dir",
        str(sessions),
    ]
    if thinking is not None:
        # pi's own default is `medium`; the earliest episodes ran at that
        # default, so a run that sets this is NOT comparable to those.
        argv.extend(["--thinking", thinking])
    if not context_files:
        argv.insert(argv.index("--no-extensions"), "--no-context-files")
    try:
        process = subprocess.Popen(
            argv,
            cwd=workspace,
            env=_agent_env(
                workspace=workspace,
                home=home,
                node_root=node_root,
                shim_dir=shim_dir,
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            text=True,
            start_new_session=True,
        )
    except BaseException:
        stderr.close()
        raise
    return PiProcess(
        actor=actor,
        workspace=workspace,
        state_dir=state_dir,
        process=process,
        stderr=stderr,
    )


def _kill_tree(process: subprocess.Popen[str]) -> None:
    try:
        # Every pi leader is spawned with `start_new_session=True`, so its PID
        # remains the process-group id even if the leader has already exited.
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def run_turn(
    target: PiProcess,
    prompt: str,
    *,
    timeout: float = 1800.0,
) -> list[dict[str, Any]]:
    """Run one complete pi turn and return its recorded RPC messages.

    The default is the uniform turn timeout: a single
    per-turn watchdog, never varied per model, so retained episodes are not a
    differentially censored sample across the leaderboard and arms.
    """
    process = target.process
    if process.stdin is None or process.stdout is None:
        raise RuntimeError(f"pi process for {target.actor} has no RPC pipes")
    timed_out = threading.Event()

    def on_timeout() -> None:
        timed_out.set()
        _kill_tree(process)

    watchdog = threading.Timer(timeout, on_timeout)
    watchdog.start()
    try:
        try:
            process.stdin.write(
                json.dumps(
                    {
                        "type": "prompt",
                        "message": prompt,
                        "streamingBehavior": "followUp",
                    }
                )
                + "\n"
            )
            process.stdin.flush()
            for line in process.stdout:
                if not (text := line.strip()):
                    continue
                try:
                    event = cast(dict[str, Any], json.loads(text))
                except (json.JSONDecodeError, TypeError) as exc:
                    # The watchdog's SIGKILL can land mid-write and truncate an
                    # RPC line (pi streams events all turn; agent_end is one
                    # large line). Classify by cause: a set flag means this is
                    # the timeout, not a crash — the seat keeps its recoverable
                    # missed-wake path instead of being retired.
                    if timed_out.is_set():
                        raise TimeoutError(
                            f"pi turn for {target.actor} exceeded {timeout}s"
                        ) from exc
                    raise PiProcessError(
                        f"pi process for {target.actor} emitted malformed RPC JSON"
                    ) from exc
                if event.get("type") == "agent_end" and not event.get("willRetry"):
                    return cast(list[dict[str, Any]], event.get("messages") or [])
        except OSError as exc:
            if timed_out.is_set():
                raise TimeoutError(
                    f"pi turn for {target.actor} exceeded {timeout}s"
                ) from exc
            raise PiProcessError(f"pi RPC transport failed for {target.actor}") from exc
        if timed_out.is_set():
            raise TimeoutError(f"pi turn for {target.actor} exceeded {timeout}s")
        raise PiProcessError(f"pi process for {target.actor} exited before agent_end")
    except (PiProcessError, TimeoutError):
        # A terminal RPC failure removes this agent from the driver. Kill its
        # dedicated group immediately instead of leaving a credential-bearing
        # process alive until episode teardown.
        _kill_tree(process)
        raise
    finally:
        watchdog.cancel()


def close_pi(target: PiProcess) -> None:
    """Close a pi process, killing its whole process group on a slow exit."""
    process = target.process
    if process.stdin is not None:
        try:
            process.stdin.close()
        except OSError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        _kill_tree(process)
        process.wait()
    else:
        # A well-behaved leader can exit while a shell/background child
        # survives. Always clear the dedicated process group on teardown.
        _kill_tree(process)
    target.stderr.close()
