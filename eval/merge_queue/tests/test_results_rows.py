"""The readout's SCORE and CONTRAST rows: the contract columns and the reference numbers each row carries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _compare import CONTRAST_COLUMNS, SCORE_COLUMNS, pp
from _harness.readout import within_epochs

from merge_queue import report
from merge_queue.tests.release_layout import FIXTURES, write_run

OPUS, SONNET = "claude-opus-5", "claude-sonnet-5"
PAPER = "paper_2026_09_23"
EMPTY: dict[str, list[dict[str, Any]]] = {
    "scores": [],
    "pooled_scores": [],
    "contrasts": [],
    "pooled_contrasts": [],
}


def _rows(
    root: Path, max_epoch: int | None = None, **kw: Any
) -> dict[str, list[dict[str, Any]]]:
    """The readout's SCORE and CONTRAST rows of `root`'s clean episodes, as `report.py` builds them."""
    episodes = [r for r in report.collect(root) if within_epochs(r, max_epoch)]
    return report.results_from_episodes(
        episodes, report.Reference(report.load_reference()), **kw
    )


def _paper(scenario: str, formation: str, model: str) -> float:
    """The paper's formation cell's welfare (instrument `paper_2026_09_23`, no arm) of the frozen reference."""
    (cell,) = [
        c
        for c in json.loads(report.DEFAULT_REFERENCE.read_text())["cells"]
        if c["instrument"] == PAPER
        and (c["scenario"], c["formation"], c["model"]) == (scenario, formation, model)
        and "mitigation" not in c
    ]
    return float(cell["welfare_mean"])


def _by(rows: list[dict[str, Any]], **where: Any) -> dict[str, Any]:
    (match,) = [r for r in rows if all(r[k] == v for k, v in where.items())]
    return match


def test_rows_are_empty_without_a_clean_episode(tmp_path: Path) -> None:
    run_dir = write_run(tmp_path, "oversub", "team", OPUS, 1, 240, 240)
    (run_dir / "DONE.json").write_text(json.dumps({"infrastructure_pass": False}))
    assert _rows(tmp_path) == EMPTY
    assert report.reference_rows(tmp_path / "missing.json") == EMPTY


def test_rows_of_the_paper_runs_carry_the_contract_columns() -> None:
    results = _rows(FIXTURES, draws=50)
    assert all(
        tuple(r) == SCORE_COLUMNS for r in results["scores"] + results["pooled_scores"]
    )
    assert all(
        tuple(r) == CONTRAST_COLUMNS
        for r in results["contrasts"] + results["pooled_contrasts"]
    )
    # six clean cells (rule T drops the other two episodes), each read against the paper's cell of its arm
    assert len(results["scores"]) == 6 and results["pooled_scores"] == []
    for row in results["scores"]:
        assert row["env"] == "merge_queue" and row["unit"] == "episode"
        assert 0.0 <= row["ci_lo"] <= row["score"] <= row["ci_hi"] <= 1.0
        assert row["ci_method"] == report.PAPER_CI_METHOD
        assert row["paper_score"] is not None and row["paper_n"] >= 4
    steward = _by(results["scores"], scenario="volunteer_p1", formation="coordinator")
    assert steward["n"] == 1 and steward["score"] == round(190 / 230, 4)
    assert steward["paper_score"] == round(
        _paper("volunteer_p1", "coordinator", OPUS), 4
    )
    assert (steward["paper_n"], steward["paper_instrument"]) == (20, PAPER)
    assert (
        _by(results["scores"], mitigation="lead_cut_line")["paper_instrument"]
        == "paper_loop_2026_09_23"
    )
    contrast = _by(
        results["contrasts"], scenario="volunteer_p1", contrast="coordinator-team"
    )
    # the control arm's reference cells are the paper's formation cells
    assert (
        contrast["n_a"] == contrast["n_b"] == 1 and contrast["ref_instrument"] == PAPER
    )


def test_score_rows_read_the_papers_cells(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    # oversub coordinator Opus 5: 4 x 1.0 + 1 x 0.5 -> mean 0.9 (the paper's cell: n=17, 0.7918)
    for epoch, release in enumerate((240, 240, 240, 240, 120), start=1):
        write_run(root, "oversub", "coordinator", OPUS, epoch, release, 240)
    for epoch in range(1, 4):
        write_run(root, "oversub", "team", OPUS, epoch, 240, 240)
    # coordinator Sonnet 5 on the three reported scenarios -> the three-scenario pooled row
    for epoch, release in enumerate((240, 200, 240, 180), start=1):
        write_run(root, "oversub", "coordinator", SONNET, epoch, release, 240)
    for scenario in ("volunteer_p1", "volunteer_p3"):
        for epoch, release in enumerate((220, 260), start=1):
            write_run(root, scenario, "coordinator", SONNET, epoch, release, 260)
    results = _rows(root, draws=100)
    paper = _paper("oversub", "coordinator", OPUS)
    opus = _by(
        results["scores"], scenario="oversub", formation="coordinator", model=OPUS
    )
    assert (opus["n"], opus["score"], opus["ci_method"]) == (
        5,
        0.9,
        report.PAPER_CI_METHOD,
    )
    assert opus["paper_score"] == round(paper, 4) == 0.7918
    assert (opus["paper_n"], opus["paper_instrument"]) == (17, PAPER)
    assert opus["paper_delta_pp"] == pp(0.9 - paper)
    # check.py's band: the point is above the paper's bootstrap band, the run's own interval overlaps it
    assert opus["paper_verdict"] == "WARN"
    assert (opus["opus5_score"], opus["opus5_delta_method"]) == (
        opus["paper_score"],
        "welch",
    )
    team = _by(results["scores"], scenario="oversub", formation="team", model=OPUS)
    assert team["score"] == team["ci_hi"] == 1.0
    sonnet = _by(
        results["scores"], scenario="oversub", formation="coordinator", model=SONNET
    )
    assert (sonnet["paper_score"], sonnet["paper_n"]) == (0.7914, 20)
    assert (sonnet["opus5_score"], sonnet["opus5_n"]) == (0.7918, 17)
    assert sonnet["opus5_delta_pp"] == pp(sonnet["score"] - paper)
    pooled = _by(results["pooled_scores"], model=SONNET, formation="coordinator")
    assert (
        pooled["scenario"] == "POOLED (3 scenarios, equal-weight mean)"
        and pooled["n"] == 8
    )
    assert pooled["ci_method"] == report.PAPER_POOLED_CI_METHOD
    means = [
        _paper(s, "coordinator", SONNET)
        for s in ("oversub", "volunteer_p1", "volunteer_p3")
    ]
    assert abs(pooled["paper_score"] - sum(means) / 3) < 1e-4
    assert (pooled["paper_n"], pooled["paper_verdict"]) == (60, None)
    contrast = _by(
        results["contrasts"],
        scenario="oversub",
        model=OPUS,
        contrast="coordinator-team",
    )
    assert (contrast["n_a"], contrast["n_b"], contrast["ref_method"]) == (5, 3, "welch")
    assert contrast["ref_diff_pp"] == pp(paper - _paper("oversub", "team", OPUS))
    # `--max-epoch` caps the units at the scenario's seed
    capped = _rows(root, max_epoch=2, draws=50)["scores"]
    assert (
        _by(capped, scenario="oversub", formation="coordinator", model=OPUS)["n"] == 2
    )
    # the readout's own three-scenario row (summary.txt / summary.json) records the root's thinking level
    (summary_pooled,) = report.pooled_rows(report.collect(root))
    assert (summary_pooled["model"], summary_pooled["thinking"]) == (SONNET, "off")


def test_the_pooled_contrast_reference_covers_the_runs_scenarios_only(
    tmp_path: Path,
) -> None:
    """The reference is pooled over the scenarios the run's pooled row covers (baseline_tight never pools).

    A covered scenario the reference lacks leaves the pooled reference empty (no partial pooling).
    """

    def contrasts(
        scenarios: tuple[str, ...], reference: report.Reference | None = None
    ) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        root = tmp_path / "_".join(scenarios) / ("partial" if reference else "full")
        for scenario in scenarios:
            optimum = 240 if scenario == "oversub" else 260
            for epoch in (1, 2):
                write_run(
                    root, scenario, "coordinator", SONNET, epoch, optimum, optimum
                )
                write_run(root, scenario, "team", SONNET, epoch, optimum // 2, optimum)
        results = report.results_from_episodes(
            report.collect(root),
            reference or report.Reference(report.load_reference()),
            draws=50,
        )
        (pooled,) = results["pooled_contrasts"]
        assert pooled["contrast"] == "coordinator-team"
        return {r["scenario"]: r for r in results["contrasts"]}, pooled

    oversub = _paper("oversub", "coordinator", SONNET) - _paper(
        "oversub", "team", SONNET
    )
    p1 = _paper("volunteer_p1", "coordinator", SONNET) - _paper(
        "volunteer_p1", "team", SONNET
    )
    for scenarios in (("oversub",), ("oversub", "baseline_tight")):
        per_scenario, pooled = contrasts(scenarios)
        assert pooled["scenario"] == "POOLED (1 scenarios, equal-weight mean)"
        assert pooled["n_a"] == pooled["n_b"] == 2
        assert (
            pooled["ref_diff_pp"]
            == per_scenario["oversub"]["ref_diff_pp"]
            == pp(oversub)
            == 24.62
        )
        assert (pooled["ref_method"], pooled["ref_instrument"]) == (
            "normal (board-mean se), 1 scenarios",
            PAPER,
        )
    per_scenario, pooled = contrasts(("oversub", "volunteer_p1"))
    assert pooled["scenario"] == "POOLED (2 scenarios, equal-weight mean)"
    assert pooled["ref_method"] == "normal (board-mean se), 2 scenarios"
    assert pooled["ref_diff_pp"] == pp((oversub + p1) / 2)
    oversub_only = report.Reference(
        c for c in report.load_reference() if c["scenario"] == "oversub"
    )
    per_scenario, pooled = contrasts(("oversub", "volunteer_p1"), oversub_only)
    assert (
        per_scenario["oversub"]["ref_diff_pp"],
        per_scenario["volunteer_p1"]["ref_diff_pp"],
    ) == (24.62, None)
    assert (pooled["ref_diff_pp"], pooled["ref_method"], pooled["ref_instrument"]) == (
        None,
        None,
        None,
    )


def test_a_thinking_medium_run_meets_no_reference_cell(tmp_path: Path) -> None:
    """Every reference instrument ran thinking off."""
    for epoch, release in enumerate((220, 260, 220), start=1):
        write_run(
            tmp_path,
            "baseline_tight",
            "coordinator",
            SONNET,
            epoch,
            release,
            260,
            thinking="medium",
        )
    results = _rows(tmp_path, draws=50)
    (row,) = results["scores"]
    assert (row["paper_score"], row["paper_instrument"], row["opus5_score"]) == (
        None,
        None,
        None,
    )
    assert results["pooled_contrasts"] == []  # a single formation has no contrast
