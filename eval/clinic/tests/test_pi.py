"""The real-pi harness offline (`run.py --fake-pi`: scripted FakePi desks) and the readers' command lines on its runs.

The pi harness is an alternative instrument, not the paper's; its fake mornings also serve as small real run dirs
for `report.py` and `check.py`. An unscripted desk idles, so a morning creeps to its horizon.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from _compare import CONTRAST_COLUMNS, SCORE_COLUMNS
from _harness.readout import load_run

from clinic import cells, check, report
from clinic.reference import PaperReference
from clinic.tests.conftest import run_fake, write_scripts

BOARD = "warfarin_inr_split"
SONNET = "claude-sonnet-5"
REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def wave(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A root holding one coordinator (its desk looks up the directory first) and one team morning of epoch 1."""
    tmp = tmp_path_factory.mktemp("pi")
    steps: list[dict[str, Any]] = [
        {"tool": "clinic_directory", "args": {}},
        {"tool": "clinic_standby", "args": {}},
    ]
    scripts = write_scripts(
        tmp / "scripts", {"A": [{"steps": steps, "reply": "on it"}]}
    )
    root = tmp / "fake_wave"
    assert run_fake(root, scripts=scripts) == 0
    assert run_fake(root, formation="team") == 0
    return root


def _summary(runs_root: Path, formation: str) -> dict[str, Any]:
    topology = "_steward_" if formation == "coordinator" else "_meshfull_"
    (run_dir,) = (p for p in runs_root.iterdir() if topology in p.name)
    return json.loads((run_dir / "world" / "summary.json").read_text())


def test_a_morning_plays_to_the_horizon_is_scored_per_contest_and_is_deterministic(
    wave: Path, tmp_path: Path
) -> None:
    for run_dir in wave.iterdir():
        loaded = load_run(run_dir)
        assert loaded is not None
        summary, config, _done = loaded
        assert (summary["framing"], summary["debrief_min"], config["eval"]) == (
            "f_all_closed",
            9999,
            "clinic",
        )
        topology = "steward" if config["formation"] == "coordinator" else "meshfull"
        assert summary["topology"] == topology
    episodes, contests = report.collect(wave)
    assert len(contests) == 12  # warfarin_inr carries 6 contests a morning
    assert {c["formation"] for c in contests} == {"coordinator", "team"}
    assert all(c["deadline_met"] in (0, 1) for c in contests)
    for episode in episodes:
        assert (
            episode["contests"] == 6 and episode["sim_clock"] >= episode["horizon_min"]
        )
        assert episode["endstate"] == "horizon" and report.is_clean(episode)
    assert [c["endstate_horizon"] for c in report.cell_rows(episodes, draws=20)] == [
        1,
        1,
    ]
    # the same epoch replays byte for byte; another epoch seeds another morning
    for name, epoch0 in (("again", 1), ("next", 2)):
        assert run_fake(tmp_path / name, formation="team", epoch0=epoch0) == 0
    assert _summary(tmp_path / "again", "team") == _summary(wave, "team")
    assert _summary(tmp_path / "next", "team") != _summary(wave, "team")


def test_the_rounds_cap_excludes_the_morning(tmp_path: Path) -> None:
    assert run_fake(tmp_path / "runs", extra=("--rounds-max", "2")) == 0
    (episode,), _ = report.collect(tmp_path / "runs")
    assert episode["ended"] == report.ROUNDS_CAP and not report.is_clean(episode)
    assert episode["paper_exclusion"] == "rounds cap"


def test_the_per_round_wait_budget_keeps_a_desk_per_caller_shift_multi_round(
    tmp_path: Path,
) -> None:
    """Without it one lockstep round of standbys ends the 240-minute shift; with its 60 minutes, at least four rounds."""
    board = "warfarin_inr_plain"
    desks = [a.id for a in cells.build_cell(board, "team", 1).spec.agents]
    turn: dict[str, Any] = {
        "steps": [{"tool": "clinic_standby", "args": {}} for _ in range(3)],
        "reply": "waiting",
    }
    scripts = write_scripts(tmp_path / "scripts", {d: [turn] * 40 for d in desks})
    done: dict[str, dict[str, Any]] = {}
    for name, extra in (("capped", ()), ("uncapped", ("--round-wait-budget", "0"))):
        runs = tmp_path / name
        assert (
            run_fake(runs, board=board, formation="team", scripts=scripts, extra=extra)
            == 0
        )
        (run_dir,) = runs.iterdir()
        done[name] = json.loads((run_dir / "DONE.json").read_text())
    assert all(d["sim_clock"] >= 240 for d in done.values())
    assert done["capped"]["rounds"] >= 4 and done["uncapped"]["rounds"] <= 2
    loaded = load_run(next((tmp_path / "capped").iterdir()))
    assert loaded is not None and loaded[1]["round_wait_budget"] == 60


