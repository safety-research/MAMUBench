"""`rel_to_opus5`: a run's welfare against the Opus 5 baseline from ONE source, per cell and pooled.

The baseline is the frozen reference by default (the paper's n=20 cells) or, on request, the run's
own Opus 5 nights; the two are never mixed within a row, and a scenario the chosen source lacks
simply has no baseline.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from api_key.report import (
    BaselineSource,
    opus5_baselines,
    pooled_rows,
    with_relative_to_opus5,
)


def _cell(
    scenario: str, formation: str, model: str, mean: float, n: int
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "formation": formation,
        "model": model,
        "episodes": n,
        "clean": n,
        "welfare_mean": mean,
        "welfare_sd": 0.1,
        "welfare_lo": mean - 0.05,
        "welfare_hi": mean + 0.05,
    }


def _episodes(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cell in cells:
        for _ in range(int(cell["clean"])):
            rows.append(
                {
                    "scenario": cell["scenario"],
                    "formation": cell["formation"],
                    "model": cell["model"],
                    "welfare_over_opt": cell["welfare_mean"],
                    "ran_to_completion": True,
                    "roster_ok": True,
                    "error_turns": 0,
                    "crashed": "",
                    "met_jobs": 1,
                    "dms_sent": 0,
                    "nonconsensual_cross_principal": 0,
                }
            )
    return rows


REFERENCE: dict[str, Any] = {
    "cells": [
        {"scenario": "s1", "formation": "team", "model": "claude-opus-5", "mean": 0.5},
        {"scenario": "s2", "formation": "team", "model": "claude-opus-5", "mean": 0.25},
        {
            "scenario": "s1",
            "formation": "team",
            "model": "claude-sonnet-5",
            "mean": 0.1,
        },
    ]
}

#: A run with its own Opus 5 nights on s1 (0.8, above the reference's 0.5) but none on s2.
RUN: list[dict[str, Any]] = [
    _cell("s1", "team", "claude-opus-5", 0.8, 2),
    _cell("s1", "team", "claude-sonnet-5", 0.4, 2),
    _cell("s2", "team", "claude-sonnet-5", 0.25, 6),
]


def test_the_reference_is_the_default_baseline_and_run_nights_never_override_it() -> (
    None
):
    cells = with_relative_to_opus5(RUN, REFERENCE)
    by = {(c["scenario"], c["model"]): c for c in cells}
    # the run's own Opus 5 cell (0.8) is NOT substituted for the frozen 0.5
    assert by[("s1", "claude-sonnet-5")]["opus5_source"] == "reference"
    assert by[("s1", "claude-sonnet-5")]["rel_to_opus5"] == 0.8
    assert by[("s1", "claude-opus-5")]["opus5_source"] == "reference"
    assert by[("s1", "claude-opus-5")]["rel_to_opus5"] == 1.6
    assert by[("s2", "claude-sonnet-5")]["opus5_source"] == "reference"
    pooled = {r["model"]: r for r in pooled_rows(_episodes(RUN), cells)}
    sonnet = pooled["claude-sonnet-5"]
    # run mean = (2*0.4 + 6*0.25)/8 = 0.2875; baseline = (2*0.5 + 6*0.25)/8 = 0.3125
    assert sonnet["welfare_mean"] == 0.2875
    assert sonnet["opus5_baseline"] == 0.3125
    assert sonnet["rel_to_opus5"] == round(0.2875 / 0.3125, 3)
    assert sonnet["opus5_source"] == "reference"
    assert sonnet["opus5_scenarios"] == 2 and sonnet["scenarios"] == 2


def test_a_run_baseline_uses_only_the_runs_own_opus5_nights() -> None:
    cells = with_relative_to_opus5(RUN, REFERENCE, "run")
    by = {(c["scenario"], c["model"]): c for c in cells}
    assert by[("s1", "claude-sonnet-5")]["opus5_source"] == "run"
    assert by[("s1", "claude-sonnet-5")]["rel_to_opus5"] == 0.5
    assert by[("s1", "claude-opus-5")]["rel_to_opus5"] == 1.0
    # s2 has no Opus 5 night in the run: the reference's 0.25 is NOT substituted
    assert by[("s2", "claude-sonnet-5")]["opus5_baseline"] is None
    assert by[("s2", "claude-sonnet-5")]["opus5_source"] is None
    assert by[("s2", "claude-sonnet-5")]["rel_to_opus5"] is None
    pooled = {r["model"]: r for r in pooled_rows(_episodes(RUN), cells)}
    sonnet = pooled["claude-sonnet-5"]
    # the headline still pools every clean night ...
    assert sonnet["welfare_mean"] == 0.2875 and sonnet["scenarios"] == 2
    # ... but the ratio compares like with like: s1's nights (0.4) over s1's run baseline (0.8)
    assert sonnet["opus5_scenarios"] == 1
    assert sonnet["opus5_baseline"] == 0.8
    assert sonnet["rel_to_opus5"] == 0.5
    assert sonnet["opus5_source"] == "run"
    opus = pooled["claude-opus-5"]
    assert opus["rel_to_opus5"] == 1.0 and opus["opus5_source"] == "run"


def test_sources_are_never_mixed() -> None:
    assert set(opus5_baselines(RUN, REFERENCE, "reference")) == {
        ("s1", "team"),
        ("s2", "team"),
    }
    assert opus5_baselines(RUN, REFERENCE, "run") == {("s1", "team"): (0.8, "run")}
    assert opus5_baselines(RUN, None, "reference") == {}
    with pytest.raises(ValueError, match="unknown baseline source"):
        opus5_baselines(RUN, REFERENCE, cast(BaselineSource, "bogus"))
