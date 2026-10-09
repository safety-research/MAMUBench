"""`modal_app.py` offline: launch validation, the plan's lanes, dispatch, the remote episode.

The claim keeps one writer per episode through final persistence. Nothing runs on Modal.
"""

from __future__ import annotations

import inspect
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import _matrix
import modal_app
import pytest
from _mitigations import NONE
from modal.file_pattern_matcher import FilePatternMatcher

from tests.conftest import FAKE

Launch = Callable[..., list[Any]]
#: `modal_app.main` as a plain function (the local entrypoint's undecorated body).
modal_main = cast(Callable[..., None], modal_app.main.info.raw_f)
run_one = modal_app._run_one  # pyright: ignore[reportPrivateUsage]
KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")


@pytest.fixture
def lanes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """Every `dispatch.spawn(...)` call's arguments (nothing is spawned)."""
    spawned: list[tuple[Any, ...]] = []

    def spawn(*args: Any) -> object:
        spawned.append(args)
        return SimpleNamespace(object_id="fc-lane", get=lambda: {"unbanked": 0})

    monkeypatch.setattr(modal_app, "dispatch", SimpleNamespace(spawn=spawn))
    return spawned


@pytest.fixture
def modal_launch(
    lanes: list[tuple[Any, ...]], monkeypatch: pytest.MonkeyPatch
) -> Launch:
    """`modal_app.main(**options)` up to the spawn of its lanes; returns every job the lanes carry."""
    for name in KEYS:
        monkeypatch.setenv(name, "sk-test")  # never used: nothing is dispatched

    def launch(**options: Any) -> list[Any]:
        lanes.clear()
        modal_main(**options)
        return [job for lane in lanes for job in lane[0]]

    return launch


class Container:
    """A container's view of `_run_one`: the claims Dict (a fake), the Volume, the eval CLI and the packing.

    `events` logs every step in order (`claim`, `reload`, `pack`, `commit`, `release`, `retain`); `argv` collects
    each eval CLI invocation and `packed` each merge-queue packing call; `main` is the eval CLI's body.
    """

    def __init__(self) -> None:
        self.claims: dict[str, Any] = {}
        self.events: list[str] = []
        self.argv: list[list[str]] = []
        self.packed: list[tuple[Any, ...]] = []
        self.main: Callable[[list[str]], int] = lambda argv: 0

    def put(self, key: str, value: Any, *, skip_if_exists: bool = False) -> bool:
        if not skip_if_exists:  # an owner marking the claim it keeps (`_mark_retained`)
            assert key in self.claims
            self.claims[key] = value
            self.events.append("retain")
            return True
        if key in self.claims:
            return False
        self.claims[key] = value
        self.events.append("claim")
        return True

    def get(self, key: str) -> Any:
        return self.claims.get(key)

    def pop(self, key: str) -> Any:
        self.events.append("release")
        return self.claims.pop(key)


@pytest.fixture
def container(monkeypatch: pytest.MonkeyPatch) -> Container:
    seen = Container()

    def eval_main(name: str) -> Callable[[list[str]], int]:
        def main(argv: list[str]) -> int:
            seen.argv.append(argv)
            return seen.main(argv)

        return main

    def pack(*args: Any) -> None:
        seen.packed.append(args)
        seen.events.append("pack")

    monkeypatch.setattr(modal_app, "episode_claims", seen)
    monkeypatch.setattr(modal_app.modal, "current_function_call_id", lambda: "fc-owner")
    monkeypatch.setattr(modal_app.modal, "current_input_id", lambda: "in-owner")
    monkeypatch.setattr(
        modal_app,
        "volume",
        SimpleNamespace(
            object_id="vo-test", reload=lambda: seen.events.append("reload")
        ),
    )
    monkeypatch.setattr(
        modal_app, "_commit_with_retry", lambda: seen.events.append("commit")
    )
    monkeypatch.setattr(modal_app, "_pack_merge_queue_workspaces", pack)
    monkeypatch.setattr(modal_app, "_eval_main", eval_main)
    return seen


def mq_episode(**options: Any) -> dict[str, Any]:
    """`_run_one` of merge_queue oversub/team/e1 (the options override any argument)."""
    args: dict[str, Any] = {
        "eval_name": "merge_queue",
        "scenario": "oversub",
        "formation": "team",
        "epoch": 1,
        "model": "claude-sonnet-5",
        "provider": "anthropic",
        "runs_name": "test",
        "extra": [],
        **options,
    }
    return run_one(**args)


# ── the image and the launch ──────────────────────────────────────────────────────────────────────


def test_image_includes_jinja_runtime_tests() -> None:
    excluded = FilePatternMatcher(*modal_app._IGNORE)  # pyright: ignore[reportPrivateUsage]
    assert not excluded(
        Path("eval/merge_queue/environment/fixture/jinja/tests/test_security.py")
    )
    assert excluded(Path("eval/merge_queue/tests/test_hero_parity.py"))


