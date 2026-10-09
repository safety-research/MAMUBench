"""Unprivileged local runtimes: the environment's food/trip episodes without docker or root.

The environment's `FoodRuntime` / `TripRuntime` bring an episode up through a `_RuntimeContainer`
(docker, or Modal's root-host shim) and fail closed on per-seat OS-user isolation preflights.
Neither is available on an ordinary host, so this module adds a third container shape:

* `LocalHostShim` — the same `_RuntimeContainer` surface executed as the CURRENT user. Every
  in-fiction `/home/<seat>` path is materialized under a private temp root (deleted at stop),
  ownership changes are declared no-ops, and each seat's pi is a direct child process launched
  through `seat_exec.py`, which swaps the bare `pi` for the pinned binary the driver resolved and
  maps the in-fiction paths back. The seat sees the same argv flags, the same env variable NAMES,
  the same AGENTS.md / tools.json / auth.json layout, the same bearer-authenticated hub — only
  the OS-user boundary is missing.
* `LocalFoodRuntime` / `LocalTripRuntime` — the environment runtimes with `ensure_started`
  re-composed from the environment's own helpers (`_setup_container`, `_spawn_seat`,
  `_preflight_tool_surfaces`; `stop()` keeps owning `_copy_seat_artifacts` and the credential
  scan) minus the two OS-isolation preflights that cannot hold under one uid. `configure()`
  selects `none` (this shim) or `docker` (the environment's own path, unchanged) for the process.

DISCLOSED DELTA vs the run of record: no per-seat OS user (a seat with shell tools could read a
peer's drawer — the environment's cells disable pi's native tools and preflight that, so the
typed hub tools are the whole surface) and in-fiction absolute paths are host paths underneath.
That second part reaches the model: pi 0.77.0 ends every system prompt with `Current working
directory: <process cwd>` (and names the loaded AGENTS.md by path under `--context-files on`), so
a seat here reads `<temp>/pa-XXXXXXXX/home/pa-<name>/dinner` where the paper's seats read
`/home/pa-<name>/dinner`. The shim root's name is opaque and fixed-length (`SEAT_ROOT_PREFIX` plus
`mkdtemp`'s random suffix) so it carries nothing about the episode (scenario, formation, arm,
model); `EVAL_SEAT_ROOT` picks the directory it is made under. The ledger's
`runtime_started.isolation` block records the delta and the completion sidecar carries the seats'
actual cwds as `host_seat_cwd`, so no reader mistakes a local episode for a contained one.

`--isolation root` is the environment's own root-host path (`live_docker.RootHostShim`, what the paper's
Modal episodes ran: real `useradd` seat users, `setpriv`, seat cwd `/home/pa-<name>/dinner`), for a
root, single-use Linux container; `auto` (the runner's default) selects it inside a Modal container
and `none` everywhere else. The only addition there is `_install_root_seat_pi`: the bare `pi` the
paper launches resolves to the pinned (or fake) pi through a seat-readable bin dir on `PATH`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Protocol, cast

from personal_assistant._paths import PA_HARNESS_DIR, bootstrap

bootstrap()

from _harness import pi_rpc  # noqa: E402

from personal_assistant.environment.food_runtime import (  # noqa: E402
    ConfidentialFoodBridge,
    FoodRuntime,
    _hub_tool_rows,  # pyright: ignore[reportPrivateUsage]
)
from personal_assistant.environment.pi_runtime import (  # noqa: E402
    BridgeServer,
    PiSeatBridge,
    _make_private_dir,  # pyright: ignore[reportPrivateUsage]
    _make_private_tree,  # pyright: ignore[reportPrivateUsage]
    _preflight_tool_surfaces,  # pyright: ignore[reportPrivateUsage]
    _private_file,  # pyright: ignore[reportPrivateUsage]
    _RuntimeContainer,  # pyright: ignore[reportPrivateUsage]
    _setup_container,  # pyright: ignore[reportPrivateUsage]
    _spawn_seat,  # pyright: ignore[reportPrivateUsage]
)
from personal_assistant.environment.trip_runtime import (  # noqa: E402
    TripBridge,
    TripRuntime,
)

SEAT_EXEC = Path(__file__).resolve().with_name("seat_exec.py")
FAKE_PI = Path(__file__).resolve().with_name("fake_pi.py")

#: The isolation modes a run resolves to. `root` (the environment's root-host path, the paper's Modal
#: episodes) and `docker` are the environment's own paths; `none` is `LocalHostShim`.
ISOLATION_MODES: tuple[str, ...] = ("none", "root", "docker")
#: What `run.py --isolation` accepts: `auto` resolves per host (`resolve_isolation`).
ISOLATION_CHOICES: tuple[str, ...] = ("auto", *ISOLATION_MODES)

#: The shim root's name prefix. `mkdtemp` appends 8 random characters, so the directory pi prints
#: as part of every seat's cwd is opaque and fixed-length: never the run dir's name (which carries
#: the scenario, formation, mitigation arm and model), never "eval".
SEAT_ROOT_PREFIX = "pa-"

#: Host tools the root-host path runs (`RootHostShim`: `useradd`, `setpriv`, the `pkill -u` kill).
ROOT_HOST_TOOLS: tuple[str, ...] = ("useradd", "setpriv", "pkill")

#: Seconds every seat gets to start pi and attest its tool surface. The environment's default (15 s)
#: assumes pi on local disk inside a container; a network-mounted pi install starting 20-40 seats
#: at once needs minutes, not seconds.
DEFAULT_ATTEST_TIMEOUT = 180.0

#: Setup commands the environment issues to give a seat's files to its OS user. There is one user
#: here, so they are declared no-ops (recorded in the isolation block below), never executed.
_IGNORED_OWNERSHIP_COMMANDS = frozenset({"chown"})

#: No out-of-band kill exists for a seat (no uid to `pkill -u`); `pi_rpc._kill_tree` runs this
#: first and then kills the host process group, which is the seat's whole tree here because each
#: seat is a direct child in its own session.
_NO_OUT_OF_BAND_KILL: tuple[str, ...] = ("true",)

_ISOLATION_RECORD: dict[str, object] = {
    "episode_boundary": "none_local_unprivileged",
    "seat_boundary": "per_seat_home_dir_same_os_user",
    "peer_home_preflight": "not_applicable",
    "peer_home_pairs_checked": None,
    "host_artifact_preflight": "not_applicable",
    "host_artifact_paths_checked": None,
    "peer_process_environ_preflight": "not_applicable",
    "peer_process_environ_pairs_checked": None,
    "ownership_commands": "ignored_single_uid",
    "home_mode": "0700",
    "tmpdir": "per_seat_home",
    "tmpdir_mode": "0700",
    "native_pi_tools": "disabled",
    # pi prints its cwd in every system prompt: here a host path under the opaque shim root, not
    # the in-fiction /home/<seat>/... (the sidecar's `host_seat_cwd` lists them)
    "seat_cwd": "host_temp_root",
}


@dataclass(frozen=True)
class SeatLaunch:
    """How this process launches seats: the pinned pi, where node lives, fake-pi scripts."""

    pi_cmd: Path
    node_dir: Path | None = None
    fake_script_dir: Path | None = None

    @property
    def path(self) -> str:
        """The seat's `PATH`: node first when the driver was told where it is."""
        inherited = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
        return (
            os.pathsep.join([str(self.node_dir), inherited])
            if self.node_dir
            else inherited
        )


