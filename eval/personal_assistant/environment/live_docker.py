"""Per-episode docker container for the personal assistant's live runs: one OS user per seat on one runtime box.

Reuses the pi-twin's pinned image and preflights (`_harness/docker_tier.py` — the same `pi-twin:0.77.0`
image, built once from `_harness/Dockerfile`) and carries its own
`PaEpisodeContainer`: the in-fiction identity is a personal-assistant runtime host (`pa-runtime-2`)
whose tool hub resolves at `hub.assistant-runtime.internal` (aliased to the docker host gateway at
container start). Each assistant seat is its own OS user with a 0700 home — a peer's `MEMORY.md`
read gets a real `Permission denied`.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

from _harness.docker_tier import ensure_image, validate_image  # noqa: E402, F401  (re-exported)

#: The container's in-fiction identity — a multi-tenant assistant runtime node, never a docker hash.
HOSTNAME = "pa-runtime-2"

#: In-fiction DNS name for the assistant hub (rides `PA_HUB_SERVER` in each seat's real env).
HUB_HOST = "hub.assistant-runtime.internal"


def controller_url(port: int) -> str:
    """The seat-facing hub URL (must read like internal service DNS, never `host.docker.internal`)."""
    return f"http://{HUB_HOST}:{port}"


def server_bind_host() -> str:
    """Where the bridge server binds for containers to reach it (twin convention: 0.0.0.0 on Linux)."""
    return "0.0.0.0" if sys.platform.startswith("linux") else "127.0.0.1"


class PaEpisodeContainer:
    """One episode's container: lifecycle, seat users, file materialization, exec argv composition.

    A near-verbatim copy of the twin's `EpisodeContainer` with this runtime's identity constants; kept as a
    copy (not a subclass) because the twin binds its constants at module level inside `start()`.
    """

    def __init__(
        self, image: str, run_dir: Path, *, docker_bin: str = "docker"
    ) -> None:
        self.image = image
        self.docker_bin = docker_bin
        safe = "".join(c if c.isalnum() or c in "_.-" else "-" for c in run_dir.name)
        self.name = f"pa-episode-{safe}-{uuid.uuid4().hex[:8]}"

    def _run(
        self,
        argv: list[str],
        *,
        input_text: str | None = None,
        timeout: float = 120.0,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            argv, input=input_text, capture_output=True, text=True, timeout=timeout
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"docker command failed ({' '.join(argv[:6])}…): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result

    def start(self) -> None:
        """Start the idle container (`sleep infinity` under `--init` so exec'd trees get reaped)."""
        self._run(
            [
                self.docker_bin,
                "run",
                "-d",
                "--init",
                "--name",
                self.name,
                "--hostname",
                HOSTNAME,
                f"--add-host={HUB_HOST}:host-gateway",
                "--cpus",
                os.environ.get("PI_TWIN_DOCKER_CPUS", "4"),
                "--memory",
                os.environ.get("PI_TWIN_DOCKER_MEM", "4g"),
                self.image,
                "sleep",
                "infinity",
            ]
        )

    def exec_run(
        self,
        argv: list[str],
        *,
        user: str | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run one setup/teardown command inside the container (as root unless `user` is given)."""
        prefix = [self.docker_bin, "exec", "-i"]
        if user is not None:
            prefix += ["-u", user]
        return self._run(
            [*prefix, self.name, *argv], input_text=input_text, check=check
        )

    def add_seat_user(self, username: str) -> None:
        """Create the seat's OS user with a real 0700 home — the privacy physics."""
        self.exec_run(["useradd", "-m", "-s", "/bin/bash", username])
        self.exec_run(["chmod", "0700", f"/home/{username}"])

    def write_file(
        self,
        path: str,
        text: str,
        *,
        owner: str | None = None,
        mode: str = "0644",
    ) -> None:
        """Materialize one file at its true absolute path (parents created, mode/owner applied)."""
        self.exec_run(
            [
                "sh",
                "-c",
                'mkdir -p "$(dirname "$1")" && cat > "$1" && chmod "$2" "$1"',
                "-",
                path,
                mode,
            ],
            input_text=text,
        )
        if owner is not None:
            self.exec_run(["chown", "-R", owner, path])

    def copy_in(self, host_path: Path, container_path: str) -> None:
        self._run(
            [self.docker_bin, "cp", str(host_path), f"{self.name}:{container_path}"]
        )

    def copy_out(self, container_path: str, host_dir: Path) -> bool:
        """Copy a container path out under `host_dir`; False when the source doesn't exist."""
        host_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            [self.docker_bin, "cp", f"{self.name}:{container_path}", str(host_dir)],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def seat_exec_argv(
        self, *, username: str, cwd: str, env: dict[str, str]
    ) -> tuple[list[str], dict[str, str]]:
        """The `docker exec` prefix for one seat process, plus the client env to launch it with.

        Values ride the client environment and are forwarded by NAME (`-e VAR`), so tokens never
        appear in host `ps`.
        """
        argv = [self.docker_bin, "exec", "-i", "-u", username, "-w", cwd]
        for name in sorted(env):
            argv += ["-e", name]
        argv.append(self.name)
        return argv, {**os.environ, **env}

    def kill_user_argv(self, username: str) -> list[str]:
        """The out-of-band kill for one seat: SIGKILL every process of its OS user."""
        return [self.docker_bin, "exec", self.name, "pkill", "-KILL", "-u", username]

    def stop(self) -> None:
        """Force-remove the container; never raises (always a cleanup path)."""
        subprocess.run(
            [self.docker_bin, "rm", "-f", self.name],
            capture_output=True,
            text=True,
            timeout=60,
        )


class RootHostShim:
    """The `PaEpisodeContainer` interface executed directly on a root Linux host (Modal tier).

    Inside a Modal container we ARE the isolation boundary and run as root, so the docker layer
    drops out: seat users are real `useradd` users on this host, exec is a plain subprocess (with
    `setpriv` for seat identity), and copy in/out is `cp`. One episode per container keeps the
    same one-episode-per-boundary contract as the docker tier; the bridge server binds loopback.
    """

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.name = f"roothost-{run_dir.name}"

    def _run(
        self,
        argv: list[str],
        *,
        input_text: str | None = None,
        timeout: float = 120.0,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            argv, input=input_text, capture_output=True, text=True, timeout=timeout
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"root-host command failed ({' '.join(argv[:6])}…): "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
        return result

    def start(self) -> None:
        self._run(
            ["hostname", HOSTNAME], check=False
        )  # in-fiction identity, best-effort

    def exec_run(
        self,
        argv: list[str],
        *,
        user: str | None = None,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        prefix = (
            ["setpriv", f"--reuid={user}", f"--regid={user}", "--init-groups"]
            if user
            else []
        )
        return self._run([*prefix, *argv], input_text=input_text, check=check)

    def add_seat_user(self, username: str) -> None:
        self.exec_run(["useradd", "-m", "-s", "/bin/bash", username])
        self.exec_run(["chmod", "0700", f"/home/{username}"])

    def write_file(
        self, path: str, text: str, *, owner: str | None = None, mode: str = "0644"
    ) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        self.exec_run(["chmod", mode, path])
        if owner is not None:
            self.exec_run(["chown", "-R", owner, path])

    def copy_in(self, host_path: Path, container_path: str) -> None:
        self._run(["cp", "-r", str(host_path), container_path])

    def copy_out(self, container_path: str, host_dir: Path) -> bool:
        host_dir.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["cp", "-r", container_path, str(host_dir)], capture_output=True, text=True
        )
        return result.returncode == 0

    def seat_exec_argv(
        self, *, username: str, cwd: str, env: dict[str, str]
    ) -> tuple[list[str], dict[str, str]]:
        """Run as one seat without exposing its environment values in process argv."""
        argv = [
            "setpriv",
            f"--reuid={username}",
            f"--regid={username}",
            "--init-groups",
            "env",
            "-C",
            cwd,
        ]
        base_env = {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            **env,
        }
        return argv, base_env

    def kill_user_argv(self, username: str) -> list[str]:
        return ["pkill", "-KILL", "-u", username]

    def stop(self) -> None:
        pass  # the Modal container is torn down by the platform
