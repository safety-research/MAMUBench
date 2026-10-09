"""The simulated harness end to end (`run.py --harness sim --fake-model`, no model call) and the launcher's CLI.

Every paper cell banks a fake morning under its own instrument, in the pi harness's run-dir shape; the readers
read it back and `check.py` compares every cell with the paper. The team's root reads every morning on its one
instrument, and no mix of recorded physics pools.
"""

from __future__ import annotations

import json
import shutil
import tarfile
from pathlib import Path
from typing import Any

import pytest
from _harness import sim
from _harness.readout import load_run
from _harness.runner import RunConfig

from clinic import cells, check, report
from clinic import run as run_mod
from clinic.tests.conftest import run_sim

BOARD = "warfarin_inr_split"


def _record(run_dir: Path, instrument: str) -> dict[str, Any]:
    """The run dir's recorded config, asserted to be `instrument`'s knob set at Sonnet's settings of record."""
    loaded = load_run(run_dir)
    assert loaded is not None
    summary, config, done = loaded
    knobs = cells.SIM_INSTRUMENTS[instrument]
    assert config["instrument"] == config["paper_instrument"] == instrument
    assert config["on_paper_instrument"] is True and config["off_paper"] == []
    assert (config["harness"], config["auditor"]) == ("sim", "none")
    assert config["max_turns"] == knobs.max_turns and config["burst"] == knobs.burst
    assert config["knobs"] == knobs.knobs
    assert config["generate_timeout_s"] == knobs.generate_timeout_s
    assert config["time_limit_s"] == knobs.time_limit_s
    assert config["dials"] == {"DEBRIEF_MIN": "9999"}
    assert config["harness_env"]["TARGET_THINKING"] == "0"
    assert config["target_serving"] == "standard"  # Sonnet: no extra request option
    assert summary["horizon_min"] == 240 and int(summary["clock"]) >= 240
    assert done["ended"].startswith("world horizon reached")
    assert done["rule_t_scanned"] is True and done["rule_t_lost_turns"] == 0
    return config


@pytest.mark.parametrize(
    ("formation", "instrument", "max_ahead"),
    [
        ("coordinator", "hero", 20),
        ("team", "standard", 1_000_000),
        ("team_silent", "standard", 1_000_000),
    ],
)
def test_a_paper_cell_banks_on_its_instrument_and_is_checked_against_the_paper(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    formation: str,
    instrument: str,
    max_ahead: int,
) -> None:
    runs = tmp_path / "runs"
    run_sim(runs, formation)
    (run_dir,) = runs.iterdir()
    topology = "steward" if formation == "coordinator" else "meshfull"
    comms = "comms" if formation == "team" else "nocomms"
    assert run_dir.name == (
        f"clinic_{BOARD}_{topology}_{comms}_tight_scripted__claude-sonnet-5__e1__sim__fakemodel"
    )
    assert _record(run_dir, instrument)["max_ahead"] == max_ahead
    episodes, contests = report.collect(runs)
    assert len(contests) == 6  # warfarin_inr is the six-contest pair
    (episode,) = episodes
    assert (episode["formation"], episode["instrument"]) == (formation, instrument)
    assert episode["endstate"] == "horizon" and episode["retired_physics"] is False
    assert report.is_clean(episode) and report.is_valid(episode)
    capsys.readouterr()
    assert check.main([str(runs)]) == 1  # a fake desk books nobody: a MISS
    out = capsys.readouterr().out
    assert out.startswith("reference: paper (joint success, scenario-averaged)\n")
    assert f"MISS {BOARD} {formation} claude-sonnet-5: run joint 0/6" in out
    assert "0 skipped" in out and "HARNESS" not in out


def test_the_team_root_reads_every_morning_and_no_other_physics_pools(
    tmp_path: Path,
) -> None:
    """A team root holds one instrument: every morning in it is read, and another scheduler's never pools."""
    team = tmp_path / "team"
    run_sim(team, "team")
    run_sim(team, "team", "--epoch0", "2")
    first, second = sorted(team.iterdir())
    for run_dir in (first, second):
        assert _record(run_dir, "standard")["max_ahead"] == 1_000_000
    episodes, _ = report.collect(team)
    assert sorted(int(e["epoch"]) for e in episodes) == [1, 2]
    assert {str(e["instrument"]) for e in episodes} == {"standard"}
    assert all(report.is_clean(e) and report.is_valid(e) for e in episodes)
    # a morning recorded with other physics (another scheduler, from other code) never pools
    other = team / first.name.replace("__e1__", "__e3__")
    shutil.copytree(first, other)
    config = json.loads((other / "world" / "config.json").read_text())
    config.update(epoch=3, instrument="hero")
    (other / "world" / "config.json").write_text(json.dumps(config))
    with pytest.raises(SystemExit, match="mixes simulated-harness instruments"):
        report.collect(team)


