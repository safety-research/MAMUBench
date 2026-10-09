"""`record.py`: the paper's episodes of record as jobs files the runner plays.

- `record.py --model M --formation F [--mitigation A]` writes one jobs file per (model, formation, arm) with the
  `run.py` command that plays it, each cell on its own instrument (`hero` for the coordinator, `standard` for the
  teams and the arms).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from _jobs import read_jobs_file

from clinic import cells, record
from clinic import run as run_mod

OPUS = "claude-opus-5"
QWEN = "qwen3.8-max"


def test_the_episodes_of_record_are_written_as_jobs_files_the_runner_plays(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def written(name: str, *argv: str) -> tuple[str, dict[str, int]]:
        out = tmp_path / name
        assert record.main([*argv, "--out-dir", str(out)]) == 0
        files = {p.name: len(read_jobs_file(p)) for p in sorted(out.iterdir())}
        return capsys.readouterr().out, files

    # the team: every one of its 480 episodes of record, one jobs file, one root
    printed, files = written("team", "--model", OPUS, "--formation", "team")
    assert (
        "arms: the formation itself" in printed and "mitigations_e1_10" not in printed
    )
    assert (
        "corpus_of_record   claude-opus-5    team         none  standard     480"
        in printed
    )
    assert files == {f"{OPUS}__team.csv": 480}
    (command,) = [line.strip() for line in printed.splitlines() if "run.py" in line]
    assert command.endswith(f"--model {OPUS} --runs-root eval/clinic/runs/results")
    printed, files = written(
        "qwen", "--model", "qwen/qwen3.8-max", "--formation", "coordinator"
    )
    assert files == {f"{QWEN}__coordinator.csv": 316}
    assert "--model qwen/qwen3.8-max --runs-root" in printed
    _, files = written("qwen_team", "--model", QWEN, "--formation", "team")
    assert files == {f"{QWEN}__team.csv": 232}
    _, files = written("s3", "--model", "claude-sonnet-5", "--mitigation", "s3")
    assert files == {"claude-sonnet-5__team__s3.csv": 240}
    _, files = written(
        "all", "--model", OPUS, "--formation", "team", "--mitigation", "all"
    )
    assert len(files) == 4
    assert record.main(["--model", OPUS, "--set", record.MITIGATION_SET]) == 0
    assert "arms: every arm" in capsys.readouterr().out
    assert record.main(["--model", "nobody"]) == 1
    s3 = read_jobs_file(tmp_path / "s3" / "claude-sonnet-5__team__s3.csv")
    assert {(j.formation, j.mitigation) for j in s3} == {("team", "s3")}
    assert {j.epoch for j in s3} == set(range(1, 11))
    # the runner plays a file as it is, each cell on its own instrument
    capsys.readouterr()
    team = tmp_path / "team" / f"{OPUS}__team.csv"
    assert (
        run_mod.main(["--jobs-file", str(team), "--model", OPUS, "--print-info"]) == 0
    )
    plan = capsys.readouterr().out
    assert plan.startswith("480 episode(s): jobs file")
    assert " team         instrument=standard max_turns=5000 " in plan


def test_every_episode_of_record_is_on_the_instrument_the_release_plays() -> None:
    assert record.own_instrument("coordinator", "none") == "hero"
    for formation, arm in (("team", "none"), ("team_silent", "none"), ("team", "s3")):
        assert record.own_instrument(formation, arm) == "standard"
    rows = record.load()
    assert {r.instrument for r in rows} == {"hero", "standard"}
    assert all(
        r.instrument == record.own_instrument(r.formation, r.mitigation) for r in rows
    )
    assert sum(len(jobs) for jobs in record.jobs_by_cell(rows).values()) == len(rows)
    stray = record.RecordEpisode(
        model=OPUS,
        formation="team",
        mitigation="none",
        scenario="warfarin_inr_split",
        epoch=1,
        instrument="hero",
        set="corpus_of_record",
        source="original_keep",
        n_contests=1,
        met=1,
        joint=1,
        plan_extra=0,
    )
    with pytest.raises(ValueError, match="not the one the release plays"):
        record.jobs_by_cell([stray])
    assert cells.PAPER_INSTRUMENT["team"] == cells.MITIGATION_INSTRUMENT == "standard"