class LocalHostShim:
    """`_RuntimeContainer` for an unprivileged host (see the module docstring)."""

    def __init__(self, run_dir: Path, launch: SeatLaunch) -> None:
        self.run_dir = run_dir
        self.launch = launch
        self.name = f"localhost-{run_dir.name}"
        self._root: Path | None = None

    @property
    def root(self) -> Path:
        """The private root every in-fiction absolute path is materialized under."""
        assert self._root is not None, "LocalHostShim.start() first"
        return self._root

    def start(self) -> None:
        """Create the private seat-home root (under `EVAL_SEAT_ROOT` or the system temp dir).

        Its name is `SEAT_ROOT_PREFIX` + 8 random characters: every seat's cwd (which pi prints in
        its system prompt) lives under it, so it must say nothing about the episode.
        """
        base = os.environ.get("EVAL_SEAT_ROOT") or None
        if base is not None:
            Path(base).mkdir(parents=True, exist_ok=True, mode=0o700)
        self._root = Path(tempfile.mkdtemp(prefix=SEAT_ROOT_PREFIX, dir=base))
        self._root.chmod(0o700)

    def host_cwd(self, in_fiction: str) -> str:
        """The working directory pi actually sees for an in-fiction cwd (symlinks resolved, as pi's `process.cwd()`)."""
        return str(self.map_path(in_fiction).resolve())

    def map_path(self, path: str) -> Path:
        """`/home/<seat>/...` -> `<root>/home/<seat>/...`; any other path is a host path."""
        if path.startswith("/home/"):
            return self.root / path.lstrip("/")
        return Path(path)

    def _map_arg(self, arg: str) -> str:
        return str(self.map_path(arg)) if arg.startswith("/home/") else arg

    def exec_run(
        self,
        argv: list[str],
        *,
        user: str | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run one setup command on the host; ownership changes are declared no-ops."""
        del user  # one OS user: seat identity is a directory, not a uid
        if argv and argv[0] in _IGNORED_OWNERSHIP_COMMANDS:
            return subprocess.CompletedProcess(argv, 0, "", "")
        mapped = [self._map_arg(arg) for arg in argv]
        result = subprocess.run(
            mapped, input=input_text, capture_output=True, text=True, timeout=120
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"local-host command failed ({' '.join(mapped[:6])}…): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result

    def add_seat_user(self, username: str) -> None:
        """Create the seat's home directory (0700) — the seat's whole identity here."""
        _make_private_dir(self.map_path(f"/home/{username}"))

    def write_file(
        self, path: str, text: str, *, owner: str | None = None, mode: str = "0644"
    ) -> None:
        """Materialize one file at its (mapped) absolute path with the requested mode."""
        del owner
        target = self.map_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        target.chmod(int(mode, 8))

    def copy_in(self, host_path: Path, container_path: str) -> None:
        """Copy a host tree to its (mapped) in-fiction path."""
        shutil.copytree(host_path, self.map_path(container_path), dirs_exist_ok=True)

    def copy_out(self, container_path: str, host_dir: Path) -> bool:
        """Copy a (mapped) in-fiction path under `host_dir` (`cp -r` semantics)."""
        source = self.map_path(container_path)
        if not source.exists():
            return False
        host_dir.mkdir(parents=True, exist_ok=True)
        target = host_dir / source.name
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)
        return True

    def seat_exec_argv(
        self, *, username: str, cwd: str, env: dict[str, str]
    ) -> tuple[list[str], dict[str, str]]:
        """The exec prefix for one seat plus the env it launches with (paths remapped).

        The environment's `_spawn_seat` supplies `HOME`, `TMPDIR`, `PI_CODING_AGENT_DIR`, ... as
        in-fiction `/home/<seat>` paths; they are mapped here so pi resolves its agent dir,
        auth file and sessions under the shim root. The pinned pi travels to `seat_exec.py` as
        an argument (no PATH search picks the binary). In fake-pi mode the seat is told which
        script to play through `FAKE_PI_SCRIPT_DIR` + `FAKE_PI_SEAT`.
        """
        launch_env: dict[str, str] = {
            "PATH": self.launch.path,
            **{key: self._map_arg(value) for key, value in env.items()},
        }
        if self.launch.fake_script_dir is not None:
            launch_env["FAKE_PI_SCRIPT_DIR"] = str(self.launch.fake_script_dir)
            launch_env["FAKE_PI_SEAT"] = username
        prefix = [
            sys.executable,
            str(SEAT_EXEC),
            str(self.root),
            str(self.map_path(cwd)),
            str(self.launch.pi_cmd),
        ]
        return prefix, launch_env

    def kill_user_argv(self, username: str) -> list[str]:
        """See `_NO_OUT_OF_BAND_KILL`."""
        del username
        return list(_NO_OUT_OF_BAND_KILL)

    def stop(self) -> None:
        """Delete the private root — seat homes (incl. auth files) never outlive the episode."""
        if self._root is not None:
            shutil.rmtree(self._root, ignore_errors=True)
            self._root = None


class _LocalRuntime(Protocol):
    """The environment-runtime surface `_start_local` reads and writes (both runtimes share it)."""

    run_dir: Path
    protected_roots: tuple[Path, ...]
    provider: str
    api_key: str
    model: str
    thinking: str
    server: BridgeServer | None
    container: _RuntimeContainer | None
    handles: dict[str, pi_rpc.PiHandle]
    ids: tuple[str, ...]
    _started: bool
    context_files: bool
    pi_argv: dict[str, list[str]]
    sidecar_notes: dict[str, object]

    def stop(self) -> None: ...


Bridge = ConfidentialFoodBridge | TripBridge


def _start_local(
    runtime: _LocalRuntime,
    make_bridge: Callable[[], Bridge],
    *,
    launch: SeatLaunch,
    attest_timeout: float,
    record: dict[str, Any],
    on_bridge: Callable[[Any], None] | None = None,
) -> Bridge:
    """The environment's `ensure_started` sequence over `LocalHostShim`, minus OS-isolation preflights.

    Identical calls, in the environment's order: fresh run dir, bridge (built by the caller's
    factory once the run dir exists), hub server, agent dir + tools.json, per-seat setup
    (`_setup_container`), seat spawn (`_spawn_seat`), the fail-closed tool/thinking attestation
    (`_preflight_tool_surfaces`), then the `runtime_started` ledger row. Any failure tears down
    through the runtime's own `stop()` and re-raises. Returns the bridge for the caller to bind.
    """
    server: BridgeServer | None = None
    container: LocalHostShim | None = None
    try:
        if runtime.run_dir.exists():
            shutil.rmtree(runtime.run_dir)
        for protected_root in runtime.protected_roots:
            _make_private_dir(protected_root)
        _make_private_dir(runtime.run_dir)
        _make_private_dir(runtime.run_dir / "world")
        bridge = make_bridge()
        if on_bridge is not None:
            on_bridge(bridge)
        seat_bridge = cast(
            PiSeatBridge, bridge
        )  # the environment's own structural cast
        runtime.ids = bridge.ids
        server = BridgeServer(seat_bridge, host="127.0.0.1")
        server.start()
        runtime.server = server
        container = LocalHostShim(runtime.run_dir, launch)
        container.start()
        runtime.container = container
        agent_dir = runtime.run_dir / "agent_dir"
        shutil.copytree(PA_HARNESS_DIR / "agent_dir", agent_dir)
        (agent_dir / "tools.json").write_text(
            json.dumps(_hub_tool_rows(bridge.tools_manifest()), indent=2),
            encoding="utf-8",
        )
        _make_private_tree(agent_dir)
        _setup_container(
            container,
            seat_bridge,
            agent_dir=agent_dir,
            provider=runtime.provider,
            api_key=runtime.api_key,
        )
        for seat in bridge.ids:
            seat_dir = runtime.run_dir / "agents" / seat
            _make_private_dir(seat_dir)
            _private_file(seat_dir / "stderr.log")
            runtime.handles[seat] = _spawn_seat(
                container,
                seat_bridge,
                seat,
                provider=runtime.provider,
                model=runtime.model,
                thinking=runtime.thinking,
                server_url=f"http://127.0.0.1:{server.port}",
                seat_token=server.token_for(seat),
                seat_dir=seat_dir,
                run_dir=runtime.run_dir,
                context_files=runtime.context_files,
            )
        runtime.pi_argv = {
            seat: list(handle.argv) for seat, handle in runtime.handles.items()
        }
        # What pi prints as each seat's cwd here (not the paper's /home/<seat>/...): into the sidecar.
        runtime.sidecar_notes = {
            "host_seat_cwd": {
                seat: container.host_cwd(seat_bridge.seat_cwd(seat))
                for seat in bridge.ids
            }
        }
        checks = _preflight_tool_surfaces(
            server,
            seat_bridge,
            timeout=attest_timeout,
            expected_thinking=runtime.thinking,
            expected_context_files=runtime.context_files,
            # pi reads the seat's AGENTS.md under the shim root, not at /home/<seat>/..., and
            # reports it from its real working directory (symlinks resolved, e.g. macOS /var)
            map_path=lambda path: container.map_path(path).resolve(),
        )
        runtime._started = True  # pyright: ignore[reportPrivateUsage]
        bridge.log(
            "runtime_started",
            None,
            {
                **record,
                "thinking": runtime.thinking,
                # Recorded only when on, so a run-of-record ledger stays byte-identical.
                **({"context_files": True} if runtime.context_files else {}),
                "tool_names": [str(row["name"]) for row in bridge.tools_manifest()],
                "isolation": {
                    **_ISOLATION_RECORD,
                    "tool_surface_preflight": "passed",
                    "tool_surface_seats_checked": checks,
                },
            },
        )
        return bridge
    except Exception:
        # `stop()` closes whatever was bound; anything it never saw is closed here.
        if runtime.server is None and server is not None:
            server.stop()
        if runtime.container is None and container is not None:
            container.stop()
        runtime.stop()
        raise


class _LocalMode:
    """Per-process launch configuration shared by both local runtimes (set by `configure`)."""

    isolation: ClassVar[str] = "none"
    launch: ClassVar[SeatLaunch] = SeatLaunch(pi_cmd=Path("pi"))
    attest_timeout: ClassVar[float] = DEFAULT_ATTEST_TIMEOUT


class LocalFoodRuntime(_LocalMode, FoodRuntime):
    """`FoodRuntime` that can also run without docker/root (`isolation = "none"`)."""

    def ensure_started(self) -> None:
        """Bring the episode up locally, or defer to the environment's docker path."""
        if self._started:
            return
        if self.root_host or self.isolation == "docker":
            super().ensure_started()
            return
        self.bridge = cast(
            ConfidentialFoodBridge,
            _start_local(
                self,
                lambda: ConfidentialFoodBridge(
                    self.cell_name,
                    self.epoch,
                    self.run_dir / "world",
                    git_sha=self.git_sha,
                    manifest=self.manifest,
                ),
                launch=self.launch,
                attest_timeout=self.attest_timeout,
                record={"cell": self.cell_name},
                on_bridge=self.on_bridge,
            ),
        )


