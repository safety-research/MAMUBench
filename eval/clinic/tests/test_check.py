"""`check.py`'s verdicts: a run's cells and pools banded against the paper's intervals.

PASS inside the paper's interval, WARN outside it with overlapping intervals, MISS disjoint, SKIP without a
reference; a scenario with fewer than 2 mornings (or pairs) is banded with a Wilson interval over its contests (or
reads WARN), and the paper's two-decimal intervals are read with half a rounding unit of slack.
"""

from __future__ import annotations

import json
import math
from typing import Any

from _stats import band

from clinic import check, report
from clinic.metric import Morning
from clinic.reference import PaperReference, paper_band
from clinic.tests.conftest import row

OPUS = "claude-opus-5"
BOARD = "warfarin_inr_split"
REFERENCE: dict[str, Any] = json.loads(check.DEFAULT_REFERENCE.read_text())


def _verdicts(rows: list[dict[str, Any]], draws: int = 50) -> list[tuple[str, str]]:
    report.apply_paper_rules(rows)
    return check.check(report.cell_rows(rows, draws=draws), REFERENCE)


def _team(joints: tuple[int, ...], *, model: str = OPUS) -> list[dict[str, Any]]:
    return [
        row("team", "standard", epoch=e, model=model, joint=j)
        for e, j in enumerate(joints, start=1)
    ]


def test_a_run_is_banded_against_every_set_holding_its_cell_and_pool() -> None:
    def statuses(verdicts: list[tuple[str, str]], prefix: str) -> list[str]:
        return [s for s, line in verdicts if line.startswith(f"{s} {prefix}")]

    near = _verdicts(_team((3, 3, 4, 3, 3, 4, 3, 3, 4, 3)), draws=200)
    # the corpus (episodes 1-20) and the arms' episode-1-10 control, per scenario and pooled
    assert statuses(near, f"{BOARD} team {OPUS}") == ["PASS", "PASS"]
    assert statuses(near, f"POOLED {OPUS} team scattered (1 of 12 scenarios)") == [
        "PASS",
        "PASS",
    ]
    assert statuses(_verdicts(_team((0,) * 10), draws=200), f"{BOARD} team {OPUS}") == [
        "MISS",
        "MISS",
    ]
    # the episode-1-10 controls are a reference only for a run within episodes 1-10
    beyond = [row("team", "standard", epoch=e) for e in (1, 15)]
    assert not any("mitigations_e1_10" in line for _, line in _verdicts(beyond))
    assert _verdicts(_team((4,), model="some-model")) == [
        ("SKIP", f"SKIP {BOARD} team some-model: no reference cell")
    ]
    status, line = check.compare_paper(
        "x",
        (1, 2, 50.0, 40.0, 60.0),
        {"joint": 1, "n": 2, "joint_pct": 50.0, "lo": math.nan, "hi": math.nan},
        "ref",
    )
    assert status == "SKIP" and "not recoverable" in line


def test_one_morning_per_scenario_is_banded_with_a_wilson_interval() -> None:
    """The within-scenario bootstrap collapses on one morning: a perfect 6/6 is WARN, not MISS."""
    perfect = _verdicts([row("coordinator", "hero", joint=6)])
    assert perfect and all(s == "WARN" for s, _ in perfect)
    notes = (check.WILSON_NOTE, check.POOLED_WILSON_NOTE)
    assert all(line.endswith(notes) and "[61.0, 100.0]" in line for _, line in perfect)
    # far outside the paper's interval still MISSes: 0/6 has Wilson [0.0, 39.0]
    assert {s for s, _ in _verdicts([row("coordinator", "hero", joint=0)])} == {"MISS"}
    two = [row("coordinator", "hero", epoch=e, joint=6) for e in (1, 2)]
    assert not any(line.endswith(notes) for _, line in _verdicts(two))
    # the pooled fallback averages the scenarios' Wilson bounds, so it holds the scenario-averaged point
    subset = {
        "warfarin_inr_plain": [Morning(epoch=1, joint=6, met=6, n=6)],
        BOARD: [Morning(epoch=e, joint=4, met=4, n=6) for e in range(1, 11)],
    }
    point = (100.0 + 400 / 6) / 2
    lo, hi = check.scenario_wilson(subset)
    assert lo <= point <= hi
    pooled_lo, pooled_hi = check.contest_interval(46, 66)
    assert (
        not pooled_lo <= point <= pooled_hi
    )  # Wilson over the pooled contests would not


def test_a_one_pair_paired_contrast_reads_warn_not_miss() -> None:
    """One matched episode per scenario: the paired bootstrap cannot vary, so the contrast is unresolved."""
    reference = PaperReference(REFERENCE)

    def paired(epochs: tuple[int, ...]) -> dict[str, Any]:
        rows = [
            row(formation, instrument, epoch=e, joint=joint)
            for e in epochs
            for formation, instrument, joint in (
                ("team_silent", "standard", 6),
                ("team", "standard", 0),
            )
        ]
        report.apply_paper_rules(rows)
        (only,) = report.paired_rows(rows, reference=reference, draws=50)
        return only

    one = paired((1,))
    assert (one["n_pairs"], one["run_degenerate"]) == (1, True)
    assert (one["lo_pp"], one["hi_pp"]) == (100.0, 100.0)  # no interval of its own
    assert one["paper_verdict"] == "WARN"  # disjoint from the paper's, yet unresolved
    ((status, line),) = check.check_paired([one])
    assert status == "WARN" and line.endswith(check.PAIRED_DEGENERATE_NOTE)
    two = paired((1, 2))  # two pairs per scenario: the same disjoint contrast is a MISS
    assert (two["n_pairs"], two["run_degenerate"], two["paper_verdict"]) == (
        2,
        False,
        "MISS",
    )
    assert check.PAIRED_DEGENERATE_NOTE not in check.check_paired([two])[0][1]


def test_a_run_equal_to_the_paper_passes_despite_the_stored_rounding() -> None:
    """The reference stores 66.67 for 200/3: a run of exactly 200/3 is inside, not disjoint."""
    assert band(200 / 3, (200 / 3, 200 / 3), (66.67, 66.67)) == "MISS"
    assert paper_band(200 / 3, (200 / 3, 200 / 3), (66.67, 66.67)) == "PASS"
    assert paper_band(0.6667, (0.6667, 0.6667), (0.6667, 0.6667), unit=0.01) == "PASS"
    assert paper_band(66.68, (66.68, 66.68), (66.67, 66.67)) == "MISS"
    sonnet = "claude-sonnet-5"
    pool = PaperReference(REFERENCE).pool(
        "silent_e1_5", sonnet, "team_silent", "none", "scattered", [BOARD]
    )
    assert pool is not None and (pool["lo"], pool["hi"]) == (66.67, 66.67)
    rows = [row("team_silent", "standard", epoch=e, model=sonnet) for e in (1, 2)]
    pooled = [line for _, line in _verdicts(rows) if "POOLED" in line]
    assert pooled and all(line.startswith("PASS POOLED") for line in pooled), pooled
