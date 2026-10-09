"""The paper's paired silent-team contrasts: frozen in `expected/reference.json`, recomputed by `report.py`, banded by `check.py`.

The paper compares the silent team with the peer-to-peer team and the coordinator over the episodes both ran,
with a paired bootstrap (the paper's silent-team analysis, `boot_paired`, seeds `[20260908, model, comparison,
condition]`). The main text prints four of them (Opus 5 +11.5 [+9.0, +14.0], GPT-5.6-terra -3.2 [-5.1, -1.3],
Qwen3.8-max +4.4 [+2.0, +7.0] over 65 pairs, and the Qwen silent team against its low-reasoning coordinator with
scattered facts, +2.2 [-5.0, +8.9]). `fixtures/pinned_tables.json` (`paired`) holds the keys of the paper's own
comparisons table and the sha256 of its values.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from clinic import check, metric, record, report
from clinic.reference import PaperReference, paired_sides
from clinic.tests.conftest import paper_rows

PINNED: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "pinned_tables.json").read_text()
)["paired"]
OPUS = "claude-opus-5"
QWEN = "qwen3.8-max"
PAPER = PaperReference.load()


def _paper_episodes(model: str, formations: tuple[str, ...]) -> list[dict[str, Any]]:
    """The frozen control episodes of `model` as run rows: the silent team (1-5) and `formations` (1-20)."""
    rows = [
        r
        for r in paper_rows(model)
        if r["mitigation"] == "none" and r["formation"] in (*formations, "team_silent")
    ]
    report.apply_paper_rules(rows)
    return rows


def test_the_frozen_paired_rows_are_the_papers_comparisons_digit_for_digit() -> None:
    keys = [tuple(k) for k in PINNED["keys"]]
    assert len(keys) == 30 and set(PAPER.paired) == set(keys)
    rows: list[list[Any]] = []
    for key in keys:
        got = PAPER.paired[key]
        values = [got["paper_label"], str(got["n_scenarios"]), str(got["n_pairs"])]
        values += [
            f"{float(got[c]):.6f}"
            for c in (
                "silent_pct",
                "silent_lo",
                "silent_hi",
                "reference_pct",
                "reference_lo",
                "reference_hi",
                "diff_pp",
                "lo",
                "hi",
            )
        ]
        values += [str(got[c]) for c in ("silent_ahead", "reference_ahead", "ties")]
        rows.append([list(key), values])
        assert got["seed"] == metric.paired_seed(key[0], key[1], key[2])
    packed = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    assert hashlib.sha256(packed.encode()).hexdigest() == PINNED["sha256"]
    # the main text's four, as printed
    for (model, formation, condition), printed in {
        (OPUS, "team", "both"): (81.0, 69.5, 11.5, 9.0, 14.0),
        ("gpt-5.6-terra", "team", "both"): (63.4, 66.6, -3.2, -5.1, -1.3),
        (QWEN, "team", "both"): (80.9, 76.5, 4.4, 2.0, 7.0),
        (QWEN, "coordinator", "scattered"): (72.5, 70.3, 2.2, -5.0, 8.9),
    }.items():
        row = PAPER.paired[(model, formation, condition)]
        got = tuple(
            row[c] for c in ("silent_pct", "reference_pct", "diff_pp", "lo", "hi")
        )
        assert all(abs(g - p) <= 0.05 + 1e-9 for g, p in zip(got, printed, strict=True))
    assert PAPER.paired[(QWEN, "team", "both")]["n_pairs"] == 65


def test_the_paired_contrast_is_the_papers_boot_paired_on_all_or_some_scenarios() -> (
    None
):
    silent, team = paired_sides(record.load(), OPUS, "team")
    seed = metric.paired_seed(OPUS, "team", "both")
    full = metric.paired_contrast(silent, team, seed=seed)
    assert (round(full.diff, 2), round(full.lo, 2), round(full.hi, 2)) == (
        11.5,
        9.05,
        14.04,
    )
    assert (full.n_scenarios, full.n_pairs) == (24, 120)
    # team epochs 6-20 have no silent twin: dropping them changes nothing
    trimmed = {b: [m for m in ms if m.epoch <= 5] for b, ms in team.items()}
    assert metric.paired_contrast(silent, trimmed, seed=seed) == full
    none = metric.paired_contrast(
        silent, {"warfarin_inr_plain": [metric.Morning(9, 1, 1, 2)]}, seed=[1]
    )
    assert (none.n_pairs, none.n_scenarios) == (0, 0)
    with pytest.raises(ValueError, match="twice"):
        metric.paired_contrast(
            {"warfarin_inr_plain": [metric.Morning(1, 1, 1, 2)] * 2},
            {"warfarin_inr_plain": [metric.Morning(1, 1, 1, 2)]},
            seed=[1],
        )
    # a partial run is compared with the paper's statistic recomputed over its own scenarios
    frozen = PAPER.paired_contrast(OPUS, "team", "both")
    assert frozen is not None and (frozen["diff_pp"], len(frozen["boards"])) == (
        11.5,
        24,
    )
    boards = ["mtx_trimethoprim_split", "warfarin_inr_split"]
    subset = PAPER.paired_contrast(OPUS, "team", "scattered", boards[::-1])
    assert subset is not None and subset["boards"] == boards
    assert (subset["n_scenarios"], subset["n_pairs"], subset["held"]) == (2, 10, 12)
    want = metric.paired_contrast(
        {b: silent[b] for b in boards},
        {b: team[b] for b in boards},
        seed=metric.paired_seed(OPUS, "team", "scattered"),
        condition="scattered",
    )
    assert subset["diff_pp"] == round(want.diff, 2)
    assert PAPER.paired_contrast(OPUS, "team", "both", ["no_such_board_plain"]) is None
    assert PAPER.paired_contrast("some-model", "team", "both") is None


def test_report_reads_the_papers_contrasts_off_its_episodes_and_misses_a_run_off_them() -> (
    None
):
    episodes = _paper_episodes(OPUS, ("team", "coordinator"))
    rows = report.paired_rows(episodes)
    by = {(r["reference_formation"], r["condition"]): r for r in rows}
    assert set(by) == {
        (f, c) for f in ("team", "coordinator") for c in metric.CONDITIONS
    }
    both = by[("team", "both")]
    assert (both["diff_pp"], both["lo_pp"], both["hi_pp"]) == (11.5, 9.05, 14.04)
    assert (both["silent_pct"], both["reference_pct"], both["n_pairs"]) == (
        80.96,
        69.46,
        120,
    )
    assert (both["paper_diff_pp"], both["paper_verdict"]) == (11.5, "PASS")
    assert (both["paper_label"], both["paper_scenarios"]) == ("silent_minus_team", "24")
    coordinator = by[("coordinator", "both")]
    assert (coordinator["diff_pp"], coordinator["paper_diff_pp"]) == (-2.67, -2.67)
    verdicts = check.check_paired(rows)
    assert [s for s, _ in verdicts] == ["PASS"] * 6
    assert any(
        line.startswith(
            f"PASS PAIRED {OPUS} team_silent-team both (24 scenarios, 120 pairs)"
        )
        and "vs paper silent_minus_team +11.50 [+9.05, +14.04]" in line
        for _, line in verdicts
    )
    # a silent team that never books anyone: a MISS, and the pooled CONTRAST row is the paired one
    team_only = [r for r in episodes if r["formation"] != "coordinator"]
    for r in team_only:
        if r["formation"] == "team_silent":
            r["contests_joint"] = 0
    rows = report.paired_rows(team_only)
    both = next(r for r in rows if r["condition"] == "both")
    assert both["diff_pp"] < -60 and both["paper_verdict"] == "MISS"
    assert {s for s, _ in check.check_paired(rows)} == {"MISS"}
    results = report.results_from_episodes(team_only, draws=50)
    pooled = next(
        r for r in results["pooled_contrasts"] if r["contrast"] == "team-team_silent"
    )
    assert (pooled["scenario"], pooled["diff_pp"]) == (
        "POOLED (24 scenarios)",
        -both["diff_pp"],
    )
    assert (pooled["ref_diff_pp"], pooled["ref_lo_pp"], pooled["ref_hi_pp"]) == (
        -11.5,
        -14.04,
        -9.05,
    )
    assert pooled["method"] == metric.paired_method(50)
    assert pooled["ref_instrument"] == report.PAIRED_REFERENCE_INSTRUMENT
    # the per-scenario contrasts stay the frozen cells' differences
    assert {r["ref_method"] for r in results["contrasts"]} == {
        "difference of the frozen cells"
    }


def test_report_main_writes_paired_csv_and_check_main_prints_the_verdicts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    episodes = _paper_episodes(QWEN, ("team", "coordinator"))

    def collect(
        *_args: Any, **_kwargs: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return episodes, []

    monkeypatch.setattr(report, "collect", collect)
    monkeypatch.setattr(check, "collect", collect)
    root = tmp_path / "runs"
    root.mkdir()
    out = tmp_path / "out"
    assert report.main([str(root), "--out-dir", str(out), "--draws", "2000"]) == 0
    assert "paired silent-team contrasts (the paper's" in capsys.readouterr().out
    with (out / "paired.csv").open() as handle:
        paired = {(r["contrast"], r["condition"]): r for r in csv.DictReader(handle)}
    assert tuple(next(iter(paired.values()))) == report.PAIRED_COLUMNS
    team = paired[("team_silent-team", "both")]
    assert (team["diff_pp"], team["n_pairs"], team["paper_verdict"]) == (
        "4.44",
        "65",
        "PASS",
    )
    scattered = paired[("team_silent-coordinator", "scattered")]
    assert (scattered["diff_pp"], scattered["lo_pp"], scattered["hi_pp"]) == (
        "2.25",
        "-4.97",
        "8.89",
    )
    check.main([str(root)])
    assert (
        f"PASS PAIRED {QWEN} team_silent-team both (23 scenarios, 65 pairs)"
        in capsys.readouterr().out
    )
