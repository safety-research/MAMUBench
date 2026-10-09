"""Real-pi runtime adapter for the cart-shaped trip world.

Mirrors `food_runtime.FoodRuntime` — same bearer-authenticated `BridgeServer`, per-seat
OS users, fail-closed tool/thinking attestation, isolation preflights, and credential
scan, all reused from `pi_runtime` by import — but the bridge dispatches into the
in-process `TripCartWorld` (one shared draft, any-seat staging, creator-unilateral
confirm), presented to the shared helpers as a `PiSeatBridge`.

The tool manifest is `trip_cart.trip_tools`, authored directly in the hub extension's
contract ({name, description, non-empty `parameters` object schema} — the B1 lesson),
so no host-side `inputSchema` conversion or manifest shipping is needed: the packaged
experiment directory computes the identical manifest in-image.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
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
from personal_assistant.environment.trip_cart import (  # noqa: E402
    TripCartScenario,
    TripCartWorld,
    TripMitigationFlags,
    resolve_trip_spec,
    trip_tools,
)

__all__ = ["TripBridge", "TripRuntime", "TransientSeatError"]

DEFAULT_SCENARIO = "demo_sofa"


class TripBridge:
    """Thread-safe MCP bridge and event ledger for one trip-cart world.

    Structurally satisfies the surface `pi_runtime`'s generic helpers consume
    (`ids`/`usernames`/`seat_cwd`/`workspace_files`/`tools_manifest`/`dispatch`/`log`);
    those helpers are annotated against `PiSeatBridge`, so call sites cast — the
    contract is structural, not nominal.

    `extra_norm_line` / `confirm_seat` (both default-off) forward verbatim into `TripCartScenario` / `TripCartWorld`; `mitigation_flags` (default `None` = all-off) is the enforced arms' `TripMitigationFlags`, forwarded into the world and its flag-aware tool manifest. The defaults keep every surface byte-identical to before the hooks existed.
    """

    def __init__(
        self,
        topology: str,
        ledger_path: Path,
        scenario: str = DEFAULT_SCENARIO,
        *,
        extra_norm_line: str = "",
        confirm_seat: str | None = None,
        mitigation_flags: TripMitigationFlags | None = None,
    ) -> None:
        spec = resolve_trip_spec(scenario)
        self.scenario = TripCartScenario(topology, spec, extra_norm_line)
        self.world = TripCartWorld(topology, spec, confirm_seat, flags=mitigation_flags)
        self.ids: tuple[str, ...] = self.world.ids
        self.usernames: dict[str, str] = self.scenario.usernames()
        self._ledger_path = ledger_path
        self._ledger_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._ledger_path.parent.chmod(0o700)
        self._ledger_path.touch(mode=0o600, exist_ok=True)
        self._ledger_path.chmod(0o600)
        self._rows = 0
        self._lock = threading.RLock()

    def tools_manifest(self) -> list[dict[str, Any]]:
        """Return the exact tool list registered as first-class pi tools (flag-aware)."""
        return trip_tools(self.world.topology, self.world.flags)

    def workspace_files(self, seat: str) -> dict[str, str]:
        """Return files materialized in one private PA workspace."""
        return self.scenario.workspace_files(seat)

    def seat_cwd(self, seat: str) -> str:
        """Return the in-fiction workspace path used inside the runtime container."""
        return f"/home/{self.usernames[seat]}/trip"

    def dispatch(self, seat: str, tool: str, args: dict[str, Any]) -> str:
        """Dispatch one authenticated MCP call and ledger its result."""
        with self._lock:
            result = self.world.dispatch(seat, tool, args)
            self.log(
                "tool_call",
                seat,
                {"tool": tool, "args": args, "result_head": result[:300]},
            )
            return result

    def log(self, kind: str, seat: str | None, payload: dict[str, Any]) -> None:
        """Append one harness event to the authoritative JSONL ledger."""
        with self._lock:
            self._rows += 1
            row = {
                "seq": self._rows,
                "wall_ts": round(time.time(), 3),
                "kind": kind,
                "seat": seat,
                **payload,
            }
            with self._ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _as_seat_bridge(bridge: TripBridge) -> PiSeatBridge:
    """Present the trip bridge to `pi_runtime`'s structurally generic helpers."""
    return cast(PiSeatBridge, bridge)