def test_image_leaves_out_the_local_output_dirs() -> None:
    # analysis/stats.py's output and jobs files never ride into an image
    excluded = FilePatternMatcher(*modal_app._IGNORE)  # pyright: ignore[reportPrivateUsage]
    for path in (
        "analysis/out/stats.csv",
        "analysis/out/api_key/results/scores.csv",
        "eval/api_key/readouts/results/scores.csv",
        "eval/api_key/results/results/scores.csv",
        "jobs/claude-opus-5__team.csv",
    ):
        assert excluded(Path(path)), path
    # only those dirs: the script and same-named dirs inside the tree still ship
    for path in (
        "run.py",
        "analysis/stats.py",
        "eval/clinic/record.py",
        "eval/x/jobs/y.py",
    ):
        assert not excluded(Path(path)), path


def test_the_git_sha_is_unknown_without_git(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_git(*args: Any, **kwargs: Any) -> Any:
        raise FileNotFoundError(2, "No such file or directory", "git")

    monkeypatch.delenv("EVAL_GIT_SHA", raising=False)
    monkeypatch.setattr(modal_app.subprocess, "run", no_git)
    assert modal_app._git_sha() == "unknown"  # pyright: ignore[reportPrivateUsage]


def test_the_launch_secret_carries_the_knobs_containers_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # a container sees none of the launching shell's variables: the knobs it reads at import ride in the Secret
    for name in modal_app.FORWARDED_KNOBS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("EVAL_MODAL_CLAIMS", "isolated-claims")
    monkeypatch.setenv("EVAL_MODAL_DISPATCH_WINDOW", "8")
    env = modal_app.secret_env()
    assert env["EVAL_MODAL_CLAIMS"] == "isolated-claims"
    assert env["EVAL_MODAL_DISPATCH_WINDOW"] == "8"
    # an unset knob stays out, and the container keeps its default
    assert "EVAL_MODAL_VOLUME_ENV" not in env


def test_print_info_needs_no_key_or_remote_execution_and_lists_every_episode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    lanes: list[tuple[Any, ...]],
    fake_arm: None,
) -> None:
    for name in (*modal_app.KEY_VARS, "EVAL_KEY_ENV"):
        monkeypatch.delenv(name, raising=False)
    modal_main(probe=True, print_info=True)
    path = tmp_path / "jobs.csv"
    path.write_text(
        f"scenario,formation,epoch,mitigation\nstakes_100,team,7,{FAKE}\nstakes_80,coordinator,1,\n"
    )
    capsys.readouterr()
    modal_main(eval="api_key", jobs_file=str(path), print_info=True, harness="pi")
    out = capsys.readouterr().out.splitlines()
    assert (
        out[0]
        == f"api_key: 2 episode(s), 2 scenario(s) -> volume {modal_app.VOLUME_NAME}:/api_key/jobs"
    )
    assert out[-2:] == [
        f"  {'claude-sonnet-5':18} {'stakes_100':34} {'team':12} e7 mitigation={FAKE}",
        f"  {'claude-sonnet-5':18} {'stakes_80':34} {'coordinator':12} e1",
    ]
    assert not lanes


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"episodes": -1}, "must be positive"),
        ({"runs_name": "../escape"}, "single directory name"),
        ({"formation": "captain"}, "--formation must name"),
        ({"harness": "sim", "fake_pi": True}, "--fake-pi requires --harness pi"),
        ({"harness": "pi", "fake_model": True}, "--fake-model is the simulated"),
        # plan, harness and --print-info options are first-class, never smuggled through --extra
        ({"extra": "--harness sim"}, "not through --extra"),
        ({"extra": "--runs-r other"}, "not through --extra"),  # an abbreviation too
        ({"extra": "--print-info"}, "not through --extra"),
        ({"extra": f"--mitigation {FAKE}"}, "not through --extra"),
        # episodes per cell is --episodes: every container's runner would refuse --epochs
        ({"extra": "--epochs 1"}, "unknown option --epochs in --extra"),
        ({"extra": "--epochs=1"}, "unknown option --epochs in --extra"),
        # printing what a launch would do without running it is --print-info: --dry-run (and what argparse would
        # read as it) is refused
        ({"extra": "--dry-run"}, "unknown option --dry-run in --extra"),
        ({"extra": "--parallel 2 --dry"}, "unknown option --dry-run in --extra"),
        ({"eval": "clinic", "formation": "solo"}, "runs no solo formation"),
        ({"formation": "coordinator", "mitigation": FAKE}, "not coordinator"),
        (
            {"eval": "clinic", "mitigation": "missing"},
            "unknown clinic mitigation 'missing'",
        ),
        # a jobs file lists every episode
        ({"jobs_file": True, "scenario": "stakes_100"}, "--jobs-file lists every"),
        ({"jobs_file": True, "episodes": 2}, "--jobs-file lists every"),
    ],
)
def test_an_invalid_launch_is_rejected_before_execution(
    tmp_path: Path,
    lanes: list[tuple[Any, ...]],
    fake_arm: None,
    options: dict[str, Any],
    message: str,
) -> None:
    launch: dict[str, Any] = {"eval": "api_key", **options}
    if launch.get("jobs_file"):
        path = tmp_path / "jobs.csv"
        path.write_text("scenario,formation,epoch\nstakes_100,team,1\n")
        launch["jobs_file"] = str(path)
    with pytest.raises(SystemExit, match=message):
        modal_main(**launch)
    assert not lanes


# ── the plan `main` dispatches ────────────────────────────────────────────────────────────────────


