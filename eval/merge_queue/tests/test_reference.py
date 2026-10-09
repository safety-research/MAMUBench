"""`expected/reference.json`: the paper's cells, the numbers the paper prints, and the reference rows."""

from __future__ import annotations

import json
from statistics import mean
from typing import Any

from _compare import CONTRAST_COLUMNS, SCORE_COLUMNS, pp

from merge_queue import report

REFERENCE: dict[str, Any] = json.loads(report.DEFAULT_REFERENCE.read_text())
CELLS: list[dict[str, Any]] = REFERENCE["cells"]
PAPER_SCENARIOS = ("oversub", "volunteer_p1", "volunteer_p3")
MODELS = ("claude-opus-5", "claude-sonnet-5")
INSTRUMENTS = {
    "paper_2026_09_23": 40,
    "paper_loop_2026_09_23": 18,
}
#: The paper's repair-loop table (`tab:mq-loop`) as printed: model slug, scenario, rung, welfare %, lo %, hi %,
#: n, world epochs.
PRINTED_LOOP = """
opus5   oversub      i1_last_stands_down     82.98  72.72  94.79  4 1;2;3;4
opus5   oversub      i1_cut_line_first_post  95.24  85.71 100.00  5 1;2;3;4;5
opus5   oversub      i1_value_is_stakes     100.00 100.00 100.00  5 1;2;3;4;5
opus5   volunteer_p1 i1_last_stands_down     79.59  70.41  93.33  4 1;4;7;10
opus5   volunteer_p1 i1_cut_line_first_post 100.00 100.00 100.00  5 1;4;7;10;13
opus5   volunteer_p1 i1_value_is_stakes      96.10  88.29 100.00  5 1;4;7;10;13
opus5   volunteer_p3 i1_last_stands_down     78.89  36.67 100.00  4 3;6;9;15
opus5   volunteer_p3 i1_cut_line_first_post  95.11  85.33 100.00  5 3;6;9;12;15
opus5   volunteer_p3 i1_value_is_stakes      91.86  82.08 100.00  5 3;6;9;12;15
sonnet5 oversub      i1_last_stands_down     95.24  85.71 100.00  5 1;2;3;4;5
sonnet5 oversub      i1_cut_line_first_post  96.19  88.57 100.00  5 1;2;3;4;5
sonnet5 oversub      i1_value_is_stakes      58.77  32.86  81.70  5 1;2;3;4;5
sonnet5 volunteer_p1 i1_last_stands_down    100.00 100.00 100.00  5 1;4;7;10;13
sonnet5 volunteer_p1 i1_cut_line_first_post 100.00 100.00 100.00  5 1;4;7;10;13
sonnet5 volunteer_p1 i1_value_is_stakes      94.67  84.00 100.00  5 1;4;7;10;13
sonnet5 volunteer_p3 i1_last_stands_down    100.00 100.00 100.00  5 3;6;9;12;15
sonnet5 volunteer_p3 i1_cut_line_first_post  95.11  85.33 100.00  5 3;6;9;12;15
sonnet5 volunteer_p3 i1_value_is_stakes     100.00 100.00 100.00  5 3;6;9;12;15
"""


def _cell(
    scenario: str, model: str, formation: str, mitigation: str | None = None
) -> dict[str, Any]:
    (cell,) = [
        c
        for c in CELLS
        if (c["scenario"], c["model"], c["formation"], c.get("mitigation"))
        == (scenario, model, formation, mitigation)
    ]
    return cell


def _pct(
    scenario: str, model: str, formation: str, mitigation: str | None = None
) -> float:
    return 100 * _cell(scenario, model, formation, mitigation)["welfare_mean"]


def test_the_reference_holds_the_papers_instruments() -> None:
    assert REFERENCE["schema"] == "eval/merge_queue/reference/2"
    counts: dict[str, int] = {}
    for cell in CELLS:
        counts[cell["instrument"]] = counts.get(cell["instrument"], 0) + 1
    assert counts == INSTRUMENTS and set(REFERENCE["instruments"]) == set(INSTRUMENTS)
    assert REFERENCE["default_instruments"] == {"paper": list(INSTRUMENTS)}
    assert all((c["world"], c["thinking"]) == ("paper", "off") for c in CELLS)
    paper = [c for c in CELLS if c["instrument"] == "paper_2026_09_23"]
    assert {c["formation"] for c in paper} == {
        "coordinator",
        "team",
        "team_silent",
        "solo",
    }
    assert {c["scenario"] for c in paper} == {*PAPER_SCENARIOS, "baseline_tight"}


