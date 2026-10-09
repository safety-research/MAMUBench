"""Run the MAMUBench merge_queue eval: scenario x formation x epoch, real pi seats repairing PRs into one shared merge queue.

The merge queue is the paper's studied extension, not one of MAMUBench's 74 scenarios.

    python eval/merge_queue/run.py --list
    python eval/merge_queue/run.py --list-mitigations
    python eval/merge_queue/run.py --scenario oversub --formation coordinator team --episodes 2 --model claude-sonnet-5
    python eval/merge_queue/run.py --all --episodes 20 --parallel 6 --model claude-opus-5   # the paper's matrix
    python eval/merge_queue/run.py --all --formation team --mitigation lead_cut_line --episodes 5
    python eval/merge_queue/run.py --jobs-file episodes.csv --print-info   # explicit episodes (eval/_jobs.py)
    python eval/merge_queue/run.py --all --formation team --mitigation priorities --episodes 5 --print-info --render-to /tmp/briefs

`--all` is the paper's three reported scenarios (`oversub`, `volunteer_p1`, `volunteer_p3`; the non-scarce
control `baseline_tight` runs with `--scenario`) and the default formations are all four (`coordinator`,
`team`, `team_silent`, `solo`). Episodes count each scenario's seeds: `--episodes 20` of `volunteer_p1` is world
epochs 1, 4, ..., 58, the paper's seeds (`scenarios.Scenario.world_epoch`); run dirs carry the world epoch.

Every episode runs the paper's world: no priority labels (a first-come queue), no captain on captainless
cells, owners stating only their own consequences, only the minute-0 owner brief scheduled.

Every episode runs in its own interpreter (`_drive.py`)
and is resumable: a run dir with `DONE.json` is skipped; a structurally incomplete one is re-driven
(the earlier attempt is quarantined under `.attempt<N>.failed/`). Shard with
`--epoch0/--episodes` across processes into the same `--runs-root`.

An episode is real execution: `git`, `python -m pytest` on the seeded Jinja clones, one pi process
per seat (1 or 4) plus the reply-only Sonnet voicer, 15-60 minutes of wall clock for Sonnet and up
to a few hours for Opus. The voicer needs an Anthropic key whatever the target provider
(`--voicer-key-env`, default `ANTHROPIC_API_KEY`); `--no-voicer` is not the battery's surface.

Claude seats run with thinking OFF unless `--thinking` says otherwise: the paper's model-settings
appendix switches thinking off for the merge queue. Keys come from the shell or the repository `.env`
(shell exports win).

`--mitigation NAME` runs an arm of `merge_queue/mitigations/` (default `none`, the formation itself; the
arms apply to the `team` formation on the paper's world): the run dir is `<cell>__mit-<name>__<model>__e<N>`
and its `config.json` records the arm (and a lead arm's `__live_captain` cell).

`--print-info --render-to DIR` builds every planned episode exactly as its `_drive.py` process would (the same
argv) and writes `DIR/<run dir>/config.json` and `DIR/<run dir>/<seat>/AGENTS.md`: the record and the briefs
the seats would auto-load, with no key, pi or episode. The root launcher forwards it (`python run.py
merge_queue --print-info ... --render-to DIR`, either backend).
"""

from __future__ import annotations

import argparse
import functools
import os
import re
import shutil
import subprocess
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import REPO_ROOT, bootstrap  # noqa: E402

bootstrap()

from dotenv import load_dotenv  # noqa: E402

# Fill unset keys from the repository .env; shell exports win.
load_dotenv(REPO_ROOT / ".env", override=False)

from _jobs import JobsFileError, read_jobs_file  # noqa: E402
from _mitigations import NONE, stamp  # noqa: E402
from _providers import (  # noqa: E402
    KEY_ENV_VARS,
    PROVIDERS,
    THINKING_BY_PROVIDER,
    provider_for,
    resolve_api_key,
)

from merge_queue import mitigations, scenarios  # noqa: E402
from merge_queue._drive import API_KEY_VAR, KEY_REJECTED  # noqa: E402
from merge_queue.scenarios._world import PAPER  # noqa: E402

EVAL_ROOT = Path(__file__).resolve().parent
DRIVE = EVAL_ROOT / "_drive.py"

