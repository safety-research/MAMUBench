"""`eval/_matrix.py`: the paper's runs each command plays by default, how options narrow them, the key preflight.

The per-cell counts are the appendix's Run Details tables (formation experiments and mitigations).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import _matrix
import pytest
from _matrix import CLAUDE, MODELS, Episode

HARNESS = {
    "api_key": "sim",
    "clinic": "sim",
    "personal_assistant": "pi",
    "merge_queue": "pi",
}


def plan(env: str, **options: object) -> list[Episode]:
    return _matrix.plan(env, harness=HARNESS[env], **options)  # pyright: ignore[reportArgumentType]


def cells(episodes: list[Episode]) -> Counter[tuple[str, str, str]]:
    """Episodes per (model, formation, arm), summed over the scenarios."""
    return Counter((e.model, e.formation, e.mitigation) for e in episodes)


def test_each_command_plays_the_papers_formation_matrix() -> None:
    api_key = plan("api_key")
    assert len(api_key) == 5 * 4 * 25 * 20
    assert set(cells(api_key).values()) == {25 * 20}
    clinic = plan("clinic")
    counts = cells(clinic)
    for model in MODELS:
        assert counts[(model, "team", "none")] == 24 * 20
        assert counts[(model, "team_silent", "none")] == 24 * 5
    # the Qwen3.8-max coordinator holds its low-reasoning episodes of record only (167 assembled + 149 scattered)
    assert counts[("qwen/qwen3.8-max", "coordinator", "none")] == 316
    assert counts[("claude-opus-5", "coordinator", "none")] == 24 * 20
    assert len(clinic) == 4 * 24 * 20 + 316 + 5 * 24 * 20 + 5 * 24 * 5
    pa = cells(plan("personal_assistant"))
    assert pa == {
        (m, f, "none"): 25 * (100 if m in CLAUDE else 50)
        for m in MODELS[:4]
        for f in ("coordinator", "team", "team_silent")
    }
    mq = plan("merge_queue")
    assert {e.scenario for e in mq} == {"oversub", "volunteer_p1", "volunteer_p3"}
    assert cells(mq) == {
        (m, f, "none"): 3 * 20
        for m in CLAUDE
        for f in ("solo", "coordinator", "team_silent", "team")
    }
    # one plan per launch: every model's episodes in one list, model by model
    assert [e.model for e in api_key] == sorted(
        (e.model for e in api_key), key=MODELS.index
    )


def test_a_mitigation_plays_that_arms_paper_runs() -> None:
    for arm in ("lead_value", "lead_full_stack"):
        assert cells(plan("api_key", mitigation=arm)) == {
            (m, "team", arm): 25 * 20 for m in CLAUDE
        }
    for arm in ("s1", "s2", "s3"):
        episodes = plan("clinic", mitigation=arm)
        assert cells(episodes) == {(m, "team", arm): 24 * 10 for m in CLAUDE}
        assert {e.epoch for e in episodes} == set(range(1, 11))
    assert cells(plan("merge_queue", mitigation="charter")) == {
        (m, "team", "charter"): 60 for m in CLAUDE
    }
    for arm in ("lead_cut_line", "priorities", "charter_stakes"):
        assert cells(plan("merge_queue", mitigation=arm)) == {
            (m, "team", arm): 15 for m in CLAUDE
        }
    # the personal assistant re-runs the paper's draw of failed team episodes under the arm and the control
    guard = cells(plan("personal_assistant", mitigation="guard"))
    assert guard == {
        ("claude-opus-5", "team", "none"): 142,
        ("claude-opus-5", "team", "guard"): 142,
        ("claude-sonnet-5", "team", "none"): 186,
        ("claude-sonnet-5", "team", "guard"): 186,
    }
    with pytest.raises(ValueError, match="listed for claude-opus-5, claude-sonnet-5"):
        plan("personal_assistant", mitigation="guard", models=["gpt-5.6-sol"])
    # `all`: every arm's runs in one launch, the personal assistant's shared control re-runs once
    for env in HARNESS:
        every = plan(env, mitigation=_matrix.ALL)
        assert len(every) == len(set(every))
        assert set(every) == {
            e for arm in _matrix.arm_runs(env) for e in plan(env, mitigation=arm)
        }
        assert [e.model for e in every] == sorted(
            (e.model for e in every), key=MODELS.index
        )
    assert cells(plan("personal_assistant", mitigation=_matrix.ALL)) == {
        (m, "team", arm): n
        for m, n in (("claude-opus-5", 142), ("claude-sonnet-5", 186))
        for arm in ("none", "guard", "full_stack")
    }
    assert len(plan("merge_queue", mitigation=_matrix.ALL)) == 2 * (60 + 3 * 15)
    # the supplementary context-files rerun
    assert cells(plan("personal_assistant", context_files=True)) == {
        (m, f, "none"): 25 * 100 for m in CLAUDE for f in ("team", "team_silent")
    }


def test_options_narrow_the_plan() -> None:
    narrowed = plan(
        "api_key",
        models=["claude-opus-5"],
        formations=["team"],
        scenarios=["stakes_100"],
        epochs=3,
    )
    assert narrowed == [
        Episode("claude-opus-5", "stakes_100", "team", e) for e in (1, 2, 3)
    ]
    # --episodes plays episodes 1..N, or the first N of a cell the paper holds as a list
    assert (
        len(plan("merge_queue", scenarios=["oversub"], formations=["team"], epochs=25))
        == 2 * 25
    )
    qwen = plan(
        "clinic", models=["qwen/qwen3.8-max"], formations=["coordinator"], epochs=2
    )
    assert len(qwen) == 48 and len({e.epoch for e in qwen}) > 2
    # a personal-assistant alias resolves to the id the runs record
    assert {e.model for e in plan("personal_assistant", models=["opus"], epochs=1)} == {
        "claude-opus-5"
    }
    # the pi harness has no API key solo: the default leaves it out, a request for it is refused
    assert "solo" not in {e.formation for e in _matrix.plan("api_key", harness="pi")}
    with pytest.raises(ValueError, match="runs no solo formation"):
        _matrix.plan("api_key", harness="pi", formations=["solo"])
    # the episodes of record are the simulated harness's: the pi harness plays episodes 1..N
    qwen_pi = _matrix.plan(
        "clinic", harness="pi", models=["qwen/qwen3.8-max"], formations=["coordinator"]
    )
    assert len(qwen_pi) == 24 * 20
    with pytest.raises(ValueError, match="applies to formation"):
        plan("clinic", mitigation="s3", formations=["coordinator"])
    with pytest.raises(ValueError, match="unknown clinic mitigation"):
        plan("clinic", mitigation="nope")
    with pytest.raises(ValueError, match="applies to formation"):
        plan("clinic", mitigation=_matrix.ALL, formations=["coordinator"])


def test_a_jobs_file_lists_one_models_episodes(tmp_path: Path) -> None:
    path = tmp_path / "jobs.csv"
    path.write_text(
        "scenario,formation,epoch,mitigation\nstakes_100,team,4,lead_value\nstakes_80,solo,2,\n"
    )
    assert plan("api_key", jobs_file=path) == [
        Episode("claude-sonnet-5", "stakes_100", "team", 4, "lead_value"),
        Episode("claude-sonnet-5", "stakes_80", "solo", 2),
    ]
    assert {
        e.model for e in plan("api_key", jobs_file=path, models=["claude-opus-5"])
    } == {"claude-opus-5"}
    path.write_text("scenario,formation,epoch\nwarfarin_inr_split,solo,1\n")
    with pytest.raises(ValueError, match="runs no solo formation"):
        plan("clinic", jobs_file=path)


def test_default_runs_names() -> None:
    name = _matrix.default_runs_name
    assert name("api_key", harness="sim") == "results"
    assert name("api_key", harness="sim", mitigation="lead_value") == "results"
    assert name("clinic", harness="pi") == "pi"
    assert name("merge_queue", harness="pi") == "results"
    assert name("personal_assistant", harness="pi", mitigation="guard") == "mitigations"
    assert name("personal_assistant", harness="pi", mitigation=_matrix.ALL) == (
        "mitigations"
    )
    assert name("clinic", harness="sim", mitigation=_matrix.ALL) == "results"
    assert (
        name("personal_assistant", harness="pi", context_files=True) == "context_files"
    )
    assert name("api_key", harness="sim", fake=True) == "results_fake"
    assert name("clinic", harness="sim", jobs_file=Path("x/team.csv")) == "team"


def test_the_personal_assistants_paper_runs_chain_the_context_files_rerun() -> None:
    """Its AGENTS.md-in-context rerun follows into `context_files`, narrowed to the models and formations it ran."""
    roots = _matrix.launch_roots("personal_assistant", harness="pi")
    assert [(r.name, len(r.episodes), r.options) for r in roots] == [
        ("results", 22500, ()),
        ("context_files", 10000, ("--context-files", "on")),
    ]
    assert roots[1].episodes == plan("personal_assistant", context_files=True)
    narrowed = _matrix.launch_roots(
        "personal_assistant",
        harness="pi",
        models=["opus", "gpt-5.6-sol"],
        formations=["coordinator", "team"],
        scenarios=["kestrel_quiz_booth"],
        epochs=2,
        extra=["--fake-pi"],
    )
    assert [r.name for r in narrowed] == ["results_fake", "context_files_fake"]
    assert {(e.model, e.formation) for e in narrowed[1].episodes} == {
        ("claude-opus-5", "team")
    }
    assert len(narrowed[1].episodes) == 2
    # a named root's rerun lands beside it; one outside the rerun's models or formations has none
    named = _matrix.launch_roots("personal_assistant", harness="pi", runs_name="mine")
    assert [r.name for r in named] == ["mine", "mine_context_files"]
    assert (
        len(
            _matrix.launch_roots(
                "personal_assistant", harness="pi", models=["gpt-5.6-sol"]
            )
        )
        == 1
    )
    assert (
        len(
            _matrix.launch_roots(
                "personal_assistant", harness="pi", formations=["coordinator"]
            )
        )
        == 1
    )
    # `--context-files on` plays the rerun alone, `off` the paper runs alone; an arm and a jobs file never chain
    only = _matrix.launch_roots(
        "personal_assistant", harness="pi", extra=["--context-files", "on"]
    )
    assert [(r.name, len(r.episodes)) for r in only] == [("context_files", 10000)]
    off = _matrix.launch_roots(
        "personal_assistant", harness="pi", extra=["--context-files", "off"]
    )
    assert [r.name for r in off] == ["results"]
    assert (
        len(
            _matrix.launch_roots("personal_assistant", harness="pi", mitigation="guard")
        )
        == 1
    )
    assert len(_matrix.launch_roots("api_key")) == 1


def test_the_merge_queue_launch_plays_the_papers_scenarios_only(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not among the paper's"):
        plan("merge_queue", scenarios=["baseline_tight"])
    path = tmp_path / "jobs.csv"
    path.write_text("scenario,formation,epoch\nbaseline_tight,team,1\n")
    assert [e.scenario for e in plan("merge_queue", jobs_file=path)] == [
        "baseline_tight"
    ]


def test_the_preflight_names_every_missing_key() -> None:
    models = ["claude-opus-5", "gpt-5.6-sol", "qwen/qwen3.8-max"]
    refusal = _matrix.missing_keys("api_key", models, "sim", {"OPENAI_API_KEY": "k"})
    assert refusal is not None
    # the API key simulated harness's house roles need the Anthropic key for every target
    assert (
        "ANTHROPIC_API_KEY (for claude-opus-5, gpt-5.6-sol, qwen/qwen3.8-max)"
        in refusal
    )
    assert (
        "OPENROUTER_API_KEY (for qwen/qwen3.8-max)" in refusal
        and "OPENAI" not in refusal
    )
    assert (
        _matrix.missing_keys(
            "clinic", models[1:], "sim", {"OPENAI_API_KEY": "k", "OPEN_ROUTER_KEY": "k"}
        )
        is None
    )
    # the merge queue's voicer runs on the Anthropic key whatever the target
    assert "ANTHROPIC_API_KEY" in str(
        _matrix.missing_keys(
            "merge_queue", ["gpt-5.6-sol"], "pi", {"OPENAI_API_KEY": "k"}
        )
    )
    assert (
        _matrix.missing_keys(
            "merge_queue",
            ["gpt-5.6-sol"],
            "pi",
            {"OPENAI_API_KEY": "k"},
            ["--no-voicer"],
        )
        is None
    )
    # a local --key-env names the target's variable
    assert (
        _matrix.missing_keys(
            "personal_assistant",
            ["claude-opus-5"],
            "pi",
            {"MINE": "k"},
            ["--key-env", "MINE"],
        )
        is None
    )
