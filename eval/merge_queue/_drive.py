r"""Drive ONE merge-queue episode in its own interpreter (the paper's direct driver, no eval_set).

`run.py` launches this script once per (scenario, formation, epoch). All
world and runtime imports are package-qualified, and each episode has its own
process, pi sessions, workspace, seed, and recovery boundary.

    python eval/merge_queue/_drive.py --scenario oversub --formation team --epoch 3 \\
        --model claude-sonnet-5 --provider anthropic --key-env ANTHROPIC_API_KEY \\
        --voicer-key-env ANTHROPIC_API_KEY --runs-root eval/merge_queue/runs/first \\
        --agent-roots-base ~/work_mq --pi-cmd /abs/path/to/pi [--thinking off] [--mitigation NAME] \\
        [--print-info [--render-to DIR]]

`--print-info` builds the episode (`plan_episode`: cell, config, world variant, run dir, `config.json` record)
and prints the record without driving; `--render-to DIR` also writes that record and every seat's
auto-loaded AGENTS.md (`DIR/<seat>/AGENTS.md`, byte for byte what the drive puts in the seats' workspaces).

`--epoch` is the scenario's seed k (1-based); the world epoch, which seeds the world and names the run dir,
is `scenarios.SCENARIOS[<scenario>].world_epoch(k)` (the identity except for the volunteer profiles:
`volunteer_p1` seed k is world epoch 3(k-1)+1). Every episode runs the paper's world, the world variant
`noprio_nocaptain_subtle_stakes_briefs_only` (`noprio_subtle_stakes_briefs_only` on a lead arm's cell).

Keys are named by environment VARIABLE (never passed as values): the target seats' key goes into
each seat's pi auth file; the reply-only Sonnet voicer (the scripted requesters' replies, the
battery's surface) needs an Anthropic key regardless of the target provider. Exit 0 = `DONE.json`
written (structurally complete episode), 2 = skipped (already done), 1 = failed after `--attempts`,
3 = the provider refused the target key (401 / 403 in the seats' sessions): no further attempt is made.

An attempt interrupted by a signal (`KeyboardInterrupt`: a preempted or stopped container) writes `INCOMPLETE.json`
naming the interruption before it propagates, so the lost attempt keeps a failure record when the next attempt
quarantines it. `DONE.json` / `INCOMPLETE.json` count the earlier attempts quarantined in the run dir
(`quarantined_attempts`: this process's failed attempts and any interrupted container's).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

EVALS_DIR = Path(__file__).resolve().parents[1]
ENV_DIR = Path(__file__).resolve().parent / "environment"
sys.path.insert(0, str(EVALS_DIR))

from _mitigations import NONE, stamp  # noqa: E402
from _providers import KEY_ENV_VARS  # noqa: E402
from _resume import configuration_drift  # noqa: E402

from merge_queue.scenarios import FORMATIONS, SCENARIOS, cell_name  # noqa: E402
from merge_queue.scenarios._world import PAPER  # noqa: E402

if TYPE_CHECKING:
    from merge_queue.environment.resources import ScenarioConfig
    from merge_queue.scenarios._cells import Cell

#: Exit status when the provider refused the target key: an attempt that every re-drive would repeat.
KEY_REJECTED = 3
#: The failure an interrupted attempt records in `INCOMPLETE.json`.
INTERRUPTED = "interrupted (the container was preempted or stopped)"
#: The target key's variable per provider: `run.py` hands the key over under this NAME, and it labels the
#: seats' pi auth file / leak probe (as the paper's runs labelled it).
API_KEY_VAR: dict[str, str] = {p: names[0] for p, names in KEY_ENV_VARS.items()}


def ensure_ci_python() -> None:
    """Provision the environment's pinned CI interpreter (real pytest runs need it) once per host."""
    check = subprocess.run(
        [sys.executable, "ci_environment.py", "check"],
        cwd=ENV_DIR,
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        return
    subprocess.run(
        [sys.executable, "ci_environment.py", "bootstrap"], cwd=ENV_DIR, check=True
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=tuple(SCENARIOS))
    parser.add_argument("--formation", required=True, choices=tuple(FORMATIONS))
    parser.add_argument(
        "--epoch", type=int, required=True, help="the scenario's seed k (1-based)"
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-slug", required=True)
    parser.add_argument("--provider", required=True)
    parser.add_argument("--key-env", required=True)
    parser.add_argument("--voicer-key-env", default="ANTHROPIC_API_KEY")
    parser.add_argument("--no-voicer", action="store_true")
    parser.add_argument("--thinking", default=None)
    parser.add_argument("--turn-timeout", type=float, default=1800.0)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--agent-roots-base", type=Path, required=True)
    parser.add_argument("--pi-cmd", required=True)
    parser.add_argument("--commit", default="unknown")
    parser.add_argument(
        "--mitigation",
        default=NONE,
        help="mitigation arm (merge_queue/mitigations/; default none = the formation itself)",
    )
    parser.add_argument("--print-info", action="store_true")
    # `--dry-run` is not an option (building the episode without driving it is `--print-info`): declared hidden only
    # so that it is refused.
    parser.add_argument(
        "--dry-run", dest="not_print_info", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--render-to",
        type=Path,
        default=None,
        help="with --print-info: write the run dir's config.json and every seat's AGENTS.md under this dir",
    )
    args = parser.parse_args(argv)
    if args.not_print_info:
        parser.error(
            "unknown option --dry-run (building the episode without driving it is --print-info)"
        )
    return args


@dataclass(frozen=True)
class EpisodePlan:
    """One episode as this driver builds it before anything runs (all a `--print-info` computes).

    Attributes:
        run_name: The run dir's name, `<formation cell>[__mit-<arm>]__<model slug>__e<world epoch>`.
        run_dir: `--runs-root` / `run_name`.
        world_epoch: The drive-side epoch that seeds the world (`Scenario.world_epoch` of the seed).
        cell: The cell the episode runs (a lead arm's is `<scenario>__none__comms__live_captain`).
        config: The episode's scenario config (`scenarios._context.build_cell`; the arm's when one is set).
        releasing: The world variant's RELEASING.md (`scenarios._world.releasing_md`; None keeps the fixture's).
        record: The `config.json` record the run dir banks (`_write_config`, `drive_episode(run_record=)`).
    """

    run_name: str
    run_dir: Path
    world_epoch: int
    cell: Cell
    config: ScenarioConfig
    releasing: str | None
    record: dict[str, Any]

    @property
    def seats(self) -> int:
        """The pi seats: the owners (or the steward), plus the team lead's fifth seat on a lead arm."""
        return len(self.config.agent_ids) + (self.config.captain_agents_md is not None)


def plan_episode(args: argparse.Namespace) -> EpisodePlan:
    """Build the episode `args` (this script's parsed argv) names: cell, config, world, run dir and record."""
    from merge_queue.scenarios._cells import Cell  # noqa: PLC0415
    from merge_queue.scenarios._context import build_cell  # noqa: PLC0415
    from merge_queue.scenarios._world import base_flags, releasing_md  # noqa: PLC0415

    scenario = SCENARIOS[args.scenario]
    world_epoch = scenario.world_epoch(args.epoch)
    cell = Cell(scenario=scenario.builder, **FORMATIONS[args.formation])  # type: ignore[arg-type]
    assert cell.name == cell_name(args.scenario, args.formation)
    # The run dir is the formation's cell + the arm's stamp (`run.run_dir_name`), whatever cell the arm
    # runs, and the WORLD epoch (the research run-dir grammar, so volunteer seeds join the paper's rows).
    run_name = f"{cell.name}{stamp(args.mitigation)}__{args.model_slug}__e{world_epoch}"
    flags = base_flags(cell.topology)
    config = build_cell(cell, world_epoch, flags=flags)
    if args.mitigation != NONE:
        from merge_queue.mitigations import ARMS, apply_to_episode  # noqa: PLC0415

        cell, config = apply_to_episode(
            args.mitigation,
            args.formation,
            cell,
            config,
            epoch=world_epoch,
        )
        flags = ARMS[args.mitigation].flags
    record_config: dict[str, Any] = {
        "eval": "merge_queue",
        "harness": "pi",
        "pi_version": "0.77.0",
        "scenario_sha256": hashlib.sha256(
            json.dumps(asdict(config), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "scenario": args.scenario,
        "formation": args.formation,
        "cell": cell.name,
        "model": args.model,
        "model_slug": args.model_slug,
        "provider": args.provider,
        "thinking": args.thinking,
        "voicer": not args.no_voicer,
        "epoch": args.epoch,
        "turn_timeout": args.turn_timeout,
        "commit": args.commit,
    }
    if args.mitigation != NONE:
        # The control arm's record is unchanged, so a run dir banked before mitigations still resumes.
        record_config["mitigation"] = args.mitigation
    # the world and the world variant it renders
    record_config["world"] = PAPER
    record_config["variant"] = flags.name
    if world_epoch != args.epoch:
        record_config["world_epoch"] = world_epoch
    return EpisodePlan(
        run_name=run_name,
        run_dir=args.runs_root.resolve() / run_name,
        world_epoch=world_epoch,
        cell=cell,
        config=config,
        releasing=releasing_md(flags),
        record=record_config,
    )


def render(plan: EpisodePlan, out_dir: Path) -> list[Path]:
    """Write what the episode's seats would be handed, without driving it; returns the files written.

    `out_dir/config.json` is the run dir's record, and `out_dir/<seat>/AGENTS.md` the auto-loaded brief of
    every seat that has one (`runtime.driver.seat_agents_md`: the owners' or the steward's, and a lead arm's
    team lead under its actor id), byte for byte what the drive writes into the seats' workspaces.
    """
    from merge_queue.runtime.driver import seat_agents_md  # noqa: PLC0415

    out_dir.mkdir(parents=True, exist_ok=True)
    written = [out_dir / "config.json"]
    written[0].write_text(json.dumps(plan.record, indent=2, sort_keys=True) + "\n")
    for seat, text in seat_agents_md(plan.config).items():
        path = out_dir / seat / "AGENTS.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.render_to is not None and not args.print_info:
        raise SystemExit(
            "--render-to writes the briefs --print-info plans; add --print-info"
        )
    # the runtime imports come first, so `--print-info` also proves the episode's runtime imports
    from merge_queue.runtime import resume  # noqa: PLC0415
    from merge_queue.runtime.driver import drive_episode  # noqa: PLC0415
    from merge_queue.runtime.process import validate_pi_runtime  # noqa: PLC0415
    from merge_queue.runtime.provider_screen import (  # noqa: PLC0415
        rejected_key_errors,
    )
    from merge_queue.runtime.stall_watchdog import (  # noqa: PLC0415
        DEFAULT_STALL_MINUTES,
        KICK_DIR_NAME,
        KickStore,
        StallWatch,
        effective_stall_seconds,
    )
    from merge_queue.runtime.voicer import SonnetVoicer  # noqa: PLC0415

    plan = plan_episode(args)
    if args.print_info:
        print(
            json.dumps(
                {"run_dir": str(plan.run_dir), "seats": plan.seats, **plan.record}
            )
        )
        if args.render_to is not None:
            render(plan, args.render_to)
        return 0
    run_name, run_dir, record_config = plan.run_name, plan.run_dir, plan.record
    validate_existing_config(run_dir, record_config)
    if (run_dir / "DONE.json").is_file() or resume.score_existing_episode(
        run_dir
    ) is True:
        _write_config(run_dir, record_config)
        print(f"[{run_name}] SKIP (done)", flush=True)
        return 2
    validate_pi_runtime(pi_bin=args.pi_cmd)
    ensure_ci_python()
    api_key = os.environ.get(args.key_env, "").strip()
    if not api_key:
        raise SystemExit(f"{args.key_env} is empty/unset")
    voicer_key = os.environ.get(args.voicer_key_env, "").strip()
    if not args.no_voicer and not voicer_key:
        raise SystemExit(
            f"{args.voicer_key_env} is empty/unset (the Sonnet voicer needs an Anthropic key; "
            "pass --voicer-key-env or --no-voicer)"
        )
    args.runs_root.mkdir(parents=True, exist_ok=True)
    args.agent_roots_base.mkdir(parents=True, exist_ok=True)
    store = KickStore(args.runs_root.resolve() / KICK_DIR_NAME)
    stall_seconds = effective_stall_seconds(
        stall_minutes=DEFAULT_STALL_MINUTES, turn_timeout=args.turn_timeout
    )
    for attempt in range(1, args.attempts + 1):
        voicer = (
            None
            if args.no_voicer
            else SonnetVoicer(
                api_key=voicer_key,
                log_path=run_dir / "voicer.jsonl",
                topology=plan.cell.topology,
            )
        )
        agent_root = resume.agent_root(args.agent_roots_base.resolve(), run_name)
        try:
            with StallWatch(
                run_name=run_name,
                run_dir=run_dir,
                agent_root=agent_root,
                store=store,
                stall_seconds=stall_seconds,
            ) as watch:
                result = drive_episode(
                    run_dir=run_dir,
                    config=plan.config,
                    api_key=api_key,
                    model=args.model,
                    pi_bin=args.pi_cmd,
                    provider=args.provider,
                    api_key_var=API_KEY_VAR.get(args.provider, "API_KEY"),
                    thinking=args.thinking,
                    turn_timeout=args.turn_timeout,
                    voicer=voicer,
                    agent_root=agent_root,
                    wake_seed=resume.wake_seed(plan.cell.scenario, plan.world_epoch),
                    empty_retries=resume.EMPTY_RETRIES,
                    max_consecutive_timeouts=resume.MAX_CONSECUTIVE_TIMEOUTS,
                    steal_stale_lease=True,
                    defer_voicer=True,
                    run_record=record_config,
                    releasing_md=plan.releasing,
                )
        except KeyboardInterrupt:
            _record_interrupted(run_dir, record_config, attempt)
            raise
        except Exception as exc:  # noqa: BLE001 — a hard driver failure: try again
            print(f"[{run_name}] attempt {attempt}: driver error {exc!r}", flush=True)
            continue
        if not watch.kicked:
            store.clear(run_name)
        failures = resume.structural_failures(result)
        record = {
            "scenario": result.scenario,
            "model": result.model,
            "run_dir": str(run_dir),
            "smoke_variant": None,
            "infrastructure_pass": not failures,
            "failures": failures,
            "events_sha256": result.events_sha256,
            "world": result.world,
            "quarantined_attempts": quarantined_attempts(run_dir),
        }
        target = "DONE.json" if not failures else "INCOMPLETE.json"
        (run_dir / target).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n"
        )
        _write_config(run_dir, record_config)
        if not failures:
            (run_dir / "INCOMPLETE.json").unlink(missing_ok=True)
            world: dict[str, Any] = dict(result.world)
            print(
                f"[{run_name}] DONE attempt {attempt}: release {world.get('release_value')} / "
                f"oracle {world.get('oracle_value')}, merged {world.get('merged_prs')}, "
                f"wall {result.wall_clock_seconds:.0f}s",
                flush=True,
            )
            return 0
        print(f"[{run_name}] attempt {attempt}: {'; '.join(failures)}", flush=True)
        rejected = rejected_key_errors(
            run_dir, cast(dict[str, Any], result.session_counts)
        )
        if rejected:
            print(
                f"[{run_name}] FATAL: target key rejected ({rejected} authentication/permission error(s) in the "
                "seats' sessions); not re-driving. Fix the key and rerun the same command.",
                flush=True,
            )
            return KEY_REJECTED
    return 1


def quarantined_attempts(run_dir: Path) -> int:
    """How many earlier attempts of this episode sit quarantined in its run dir (`.attempt<N>.failed/`)."""
    if not run_dir.is_dir():
        return 0
    return sum(
        1
        for path in run_dir.iterdir()
        if path.is_dir()
        and path.name.startswith(".attempt")
        and path.name.endswith(".failed")
    )


def _record_interrupted(run_dir: Path, record: dict[str, Any], attempt: int) -> None:
    """`INCOMPLETE.json` for an attempt a signal stopped (best effort: the process is being torn down)."""
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "INCOMPLETE.json").write_text(
            json.dumps(
                {
                    "run_dir": str(run_dir),
                    "infrastructure_pass": False,
                    "failures": [f"attempt {attempt}: {INTERRUPTED}"],
                    "interrupted": True,
                    "quarantined_attempts": quarantined_attempts(run_dir),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        _write_config(run_dir, record)
        print(f"[{run_dir.name}] attempt {attempt}: {INTERRUPTED}", flush=True)
    except OSError as exc:
        print(
            f"[{run_dir.name}] could not record the interruption: {exc!r}", flush=True
        )


def validate_existing_config(run_dir: Path, record: dict[str, Any]) -> None:
    """Avoid silently reusing a completed episode from a different instrument."""
    path = run_dir / "config.json"
    if not path.is_file():
        if any((run_dir / name).is_file() for name in ("DONE.json", "episode.json")):
            raise SystemExit(
                f"{run_dir}: existing episode has no configuration provenance; choose a new --runs-root"
            )
        return
    saved = json.loads(path.read_text())
    if not isinstance(saved, dict):
        raise SystemExit(f"{path}: expected a configuration object")
    changed = configuration_drift(cast(dict[str, Any], saved), record)
    if changed:
        raise SystemExit(
            f"{run_dir}: existing episode differs in {', '.join(changed)}; choose a new --runs-root"
        )


def _write_config(run_dir: Path, record: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "config.json"
    if not path.exists():
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