#: The paper runs' slugs for the model ids they ran (run-dir slugs stay comparable with the paper's run dirs).
CAMPAIGN_SLUGS: dict[str, str] = {
    "claude-sonnet-5": "sonnet5",
    "claude-opus-5": "opus5",
    "claude-opus-4-8": "opus48",
    "claude-haiku-4-5": "haiku45",
    "gpt-5.5": "gpt55",
    "gpt-5.6-terra": "gpt56terra",
    "z-ai/glm-5.2": "glm52",
    "qwen/qwen3.7-max": "qwen37max",
    "minimax/minimax-m3": "minimaxm3",
}


def model_slug(model: str) -> str:
    """The run-dir slug for a model id: the paper runs' slug when it has one, else `[a-z0-9]+` of the id."""
    return CAMPAIGN_SLUGS.get(model) or re.sub(r"[^a-z0-9]", "", model.lower())


def run_dir_name(
    scenario: str, formation: str, model: str, epoch: int, mitigation: str = NONE
) -> str:
    """The run dir `_drive.py` banks an episode in: `<cell>[__mit-<arm>]__<slug>__e<world epoch>`.

    The cell is the formation's own cell (an arm that changes the cell, a lead seat say, records
    its own in `config.json`), so the name is known before the episode runs (`modal_app` packs by it).
    `epoch` is the scenario's seed; the name carries its world epoch (the research grammar).
    """
    world_epoch = scenarios.scenario(scenario).world_epoch(epoch)
    return (
        f"{scenarios.cell_name(scenario, formation)}{stamp(mitigation)}"
        f"__{model_slug(model)}__e{world_epoch}"
    )


