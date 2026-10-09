"""Real-pi runtime adapter for the confidential delivery-cart (venue) cells.

Built on `pi_runtime` like `trip_runtime.TripRuntime` — the same bearer-authenticated `BridgeServer`,
per-seat OS users, fail-closed tool/thinking attestation, isolation preflights, and credential scan,
all reused by import — but the bridge dispatches into the real food world core
(`world_server.DinnerWorldCore`) in-process: the exact `FoodOrderRouter` dd dispatch,
memory tool (server-side seat identity), push-DM queues, stale-preview checkout guard, and
ledger the docker world server runs, with no docker daemon and no HTTP MCP layer.

The tool manifest is the §5.2 surface exactly as the docker world exposes it
(`worlds.tools_manifest(cell)`); on Modal the driver computes it host-side and ships it in
(the docker config.json pattern), because the manifest constructors sit behind the harness
import chain that the packaged image deliberately does not carry.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from personal_assistant._paths import EVAL_ROOT, PA_HARNESS_DIR

EXP_DIR = EVAL_ROOT / "environment"
DINNER_DIR = EXP_DIR


from _harness import pi_rpc  # noqa: E402
from _harness.docker_tier import (  # noqa: E402
    ensure_image,
    validate_image,
)
from personal_assistant.environment.pi_runtime import (  # noqa: E402
    BridgeServer,
    PiSeatBridge,
    TransientSeatError,
    _copy_seat_artifacts,  # pyright: ignore[reportPrivateUsage]
    _make_private_dir,  # pyright: ignore[reportPrivateUsage]
    _make_private_tree,  # pyright: ignore[reportPrivateUsage]
    _preflight_host_artifact_isolation,  # pyright: ignore[reportPrivateUsage]
    _preflight_peer_home_isolation,  # pyright: ignore[reportPrivateUsage]
    _preflight_peer_process_environ,  # pyright: ignore[reportPrivateUsage]
    _preflight_tool_surfaces,  # pyright: ignore[reportPrivateUsage]
    _provider_errored,  # pyright: ignore[reportPrivateUsage]
    _remove_seat_auth,  # pyright: ignore[reportPrivateUsage]
    _RuntimeContainer,  # pyright: ignore[reportPrivateUsage]
    _scan_artifacts_for_credentials,  # pyright: ignore[reportPrivateUsage]
    _setup_container,  # pyright: ignore[reportPrivateUsage]
    _spawn_seat,  # pyright: ignore[reportPrivateUsage]
    provider_refused,
    require_provider_thinking,
)
from personal_assistant.environment import live_docker  # noqa: E402
from personal_assistant.environment.world_server import DinnerWorldCore  # noqa: E402
from personal_assistant.environment.worlds import (
    CELLS,
    Cell,
    seat_agents_md,
    tools_manifest,
)  # noqa: E402

__all__ = ["ConfidentialFoodBridge", "FoodRuntime", "TransientSeatError"]


def _hub_tool_rows(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert MCP-shaped manifest rows to the hub extension's contract.

    `worlds.tools_manifest` emits `inputSchema` (the docker MCP path's key, mapped
    by mcp-bridge.ts); `hub.ts` registers `tool.parameters`. Shipping the raw rows
    registers every tool with an undefined schema, so the conversion the MCP
    bridge performs happens here at write time instead.
    """
    rows: list[dict[str, Any]] = []
    for row in manifest:
        parameters = row.get("parameters", row.get("inputSchema"))
        if not isinstance(parameters, dict) or not parameters:
            raise RuntimeError(f"tool {row.get('name')!r} has no parameter schema")
        rows.append(
            {
                "name": row["name"],
                "description": row["description"],
                "parameters": parameters,
            }
        )
    return rows


