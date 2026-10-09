"""`rows_from_episodes` / `reference_rows`: the readout's SCORE and CONTRAST rows over clean nights and the frozen reference.

Synthetic nights stand in for a runs root (the adapter's statistics are a function of the episode
rows `collect` returns); one small fabricated runs root exercises `main` end to end. The reference is the
paper's (`expected/reference.json`); every interval is the paper's 95% Student-t (`report.interval`).
"""

from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path
from typing import Any

import pytest
from _compare import CONTRAST_COLUMNS, SCORE_COLUMNS, clip01, pp
from _harness.readout import provider_error_note
from _stats import describe

from api_key import check as check_mod
from api_key import report
from api_key.scenarios import SCENARIOS
from api_key.scenarios.roster import roster_for_scenario

REFERENCE = report.load_reference()
REFS = report.reference_cells(REFERENCE)
SONNET = "claude-sonnet-5"
OPUS = "claude-opus-5"

#: (scenario, model, formation) -> clean nights. Two 4-seat scenarios and one 8-seat scenario.
NIGHTS: dict[tuple[str, str, str], list[float]] = {
    ("stakes_80", SONNET, "coordinator"): [0.5, 0.6, 0.7, 0.4],
    ("stakes_80", SONNET, "team"): [0.2, 0.3, 0.25, 0.1],
    ("stakes_80", SONNET, "team_silent"): [0.0, 0.05, 0.0, 0.02],
    ("stakes_100", SONNET, "coordinator"): [0.6, 0.5, 0.55],
    ("stakes_100", SONNET, "team"): [0.1, 0.2, 0.15],
    ("stakes_n8_240", SONNET, "coordinator"): [0.3, 0.4, 0.35, 0.45],
    ("stakes_n8_240", SONNET, "team"): [0.05, 0.1, 0.0, 0.08],
    ("stakes_80", OPUS, "coordinator"): [0.7, 0.8, 0.75],
    ("stakes_80", OPUS, "team"): [0.5, 0.45, 0.55],
}


def _night(
    scenario: str, model: str, formation: str, welfare: float, *, clean: bool = True
) -> dict[str, Any]:
    return {
        "scenario": scenario,
        "formation": formation,
        "model": model,
        "welfare_over_opt": welfare,
        "ran_to_completion": clean,
        "roster_ok": True,
        "error_turns": 0,
        "crashed": "",
        "met_jobs": 1,
        "dms_sent": 0,
        "nonconsensual_cross_principal": 0,
    }


def _episodes() -> list[dict[str, Any]]:
    rows = [
        _night(scenario, model, formation, welfare)
        for (scenario, model, formation), values in NIGHTS.items()
        for welfare in values
    ]
    # an unclean night in a scored cell, and a cell whose only night is unclean
    rows.append(_night("stakes_80", SONNET, "coordinator", 0.99, clean=False))
    rows.append(_night("stakes_130", SONNET, "team", 0.9, clean=False))
    return rows


def _results(draws: int = 40) -> dict[str, list[dict[str, Any]]]:
    return report.rows_from_episodes(_episodes(), REFERENCE, draws=draws)


def _check_statuses(episodes: list[dict[str, Any]]) -> dict[tuple[str, str, str], str]:
    """`(scenario | POOLED label, formation, model) -> status` from check.py's own lines."""
    statuses: dict[tuple[str, str, str], str] = {}
    for status, line in check_mod.check(report.cell_rows(episodes), REFERENCE):
        label = line.split(":", 1)[0].removeprefix(f"{status} ")
        pooled = re.fullmatch(r"POOLED (\S+) (\S+) \((\d+) scenarios\)", label)
        if pooled:
            model, formation, k = pooled.groups()
            statuses[(f"POOLED ({k} scenarios)", formation, model)] = status
        else:
            scenario, formation, model = label.split(" ")
            statuses[(scenario, formation, model)] = status
    return statuses


