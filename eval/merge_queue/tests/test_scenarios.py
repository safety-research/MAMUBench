"""The scenario registry, its seeds and cells, the scenarios' certification, and the launcher's plan."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from _providers import provider_for

from merge_queue import scenarios
from merge_queue.run import (
    Job,
    drive_argv,
    git_commit,
    model_slug,
    parse_args,
    plan,
    resolve_thinking,
    run_dir_name,
    target_key_env,
)
from merge_queue.scenarios._cells import Cell
from merge_queue.scenarios.baseline_tight.config import check as check_baseline
from merge_queue.scenarios.oversub.config import check as check_oversub
from merge_queue.scenarios.volunteer.config import (
    _profile_index,  # pyright: ignore[reportPrivateUsage]
)
from merge_queue.scenarios.volunteer.config import check as check_volunteer


def test_the_registry_is_the_papers_three_plus_the_control() -> None:
    assert list(scenarios.SCENARIOS) == [
        "oversub",
        "volunteer_p1",
        "volunteer_p3",
        "baseline_tight",
    ]
    assert scenarios.PAPER_SCENARIOS == ("oversub", "volunteer_p1", "volunteer_p3")
    assert [r.id for r in scenarios.select([], all_=True)] == list(
        scenarios.PAPER_SCENARIOS
    )
    assert [r.id for r in scenarios.select(["baseline_tight"], all_=True)] == list(
        scenarios.SCENARIOS
    )
    # the builder is not a scenario id: pick a profile
    for names in ([], ["nope"], ["volunteer"]):
        with pytest.raises(SystemExit):
            scenarios.select(names)


def test_volunteer_seeds_are_strided_world_epochs() -> None:
    """The paper's seeds: volunteer_p1 = world epochs 1, 4, ..., 58; volunteer_p3 = 3, 6, ..., 60."""
    p1, p3 = scenarios.SCENARIOS["volunteer_p1"], scenarios.SCENARIOS["volunteer_p3"]
    assert [p1.world_epoch(k) for k in range(1, 21)] == list(range(1, 59, 3))
    assert [p3.world_epoch(k) for k in range(1, 21)] == list(range(3, 61, 3))
    assert scenarios.SCENARIOS["oversub"].world_epoch(7) == 7
    for row in (p1, p3):
        for k in range(1, 21):
            world = row.world_epoch(k)
            # the builder's own profile selector agrees (research certify_volunteer_split)
            assert _profile_index(world) == scenarios.profile_of(world) == row.profile
            assert row.seed_of(world) == k
    with pytest.raises(ValueError, match="merge profile 2"):
        p1.seed_of(2)
    assert scenarios.analysis_scenario("volunteer", 5) == "volunteer_p2"
    assert scenarios.analysis_scenario("oversub", 5) == "oversub"


@pytest.mark.parametrize(
    ("scenario", "check", "seeds"),
    [
        ("oversub", check_oversub, 5),
        ("baseline_tight", check_baseline, 5),
        ("volunteer_p1", check_volunteer, 20),
        ("volunteer_p3", check_volunteer, 20),
    ],
)
def test_the_scenarios_certify_on_the_papers_seeds(
    scenario: str, check: Callable[[int], list[str]], seeds: int
) -> None:
    """The queue engine and the oracle hold each design: all-fit, drop the cheapest, the volunteer's slack."""
    row = scenarios.SCENARIOS[scenario]
    for k in range(1, seeds + 1):
        assert check(row.world_epoch(k)) == []


@pytest.mark.parametrize(
    ("scenario", "formation", "cell"),
    [
        ("oversub", "coordinator", "oversub__steward"),
        ("oversub", "team", "oversub__none__comms"),
        ("oversub", "team_silent", "oversub__none__nocomms"),
        ("volunteer_p3", "solo", "volunteer__solo"),
        (None, "team", "oversub__none__comms__live_captain"),
        (
            None,
            "none__comms__scripted_captain",
            "oversub__none__comms__scripted_captain",
        ),
    ],
)
def test_cell_names_are_the_research_grammar(
    scenario: str | None, formation: str, cell: str
) -> None:
    """A lead arm's `__live_captain` cell is the team; another research leg keeps its own label."""
    if scenario is not None:
        assert scenarios.cell_name(scenario, formation) == cell
    assert scenarios.formation_of_cell(cell) == formation