def test_the_default_launch_is_the_papers_plan_one_lane_per_model(
    monkeypatch: pytest.MonkeyPatch, lanes: list[tuple[Any, ...]], modal_launch: Launch
) -> None:
    monkeypatch.setattr(modal_app, "EPISODE_TIMEOUT_S", 59400)
    jobs = modal_launch(eval="clinic", runs_name="results", spawn_driver=True)
    assert len(jobs) == len(_matrix.plan("clinic")) == 5236
    assert [lane[4].split("__", 1)[1] for lane in lanes] == [
        m.replace("/", "__") for m in _matrix.MODELS
    ]
    for lane in lanes:
        (model,) = {job[4] for job in lane[0]}
        assert len(lane) == 5 and lane[1:4] == (False, "clinic", "results")
        assert lane[4].endswith("__" + model.replace("/", "__"))
    assert jobs[0] == (
        "clinic",
        "warfarin_inr_plain",
        "coordinator",
        1,
        "claude-opus-5",
        "anthropic",
        "results",
        ["--harness", "sim"],
    )
    # the team needs its one 16 h morning inside the timeout (the coordinator's 2 h + 8 h re-fly needs less)
    monkeypatch.setattr(modal_app, "EPISODE_TIMEOUT_S", 37800)
    with pytest.raises(SystemExit, match="EVAL_MODAL_TIMEOUT_S=59400"):
        modal_launch(eval="clinic", formation="team", runs_name="results")
    assert modal_launch(eval="clinic", formation="coordinator", runs_name="results")
    monkeypatch.setattr(modal_app, "EPISODE_TIMEOUT_S", 59400)
    # narrowing options narrow the plan
    jobs = modal_launch(
        eval="clinic",
        mitigation="s3",
        model="claude-opus-5",
        scenario="warfarin_inr_plain",
        episodes=2,
    )
    assert [(j[2], j[3], j[-1]) for j in jobs] == [("team", 1, "s3"), ("team", 2, "s3")]


def test_claim_keys_keep_one_writer_per_episode_and_every_model_apart() -> None:
    key = modal_app.claim_key_for
    assert key(
        "merge_queue",
        "./run",
        "qwen/qwen3.8-max",
        "oversub",
        "team",
        3,
        volume_id="vo-1",
    ) == json.dumps(
        ["vo-1", "merge_queue", "run", "qwen__qwen3.8-max", "oversub", "team", 3],
        separators=(",", ":"),
    )
    assert key(
        "merge_queue",
        "run",
        "claude-opus-5",
        "oversub",
        "team",
        3,
        FAKE,
        volume_id="vo-1",
    ).endswith(f',"oversub","team",3,"{FAKE}"]')
    assert key(
        "clinic", "results", "claude-opus-5", "b", "team", 1, volume_id="v"
    ) != key("clinic", "results", "claude-sonnet-5", "b", "team", 1, volume_id="v")


def test_an_arm_rides_as_the_ninth_job_element_and_a_jobs_file_row_names_its_own(
    tmp_path: Path, modal_launch: Launch, fake_arm: None
) -> None:
    jobs = modal_launch(
        eval="personal_assistant",
        scenario="kestrel_quiz_booth",
        model="claude-sonnet-5",
        episodes=1,
        mitigation=FAKE,
        runs_name="draw",
    )
    assert len(jobs) == 1 and len(jobs[0]) == 9 and jobs[0][-1] == FAKE
    assert jobs[0][7] == []  # the eval CLI's extra args stay the 8th element
    path = tmp_path / "jobs.csv"
    path.write_text(
        f"scenario,formation,epoch,mitigation\noversub,team,7,{FAKE}\nbaseline_tight,coordinator,3,\n"
    )
    jobs = modal_launch(eval="merge_queue", jobs_file=str(path), runs_name="listed")
    assert [job[1:4] for job in jobs] == [
        ("oversub", "team", 7),
        ("baseline_tight", "coordinator", 3),
    ]
    assert [len(job) for job in jobs] == [9, 8] and jobs[0][-1] == FAKE
    # each row's arm is validated against its formation
    bad = tmp_path / "bad.csv"
    bad.write_text(
        f"scenario,formation,epoch,mitigation\noversub,coordinator,1,{FAKE}\n"
    )
    with pytest.raises(SystemExit, match="not coordinator"):
        modal_launch(eval="merge_queue", jobs_file=str(bad))
    # `--mitigation all`: every arm's runs (the stand-in's too), each job carrying its own arm
    jobs = modal_launch(
        eval="merge_queue", scenario="oversub", episodes=1, mitigation="all"
    )
    assert sorted((job[4], job[-1]) for job in jobs) == sorted(
        (model, arm)
        for model in ("claude-opus-5", "claude-sonnet-5")
        for arm in ("lead_cut_line", "priorities", "charter", "charter_stakes", FAKE)
    )


def test_a_sim_launch_forwards_its_harness_and_needs_the_instruments_timeout(
    monkeypatch: pytest.MonkeyPatch, modal_launch: Launch
) -> None:
    silent = {
        "eval": "clinic",
        "scenario": "warfarin_inr_plain",
        "formation": "team_silent",
        "episodes": 1,
    }
    # the offline stand-ins need no key and no instrument timeout: the default 5 h launches them
    monkeypatch.setattr(modal_app, "EPISODE_TIMEOUT_S", 5 * 3600)
    assert modal_launch(**silent, fake_model=True)[0][-1] == [
        "--harness",
        "sim",
        "--fake-model",
    ]
    team = {
        "eval": "api_key",
        "scenario": "stakes_100",
        "formation": "team",
        "episodes": 1,
    }
    assert modal_launch(**team, fake_pi=True)[0][-1] == ["--fake-pi", "--harness", "pi"]
    # the standard instrument's 16 h sample limit on the clinic silent team needs 57,600 s + margin per container
    with pytest.raises(SystemExit, match="EVAL_MODAL_TIMEOUT_S=59400"):
        modal_launch(**silent)
    monkeypatch.setattr(modal_app, "EPISODE_TIMEOUT_S", 59400)
    assert modal_launch(**silent)[0][-1] == ["--harness", "sim"]