class LocalTripRuntime(_LocalMode, TripRuntime):
    """`TripRuntime` that can also run without docker/root (`isolation = "none"`)."""

    def ensure_started(self) -> None:
        """Bring the episode up locally, or defer to the environment's docker path."""
        if self._started:
            return
        if self.root_host or self.isolation == "docker":
            super().ensure_started()
            return
        self.bridge = cast(
            TripBridge,
            _start_local(
                self,
                lambda: TripBridge(
                    self.topology,
                    self.run_dir / "world" / "ledger.jsonl",
                    self.scenario_name,
                    extra_norm_line=self.extra_norm_line,
                    confirm_seat=self.confirm_seat,
                    mitigation_flags=self.mitigation_flags,
                ),
                launch=self.launch,
                attest_timeout=self.attest_timeout,
                record={"topology": self.topology, "scenario": self.scenario_name},
                on_bridge=self.on_bridge,
            ),
        )


def in_modal_container() -> bool:
    """Whether this process runs inside a Modal container (Modal's own test, `modal.is_local()`)."""
    return os.environ.get("MODAL_IS_REMOTE") == "1"


def root_host_problem() -> str | None:
    """Why the environment's root-host path cannot run on this host, or None when it can."""
    if not sys.platform.startswith("linux"):
        return f"it needs Linux (this is {sys.platform})"
    if os.geteuid() != 0:
        return "it needs root (it creates one OS user per seat)"
    missing = [tool for tool in ROOT_HOST_TOOLS if shutil.which(tool) is None]
    if missing:
        return f"missing host tools: {', '.join(missing)}"
    return None


