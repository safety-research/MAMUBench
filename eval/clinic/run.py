"""Run the MAMUBench clinic eval: board x formation x epoch, desks triaging onto one shared calendar.

    python eval/clinic/run.py --list
    python eval/clinic/run.py --list-mitigations
    python eval/clinic/run.py --board warfarin_inr_split --formation coordinator team --episodes 2 \
        --model claude-sonnet-5                      # the simulated harness: the paper's instrument
    python eval/clinic/run.py --board warfarin_inr_split --model gpt-5.6-sol --print-info   # each cell's instrument
    python eval/clinic/run.py --all --episodes 20 --parallel 8 --model claude-opus-5 --harness pi
    python eval/clinic/run.py --jobs-file mornings.csv --print-info     # explicit episodes (eval/_jobs.py)

The default harness is `sim` (the paper's scripted driver; every cell plays its own settings: the formation's
scheduler instrument, `cells.PAPER_INSTRUMENT`, or the arms' `cells.MITIGATION_INSTRUMENT`, with the paper's
per-provider reasoning setting). `--harness pi` runs real pi seats (a different instrument;
`--fake-pi` implies it).

Episodes are resumable (a finished `DONE.json` is skipped; a partial run dir is wiped and rerun) and
storm-aborted episodes are simply rerun by the next invocation. Shard with `--epoch0/--episodes` across
processes into the same `--runs-root`. See `_harness/sim.py` and `_harness/runner.py` for the episode itself.

`--mitigation NAME` runs a mitigation arm of `clinic/mitigations/` (default `none`, the formation itself;
the arm is recorded and stamps the run dir): the paper's s1, s2, s3 on the team, under the standard scheduler.
A jobs file's `scenario` column holds board ids; `record.py` writes the paper's episodes of record as jobs
files (one per model x formation x arm, each with its `run.py` command).

    python eval/clinic/run.py --all --formation team --mitigation s3 --episodes 10 --model claude-opus-5
    python eval/clinic/run.py --all --formation team_silent --episodes 5 --model qwen/qwen3.8-max

Read the runs on the paper's metric with `report.py` and compare them with the paper with `check.py`.
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

from clinic import cells, mitigations, scenarios  # noqa: E402

EVAL_ROOT = Path(__file__).resolve().parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    which = parser.add_argument_group("which boards")
    which.add_argument(
        "--board",
        "--scenario",
        dest="board",
        nargs="*",
        default=[],
        help="board ids (see --list); --scenario is the root launcher's name for the same flag",
    )
    which.add_argument(
        "--twin",
        choices=("plain", "split"),
        default=None,
        help="every board of one twin",
    )
    which.add_argument("--all", action="store_true", help="all 24 boards of record")
    runner.add_common_args(
        parser,
        formations=tuple(scenarios.FORMATIONS),
        mitigations=tuple(mitigations.MITIGATIONS),
    )
    parser.add_argument(
        "--parallel", type=int, default=1, help="episodes run concurrently"
    )
    args = parser.parse_args(argv)
    runner.validate_args(parser, args)
    if args.harness == "sim" and args.parallel != 1:
        parser.error(sim.PARALLEL_REFUSAL)
    if args.jobs_file is not None and (args.board or args.all or args.twin):
        parser.error("--jobs-file lists every episode; drop --board / --all / --twin")
    return args


def check_cell(formation: str, mitigation: str, harness: str) -> None:
    """`runner.plan_jobs`'s check: the formation runs here and the arm applies to it on this harness."""
    if formation not in scenarios.FORMATIONS:
        raise ValueError(
            f"unknown clinic formation {formation!r}; expected one of {tuple(scenarios.FORMATIONS)}"
        )
    mitigations.validate(mitigation, [formation], harness)


def plan(args: argparse.Namespace) -> list[runner.Job]:
    """Every episode of the invocation (matrix or `--jobs-file`); exits with the message on a bad plan."""
    try:
        return runner.plan_jobs(
            args,
            eval_name="clinic",
            default_runs_root=EVAL_ROOT / "runs",
            select=lambda: [
                row.id
                for row in scenarios.select(args.board, all_=args.all, twin=args.twin)
            ],
            canonical=lambda board_id: scenarios.board(board_id).id,
            check=lambda formation, mitigation: check_cell(
                formation, mitigation, str(args.harness)
            ),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


def recipe_for(config: runner.RunConfig) -> sim.SimRecipe:
    """The simulated-harness recipe of one run config: its (board, formation) and its mitigation arm."""
    return cells.build_sim_recipe(
        config.scenario, config.formation, mitigation=config.mitigation
    )


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
            f"{len({c.scenario for c in configs})} board(s) x {args.formation} x epochs "
            f"{epochs[0]}-{epochs[-1]}"
        )
    arms = sorted({c.mitigation for c in configs})
    print(
        f"{len(jobs)} episode(s): {shape}; "
        f"model={configs[0].model} provider={configs[0].provider} framing={scenarios.FRAMING} "
        f"harness={args.harness} parallel={args.parallel} "
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
                    f"  {config.scenario:34} {config.formation:12} instrument={recipe.instrument} "
                    f"max_turns={recipe.max_turns} burst={recipe.burst} "
                    f"time_limit={recipe.time_limit_s}s retry={recipe.retry_time_limit_s} "
                    f"knobs={recipe.knobs or '-'}{arm} {sim.model_settings(config, recipe)}"
                )
        for config, epoch in jobs:
            print(runner.job_line(config, epoch, 34))
        return 0
    api_key = runner.prepare(configs[0], args.api_key)
    failures = 0
    if args.harness == "sim":
        for config, epoch in jobs:
            failures += sim.run_epochs(
                config,
                lambda c=config: recipe_for(c),
                [epoch],
                api_key,
            )
        print(
            f"{len(jobs) - failures}/{len(jobs)} episodes completed -> {configs[0].runs_root}",
            flush=True,
        )
        return 1 if failures else 0
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
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
    print(
        f"{len(jobs) - failures}/{len(jobs)} episodes completed -> {configs[0].runs_root}",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