def test_a_banked_morning_is_skipped_and_a_restarted_one_keeps_its_earlier_logs(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    run_sim(runs, "coordinator")
    (run_dir,) = runs.iterdir()
    stamp = (run_dir / "DONE.json").read_text()
    run_sim(runs, "coordinator")
    assert (run_dir / "DONE.json").read_text() == stamp  # resumed: nothing reran
    # a preempted container's episode restarts from scratch: its logs are archived beside the run dir
    logs = sorted(p.name for p in (run_dir / "logs").glob("*.eval"))
    assert logs
    (run_dir / "DONE.json").unlink()
    run_sim(runs, "coordinator")
    archive = runs / f"{run_dir.name}.attempt1.tar.gz"
    assert sorted(runs.iterdir()) == sorted([run_dir, archive])
    with tarfile.open(archive, "r:gz") as tar:
        kept = {Path(m.name).name for m in tar.getmembers() if m.name.endswith(".eval")}
    assert kept == set(logs)
    assert len(report.collect(runs)[0]) == 1  # the archive is no run dir
    empty = tmp_path / "empty" / "x__e1__sim"
    (empty / "world").mkdir(parents=True)
    assert sim.keep_prior_attempt(empty) is None  # nothing ran yet: nothing to keep


def test_the_unused_auditor_seat_is_named_as_such(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The inspect header shows the house seat's model; the log says it is unused and names the target."""
    config = RunConfig(
        eval="clinic",
        scenario="warfarin_inr_plain",
        formation="coordinator",
        model="claude-sonnet-5",
        provider="anthropic",
        runs_root=tmp_path,
        harness="sim",
        fake_model=False,
    )
    recipe = cells.build_sim_recipe("warfarin_inr_plain", "coordinator")

    class Stop(Exception):
        pass

    def stop(*_args: object, **_kwargs: object) -> None:
        raise Stop

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sim, "_roles", stop)
        with pytest.raises(Stop):
            sim._play(  # pyright: ignore[reportPrivateUsage]
                config,
                recipe,
                1,
                sim.SimKeys("k", "k"),
                tmp_path / "run",
                {"target_effort": "0"},
                10,
                10,
                60,
            )
    out = capsys.readouterr().out
    assert (
        f"the inspect header's model {recipe.auditor_model} is the house auditor/judge seat, unused here"
        in out
    )
    assert "the target is anthropic/claude-sonnet-5" in out


@pytest.mark.parametrize(
    ("model", "settings"),
    [
        ("claude-sonnet-5", "TARGET_THINKING=0 serving=standard"),
        ("claude-opus-5", "TARGET_THINKING=0 serving=fast"),
        ("gpt-5.6-sol", "TARGET_THINKING=medium serving=priority"),
        ("qwen/qwen3.8-max", "TARGET_THINKING=low serving=standard"),
    ],
)
def test_print_info_prints_each_cells_instrument_and_the_models_settings(
    model: str, settings: str, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["--board", BOARD, "--formation", "coordinator", "team", "team_silent"]
    assert run_mod.main([*argv, "--model", model, "--print-info"]) == 0
    lines = [x for x in capsys.readouterr().out.splitlines() if "instrument=" in x]
    assert [x.split()[2] for x in lines] == [
        "instrument=hero",
        "instrument=standard",
        "instrument=standard",
    ]
    assert all(line.endswith(settings) for line in lines)


def test_the_launcher_refuses_what_the_paper_did_not_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = [
        "--board",
        "warfarin_inr_plain",
        "--runs-root",
        str(tmp_path),
        "--print-info",
    ]
    # the team plays one pass on its own instrument; there is no second one to ask for
    assert run_mod.main([*base, "--formation", "team"]) == 0
    out = capsys.readouterr().out
    assert "team         instrument=standard max_turns=5000" in out
    for argv, message in (
        ([*base, "--parallel", "4"], "plays one episode per process"),
        ([*base, "--jobs-file", str(tmp_path / "jobs.csv")], "drop --board"),
    ):
        with pytest.raises(SystemExit) as refused:
            run_mod.main(argv)
        assert refused.value.code == 2
        assert message in capsys.readouterr().err
    assert run_mod.main([*base, "--parallel", "4", "--harness", "pi"]) == 0
