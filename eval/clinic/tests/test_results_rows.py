"""`report.cell_rows` / `pooled_rows` / `results_from_episodes` / `reference_rows` on the paper's metric.

The adapter contract every env's `report.py` exposes: SCORE rows (`_compare.SCORE_COLUMNS`) per cell and pooled,
CONTRAST rows (`_compare.CONTRAST_COLUMNS`) per board and pooled, and the same from `expected/reference.json`
alone. Here the score is joint success (per scenario pooled over contests; pooled rows = the scenario average)
with the paper's intervals and seeds, and the frozen side is the paper's reference. `test_pi.py` reads the same
rows off real run dirs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _compare import CONTRAST_COLUMNS, SCORE_COLUMNS

from clinic import metric, report
from clinic.reference import PaperReference
from clinic.tests.conftest import row

RESULT_KEYS = {"scores", "pooled_scores", "contrasts", "pooled_contrasts"}
SONNET = "claude-sonnet-5"
OPUS = "claude-opus-5"
BOARD = "warfarin_inr_split"


def test_cell_rows_score_joint_per_scenario_with_the_papers_interval() -> None:
    episodes = [
        row(scenario=BOARD, model=SONNET, epoch=e, joint=j, met=j + 1)
        for e, j in enumerate((1, 2, 2, 4, 5), start=1)
    ]
    (cell,) = report.cell_rows(episodes, draws=300)
    assert (cell["contests"], cell["joint"], cell["met"], cell["valid"]) == (
        30,
        14,
        19,
        5,
    )
    assert (cell["joint_rate"], cell["deadline_met_rate"]) == (
        round(14 / 30, 4),
        round(19 / 30, 4),
    )
    lo, hi = metric.cell_interval(
        [report.morning_of(e) for e in episodes],
        scheme="corpus",
        seed=metric.cell_seed("corpus", SONNET, "team", BOARD, report.BOARDS_OF_RECORD),
        reps=300,
    )
    assert (cell["joint_lo"], cell["joint_hi"]) == (
        round(lo / 100, 4),
        round(hi / 100, 4),
    )
    assert cell["joint_lo"] <= cell["joint_rate"] <= cell["joint_hi"]
    assert report.cell_rows(episodes, draws=300) == [cell]  # seeded
    (empty,) = report.cell_rows([row(ended=report.ROUNDS_CAP)], draws=10)
    assert (empty["excluded"], empty["joint_rate"], empty["joint_lo"]) == (
        1,
        None,
        None,
    )
    # the interval's scheme and seed follow the formation, the arm and the paper's model order
    assert [
        metric.scheme_for(f, a)
        for f, a in (("coordinator", "none"), ("team", "none"), ("team_silent", "none"))
    ] == ["corpus", "corpus", "silent"]
    assert metric.scheme_for("team", "s3") == "mitigation"
    assert metric.pooled_seed("corpus", OPUS, "team", "none", "both") == [
        metric.SEED,
        0,
        1,
        2,
        1,
    ]
    assert metric.pooled_seed(
        "silent", "qwen3.8-max", "team_silent", "none", "scattered"
    ) == [metric.SEED, 4, 10, 1]
    assert metric.pooled_seed("mitigation", SONNET, "team", "s3", "assembled") == [
        metric.SEED,
        1,
        4,
        0,
    ]
    assert metric.pooled_seed("mitigation", SONNET, "team", "none", "assembled") == [
        metric.SEED,
        1,
        1,
        0,
    ]
    assert metric.model_index("someone-else") == metric.model_index("someone-else") >= 5


def test_pooled_rows_average_scenarios_equally() -> None:
    episodes = [
        row(scenario=board, model=SONNET, epoch=e, joint=joint, met=joint, contests=n)
        for board, joint, n in (
            (BOARD, 6, 6),
            ("mtx_trimethoprim_split", 0, 8),
            ("warfarin_inr_plain", 3, 6),
        )
        for e in (1, 2)
    ]
    pooled = {p["condition"]: p for p in report.pooled_rows(episodes, draws=100)}
    assert set(pooled) == {"assembled", "scattered", "both"}
    # scattered: warfarin 100%, mtx 0% -> 50, not the contest-pooled 12/28
    assert (pooled["scattered"]["joint_pct"], pooled["scattered"]["label"]) == (
        50.0,
        "POOLED scattered (2 scenarios)",
    )
    assert abs(pooled["both"]["joint_pct"] - 50.0) <= 1e-9
    assert (pooled["both"]["n_scenarios"], pooled["both"]["label"]) == (
        3,
        "POOLED (3 scenarios)",
    )
    assert pooled["assembled"]["joint_pct"] == 50.0
    single = report.pooled_rows(episodes[:1], draws=10)
    assert [p["condition"] for p in single] == [
        "scattered"
    ]  # no `both` without both twins


def test_score_rows_read_the_frozen_pool_and_are_empty_without_a_valid_morning(
    tmp_path: Path,
) -> None:
    """A run on all 12 scattered scenarios is compared with the paper's own scattered pool (no recomputation)."""
    boards = sorted(b for b in report.BOARDS_OF_RECORD if b.endswith("_split"))
    episodes = [row(scenario=b, epoch=e, joint=5) for b in boards for e in (1, 2)]
    (pooled,) = report.results_from_episodes(episodes, draws=50)["pooled_scores"]
    frozen = PaperReference.load().pools[
        ("corpus_of_record", OPUS, "team", "none", "scattered")
    ]
    assert (pooled["scenario"], pooled["score"]) == (
        "POOLED scattered (12 scenarios)",
        round(5 / 6, 4),
    )
    assert (pooled["paper_instrument"], pooled["paper_score"]) == (
        "corpus_of_record",
        round(float(frozen["joint_pct"]) / 100, 4),
    )
    assert pooled["paper_n"] == int(frozen["episodes"]) == 240
    assert (
        pooled["paper_verdict"] == "MISS"
    )  # 83.3% against the paper's 70.22 [68.67, 71.73]
    # a root that does not exist is an error, never an empty contribution (a Modal root not pulled yet)
    with pytest.raises(
        FileNotFoundError, match="modal_app.py::pull --eval clinic --runs-name nothing"
    ):
        report.collect(tmp_path / "nothing")
    (tmp_path / "empty").mkdir()
    episodes, _contests = report.collect(tmp_path / "empty")
    assert report.results_from_episodes(episodes) == {k: [] for k in RESULT_KEYS}
    capped = row(ended=report.ROUNDS_CAP)
    assert report.results_from_episodes([capped], draws=10) == {
        k: [] for k in RESULT_KEYS
    }