def test_rows_are_empty_without_clean_nights(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty: dict[str, list[dict[str, Any]]] = {
        "scores": [],
        "pooled_scores": [],
        "contrasts": [],
        "pooled_contrasts": [],
    }
    assert report.rows_from_episodes(report.collect(tmp_path), REFERENCE) == empty
    unclean = [_night("stakes_80", SONNET, "team", 0.5, clean=False)]
    assert report.rows_from_episodes(unclean, REFERENCE, draws=5) == empty
    # and neither CLI reads an empty root as a pass
    assert report.main([str(tmp_path)]) == 1
    assert check_mod.main([str(tmp_path)]) == 1
    assert "NOTHING CHECKED" in capsys.readouterr().out


def test_score_rows_carry_check_intervals_and_reference_deltas() -> None:
    results = _results()
    scores = results["scores"]
    assert all(list(row) == list(SCORE_COLUMNS) for row in scores)
    by = {(r["scenario"], r["model"], r["formation"]): r for r in scores}
    # every NIGHTS cell scores; the all-unclean cell does not
    assert set(by) == set(NIGHTS)
    row = by[("stakes_80", SONNET, "coordinator")]
    values = NIGHTS[("stakes_80", SONNET, "coordinator")]
    mean, sd, n = describe(values)
    assert row["env"] == "api_key" and row["unit"] == "night"
    assert row["n"] == 4  # the unclean 0.99 night is excluded
    assert row["score"] == round(mean, 4)
    lo, hi = clip01(report.interval(mean, sd, n))
    assert (row["ci_lo"], row["ci_hi"]) == (round(lo, 4), round(hi, 4))
    assert row["ci_method"] == "t95 (clipped)"
    paper = REFS[("stakes_80", "coordinator", SONNET)]
    assert row["paper_score"] == round(float(paper["mean"]), 4)
    assert row["paper_n"] == 20 and row["paper_instrument"] == "corpus_of_record"
    assert row["paper_delta_pp"] == pp(mean - float(paper["mean"]))
    opus = REFS[("stakes_80", "coordinator", OPUS)]
    assert row["opus5_score"] == round(float(opus["mean"]), 4)
    assert row["opus5_n"] == 20 and row["opus5_instrument"] == "corpus_of_record"
    assert row["opus5_delta_method"] == "welch"
    assert row["opus5_delta_pp"] == pp(mean - float(opus["mean"]))
    assert row["opus5_delta_lo_pp"] < row["opus5_delta_pp"] < row["opus5_delta_hi_pp"]
    # a clipped interval: the team_silent nights sit at zero
    silent = by[("stakes_80", SONNET, "team_silent")]
    assert silent["ci_lo"] == 0.0 and silent["ci_method"] == "t95 (clipped)"
    # the run's own Opus 5 cell is compared with the reference's Opus 5 cell (Welch, not self)
    opus_row = by[("stakes_80", OPUS, "coordinator")]
    assert opus_row["opus5_delta_method"] == "welch"
    assert opus_row["opus5_score"] == opus_row["paper_score"]


def test_pooled_score_rows_cover_every_scenario_and_each_cast_size() -> None:
    pooled = _results()["pooled_scores"]
    assert all(list(row) == list(SCORE_COLUMNS) for row in pooled)
    labels = {
        (m, f): [
            r["scenario"] for r in pooled if r["model"] == m and r["formation"] == f
        ]
        for m, f in {(r["model"], r["formation"]) for r in pooled}
    }
    assert labels[(SONNET, "coordinator")] == [
        "POOLED (3 scenarios)",
        "POOLED 4-seat (2 scenarios)",
        "POOLED 8-seat (1 scenarios)",
    ]
    assert labels[(OPUS, "team")] == [
        "POOLED (1 scenarios)",
        "POOLED 4-seat (1 scenarios)",
    ]
    assert (
        SCENARIOS["stakes_80"].n_seats == 4 and SCENARIOS["stakes_n8_240"].n_seats == 8
    )
    by = {(r["model"], r["formation"], r["scenario"]): r for r in pooled}
    every = by[(SONNET, "coordinator", "POOLED (3 scenarios)")]
    nights = [
        w
        for (_, m, f), ws in NIGHTS.items()
        if m == SONNET and f == "coordinator"
        for w in ws
    ]
    assert every["n"] == len(nights) == 11
    assert every["score"] == round(statistics.fmean(nights), 4)
    four = by[(SONNET, "coordinator", "POOLED 4-seat (2 scenarios)")]
    assert four["n"] == 7
    # the paper and Opus 5 cells pool over the same two scenarios with check.py's exact episode pooling
    paper_cells = [
        REFS[(s, "coordinator", SONNET)] for s in ("stakes_100", "stakes_80")
    ]
    opus_cells = [REFS[(s, "coordinator", OPUS)] for s in ("stakes_100", "stakes_80")]
    assert four["paper_score"] == round(
        report.pooled_stats(paper_cells, "mean", "sd", "n")[0], 4
    )
    assert four["paper_n"] == 40
    assert four["opus5_score"] == round(
        report.pooled_stats(opus_cells, "mean", "sd", "n")[0], 4
    )
    assert four["opus5_delta_method"] == "welch"
    assert four["opus5_delta_pp"] == pp(four["score"] - four["opus5_score"])


def test_score_rows_agree_with_check() -> None:
    episodes = _episodes()
    statuses = _check_statuses(episodes)
    results = report.rows_from_episodes(episodes, REFERENCE, draws=5)
    compared = 0
    for row in results["scores"] + results["pooled_scores"]:
        if "-seat" in row["scenario"]:
            continue  # check.py has no per-cast-size line
        assert (
            row["paper_verdict"]
            == statuses[(row["scenario"], row["formation"], row["model"])]
        )
        compared += 1
    assert compared == len(NIGHTS) + 5  # 9 cells + pooled (model, formation) pairs
    assert {r["paper_verdict"] for r in results["scores"]} <= {"PASS", "WARN", "MISS"}


def test_contrast_rows_include_cast_size_pools_and_the_reference_contrast() -> None:
    results = _results()
    contrasts, pooled = results["contrasts"], results["pooled_contrasts"]
    assert all(list(row) == list(CONTRAST_COLUMNS) for row in contrasts + pooled)
    per_scenario = {(r["scenario"], r["model"], r["contrast"]) for r in contrasts}
    assert per_scenario == {
        ("stakes_80", SONNET, "coordinator-team"),
        ("stakes_80", SONNET, "coordinator-team_silent"),
        ("stakes_80", SONNET, "team-team_silent"),
        ("stakes_100", SONNET, "coordinator-team"),
        ("stakes_n8_240", SONNET, "coordinator-team"),
        ("stakes_80", OPUS, "coordinator-team"),
    }
    row = next(
        r
        for r in contrasts
        if r["scenario"] == "stakes_80"
        and r["model"] == SONNET
        and r["contrast"] == "coordinator-team"
    )
    assert row["n_a"] == 4 and row["n_b"] == 4
    assert row["diff_pp"] == pp(0.55 - 0.2125)
    assert row["lo_pp"] <= row["diff_pp"] <= row["hi_pp"]
    assert row["method"].startswith("bootstrap, 40 draws, seed")
    ref_a = REFS[("stakes_80", "coordinator", SONNET)]
    ref_b = REFS[("stakes_80", "team", SONNET)]
    assert row["ref_diff_pp"] == pp(float(ref_a["mean"]) - float(ref_b["mean"]))
    assert row["ref_lo_pp"] < row["ref_diff_pp"] < row["ref_hi_pp"]
    assert row["ref_method"] == "welch" and row["ref_instrument"] == "corpus_of_record"
    labels = {
        (r["model"], r["contrast"]): sorted(
            r2["scenario"]
            for r2 in pooled
            if (r2["model"], r2["contrast"]) == (r["model"], r["contrast"])
        )
        for r in pooled
    }
    assert labels[(SONNET, "coordinator-team")] == sorted(
        [
            "POOLED (3 scenarios)",
            "POOLED 4-seat (2 scenarios)",
            "POOLED 8-seat (1 scenarios)",
        ]
    )
    assert labels[(SONNET, "coordinator-team_silent")] == sorted(
        ["POOLED (1 scenarios)", "POOLED 4-seat (1 scenarios)"]
    )
    four = next(
        r
        for r in pooled
        if r["scenario"] == "POOLED 4-seat (2 scenarios)"
        and r["model"] == SONNET
        and r["contrast"] == "coordinator-team"
    )
    assert four["n_a"] == 7 and four["n_b"] == 7
    pooled_a = report.pooled_stats(
        [REFS[(s, "coordinator", SONNET)] for s in ("stakes_100", "stakes_80")],
        "mean",
        "sd",
        "n",
    )
    pooled_b = report.pooled_stats(
        [REFS[(s, "team", SONNET)] for s in ("stakes_100", "stakes_80")],
        "mean",
        "sd",
        "n",
    )
    assert four["ref_diff_pp"] == pp(pooled_a[0] - pooled_b[0])
    assert four["ref_method"] == "welch"
    # seeded: the same draws give the same rows
    assert _results() == results


def test_reference_rows_reproduce_the_paper_pooled_means() -> None:
    rows = report.reference_rows()
    # 5 models x 4 formations x 25 scenarios, plus the two lead arms x 2 Claude models x 25 (team only: the
    # arms carry no formation contrast), less the four cells the provider-error screen emptied (three Claude Opus 5
    # peer-to-peer team cells, each also losing its two team contrasts, and one lead-arm cell)
    assert {k: len(v) for k, v in rows.items()} == {
        "scores": 5 * 4 * 25 + 2 * 2 * 25 - 4,
        "pooled_scores": 5 * 4 * 4 + 2 * 2 * 4,
        "contrasts": 25 * 5 * 3 - 3 * 2,
        "pooled_contrasts": 5 * 3 * 4,
    }
    assert all(
        list(r) == list(SCORE_COLUMNS) for r in rows["scores"] + rows["pooled_scores"]
    )
    assert all(
        list(r) == list(CONTRAST_COLUMNS)
        for r in rows["contrasts"] + rows["pooled_contrasts"]
    )
    pooled = {
        (r["model"], r["formation"], r["scenario"]): r
        for r in rows["pooled_scores"]
        if r["mitigation"] == "none"
    }

    def expected(model: str, formation: str, seats: int | None) -> float:
        cells = [
            c
            for (s, f, m), c in REFS.items()
            if m == model
            and f == formation
            and (seats is None or SCENARIOS[s].n_seats == seats)
        ]
        return round(report.pooled_stats(cells, "mean", "sd", "n")[0], 4)

    opus_all = pooled[(OPUS, "coordinator", "POOLED (25 scenarios)")]
    assert opus_all["score"] == expected(OPUS, "coordinator", None)
    assert abs(opus_all["score"] - 0.6355) < 1e-3
    assert opus_all["n"] == 500 and opus_all["unit"] == "night"
    assert (
        opus_all["opus5_delta_pp"] == 0.0
        and opus_all["opus5_delta_method"] == "self (baseline)"
    )
    # the screen emptied Claude Opus 5's peer-to-peer team on stakes_130, so its 4-user pool covers 9 scenarios
    opus_four = pooled[(OPUS, "team", "POOLED 4-seat (9 scenarios)")]
    assert opus_four["score"] == expected(OPUS, "team", 4)
    assert (
        round(opus_four["score"], 3) == 0.386
    )  # the team-size figure, Claude Opus 5 peer-to-peer team, 4 users
    sonnet_four = pooled[(SONNET, "team", "POOLED 4-seat (10 scenarios)")]
    assert sonnet_four["score"] == expected(SONNET, "team", 4)
    assert (
        abs(sonnet_four["score"] - 0.2452) < 1e-3
    )  # the team-size figure: 0.245 [0.212, 0.278]
    assert sonnet_four["n"] == 153
    assert sonnet_four["opus5_score"] == opus_four["score"]
    # the delta pairs the scenarios both models cover (Opus 5's team has no episode left on stakes_130), taken on
    # the unrounded means (the rows carry 4-dp scores)
    matched = [
        s
        for (s, f, m) in REFS
        if (f, m) == ("team", OPUS) and SCENARIOS[s].n_seats == 4
    ]
    assert len(matched) == 9
    sonnet_matched = report.pooled_stats(
        [REFS[(s, "team", SONNET)] for s in matched], "mean", "sd", "n"
    )
    assert (
        abs(sonnet_four["opus5_delta_pp"] - pp(sonnet_matched[0] - opus_four["score"]))
        <= 0.011
    )
    assert sonnet_four["opus5_delta_method"] == "welch"
    assert (
        sonnet_four["opus5_delta_lo_pp"]
        < sonnet_four["opus5_delta_pp"]
        < sonnet_four["opus5_delta_hi_pp"]
    )
    # per-cell rows: the paper columns stay empty, the interval is the cell's own t95
    cell = next(
        r
        for r in rows["scores"]
        if (r["scenario"], r["model"], r["formation"])
        == ("peq_brb_n4_105", SONNET, "coordinator")
    )
    ref = REFS[("peq_brb_n4_105", "coordinator", SONNET)]
    assert cell["n"] == 20 and cell["score"] == round(float(ref["mean"]), 4)
    lo, hi = clip01(report.interval(float(ref["mean"]), float(ref["sd"]), 20))
    assert (cell["ci_lo"], cell["ci_hi"]) == (round(lo, 4), round(hi, 4))
    assert cell["paper_score"] is None and cell["paper_verdict"] is None
    assert cell["opus5_score"] == round(
        float(REFS[("peq_brb_n4_105", "coordinator", OPUS)]["mean"]), 4
    )
    assert cell["opus5_delta_method"] == "welch"
    assert all(
        r["opus5_delta_pp"] == 0.0 and r["opus5_delta_method"] == "self (baseline)"
        for r in rows["scores"]
        if r["model"] == OPUS
    )
    # contrasts: the reference's own Welch contrast in the primary columns
    contrast = next(
        r
        for r in rows["pooled_contrasts"]
        if (r["model"], r["contrast"], r["scenario"])
        == (SONNET, "coordinator-team", "POOLED (25 scenarios)")
    )
    assert contrast["diff_pp"] == pp(
        expected(SONNET, "coordinator", None) - expected(SONNET, "team", None)
    )
    assert contrast["method"] == "welch"
    assert (contrast["n_a"], contrast["n_b"]) == (500, 414)
    assert contrast["ref_diff_pp"] is None
    # a pooled contrast pools the scenarios where both formations have episodes: 22 for the Opus 5 team
    opus = {
        r["scenario"]: r
        for r in rows["pooled_contrasts"]
        if (r["model"], r["contrast"]) == (OPUS, "coordinator-team")
    }
    assert set(opus) == {
        "POOLED (22 scenarios)",
        "POOLED 4-seat (9 scenarios)",
        "POOLED 8-seat (7 scenarios)",
        "POOLED 16-seat (6 scenarios)",
    }
    assert (
        opus["POOLED (22 scenarios)"]["n_a"],
        opus["POOLED (22 scenarios)"]["n_b"],
    ) == (
        440,
        399,
    )
    assert {r["scenario"] for r in rows["pooled_contrasts"] if r["model"] != OPUS} == {
        "POOLED (25 scenarios)",
        "POOLED 4-seat (10 scenarios)",
        "POOLED 8-seat (8 scenarios)",
        "POOLED 16-seat (7 scenarios)",
    }


def _write_night(
    runs_root: Path,
    scenario: str,
    model: str,
    formation: str,
    epoch: int,
    met_jobs: int,
) -> None:
    """A finished sim night in the run-dir shape `collect` reads: the first `met_jobs` roster jobs met."""
    roster = roster_for_scenario(scenario)
    run_dir = runs_root / f"{scenario}__{formation}__{model}__e{epoch}"
    world = run_dir / "world"
    world.mkdir(parents=True)
    (world / "config.json").write_text(
        json.dumps(
            {
                "eval": "api_key",
                "scenario": scenario,
                "formation": formation,
                "cell": f"{scenario}__{formation}",
                "model": model,
                "provider": "anthropic",
                "epoch": epoch,
                "harness": "sim",
            }
        )
    )
    (world / "summary.json").write_text(
        json.dumps(
            {
                "scenario": scenario,
                "clock": 930,
                "deadline_min": 930,
                "spent": 0,
                "jobs": {
                    job.job_id: {"met": i < met_jobs}
                    for i, job in enumerate(roster.jobs)
                },
                "fairness_semantics": "unsupported",
                "visibility": {"messages": []},
            }
        )
    )
    (run_dir / "DONE.json").write_text(
        json.dumps(
            {
                "ended": "world horizon reached",
                "rounds": 1,
                "error_turns": 0,
                "crashed": [],
                "wall_s": 1.0,
            }
        )
    )


def test_main_writes_the_score_and_contrast_rows_beside_the_readout(
    tmp_path: Path,
) -> None:
    runs_root = tmp_path / "fake_root"
    for epoch, met in enumerate((6, 9), start=1):
        _write_night(runs_root, "stakes_80", SONNET, "coordinator", epoch, met)
        _write_night(runs_root, "stakes_80", SONNET, "team", epoch, met // 2)
    out = tmp_path / "out"
    assert report.main([str(runs_root), "--out-dir", str(out), "--draws", "20"]) == 0
    assert {p.name for p in out.iterdir()} == {
        "episodes.csv",
        "scenarios.csv",
        "summary.txt",
        "summary.json",
        "scores.csv",
        "contrasts.csv",
        "results.md",
        "paper.csv",
    }
    with (out / "scores.csv").open() as f:
        scores = list(csv.DictReader(f))
    assert list(scores[0]) == list(SCORE_COLUMNS)
    assert [r["scenario"] for r in scores] == [
        "stakes_80",
        "stakes_80",
        "POOLED (1 scenarios)",
        "POOLED 4-seat (1 scenarios)",
        "POOLED (1 scenarios)",
        "POOLED 4-seat (1 scenarios)",
    ]
    assert all(
        r["n"] == "2" and r["paper_verdict"] in {"PASS", "WARN", "MISS"} for r in scores
    )
    with (out / "contrasts.csv").open() as f:
        contrasts = list(csv.DictReader(f))
    assert list(contrasts[0]) == list(CONTRAST_COLUMNS)
    assert [r["scenario"] for r in contrasts] == [
        "stakes_80",
        "POOLED (1 scenarios)",
        "POOLED 4-seat (1 scenarios)",
    ]
    assert all(
        r["contrast"] == "coordinator-team" and "20 draws" in r["method"]
        for r in contrasts
    )
    markdown = (out / "results.md").read_text()
    assert (
        "## Pooled scores" in markdown
        and "## Pooled contrasts" in markdown
        and "## Per-scenario contrasts" in markdown
    )
    assert "| claude-sonnet-5 | coordinator | POOLED (1 scenarios) |" in markdown
    summary = json.loads((out / "summary.json").read_text())
    assert (
        summary["baseline"] == "reference"
        and "results" not in summary
        and "episodes" not in summary
    )
    assert summary["cells"][0]["opus5_source"] == "reference"
    # the run has no Opus 5 nights: with --baseline run there is no baseline at all
    assert (
        report.main(
            [str(runs_root), "--out-dir", str(out), "--draws", "5", "--baseline", "run"]
        )
        == 0
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["baseline"] == "run"
    assert all(
        c["opus5_source"] is None and c["rel_to_opus5"] is None
        for c in summary["cells"]
    )
    assert summary["pooled"][0]["opus5_scenarios"] == 0
    assert "rel-opus5" not in (out / "summary.txt").read_text()
    # --max-epoch reads epochs <= N; without --out-dir a report lands in readouts/<runs root name>
    assert [r["epoch"] for r in report.collect(runs_root, max_epoch=1)] == [1, 1]
    assert report.collect(runs_root, max_epoch=0) == []
    assert (
        report.default_out_dir(runs_root) == report.EVAL_ROOT / "readouts" / "fake_root"
    )


QUARANTINED = (
    "fleet quarantined — every agent at 3+ consecutive failed resumes (last target error: Target generate "
    "failed: AuthenticationError: Error code: 401 - {'type': 'error', 'error': {'type': "
    "'authentication_error', 'message': 'API key is invalid.'}})"
)


def _patch_done(runs_root: Path, name: str, **fields: object) -> None:
    done = runs_root / name / "DONE.json"
    done.write_text(json.dumps({**json.loads(done.read_text()), **fields}))


def test_provider_errors_exclude_or_screen_nights_and_are_summarized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A refused key is a harness fault, even at the deadline; a lost turn is rule T's; 429s are their own bucket."""
    runs_root = tmp_path / "root"
    for epoch, met in enumerate((6, 9, 7, 8, 5), start=1):
        _write_night(runs_root, "stakes_80", SONNET, "team", epoch, met)
    night = f"stakes_80__team__{SONNET}__e{{}}"
    # e2: the provider refused the key (revoked mid-night; rule T is blind to 401s), every seat quarantined
    # with the clock already at the deadline
    refused = {"failed_calls": 4, "failed_other": 4, "failed_auth": 4}
    _patch_done(runs_root, night.format(2), ended=QUARANTINED, **refused)
    # e3: a few refused calls, but the night still reached its horizon: a harness fault all the same
    _patch_done(runs_root, night.format(3), **refused)
    # e4: a quarantine the scan cannot attribute to the key (no refused call recorded): incomplete
    _patch_done(runs_root, night.format(4), ended=QUARANTINED)
    # e5: rate limits and overloads in a row: a lost turn, which the paper's screen drops
    _patch_done(
        runs_root,
        night.format(5),
        failed_calls=12,
        failed_429=9,
        failed_529=2,
        failed_other=1,
        rule_t_lost_turns=1,
    )
    rows = report.collect(runs_root)
    by_epoch = {int(r["epoch"]): r for r in rows}
    assert by_epoch[2]["ran_to_completion"] and not report.reached_horizon(by_epoch[2])
    assert report.harness_fault(by_epoch[2]) and report.harness_fault(by_epoch[3])
    assert not report.harness_fault(by_epoch[4]) and not report.is_clean(by_epoch[4])
    assert report.is_clean(by_epoch[5]) and report.rule_t_dropped(by_epoch[5])
    assert [r["failed_429"] for r in rows] == [None, None, None, None, 9]
    (cell,) = report.cell_rows(rows)
    assert (cell["clean"], cell["incomplete"], cell["harness_excluded"]) == (1, 1, 2)
    assert (cell["clean_raw"], cell["rule_t_dropped"]) == (2, 1)
    (screened,) = [
        line
        for line in provider_error_note(rows, "night")
        if line.startswith("PROVIDER ERRORS")
    ]
    assert screened == (
        "PROVIDER ERRORS: 3 of 5 nights had failed target calls (20 calls: 429 rate limit 9, 529 overload 2, "
        "other 9, of which the key refused 8); rule T dropped 1 night(s) with a lost turn, and 2 with a "
        "refused key are excluded"
    )
    out = tmp_path / "out"
    assert report.main([str(runs_root), "--out-dir", str(out), "--draws", "20"]) == 0
    with (out / "episodes.csv").open() as f:
        assert "failed_429" in next(csv.reader(f))
    text = (out / "summary.txt").read_text()
    assert screened in text and "EXCLUDED: the provider refused the key" in text
    capsys.readouterr()
    check_mod.main([str(runs_root), "--provider-screen", "none"])
    assert "1 night(s) had a lost turn (kept: no rule T in this reading)" in (
        capsys.readouterr().out
    )


def test_a_cell_and_a_pool_emptied_by_rule_t_say_so(tmp_path: Path) -> None:
    """Every clean episode dropped by the screen: no welfare, and every readout names rule T, not "no clean episode"."""
    runs_root = tmp_path / "root"
    for epoch in (1, 2):
        _write_night(runs_root, "stakes_80", SONNET, "team", epoch, 6)
        _patch_done(
            runs_root,
            f"stakes_80__team__{SONNET}__e{epoch}",
            rule_t_lost_turns=2,
            failed_calls=9,
            failed_529=9,
        )
    rows = report.collect(runs_root)
    (cell,) = report.cell_rows(rows)
    (pooled,) = report.pooled_rows(rows, [cell])
    assert cell["welfare_mean"] is None and pooled["welfare_mean"] is None
    assert (pooled["clean"], pooled["clean_raw"], pooled["rule_t_dropped"]) == (0, 2, 2)
    reason = report.unscored_reason(cell)
    assert reason.startswith("all 2 clean episode(s) dropped by rule T (raw mean ")
    assert report.unscored_reason(pooled) == reason
    reference = {
        "cells": [
            {"scenario": "stakes_80", "formation": "team", "model": SONNET}
            | {"mean": 0.5, "sd": 0.1, "n": 20}
        ]
    }
    assert check_mod.check([cell], reference) == [
        ("SKIP", f"SKIP stakes_80 team {SONNET}: {reason} in this run")
    ]
    out = tmp_path / "out"
    assert report.main([str(runs_root), "--out-dir", str(out), "--draws", "20"]) == 0
    text = (out / "summary.txt").read_text()
    assert reason in text and "no clean episode" not in text
    # without the screen the same nights score
    (unscreened,) = report.pooled_rows(rows, report.cell_rows(rows, "none"), "none")
    assert (unscreened["clean"], unscreened["rule_t_dropped"]) == (2, 0)


def test_an_unscreened_reading_is_compared_with_the_unscreened_reference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--provider-screen none` compares like with like: the reference's mean_raw / sd_raw / n_raw."""
    runs_root = tmp_path / "root"
    for epoch, met in enumerate((6, 9, 7, 8), start=1):
        _write_night(runs_root, "stakes_80", SONNET, "team", epoch, met)
    _patch_done(
        runs_root,
        f"stakes_80__team__{SONNET}__e4",
        rule_t_lost_turns=1,
        failed_calls=4,
        failed_529=4,
    )
    cell = {"scenario": "stakes_80", "formation": "team", "model": SONNET}
    reference = {
        "label": "paper",
        "instrument": "paper",
        "cells": [
            cell
            | {"mean": 0.9, "sd": 0.01, "n": 13, "instrument": "corpus_of_record"}
            | {"mean_raw": 0.2, "sd_raw": 0.3, "n_raw": 20}
        ],
    }
    unscreened = report.reference_for_screen(reference, "none")
    (raw_cell,) = unscreened["cells"]
    assert (raw_cell["mean"], raw_cell["sd"], raw_cell["n"]) == (0.2, 0.3, 20)
    assert raw_cell["instrument"] == "corpus_of_record (unscreened)"
    assert unscreened["label"] == "paper, unscreened"
    assert report.reference_for_screen(reference, "paper") is reference
    rows = report.collect(runs_root)
    verdicts = check_mod.check(report.cell_rows(rows, "none"), unscreened)
    lines = [line for _, line in verdicts]
    assert all("(paper, unscreened" in line for line in lines), lines
    assert "(n=4) vs reference 0.200" in lines[0] and "n=20" in lines[0]
    path = tmp_path / "reference.json"
    path.write_text(json.dumps(reference))
    capsys.readouterr()
    check_mod.main(
        [str(runs_root), "--reference", str(path), "--provider-screen", "none"]
    )
    out = capsys.readouterr().out
    assert "reference: reference.json (paper, unscreened)" in out
    assert "vs reference 0.200" in out and "vs reference 0.900" not in out
