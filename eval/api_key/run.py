"""Run the MAMUBench api_key eval: scenario x formation x epoch, seats sharing one token-capped budget.

    python eval/api_key/run.py --list
    python eval/api_key/run.py --list-mitigations
    python eval/api_key/run.py --scenario stakes_100 --formation coordinator team --episodes 2 \
        --model claude-sonnet-5                      # the simulated harness: the paper's instrument
    python eval/api_key/run.py --scenario stakes_100 --model gpt-5.6-sol --print-info   # each cell's instrument
    python eval/api_key/run.py --all --episodes 20 --parallel 8 --model claude-opus-5 --harness pi
    python eval/api_key/run.py --jobs-file episodes.csv --print-info    # explicit episodes (eval/_jobs.py)
    python eval/api_key/run.py --all --formation solo coordinator team team_silent --episodes 20 \
        --model claude-opus-5                        # the paper's formation matrix for one model
    python eval/api_key/run.py --all --formation team --mitigation lead_value --episodes 20 \
        --model claude-opus-5                        # the paper's recommended mitigation

The default harness is `sim` (the paper's scripted driver; every cell plays the settings behind its paper
number: the formation's scheduler instrument, `cells.PAPER_INSTRUMENT`, or the lead arms' ladder, with the
paper's step budget, time limits and per-provider reasoning setting). `--harness pi` runs real pi seats (a
different instrument; `--fake-pi` implies it).
Episodes are resumable (a finished `DONE.json` is skipped; a partial run dir is wiped and rerun) and
storm-aborted episodes are simply rerun by the next invocation. Shard with `--epoch0/--episodes` across
processes into the same `--runs-root`. See `_harness/sim.py` and `_harness/runner.py` for the episode itself.

`--mitigation NAME` runs a mitigation arm of `api_key/mitigations/` (default `none`, the formation itself;
the arm is recorded and stamps the run dir): `lead_value` and `lead_full_stack` (formation `team`, simulated
harness). The `solo` formation (one owner, one agent) runs on the simulated harness only; `--formation` defaults
to the three multi-principal formations (`scenarios.DEFAULT_FORMATIONS`).
"""

from __future__ import annotations

import argparse
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import bootstrap  # noqa: E402

bootstrap()

from dotenv import load_dotenv  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
# Fill unset provider keys from the repository .env (shell exports win), as personal_assistant/run.py
# does, so the direct runner and the root launcher read the same file.
load_dotenv(REPO_ROOT / ".env", override=False)

from _harness import runner, sim  # noqa: E402
from _mitigations import NONE  # noqa: E402

from api_key import cells, mitigations, scenarios  # noqa: E402

EVAL_ROOT = Path(__file__).resolve().parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    which = parser.add_argument_group("which scenarios")
    which.add_argument(
        "--scenario", nargs="*", default=[], help="scenario ids (see --list)"
    )
    which.add_argument(
        "--seats",
        type=int,
        choices=(4, 8, 16),
        default=None,
        help="every scenario with this cast size",
    )
    which.add_argument("--all", action="store_true", help="all 25 scenarios of record")
    runner.add_common_args(
        parser,
        formations=tuple(scenarios.FORMATIONS),
        default_formations=scenarios.DEFAULT_FORMATIONS,
        mitigations=tuple(mitigations.MITIGATIONS),
    )
    parser.add_argument(
        "--parallel", type=int, default=1, help="episodes run concurrently"
    )
    args = parser.parse_args(argv)
    runner.validate_args(parser, args)
    if args.harness == "sim" and args.parallel != 1:
        parser.error(sim.PARALLEL_REFUSAL)
    if args.jobs_file is not None and (args.scenario or args.all or args.seats):
        parser.error(
            "--jobs-file lists every episode; drop --scenario / --all / --seats"
        )
    return args


def check_cell(formation: str, mitigation: str, harness: str) -> None:
    """`runner.plan_jobs`'s check: the formation runs on this harness and the arm applies to it there.

    `--formation` is checked by argparse; this also covers a jobs file's formations.
    """
    if formation not in scenarios.FORMATIONS:
        raise ValueError(
            f"unknown api_key formation {formation!r}; expected one of {tuple(scenarios.FORMATIONS)}"
        )
    cells.check_formation(formation, harness)
    mitigations.validate(mitigation, [formation], harness)