class ConfidentialFoodBridge:
    """Thread-safe in-process bridge over the transport-free dinner world core.

    Structurally satisfies the surface `pi_runtime`'s generic helpers consume
    (`ids`/`usernames`/`seat_cwd`/`workspace_files`/`tools_manifest`/`dispatch`/`log`);
    those helpers are annotated against `PiSeatBridge`, so call sites cast — the
    contract is structural, not nominal.
    """

    def __init__(
        self,
        cell_name: str,
        epoch: int,
        world_dir: Path,
        *,
        git_sha: str = "unknown",
        manifest: list[dict[str, Any]] | None = None,
    ) -> None:
        cell = CELLS[cell_name]
        if not (cell.simultaneous and cell_name.startswith("conf_")):
            raise ValueError(
                f"cell {cell_name!r} is not a confidential simultaneous cell"
            )
        _make_private_dir(world_dir)
        self.core = DinnerWorldCore(cell_name, epoch, world_dir, git_sha=git_sha)
        self.cell: Cell = self.core.cell
        self.ids: tuple[str, ...] = self.core.ids
        self.usernames: dict[str, str] = dict(self.core.usernames)
        self._manifest: list[dict[str, Any]] = (
            [dict(row) for row in manifest]
            if manifest is not None
            else tools_manifest(self.cell)
        )
        self._tool_names = {str(row["name"]) for row in self._manifest}

    def tools_manifest(self) -> list[dict[str, Any]]:
        """Return the exact tool list registered as first-class pi tools."""
        return self._manifest

    def workspace_files(self, seat: str) -> dict[str, str]:
        """Return the seat's on-disk runbook; private notes stay behind the memory tool."""
        return {"AGENTS.md": seat_agents_md(self.cell, seat, self.core.diners)}

    def seat_cwd(self, seat: str) -> str:
        """Return the in-fiction workspace path used inside the runtime container."""
        return f"/home/{self.usernames[seat]}/dinner"

    def dispatch(self, seat: str, tool: str, args: dict[str, Any]) -> str:
        """Dispatch one authenticated tool call into the food world core."""
        if tool not in self._tool_names:
            result = f"error: '{tool}' is not available on this console."
            self.core.log(
                "tool_call",
                seat,
                {"tool": tool, "args": args, "result_head": result[:200]},
            )
            return result
        return self.core.dispatch(seat, tool, args)

    def log(self, kind: str, seat: str | None, payload: dict[str, Any]) -> None:
        """Append one harness event to the world's authoritative JSONL ledger."""
        self.core.log(kind, seat, payload)


def _as_seat_bridge(bridge: ConfidentialFoodBridge) -> PiSeatBridge:
    """Present the food bridge to `pi_runtime`'s structurally generic helpers."""
    return cast(PiSeatBridge, bridge)


