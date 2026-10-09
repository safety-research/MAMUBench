"""`--jobs-file` (explicit episodes) and `--mitigation` through the four eval runners.

The root launcher's side is `test_launcher.py`.

`--print-info` only: every matrix here is resolved and printed, never run. A registered stand-in arm (`fake_arm`)
drives the per-arm plumbing (validation, the `--print-info` listing, the forwarded flags).
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from _jobs import JobsFileError, JobSpec, read_jobs_file, write_jobs_file
from _mitigations import NONE

from tests.conftest import FAKE, write

# ── the file format ───────────────────────────────────────────────────────────────────────────────


def test_reads_episodes_comments_and_the_default_arm_and_round_trips(
    tmp_path: Path,
) -> None:
    path = write(
        tmp_path / "jobs.csv",
        "scenario,formation,epoch,mitigation\n"
        "# the paper's draw\n"
        "\n"
        "stakes_100,team,7,guard\n"
        " stakes_80 , coordinator , 12 , \n",
    )
    jobs = [
        JobSpec("stakes_100", "team", 7, "guard"),
        JobSpec("stakes_80", "coordinator", 12, NONE),
    ]
    assert read_jobs_file(path) == jobs
    assert read_jobs_file(path, default_mitigation="lead")[1].mitigation == "lead"
    no_column = write(tmp_path / "plain.csv", "epoch,formation,scenario\n3,team,s\n")
    assert read_jobs_file(no_column) == [JobSpec("s", "team", 3)]
    assert (JobSpec("s", "team", 3).label, JobSpec("s", "team", 3, "guard").label) == (
        "s/team/e3",
        "s/team/e3/guard",
    )
    write_jobs_file(tmp_path / "out" / "jobs.csv", jobs)
    assert read_jobs_file(tmp_path / "out" / "jobs.csv") == jobs


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (None, "no such file"),
        ("", "no header and no episode"),
        ("scenario,formation,epoch\n", "a header but no episode"),
        ("scenario,formation,epoch,model\ns,team,1,x\n", r"unknown \['model'\]"),
        ("scenario,formation,epoch\ns,team,zero\n", "line 2: epoch 'zero'"),
        ("scenario,formation,epoch\n\n# c\ns,,1\n", "line 4: empty formation"),
        ("scenario,formation,epoch\ns,team,1,extra\n", "line 2: more cells"),
        (
            "scenario,formation,epoch,mitigation\ns,team,1,\ns,team,1,none\n",
            "line 3: s/team/e1 repeats line 2",
        ),
    ],
)
def test_refuses_a_malformed_file(
    tmp_path: Path, text: str | None, message: str
) -> None:
    path = tmp_path / "jobs.csv"
    if text is not None:
        path.write_text(text)
    with pytest.raises(JobsFileError, match=message):
        read_jobs_file(path)


# ── the eval runners' --print-info ────────────────────────────────────────────────────────────────


def _plan(env: str, argv: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    run_mod = importlib.import_module(f"{env}.run")
    assert run_mod.main([*argv, "--print-info"]) == 0
    return capsys.readouterr().out


def test_api_key_matrix_with_an_arm(
    capsys: pytest.CaptureFixture[str], fake_arm: None
) -> None:
    argv = ["--scenario", "stakes_100", "--mitigation", FAKE]
    out = _plan("api_key", [*argv, "--formation", "team", "--harness", "pi"], capsys)
    assert f"mitigation={FAKE} ->" in out and out.rstrip().endswith(
        f"e1 mitigation={FAKE}"
    )
    # the arm applies to team only: coordinator is refused before anything runs
    with pytest.raises(SystemExit, match="not coordinator"):
        _plan("api_key", [*argv, "--formation", "coordinator"], capsys)


def test_clinic_jobs_file_holds_board_ids(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(
        tmp_path / "mornings.csv",
        "scenario,formation,epoch\nwarfarin_inr_split,team,4\nwarfarin_inr_plain,team_silent,9\n",
    )
    out = _plan("clinic", ["--jobs-file", str(path)], capsys)
    lines = out.splitlines()
    assert lines[0].startswith("2 episode(s): jobs file")
    # the simulated harness prints each cell's instrument, then the episodes
    assert "warfarin_inr_split                 team         instrument=standard" in out
    assert "warfarin_inr_plain                 team_silent  instrument=standard" in out
    assert lines[-2:] == [
        "  warfarin_inr_split                 team         e4",
        "  warfarin_inr_plain                 team_silent  e9",
    ]
    unknown = write(
        tmp_path / "bad.csv", "scenario,formation,epoch\nnot_a_board,team,1\n"
    )
    with pytest.raises(SystemExit, match="unknown board 'not_a_board'"):
        _plan("clinic", ["--jobs-file", str(unknown)], capsys)


def test_personal_assistant_jobs_file_groups_waves_by_arm(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fake_arm: None
) -> None:
    path = write(
        tmp_path / "draw.csv",
        "scenario,formation,epoch,mitigation\n"
        f"kestrel_quiz_booth,team,7,{FAKE}\n"
        f"kestrel_quiz_booth,team,12,{FAKE}\n"
        "kestrel_quiz_booth,team,7,\n",
    )
    out = _plan("personal_assistant", ["--jobs-file", str(path)], capsys)
    lines = out.splitlines()
    assert lines[0].startswith("3 episode(s): jobs file") and lines[0].endswith(
        f"mitigation={FAKE},none"
    )
    wave = f"kestrel_quiz_booth__claude-sonnet-5__mit-{FAKE}"
    assert [line.split() for line in lines[1:]] == [
        [f"kestrel_quiz_booth/team/e7/{FAKE}", "->", wave],
        [f"kestrel_quiz_booth/team/e12/{FAKE}", "->", wave],
        ["kestrel_quiz_booth/team/e7", "->", "kestrel_quiz_booth__claude-sonnet-5"],
    ]
    # the jobs-file default arm is --mitigation
    plain = write(
        tmp_path / "plain.csv", "scenario,formation,epoch\nkestrel_quiz_booth,team,3\n"
    )
    out = _plan(
        "personal_assistant", ["--jobs-file", str(plain), "--mitigation", FAKE], capsys
    )
    assert f"__mit-{FAKE}" in out


def test_merge_queue_jobs_file_and_arm(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], fake_arm: None
) -> None:
    path = write(
        tmp_path / "jobs.csv",
        f"scenario,formation,epoch,mitigation\noversub,team,5,{FAKE}\nbaseline_tight,coordinator,2,\n",
    )
    out = _plan("merge_queue", ["--jobs-file", str(path)], capsys)
    assert out.splitlines()[1:] == [
        f"  oversub          team         e5 mitigation={FAKE}",
        "  baseline_tight   coordinator  e2",
    ]
    from merge_queue import run as mq_run

    args = mq_run.parse_args(["--jobs-file", str(path)])
    jobs = mq_run.plan(args)
    argv = mq_run.drive_argv(
        args, jobs[0], provider="anthropic", key_env="K", pi_cmd="/pi"
    )
    assert argv[argv.index("--mitigation") + 1] == FAKE
    assert "--mitigation" not in mq_run.drive_argv(
        args, jobs[1], provider="anthropic", key_env="K", pi_cmd="/pi"
    )


@pytest.mark.parametrize(
    ("env", "argv"),
    [
        ("api_key", ["--scenario", "stakes_100"]),
        ("api_key", ["--episodes", "2"]),
        ("clinic", ["--all"]),
        ("clinic", ["--epoch0", "3"]),
        ("personal_assistant", ["--hero"]),
        ("merge_queue", ["--all"]),
    ],
)
def test_jobs_file_is_exclusive_with_the_matrix_flags(
    tmp_path: Path, env: str, argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path / "jobs.csv", "scenario,formation,epoch\nx,team,1\n")
    run_mod = importlib.import_module(f"{env}.run")
    with pytest.raises(SystemExit) as refused:
        run_mod.parse_args(["--jobs-file", str(path), *argv])
    assert refused.value.code == 2
    assert "--jobs-file lists every episode" in capsys.readouterr().err


_SOLO_SCENARIO = {
    "api_key": "stakes_100",
    "merge_queue": "oversub",
    "clinic": "warfarin_inr_split",
    "personal_assistant": "kestrel_quiz_booth",
}


# api_key and merge_queue implement solo (eval/api_key/tests/test_sim_e2e.py and the merge_queue
# formation tests cover the cells); their runners accept it from the CLI and from a jobs file.
@pytest.mark.parametrize("env", ["api_key", "merge_queue"])
def test_solo_is_accepted_where_implemented(
    env: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    scenario = _SOLO_SCENARIO[env]
    assert "solo" in importlib.import_module(f"{env}.scenarios").FORMATIONS
    out = _plan(env, ["--scenario", scenario, "--formation", "solo"], capsys)
    assert scenario in out and "solo" in out
    path = write(
        tmp_path / "solo.csv", f"scenario,formation,epoch\n{scenario},solo,1\n"
    )
    out = _plan(env, ["--jobs-file", str(path)], capsys)
    assert "1 episode(s)" in out and "solo" in out


# clinic and personal_assistant have no solo formation (the paper runs solo on API key and the merge
# queue only): the CLI refuses it as an unknown choice and a jobs file naming it is refused too.
@pytest.mark.parametrize(
    ("env", "listed"),
    [
        ("clinic", "unknown clinic formation 'solo'"),
        ("personal_assistant", "is wired for coordinator/team/team_silent only"),
    ],
)
def test_solo_is_refused_where_not_implemented(
    env: str, listed: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run_mod = importlib.import_module(f"{env}.run")
    scenario = _SOLO_SCENARIO[env]
    with pytest.raises(SystemExit) as refused:
        run_mod.parse_args(["--scenario", scenario, "--formation", "solo"])
    assert refused.value.code == 2
    assert "invalid choice: 'solo'" in capsys.readouterr().err
    path = write(
        tmp_path / "solo.csv", f"scenario,formation,epoch\n{scenario},solo,1\n"
    )
    with pytest.raises(SystemExit, match=listed):
        run_mod.main(["--jobs-file", str(path), "--print-info"])