def resolve_isolation(requested: str, *, check: bool = True) -> str:
    """The isolation mode a run uses: `auto` is `root` inside a Modal container, else `none`.

    A Modal episode runs alone in a single-use root container, which is where the paper's episodes
    ran the root-host path (the paper's launchers, `root_host=True`); anywhere else `root` would leave seat users behind on a shared host, so it is
    only ever explicit. `check=False` skips the host probe (`--print-info` only prints the plan).

    Raises:
        SystemExit: `root` (asked for, or `auto` in a Modal container) on a host that cannot run it.
    """
    if requested not in ISOLATION_CHOICES:
        raise ValueError(
            f"isolation must be one of {ISOLATION_CHOICES}; got {requested!r}"
        )
    mode = requested
    if requested == "auto":
        mode = "root" if in_modal_container() else "none"
    if mode == "root" and check and (problem := root_host_problem()) is not None:
        raise SystemExit(
            f"--isolation {requested} selects the paper's root-host path (per-seat OS users, seat "
            f"cwd /home/pa-<name>/dinner), but {problem}; use --isolation none (per-seat homes under "
            "one OS user) or docker"
        )
    return mode


#: Where `_install_root_seat_pi` put the seats' `pi` this process (one per process).
_ROOT_SEAT_BIN: list[Path] = []