@pytest.mark.parametrize(
    "kwargs",
    [
        {"scenario": "reserve_gated", "arm": "none", "comms": True},
        {"scenario": "oversub", "arm": "desperation", "comms": True},
        {"scenario": "oversub", "arm": "none", "comms": True, "steward": True},
        {
            "scenario": "oversub",
            "arm": "none",
            "comms": False,
            "steward": True,
            "solo": True,
        },
        {
            "scenario": "oversub",
            "arm": "none",
            "comms": False,
            "topology": "live_captain",
        },
        {
            "scenario": "oversub",
            "arm": "none",
            "comms": False,
            "solo": True,
            "topology": "live_captain",
        },
        {
            "scenario": "oversub",
            "arm": "none",
            "comms": True,
            "topology": "scripted_captain",
        },
    ],
)
def test_cells_the_paper_did_not_run_are_refused(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Cell(**kwargs)  # type: ignore[arg-type]


def test_run_dirs_carry_the_model_slug_and_the_world_epoch() -> None:
    """Episodes count a scenario's seeds; the run dir names the world epoch (the research grammar)."""
    assert run_dir_name("volunteer_p1", "team", "claude-opus-5", 20) == (
        "volunteer__none__comms__opus5__e58"
    )
    assert run_dir_name("volunteer_p3", "coordinator", "claude-sonnet-5", 1) == (
        "volunteer__steward__sonnet5__e3"
    )
    assert run_dir_name("oversub", "team", "claude-opus-5", 4, "charter") == (
        "oversub__none__comms__mit-charter__opus5__e4"
    )
    assert Job("volunteer_p3", "team", 2, "charter").label == (
        "volunteer_p3 team e2 (world e6) [charter]"
    )
    # a model without a paper slug keeps `[a-z0-9]` of its id
    assert [model_slug(m) for m in ("anthropic/claude-sonnet-4.5", "gpt-5-mini")] == [
        "anthropicclaudesonnet45",
        "gpt5mini",
    ]


def test_the_launcher_plans_the_papers_matrix_with_thinking_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    """`--all` is the paper's three scenarios x four formations; Claude seats default to thinking off."""
    args = parse_args(["--all", "--episodes", "2"])
    assert set(args.formation) == {"coordinator", "team", "team_silent", "solo"}
    jobs = plan(args)
    assert len(jobs) == 3 * 4 * 2
    assert {job.scenario for job in jobs} == set(scenarios.PAPER_SCENARIOS)
    jobs_file = tmp_path / "jobs.csv"
    jobs_file.write_text("scenario,formation,epoch\nvolunteer_p1,solo,5\n")
    (job,) = plan(parse_args(["--jobs-file", str(jobs_file)]))
    assert (job.scenario, job.formation, job.epoch, job.world_epoch) == (
        "volunteer_p1",
        "solo",
        5,
        13,
    )
    jobs_file.write_text("scenario,formation,epoch\noversub,crowd,1\n")
    with pytest.raises(SystemExit, match="unknown merge_queue formation 'crowd'"):
        plan(parse_args(["--jobs-file", str(jobs_file)]))
    # `--thinking` stays None until the provider resolves it: off for Claude, medium for GPT
    assert parse_args(["--all"]).thinking is None
    assert [
        resolve_thinking(provider_for(m), None)
        for m in ("claude-sonnet-5", "claude-opus-5", "gpt-5.5")
    ] == ["off", "off", "medium"]
    # the driver records the resolved level and the commit (`EVAL_GIT_SHA` in a container without a checkout)
    monkeypatch.setenv("EVAL_GIT_SHA", "test-sha")
    git_commit.cache_clear()
    request.addfinalizer(git_commit.cache_clear)
    for extra, level in (([], "off"), (["--thinking", "medium"], "medium")):
        argv = drive_argv(
            parse_args(["--all", "--model", "claude-opus-5", *extra]),
            Job("oversub", "coordinator", 1),
            provider="anthropic",
            key_env="ANTHROPIC_API_KEY",
            pi_cmd="/opt/pi",
        )
        assert argv[argv.index("--thinking") + 1] == level
        assert argv[argv.index("--commit") + 1] == "test-sha"


def test_the_commit_is_unknown_without_git(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> None:
    def no_git(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError(2, "No such file or directory", "git")

    monkeypatch.delenv("EVAL_GIT_SHA", raising=False)
    monkeypatch.setattr(subprocess, "run", no_git)
    git_commit.cache_clear()
    request.addfinalizer(git_commit.cache_clear)
    assert git_commit() == "unknown"


def test_the_target_key_travels_under_whichever_alias_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OpenRouter's key may sit in `OPEN_ROUTER_KEY`, as the root launcher's key check accepts.

    The driver is handed that variable's name; `--key-env` always wins, and with no variable set the first
    name stands.
    """
    for name in ("OPENROUTER_API_KEY", "OPEN_ROUTER_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert target_key_env("openrouter", None) == "OPENROUTER_API_KEY"
    monkeypatch.setenv("OPEN_ROUTER_KEY", "sk-or-test")
    assert target_key_env("openrouter", None) == "OPEN_ROUTER_KEY"
    assert target_key_env("openrouter", "MY_KEY") == "MY_KEY"
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-2")
    assert target_key_env("openrouter", None) == "OPENROUTER_API_KEY"
    assert target_key_env("anthropic", None) == "ANTHROPIC_API_KEY"
