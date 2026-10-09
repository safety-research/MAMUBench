"""The root launcher `run.py`: what it refuses, and the Modal and local commands it runs.

Plus the eval CLI defaults it relies on: the paper's harness by default and no simulated-harness override.
"""

from __future__ import annotations

import csv
import importlib
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import _matrix
import pytest
from _harness import runner
from api_key import run as api_key_run
from clinic import run as clinic_run

import run
from tests.conftest import write

Launched = list[tuple[list[str], dict[str, str]]]
KEYS = {"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o", "OPENROUTER_API_KEY": "r"}


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every provider key set (never used: every subprocess is stubbed)."""
    for name, value in KEYS.items():
        monkeypatch.setenv(name, value)


def _after(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def _jobs(path: str) -> list[tuple[str, str, int, str]]:
    with open(path, newline="") as handle:
        return [
            (r["scenario"], r["formation"], int(r["epoch"]), r["mitigation"])
            for r in csv.DictReader(handle)
        ]


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ["merge_queue", "--harness", "sim"],
            "--harness sim is available for api_key and clinic",
        ),
        (["merge_queue", "--fake-pi"], "merge_queue has no offline stand-in"),
        (["api_key", "--episodes", "0"], "must be positive"),
        (["api_key", "--runs-name", "../escape"], "single directory name"),
        (
            ["api_key", "--jobs-file", "j.csv", "--episodes", "2"],
            "--jobs-file lists every episode",
        ),
        # a container sees only the shipped keys and writes the Volume's root
        (["api_key", "--key-env", "X"], "--key-env is local only"),
        (["clinic", "--runs-root=/tmp/x"], "--runs-root is local only"),
        # episodes per cell is --episodes: --epochs (and what argparse would have abbreviated to it) is refused,
        # not forwarded to a launch that would plan the full matrix
        (
            ["api_key", "--epochs", "1"],
            "unknown option --epochs (episodes per cell is --episodes)",
        ),
        (["clinic", "--epochs=2"], "unknown option --epochs (episodes per cell"),
        (["merge_queue", "--epoch", "2"], "unknown option --epoch (episodes per cell"),
        # printing what a launch would do without running it is --print-info: --dry-run (and what argparse would
        # have abbreviated to it) is refused, not forwarded to a launch that would run
        (
            ["api_key", "--dry-run"],
            "unknown option --dry-run (printing what a launch would do without running it is --print-info)",
        ),
        (
            ["personal_assistant", "--dry"],
            "unknown option --dry (printing what a launch",
        ),
        (["merge_queue", "--d", "--backend", "local"], "unknown option --d (printing"),
    ],
)
def test_the_launcher_refuses_a_bad_invocation_before_anything_runs(
    argv: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as refused:
        run.parse_args(argv)
    assert refused.value.code == 2
    assert message in capsys.readouterr().err


def test_the_launcher_forwards_epoch0_and_reads_an_episodes_abbreviation() -> None:
    assert run.parse_args(["api_key", "--epoch0", "3"])[1] == ["--epoch0", "3"]
    assert run.parse_args(["api_key", "--epi", "2"])[0].episodes == 2


@pytest.mark.parametrize(
    ("env", "selection"),
    [
        ("api_key", ["--scenario", "stakes_100"]),
        ("clinic", ["--board", "warfarin_inr_split"]),
        ("personal_assistant", ["--scenario", "watchparty_priority_fee"]),
        ("merge_queue", ["--scenario", "oversub"]),
    ],
)
def test_the_eval_clis_refuse_epochs_and_never_read_epoch_as_epoch0(
    env: str, selection: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Episodes per cell is `--episodes`: `--epochs` is refused and `--epoch N` stays ambiguous (not `--epoch0 N`)."""
    run_mod = importlib.import_module(f"{env}.run")
    for argv, message in (
        (
            ["--epochs", "2"],
            "unknown option --epochs (episodes per cell is --episodes)",
        ),
        (["--epochs=2"], "unknown option --epochs (episodes per cell is --episodes)"),
        (["--epochs"], "unknown option --epochs (episodes per cell is --episodes)"),
        (["--epoch", "2"], "ambiguous option: --epoch could match"),
    ):
        with pytest.raises(SystemExit) as refused:
            run_mod.parse_args([*selection, *argv])
        assert refused.value.code == 2
        assert message in capsys.readouterr().err
    args = run_mod.parse_args([*selection, "--episodes", "2", "--epoch0", "3"])
    assert (args.episodes, args.epoch0) == (2, 3)
    with pytest.raises(SystemExit):
        run_mod.parse_args(["--help"])
    assert "--epochs" not in capsys.readouterr().out