_FAKE_PI_WRAPPER = """#!/bin/sh
# MAMUBench --isolation root --fake-pi: the seat's bare `pi` is harness/fake_pi.py, playing the
# script named after this seat's OS user (LocalHostShim passes the same pair as env).
FAKE_PI_SEAT="$(id -un)"
export FAKE_PI_SEAT
{script_dir}exec python3 "{fake_pi}" "$@"
"""


def _install_root_seat_pi(launch: SeatLaunch) -> Path:
    """Make the bare `pi` the root-host path launches resolve to the pinned (or fake) pi.

    `RootHostShim` runs `setpriv ... env -C <cwd> pi ...` with this process's `PATH`, as the research code
    did with pi installed in the image. A private, seat-readable bin dir goes first on `PATH`: `pi`
    there is a symlink to the pinned pi, or, under `--fake-pi`, a wrapper around a copy of
    `fake_pi.py` (and of the scripts), since the seats' OS users cannot read the repository (a
    protected root, as in the research code). Idempotent per process.
    """
    if _ROOT_SEAT_BIN:
        return _ROOT_SEAT_BIN[0]
    bin_dir = Path(tempfile.mkdtemp(prefix="pa-pi-"))
    bin_dir.chmod(0o755)
    pi = bin_dir / "pi"
    if launch.pi_cmd.resolve() == FAKE_PI.resolve():
        shutil.copy2(FAKE_PI, bin_dir / FAKE_PI.name)
        (bin_dir / FAKE_PI.name).chmod(0o644)
        script_line = ""
        if launch.fake_script_dir is not None:
            scripts = bin_dir / "scripts"
            shutil.copytree(launch.fake_script_dir, scripts)
            for path in (scripts, *scripts.rglob("*")):
                path.chmod(0o755 if path.is_dir() else 0o644)
            script_line = f'FAKE_PI_SCRIPT_DIR="{scripts}"\nexport FAKE_PI_SCRIPT_DIR\n'
        pi.write_text(
            _FAKE_PI_WRAPPER.format(
                script_dir=script_line, fake_pi=bin_dir / FAKE_PI.name
            )
        )
        pi.chmod(0o755)
    else:
        pi.symlink_to(launch.pi_cmd)
    os.environ["PATH"] = os.pathsep.join(
        [str(bin_dir), *filter(None, os.environ.get("PATH", "").split(os.pathsep))]
    )
    _ROOT_SEAT_BIN.append(bin_dir)
    return bin_dir


def configure(
    isolation: str,
    launch: SeatLaunch,
    attest_timeout: float = DEFAULT_ATTEST_TIMEOUT,
) -> None:
    """Select the (resolved) isolation mode, seat launch configuration and attestation window."""
    if isolation not in ISOLATION_MODES:
        raise ValueError(
            f"isolation must be one of {ISOLATION_MODES}; got {isolation!r}"
        )
    _LocalMode.isolation = isolation
    _LocalMode.launch = launch
    _LocalMode.attest_timeout = attest_timeout
    if isolation == "root":
        _install_root_seat_pi(launch)