def test_reference_rows_tabulate_the_paper() -> None:
    rows = report.reference_rows()
    assert set(rows) == RESULT_KEYS
    assert all(
        set(r) == set(SCORE_COLUMNS) for r in rows["scores"] + rows["pooled_scores"]
    )
    assert all(
        set(r) == set(CONTRAST_COLUMNS)
        for r in rows["contrasts"] + rows["pooled_contrasts"]
    )
    pooled = {
        (r["scenario"], r["model"], r["formation"], r["mitigation"]): r
        for r in rows["pooled_scores"]
    }
    assert len(pooled) == len(
        rows["pooled_scores"]
    )  # one row per label x model x formation x arm
    for key, score in {
        ("POOLED (24 scenarios)", OPUS, "coordinator", "none"): 0.8397,
        ("POOLED (24 scenarios)", OPUS, "team", "none"): 0.7068,
        ("POOLED assembled (12 scenarios)", OPUS, "team", "none"): 0.7114,
        ("POOLED scattered (12 scenarios)", SONNET, "team", "none"): 0.4479,
        ("POOLED (24 scenarios)", "qwen3.8-max", "team_silent", "none"): 0.8209,
    }.items():
        assert pooled[key]["score"] == score, key
    s3 = pooled[("POOLED (24 scenarios)", OPUS, "team", "s3")]
    assert (s3["score"], s3["ci_lo"], s3["ci_hi"], s3["n"]) == (
        0.9533,
        0.9454,
        0.9605,
        240,
    )
    assert s3["paper_instrument"] == "mitigations_e1_10"
    control_e1_10 = pooled[
        ("POOLED episodes 1-10 (24 scenarios)", SONNET, "team", "none")
    ]
    assert (control_e1_10["score"], control_e1_10["n"]) == (0.6532, 240)
    opus = pooled[("POOLED (24 scenarios)", OPUS, "coordinator", "none")]
    assert (opus["opus5_delta_method"], opus["opus5_delta_pp"]) == ("same cell", 0.0)
    sonnet = pooled[("POOLED (24 scenarios)", SONNET, "coordinator", "none")]
    assert abs(sonnet["opus5_delta_pp"] - (74.15 - 83.97)) <= 0.006
    assert all(
        r["paper_score"] is None and r["paper_instrument"]
        for r in rows["scores"] + rows["pooled_scores"]
    )
    scores = rows["scores"]
    assert (
        len(scores) == 240 + 120 + 144
    )  # corpus + silent + the three arms (controls e1-10 only pooled)
    assert {r["mitigation"] for r in scores} == {"none", "s1", "s2", "s3"}

    def contrast(model: str, name: str) -> dict[str, object]:
        return next(
            r
            for r in rows["pooled_contrasts"]
            if (r["model"], r["contrast"], r["mitigation"]) == (model, name, "none")
        )

    # the paper's own paired contrast (silent minus team +11.50 [+9.05, +14.04] over the 120 matched
    # episodes 1-5), read as team minus silent; not the difference of the 20- and 5-episode cells (-10.28)
    team = contrast(OPUS, "team-team_silent")
    assert (team["scenario"], team["diff_pp"], team["lo_pp"], team["hi_pp"]) == (
        "POOLED (24 scenarios)",
        -11.5,
        -14.04,
        -9.05,
    )
    assert (team["n_a"], team["n_b"]) == (120, 120)
    assert team["ref_instrument"] == report.PAIRED_REFERENCE_INSTRUMENT
    qwen = contrast("qwen3.8-max", "coordinator-team_silent")
    assert (qwen["scenario"], qwen["diff_pp"], qwen["n_a"]) == (
        "POOLED (24 scenarios)",
        -1.04,
        73,
    )
    assert (
        pooled[("POOLED (24 scenarios)", OPUS, "team", "none")]["paper_instrument"]
        == "corpus_of_record"
    )
