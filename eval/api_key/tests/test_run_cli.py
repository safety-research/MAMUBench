"""run.py's command line: what `--print-info` promises for each cell, and what it refuses before anything runs."""

from __future__ import annotations

from pathlib import Path

import pytest

from api_key import run as run_mod


def test_list_prints_the_scenarios_and_the_mitigation_arms(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_mod.main(["--list"]) == 0
    header, *rows = capsys.readouterr().out.splitlines()
    assert header.split() == ["scenario", "family", "seats", "budget", "org_cap"]
    assert len(rows) == 25
    assert rows[1].split() == ["stakes_100", "stakes", "4", "100,000,000", "400,000"]
    assert run_mod.main(["--list-mitigations"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("api_key mitigations (3):")
    assert "lead_value" in out and "lead_full_stack" in out and "research_id" not in out


def test_a_jobs_file_print_info_prints_each_cells_settings_of_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "jobs.csv"
    path.write_text(
        "scenario,formation,epoch,mitigation\n"
        "stakes_100,solo,3,none\n"
        "peq_duo_n16_409,team,7,lead_value\n"
        "stakes_n8_240,team,2,lead_full_stack\n"
        "stakes_80,team_silent,1,\n"
    )
    assert run_mod.main(["--jobs-file", str(path), "--print-info"]) == 0
    header, *lines = capsys.readouterr().out.splitlines()
    assert header.startswith(f"4 episode(s): jobs file {path}; model=claude-sonnet-5")
    assert "harness=sim parallel=1 mitigation=lead_full_stack,lead_value,none" in header
    settings = "knobs=- {}TARGET_REASONING=none serving=standard"
    assert lines == [
        "  stakes_100         solo         instrument=hero max_turns=800 burst=6 time_limit=7200s retry=None "
        + settings.format(""),
        "  peq_duo_n16_409    team         instrument=limits_off max_turns=1450 burst=1000000 time_limit=28800s "
        "retry=None " + settings.format("mitigation=lead_value "),
        "  stakes_n8_240      team         instrument=limits_off max_turns=1050 burst=1000000 time_limit=21600s "
        "retry=None " + settings.format("mitigation=lead_full_stack "),
        "  stakes_80          team_silent  instrument=limits_off max_turns=800 burst=1000000 time_limit=7200s "
        "retry=28800 " + settings.format(""),
        "  stakes_100         solo         e3",
        "  peq_duo_n16_409    team         e7 mitigation=lead_value",
        "  stakes_n8_240      team         e2 mitigation=lead_full_stack",
        "  stakes_80          team_silent  e1",
    ]


@pytest.mark.parametrize(
    ("model", "settings"),
    [
        ("gpt-5.6-sol", "TARGET_REASONING=medium serving=standard"),
        ("claude-opus-5", "TARGET_REASONING=none serving=standard"),
        ("qwen/qwen3.8-max", "TARGET_REASONING=minimal serving=standard"),
    ],
)
def test_every_model_plays_its_reasoning_of_record_on_the_default_formations(
    model: str, settings: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        run_mod.main(["--scenario", "stakes_100", "--model", model, "--print-info"])
        == 0
    )
    header, *lines = capsys.readouterr().out.splitlines()
    assert (
        "1 scenario(s) x ['coordinator', 'team', 'team_silent'] x epochs 1-1" in header
    )
    cells = [line for line in lines if "instrument=" in line]
    assert len(cells) == 3 and all(line.endswith(settings) for line in cells)


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ["--formation", "solo", "--harness", "pi"],
            "runs on the simulated harness only",
        ),
        (
            ["--formation", "team", "--mitigation", "lead_value", "--harness", "pi"],
            "'lead_value' is implemented for the sim harness, not pi",
        ),
        (
            ["--formation", "coordinator", "--mitigation", "lead_value"],
            "'lead_value' applies to formation(s) team, not coordinator",
        ),
        # the pi harness runs episodes concurrently; the simulated harness's dials are process-global
        (["--formation", "team", "--parallel", "4"], "plays one episode per process"),
        (["--harness", "pi", "--fake-model"], "--fake-model needs --harness sim"),
        (["--harness", "sim", "--fake-pi"], "the simulated harness's is --fake-model"),
        (
            ["--jobs-file", "jobs.csv"],
            "--jobs-file lists every episode; drop --scenario",
        ),
    ],
)
def test_the_cli_refuses_what_the_paper_never_ran(
    argv: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as refused:
        run_mod.main(["--scenario", "stakes_100", *argv, "--print-info"])
    assert message in f"{refused.value.code} {capsys.readouterr().err}"


def test_a_jobs_file_is_checked_like_the_flags(tmp_path: Path) -> None:
    path = tmp_path / "jobs.csv"
    pi = ["--jobs-file", str(path), "--harness", "pi", "--print-info"]
    path.write_text("scenario,formation,epoch\nstakes_100,captain,1\n")
    with pytest.raises(SystemExit, match="unknown api_key formation 'captain'"):
        run_mod.main(pi)
    path.write_text("scenario,formation,epoch\nstakes_100,solo,1\n")
    with pytest.raises(SystemExit, match="simulated harness only"):
        run_mod.main(pi)
    path.write_text("scenario,formation,epoch\nstakes_100,team,1\nstakes_80,team,1\n")
    assert run_mod.main([*pi, "--parallel", "4"]) == 0  # pi seats run concurrently
