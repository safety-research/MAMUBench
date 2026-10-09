"""The lockstep episode runner shared by the `api_key` and `clinic` evals: N `pi --mode rpc` seats, one world.

One episode = one `EpisodeBridge` (the env's own deterministic world + router, seeded exactly like the
simulated harness's cells) + one `BridgeServer` (localhost HTTP the seats' typed-tool extension talks to)
+ N persistent pi processes round-robined in LOCKSTEP rounds. The wake discipline mirrors the simulated
harness's resume loop: the seat the router wants woken (a fired beat) goes first; a seat with nothing staged whose
last turn was pure text is skipped (the sim refuses that bare resume); a fully idle round advances the
world the env's own way; the episode ends when the world reports it over and the router's end guard is
clean.

Resumable at episode granularity: an episode with a `DONE.json` is skipped on re-run; a partial episode
is wiped and rerun. Provider storms (529s) KILL the episode — no `DONE.json` — so the next invocation
simply reruns it instead of banking a do-nothing night as a clean result.

The provider key is written into each seat's pi auth file, never the process environment, so a seat
that runs `env` in its own shell never sees it.
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _jobs import read_jobs_file
from _mitigations import NONE, stamp
from _providers import (
    PI_THINKING_LEVELS,
    PROVIDERS,
    THINKING_BY_PROVIDER,
    path_safe_model,
    provider_for,
    resolve_api_key,
)
from _resume import configuration_drift

from _harness import pi_rpc
from _harness.bridge import EnvCell, EpisodeBridge
from _harness.credentials import remove_pi_auth_files
from _harness.server import BridgeServer

HARNESS_DIR = Path(__file__).resolve().parent
FAKE_PI = HARNESS_DIR / "fake_pi.py"

#: Wall-clock pause after a storm-aborted episode before the next epoch is attempted.
STORM_COOLDOWN_S = 180.0


class ProviderStormAbort(RuntimeError):
    """A seat exhausted its provider-error streak: the episode is killed for a clean rerun.

    Provider outages are an accepted operational fact; the correct handling is to KILL the episode and
    let the resumable relaunch rerun it, not to ride the storm out or burn the surviving seats' calls
    on an episode already excluded from clean pools. The aborted episode keeps its world artifacts for
    forensics but gets NO `DONE.json`, so the next invocation wipes and reruns it.
    """


@dataclass(frozen=True)
class RunConfig:
    """Everything one invocation pins for every episode it runs (recorded in each run's `config.json`)."""

    eval: str
    scenario: str
    formation: str
    model: str
    provider: str
    runs_root: Path
    key_env: str | None = None
    fake_pi: bool = False
    fake_scripts: Path | None = None
    rounds_max: int | None = None
    turn_timeout: float | None = None
    turn_wait_budget: int | None = None
    round_wait_budget: int | None = None
    idle_stride: int = 10
    wrapup_grants: int = 2
    error_streak_max: int = 4
    error_backoff: float = 30.0
    pack_workspaces: bool = False
    #: `pi` (this runner: real pi seats in lockstep) or `sim` (`_harness/sim.py`: the simulated harness,
    #: the paper's instrument). One runs root holds one harness.
    harness: str = "pi"
    #: sim only: bind every role to inspect's `mockllm` wait-loop stand-in (offline plumbing).
    fake_model: bool = False
    #: The mitigation arm (`<env>/mitigations.py`); `none` = the formation itself. Any other arm is
    #: recorded in `config.json` and stamps the run dir (`_mitigations.stamp`).
    mitigation: str = NONE
    #: pi only: the seats' pi thinking level (`--thinking`; default `_providers.THINKING_BY_PROVIDER`), passed to
    #: every seat and recorded. `None` on the simulated harness, which plays the paper's reasoning setting.
    thinking: str | None = None


def add_common_args(
    parser: argparse.ArgumentParser,
    *,
    formations: tuple[str, ...],
    mitigations: tuple[str, ...] = (NONE,),
    default_formations: tuple[str, ...] | None = None,
) -> None:
    """The CLI surface both evals share (scenario selection is the eval's own).

    `--formation`, `--episodes` and `--epoch0` parse to `None` when not given; `validate_args` fills their
    defaults (every formation, one epoch from epoch 1) after checking they were not combined with
    `--jobs-file`.

    Args:
        parser: The eval's parser.
        formations: The formations the CLI accepts (the eval validates the ones it does not run yet).
        mitigations: The eval's mitigation arms (`<env>/mitigations.py` `MITIGATIONS`).
        default_formations: The formations run when `--formation` is not given (default: `formations`).
    """
    defaults = list(
        default_formations if default_formations is not None else formations
    )
    parser.set_defaults(default_formations=defaults)
    parser.add_argument(
        "--formation",
        nargs="+",
        choices=formations,
        default=None,
        help=f"default: {' '.join(defaults)}",
    )
    parser.add_argument("--episodes", type=int, default=None, help="default: 1")
    parser.add_argument(
        "--epoch0",
        type=int,
        default=None,
        help="first epoch (1-based, seeds the world; default 1)",
    )
    # `--epochs` is not an option (episodes per cell is `--episodes`): declared hidden only so that it is refused,
    # and so that `--epoch N` stays ambiguous instead of argparse expanding it to `--epoch0 N`.
    parser.add_argument(
        "--epochs", dest="not_episodes", nargs="?", const="", help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--mitigation",
        choices=mitigations,
        default=NONE,
        help="mitigation arm (default none = the formation itself; see --list-mitigations); recorded, "
        "and stamped on the run dir (`__mit-<name>`)",
    )
    parser.add_argument(
        "--list-mitigations",
        action="store_true",
        help="print the mitigation registry and exit",
    )
    parser.add_argument(
        "--jobs-file",
        type=Path,
        default=None,
        help="a CSV of explicit episodes (scenario,formation,epoch[,mitigation]; see eval/_jobs.py) instead "
        "of the scenario x formation x epoch matrix; exclusive with the scenario selection, --formation, "
        "--episodes and --epoch0",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("MODEL", "claude-sonnet-5"),
        help="pi model id: claude-* (anthropic), gpt-*/o* (openai), <vendor>/<model> (openrouter)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=PROVIDERS,
        help="pi provider (default: inferred from the model id)",
    )
    parser.add_argument(
        "--key-env",
        default=None,
        help="env var holding the provider key (default: ANTHROPIC_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--api-key", default=None, help="the key itself (wins over --key-env)"
    )
    parser.add_argument(
        "--thinking",
        choices=PI_THINKING_LEVELS,
        default=None,
        help="(pi) the seats' pi thinking level (default per provider: "
        + ", ".join(f"{p} {level}" for p, level in THINKING_BY_PROVIDER.items())
        + "); recorded",
    )
    parser.add_argument(
        "--runs-root", type=Path, default=None, help="default: <eval>/runs"
    )
    parser.add_argument(
        "--rounds-max",
        type=int,
        default=None,
        help="lockstep rounds per episode (default per env)",
    )
    parser.add_argument(
        "--turn-timeout",
        type=float,
        default=None,
        help="seconds per pi turn (default per env)",
    )
    parser.add_argument(
        "--turn-wait-budget",
        type=int,
        default=None,
        help="cumulative wait-tool sim-minutes one pi turn may advance (<=0 = uncapped; default per env)",
    )
    parser.add_argument(
        "--round-wait-budget",
        type=int,
        default=None,
        help="cumulative wait-tool sim-minutes ALL seats may advance per lockstep round (<=0 = uncapped; default per env cell)",
    )
    parser.add_argument(
        "--idle-stride",
        type=int,
        default=10,
        help="sim-minutes a fully idle round advances",
    )
    parser.add_argument(
        "--wrapup-grants",
        type=int,
        default=2,
        help="post-horizon delivery turns per seat",
    )
    parser.add_argument(
        "--error-streak-max",
        type=int,
        default=4,
        help="provider-error turns before the episode is killed",
    )
    parser.add_argument(
        "--error-backoff",
        type=float,
        default=30.0,
        help="seconds slept after a provider-error turn (doubles)",
    )
    parser.add_argument(
        "--pack-workspaces",
        action="store_true",
        help="after an episode banks, tar its seat trees (agents/, agent_dir/, fsroot/) into workspaces.tar.gz "
        "(the reports read only world/ + DONE.json + config.json; on a Modal Volume the file count is the budget)",
    )
    parser.add_argument(
        "--fake-pi",
        action="store_true",
        help="drive _harness/fake_pi.py instead of real pi (offline)",
    )
    parser.add_argument(
        "--fake-scripts",
        type=Path,
        default=None,
        help="dir of per-seat FakePi scripts (<seat>.json)",
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
        "--list", action="store_true", help="print the scenario registry and exit"
    )
    harness = parser.add_argument_group(
        "harness",
        "`sim` (default) = the research code's simulated harness, the instrument behind the paper's "
        "api_key and clinic numbers (inspect_ai scripted driver over the same worlds; Anthropic, OpenAI "
        "and OpenRouter targets); every cell plays the settings behind its paper number (scheduler, step "
        "budget, time limits, the target's reasoning setting), with no override. `pi` = real pi 0.77.0 "
        "seats in lockstep (an alternative instrument, not the paper's; `--fake-pi` implies it). Never pool "
        "the two in one runs root.",
    )
    harness.add_argument(
        "--harness",
        choices=("pi", "sim"),
        default=None,
        help="default: sim (pi when --fake-pi / --fake-scripts is given)",
    )
    harness.add_argument(
        "--fake-model",
        action="store_true",
        help="(sim) bind every role to inspect's mockllm wait-loop stand-in (offline plumbing)",
    )


def validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.harness is None:
        # The paper's instrument by default; the pi harness's own stand-ins select the pi harness.
        args.harness = "pi" if args.fake_pi or args.fake_scripts is not None else "sim"
    if args.fake_scripts is not None and not args.fake_pi:
        parser.error("--fake-scripts needs --fake-pi")
    if args.not_episodes is not None:
        parser.error("unknown option --epochs (episodes per cell is --episodes)")
    if args.not_print_info:
        parser.error(
            "unknown option --dry-run (printing the job matrix without running it is --print-info)"
        )
    if args.harness == "sim" and args.fake_pi:
        parser.error(
            "--fake-pi is the pi harness's stand-in; the simulated harness's is --fake-model"
        )
    if args.harness != "sim" and args.fake_model:
        parser.error("--fake-model needs --harness sim")
    if args.harness == "sim" and args.thinking is not None:
        parser.error(
            "--thinking is the pi harness's; the simulated harness plays the paper's reasoning setting"
        )
    if args.jobs_file is not None:
        given = [
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
        args.formation = list(args.default_formations)
    args.episodes = 1 if args.episodes is None else args.episodes
    args.epoch0 = 1 if args.epoch0 is None else args.epoch0
    if args.episodes < 1 or args.epoch0 < 1:
        parser.error("--episodes and --epoch0 are 1-based positive integers")
    # Resolve the provider at parse time so an uninferable model id fails `--print-info` too.
    provider_for(str(args.model), args.provider)


def prepare(config: RunConfig, api_key: str | None = None) -> str:
    """Validate the pi runtime (or point at the fake) and return the provider key to hand to seats."""
    config.runs_root.mkdir(parents=True, exist_ok=True)
    if config.harness == "sim":
        # No pi runtime is involved. This is the TARGET's key (its provider's); the house auditor and
        # judge keep their Anthropic key (`sim.resolve_keys`).
        if config.fake_model:
            return "fake-not-used"
        return resolve_api_key(config.provider, config.key_env, api_key)
    if config.fake_pi:
        os.environ["EVAL_PI_CMD"] = f"{sys.executable} {FAKE_PI}"
        return "fake-not-used"
    pi_rpc.validate_runtime()
    return resolve_api_key(config.provider, config.key_env, api_key)


def config_from_args(
    args: argparse.Namespace,
    *,
    eval_name: str,
    scenario: str,
    formation: str,
    default_runs_root: Path,
    mitigation: str | None = None,
) -> RunConfig:
    """One `RunConfig` per (scenario, formation, mitigation) of an invocation, with every path made absolute.

    Absolute paths matter: pi resolves HOME/cwd/--session-dir against its own cwd otherwise, and a
    relative FakePi script dir would resolve against each seat's workspace (every seat then silently
    runs the empty script). `mitigation` defaults to the invocation's `--mitigation` (a jobs file's row
    may name its own).
    """
    model = str(args.model)
    provider = provider_for(model, args.provider)
    harness = str(args.harness or ("pi" if args.fake_pi else "sim"))
    return RunConfig(
        eval=eval_name,
        scenario=scenario,
        formation=formation,
        model=model,
        provider=provider,
        runs_root=(args.runs_root or default_runs_root).resolve(),
        key_env=args.key_env,
        fake_pi=bool(args.fake_pi),
        fake_scripts=args.fake_scripts.resolve() if args.fake_scripts else None,
        rounds_max=args.rounds_max,
        turn_timeout=args.turn_timeout,
        turn_wait_budget=args.turn_wait_budget,
        round_wait_budget=args.round_wait_budget,
        idle_stride=args.idle_stride,
        wrapup_grants=args.wrapup_grants,
        error_streak_max=args.error_streak_max,
        error_backoff=args.error_backoff,
        pack_workspaces=bool(args.pack_workspaces),
        harness=harness,
        fake_model=bool(args.fake_model),
        mitigation=(
            mitigation
            if mitigation is not None
            else str(getattr(args, "mitigation", None) or NONE)
        ),
        thinking=(
            None
            if harness == "sim"
            else str(getattr(args, "thinking", None) or THINKING_BY_PROVIDER[provider])
        ),
    )


#: One planned episode: the run config of its (scenario, formation, mitigation) and its epoch.
Job = tuple[RunConfig, int]


def plan_jobs(
    args: argparse.Namespace,
    *,
    eval_name: str,
    default_runs_root: Path,
    select: Callable[[], list[str]],
    canonical: Callable[[str], str],
    check: Callable[[str, str], object],
) -> list[Job]:
    """Every episode of an invocation: the scenario x formation x epoch matrix, or `--jobs-file`'s list.

    One `RunConfig` per (scenario, formation, mitigation), shared by its episodes; matrix order is
    scenario, formation, epoch (the order the runners always used), a jobs file keeps its own order.

    Args:
        args: The parsed CLI (`add_common_args` + `validate_args`).
        eval_name: The eval.
        default_runs_root: `<eval>/runs`.
        select: The matrix's scenario ids (the eval's own selection flags); not called with a jobs file.
        canonical: A jobs-file scenario id -> the registry's id (exits on an unknown one).
        check: `(formation, mitigation)` -> raises `ValueError` when the eval cannot run the pair
            (a formation it does not implement, an arm that does not apply to it or to the harness).

    Raises:
        ValueError: A bad jobs file or a pair `check` refuses (the runners exit with the message).
    """
    if args.jobs_file is not None:
        cells = [
            (canonical(job.scenario), job.formation, job.mitigation, job.epoch)
            for job in read_jobs_file(
                args.jobs_file, default_mitigation=args.mitigation
            )
        ]
    else:
        epochs = range(args.epoch0, args.epoch0 + args.episodes)
        cells = [
            (scenario, formation, str(args.mitigation), epoch)
            for scenario in select()
            for formation in args.formation
            for epoch in epochs
        ]
    configs: dict[tuple[str, str, str], RunConfig] = {}
    jobs: list[Job] = []
    for scenario, formation, mitigation, epoch in cells:
        key = (scenario, formation, mitigation)
        if key not in configs:
            check(formation, mitigation)
            configs[key] = config_from_args(
                args,
                eval_name=eval_name,
                scenario=scenario,
                formation=formation,
                default_runs_root=default_runs_root,
                mitigation=mitigation,
            )
        jobs.append((configs[key], epoch))
    return jobs


def job_line(config: RunConfig, epoch: int, width: int) -> str:
    """One `--print-info` line: scenario, formation, epoch (+ the arm when it is not the control)."""
    arm = "" if config.mitigation == NONE else f" mitigation={config.mitigation}"
    return f"  {config.scenario:{width}} {config.formation:12} e{epoch}{arm}"


@functools.lru_cache(maxsize=None)
def git_commit() -> str:
    """The launching commit: `EVAL_GIT_SHA` when set (containers carry no `.git`), else `git rev-parse`."""
    if override := os.environ.get("EVAL_GIT_SHA", "").strip():
        return override
    try:
        out = subprocess.run(
            ["git", "-C", str(HARNESS_DIR), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def _agent_env(
    *, home: Path, run_dir: Path, server_url: str, seat_token: str
) -> dict[str, str]:
    """The minimal environment one pi seat sees.

    The vendor key is deliberately absent: it lives in pi's auth file (`pi_rpc.write_auth_file`), not the
    process env. The agent dir is NOT overridden (`PI_CODING_AGENT_DIR` relocates the auth lookup too):
    each seat gets the default `~/.pi/agent/` materialized in its own home.
    """
    env = {
        "LABCTL_SERVER": server_url,
        "LABCTL_TOKEN": seat_token,
        "PI_OFFLINE": "1",
        "PI_TELEMETRY": "0",
        "GIT_CEILING_DIRECTORIES": str(run_dir),
        "HOME": str(home),
        "PATH": os.environ.get("PATH", ""),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
    }
    for name in (
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    ):
        if value := os.environ.get(name):
            env[name] = value
    return env


def _seat_argv(
    config: RunConfig, bridge: EpisodeBridge, seat: str, seat_dir: Path
) -> list[str]:
    """One seat's full pi argv: base command + RPC flags + the cell's own console prompt, no native tools.

    Both envs run their console framing: the spec's own per-seat prompt replaces pi's and pi's native
    tools are disabled, so the typed world tools are the WHOLE surface (the same no-real-shell line the
    paper's runs measured).
    """
    argv = [
        *pi_rpc.pi_argv(),
        *pi_rpc.rpc_argv(
            provider=config.provider,
            model=config.model,
            session_dir=seat_dir / "sessions",
        ),
    ]
    if config.thinking is not None:
        argv += ["--thinking", config.thinking]
    system_prompt = bridge.seat_system_prompt(seat)
    if system_prompt is not None:
        argv += ["--system-prompt", system_prompt, "--no-builtin-tools"]
    return argv


def _config_record(
    config: RunConfig,
    cell: EnvCell,
    epoch: int,
    rounds_max: int,
    turn_timeout: float,
    wait_budget: int,
    round_wait_budget: int | None = None,
) -> dict[str, Any]:
    """The episode's full recorded configuration (written to `config.json`; compared on a DONE-skip).

    A mitigation arm adds its `mitigation` key; the control arm's record is unchanged, so a run dir
    banked before mitigations existed still DONE-skips.
    """
    record: dict[str, Any] = {
        "eval": config.eval,
        "scenario": config.scenario,
        "formation": config.formation,
        "cell": cell.spec.name,
        "framing": cell.framing,
        "harness": "pi",
        "fake_pi": config.fake_pi,
        "model": config.model,
        "provider": config.provider,
        "thinking": config.thinking,
        "epoch": epoch,
        "pi_version": pi_rpc.pi_version() if not config.fake_pi else "fake",
        "commit": git_commit(),
        "turn_timeout": turn_timeout,
        "rounds_max": rounds_max,
        "turn_wait_budget": wait_budget,
        "round_wait_budget": round_wait_budget,
        "idle_stride": config.idle_stride,
        "wrapup_grants": config.wrapup_grants,
        "error_streak_max": config.error_streak_max,
        "error_backoff": config.error_backoff,
    }
    if config.mitigation != NONE:
        record["mitigation"] = config.mitigation
    return record


def run_dir_for(config: RunConfig, cell: EnvCell, epoch: int) -> Path:
    """The run dir `<cell>[__mit-<arm>]__<model>__e<N>` (+ `__fakepi`).

    The cell name encodes scenario + formation, the stamp a mitigation arm (none for the control arm,
    so every earlier run dir keeps its name); the tag is the one harness-level deviation that must
    never collide with a real run on one `DONE.json`.
    """
    tag = "__fakepi" if config.fake_pi else ""
    return (
        config.runs_root
        / f"{cell.spec.name}{stamp(config.mitigation)}__{path_safe_model(config.model)}__e{epoch}{tag}"
    )


def _given_or[T](value: T | None, default: T) -> T:
    """A CLI override, or the cell's default when it was not given."""
    return default if value is None else value


def run_episode(
    config: RunConfig, cell: EnvCell, epoch: int, api_key: str
) -> dict[str, Any]:
    """Run (or skip) one episode; returns the DONE record."""
    rounds_max = _given_or(config.rounds_max, cell.rounds_max_default)
    turn_timeout = _given_or(config.turn_timeout, cell.turn_timeout_default)
    wait_budget = _given_or(config.turn_wait_budget, cell.turn_wait_budget_default)
    round_budget = _given_or(config.round_wait_budget, cell.round_wait_budget_default)
    if round_budget is not None and round_budget <= 0:
        round_budget = None
    run_dir = run_dir_for(config, cell, epoch)
    done_path = run_dir / "DONE.json"
    expected = _config_record(
        config, cell, epoch, rounds_max, turn_timeout, wait_budget, round_budget
    )
    if done_path.exists():
        prior = json.loads((run_dir / "world" / "config.json").read_text())
        drift = configuration_drift(prior, expected)
        if drift:
            raise SystemExit(
                f"{run_dir} was produced by a different configuration ({drift}); use a fresh --runs-root"
            )
        record: dict[str, Any] = json.loads(done_path.read_text())
        record["skipped"] = True
        return record
    if run_dir.exists():
        shutil.rmtree(run_dir)
    world_dir = run_dir / "world"
    world_dir.mkdir(parents=True)

    bridge = EpisodeBridge(
        cell,
        ledger_path=world_dir / "ledger.jsonl",
        turn_wait_budget=(wait_budget if wait_budget > 0 else None),
        round_wait_budget=round_budget,
    )
    server = BridgeServer(bridge)
    server.start()
    # Any norms files the world serves (policy docs) are written as real bytes under the run dir, so the
    # exact text a seat could read is inspectable even though no seat has file tools in the console cells.
    for raw_path, text in bridge.norms_files().items():
        target = run_dir / "fsroot" / raw_path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    # One shared agent dir per episode: the extension + the generated tool manifest.
    agent_dir = run_dir / "agent_dir"
    shutil.copytree(HARNESS_DIR / "agent_dir", agent_dir)
    (agent_dir / "tools.json").write_text(json.dumps(bridge.tools_manifest(), indent=2))

    procs: dict[str, pi_rpc.PiHandle] = {}
    crashed: set[str] = set()
    started_wall = time.monotonic()
    rounds = 0
    error_turns = 0
    ended = "rounds cap reached"
    try:
        for seat in bridge.ids:
            seat_dir = run_dir / "agents" / seat
            home = seat_dir / "home"
            workspace = seat_dir / "ws"
            for directory in (home, workspace, seat_dir / "sessions"):
                directory.mkdir(parents=True, exist_ok=True)
            env = _agent_env(
                home=home,
                run_dir=run_dir,
                server_url=server.base_url,
                seat_token=server.token_for(seat),
            )
            if config.fake_pi:
                script = (
                    config.fake_scripts / f"{seat}.json"
                    if config.fake_scripts
                    else None
                )
                if script is not None and script.exists():
                    env["FAKE_PI_SCRIPT"] = str(script)
            else:
                seat_agent_dir = home / ".pi" / "agent"
                shutil.copytree(agent_dir, seat_agent_dir)
                pi_rpc.write_auth_file(
                    seat_agent_dir, provider=config.provider, api_key=api_key
                )
            procs[seat] = pi_rpc.spawn_agent(
                _seat_argv(config, bridge, seat, seat_dir),
                cwd=workspace,
                env=env,
                stderr_path=seat_dir / "stderr.log",
            )

        wrapup_used: dict[str, int] = {i: 0 for i in bridge.ids}
        error_streak: dict[str, int] = {i: 0 for i in bridge.ids}
        while rounds < rounds_max:
            bridge.begin_round()
            over = bridge.is_over()
            if over and bridge.may_end() is None:
                ended = "world horizon reached"
                break
            if not over and crashed and bridge.past_window():
                # A crashed seat's deliveries can never render, so is_over() may stay false forever:
                # treat the episode as over — the bounded wrap-up drain below serves remaining
                # deliveries, then the no-progress break ends the episode.
                over = True
            priority = bridge.wake_priority()
            order = list(bridge.ids)
            if priority in order:
                order.remove(priority)
                order.insert(0, priority)
            any_turn = False
            any_error = False
            for seat in order:
                if seat in crashed or bridge.withheld(seat) is not None:
                    continue
                first_wake = not bridge.nstate["started"][seat]
                if over:
                    # Post-horizon: only drain deliveries (queued mail, a debrief), bounded.
                    if (
                        not bridge.pending_for(seat)
                        or wrapup_used[seat] >= config.wrapup_grants
                    ):
                        continue
                    wrapup_used[seat] += 1
                elif not (
                    first_wake or bridge.pending_for(seat) or bridge.seat_active(seat)
                ):
                    continue  # the sim's bare-resume refusal: text-idle with nothing staged
                delivery = bridge.begin_turn(seat)
                try:
                    messages = pi_rpc.run_turn(
                        procs[seat], delivery.prompt, timeout=turn_timeout
                    )
                except (TimeoutError, RuntimeError) as exc:
                    bridge.end_turn(delivery, rendered=False)
                    crashed.add(seat)
                    (run_dir / "agents" / seat / "crash.log").write_text(
                        f"{type(exc).__name__}: {exc}\n"
                    )
                    print(f"[seat {seat}] crashed: {exc}", flush=True)
                    continue
                error = pi_rpc.turn_error(messages)
                if error is not None:
                    # A provider-failure turn (pi retried internally, then gave up WITHOUT raising):
                    # bounced — deliveries requeue, nothing rendered — then back off. Counting it as a
                    # rendered empty turn would convert an API outage into a "clean" do-nothing episode.
                    bridge.end_turn(delivery, rendered=False)
                    error_turns += 1
                    error_streak[seat] += 1
                    any_error = True
                    print(
                        f"[seat {seat}] model call errored (streak {error_streak[seat]}): {error[:140]}",
                        flush=True,
                    )
                    if error_streak[seat] >= config.error_streak_max:
                        (run_dir / "agents" / seat / "crash.log").write_text(
                            f"provider errors x{error_streak[seat]}: {error}\n"
                        )
                        raise ProviderStormAbort(
                            f"seat {seat}: {error_streak[seat]} consecutive provider errors"
                        )
                    time.sleep(config.error_backoff * (2 ** (error_streak[seat] - 1)))
                    continue
                error_streak[seat] = 0
                bridge.end_turn(
                    delivery,
                    rendered=True,
                    est_tokens=pi_rpc.turn_est_tokens(messages),
                    had_tool_calls=pi_rpc.had_tool_calls(messages),
                )
                any_turn = True
            rounds += 1
            if crashed >= set(bridge.ids):
                ended = "all seats crashed"
                break
            if over and not any_turn:
                ended = f"world horizon reached (wrap-up exhausted: {bridge.may_end() or 'pending deliveries unservable'})"
                break
            if not any_turn and not bridge.is_over():
                if any_error:
                    continue  # an outage round: hold the world clock, retry after the backoff
                bridge.idle_nudge(config.idle_stride)
    finally:
        # Best-effort artifact writes even when unwinding (Ctrl-C, a bridge bug): each one is durable on
        # its own, and no artifact failure may mask the original exception.
        unwinding = sys.exc_info()[0] is not None
        try:
            pi_rpc.close_agents(list(procs.values()))
        finally:
            remove_pi_auth_files(
                run_dir / "agents" / seat / "home" / ".pi" / "agent"
                for seat in bridge.ids
            )
            server.stop()
        try:
            (world_dir / "notices.log").write_text(
                "\n".join(bridge.drain_notices()) + "\n"
            )
            (world_dir / "summary.json").write_text(
                json.dumps(bridge.finalize(), indent=2)
            )
            (world_dir / "config.json").write_text(json.dumps(expected, indent=2))
        except Exception:  # noqa: BLE001 — never mask the original exception with an artifact failure
            if not unwinding:
                raise

    record = {
        "ended": ended,
        "rounds": rounds,
        "error_turns": error_turns,
        "crashed": sorted(crashed),
        "counts": bridge.counts(),
        "sim_clock": bridge.clock(),
        "wall_s": round(time.monotonic() - started_wall, 1),
        "skipped": False,
    }
    done_path.write_text(json.dumps(record, indent=2))
    if config.pack_workspaces:
        pack_workspaces(run_dir)
    return record


#: The bulky per-seat trees a run dir carries (pi homes, sessions, the served norms files).
WORKSPACE_DIRS: tuple[str, ...] = ("agents", "agent_dir", "fsroot")


def pack_workspaces(run_dir: Path) -> Path | None:
    """Tar the seat trees of a banked run dir into `workspaces.tar.gz` and remove them.

    Everything the reports read (`world/`, `DONE.json`, `config.json`) stays as files; the pi sessions
    and homes travel as one archive. Idempotent: a run dir already packed is left alone.
    """
    bulky = [run_dir / name for name in WORKSPACE_DIRS if (run_dir / name).is_dir()]
    if not bulky:
        return None
    archive = run_dir / "workspaces.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in bulky:
            tar.add(path, arcname=path.name)
    for path in bulky:
        shutil.rmtree(path, ignore_errors=True)
    return archive


def run_epochs(
    config: RunConfig,
    build_cell: Callable[[int], EnvCell],
    epochs: Iterable[int],
    api_key: str,
) -> int:
    """Run every epoch of one (scenario, formation) in sequence; returns the number storm-aborted."""
    aborted = 0
    label = f"{config.eval} {config.scenario} {config.formation}" + (
        "" if config.mitigation == NONE else f" [{config.mitigation}]"
    )
    for epoch in epochs:
        try:
            record = run_episode(config, build_cell(epoch), epoch, api_key)
        except ProviderStormAbort as exc:
            aborted += 1
            print(
                f"[{label} e{epoch}] STORM-ABORTED ({exc}) — no DONE.json written; rerun this command to redo it",
                flush=True,
            )
            time.sleep(0 if config.fake_pi else STORM_COOLDOWN_S)
            continue
        status = "SKIP" if record.get("skipped") else record["ended"]
        print(
            f"[{label} e{epoch}] {status} rounds={record['rounds']} clock={record['sim_clock']} "
            f"counts={record['counts']} wall={record['wall_s']}s",
            flush=True,
        )
    return aborted