class TripRuntime:
    """One real-pi trip episode exposing the relay's generic push-runtime contract.

    `context_files` selects the pi launch; `extra_norm_line` / `confirm_seat` / `mitigation_flags` / `on_bridge` (the platform mitigations, all default-off) forward into the `TripBridge` this runtime constructs; the defaults keep every surface byte-identical to before the hooks existed.
    """

    def __init__(
        self,
        topology: str,
        run_dir: Path,
        *,
        model: str,
        provider: str,
        api_key: str,
        turn_timeout: float,
        thinking: str,
        root_host: bool,
        protected_roots: tuple[Path, ...],
        scenario: str = DEFAULT_SCENARIO,
        context_files: bool = False,
        extra_norm_line: str = "",
        confirm_seat: str | None = None,
        mitigation_flags: TripMitigationFlags | None = None,
        on_bridge: Callable[[TripBridge], None] | None = None,
    ) -> None:
        resolve_trip_spec(scenario)
        self.topology = topology
        self.scenario_name = scenario
        self.extra_norm_line = extra_norm_line
        self.confirm_seat = confirm_seat
        self.mitigation_flags = mitigation_flags
        #: Called with the live `TripBridge` right after it is built and before any
        #: seat starts (the mitigation arms' fail-closed flag / manifest attestation).
        self.on_bridge = on_bridge
        self.run_dir = run_dir.resolve()
        self.model = model
        self.provider = provider
        self.api_key = api_key
        self.turn_timeout = turn_timeout
        self.thinking = require_provider_thinking(provider, thinking, runtime="trip")
        self.root_host = root_host
        self.protected_roots = tuple(path.resolve() for path in protected_roots)
        self.context_files = context_files
        #: Per seat, the exact argv it was launched with (recorded in a context-files sidecar).
        self.pi_argv: dict[str, list[str]] = {}
        #: Release-only: extra completion-sidecar fields this runtime records (the unprivileged local
        #: runtime's `host_seat_cwd`); empty on the paper's docker / root-host paths, so their
        #: sidecars stay byte-identical.
        self.sidecar_notes: dict[str, object] = {}
        self.record_turn_text = True
        self.crashed: dict[str, str] = {}
        self.bridge: TripBridge | None = None
        self.server: BridgeServer | None = None
        self.container: _RuntimeContainer | None = None
        self.handles: dict[str, pi_rpc.PiHandle] = {}
        self.ids: tuple[str, ...] = ()
        self._started = False
        self._stopped = False

    def ensure_started(self) -> None:
        """Start the MCP bridge, isolated OS users, and one persistent pi per seat."""
        if self._started:
            return
        try:
            if self.run_dir.exists():
                shutil.rmtree(self.run_dir)
            for protected_root in self.protected_roots:
                _make_private_dir(protected_root)
            _make_private_dir(self.run_dir)
            world_dir = self.run_dir / "world"
            _make_private_dir(world_dir)
            bridge = TripBridge(
                self.topology,
                world_dir / "ledger.jsonl",
                self.scenario_name,
                extra_norm_line=self.extra_norm_line,
                confirm_seat=self.confirm_seat,
                mitigation_flags=self.mitigation_flags,
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
                json.dumps(bridge.tools_manifest(), indent=2),
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
                    "topology": self.topology,
                    "scenario": self.scenario_name,
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
    def _world(self) -> TripCartWorld:
        assert self.bridge is not None
        return self.bridge.world

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
        self._world.rendered_turns.append(
            {
                "seat": seat,
                "text": text,
                "had_tool_calls": pi_rpc.had_tool_calls(messages),
            }
        )
        self.bridge.log(
            "turn_rendered",
            seat,
            {
                "text": text,
                "had_tool_calls": pi_rpc.had_tool_calls(messages),
            },
        )
        return messages

    def status(self) -> dict[str, Any]:
        """Return commit and pending-push status for the relay."""
        return self._world.status()

    def dm_drain(self, seat: str) -> list[str]:
        """Drain DMs and platform receipts, all delivered through the push relay."""
        return self._world.drain(seat)

    def dm_requeue(self, seat: str, rows: list[str]) -> None:
        """Requeue push events after a transient provider failure."""
        self._world.requeue(seat, rows)

    def record_diner_msg(self, seat: str, principal: str, beat: str, text: str) -> None:
        """Ledger one principal-authored opening or debrief prompt."""
        self._world.prompts.append(
            {"seat": seat, "principal": principal, "beat": beat, "text": text}
        )
        assert self.bridge is not None
        self.bridge.log(
            "principal_prompt",
            seat,
            {"principal": principal, "beat": beat, "text": text},
        )

    def post_event(self, body: dict[str, Any]) -> None:
        """Ledger one relay event."""
        assert self.bridge is not None
        payload = dict(body)
        kind = str(payload.pop("kind", "relay_event"))
        seat = payload.pop("seat", None)
        nested = payload.pop("payload", None)
        if isinstance(nested, dict):
            payload.update(cast(dict[str, Any], nested))
        self.bridge.log(kind, str(seat) if seat is not None else None, payload)

    def finalize_summary(self) -> dict[str, Any]:
        """Return the authoritative world state without any post-booking horizon."""
        return self._world.summary()

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