@pytest.mark.parametrize(
    ("env", "selection"),
    [
        ("api_key", ["--scenario", "stakes_100"]),
        ("clinic", ["--board", "warfarin_inr_split"]),
        ("personal_assistant", ["--scenario", "watchparty_priority_fee"]),
        ("merge_queue", ["--scenario", "oversub"]),
    ],
)
def test_the_eval_clis_refuse_dry_run_and_name_print_info(
    env: str, selection: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    """Printing the job matrix without running it is `--print-info`: a leftover `--dry-run` is refused, not run."""
    run_mod = importlib.import_module(f"{env}.run")
    for argv in (["--dry-run"], ["--dry"], ["--print-info", "--dry-run"]):
        with pytest.raises(SystemExit) as refused:
            run_mod.parse_args([*selection, *argv])
        assert refused.value.code == 2
        assert (
            "unknown option --dry-run (printing the job matrix without running it is --print-info)"
            in capsys.readouterr().err
        )
    assert run_mod.parse_args([*selection, "--print-info"]).print_info
    with pytest.raises(SystemExit):
        run_mod.parse_args(["--help"])
    out = capsys.readouterr().out
    assert "--dry-run" not in out and "--print-info" in out


def test_a_plan_the_environment_cannot_run_is_refused(
    launched: Launched, keys: None, capsys: pytest.CaptureFixture[str]
) -> None:
    for argv, message in (
        (["clinic", "--formation", "solo"], "runs no solo formation"),
        (["clinic", "--mitigation", "nope"], "unknown clinic mitigation 'nope'"),
        (["api_key", "--mitigation", "lead_value", "--harness", "pi"], "not pi"),
        (["merge_queue", "--scenario", "baseline_tight"], "not among the paper's"),
        # an arm that plays listed episodes names its list when a narrowing leaves none
        (
            ["personal_assistant", "--mitigation", "guard"]
            + ["--scenario", "watchparty_priority_fee", "--model", "claude-sonnet-5"],
            "nothing to run: the paper's personal_assistant guard runs play only the episodes listed in "
            "eval/personal_assistant/mitigations/",
        ),
    ):
        assert run.main(argv) == 2
        assert message in capsys.readouterr().err
    assert not launched


def test_the_default_launch_is_the_whole_matrix_detached_on_modal(
    monkeypatch: pytest.MonkeyPatch,
    launched: Launched,
    keys: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("EVAL_MODAL_TIMEOUT_S", raising=False)
    assert run.main(["clinic"]) == 0
    ((command, env),) = launched
    assert command[3:6] == [
        "run",
        "--detach",
        str(run.ROOT / "eval" / "modal_app.py") + "::main",
    ]
    assert (
        _after(command, "--eval") == "clinic"
        and _after(command, "--runs-name") == "results"
    )
    assert command[-1] == "--spawn-driver"
    for narrowing in (
        "--model",
        "--formation",
        "--scenario",
        "--episodes",
        "--mitigation",
    ):
        assert narrowing not in command  # the app resolves the same plan
    # sized for the teams' 16 h morning (one pass) + margin, which covers the coordinator's 2 h + 8 h re-fly
    assert env["EVAL_MODAL_TIMEOUT_S"] == str(57600 + 1800)
    out = capsys.readouterr().out
    assert (
        "clinic: 5236 episode(s), 24 scenario(s) -> Modal Volume clinic/results" in out
    )
    assert "results_" not in out and "+ after" not in out  # one root, one pass


def test_options_ride_the_modal_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, launched: Launched, keys: None
) -> None:
    monkeypatch.delenv("EVAL_MODAL_TIMEOUT_S", raising=False)
    argv = [
        "api_key",
        "--model",
        "claude-opus-5",
        "gpt-5.6-sol",
        "--formation",
        "coordinator",
        "team",
        "--scenario",
        "stakes_100",
        "--episodes",
        "2",
        "--fake-model",
        "--fake-scripts",
        "/tmp/a b.json",
    ]
    assert run.main(argv) == 0
    command = launched[-1][0]
    assert _after(command, "--model") == "claude-opus-5,gpt-5.6-sol"
    assert _after(command, "--formation") == "coordinator,team"
    assert (_after(command, "--scenario"), _after(command, "--episodes")) == (
        "stakes_100",
        "2",
    )
    assert (
        "--fake-model" in command
        and _after(command, "--extra") == "--fake-scripts '/tmp/a b.json'"
    )
    assert _after(command, "--runs-name") == "results_fake"
    assert (
        "EVAL_MODAL_TIMEOUT_S" not in launched[-1][1]
    )  # an offline stand-in finishes in seconds
    jobs = write(
        tmp_path / "team.csv", "scenario,formation,epoch\nwarfarin_inr_plain,team,3\n"
    )
    assert (
        run.main(["clinic", "--jobs-file", str(jobs), "--model", "claude-opus-5"]) == 0
    )
    command, env = launched[-1]
    assert _after(command, "--jobs-file") == str(jobs.resolve())
    # a jobs file's team mornings play the team's one 16 h pass
    assert (
        _after(command, "--runs-name") == "team"
        and env["EVAL_MODAL_TIMEOUT_S"] == "59400"
    )
    # a caller's own timeout is kept, and the pi harness needs none
    monkeypatch.setenv("EVAL_MODAL_TIMEOUT_S", "86400")
    assert run.main(["clinic", "--scenario", "warfarin_inr_plain"]) == 0
    assert launched[-1][1]["EVAL_MODAL_TIMEOUT_S"] == "86400"
    monkeypatch.delenv("EVAL_MODAL_TIMEOUT_S")
    assert run.main(["api_key", "--harness", "pi", "--scenario", "stakes_100"]) == 0
    assert "EVAL_MODAL_TIMEOUT_S" not in launched[-1][1]
    assert _after(launched[-1][0], "--runs-name") == "pi"


def test_the_preflight_names_missing_keys_before_anything_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    launched: Launched,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for name in (*KEYS, "OPEN_ROUTER_KEY"):
        monkeypatch.delenv(name, raising=False)
    empty = str(write(tmp_path / "empty.env", ""))
    assert run.main(["merge_queue", "--env-file", empty]) == 2
    assert (
        "missing provider key(s): ANTHROPIC_API_KEY (for claude-opus-5, claude-sonnet-5)"
        in capsys.readouterr().err
    )
    assert not launched
    # `--print-info` and an offline stand-in need no key
    assert (
        run.main(
            ["api_key", "--scenario", "stakes_100", "--fake-model", "--env-file", empty]
        )
        == 0
    )
    assert (
        run.main(
            [
                "merge_queue",
                "--scenario",
                "oversub",
                "--print-info",
                "--env-file",
                empty,
            ]
        )
        == 0
    )


def test_a_modal_print_info_prints_the_modal_command_and_resolves_the_plan_locally(
    launched: Launched, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--render-to` renders the local `--print-info`; the printed Modal command must work as copied."""
    for render in (["--render-to", "/tmp/briefs"], ["--render-to=/tmp/briefs"]):
        capsys.readouterr()
        argv = [
            "merge_queue",
            "--scenario",
            "oversub",
            "--model",
            "claude-opus-5",
            "--print-info",
            *render,
        ]
        assert run.main(argv) == 0
        command, _ = launched[-1]
        out = capsys.readouterr().out
        (modal_line,) = [
            line for line in out.splitlines() if line.startswith("Modal command: ")
        ]
        assert "--render-to" not in modal_line and "--extra" not in modal_line
        assert f"left out of the Modal command: {shlex.join(render)}" in out
        # the plan itself is the eval's own `--print-info`, over a jobs file of the model's episodes, and it renders
        assert (
            command[1].endswith("eval/merge_queue/run.py") and "--print-info" in command
        )
        assert command[-len(render) :] == render
    kept, removed = run.without_local_print_info_options(
        ["--parallel", "2", "--render-to", "d", "--thinking=off"]
    )
    assert (kept, removed) == (
        ["--parallel", "2", "--thinking=off"],
        ["--render-to", "d"],
    )
    # a listing runs locally
    assert run.main(["clinic", "--list-mitigations"]) == 0
    assert (
        launched[-1][0][1].endswith("eval/clinic/run.py")
        and launched[-1][0][-1] == "--list-mitigations"
    )


def test_a_local_launch_plays_each_model_into_one_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    keys: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each model's episodes, the clinic team's included, are one runner call into the one root."""
    calls: list[tuple[list[str], list[tuple[str, str, int, str]]]] = []

    def execute(command: list[str], **kwargs: Any) -> object:
        calls.append((command, _jobs(_after(command, "--jobs-file"))))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(run.subprocess, "run", execute)
    root = (tmp_path / "results").resolve()
    argv = ["clinic", "--backend", "local", "--scenario", "warfarin_inr_plain"]
    argv += ["--episodes", "2", "--fake-model", "--runs-root", str(root)]
    assert run.main([*argv, "--model", "claude-opus-5", "qwen/qwen3.8-max"]) == 0
    opus, qwen = calls
    assert _after(opus[0], "--model") == "claude-opus-5"
    assert _after(opus[0], "--runs-root") == str(root)
    assert opus[1] == [
        ("warfarin_inr_plain", f, e, "none")
        for f in ("coordinator", "team", "team_silent")
        for e in (1, 2)
    ]
    assert _after(qwen[0], "--model") == "qwen/qwen3.8-max"
    assert _after(qwen[0], "--runs-root") == str(root)
    assert not list(
        tmp_path.iterdir()
    )  # no second root beside it (the stubbed runner makes none)
    capsys.readouterr()
    # `all` plays every arm, one runner call per model
    calls.clear()
    assert run.main([*argv, "--mitigation", "s3"]) == 0
    assert [_after(c, "--model") for c, _ in calls] == list(_matrix.CLAUDE)
    calls.clear()
    assert run.main([*argv, "--mitigation", "all"]) == 0
    assert [_after(c, "--model") for c, _ in calls] == list(_matrix.CLAUDE)
    assert {job[3] for _, jobs in calls for job in jobs} == {"s1", "s2", "s3"}


def test_a_modal_print_info_of_the_personal_assistant_shows_the_containers_isolation(
    launched: Launched, capsys: pytest.CaptureFixture[str]
) -> None:
    """Inside a Modal container `--isolation auto` is root, not the launching host's none."""
    argv = [
        "personal_assistant",
        "--scenario",
        "kestrel_quiz_booth",
        "--model",
        "opus",
        "--print-info",
        "--verbose",
    ]
    assert run.main(argv) == 0
    # the paper runs, then the AGENTS.md-in-context rerun, each with the container's isolation
    (paper, _), (context_files, _) = launched
    assert _after(paper, "--isolation") == "root" and "--context-files" not in paper
    assert _after(context_files, "--isolation") == "root"
    assert _after(context_files, "--context-files") == "on"
    assert "resolves to root inside each Modal container" in capsys.readouterr().out
    # an explicit choice is the user's, and a local `--print-info` resolves on this host
    launched.clear()
    assert run.main([*argv, "--isolation", "none"]) == 0
    assert [c.count("--isolation") for c, _ in launched] == [1, 1]
    assert _after(launched[-1][0], "--isolation") == "none"
    assert run.main([*argv, "--backend", "local"]) == 0
    assert "--isolation" not in launched[-1][0]


def test_print_info_prints_the_plan_and_the_modal_command_only(
    launched: Launched, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without --verbose no eval runner is asked for its per-episode plan; the header names the Volume's roots."""
    assert run.main(["personal_assistant", "--print-info"]) == 0
    assert not launched
    out = capsys.readouterr().out.splitlines()
    assert out[0] == (
        "personal_assistant: 22500 episode(s), 25 scenario(s) -> Modal Volume personal_assistant/results"
    )
    (context,) = [
        line for line in out if line.startswith("personal_assistant (AGENTS.md")
    ]
    assert context == (
        "personal_assistant (AGENTS.md in context): 10000 episode(s), 25 scenario(s) -> Modal Volume "
        "personal_assistant/context_files"
    )
    assert out[-1].startswith("Modal command: ") and len(out) < 20
    assert run.main(["api_key", "--backend", "local", "--print-info"]) == 0
    assert not launched


def test_the_launchers_print_info_resolves_a_jobs_file_end_to_end(
    tmp_path: Path,
) -> None:
    """Through `run.py` and the eval's own runner: a GPT target's jobs file on the paper's settings needs no key."""
    path = write(
        tmp_path / "jobs.csv",
        "scenario,formation,epoch\nstakes_100,team,4\npeq_brb_n4_105,coordinator,9\n",
    )
    argv = [
        "api_key",
        "--jobs-file",
        str(path),
        "--model",
        "gpt-5.6-sol",
        "--print-info",
        "--verbose",
    ]
    proc = subprocess.run(
        [sys.executable, str(run.ROOT / "run.py"), *argv],
        capture_output=True,
        text=True,
        cwd=run.ROOT,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert (
        f"--jobs-file {path.resolve()}" in out and "--runs-name jobs " in out
    )  # the Modal command
    assert "provider=openai" in out and "harness=sim" in out
    # each listed cell on its paper settings, and the Modal timeout sized for them (limits_off: 2 h + 8 h retry)
    assert "  stakes_100         team         instrument=limits_off" in out
    assert "  peq_brb_n4_105     coordinator  instrument=hero" in out
    assert "EVAL_MODAL_TIMEOUT_S=37800" in out
    assert (
        "  stakes_100         team         e4" in out
        and "  peq_brb_n4_105     coordinator  e9" in out
    )


def test_the_eval_clis_default_to_the_papers_harness_and_the_pi_stand_in_selects_pi() -> (
    None
):
    assert api_key_run.parse_args(["--scenario", "stakes_100"]).harness == "sim"
    assert clinic_run.parse_args(["--board", "warfarin_inr_split"]).harness == "sim"
    assert (
        api_key_run.parse_args(["--scenario", "stakes_100", "--fake-pi"]).harness
        == "pi"
    )
    assert run.parse_args(["api_key"])[0].harness == "sim"
    args, extra = run.parse_args(["clinic", "--fake-pi"])
    assert args.harness == "pi" and extra == ["--fake-pi"]
    assert run.parse_args(["personal_assistant"])[0].harness == "pi"
    # the clinic CLI takes --scenario as an alias of --board
    assert clinic_run.parse_args(["--scenario", "warfarin_inr_split"]).board == [
        "warfarin_inr_split"
    ]
    # the paper ran GPT-5.6 and Qwen3.8-max on the simulated harness: the provider follows the model id
    for argv, provider in (
        (["--provider", "openai", "--harness", "sim"], "openai"),
        (["--model", "gpt-5.6-sol"], "openai"),
        (["--model", "qwen/qwen3.8-max"], "openrouter"),
    ):
        args = api_key_run.parse_args(["--scenario", "stakes_100", *argv])
        config = runner.config_from_args(
            args,
            eval_name="api_key",
            scenario="stakes_100",
            formation="team",
            default_runs_root=Path("/tmp/unused"),
        )
        assert (config.provider, config.harness) == (provider, "sim")


def test_no_simulated_harness_setting_can_be_overridden(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every cell plays the settings behind its paper number: the eval CLIs offer no override."""
    for override in (
        ["--sim-instrument", "hero"],
        ["--sim-reasoning", "high"],
        ["--sim-max-turns", "50"],
        ["--sim-max-ahead", "9"],
        ["--sim-time-limit", "600"],
    ):
        for parse, which in (
            (api_key_run.parse_args, ["--scenario", "stakes_100"]),
            (clinic_run.parse_args, ["--board", "warfarin_inr_split"]),
        ):
            with pytest.raises(SystemExit) as refused:
                parse([*which, *override])
            assert refused.value.code == 2
            assert "unrecognized arguments" in capsys.readouterr().err
