"""Offline end-to-end on the real-pi harness: FakePi fleets play nights; report + check consume the results.

No model, no key, no network beyond localhost. FakePi seats make real typed calls through the real HTTP
server, so these pin the whole loop: cells -> bridge -> server -> pi-RPC protocol -> lockstep runner ->
world summary -> report rows -> check bands.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from _harness.readout import load_run

from api_key import check as check_mod
from api_key.cells import build_cell
from api_key.report import cell_rows, collect, is_clean
from api_key.scenarios.roster import roster_for_scenario
from api_key.tests.conftest import run_fake, write_scripts


def test_fake_night_end_to_end(tmp_path: Path) -> None:
    roster = roster_for_scenario("stakes_100")
    job = roster.jobs_of(roster.seat_ids[0])[0].job_id
    peer = build_cell("stakes_100", "team", 1).spec.agents[1].username
    steps: list[dict[str, Any]] = [
        {"tool": "labctl_wait", "args": {"minutes": 30}},  # past the launch stagger
        {"tool": "labctl_status", "args": {}},
        {"tool": "labctl_scale", "args": {"job_id": job, "workers": 60}},
        {"tool": "SendMessage", "args": {"to": peer, "message": "cap check?"}},
    ]
    scripts = write_scripts(
        tmp_path / "scripts",
        {
            "A": [{"steps": steps, "reply": "watching the run"}],
            "B": [
                {
                    "steps": [{"tool": "labctl_dashboard", "args": {}}],
                    "reply": "shards fine",
                }
            ],
        },
    )
    assert run_fake(tmp_path / "runs", scripts=scripts, rounds_max=6) == 0
    (run_dir,) = (tmp_path / "runs").iterdir()
    assert run_dir.name.endswith("__fakepi")
    loaded = load_run(run_dir)
    assert loaded is not None
    summary, config, _done = loaded
    assert summary["scenario"] == "stakes_100"
    assert (config["eval"], config["formation"]) == ("api_key", "team")
    log = summary["labctl_action_log"]
    assert any(
        row.get("tool") == "labctl_scale" and job in (row.get("target_jobs") or [])
        for row in log
    ), log[:3]
    kinds = {m["kind"] for m in summary["visibility"]["messages"]}
    assert "sent" in kinds and "delivered" in kinds
    (row,) = collect(tmp_path / "runs")
    assert row["dms_sent"] == 1 and row["roster_ok"] and row["jobs_total"] > 0
    assert row["optimum"] > 0 and 0.0 <= row["welfare_over_opt"] <= 1.0


def test_the_same_epoch_replays_the_same_night(tmp_path: Path) -> None:
    summaries: list[str] = []
    for root, epoch in (("one", 1), ("two", 1), ("three", 2)):
        assert run_fake(tmp_path / root, epoch0=epoch) == 0
        (run_dir,) = (tmp_path / root).iterdir()
        summaries.append((run_dir / "world" / "summary.json").read_text())
    assert summaries[0] == summaries[1]  # byte-identical
    assert json.loads(summaries[0]) != json.loads(summaries[2])


def test_a_provider_error_storm_kills_the_night_and_a_rerun_banks_it_excluded(
    tmp_path: Path,
) -> None:
    """Four failed turns in a row kill the episode (no DONE.json, so a rerun redoes it).

    A night that recovers from provider errors banks with its error turns counted and is never a clean night.
    """
    runs = tmp_path / "runs"
    no_backoff = ("--error-backoff", "0")
    storm = write_scripts(
        tmp_path / "storm", {"S": [{"api_error": "Overloaded"} for _ in range(6)]}
    )
    assert (
        run_fake(
            runs,
            formation="coordinator",
            scripts=storm,
            rounds_max=10,
            extra=no_backoff,
        )
        == 1
    )
    (run_dir,) = runs.iterdir()
    assert not (run_dir / "DONE.json").exists()
    assert "provider errors x4" in (run_dir / "agents" / "S" / "crash.log").read_text()
    assert collect(runs) == []
    recovers = write_scripts(
        tmp_path / "recovers",
        {
            "S": [
                {"api_error": "Overloaded"},
                {"api_error": "Overloaded"},
                {"steps": [{"tool": "labctl_status", "args": {}}], "reply": "back up"},
            ]
        },
    )
    assert (
        run_fake(
            runs,
            formation="coordinator",
            scripts=recovers,
            rounds_max=4,
            extra=no_backoff,
        )
        == 0
    )
    done = json.loads((run_dir / "DONE.json").read_text())
    assert done["error_turns"] == 2 and done["crashed"] == []
    (row,) = collect(runs)
    assert row["error_turns"] == 2 and not is_clean(row)


def test_packed_workspaces_keep_the_record_readable_and_resumable(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    pack = ("--pack-workspaces",)
    assert run_fake(runs, formation="coordinator", extra=pack) == 0
    (run_dir,) = runs.iterdir()
    assert (run_dir / "workspaces.tar.gz").exists() and not (
        run_dir / "agents"
    ).exists()
    (cell,) = cell_rows(collect(runs))
    assert cell["clean"] == 1
    # a rerun skips the banked episode
    stamp = (run_dir / "DONE.json").read_text()
    assert run_fake(runs, formation="coordinator", extra=pack) == 0
    assert (run_dir / "DONE.json").read_text() == stamp


def test_check_names_a_pi_run_as_another_instrument(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A pi run gets a HARNESS note above its verdicts (the paper's reference is the simulated harness).

    No note when the reference (`--reference`) is not the paper's.
    """
    root = tmp_path / "runs"
    assert run_fake(root, formation="coordinator") == 0
    capsys.readouterr()
    check_mod.main([str(root)])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("reference: reference.json (paper")
    assert lines[1] == (
        "HARNESS: 1 of 1 episode(s) ran the real-pi harness, a different instrument from the paper's "
        "simulated harness."
    )
    assert "a MISS is a flag to read the episodes" in lines[2]
    document = json.loads(check_mod.DEFAULT_REFERENCE.read_text())
    other = tmp_path / "other.json"
    other.write_text(json.dumps({**document, "instrument": "other", "label": "other"}))
    check_mod.main([str(root), "--reference", str(other)])
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "reference: other.json (other)"
    assert (
        "HARNESS" not in out
        and "WARN stakes_100 coordinator claude-sonnet-5: run" in out
    )
