"""Shared helpers for the api_key tests: offline invocations of `run.main` and a typed tolerance check."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from api_key import run as run_mod


def write_scripts(path: Path, scripts: dict[str, list[dict[str, Any]]]) -> Path:
    """Per-seat FakePi scripts (`<seat>.json`), see `_harness/fake_pi.py` for the turn format."""
    path.mkdir(parents=True, exist_ok=True)
    for seat, turns in scripts.items():
        (path / f"{seat}.json").write_text(json.dumps(turns))
    return path


def run_fake(
    runs_root: Path,
    *,
    scenario: str = "stakes_100",
    formation: str = "team",
    scripts: Path | None = None,
    rounds_max: int = 3,
    epoch0: int = 1,
    extra: tuple[str, ...] = (),
) -> int:
    """Invoke `run.main` in fake-pi mode (no model, no key, localhost only)."""
    argv = [
        "--scenario",
        scenario,
        "--formation",
        formation,
        "--episodes",
        "1",
        "--epoch0",
        str(epoch0),
        "--fake-pi",
        "--rounds-max",
        str(rounds_max),
        "--runs-root",
        str(runs_root),
        *extra,
    ]
    if scripts is not None:
        argv += ["--fake-scripts", str(scripts)]
    return run_mod.main(argv)


def run_sim(runs_root: Path, *argv: str) -> int:
    """Invoke `run.main` on the simulated harness with the fake model (`stakes_100`, one epoch by default).

    Callers set `EVAL_SIM_DISPLAY=none` (the driver's live display off).
    """
    return run_mod.main(
        ["--scenario", "stakes_100", "--harness", "sim", "--fake-model"]
        + ["--runs-root", str(runs_root), *argv]
    )


def close(
    got: Sequence[float] | float, want: Sequence[float] | float, tol: float = 1e-9
) -> bool:
    """Element-wise `|got - want| <= tol` (a typed tolerance check for strict pyright)."""
    a = [got] if isinstance(got, (int, float)) else list(got)
    b = [want] if isinstance(want, (int, float)) else list(want)
    return len(a) == len(b) and all(
        abs(x - y) <= tol for x, y in zip(a, b, strict=True)
    )
