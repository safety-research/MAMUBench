"""Shared helpers for the clinic tests: fake mornings on either harness, and episode rows for the readers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from clinic import record
from clinic import run as run_mod


@pytest.fixture(autouse=True)
def quiet_sim(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_SIM_DISPLAY", "none")


def write_scripts(path: Path, scripts: dict[str, list[dict[str, Any]]]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    for seat, turns in scripts.items():
        (path / f"{seat}.json").write_text(json.dumps(turns))
    return path


def run_fake(
    runs_root: Path,
    *,
    board: str = "warfarin_inr_split",
    formation: str = "coordinator",
    scripts: Path | None = None,
    epoch0: int = 1,
    extra: tuple[str, ...] = (),
) -> int:
    """One fake-pi morning (`run.py --fake-pi`); an unscripted desk idles, so the morning creeps to its horizon."""
    argv = ["--board", board, "--formation", formation, "--episodes", "1"]
    argv += ["--epoch0", str(epoch0), "--fake-pi", "--runs-root", str(runs_root)]
    if scripts is not None:
        argv += ["--fake-scripts", str(scripts)]
    return run_mod.main([*argv, *extra])


def run_sim(
    runs_root: Path, formation: str, *extra: str, board: str = "warfarin_inr_split"
) -> None:
    """One fake-model morning on the simulated harness (`run.py --harness sim --fake-model`)."""
    argv = ["--board", board, "--formation", formation, "--episodes", "1"]
    argv += ["--harness", "sim", "--fake-model", "--runs-root", str(runs_root)]
    assert run_mod.main([*argv, *extra]) == 0


def row(
    formation: str = "team",
    instrument: str | None = "standard",
    *,
    scenario: str = "warfarin_inr_split",
    model: str = "claude-opus-5",
    epoch: int = 1,
    mitigation: str = "none",
    joint: int = 4,
    met: int = 5,
    contests: int = 6,
    **extra: Any,
) -> dict[str, Any]:
    """A harness-clean simulated-harness episode row at the horizon, with the columns the readers use."""
    return {
        "run": f"{scenario}_{formation}_{model}_{mitigation}_{instrument}_{epoch}",
        "scenario": scenario,
        "formation": formation,
        "model": model,
        "mitigation": mitigation,
        "epoch": epoch,
        "harness": "sim",
        "instrument": instrument,
        "ended": "world horizon reached",
        "error_turns": 0,
        "crashed": "",
        "retired_physics": False,
        "reached_horizon": 1,
        "unmet": 0,
        "stranded_callers_live": 0,
        "endstate": "horizon",
        "contests": contests,
        "contests_met": met,
        "contests_joint": joint,
        "holders_dropped": 0,
        **extra,
    }


def paper_rows(model: str) -> list[dict[str, Any]]:
    """Every episode of record of `model` (all three sets) as a run's episode rows."""
    return [
        row(
            r.formation,
            r.instrument,
            scenario=r.scenario,
            model=model,
            epoch=r.epoch,
            mitigation=r.mitigation,
            joint=r.joint,
            met=r.met,
            contests=r.n_contests,
        )
        for r in record.load()
        if r.model == model
    ]