def test_report_writes_the_readout_and_its_score_rows(
    wave: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`report.py <root>` lands in readouts/<root name>/; `results_from_episodes` is the same table, read without writing."""
    monkeypatch.setattr(report, "EVAL_ROOT", tmp_path / "eval_root")
    capsys.readouterr()
    assert report.main([str(wave), "--draws", "50"]) == 0
    assert capsys.readouterr().out.rstrip().endswith("(2 episodes, 12 contests)")
    out = tmp_path / "eval_root" / "readouts" / "fake_wave"
    assert {p.name for p in out.iterdir()} == {
        "episodes.csv",
        "contests.csv",
        "scenarios.csv",
        "pooled.csv",
        "paired.csv",
        "summary.txt",
        "summary.json",
        "scores.csv",
        "contrasts.csv",
        "results.md",
    }

    def header(name: str) -> list[str]:
        with (out / name).open() as f:
            return next(csv.reader(f))

    assert {"joint_rate", "joint_lo", "joint_hi", "deadline_met_rate", "valid"} <= set(
        header("scenarios.csv")
    )
    assert "mornings" not in header("scenarios.csv")
    assert {"deadline_met", "joint_success_upper", "n_displaced_named", "valid"} <= set(
        header("contests.csv")
    )
    assert header("paired.csv") == list(report.PAIRED_COLUMNS)
    with (out / "pooled.csv").open() as f:
        pooled = {(r["formation"], r["condition"]) for r in csv.DictReader(f)}
    assert pooled == {("coordinator", "scattered"), ("team", "scattered")}
    assert header("scores.csv") == list(SCORE_COLUMNS)
    assert header("contrasts.csv") == list(CONTRAST_COLUMNS)
    text = (out / "results.md").read_text()
    assert "## Pooled scores" in text and "## Pooled contrasts" in text
    assert f"| POOLED (1 scenarios) | {SONNET} | coordinator-team |" in text

    results = report.results_from_episodes(report.collect(wave)[0], draws=100)
    assert capsys.readouterr() == ("", "")  # reading the rows neither prints nor writes
    scores, pooled_scores = results["scores"], results["pooled_scores"]
    assert len(scores) == len(pooled_scores) == 2
    paper = PaperReference.load()
    for score in scores:
        ref = paper.cell("corpus_of_record", BOARD, str(score["formation"]), SONNET)
        assert ref is not None
        assert (score["unit"], score["n"], score["ci_method"]) == (
            "morning",
            1,
            report.CI_METHOD,
        )
        assert (score["paper_instrument"], score["paper_n"]) == ("corpus_of_record", 20)
        assert score["paper_score"] == round(float(ref["joint_pct"]) / 100, 4)
        assert (
            abs(score["paper_delta_pp"] - 100 * (score["score"] - score["paper_score"]))
            <= 0.006
        )
        assert score["paper_verdict"] in ("PASS", "WARN", "MISS")
        assert score["opus5_instrument"] == "corpus_of_record"
        assert score["opus5_delta_method"] == report.POINT_DIFF
    for score in pooled_scores:
        assert score["scenario"] == "POOLED scattered (1 scenarios)"
        assert score["ci_method"] == report.POOLED_CI_METHOD
        assert score["paper_instrument"] == "corpus_of_record (1 of 12 scenarios)"
    (contrast,) = results["contrasts"]
    assert (contrast["scenario"], contrast["contrast"]) == (BOARD, "coordinator-team")
    assert contrast["method"] == "bootstrap, 100 draws, seed 20260921"
    assert contrast["ref_method"] == "difference of the frozen cells"
    coordinator = paper.cell("corpus_of_record", BOARD, "coordinator", SONNET)
    team = paper.cell("corpus_of_record", BOARD, "team", SONNET)
    assert coordinator is not None and team is not None
    diff = float(coordinator["joint_pct"]) - float(team["joint_pct"])
    assert abs(float(contrast["ref_diff_pp"]) - diff) <= 0.006
    (pooled_contrast,) = results["pooled_contrasts"]
    assert pooled_contrast["scenario"] == "POOLED (1 scenarios)"
    assert (
        pooled_contrast["method"] == "bootstrap (strata mean), 100 draws, seed 20260921"
    )


def test_check_reads_a_pi_run_against_the_paper_and_names_the_instrument(
    wave: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    capsys.readouterr()
    assert check.main([str(wave)]) in (0, 1)
    default = capsys.readouterr().out
    lines = default.splitlines()
    at = lines.index("reference: paper (joint success, scenario-averaged)")
    assert lines[at + 1].startswith(
        "HARNESS: 2 of 2 episode(s) ran the real-pi harness"
    )
    assert "corpus_of_record (20 episodes)" in default
    # --reference: a relative path, from the repository root, reads exactly as the default
    monkeypatch.chdir(REPO_ROOT)
    for given in (
        "expected/reference.json",
        "reference.json",
        str(check.DEFAULT_REFERENCE),
    ):
        assert check.resolve_reference(Path(given)) == check.DEFAULT_REFERENCE
    with pytest.raises(SystemExit, match="not found"):
        check.resolve_reference(Path("expected/nope.json"))
    check.main([str(wave), "--reference", "expected/reference.json"])
    assert capsys.readouterr().out == default
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"schema": "other", "cells": []}))
    with pytest.raises(
        SystemExit, match="not a clinic reference in the paper's schema"
    ):
        check.main([str(wave), "--reference", str(other)])


def test_a_cell_reads_from_several_roots_and_a_missing_root_is_refused(
    wave: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two roots holding one cell's mornings read as one collection; a root not pulled is an error."""
    second = tmp_path / "fake_wave_second"
    assert run_fake(second, formation="team", epoch0=2) == 0
    capsys.readouterr()
    out = tmp_path / "b"
    assert (
        report.main([str(wave), str(second), "--out-dir", str(out), "--draws", "50"])
        == 0
    )
    with (out / "scores.csv").open() as handle:
        team = [
            r
            for r in csv.DictReader(handle)
            if (r["scenario"], r["formation"]) == (BOARD, "team")
        ]
    assert [r["n"] for r in team] == ["2"]  # both mornings, not the last root's one
    missing = tmp_path / "fake_wave_nope"
    with pytest.raises(FileNotFoundError, match="fake_wave_nope"):
        report.collect([wave, missing])
    for main, argv in (
        (report.main, [str(wave), str(missing)]),
        (check.main, [str(wave), str(missing)]),
    ):
        with pytest.raises(SystemExit) as refused:
            main(argv)
        assert refused.value.code == 2
        assert "fake_wave_nope" in capsys.readouterr().err