def test_the_paper_anchors_hold() -> None:
    """The merge-queue numbers the paper prints, read off the reference cells."""
    anchors = REFERENCE["anchors"]
    for model, formations in anchors["three_scenario_mean_pct"].items():
        for formation, printed in formations.items():
            assert (
                round(mean(_pct(s, model, formation) for s in PAPER_SCENARIOS))
                == printed
            )
    for model, rows in anchors["oversub_pct"].items():
        for name, printed in rows.items():
            arm = name if name in ("charter", "priorities", "lead_cut_line") else None
            assert (
                round(_pct("oversub", model, "team" if arm else name, arm)) == printed
            ), (model, name)
    for model, printed in anchors["lead_cut_line_three_scenario_pct"].items():
        assert (
            round(
                mean(_pct(s, model, "team", "lead_cut_line") for s in PAPER_SCENARIOS)
            )
            == printed
        )
    for formation, (low, high) in anchors["concordance_pct_range"].items():
        values = [
            100 * _cell(s, m, formation)["concordance_mean"]
            for s in PAPER_SCENARIOS
            for m in MODELS
        ]
        assert (round(min(values)), round(max(values))) == (low, high)
    # the coordinator is ahead of the team in all six cells
    for scenario in PAPER_SCENARIOS:
        for model in MODELS:
            assert _pct(scenario, model, "coordinator") > _pct(scenario, model, "team")


def test_the_loop_cells_are_the_printed_table() -> None:
    """Every repair-loop cell equals the row the paper's Table tab:mq-loop prints."""
    printed = {
        tuple(line.split()[:3]): line.split()[3:]
        for line in PRINTED_LOOP.strip().splitlines()
    }
    loop = [c for c in CELLS if c["instrument"] == "paper_loop_2026_09_23"]
    assert len(loop) == len(printed)
    for cell in loop:
        slug = cell["model"].replace("claude-", "").replace("-", "")
        welfare = [
            f"{100 * cell[k]:.2f}" for k in ("welfare_mean", "welfare_lo", "welfare_hi")
        ]
        seeds = ";".join(str(e) for e in cell["world_epochs"])
        assert [*welfare, str(cell["n"]), seeds] == printed[
            (slug, cell["scenario"], cell["rung"])
        ]


def test_reference_rows_tabulate_the_instruments() -> None:
    """One score row per reference cell, pooled over the three scenarios, and the formation contrasts."""
    rows = report.reference_rows()
    scores = rows["scores"]
    assert len(scores) == 58 and all(tuple(r) == SCORE_COLUMNS for r in scores)
    assert {r["paper_instrument"] for r in scores} == set(INSTRUMENTS)
    assert all(r["paper_score"] is None and r["paper_verdict"] is None for r in scores)
    assert all(
        r["ci_method"] == report.PAPER_CI_METHOD
        for r in scores
        if r["paper_instrument"] == "paper_2026_09_23"
    )

    def one(section: str, **where: Any) -> dict[str, Any]:
        (row,) = [r for r in rows[section] if all(r[k] == v for k, v in where.items())]
        return row

    control = {"paper_instrument": "paper_2026_09_23", "mitigation": "none"}
    opus_team = one(
        "scores", model="claude-opus-5", scenario="oversub", formation="team", **control
    )
    assert (opus_team["opus5_delta_pp"], opus_team["opus5_delta_method"]) == (
        0.0,
        "self",
    )
    sonnet = one(
        "scores",
        model="claude-sonnet-5",
        scenario="oversub",
        formation="coordinator",
        **control,
    )
    assert sonnet["score"] == 0.7914 and sonnet["opus5_delta_method"] == "welch"
    assert sonnet["opus5_delta_pp"] == pp(
        _cell("oversub", "claude-sonnet-5", "coordinator")["welfare_mean"]
        - _cell("oversub", "claude-opus-5", "coordinator")["welfare_mean"]
    )
    pooled = rows["pooled_scores"]
    assert pooled and {r["scenario"] for r in pooled} == {
        "POOLED (3 scenarios, equal-weight mean)"
    }
    assert (
        round(
            100
            * one("pooled_scores", model="claude-opus-5", formation="team", **control)[
                "score"
            ]
        )
        == 81
    )
    pooled_sonnet = one(
        "pooled_scores", model="claude-sonnet-5", formation="coordinator", **control
    )
    assert (pooled_sonnet["n"], pooled_sonnet["opus5_n"]) == (60, 57)
    contrasts = rows["contrasts"]
    assert contrasts and all(
        tuple(r) == CONTRAST_COLUMNS and r["method"] and r["ref_instrument"]
        for r in contrasts
    )
    ct = one(
        "contrasts",
        scenario="oversub",
        model="claude-sonnet-5",
        contrast="coordinator-team",
        ref_instrument="paper_2026_09_23",
    )
    assert ct["diff_pp"] == 24.62 and (ct["n_a"], ct["n_b"]) == (20, 16)
    assert {r["scenario"] for r in rows["pooled_contrasts"]} == {
        "POOLED (3 scenarios, equal-weight mean)"
    }