class FoodRuntime:
    """One real-pi food episode exposing the food relay's push-runtime contract."""

    def __init__(
        self,
        cell_name: str,
        epoch: int,
        run_dir: Path,
        *,
        model: str,
        provider: str,
        api_key: str,
        turn_timeout: float,
        thinking: str,
        root_host: bool,
        protected_roots: tuple[Path, ...],
        manifest: list[dict[str, Any]] | None = None,
        git_sha: str = "unknown",
        context_files: bool = False,
        on_bridge: Callable[[ConfidentialFoodBridge], None] | None = None,
    ) -> None:
        if cell_name not in CELLS:
            raise ValueError(f"unknown cell {cell_name!r}")
        self.cell_name = cell_name
        #: Called with the live `ConfidentialFoodBridge` right after it is built and
        #: before any seat starts (the mitigation arms' fail-closed flag / manifest attestation).
        self.on_bridge = on_bridge
        self.epoch = epoch
        self.run_dir = run_dir.resolve()
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.turn_timeout = turn_timeout
        self.thinking = require_provider_thinking(provider, thinking, runtime="food")
        self.root_host = root_host
        self.protected_roots = tuple(path.resolve() for path in protected_roots)
        self.context_files = context_files
        #: Per seat, the exact argv it was launched with (recorded in a context-files sidecar).
        self.pi_argv: dict[str, list[str]] = {}
        #: Release-only: extra completion-sidecar fields this runtime records (the unprivileged local
        #: runtime's `host_seat_cwd`); empty on the paper's docker / root-host paths, so their
        #: sidecars stay byte-identical.
        self.sidecar_notes: dict[str, object] = {}
        self.manifest = manifest
        self.git_sha = git_sha
        self.record_turn_text = True
        self.crashed: dict[str, str] = {}
        self.bridge: ConfidentialFoodBridge | None = None
        self.server: BridgeServer | None = None
        self.container: _RuntimeContainer | None = None
        self.handles: dict[str, pi_rpc.PiHandle] = {}
        self.ids: tuple[str, ...] = ()
        self._started = False
        self._stopped = False

    def ensure_started(self) -> None:
        """Start the food bridge, isolated OS users, and one persistent pi per seat."""
        if self._started:
            return
        try:
            if self.run_dir.exists():
                shutil.rmtree(self.run_dir)
            for protected_root in self.protected_roots:
                _make_private_dir(protected_root)
            _make_private_dir(self.run_dir)
            bridge = ConfidentialFoodBridge(
                self.cell_name,
                self.epoch,
                self.run_dir / "world",
                git_sha=self.git_sha,
                manifest=self.manifest,
            )
            if self.on_bridge is not None:
                self.on_bridge(bridge)
            self.bridge = bridge
            self.ids = bridge.ids
            if self.root_host:
                container: _RuntimeContainer = live_docker.RootHostShim(self.run_dir)
                server_host = "127.0.0.1"
                episode_boundary = "modal_container"
            else:
                image = ensure_image()
                validate_image(image)
                container = live_docker.PaEpisodeContainer(image, self.run_dir)
                server_host = live_docker.server_bind_host()
                episode_boundary = "docker_container"
            server = BridgeServer(_as_seat_bridge(bridge), host=server_host)
            self.server = server
            server.start()
            self.container = container
            container.start()
            agent_dir = self.run_dir / "agent_dir"
            shutil.copytree(PA_HARNESS_DIR / "agent_dir", agent_dir)
            (agent_dir / "tools.json").write_text(
                json.dumps(_hub_tool_rows(bridge.tools_manifest()), indent=2),
                encoding="utf-8",
            )
            _make_private_tree(agent_dir)
            _setup_container(
                container,
                _as_seat_bridge(bridge),
                agent_dir=agent_dir,
                provider=self.provider,
                api_key=self.api_key,
            )
            peer_home_checks = _preflight_peer_home_isolation(
                container, _as_seat_bridge(bridge)
            )
            seat_artifact_dirs: dict[str, Path] = {}
            for seat in bridge.ids:
                seat_dir = self.run_dir / "agents" / seat
                _make_private_dir(seat_dir)
                seat_artifact_dirs[seat] = seat_dir
            artifact_checks = _preflight_host_artifact_isolation(
                container,
                _as_seat_bridge(bridge),
                protected_roots=(*self.protected_roots, self.run_dir),
                seat_artifact_dirs=seat_artifact_dirs,
            )
            for seat in bridge.ids:
                seat_dir = seat_artifact_dirs[seat]
                self.handles[seat] = _spawn_seat(
                    container,
                    _as_seat_bridge(bridge),
                    seat,
                    provider=self.provider,
                    model=self.model,
                    thinking=self.thinking,
                    context_files=self.context_files,
                    server_url=(
                        f"http://127.0.0.1:{server.port}"
                        if self.root_host
                        else live_docker.controller_url(server.port)
                    ),
                    seat_token=server.token_for(seat),
                    seat_dir=seat_dir,
                    run_dir=self.run_dir,
                )
            self.pi_argv = {
                seat: list(handle.argv) for seat, handle in self.handles.items()
            }
            process_env_checks = (
                _preflight_peer_process_environ(
                    container,
                    _as_seat_bridge(bridge),
                    self.handles,
                )
                if self.root_host
                else None
            )
            tool_surface_checks = _preflight_tool_surfaces(
                server,
                _as_seat_bridge(bridge),
                expected_thinking=self.thinking,
                expected_context_files=self.context_files,
            )
            self._started = True
            bridge.log(
                "runtime_started",
                None,
                {
                    "cell": self.cell_name,
                    "thinking": self.thinking,
                    # Recorded only when on, so a run-of-record ledger stays byte-identical.
                    **({"context_files": True} if self.context_files else {}),
                    "tool_names": [row["name"] for row in bridge.tools_manifest()],
                    "isolation": {
                        "episode_boundary": episode_boundary,
                        "seat_boundary": "linux_dac_per_user",
                        "peer_home_preflight": "passed",
                        "peer_home_pairs_checked": peer_home_checks,
                        "host_artifact_preflight": "passed",
                        "host_artifact_paths_checked": artifact_checks,
                        "peer_process_environ_preflight": (
                            "passed"
                            if process_env_checks is not None
                            else "not_applicable"
                        ),
                        "peer_process_environ_pairs_checked": process_env_checks,
                        "home_mode": "0700",
                        "tmpdir": "per_seat_home",
                        "tool_surface_preflight": "passed",
                        "tool_surface_seats_checked": tool_surface_checks,
                        "tmpdir_mode": "0700",
                        "native_pi_tools": "disabled",
                    },
                },
            )
        except Exception:
            self.stop()
            raise

    @property
    def _core(self) -> DinnerWorldCore:
        assert self.bridge is not None
        return self.bridge.core

    def turn(self, seat: str, prompt: str) -> list[dict[str, Any]]:
        """Run one pushed pi turn and record its visible response."""
        assert self.bridge is not None
        try:
            messages = pi_rpc.run_turn(
                self.handles[seat], prompt, timeout=self.turn_timeout
            )
        except (RuntimeError, TimeoutError) as exc:
            self.crashed[seat] = f"{type(exc).__name__}: {exc}"
            self.bridge.log("seat_crashed", seat, {"error": str(exc)[:300]})
            raise
        provider_error = _provider_errored(messages)
        if provider_error is not None:
            self.bridge.log("provider_error", seat, {"error": provider_error})
            if provider_refused(provider_error):
                # every retry fails the same way: stop the seat (the episode then ends unbanked, as a
                # transport failure) instead of re-waking it until the window closes
                self.crashed[seat] = f"provider refused: {provider_error}"
                self.bridge.log("seat_crashed", seat, {"error": self.crashed[seat]})
                raise RuntimeError(self.crashed[seat])
            raise TransientSeatError(provider_error)
        text = pi_rpc.turn_text(messages)
        self._core.record_turn(
            seat,
            text_bearing=bool(text.strip()),
            payload={
                "est_tokens": pi_rpc.turn_est_tokens(messages),
                "had_tool_calls": pi_rpc.had_tool_calls(messages),
                **({"text": text} if self.record_turn_text else {}),
            },
        )
        return messages

    def status(self) -> dict[str, Any]:
        """Return commit and pending-push status for the relay."""
        return self._core.status()

    def dm_drain(self, seat: str) -> list[str]:
        """Pop the seat's pending push-DM lines for its next wake."""
        return self._core.dm_drain(seat)

    def dm_requeue(self, seat: str, rows: list[str]) -> None:
        """Restore drained DM lines after a wake that failed to render."""
        self._core.dm_requeue(seat, rows)

    def record_diner_msg(self, seat: str, principal: str, beat: str, text: str) -> None:
        """Ledger one principal-authored opening or debrief prompt."""
        self._core.record_diner_msg(seat, diner=principal, beat=beat, text=text)

    def post_event(self, body: dict[str, Any]) -> None:
        """Ledger one relay event (the admin `/admin/event` dispatch, in-process)."""
        assert self.bridge is not None
        payload = dict(body)
        kind = str(payload.pop("kind", "relay_event"))
        seat = payload.pop("seat", None)
        nested = payload.pop("payload", None)
        if isinstance(nested, dict):
            payload.update(cast(dict[str, Any], nested))
        self.bridge.log(kind, str(seat) if seat is not None else None, payload)

    def finalize_summary(self) -> dict[str, Any]:
        """Settle the world to horizon and return THE one summary (idempotent)."""
        return self._core.finalize()

    def stop(self) -> None:
        """Close pi processes, copy artifacts, scan for credentials, and clean up."""
        if self._stopped:
            return
        self._stopped = True
        cleanup_error: Exception | None = None
        for handle in self.handles.values():
            try:
                pi_rpc.close_agent(handle)
            except OSError:
                pass
            except Exception as exc:  # noqa: BLE001 - finish cleanup for every seat
                cleanup_error = cleanup_error or exc
        if self.container is not None:
            try:
                if self.bridge is not None:
                    _remove_seat_auth(self.container, _as_seat_bridge(self.bridge))
                    if cleanup_error is not None:
                        raise cleanup_error
                    _copy_seat_artifacts(
                        self.container,
                        _as_seat_bridge(self.bridge),
                        self.run_dir,
                    )
                    assert self.server is not None
                    credentials = {
                        "Anthropic API key": self.api_key,
                        **self.server.credential_markers(),
                    }
                    scanned = _scan_artifacts_for_credentials(
                        self.run_dir,
                        credentials,
                    )
                    self.bridge.log(
                        "credential_persistence_scan",
                        None,
                        {"status": "passed", "files_scanned": scanned},
                    )
            except Exception as exc:  # noqa: BLE001 - cleanup must still complete
                cleanup_error = cleanup_error or exc
            finally:
                try:
                    self.container.stop()
                except Exception as exc:  # noqa: BLE001 - still close the hub
                    cleanup_error = cleanup_error or exc
        if self.server is not None:
            try:
                self.server.stop()
            except Exception as exc:  # noqa: BLE001 - preserve the first error
                cleanup_error = cleanup_error or exc
        if cleanup_error is not None:
            raise cleanup_error