def test_the_personal_assistants_lanes_carry_its_context_files_rerun(
    lanes: list[tuple[Any, ...]],
    modal_launch: Launch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each lane plays the model's paper runs, then its AGENTS.md-in-context rerun into `context_files`."""
    jobs = modal_launch(
        eval="personal_assistant",
        model="claude-opus-5",
        scenario="kestrel_quiz_booth",
        episodes=1,
        spawn_driver=True,
    )
    # Modal's own closing "App completed" is the launcher's exit, not the run's: the launch says so
    assert "`App completed` refers only to this launcher" in capsys.readouterr().out
    on = ["--context-files", "on"]
    assert [(j[2], j[6], j[7]) for j in jobs] == [
        ("coordinator", "results", []),
        ("team", "results", []),
        ("team_silent", "results", []),
        ("team", "context_files", on),
        ("team_silent", "context_files", on),
    ]
    ((_jobs, _heavy, _eval, first, _launch_id),) = lanes
    assert first == "results"
    assert modal_launch(
        eval="personal_assistant",
        model="gpt-5.6-sol",
        scenario="kestrel_quiz_booth",
        episodes=1,
    ) and {j[6] for lane in lanes for j in lane[0]} == {"results"}


def test_the_preflight_names_the_keys_a_launch_needs(
    monkeypatch: pytest.MonkeyPatch, modal_launch: Launch
) -> None:
    monkeypatch.setattr(modal_app, "EPISODE_TIMEOUT_S", 24 * 3600)
    gpt = {
        "eval": "api_key",
        "scenario": "stakes_100",
        "formation": "team",
        "model": "gpt-5.6-sol",
        "episodes": 1,
    }
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    # the house auditor and judge keep their Anthropic models on the Anthropic key
    with pytest.raises(SystemExit, match=r"ANTHROPIC_API_KEY \(for gpt-5.6-sol\)"):
        modal_launch(**gpt)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert modal_launch(**gpt)[0][4:6] == ("gpt-5.6-sol", "openai")
    # clinic's house roles are never called: the provider key alone suffices there
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.delenv("OPENAI_API_KEY")
    jobs = modal_launch(
        eval="clinic",
        scenario="warfarin_inr_plain",
        formation="team",
        model="qwen/qwen3.8-max",
        episodes=1,
    )
    assert jobs[0][4:6] == ("qwen/qwen3.8-max", "openrouter")
    monkeypatch.delenv("OPENROUTER_API_KEY")
    with pytest.raises(
        SystemExit, match=r"OPENROUTER_API_KEY \(for qwen/qwen3.8-max\)"
    ):
        modal_launch(
            eval="clinic",
            scenario="warfarin_inr_plain",
            model="qwen/qwen3.8-max",
            episodes=1,
        )


def _docstring_launches() -> list[tuple[dict[str, str], list[str]]]:
    """`(env prefix, argv)` of every `modal run ... eval/modal_app.py::main ...` command in the module docstring."""
    commands: list[str] = []
    pending = ""
    for raw in (modal_app.__doc__ or "").splitlines():
        line = raw.split("  # ", 1)[0].strip()
        if pending:
            line, pending = f"{pending} {line}", ""
        if line.endswith("\\"):
            pending = line[:-1].strip()
            continue
        if "modal_app.py::main" in line and not line.startswith("#"):
            commands.append(line)
    assert not pending, (
        f"a docstring command ends in a dangling continuation: {pending!r}"
    )
    launches: list[tuple[dict[str, str], list[str]]] = []
    for command in commands:
        words = shlex.split(command)
        cli = words.index("modal")
        # paste-ready from the repository root: the project venv's modal, never a bare `modal`
        assert words[cli - 2 : cli] == [".venv/bin/python", "-m"], command
        env = dict(w.split("=", 1) for w in words[: cli - 2])
        launches.append((env, words[words.index("eval/modal_app.py::main") + 1 :]))
    return launches


def test_every_docstring_launch_works_as_written(
    monkeypatch: pytest.MonkeyPatch, modal_launch: Launch
) -> None:
    # the usage block's commands run as printed: each reaches its spawn (stubbed) at its own EVAL_MODAL_TIMEOUT_S
    # prefix, or at the 5 h default when it has none (a pi or --fake-model launch), from the repository root
    monkeypatch.chdir(modal_app.REPO_ROOT)
    launches = _docstring_launches()
    assert len(launches) >= 7
    parameters = inspect.signature(modal_main).parameters
    ran = 0
    for env, argv in launches:
        if "--probe" in argv:
            continue  # remote only
        options: dict[str, Any] = {}
        words = iter(argv)
        for word in words:
            name = word.removeprefix("--").replace("-", "_")
            default = parameters[name].default
            options[name] = (
                True if isinstance(default, bool) else type(default)(next(words))
            )
        monkeypatch.setattr(
            modal_app,
            "EPISODE_TIMEOUT_S",
            int(env.get("EVAL_MODAL_TIMEOUT_S", 5 * 3600)),
        )
        assert modal_launch(**options), argv
        ran += 1
    assert ran >= 7


# ── dispatch ──────────────────────────────────────────────────────────────────────────────────────


class Call:
    """A spawned episode call: `get(timeout=0)` answers each poll from `outcomes` (None = still running)."""

    def __init__(self, object_id: str, outcomes: list[Any]) -> None:
        self.object_id = object_id
        self.outcomes = outcomes

    def get(self, timeout: float | None = None) -> Any:
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if outcome is None:
            raise TimeoutError()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class Runner:
    """`run_episode`'s `spawn`: every job's call answers from `script(job, attempt)`."""

    def __init__(self, script: Callable[[tuple[Any, ...], int], list[Any]]) -> None:
        self.script = script
        self.spawned: list[tuple[Any, ...]] = []
        self.calls: dict[str, Call] = {}

    def spawn(self, *job: Any) -> Call:
        self.spawned.append(job)
        call = Call(
            f"fc-{len(self.spawned)}", self.script(job, self.spawned.count(job))
        )
        self.calls[call.object_id] = call
        return call


def ok(job: tuple[Any, ...], rc: int = 0) -> dict[str, Any]:
    return {
        "scenario": job[1],
        "formation": job[2],
        "epoch": job[3],
        "model": job[4],
        "mitigation": job[8] if len(job) > 8 else NONE,
        "rc": rc,
    }


@pytest.fixture
def lane_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[float]:
    """The lane's Volume in `tmp_path`, no Modal call, and a sleep that only records; returns the sleeps."""
    slept: list[float] = []
    monkeypatch.setattr(modal_app, "VOLUME_MOUNT", tmp_path)
    monkeypatch.setattr(modal_app, "_bootstrap_remote", lambda: None)
    monkeypatch.setattr(modal_app, "_commit_with_retry", lambda: None)
    monkeypatch.setattr(modal_app.time, "sleep", slept.append)
    return slept


CLINIC_JOB: tuple[Any, ...] = (
    "clinic",
    "warfarin_inr_split",
    "team",
    2,
    "claude-sonnet-5",
    "anthropic",
    "run",
    [],
)


@pytest.mark.parametrize("claim_conflict", [False, True])
def test_dispatch_retries_the_matrix_and_waits_only_after_claim_conflicts(
    monkeypatch: pytest.MonkeyPatch, lane_env: list[float], claim_conflict: bool
) -> None:
    """A claim still held by a container in its shutdown window fails every immediate retry: wait first."""
    conflict = RuntimeError(f"{modal_app.CLAIM_CONFLICT} in Modal Dict ...")

    def script(job: tuple[Any, ...], attempt: int) -> list[Any]:
        if attempt > 1:
            return [ok(job)]
        return [conflict if claim_conflict else ok(job, rc=1)]

    runner = Runner(script)
    monkeypatch.setattr(modal_app, "run_episode", runner)
    monkeypatch.setattr(modal_app, "CLAIM_WAIT_S", 900)
    result = modal_app.dispatch.get_raw_f()(
        [CLINIC_JOB], False, "clinic", "run", "test"
    )
    assert runner.spawned == [CLINIC_JOB, CLINIC_JOB]
    assert result == {"jobs": 1, "failures": 0, "unbanked": 0, "continuations": 0}
    assert lane_env == ([900] if claim_conflict else [])


def test_drain_rewrites_the_progress_file_after_every_result_best_effort(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lane_env: list[float],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A launch of a few episodes shows each banked episode; a failed progress commit never stops the loop."""
    jobs = [(*CLINIC_JOB[:3], e, *CLINIC_JOB[4:]) for e in (1, 2, 3)]

    def script(job: tuple[Any, ...], attempt: int) -> list[Any]:
        if job[3] == 2:
            return [RuntimeError(f"{modal_app.CLAIM_CONFLICT} in Modal Dict 'claims'")]
        return [None, ok(job)] if job[3] == 1 else [ok(job)]

    monkeypatch.setattr(modal_app, "run_episode", Runner(script))
    monkeypatch.setattr(modal_app, "DISPATCH_PASSES", 1)
    progress = tmp_path / "clinic" / "run" / "_launch_x.json"
    seen: list[dict[str, Any]] = []
    monkeypatch.setattr(
        modal_app,
        "_commit_with_retry",
        lambda: seen.append(json.loads(progress.read_text())),
    )
    result = modal_app.dispatch.get_raw_f()(jobs, False, "clinic", "run", "x")
    assert result["failures"] == result["unbanked"] == 1
    assert [(p["done"], p["failures"], p["jobs"], p["finished"]) for p in seen] == [
        (0, 0, 3, False),
        (1, 1, 3, False),  # the claim conflict returns first
        (2, 1, 3, False),
        (3, 1, 3, False),
        (3, 1, 3, True),
    ]
    assert lane_env == []  # every look found an episode finished: no wait

    def fail() -> None:
        raise RuntimeError("DataLossError('failed to publish commit to server')")

    monkeypatch.setattr(modal_app, "_commit_with_retry", fail)
    progress.unlink()
    assert (
        modal_app.dispatch.get_raw_f()(jobs, False, "clinic", "run", "x")["unbanked"]
        == 1
    )
    assert json.loads(progress.read_text())["finished"] is True
    assert "progress file not updated" in capsys.readouterr().out


def test_a_clinic_lane_plays_its_team_mornings_once_into_its_one_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lane_env: list[float]
) -> None:
    """A clinic lane's team mornings are episodes like any other: played once, banked in the lane's root."""
    extra = ["--harness", "sim"]
    base = ("clinic", "warfarin_inr_plain")
    tail = ("claude-opus-5", "anthropic", "results", extra)
    jobs: list[tuple[Any, ...]] = [
        (*base, "coordinator", 1, *tail),
        (*base, "team", 1, *tail),
        (*base, "team", 2, *tail),
        (*base, "team", 1, *tail, "s3"),
    ]
    runner = Runner(lambda job, attempt: [ok(job)])
    monkeypatch.setattr(modal_app, "run_episode", runner)
    result = modal_app.dispatch.get_raw_f()(jobs, False, "clinic", "results", "lane")
    assert runner.spawned == jobs
    root = tmp_path / "clinic"
    assert [p.name for p in root.iterdir()] == ["results"]
    record = json.loads((root / "results" / "_launch_lane.json").read_text())
    assert (record["stage"], record["done"], record["finished"]) == (
        "episodes",
        4,
        True,
    )
    assert result == {"jobs": 4, "failures": 0, "unbanked": 0, "continuations": 0}


def test_a_lane_hands_itself_to_a_continuation_before_modals_limit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lane_env: list[float]
) -> None:
    """Past its hand-off time a lane submits nothing more; a continuation collects its calls in flight and goes on."""
    clock = [0.0]
    monkeypatch.setattr(modal_app.time, "monotonic", lambda: clock[0])

    def sleep(seconds: float) -> None:
        lane_env.append(seconds)
        clock[0] += 3600

    monkeypatch.setattr(modal_app.time, "sleep", sleep)
    monkeypatch.setattr(modal_app, "DISPATCH_WINDOW", 1)
    jobs = [(*CLINIC_JOB[:3], e, *CLINIC_JOB[4:]) for e in (1, 2, 3)]
    runner = Runner(lambda job, attempt: [None, ok(job)] if job[3] == 1 else [ok(job)])
    monkeypatch.setattr(modal_app, "run_episode", runner)
    followers: list[tuple[Any, ...]] = []

    def spawn(*args: Any) -> SimpleNamespace:
        followers.append(args)
        return SimpleNamespace(object_id="fc-next")

    monkeypatch.setattr(modal_app, "dispatch", SimpleNamespace(spawn=spawn))
    first = modal_app.run_lane(
        jobs, False, "clinic", "run", "lane", modal_app.new_lane(jobs), 1800.0
    )
    assert first["continued"] == "fc-next" and runner.spawned == jobs[:1]
    ((_jobs, _heavy, _eval, _runs, _lane, state),) = followers
    assert state["pending"] == [["fc-1", jobs[0]]] and state["todo"] == jobs[1:]
    assert state["continuation"] == 1
    record = json.loads((tmp_path / "clinic" / "run" / "_launch_lane.json").read_text())
    assert (record["continued"], record["finished"]) == ("fc-next", False)
    # the continuation: the call in flight by id (it finished meanwhile), then the rest
    monkeypatch.setattr(
        modal_app.modal.FunctionCall, "from_id", runner.calls.__getitem__
    )
    result = modal_app.run_lane(
        jobs, False, "clinic", "run", "lane", state, clock[0] + 1800
    )
    assert runner.spawned == jobs
    assert result == {"jobs": 3, "failures": 0, "unbanked": 0, "continuations": 1}
    record = json.loads((tmp_path / "clinic" / "run" / "_launch_lane.json").read_text())
    assert (record["continuation"], record["finished"]) == (1, True)


def test_a_waiting_launch_follows_each_lanes_continuations(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    for name in KEYS:
        monkeypatch.setenv(name, "sk-test")

    def spawn(*_args: object) -> SimpleNamespace:
        return SimpleNamespace(get=lambda: {"continued": "fc-2"})

    def from_id(call_id: str) -> SimpleNamespace:
        assert call_id == "fc-2"
        return SimpleNamespace(get=lambda: {"unbanked": 0, "continuations": 1})

    monkeypatch.setattr(modal_app, "dispatch", SimpleNamespace(spawn=spawn))
    monkeypatch.setattr(modal_app.modal.FunctionCall, "from_id", from_id)
    modal_main(
        eval="merge_queue", model="claude-opus-5", scenario="oversub", episodes=1
    )
    assert '"continuations": 1' in capsys.readouterr().out


@pytest.mark.parametrize("volume_env", [None, "research"])
def test_the_detached_follow_up_names_the_volume_environment(
    monkeypatch: pytest.MonkeyPatch, volume_env: str | None
) -> None:
    monkeypatch.setattr(modal_app, "VOLUME_ENV", volume_env)
    lanes = ["20260925T043012Z__claude-opus-5", "20260925T043012Z__qwen__qwen3.8-max"]
    hint = modal_app.follow_up("clinic", "results", lanes)
    cli = ".venv/bin/python -m modal"
    gets = [
        line.split("#")[0].strip()
        for line in hint.splitlines()
        if "modal volume get" in line
    ]
    flag = f" --env {volume_env}" if volume_env else ""
    assert gets == [
        f"{cli} volume get{flag} {modal_app.VOLUME_NAME} clinic/results/_launch_{lane}.json -"
        for lane in lanes
    ]
    assert (
        f"{cli} run eval/modal_app.py::volume_status --eval clinic --runs-name results"
        in hint
    )
    pulls = [line.strip() for line in hint.splitlines() if "::pull" in line]
    assert pulls == [
        f"{cli} run eval/modal_app.py::pull --eval clinic --runs-name results"
    ]


def test_the_detached_follow_up_stops_and_streams_the_app_by_its_id() -> None:
    hint = modal_app.follow_up("api_key", "results", ["x"], app_id="ap-AbC123")
    assert ".venv/bin/python -m modal app logs ap-AbC123 -f" in hint
    assert ".venv/bin/python -m modal app stop ap-AbC123 -y" in hint
    # every printed command is ready to paste from the repository root: none calls a bare `modal`
    commands = [line.strip() for line in hint.splitlines() if line.startswith("  ")]
    assert commands and all(
        c.startswith(".venv/bin/python -m modal ") for c in commands
    )
    unknown = modal_app.follow_up("api_key", "results", ["x"])
    assert (
        "app stop <app id: the ap-... at the end of Modal's `View run at` URL> -y"
        in unknown
    )


def test_episodes_and_dispatch_run_on_nonpreemptible_containers() -> None:
    for function in (
        modal_app.run_episode,
        modal_app.run_episode_mq,
        modal_app.dispatch,
    ):
        assert function.spec.scheduler_placement is not None
        assert function.spec.scheduler_placement.nonpreemptible
    probe = (
        "import modal_app as m; "
        "print(m.NONPREEMPTIBLE, m.run_episode.spec.scheduler_placement is None)"
    )
    out = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=Path(modal_app.__file__).parent,
        env={**os.environ, "EVAL_MODAL_NONPREEMPTIBLE": "0"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.split() == ["False", "True"]


# ── the remote episode ───────────────────────────────────────────────────────────────────────────


def test_the_remote_episode_forwards_its_options_and_arm(container: Container) -> None:
    extra = ["--harness", "sim", "--fake-model"]
    result = run_one(
        "clinic",
        "warfarin_inr_split",
        "team",
        4,
        "claude-sonnet-5",
        "anthropic",
        "t",
        extra,
    )
    assert result["rc"] == 0 and result["mitigation"] == NONE
    assert container.argv[0][:2] == ["--board", "warfarin_inr_split"]
    assert container.argv[0][-4:] == [*extra, "--pack-workspaces"]
    # merge_queue packs its own workspaces; an arm rides as `--mitigation` (the control arm adds nothing)
    mq: tuple[Any, ...] = (
        "merge_queue",
        "oversub",
        "team",
        4,
        "claude-sonnet-5",
        "anthropic",
        "r",
        [],
    )
    assert modal_app.run_episode_mq.get_raw_f()(*mq, FAKE)["mitigation"] == FAKE
    modal_app.run_episode_mq.get_raw_f()(*mq)
    assert container.argv[1][-2:] == ["--mitigation", FAKE]
    assert (
        "--mitigation" not in container.argv[2]
        and "--pack-workspaces" not in container.argv[2]
    )
    runs_root = modal_app.VOLUME_MOUNT / "merge_queue" / "r"
    assert container.packed == [
        (runs_root, "oversub", "team", 4, "claude-sonnet-5", FAKE),
        (runs_root, "oversub", "team", 4, "claude-sonnet-5", NONE),
    ]
    assert not container.claims  # every claim released


def test_merge_queue_packing_finds_an_arms_run_dir(tmp_path: Path) -> None:
    from merge_queue.run import run_dir_name

    run_dir = tmp_path / run_dir_name("oversub", "team", "claude-sonnet-5", 2, FAKE)
    (run_dir / "agents" / "owner").mkdir(parents=True)
    (run_dir / "agents" / "owner" / "file").write_text("x")
    modal_app._pack_merge_queue_workspaces(  # pyright: ignore[reportPrivateUsage]
        tmp_path, "oversub", "team", 2, "claude-sonnet-5", FAKE
    )
    assert (run_dir / "workspaces.tar.gz").exists() and not (
        run_dir / "agents"
    ).exists()


def test_status_reads_the_arm_off_every_run_dir_grammar() -> None:
    for name, arm in (
        ("oversub__none__comms__sonnet5__e3", NONE),
        (f"oversub__none__comms__mit-{FAKE}__sonnet5__e3", FAKE),
        (f"kestrel__claude-opus-5__mit-{FAKE}", FAKE),
        (
            f"token_cluster__stakes_100__mesh__notax__mit-{FAKE}__claude-opus-5__e1__sim",
            FAKE,
        ),
    ):
        assert modal_app.mitigation_of_name(name) == arm


# ── the episode claim: one writer per episode through final persistence ─────────────────────────


@pytest.mark.parametrize(
    "other",
    [
        {"runs_name": "./test"},
        {"provider": "openrouter", "extra": ["--harness", "sim"]},
    ],
)
def test_a_duplicate_never_touches_the_volume_or_the_cli_even_during_the_commit(
    monkeypatch: pytest.MonkeyPatch, container: Container, other: dict[str, Any]
) -> None:
    events = container.events

    def duplicate() -> None:
        before = list(events)
        with (
            monkeypatch.context() as patch
        ):  # another launch's input of the same episode
            patch.setattr(modal_app.modal, "current_input_id", lambda: "in-other")
            with pytest.raises(RuntimeError, match="fc-owner.*in-owner"):
                mq_episode(**other)
        assert events == before

    def main(argv: list[str]) -> int:
        events.append("main")
        duplicate()
        return 0

    def commit() -> None:
        assert len(container.claims) == 1
        duplicate()
        events.append("commit")

    container.main = main
    monkeypatch.setattr(modal_app, "_commit_with_retry", commit)
    assert mq_episode()["rc"] == 0
    assert events == ["claim", "reload", "main", "pack", "commit", "release"]
    assert not container.claims


@pytest.mark.parametrize(
    "error", [RuntimeError("evaluation failed"), KeyboardInterrupt()]
)
def test_an_exception_releases_only_after_teardown_packing_and_commit(
    container: Container, error: BaseException
) -> None:
    def main(argv: list[str]) -> int:
        try:
            container.events.append("main")
            raise error
        finally:
            assert container.claims
            container.events.append("teardown")

    container.main = main
    with pytest.raises(type(error)):
        mq_episode()
    assert container.events == [
        "claim",
        "reload",
        "main",
        "teardown",
        "pack",
        "commit",
        "release",
    ]
    assert not container.claims


@pytest.mark.parametrize("failed_step", ["pack", "commit"])
def test_a_failed_artifact_cleanup_retains_the_owner_and_blocks_a_replay(
    monkeypatch: pytest.MonkeyPatch, container: Container, failed_step: str
) -> None:
    def fail(*args: Any) -> None:
        raise RuntimeError(failed_step)

    step = (
        "_pack_merge_queue_workspaces"
        if failed_step == "pack"
        else "_commit_with_retry"
    )
    monkeypatch.setattr(modal_app, step, fail)
    with pytest.raises(RuntimeError, match=failed_step):
        mq_episode()
    owner = next(iter(container.claims.values()))
    assert (owner["function_call_id"], owner["input_id"]) == ("fc-owner", "in-owner")
    assert owner[
        "retained"
    ]  # marked, so a restart of the same input does not wait for it
    assert "release" not in container.events and container.events[-1] == "retain"
    before = list(container.events)
    slept: list[float] = []
    monkeypatch.setattr(modal_app.time, "sleep", slept.append)
    monkeypatch.setattr(modal_app, "VOLUME_ENV", "env-b")
    with pytest.raises(RuntimeError, match="already claimed") as refused:
        mq_episode()  # Modal's retry of the same input: refused at once
    assert container.events == before and slept == []
    # the remedy it names is a command the Modal CLI has (it has no `dict pop`)
    assert (
        f".venv/bin/python -m modal dict clear --env env-b {modal_app.CLAIMS_NAME} -y"
        in str(refused.value)
    )


def test_a_failure_before_evaluation_releases_the_unused_claim(
    monkeypatch: pytest.MonkeyPatch, container: Container
) -> None:
    def fail(name: str) -> None:
        raise ImportError("unavailable runner")

    monkeypatch.setattr(modal_app, "_eval_main", fail)
    with pytest.raises(ImportError):
        mq_episode()
    assert container.events == ["claim", "release"] and not container.claims


def _held_by_an_earlier_attempt(container: Container) -> str:
    key = modal_app.claim_key_for(
        "merge_queue",
        "test",
        "claude-sonnet-5",
        "oversub",
        "team",
        1,
        volume_id="vo-test",
    )
    container.claims[key] = {
        "token": "old",
        "function_call_id": "fc-owner",
        "input_id": "in-owner",
    }
    return key


def test_a_restarted_input_waits_for_its_interrupted_attempt_to_release(
    monkeypatch: pytest.MonkeyPatch, container: Container
) -> None:
    """A preemption: Modal restarts the input while the old container still packs, commits and releases."""
    key = _held_by_an_earlier_attempt(container)
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) == 3:  # the preempted container's teardown finishes
            container.pop(key)

    monkeypatch.setattr(modal_app.time, "sleep", sleep)
    monkeypatch.setattr(modal_app, "CLAIM_WAIT_S", 3600)
    assert mq_episode()["rc"] == 0
    assert slept == [modal_app.CLAIM_POLL_S] * 3
    assert container.events == [
        "release",
        "claim",
        "reload",
        "pack",
        "commit",
        "release",
    ]
    assert not container.claims


def test_a_restart_gives_up_after_the_claim_wait(
    monkeypatch: pytest.MonkeyPatch, container: Container
) -> None:
    key = _held_by_an_earlier_attempt(container)
    clock = [0.0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    monkeypatch.setattr(modal_app.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(modal_app.time, "sleep", sleep)
    monkeypatch.setattr(modal_app, "CLAIM_WAIT_S", 60)
    with pytest.raises(RuntimeError, match="already claimed.*after waiting 60 s"):
        mq_episode()
    assert (
        container.events == [] and clock[0] >= 60
    )  # nothing touched; the old claim stays
    assert container.claims[key]["token"] == "old"
