"""The pinned pi image (`Dockerfile`, tag `pi-twin:<PI_PIN>`): build it once, then attest its runtime.

personal_assistant's docker tier (`personal_assistant/environment/live_docker.py`) runs each episode's seats
in a container of this image, and the Modal image is built from the same `Dockerfile`. The image builds once
via a stdin build (no build context uploaded), only under its pinned default tag; an explicit
`PI_TWIN_DOCKER_IMAGE` override must already exist locally.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from _harness.pi_rpc import PI_PIN, matches_pin, node_major

EXP_DIR = Path(__file__).resolve().parent
DOCKERFILE = EXP_DIR / "Dockerfile"

#: Auto-built default image tag; `PI_TWIN_DOCKER_IMAGE` overrides (and must already exist locally).
DEFAULT_IMAGE = f"pi-twin:{PI_PIN}"


def image_name() -> str:
    """The image tag to run; `PI_TWIN_DOCKER_IMAGE` overrides the pinned default."""
    return os.environ.get("PI_TWIN_DOCKER_IMAGE", DEFAULT_IMAGE)


def ensure_image(docker_bin: str = "docker") -> str:
    """Build the twin image from `Dockerfile` if absent; return its tag.

    Doubles as the docker preflight: a missing binary or unusable daemon surfaces as a clear
    `SystemExit` before any run directory is touched. Only the pinned default tag is auto-built; a
    `PI_TWIN_DOCKER_IMAGE` override must already exist locally.
    """
    image = image_name()
    try:
        daemon = subprocess.run([docker_bin, "version"], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(f"docker binary not found: {docker_bin}") from None
    if daemon.returncode != 0:
        raise SystemExit(
            f"docker daemon not usable: {daemon.stderr.strip() or daemon.stdout.strip()}"
        )
    probe = subprocess.run(
        [docker_bin, "image", "inspect", image], capture_output=True, text=True
    )
    if probe.returncode == 0:
        return image
    if "PI_TWIN_DOCKER_IMAGE" in os.environ:
        raise SystemExit(
            f"PI_TWIN_DOCKER_IMAGE={image} not found locally; pull or build it first "
            f"(only the pinned default {DEFAULT_IMAGE} is auto-built)"
        )
    if f"@{PI_PIN}" not in DOCKERFILE.read_text():
        raise SystemExit(
            f"{DOCKERFILE.name} does not pin pi@{PI_PIN}: PI_PIN and the Dockerfile npm pin "
            "must move in lockstep (re-run the real-pi smoke on any bump)"
        )
    print(f"[docker] building {image} from {DOCKERFILE.name} (one-time)", flush=True)
    with DOCKERFILE.open("rb") as df:
        build = subprocess.run(
            [docker_bin, "build", "-t", image, "-"],
            stdin=df,
            capture_output=True,
            text=True,
        )
    if build.returncode != 0:
        raise SystemExit(f"docker build of {image} failed:\n{build.stderr[-3000:]}")
    return image


def validate_image(image: str, docker_bin: str = "docker") -> None:
    """Require the reviewed in-image runtime (Node 22+, pi == PI_PIN) — the docker-tier preflight."""
    probe = subprocess.run(
        [
            docker_bin,
            "run",
            "--rm",
            image,
            "sh",
            "-c",
            "node --version && pi --version 2>&1",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if probe.returncode != 0:
        raise SystemExit(
            f"image {image} runtime probe failed: {probe.stderr.strip() or probe.stdout.strip()}"
        )
    lines = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        raise SystemExit(f"image {image} runtime probe output unreadable: {lines!r}")
    node, pi = lines[0], lines[-1]
    if node_major(node) < 22:
        raise SystemExit(f"image {image} carries Node {node!r}; Node 22+ is required")
    if not matches_pin(pi):
        raise SystemExit(
            f"image {image} carries pi {pi!r}; {PI_PIN} exactly is required"
        )
