"""The real-pi seat runtime the food and trip worlds share: the bridge server, seat spawn, attestation and scans."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol, cast

from personal_assistant._paths import EVAL_ROOT

EXP_DIR = EVAL_ROOT / "environment"
DINNER_DIR = EXP_DIR


from _harness import pi_rpc  # noqa: E402


class _RuntimeContainer(Protocol):
    """Container operations shared by Docker and the Modal root-host shim."""

    def start(self) -> None: ...

    def exec_run(
        self,
        argv: list[str],
        *,
        user: str | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]: ...

    def add_seat_user(self, username: str) -> None: ...

    def write_file(
        self,
        path: str,
        text: str,
        *,
        owner: str | None = None,
        mode: str = "0644",
    ) -> None: ...

    def copy_in(self, host_path: Path, container_path: str) -> None: ...

    def copy_out(self, container_path: str, host_dir: Path) -> bool: ...

    def seat_exec_argv(
        self, *, username: str, cwd: str, env: dict[str, str]
    ) -> tuple[list[str], dict[str, str]]: ...

    def kill_user_argv(self, username: str) -> list[str]: ...

    def stop(self) -> None: ...


class TransientSeatError(RuntimeError):
    """A provider-only turn failure whose pushed events should be retried."""


#: pi 0.77.0's `ThinkingLevel` union, exactly (`@earendil-works/pi-agent-core`
#: `types.d.ts`). For the openai provider pi maps the level onto the Responses API's
#: `reasoning.effort` (`openai-responses.js`: `thinkingLevelMap[level] ?? level`), so
#: "medium" IS reasoningEffort=medium on GPT seats.
PI_THINKING_LEVELS = ("off", "minimal", "low", "medium", "high", "xhigh")


def require_provider_thinking(provider: str, thinking: str, *, runtime: str) -> str:
    """Fail-closed per-provider thinking gate.

    Anthropic seats stay thinking-off exactly (the paper's standing surface — byte-identical paths). OpenAI seats carry a real pi thinking level, which pi maps to the Responses API's `reasoning.effort`; the level is recorded verbatim in the wave manifest, sidecars, and the seats' own attestations.
    """
    if provider == "anthropic":
        if thinking != "off":
            raise ValueError(
                f"confidential {runtime} runtime requires thinking='off'; "
                f"got {thinking!r}"
            )
    elif provider in ("openai", "openrouter"):
        # (openrouter added for the standalone eval: any pi thinking level, default off.)
        if thinking not in PI_THINKING_LEVELS:
            raise ValueError(
                f"{provider} seats need a pi thinking level {PI_THINKING_LEVELS}; "
                f"got {thinking!r}"
            )
    else:
        raise ValueError(f"unknown pi provider {provider!r}")
    return thinking


#: The one context file pi loads from a seat's cwd when it is launched WITHOUT
#: `--no-context-files` (pi 0.77.0 `resource-loader.js` tries AGENTS.md first, then
#: walks the cwd's ancestors and the agent dir); every runtime here stages exactly
#: this one file per seat (`workspace_files`), and nothing else on that walk.
PROJECT_CONTEXT_FILE = "AGENTS.md"

#: The launchers' `--context-files` spellings.
CONTEXT_FILES_CHOICES = ("on", "off")


def context_files_flag(value: str) -> bool:
    """Parse a launcher's `--context-files on|off` (case/whitespace-insensitive) into the runtime's boolean; anything else raises `ValueError`."""
    normalized = value.strip().lower()
    if normalized not in CONTEXT_FILES_CHOICES:
        raise ValueError(
            f"context_files must be one of {CONTEXT_FILES_CHOICES}; got {value!r}"
        )
    return normalized == "on"


def expected_project_context(
    bridge: PiSeatBridge,
    seat: str,
    map_path: Callable[[str], Path] | None = None,
) -> dict[str, str]:
    """The one `<project_instructions>` block pi must carry for `seat` when context files are on: its cwd AGENTS.md, as path plus sha256 of the verbatim text (what the hub extension attests).

    `map_path` (MAMUBench addition for the unprivileged local runtime, where a seat's in-fiction
    `/home/<user>/...` cwd lives under the run dir) turns the in-fiction path into the host path pi
    actually reads; the default (`None`) is the research container path, unchanged.
    """
    text = bridge.workspace_files(seat).get(PROJECT_CONTEXT_FILE)
    if text is None:
        raise RuntimeError(
            f"seat {seat} stages no {PROJECT_CONTEXT_FILE}; nothing for pi to load"
        )
    path = f"{bridge.seat_cwd(seat)}/{PROJECT_CONTEXT_FILE}"
    return {
        "path": path if map_path is None else str(map_path(path)),
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def _parse_project_context(raw: object) -> list[dict[str, str]]:
    """Validate the extension's `project_context` attestation — a list of `{path, sha256}` string pairs — or raise `TypeError`."""
    if not isinstance(raw, list):
        raise TypeError("malformed project-context attestation")
    blocks: list[dict[str, str]] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise TypeError("malformed project-context attestation")
        entry = cast(dict[str, object], item)
        path, digest = entry.get("path"), entry.get("sha256")
        if not (isinstance(path, str) and isinstance(digest, str)):
            raise TypeError("malformed project-context attestation")
        blocks.append({"path": path, "sha256": digest})
    return blocks


def _provider_errored(messages: list[dict[str, Any]]) -> str | None:
    """Return a terminal provider error only when a turn produced no content."""
    if pi_rpc.had_tool_calls(messages) or pi_rpc.turn_text(messages).strip():
        return None
    for message in messages:
        if str(message.get("stopReason", "")) == "error":
            return str(message.get("errorMessage") or "provider error")[:300]
    return None


#: Status prefixes of a pi provider error no retry can clear (pi reports `<status> <provider message>`).
REFUSED_STATUSES = ("401", "402", "403", "404")


def provider_refused(error: str) -> bool:
    """A provider error that fails every retry the same way, so the seat is stopped instead of re-woken.

    The key refused (401 / 403: `authentication_error`, `permission_error`, OpenRouter's `401 User not found.`), no
    credits (402), or nothing serves the model (404: an unknown model id, or no endpoint with tool calling). Rate
    limits, overloads, timeouts and 5xx stay transient.
    """
    return (
        error.startswith(REFUSED_STATUSES)
        or "authentication_error" in error
        or "permission_error" in error
    )


class PiSeatBridge(Protocol):
    """Interface shared by food and trip worlds behind the authenticated hub."""

    ids: tuple[str, ...]
    usernames: dict[str, str]

    def tools_manifest(self) -> list[dict[str, Any]]: ...
    def workspace_files(self, seat: str) -> dict[str, str]: ...
    def seat_cwd(self, seat: str) -> str: ...
    def dispatch(self, seat: str, tool: str, args: dict[str, Any]) -> str: ...
    def log(self, kind: str, seat: str | None, payload: dict[str, Any]) -> None: ...


class BridgeServer:
    """Bearer-authenticated MCP bridge used by the pi hub extension."""

    def __init__(self, bridge: PiSeatBridge, *, host: str = "127.0.0.1") -> None:
        self.bridge = bridge
        self.host = host
        self._seat_tokens = {seat: secrets.token_urlsafe(24) for seat in bridge.ids}
        self._tokens = {token: seat for seat, token in self._seat_tokens.items()}
        self._tool_attestations: dict[str, dict[str, object]] = {}
        self._attestation_lock = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def token_for(self, seat: str) -> str:
        """Return the unguessable server-side identity token for one seat."""
        return self._seat_tokens[seat]

    def credential_markers(self) -> dict[str, str]:
        """Return labelled credentials for the persistence safety scan."""
        return {
            f"seat bearer for {seat}": token
            for seat, token in self._seat_tokens.items()
        }

    def record_tool_attestation(
        self, seat: str, attestation: dict[str, object]
    ) -> None:
        """Record the first extension-authored runtime surface for one seat."""
        with self._attestation_lock:
            prior = self._tool_attestations.setdefault(seat, attestation)
            if prior != attestation:
                raise ValueError(f"conflicting tool attestation for {seat}")

    def tool_attestations(self) -> dict[str, dict[str, object]]:
        """Return a snapshot of the extension-authored runtime surfaces."""
        with self._attestation_lock:
            return {
                seat: dict(attestation)
                for seat, attestation in self._tool_attestations.items()
            }

    @property
    def port(self) -> int:
        """Return the ephemeral port after `start`."""
        assert self._httpd is not None
        return int(self._httpd.server_address[1])

    def start(self) -> None:
        """Start the local tool bridge."""
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass

            def _reply(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802
                if self.path not in {"/agent/call", "/runtime/attest"}:
                    self._reply(404, {"text": "unknown endpoint"})
                    return
                seat = server._tokens.get(self.headers.get("X-Seat-Token", ""))
                if seat is None:
                    self._reply(403, {"text": "invalid session token"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    payload_raw = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(payload_raw, dict):
                        raise TypeError("payload must be an object")
                    payload = cast(dict[str, Any], payload_raw)
                    if self.path == "/runtime/attest":
                        active_tools = payload.get("active_tools")
                        all_tools = payload.get("all_tools")
                        thinking = payload.get("thinking")
                        if not isinstance(active_tools, list) or not isinstance(
                            all_tools, list
                        ):
                            raise TypeError("malformed tool attestation")
                        active_items = cast(list[object], active_tools)
                        all_items = cast(list[object], all_tools)
                        if not (
                            all(isinstance(name, str) for name in active_items)
                            and all(isinstance(name, str) for name in all_items)
                            and isinstance(thinking, str)
                        ):
                            raise TypeError("malformed tool attestation")
                        active_tool_names = cast(list[str], active_items)
                        all_tool_names = cast(list[str], all_items)
                        attestation: dict[str, object] = {
                            "active_tools": list(active_tool_names),
                            "all_tools": list(all_tool_names),
                            "thinking": thinking,
                        }
                        # Optional so an older hub.ts still attests; the preflight
                        # then fails closed when context files are expected.
                        if "project_context" in payload:
                            attestation["project_context"] = _parse_project_context(
                                payload["project_context"]
                            )
                        server.record_tool_attestation(seat, attestation)
                        self._reply(200, {"text": "attested"})
                        return
                    command = str(payload.get("command", ""))
                    args_raw = payload.get("args")
                    args = (
                        cast(dict[str, Any], args_raw)
                        if isinstance(args_raw, dict)
                        else {}
                    )
                    text = server.bridge.dispatch(seat, command, args)
                except (TypeError, ValueError, json.JSONDecodeError):
                    self._reply(400, {"text": "malformed request"})
                    return
                except Exception as exc:  # noqa: BLE001 - tool calls must terminate
                    server.bridge.log(
                        "bridge_error",
                        seat,
                        {"error": f"{type(exc).__name__}: {str(exc)[:240]}"},
                    )
                    self._reply(500, {"text": "internal tool error"})
                    return
                self._reply(200, {"text": text})

        self._httpd = ThreadingHTTPServer((self.host, 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the bridge and join its serving thread."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)


def _make_private_dir(path: Path) -> None:
    """Create a host artifact directory and enforce owner-only access."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def _make_private_tree(path: Path) -> None:
    """Make every real directory/file in an artifact tree owner-only."""
    if not path.exists() or path.is_symlink():
        return
    for root, dirnames, filenames in os.walk(path):
        root_path = Path(root)
        root_path.chmod(0o700)
        for dirname in dirnames:
            child = root_path / dirname
            if not child.is_symlink():
                child.chmod(0o700)
        for filename in filenames:
            child = root_path / filename
            if not child.is_symlink():
                child.chmod(0o600)


def _private_file(path: Path) -> None:
    """Create a host artifact file with owner-only read/write access."""
    _make_private_dir(path.parent)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)


def _setup_container(
    container: _RuntimeContainer,
    bridge: PiSeatBridge,
    *,
    agent_dir: Path,
    provider: str,
    api_key: str,
) -> None:
    """Create isolated seat users, runbooks, tool extension, and pi auth."""
    for seat in bridge.ids:
        container.add_seat_user(bridge.usernames[seat])

    for seat in bridge.ids:
        username = bridge.usernames[seat]
        home = f"/home/{username}"
        tmpdir = f"{home}/tmp"
        container.exec_run(
            ["mkdir", "-p", bridge.seat_cwd(seat), f"{home}/.pi/sessions", tmpdir],
            user=username,
        )
        container.copy_in(agent_dir, f"{home}/.pi/agent")
        container.write_file(
            f"{home}/.pi/agent/auth.json",
            pi_rpc.auth_json(provider, api_key),
            mode="0600",
        )
        container.exec_run(["chown", "-R", username, f"{home}/.pi"])
        for relative, text in bridge.workspace_files(seat).items():
            container.write_file(
                f"{bridge.seat_cwd(seat)}/{relative}",
                text,
                owner=username,
                mode="0600",
            )
        container.exec_run(
            [
                "chmod",
                "0700",
                home,
                f"{home}/.pi",
                f"{home}/.pi/agent",
                f"{home}/.pi/sessions",
                bridge.seat_cwd(seat),
                tmpdir,
            ]
        )


def _preflight_peer_home_isolation(
    container: _RuntimeContainer, bridge: PiSeatBridge
) -> int:
    """Require every seat to lack read, traverse, and write access to peer homes."""
    checks = 0
    for seat in bridge.ids:
        username = bridge.usernames[seat]
        for peer in bridge.ids:
            if peer == seat:
                continue
            peer_home = f"/home/{bridge.usernames[peer]}"
            result = container.exec_run(
                [
                    "sh",
                    "-c",
                    '! test -r "$1" && ! test -x "$1" && ! test -w "$1"',
                    "peer-home-preflight",
                    peer_home,
                ],
                user=username,
                check=False,
            )
            checks += 1
            if result.returncode != 0:
                raise RuntimeError(
                    "seat isolation preflight failed: "
                    f"{seat} can access peer home {peer_home}"
                )
    return checks


def _preflight_host_artifact_isolation(
    container: _RuntimeContainer,
    bridge: PiSeatBridge,
    *,
    protected_roots: tuple[Path, ...],
    seat_artifact_dirs: Mapping[str, Path],
) -> int:
    """Require seat UIDs to have no access to host roots or peer artifacts."""
    checks = 0
    for seat in bridge.ids:
        username = bridge.usernames[seat]
        targets = [*protected_roots]
        targets.extend(
            path for peer, path in seat_artifact_dirs.items() if peer != seat
        )
        for target in targets:
            result = container.exec_run(
                [
                    "sh",
                    "-c",
                    '! test -r "$1" && ! test -x "$1" && ! test -w "$1"',
                    "artifact-preflight",
                    str(target),
                ],
                user=username,
                check=False,
            )
            checks += 1
            if result.returncode != 0:
                raise RuntimeError(
                    "artifact isolation preflight failed: "
                    f"{seat} can access protected path {target}"
                )
    return checks


def _preflight_peer_process_environ(
    container: _RuntimeContainer,
    bridge: PiSeatBridge,
    handles: Mapping[str, pi_rpc.PiHandle],
) -> int:
    """Require each root-host pi PID to belong to its seat and hide peer envs."""
    for seat, handle in handles.items():
        pid = str(handle.proc.pid)
        username = bridge.usernames[seat]
        result = container.exec_run(
            [
                "sh",
                "-c",
                'expected="$(id -u "$2")"; i=0; '
                'while test "$i" -lt 100; do '
                'actual="$(stat -c %u "/proc/$1" 2>/dev/null || true)"; '
                'test "$actual" = "$expected" && exit 0; '
                'kill -0 "$1" 2>/dev/null || exit 2; '
                "i=$((i + 1)); sleep 0.02; done; exit 1",
                "proc-owner-preflight",
                pid,
                username,
            ],
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "process isolation preflight failed: "
                f"pi pid {pid} did not settle to seat {seat} uid"
            )

    checks = 0
    for seat in bridge.ids:
        username = bridge.usernames[seat]
        for peer, handle in handles.items():
            if peer == seat:
                continue
            pid = str(handle.proc.pid)
            result = container.exec_run(
                [
                    "sh",
                    "-c",
                    '! test -r "/proc/$1/environ"',
                    "proc-environ-preflight",
                    pid,
                ],
                user=username,
                check=False,
            )
            checks += 1
            if result.returncode != 0:
                raise RuntimeError(
                    "process isolation preflight failed: "
                    f"{seat} can read peer {peer} process environment"
                )
    return checks


def _scan_artifacts_for_credentials(root: Path, credentials: Mapping[str, str]) -> int:
    """Fail if a bearer or provider key was persisted anywhere under `root`."""
    markers = {label: value.encode() for label, value in credentials.items() if value}
    scanned = 0
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in [*dirnames, *filenames]:
            path = current_path / name
            if path.is_symlink():
                try:
                    payload = os.readlink(path).encode()
                except OSError as exc:
                    raise RuntimeError(
                        f"credential persistence scan could not read symlink {path}"
                    ) from exc
            elif path.is_file():
                try:
                    payload = path.read_bytes()
                except OSError as exc:
                    raise RuntimeError(
                        f"credential persistence scan could not read file {path}"
                    ) from exc
            else:
                continue
            scanned += 1
            for label, marker in markers.items():
                if marker in payload:
                    relative = path.relative_to(root)
                    raise RuntimeError(
                        "credential persistence scan failed: "
                        f"{label} found in {relative}"
                    )
    return scanned


def _spawn_seat(
    container: _RuntimeContainer,
    bridge: PiSeatBridge,
    seat: str,
    *,
    provider: str,
    model: str,
    thinking: str,
    server_url: str,
    seat_token: str,
    seat_dir: Path,
    run_dir: Path,
    context_files: bool = False,
) -> pi_rpc.PiHandle:
    """Spawn one persistent pi process as its isolated seat user.

    `context_files=False` (the run-of-record launch) passes pi `--no-context-files`; `True` omits it so pi loads the seat's cwd `AGENTS.md` into its system prompt (see `pi_rpc.rpc_argv`).
    """
    username = bridge.usernames[seat]
    home = f"/home/{username}"
    tool_names = ",".join(str(row["name"]) for row in bridge.tools_manifest())
    env = {
        "PA_HUB_SERVER": server_url,
        "PA_HUB_TOKEN": seat_token,
        "PI_OFFLINE": "1",
        "PI_TELEMETRY": "0",
        "GIT_CEILING_DIRECTORIES": home,
        "PI_CODING_AGENT_DIR": f"{home}/.pi/agent",
        "HOME": home,
        "TMPDIR": f"{home}/tmp",
    }
    prefix, client_env = container.seat_exec_argv(
        username=username,
        cwd=bridge.seat_cwd(seat),
        env=env,
    )
    return pi_rpc.spawn_agent(
        [
            *prefix,
            "pi",
            *pi_rpc.rpc_argv(
                provider=provider,
                model=model,
                session_dir=Path(home) / ".pi" / "sessions",
                context_files=context_files,
            ),
            "--thinking",
            thinking,
            "--no-extensions",
            "--extension",
            f"{home}/.pi/agent/extensions/hub.ts",
            "--no-builtin-tools",
            "--tools",
            tool_names,
        ],
        cwd=None,
        env=client_env,
        stderr_path=seat_dir / "stderr.log",
        kill_argv=container.kill_user_argv(username),
    )


def _preflight_tool_surfaces(
    server: BridgeServer,
    bridge: PiSeatBridge,
    *,
    timeout: float = 15.0,
    expected_thinking: str = "off",
    expected_context_files: bool = False,
    map_path: Callable[[str], Path] | None = None,
) -> int:
    """Require every live pi seat to attest its exact tools, thinking mode and context files.

    `expected_thinking` defaults to the paper's no-thinking surface; openai (GPT-pilot) runtimes pass their configured level so a seat that silently fell back to another mode still fails closed.

    `expected_context_files=True` requires each seat's attested `project_context` to be exactly its staged AGENTS.md (`expected_project_context`, with `map_path` translating the in-fiction path on the local runtime); `False` requires that no project-context block reached the prompt. A seat whose extension attests no `project_context` at all passes only the `False` case (an earlier hub.ts never reported it).
    """
    deadline = time.monotonic() + timeout
    attestations = server.tool_attestations()
    while set(attestations) != set(bridge.ids) and time.monotonic() < deadline:
        time.sleep(0.05)
        attestations = server.tool_attestations()

    missing = set(bridge.ids) - set(attestations)
    if missing:
        raise RuntimeError(
            "pi tool-surface preflight timed out for seats "
            + ", ".join(sorted(missing))
        )

    expected = {str(row["name"]) for row in bridge.tools_manifest()}
    forbidden = {"bash", "read", "write", "edit", "grep", "find", "ls"}
    for seat in bridge.ids:
        attestation = attestations[seat]
        active_raw = attestation.get("active_tools")
        all_raw = attestation.get("all_tools")
        thinking = attestation.get("thinking")
        if not isinstance(active_raw, list):
            raise RuntimeError(f"invalid active-tool attestation for {seat}")
        if not isinstance(all_raw, list):
            raise RuntimeError(f"invalid configured-tool attestation for {seat}")
        active_items = cast(list[object], active_raw)
        configured_items = cast(list[object], all_raw)
        if not all(isinstance(name, str) for name in active_items):
            raise RuntimeError(f"invalid active-tool attestation for {seat}")
        if not all(isinstance(name, str) for name in configured_items):
            raise RuntimeError(f"invalid configured-tool attestation for {seat}")
        active = set(cast(list[str], active_items))
        configured = set(cast(list[str], configured_items))
        if active != expected:
            raise RuntimeError(
                f"pi tool-surface preflight failed for {seat}: "
                f"active={sorted(active)!r}, expected={sorted(expected)!r}"
            )
        if forbidden & active:
            raise RuntimeError(
                f"pi native tools active for {seat}: {sorted(forbidden & active)!r}"
            )
        if not expected <= configured:
            raise RuntimeError(
                f"pi bridge tools were not registered for {seat}: "
                f"missing={sorted(expected - configured)!r}"
            )
        if thinking != expected_thinking:
            raise RuntimeError(
                f"pi thinking preflight failed for {seat}: found {thinking!r}, "
                f"expected {expected_thinking!r}"
            )
        blocks = attestation.get("project_context")
        if expected_context_files:
            expected_block = expected_project_context(bridge, seat, map_path)
            if blocks != [expected_block]:
                raise RuntimeError(
                    f"pi context-files preflight failed for {seat}: the system "
                    f"prompt carries {blocks!r}, expected exactly {[expected_block]!r}"
                )
        elif blocks:
            raise RuntimeError(
                f"pi context-files preflight failed for {seat}: the run is "
                f"context_files=off but the system prompt carries {blocks!r}"
            )
    return len(attestations)


def _remove_seat_auth(container: _RuntimeContainer, bridge: PiSeatBridge) -> None:
    """Remove provider credentials after seats stop, before any artifacts are copied."""
    container.exec_run(
        [
            "rm",
            "-f",
            *(
                f"/home/{bridge.usernames[seat]}/.pi/agent/auth.json"
                for seat in bridge.ids
            ),
        ]
    )


def _copy_seat_artifacts(
    container: _RuntimeContainer,
    bridge: PiSeatBridge,
    run_dir: Path,
) -> None:
    """Copy pi sessions and non-secret workspaces out before container removal."""
    for seat in bridge.ids:
        username = bridge.usernames[seat]
        seat_dir = run_dir / "agents" / seat
        container.copy_out(f"/home/{username}/.pi/sessions", seat_dir)
        cwd = bridge.seat_cwd(seat)
        if container.copy_out(cwd, seat_dir):
            copied = seat_dir / Path(cwd).name
            if copied.is_dir() and not (seat_dir / "ws").exists():
                copied.rename(seat_dir / "ws")
        _make_private_tree(seat_dir)
