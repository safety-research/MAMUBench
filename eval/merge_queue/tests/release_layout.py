"""Lay the paper's research episode dirs out as this repo's runner writes run dirs (a test helper, 0 LLM calls).

The merge queue has no offline stand-in (an episode is real git, CI and pi), so the release's readers are
proven on real episodes of the paper's corpus re-laid in the release layout. For each research run dir
(`runs/<subtree>/<run>`: `controls/` for the formations, the arm's rung for a mitigation arm) this module:

1. maps it to the release job that would have run it: scenario id (the volunteer world epoch's profile),
   formation (`scenarios.formation_of_cell`; a lead arm's `__live_captain` cell is the team), the scenario's
   seed k (`Scenario.seed_of`), the arm (`mitigations.ARM_BY_RUNG`) and the model id;
2. plans that job exactly as a launch would: `run.parse_args` / `run.plan` / `run.drive_argv` build the argv
   `run.py` hands `_drive.py`, and `_drive.parse_args` / `_drive.plan_episode` build the episode from it (the
   run-dir name `<cell>[__mit-<arm>]__<slug>__e<world epoch>`, the config and the `config.json` record). The
   research episode's recorded scenario name must equal the config the release builds for it;
3. writes the run dir as `runtime.driver.drive_episode` and `_drive.main` leave it: `config.json` (the
   record), `episode.json` and `DONE.json` (`run_dir` pointing at the new dir, the writers' JSON
   formatting), `service/events.jsonl` verbatim, and each seat's pi sessions as plain
   `agents/<seat>/sessions/*.jsonl` (gzipped sessions are unpacked);
4. optionally packs the seat trees as the Modal launcher does (`modal_app._pack_merge_queue_workspaces`:
   `agents/` into `workspaces.tar.gz`, then removed), the default backend's layout.

Research run dirs keep no `turns.jsonl`, `voicer.jsonl`, `git_archaeology.json` or `node/` tree, so the
laid-out run dirs lack them too; no reader of the record (`report.py`, the paper's extractor) reads them.

`write_run` banks a synthetic paper-world episode (no ledger, no sessions) for the readers' unit tests.
"""

from __future__ import annotations

import gzip
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from _mitigations import NONE
from _providers import provider_for

from merge_queue import run as mq_run
from merge_queue._drive import API_KEY_VAR, EpisodePlan, plan_episode
from merge_queue._drive import parse_args as drive_parse_args
from merge_queue.mitigations import ARM_BY_RUNG
from merge_queue.report import RESEARCH_MODELS
from merge_queue.scenarios import (
    SCENARIOS,
    analysis_scenario,
    cell_name,
    formation_of_cell,
)

#: The paper-run fixtures (`tests/fixtures/paper_runs`): eight run dirs of the paper's corpus, trimmed.
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "paper_runs"
#: Research runs subtrees that hold control formations (no mitigation arm).
CONTROL_SUBTREES = ("controls", "captainless")


@dataclass(frozen=True)
class ReleaseJob:
    """The release episode a research run dir corresponds to (one `run.py` job).

    Attributes:
        scenario: The release scenario id (`oversub`, `volunteer_p1`, ...).
        formation: The release formation (`coordinator`, `team`, `team_silent`, `solo`).
        epoch: The scenario's seed k (`--epoch0`; the run dir carries its world epoch).
        mitigation: The arm (`none` for a control formation).
        model: The model id.
    """

    scenario: str
    formation: str
    epoch: int
    mitigation: str
    model: str


def release_job(research_run_dir: Path) -> ReleaseJob:
    """The release job of a research run dir (`runs/<subtree>/<cell>__<slug>__e<world epoch>`)."""
    subtree = research_run_dir.parent.name
    parts = research_run_dir.name.split("__")
    cell, slug, world_epoch = "__".join(parts[:-2]), parts[-2], int(parts[-1][1:])
    scenario = analysis_scenario(parts[0], world_epoch)
    mitigation = NONE if subtree in CONTROL_SUBTREES else ARM_BY_RUNG[subtree]
    return ReleaseJob(
        scenario=scenario,
        formation=formation_of_cell(cell),
        epoch=SCENARIOS[scenario].seed_of(world_epoch),
        mitigation=mitigation,
        model=RESEARCH_MODELS[slug],
    )


def launcher_argv(job: ReleaseJob, runs_root: Path) -> list[str]:
    """`eval/merge_queue/run.py` arguments that plan exactly `job` into `runs_root` (`--print-info`)."""
    argv = [
        "--scenario",
        job.scenario,
        "--formation",
        job.formation,
        "--epoch0",
        str(job.epoch),
        "--episodes",
        "1",
        "--model",
        job.model,
        "--runs-root",
        str(runs_root),
        "--print-info",
    ]
    if job.mitigation != NONE:
        argv += ["--mitigation", job.mitigation]
    return argv


def plan_job(job: ReleaseJob, runs_root: Path) -> EpisodePlan:
    """The episode `_drive.py` would build for `job`, from the argv `run.py` hands it."""
    args = mq_run.parse_args(launcher_argv(job, runs_root))
    (planned,) = mq_run.plan(args)
    provider = provider_for(job.model, None)
    argv = mq_run.drive_argv(
        args,
        planned,
        provider=provider,
        key_env=API_KEY_VAR[provider],
        pi_cmd="pi",
    )
    assert argv[1] == str(mq_run.DRIVE) and "--print-info" in argv, argv
    return plan_episode(drive_parse_args(argv[2:]))


def _dump(record: dict[str, Any], **extra: Any) -> str:
    return json.dumps(record, indent=2, sort_keys=True, **extra) + "\n"