@functools.lru_cache(maxsize=None)
def git_commit() -> str:
    if override := os.environ.get("EVAL_GIT_SHA", "").strip():
        return override
    try:
        out = subprocess.run(
            ["git", "-C", str(EVAL_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:  # no git on this host
        return "unknown"
    return out.stdout.strip() or "unknown"


@dataclass(frozen=True)
class Job:
    scenario: str
    formation: str
    epoch: int
    mitigation: str = NONE

    @property
    def world_epoch(self) -> int:
        """The drive-side epoch (the world seed) of this job's scenario seed."""
        return scenarios.scenario(self.scenario).world_epoch(self.epoch)

    @property
    def epoch_label(self) -> str:
        """`e<seed>`, plus the world epoch when it differs (a volunteer profile's seed)."""
        world = (
            "" if self.world_epoch == self.epoch else f" (world e{self.world_epoch})"
        )
        return f"e{self.epoch}{world}"

    @property
    def label(self) -> str:
        arm = "" if self.mitigation == NONE else f" [{self.mitigation}]"
        return f"{self.scenario} {self.formation} {self.epoch_label}{arm}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    which = parser.add_argument_group("which scenarios")
    which.add_argument(
        "--scenario", nargs="*", default=[], help="scenario ids (see --list)"
    )
    which.add_argument(
        "--all",
        action="store_true",
        help=f"the paper's three reported scenarios ({', '.join(scenarios.PAPER_SCENARIOS)})",
    )
    which.add_argument(
        "--jobs-file",
        type=Path,
        default=None,
        help="a CSV of explicit episodes (scenario,formation,epoch[,mitigation]; see eval/_jobs.py) "
        "instead of the matrix; exclusive with --scenario, --all, --formation, --episodes, --epoch0",
    )
    parser.add_argument(
        "--formation",
        nargs="+",
        choices=tuple(scenarios.FORMATIONS),
        default=None,
        help=f"default: {' '.join(scenarios.FORMATIONS)}",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="seeds per scenario (default: 1; volunteer_p<p> seed k is world epoch 3(k-1)+p)",
    )
    parser.add_argument(
        "--epoch0", type=int, default=None, help="first seed (1-based; default 1)"
    )
    # `--epochs` is not an option (episodes per cell is `--episodes`): declared hidden only so that it is refused,
    # and so that `--epoch N` stays ambiguous instead of argparse expanding it to `--epoch0 N`.
    parser.add_argument(
        "--epochs", dest="not_episodes", nargs="?", const="", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--mitigation",
        choices=tuple(mitigations.MITIGATIONS),
        default=NONE,
        help="mitigation arm (default none = the formation itself; see --list-mitigations); recorded "
        "and stamped on the run dir (`__mit-<name>`)",
    )
    parser.add_argument(
        "--list-mitigations",
        action="store_true",
        help="print the mitigation registry and exit",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("MODEL", "claude-sonnet-5"),
        help="pi model id: claude-* (anthropic), gpt-*/o* (openai), <vendor>/<model> (openrouter)",
    )
    parser.add_argument("--provider", default=None, choices=PROVIDERS)
    parser.add_argument(
        "--key-env", default=None, help="env var holding the target key"
    )
    parser.add_argument(
        "--api-key", default=None, help="the target key itself (wins over --key-env)"
    )
    parser.add_argument(
        "--voicer-key-env",
        default="ANTHROPIC_API_KEY",
        help="env var holding the Anthropic key for the reply-only Sonnet voicer",
    )
    parser.add_argument(
        "--no-voicer",
        action="store_true",
        help="run without the requester voicer (NOT the battery's surface; for plumbing checks)",
    )
    parser.add_argument(
        "--thinking",
        default=None,
        help="pi thinking level (default per provider: anthropic off (the paper's setting), openai medium)",
    )
    parser.add_argument("--turn-timeout", type=float, default=1800.0)
    parser.add_argument(
        "--attempts", type=int, default=3, help="drive attempts per episode"
    )
    parser.add_argument("--runs-root", type=Path, default=EVAL_ROOT / "runs")
    parser.add_argument(
        "--agent-roots-base",
        type=Path,
        default=Path(
            os.environ.get("EVAL_MQ_AGENT_ROOTS", str(Path.home() / "work_mq"))
        ),
        help="where the seats' de-identified live workspaces go (local disk; one per concurrent lane)",
    )
    parser.add_argument(
        "--parallel", type=int, default=1, help="episodes run concurrently"
    )
    parser.add_argument(
        "--pi-cmd",
        default=os.environ.get("EVAL_PI_CMD"),
        help="absolute path to pi 0.77.0",
    )
    parser.add_argument(
        "--node-dir", type=Path, default=os.environ.get("EVAL_NODE_DIR")
    )
    parser.add_argument(
        "--print-info",
        action="store_true",
        help="print the job matrix and exit, running nothing (useful before an expensive eval)",
    )
    # `--dry-run` is not an option (printing the job matrix without running it is `--print-info`): declared hidden
    # only so that it is refused.
    parser.add_argument(
        "--dry-run", dest="not_print_info", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--render-to",
        type=Path,
        default=None,
        help="with --print-info: build every episode exactly as _drive.py would (its argv, no episode runs) "
        "and write DIR/<run dir>/config.json and DIR/<run dir>/<seat>/AGENTS.md (the briefs the seats "
        "would auto-load)",
    )
    parser.add_argument(
        "--list", action="store_true", help="print the scenario registry and exit"
    )
    args = parser.parse_args(argv)
    if args.not_episodes is not None:
        parser.error("unknown option --epochs (episodes per cell is --episodes)")
    if args.not_print_info:
        parser.error(
            "unknown option --dry-run (printing the job matrix without running it is --print-info)"
        )
    if args.jobs_file is not None:
        given = [
            flag
            for flag, value in (("--scenario", args.scenario), ("--all", args.all))
            if value
        ] + [
            flag
            for flag, value in (
                ("--formation", args.formation),
                ("--episodes", args.episodes),
                ("--epoch0", args.epoch0),
            )
            if value is not None
        ]
        if given:
            parser.error(f"--jobs-file lists every episode; drop {', '.join(given)}")
    if args.formation is None:
        args.formation = list(scenarios.FORMATIONS)
    args.episodes = 1 if args.episodes is None else args.episodes
    args.epoch0 = 1 if args.epoch0 is None else args.epoch0
    if args.episodes < 1 or args.epoch0 < 1:
        parser.error("--episodes and --epoch0 are 1-based positive integers")
    if args.render_to is not None and not args.print_info:
        parser.error("--render-to renders what --print-info plans; add --print-info")
    return args


def check_formation(formation: str) -> None:
    """Refuse a formation this eval does not run (a jobs file's; `--formation` has argparse choices)."""
    if formation not in scenarios.FORMATIONS:
        raise ValueError(
            f"unknown merge_queue formation {formation!r}; expected one of {tuple(scenarios.FORMATIONS)}"
        )


def plan(args: argparse.Namespace) -> list[Job]:
    """Every episode of the invocation: the matrix, or `--jobs-file`'s list (exits on a bad plan)."""
    try:
        if args.jobs_file is not None:
            specs = read_jobs_file(args.jobs_file, default_mitigation=args.mitigation)
            jobs = [
                Job(
                    scenarios.scenario(spec.scenario).id,
                    spec.formation,
                    spec.epoch,
                    spec.mitigation,
                )
                for spec in specs
            ]
        else:
            jobs = [
                Job(row.id, formation, epoch, str(args.mitigation))
                for row in scenarios.select(args.scenario, all_=args.all)
                for formation in args.formation
                for epoch in range(args.epoch0, args.epoch0 + args.episodes)
            ]
        for job in jobs:
            check_formation(job.formation)
            mitigations.validate(job.mitigation, [job.formation])
    except (JobsFileError, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    return jobs


def resolve_thinking(provider: str, requested: str | None) -> str:
    """The pi thinking level an invocation runs: `--thinking` when given, else the provider's default.

    Anthropic seats default to `off` (the paper's setting and the matrix of record), OpenAI seats to
    `medium` (`_providers.THINKING_BY_PROVIDER`), exactly as `personal_assistant.registry.resolve_thinking`.
    """
    return requested if requested is not None else THINKING_BY_PROVIDER[provider]


def resolve_pi(pi_cmd: str | None, node_dir: Path | None) -> str:
    """The pinned pi as an absolute path; `node` must be on PATH (prepend `--node-dir`)."""
    resolved = pi_cmd or shutil.which("pi")
    if not resolved:
        raise SystemExit(
            "pi not found — set EVAL_PI_CMD to the absolute path of pi 0.77.0"
        )
    if node_dir is not None:
        os.environ["PATH"] = os.pathsep.join(
            [str(node_dir), os.environ.get("PATH", "")]
        )
    if shutil.which("node") is None:
        raise SystemExit(
            "node not found on PATH — set EVAL_NODE_DIR to a Node 22+ bin dir"
        )
    return str(Path(resolved).resolve())


def drive_argv(
    args: argparse.Namespace, job: Job, *, provider: str, key_env: str, pi_cmd: str
) -> list[str]:
    argv = [
        sys.executable,
        str(DRIVE),
        "--scenario",
        job.scenario,
        "--formation",
        job.formation,
        "--epoch",
        str(job.epoch),
        "--model",
        args.model,
        "--model-slug",
        model_slug(args.model),
        "--provider",
        provider,
        "--key-env",
        key_env,
        "--voicer-key-env",
        args.voicer_key_env,
        "--turn-timeout",
        str(args.turn_timeout),
        "--attempts",
        str(args.attempts),
        "--runs-root",
        str(args.runs_root.resolve()),
        "--agent-roots-base",
        str(args.agent_roots_base.expanduser().resolve()),
        "--pi-cmd",
        pi_cmd,
        "--commit",
        git_commit(),
        # Always the resolved level: `_drive` records it in the run dir's config.json.
        "--thinking",
        resolve_thinking(provider, args.thinking),
    ]
    if job.mitigation != NONE:
        argv += ["--mitigation", job.mitigation]
    if args.no_voicer:
        argv.append("--no-voicer")
    if args.print_info:
        argv.append("--print-info")
    return argv


def render_briefs(args: argparse.Namespace, jobs: list[Job], *, provider: str) -> int:
    """`--render-to`: build every job exactly as its `_drive.py` process would and write what its seats get.

    Each job's argv is the one `drive_argv` hands `_drive.py` (parsed by `_drive.parse_args`, planned by
    `_drive.plan_episode`); `_drive.render` writes `<render-to>/<run dir name>/config.json` (the record the
    run dir would bank) and `<render-to>/<run dir name>/<seat>/AGENTS.md` (every auto-loaded brief). No key,
    pi, workspace or runs root is touched. Returns the number of files written.
    """
    from merge_queue._drive import parse_args as drive_parse_args  # noqa: PLC0415
    from merge_queue._drive import plan_episode, render  # noqa: PLC0415

    assert args.render_to is not None
    root = Path(args.render_to).resolve()
    key_env = args.key_env or API_KEY_VAR[provider]
    files = 0
    for job in jobs:
        argv = drive_argv(
            args, job, provider=provider, key_env=key_env, pi_cmd=args.pi_cmd or "pi"
        )
        episode = plan_episode(drive_parse_args(argv[2:]))
        files += len(render(episode, root / episode.run_name))
    print(f"rendered {len(jobs)} episode(s), {files} files -> {root}", flush=True)
    return files


def target_key_env(provider: str, key_env: str | None) -> str:
    """The variable the target key travels to `_drive.py` under: `--key-env`, else the provider's first set one.

    A provider can have several conventional variables (OpenRouter: `OPENROUTER_API_KEY`, `OPEN_ROUTER_KEY`;
    `_providers.KEY_ENV_VARS`), and the driver reads exactly the one it is named; with none set, the first.
    """
    if key_env:
        return key_env
    names = KEY_ENV_VARS[provider]
    return next((name for name in names if os.environ.get(name, "").strip()), names[0])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        print(scenarios.listing())
        return 0
    if args.list_mitigations:
        print(mitigations.listing())
        return 0
    jobs = plan(args)
    provider = provider_for(args.model, args.provider)
    if args.jobs_file is not None:
        shape = f"jobs file {args.jobs_file}"
    else:
        shape = (
            f"{len({job.scenario for job in jobs})} scenario(s) x {args.formation} x epochs "
            f"{args.epoch0}-{args.epoch0 + args.episodes - 1}"
        )
    arms = sorted({job.mitigation for job in jobs})
    print(
        f"{len(jobs)} episode(s): {shape}; world={PAPER} model={args.model} provider={provider} "
        f"thinking={resolve_thinking(provider, args.thinking)} voicer={not args.no_voicer} "
        f"parallel={args.parallel} "
        + (f"mitigation={','.join(arms)} " if arms != [NONE] else "")
        + f"-> {args.runs_root.resolve()}",
        flush=True,
    )
    if args.print_info:
        for job in jobs:
            arm = "" if job.mitigation == NONE else f" mitigation={job.mitigation}"
            print(f"  {job.scenario:16} {job.formation:12} {job.epoch_label}{arm}")
        if args.render_to is not None:
            render_briefs(args, jobs, provider=provider)
        return 0
    pi_cmd = resolve_pi(args.pi_cmd, args.node_dir)
    # The key travels to the driver by variable NAME; an explicit --api-key is exported under one.
    key_env = target_key_env(provider, args.key_env)
    if args.api_key:
        key_env = "EVAL_MQ_TARGET_KEY"
        os.environ[key_env] = args.api_key
    # fail early with the resolver's message (every alias of the provider when no variable was named)
    resolve_api_key(provider, key_env if args.key_env or args.api_key else None)
    if not args.no_voicer:
        resolve_api_key("anthropic", args.voicer_key_env)
    failures = 0
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(
                subprocess.run,
                drive_argv(
                    args, job, provider=provider, key_env=key_env, pi_cmd=pi_cmd
                ),
            ): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                rc = future.result().returncode
            except Exception:  # noqa: BLE001 — one episode must not destroy resumability
                failures += 1
                print(
                    f"[{job.label}] FAILED (rerun the same command to resume):",
                    flush=True,
                )
                traceback.print_exc()
                continue
            if rc == KEY_REJECTED:
                failures += 1
                print(
                    f"[{job.label}] FAILED: the provider refused the target key (fix the key, then rerun)",
                    flush=True,
                )
            elif rc not in (0, 2):
                failures += 1
                print(
                    f"[{job.label}] FAILED rc={rc} (rerun the same command to resume)",
                    flush=True,
                )
    print(
        f"{len(jobs) - failures}/{len(jobs)} episodes completed -> {args.runs_root.resolve()}",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
