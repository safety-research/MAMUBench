"""Reports and checks key cells by mitigation arm: arms never pool, and an arm compares only with its own reference.

Fixture rows per env (the readers' statistics are functions of the episode rows) plus two offline
end-to-end runs (api_key on the simulated harness with a fake model, and on the pi harness with fake pi)
in which a registered arm banks next to the control arm in one runs root.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from _compare import CONTRAST_COLUMNS, SCORE_COLUMNS
from _harness import sim
from _harness.readout import load_run
from _mitigations import NONE, Mitigation

from tests.conftest import FAKE, fake_arm_record

SONNET = "claude-sonnet-5"
OPUS = "claude-opus-5"


def _arm() -> Mitigation:
    """The fake arm on coordinator and team (its hooks are stubbed to play the control recipe/cell)."""
    return fake_arm_record(formations=("coordinator", "team"))


def _by(rows: list[dict[str, Any]], **match: Any) -> list[dict[str, Any]]:
    return [r for r in rows if all(r.get(k) == v for k, v in match.items())]


# ── api_key ───────────────────────────────────────────────────────────────────────────────────────


def _night(
    scenario: str, formation: str, welfare: float, mitigation: str | None
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scenario": scenario,
        "formation": formation,
        "model": SONNET,
        "welfare_over_opt": welfare,
        "ran_to_completion": True,
        "roster_ok": True,
        "error_turns": 0,
        "crashed": "",
        "met_jobs": 1,
        "dms_sent": 0,
        "nonconsensual_cross_principal": 0,
    }
    if mitigation is not None:
        row["mitigation"] = mitigation
    return row


def _api_key_nights() -> list[dict[str, Any]]:
    control = [
        _night("stakes_80", f, w, None)
        for f, w in (
            ("coordinator", 0.6),
            ("coordinator", 0.5),
            ("team", 0.2),
            ("team", 0.3),
        )
    ]
    armed = [_night("stakes_80", "team", w, FAKE) for w in (0.9, 0.8, 0.85)]
    return control + armed


def test_api_key_cells_pools_contrasts_and_references_are_per_arm() -> None:
    from api_key import check as check_mod
    from api_key import report

    episodes = _api_key_nights()
    cells = report.cell_rows(episodes)
    assert [(c["formation"], c["mitigation"], c["clean"]) for c in cells] == [
        ("coordinator", NONE, 2),
        ("team", NONE, 2),
        ("team", FAKE, 3),
    ]
    assert round(float(_by(cells, mitigation=FAKE)[0]["welfare_mean"]), 4) == 0.85
    pooled = report.pooled_rows(episodes, report.with_relative_to_opus5(cells, None))
    assert [(r["formation"], r["mitigation"], r["clean"]) for r in pooled] == [
        ("coordinator", NONE, 2),
        ("team", NONE, 2),
        ("team", FAKE, 3),
    ]
    # the control cells of the paper reference (it also ships the api_key lead arms' cells)
    full = report.load_reference()
    reference = {
        **full,
        "cells": [c for c in full["cells"] if c.get("mitigation", NONE) == NONE],
    }
    control_ref = report.reference_cells(reference)[("stakes_80", "team", SONNET)]
    arm_ref = {**control_ref, "mitigation": FAKE, "mean": 0.9, "sd": 0.05, "n": 20}
    with_arm = {**reference, "cells": [*reference["cells"], arm_ref]}
    results = report.rows_from_episodes(episodes, with_arm, draws=20)
    assert all(
        tuple(r) == SCORE_COLUMNS for r in results["scores"] + results["pooled_scores"]
    )
    assert all(
        tuple(r) == CONTRAST_COLUMNS
        for r in results["contrasts"] + results["pooled_contrasts"]
    )
    control_row = _by(results["scores"], formation="team", mitigation=NONE)[0]
    arm_row = _by(results["scores"], formation="team", mitigation=FAKE)[0]
    assert control_row["paper_score"] == round(float(control_ref["mean"]), 4)
    assert arm_row["paper_score"] == 0.9 and arm_row["n"] == 3
    # an arm has no Opus 5 cell of its own here: no baseline, never the control's
    assert arm_row["opus5_score"] is None and control_row["opus5_score"] is not None
    # contrasts are within one arm: the arm ran team only, so it has none
    assert {r["mitigation"] for r in results["contrasts"]} == {NONE}
    assert {
        (r["scenario"], r["mitigation"])
        for r in results["pooled_scores"]
        if r["formation"] == "team"
    } >= {
        ("POOLED (1 scenarios)", NONE),
        ("POOLED (1 scenarios)", FAKE),
    }
    # without an arm reference, the arm's cells are skipped, never compared with the control's
    verdicts = check_mod.check(cells, reference)
    arm_lines = [line for _, line in verdicts if f"[mitigation {FAKE}]" in line]
    assert arm_lines == [
        f"SKIP stakes_80 team {SONNET} [mitigation {FAKE}]: no reference cell"
    ]
    verdicts = check_mod.check(cells, with_arm)
    arm_lines = [line for _, line in verdicts if f"[mitigation {FAKE}]" in line]
    assert len(arm_lines) == 2 and all("reference 0.900" in line for line in arm_lines)
    # the frozen reference as a table: arm cells in rows of their own
    table = report.reference_rows(with_arm)
    assert (
        _by(
            table["scores"],
            scenario="stakes_80",
            formation="team",
            model=SONNET,
            mitigation=FAKE,
        )[0]["score"]
        == 0.9
    )
    # one row per control cell with episodes (the provider-error screen emptied three)
    assert len(_by(table["scores"], mitigation=NONE)) == sum(
        1 for c in reference["cells"] if report.has_episodes(c)
    )
    assert report.reference_rows(reference) == {
        section: [r for r in rows if r["mitigation"] == NONE]
        for section, rows in table.items()
    }


def test_api_key_markdown_shows_the_arm_column_only_with_an_arm() -> None:
    from api_key import report

    reference = report.load_reference()
    control_only = report.rows_from_episodes(
        [r for r in _api_key_nights() if "mitigation" not in r], reference, draws=10
    )
    assert "| mitigation |" not in report.results_markdown(control_only, "t")
    armed = report.rows_from_episodes(_api_key_nights(), reference, draws=10)
    text = report.results_markdown(armed, "t")
    assert "| model | formation | mitigation | scenario |" in text
    assert f"| {SONNET} | team | {FAKE} | POOLED (1 scenarios) |" in text


# ── clinic ────────────────────────────────────────────────────────────────────────────────────────


def _morning(formation: str, met: int, mitigation: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "run": f"r{formation}{met}{mitigation}",
        "scenario": "warfarin_inr_split",
        "formation": formation,
        "model": SONNET,
        "epoch": 1,
        "harness": "sim",
        "ended": "world horizon reached",
        "error_turns": 0,
        "crashed": "",
        "retired_physics": False,
        "endstate": "horizon",
        "contests_met": met,
        "contests": 10,
        "holders_dropped": 0,
    }
    if mitigation is not None:
        row["mitigation"] = mitigation
    return row


def test_clinic_cells_and_references_are_per_arm(tmp_path: Path) -> None:
    from clinic import check as check_mod
    from clinic import report

    episodes = [
        _morning("coordinator", 8),
        _morning("team", 4),
        _morning("team", 9, FAKE),
        _morning("team", 10, FAKE),
    ]
    cells = report.cell_rows(episodes, draws=20)
    assert [
        (c["formation"], c["mitigation"], c["met"], c["contests"]) for c in cells
    ] == [
        ("coordinator", NONE, 8, 10),
        ("team", NONE, 4, 10),
        ("team", FAKE, 19, 20),
    ]
    assert [
        (r["formation"], r["mitigation"])
        for r in report.pooled_rows(episodes, draws=20)
    ] == [
        ("coordinator", NONE),
        ("team", NONE),
        ("team", FAKE),
    ]
    raw = json.loads(report.REFERENCE_PATH.read_text())
    control_cell = next(
        c
        for c in raw["cells"]
        if (c["scenario"], c["formation"], c["model"])
        == ("warfarin_inr_split", "team", SONNET)
    )
    arm_cell = {
        **control_cell,
        "mitigation": FAKE,
        "met": 190,
        "joint": 190,
        "joint_pct": 95.0,
        "n": 200,
        "episodes": 20,
    }
    path = tmp_path / "reference.json"
    path.write_text(json.dumps({**raw, "cells": [*raw["cells"], arm_cell]}))
    assert report.Reference.arms(path) == [NONE, FAKE, "s1", "s2", "s3"]
    assert report.Reference.load(path, FAKE).keys() == [
        ("warfarin_inr_split", "team", SONNET)
    ]
    results = report.results_from_episodes(episodes, reference_path=path, draws=20)
    arm_row = _by(results["scores"], mitigation=FAKE)[0]
    control_row = _by(results["scores"], formation="team", mitigation=NONE)[0]
    assert arm_row["paper_score"] == 0.95 and arm_row["n"] == 2
    assert control_row["paper_score"] == round(control_cell["joint_pct"] / 100, 4)
    assert {
        r["mitigation"] for r in results["contrasts"] + results["pooled_contrasts"]
    } == {NONE}
    verdicts = check_mod.check(cells, {**raw, "cells": [*raw["cells"], arm_cell]})
    arm_lines = [line for _, line in verdicts if f"[mitigation {FAKE}]" in line]
    assert len(arm_lines) == 2 and all("190/200" in line for line in arm_lines)
    assert [line for _, line in check_mod.check(cells, raw) if FAKE in line] == [
        f"SKIP warfarin_inr_split team {SONNET} [mitigation {FAKE}]: no reference cell"
    ]
    table = report.reference_rows(path)
    assert len(_by(table["scores"], mitigation=FAKE)) == 1
    assert table["scores"][: len(_by(table["scores"], mitigation=NONE))] == _by(
        report.reference_rows()["scores"], mitigation=NONE
    )


# ── personal_assistant ────────────────────────────────────────────────────────────────────────────


def _episode(formation: str, outcome: str, epoch: int, mitigation: str = NONE) -> Any:
    from personal_assistant.outcomes import EpisodeOutcome

    return EpisodeOutcome(
        wave="w",
        sidecar=f"s{epoch}.json",
        scenario="airport_soup_sixteen",
        formation=formation,
        cell=f"c_{formation}",
        model=OPUS,
        thinking="off",
        epoch=epoch,
        git_sha="x",
        ending="committed" if outcome in ("kept", "violated") else "no_decision",
        outcome=outcome,
        gate_instrument="g",
        gate_errors=0,
        canaries=(),
        turns=1,
        mitigation=mitigation,
    )


def test_personal_assistant_cells_and_references_are_per_arm(tmp_path: Path) -> None:
    from personal_assistant import check as check_mod
    from personal_assistant import report

    episodes = [
        _episode("coordinator", "kept", 1),
        _episode("team", "kept", 1),
        _episode("team", "violated", 2),
        _episode("team", "kept", 1, FAKE),
        _episode("team", "kept", 2, FAKE),
        _episode("team", "violated", 3, FAKE),
    ]
    cells = report.cell_rows(episodes)
    assert [(c["arm"], c["mitigation"], c["n"], c["kept"]) for c in cells] == [
        ("coordinator", NONE, 1, 1),
        ("team", NONE, 2, 1),
        ("team", FAKE, 3, 2),
    ]
    assert list(cells[0])[-1] == "mitigation"
    assert [(r["arm"], r["mitigation"], r["n"]) for r in report.pooled_rows(cells)] == [
        ("coordinator", NONE, 1),
        ("team", NONE, 2),
        ("team", FAKE, 3),
    ]
    assert "team+fake_arm" in report.grid_text(cells, report.pooled_rows(cells))
    raw = json.loads(report.REFERENCE_PATH.read_text())
    control_cell = next(
        c
        for c in raw["cells"]
        if (c["scenario"], c["formation"], c["model"])
        == ("airport_soup_sixteen", "team", OPUS)
    )
    arm_cell = {
        **control_cell,
        "mitigation": FAKE,
        "kept": 80,
        "admissible": 100,
        "committed": 100,
    }
    path = tmp_path / "reference.json"
    path.write_text(json.dumps({**raw, "cells": [*raw["cells"], arm_cell]}))
    assert report.reference_arms(path) == [NONE, FAKE]
    assert set(report.load_reference(path, FAKE)) == {
        ("airport_soup_sixteen", "team", OPUS)
    }
    assert len(report.load_reference(path)) == len(raw["cells"])
    results = report.rows_from_episodes(episodes, draws=20, reference_path=path)
    arm_row = _by(results["scores"], mitigation=FAKE)[0]
    assert (arm_row["paper_score"], arm_row["n"]) == (0.8, 3)
    control_row = _by(results["scores"], formation="team", mitigation=NONE)[0]
    assert control_row["paper_score"] == round(
        control_cell["kept"] / control_cell["n"], 4
    )
    assert {r["mitigation"] for r in results["contrasts"]} == {NONE}
    arm_lines = [
        v.line
        for v in check_mod.check_cells(
            cells, {**raw, "cells": [*raw["cells"], arm_cell]}
        )
        if FAKE in v.line
    ]
    assert (
        arm_lines[0]
        .split(": ", 1)[0]
        .endswith(f"airport_soup_sixteen | team | {OPUS} [mitigation {FAKE}]")
    )
    assert "2/3" in arm_lines[0] and "80/100" in arm_lines[0]
    assert [v.line for v in check_mod.check_cells(cells, raw) if FAKE in v.line][
        0
    ].startswith(
        f"SKIP airport_soup_sixteen | team | {OPUS} [mitigation {FAKE}]: no reference cell"
    )
    ask = check_mod.ask_met_verdicts(cells, {**raw, "cells": [*raw["cells"], arm_cell]})
    assert any(f"[mitigation {FAKE}] :: ask met" in v.line for v in ask)


def test_personal_assistant_reads_the_arm_from_the_wave_manifest(
    tmp_path: Path,
) -> None:
    from personal_assistant import outcomes

    wave = tmp_path / "kestrel__claude-opus-5__mit-fake_arm"
    wave.mkdir()
    assert outcomes.wave_mitigation(wave) == NONE
    outcomes.wave_mitigation.cache_clear()
    (wave / "wave_config.json").write_text(json.dumps({"mitigation": FAKE}))
    assert outcomes.wave_mitigation(wave) == FAKE
    outcomes.wave_mitigation.cache_clear()


# ── merge_queue ───────────────────────────────────────────────────────────────────────────────────


def _mq_run(
    root: Path, formation: str, epoch: int, release: int, mitigation: str | None
) -> None:
    from merge_queue.run import run_dir_name

    run_dir = root / run_dir_name(
        "oversub", formation, SONNET, epoch, mitigation or NONE
    )
    run_dir.mkdir(parents=True)
    (run_dir / "DONE.json").write_text(json.dumps({"infrastructure_pass": True}))
    config: dict[str, Any] = {
        "model": SONNET,
        "formation": formation,
        "scenario": "oversub",
        "thinking": "off",
    }
    if mitigation is not None:
        config["mitigation"] = mitigation
    (run_dir / "config.json").write_text(json.dumps(config))
    world: dict[str, Any] = {
        "release_value": release,
        "oracle_value": 100,
        "merged_prs": [201],
        "cutoff_reached": True,
        "queue": {"starved_prs": []},
        "unauthorized_actions": [],
        "communications": {"comments": 0, "voiced_replies": 0},
    }
    (run_dir / "episode.json").write_text(
        json.dumps(
            {
                "crashed_agents": [],
                "rounds": 1,
                "wall_clock_seconds": 1.0,
                "world": world,
                "oracle": {},
            }
        )
    )


def test_merge_queue_cells_and_references_are_per_arm(tmp_path: Path) -> None:
    from merge_queue import check as check_mod
    from merge_queue import report

    root = tmp_path / "runs"
    _mq_run(root, "team", 1, 60, None)
    _mq_run(root, "team", 2, 70, None)
    _mq_run(root, "coordinator", 1, 80, None)
    _mq_run(root, "team", 1, 95, FAKE)
    _mq_run(root, "team", 2, 97, FAKE)
    episodes = report.collect(root)
    assert sorted((r["formation"], r["mitigation"]) for r in episodes) == [
        ("coordinator", NONE),
        ("team", FAKE),
        ("team", FAKE),
        ("team", NONE),
        ("team", NONE),
    ]
    cells = report.cell_rows(episodes)
    assert [(c["formation"], c["mitigation"], c["welfare_mean"]) for c in cells] == [
        ("coordinator", NONE, 0.8),
        ("team", NONE, 0.65),
        ("team", FAKE, 0.96),
    ]
    raw = json.loads(report.DEFAULT_REFERENCE.read_text())
    arm_cell = {
        "scenario": "oversub",
        "formation": "team",
        "model": SONNET,
        "instrument": "instrument_b",
        "thinking": "off",
        "n": 20,
        "welfare_mean": 0.97,
        "welfare_sd": 0.02,
        "lost_dearer": 0,
        "mitigation": FAKE,
    }
    reference = report.Reference([*raw["cells"], arm_cell])
    results = report.results_from_episodes(episodes, reference, draws=20)
    arm_row = _by(results["scores"], mitigation=FAKE)[0]
    assert arm_row["paper_score"] == 0.97 and arm_row["n"] == 2
    assert {r["mitigation"] for r in results["contrasts"]} == {NONE}
    arm_lines = [
        line
        for _, line in check_mod.check(
            cells, {**raw, "cells": [*raw["cells"], arm_cell]}
        )
        if FAKE in line
    ]
    assert len(arm_lines) == 2 and all(
        "instrument_b (n=20)" in line for line in arm_lines
    )
    assert [line for _, line in check_mod.check(cells, raw) if FAKE in line] == [
        f"SKIP oversub team {SONNET} [mitigation {FAKE}]: no reference cell"
    ]
    path = tmp_path / "reference.json"
    path.write_text(json.dumps({**raw, "cells": [*raw["cells"], arm_cell]}))
    table = report.reference_rows(path)
    assert len(_by(table["scores"], mitigation=FAKE)) == 1


# ── end to end: an arm banks beside the control arm in one runs root ──────────────────────────────


def test_api_key_sim_arm_banks_stamped_and_reports_apart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api_key import cells, mitigations, report
    from api_key import run as run_mod

    monkeypatch.setenv("EVAL_SIM_DISPLAY", "none")
    monkeypatch.setitem(mitigations.MITIGATIONS, FAKE, _arm())

    def same_world(scenario: str, formation: str, mitigation: str) -> sim.SimRecipe:
        return replace(
            cells.build_sim_recipe(scenario, formation), mitigation=mitigation
        )

    monkeypatch.setattr(mitigations, "build_sim_recipe", same_world)
    jobs = tmp_path / "jobs.csv"
    jobs.write_text(
        f"scenario,formation,epoch,mitigation\nstakes_100,coordinator,1,\nstakes_100,coordinator,1,{FAKE}\n"
    )
    runs = tmp_path / "runs"
    argv = [
        "--jobs-file",
        str(jobs),
        "--harness",
        "sim",
        "--fake-model",
        "--runs-root",
        str(runs),
    ]
    assert run_mod.main(argv) == 0
    names = sorted(p.name for p in runs.iterdir())
    cell = "token_cluster__stakes_100__steward__notax"
    assert names == [
        f"{cell}__claude-sonnet-5__e1__sim__fakemodel",
        f"{cell}__mit-{FAKE}__claude-sonnet-5__e1__sim__fakemodel",
    ]
    configs = [load_run(runs / name) for name in names]
    assert [c[1]["mitigation"] for c in configs if c] == [None, FAKE]
    rows = report.collect(runs)
    assert sorted(r["mitigation"] for r in rows) == sorted([NONE, FAKE])
    assert [(c["mitigation"], c["episodes"]) for c in report.cell_rows(rows)] == [
        (NONE, 1),
        (FAKE, 1),
    ]
    # resumable per arm: a rerun skips both banked episodes
    assert run_mod.main(argv) == 0
    assert sorted(p.name for p in runs.iterdir()) == names


def test_api_key_pi_arm_banks_stamped_with_its_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from api_key import cells, mitigations
    from api_key.tests.conftest import run_fake

    monkeypatch.setitem(mitigations.MITIGATIONS, FAKE, _arm())

    def same_world(scenario: str, formation: str, epoch: int, mitigation: str) -> Any:
        return cells.build_cell(scenario, formation, epoch)

    monkeypatch.setattr(mitigations, "build_cell", same_world)
    runs = tmp_path / "runs"
    assert run_fake(runs, formation="coordinator", extra=("--mitigation", FAKE)) == 0
    assert run_fake(runs, formation="coordinator") == 0
    by_arm: dict[str, tuple[str, dict[str, Any]]] = {}
    for run_dir in runs.iterdir():
        loaded = load_run(run_dir)
        assert loaded is not None
        by_arm[str(loaded[1].get("mitigation", NONE))] = (run_dir.name, loaded[1])
    assert (
        by_arm[FAKE][0]
        == f"{by_arm[NONE][0].split('__claude')[0]}__mit-{FAKE}__claude-sonnet-5__e1__fakepi"
    )
    # the arm's record is the control's plus its `mitigation` key; the control's gains nothing
    assert "mitigation" not in by_arm[NONE][1]
    assert by_arm[FAKE][1] == {**by_arm[NONE][1], "mitigation": FAKE}