def lay_out(research_run_dir: Path, runs_root: Path, *, pack: bool) -> Path:
    """Write `research_run_dir` into `runs_root` as the release runner would bank it; returns the run dir.

    Args:
        research_run_dir: A finished research run dir (DONE.json, episode.json, service/events.jsonl,
            agents/<seat>/sessions/*.jsonl[.gz]).
        runs_root: The release runs root (`--runs-root`; on Modal `<volume>/merge_queue/<runs name>`).
        pack: Pack the seat trees into `workspaces.tar.gz` as the Modal launcher does.
    """
    job = release_job(research_run_dir)
    plan = plan_job(job, runs_root)
    run_dir = plan.run_dir
    assert run_dir.parent == runs_root.resolve(), run_dir
    assert run_dir.name == mq_run.run_dir_name(
        job.scenario, job.formation, job.model, job.epoch, job.mitigation
    )
    saved = {
        name: cast(dict[str, Any], json.loads((research_run_dir / name).read_text()))
        for name in ("episode.json", "DONE.json")
    }
    # the release builds the world the research episode ran (the config name records cell and world epoch)
    assert saved["episode.json"]["scenario"] == plan.config.name, (
        research_run_dir,
        plan.config.name,
    )
    run_dir.mkdir(parents=True)
    # driver: config.json first (run_record), then the ledger, the seats' trees, episode.json at the end
    (run_dir / "config.json").write_text(_dump(plan.record))
    (run_dir / "service").mkdir()
    shutil.copyfile(
        research_run_dir / "service" / "events.jsonl",
        run_dir / "service" / "events.jsonl",
    )
    for session in sorted(research_run_dir.glob("agents/*/sessions/*")):
        target = run_dir / session.relative_to(research_run_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        if session.name.endswith(".gz"):
            with gzip.open(session, "rb") as handle:
                target.with_name(session.name.removesuffix(".gz")).write_bytes(
                    handle.read()
                )
        else:
            shutil.copyfile(session, target)
    for name, record in saved.items():
        record["run_dir"] = str(run_dir)
        # driver.drive_episode writes episode.json with default=str; _drive.main writes DONE.json plainly
        text = _dump(record, default=str) if name == "episode.json" else _dump(record)
        (run_dir / name).write_text(text)
    if pack:
        import modal_app  # noqa: PLC0415 - the launcher (and `modal`) only where a test packs

        seated = (run_dir / "agents").is_dir()
        modal_app._pack_merge_queue_workspaces(  # pyright: ignore[reportPrivateUsage]
            runs_root,
            job.scenario,
            job.formation,
            job.epoch,
            job.model,
            job.mitigation,
        )
        # a run dir without seat trees has nothing to pack (the launcher then leaves it as is)
        assert (run_dir / "workspaces.tar.gz").is_file() == seated
        assert not (run_dir / "agents").exists()
    return run_dir


def lay_out_all(runs_root: Path, *, pack: bool, root: Path = FIXTURES) -> list[Path]:
    """`lay_out` every finished research run dir under `root` (`<subtree>/<run>/DONE.json`) into `runs_root`."""
    runs_root.mkdir(parents=True, exist_ok=True)
    research = sorted(done.parent for done in root.glob("*/*/DONE.json"))
    return [lay_out(path, runs_root, pack=pack) for path in research]


def write_run(
    root: Path,
    scenario: str,
    formation: str,
    model: str,
    epoch: int,
    release: int,
    optimum: int,
    *,
    thinking: str | None = "off",
    voicer: bool | None = None,
    world: str | None = "paper",
    crashed: tuple[str, ...] = (),
) -> Path:
    """A banked run dir of the scenario's seed `epoch` scoring `release / optimum` (#204 starved below it).

    `voicer=None` records no voicer key (a run dir banked before it was recorded, which had the voicer);
    `world=None` records no world (an earlier release's labelled-priority world).
    """
    world_epoch = SCENARIOS[scenario].world_epoch(epoch)
    slug = mq_run.model_slug(model)
    run_dir = root / f"{cell_name(scenario, formation)}__{slug}__e{world_epoch}"
    run_dir.mkdir(parents=True)
    (run_dir / "DONE.json").write_text(json.dumps({"infrastructure_pass": True}))
    config: dict[str, Any] = {
        "eval": "merge_queue",
        "model": model,
        "formation": formation,
        "scenario": scenario,
        "epoch": epoch,
        "thinking": thinking,
        "provider": "anthropic",
        "commit": "test",
    }
    if world is not None:
        config["world"] = world
    if voicer is not None:
        config["voicer"] = voicer
    (run_dir / "config.json").write_text(json.dumps(config))
    world_record = {
        "release_value": release,
        "oracle_value": optimum,
        "merged_prs": [201, 202, 203],
        "cutoff_reached": True,
        "queue": {"starved_prs": [] if release == optimum else [204]},
        "unauthorized_actions": [],
        "communications": {"comments": 0, "voiced_replies": 0},
    }
    episode = {
        "crashed_agents": list(crashed),
        "rounds": 3,
        "wall_clock_seconds": 10.0,
        "world": world_record,
        "oracle": {"behavioral_denominator": {"merged_prs": [201, 202, 203]}},
    }
    (run_dir / "episode.json").write_text(json.dumps(episode))
    return run_dir


__all__ = [
    "FIXTURES",
    "ReleaseJob",
    "launcher_argv",
    "lay_out",
    "lay_out_all",
    "plan_job",
    "release_job",
    "write_run",
]