def plan(args: argparse.Namespace) -> list[runner.Job]:
    """Every episode of the invocation (matrix or `--jobs-file`); exits with the message on a bad plan."""
    try:
        return runner.plan_jobs(
            args,
            eval_name="api_key",
            default_runs_root=EVAL_ROOT / "runs",
            select=lambda: [
                row.id
                for row in scenarios.select(
                    args.scenario, all_=args.all, seats=args.seats
                )
            ],
            canonical=lambda name: scenarios.scenario(name).id,
            check=lambda formation, mitigation: check_cell(
                formation, mitigation, str(args.harness)
            ),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


def recipe_for(config: runner.RunConfig) -> sim.SimRecipe:
    """The simulated-harness recipe of one run config: its (scenario, formation) or mitigation arm."""
    return cells.build_sim_recipe(
        config.scenario, config.formation, mitigation=config.mitigation
    )


def run_pi(jobs: list[runner.Job], api_key: str, parallel: int) -> int:
    """Play every episode on real pi seats, `parallel` at a time; returns the number that failed."""
    failures = 0
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {
            pool.submit(
                runner.run_epochs,
                config,
                lambda e, c=config: cells.build_cell(
                    c.scenario, c.formation, e, c.mitigation
                ),
                [epoch],
                api_key,
            ): (config, epoch)
            for config, epoch in jobs
        }
        for future in as_completed(futures):
            config, epoch = futures[future]
            try:
                failures += future.result()
            except Exception:  # noqa: BLE001 — one episode must not destroy resumability
                failures += 1
                print(
                    f"[{config.scenario} {config.formation} e{epoch}] FAILED (rerun the same command to resume):",
                    flush=True,
                )
                traceback.print_exc()
    return failures


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        print(scenarios.listing())
        return 0
    if args.list_mitigations:
        print(mitigations.listing())
        return 0
    jobs = plan(args)
    configs = list(dict.fromkeys(config for config, _ in jobs))
    if args.jobs_file is not None:
        shape = f"jobs file {args.jobs_file}"
    else:
        epochs = list(range(args.epoch0, args.epoch0 + args.episodes))
        shape = (
            f"{len({c.scenario for c in configs})} scenario(s) x {args.formation} x epochs "
            f"{epochs[0]}-{epochs[-1]}"
        )
    arms = sorted({c.mitigation for c in configs})
    print(
        f"{len(jobs)} episode(s): {shape}; model={configs[0].model} provider={configs[0].provider} "
        f"exec={cells.EXEC_DIAL} clock={cells.CLOCK_DIAL} harness={args.harness} parallel={args.parallel} "
        + (
            f"thinking={configs[0].thinking} "
            if configs[0].thinking is not None
            else ""
        )
        + (f"mitigation={','.join(arms)} " if arms != [NONE] else "")
        + f"-> {configs[0].runs_root}",
        flush=True,
    )
    if args.print_info:
        if args.harness == "sim":
            for config in configs:
                recipe = recipe_for(config)
                arm = (
                    ""
                    if config.mitigation == NONE
                    else f" mitigation={config.mitigation}"
                )
                print(
                    f"  {config.scenario:18} {config.formation:12} instrument={recipe.instrument} "
                    f"max_turns={recipe.max_turns} burst={recipe.burst} "
                    f"time_limit={recipe.time_limit_s}s retry={recipe.retry_time_limit_s} "
                    f"knobs={recipe.knobs or '-'}{arm} {sim.model_settings(config, recipe)}"
                )
        for config, epoch in jobs:
            print(runner.job_line(config, epoch, 18))
        return 0
    api_key = runner.prepare(configs[0], args.api_key)
    if args.harness == "sim":
        failures = sum(
            sim.run_epochs(config, lambda c=config: recipe_for(c), [epoch], api_key)
            for config, epoch in jobs
        )
    else:
        failures = run_pi(jobs, api_key, args.parallel)
    print(
        f"{len(jobs) - failures}/{len(jobs)} episodes completed -> {configs[0].runs_root}",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
