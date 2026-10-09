"""Run the MAMUBench personal_assistant eval: scenario x formation x epoch, real pi seats, one world.

One episode = the environment's own episode (`food_run.run_episode` / `trip_run.run_episode`): the
scenario's authored world behind a bearer-authenticated hub, one persistent `pi --mode rpc`
process per seat, the decision-free push relay (concurrent openings, pushed DMs, commit or
quiescence, the 21-minute window), and a completion sidecar with the world + scored metrics.
Formations: `coordinator` (one pooled seat) vs `team` (one seat per principal, peer DMs), and
`team_silent` (team with the DM channel removed); all three run on all 25 scenarios.

Resumable per (scenario, formation, epoch): a sidecar that exists is validated against this
invocation (cell, epoch, model, thinking, git revision) and skipped; a wave's `wave_config.json`
pins the run to one revision, model and tool manifest, exactly as the paper's Modal waves did.
An episode that ends operationally (`ops_timeout`, a transport failure) publishes no sidecar and
is simply rerun by the next invocation.

    python eval/personal_assistant/run.py --scenario kestrel_quiz_booth --episodes 2 \
        --model claude-sonnet-5 --key-env MY_ANTHROPIC_KEY
    python eval/personal_assistant/run.py --all --episodes 100 --parallel 8 --model gpt-5.6-terra
    python eval/personal_assistant/run.py --jobs-file draw.csv --mitigation guard --print-info
    python eval/personal_assistant/run.py --all --formation team --context-files on --episodes 100

Layout under `--runs-root`: `<short>__<model>/wave_config.json`, `worlds/<cell>__e<N>.json`
(the sidecars `report.py` scores) and `runs/<cell>__<model>__e<N>/` (pi sessions, the world
ledger — the provider screens need these; keep them).

Mitigations: `--mitigation NAME` (default `none`) runs an arm of `personal_assistant/mitigations/`; an
arm's episodes live in their own wave, `<short>__<model>__mit-<name>/`, whose `wave_config.json` records
the arm. `--jobs-file` runs an explicit episode list instead of the matrix (the paper's mitigation
protocol re-runs a draw of previously failed team episodes, an explicit (scenario, epoch) list; each row
may name its own arm; see `eval/_jobs.py` and `mitigations/`).

Isolation: pi ends every seat's system prompt with `Current working directory: <cwd>`. The paper's
episodes ran the root-host path (`root_host=True`: one OS user per seat in a
single-use Modal container, cwd `/home/pa-<name>/dinner`); `--isolation auto` (the default) takes
that path inside a Modal container (`--isolation root` elsewhere, as root in a single-use Linux
container: one episode per invocation). On any other host `auto` is `none` (`harness/local_runtime.py`):
per-seat homes under one OS user in an opaque temp root, so the prompt shows a host path instead,
recorded as `host_seat_cwd` in each sidecar (a known difference; `report.py` / `check.py` flag it).

Context files: `--context-files on` launches every pi seat without `--no-context-files`, so pi loads the
AGENTS.md the runtime writes into each seat's cwd (the paper's supplementary
`pa_context_files` rerun). The default, `off`, is the paper's main instrument. An on-run lives in its own
waves, `<short>__<model>[__mit-<arm>]__ctx-on/`, whose `wave_config.json` and sidecars record
`"context_files": true`; the reports refuse to pool it with off-episodes.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from personal_assistant._paths import EVAL_ROOT, REPO_ROOT, bootstrap  # noqa: E402

bootstrap()

from dotenv import load_dotenv  # noqa: E402

# Fill unset keys from the repository or environment-local .env; shell exports win.
load_dotenv(EVAL_ROOT.parent.parent / ".env", override=False)
load_dotenv(EVAL_ROOT / ".env", override=False)

from _harness import pi_rpc  # noqa: E402
from _jobs import JobsFileError, read_jobs_file  # noqa: E402
from _mitigations import NONE, stamp  # noqa: E402
from _providers import PROVIDERS, path_safe_model, resolve_api_key  # noqa: E402

from personal_assistant import mitigations, registry  # noqa: E402
from personal_assistant.environment import food_run, trip_cart, trip_run  # noqa: E402
from personal_assistant.environment.pi_runtime import (  # noqa: E402
    CONTEXT_FILES_CHOICES,
    context_files_flag,
)
from personal_assistant.environment.worlds import CELLS, tools_manifest  # noqa: E402
from personal_assistant.harness import local_runtime  # noqa: E402
from personal_assistant.mitigations import manifest_digest  # noqa: E402
from personal_assistant.scenarios import register_trip_specs  # noqa: E402

register_trip_specs()

WAVE_CONFIG_NAME = "wave_config.json"
WAVE_SCHEMA = "eval/personal_assistant/1"


@dataclass(frozen=True)
class RunConfig:
    """Everything one invocation pins for every episode it runs."""

    model: str
    provider: str
    thinking: str
    isolation: str
    fake_pi: bool
    turn_timeout: float
    hard_cap: float
    revision: str
    pi_version: str
    #: `--context-files on`: pi loads each seat's AGENTS.md.
    context_files: bool = False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    which = parser.add_argument_group("which scenarios")
    which.add_argument(
        "--scenario", nargs="*", default=[], help="launcher shorts (see --list)"
    )
    which.add_argument("--hero", action="store_true", help="the 16 original scenarios")
    which.add_argument("--safety", action="store_true", help="the 9 safety scenarios")
    which.add_argument("--all", action="store_true", help="all 25 scenarios of record")
    which.add_argument(
        "--list", action="store_true", help="print the registry and exit"
    )
    which.add_argument(
        "--jobs-file",
        type=Path,
        default=None,
        help="a CSV of explicit episodes (scenario,formation,epoch[,mitigation]; see eval/_jobs.py) "
        "instead of the matrix; exclusive with the scenario selection, --formation, --episodes, --epoch0",
    )
    parser.add_argument(
        "--formation",
        nargs="+",
        choices=registry.FORMATIONS,
        default=None,
        help="formations to run (default: coordinator team; the paper's matrix names all three, "
        "coordinator team team_silent, which every scenario carries)",
    )
    parser.add_argument("--episodes", type=int, default=None, help="default: 1")
    parser.add_argument(
        "--epoch0", type=int, default=None, help="first epoch (1-based; default 1)"
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
        help="mitigation arm (default none = the formation itself; see --list-mitigations); its "
        "episodes get their own wave dir, <short>__<model>__mit-<name>",
    )
    parser.add_argument(
        "--list-mitigations",
        action="store_true",
        help="print the mitigation registry and exit",
    )
    parser.add_argument(
        "--context-files",
        choices=CONTEXT_FILES_CHOICES,
        default="off",
        help="off (default, the paper's main instrument): every pi seat runs with "
        "--no-context-files; on: pi loads each seat's AGENTS.md (the paper's supplementary "
        "pa_context_files rerun); on-episodes get their own waves, <short>__<model>...__ctx-on",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("MODEL", "claude-sonnet-5"),
        help="pi model id: claude-* (anthropic), gpt-*/o* (openai), <vendor>/<model> (openrouter), "
        "or a campaign alias (opus, sonnet, sol, terra)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=PROVIDERS,
        help="pi provider (default: inferred from the model id)",
    )
    parser.add_argument(
        "--thinking",
        default=None,
        help="pi thinking level (default per provider: anthropic off, openai medium, openrouter off)",
    )
    parser.add_argument(
        "--key-env",
        default=None,
        help="env var holding the provider key (default ANTHROPIC_API_KEY / OPENAI_API_KEY / "
        "OPENROUTER_API_KEY or OPEN_ROUTER_KEY)",
    )
    parser.add_argument(
        "--api-key", default=None, help="the key itself (wins over --key-env)"
    )
    parser.add_argument("--runs-root", type=Path, default=EVAL_ROOT / "runs")
    parser.add_argument(
        "--parallel", type=int, default=1, help="episodes run concurrently"
    )
    parser.add_argument("--turn-timeout", type=float, default=1800.0)
    parser.add_argument(
        "--hard-cap",
        type=float,
        default=2700.0,
        help="ops hard cap per episode in seconds (must exceed the 21-minute window)",
    )
    parser.add_argument(
        "--isolation",
        choices=local_runtime.ISOLATION_CHOICES,
        default="auto",
        help="auto (default): root inside a Modal container, else none. root: the "
        "root-host path the paper's episodes ran (one OS user per seat, seat cwd "
        "/home/pa-<name>/dinner in pi's system prompt; Linux, as root, one episode per single-use "
        "container). none: per-seat homes under one OS user (any host; pi's system prompt then "
        "shows a host temp path as the seat's cwd). docker: the research code's per-seat "
        "OS-user container path",
    )
    parser.add_argument(
        "--attest-timeout",
        type=float,
        default=local_runtime.DEFAULT_ATTEST_TIMEOUT,
        help="seconds each seat gets to start pi and attest its tool surface (network-mounted "
        "pi installs starting many seats at once need minutes)",
    )
    parser.add_argument(
        "--pi-cmd",
        default=os.environ.get("EVAL_PI_CMD"),
        help="absolute path to the pinned pi 0.77.0 (default: EVAL_PI_CMD, else `pi` on PATH)",
    )
    parser.add_argument(
        "--node-dir",
        type=Path,
        default=os.environ.get("EVAL_NODE_DIR"),
        help="a Node 22+ bin dir to put first on the seats' PATH (default: EVAL_NODE_DIR)",
    )
    parser.add_argument(
        "--pack-workspaces",
        action="store_true",
        help="after an episode banks, tar its seat trees (agents/, agent_dir/) into workspaces.tar.gz "
        "(the readout needs only the sidecar and the run dir's world/; on a Modal Volume the file count is the budget)",
    )
    parser.add_argument(
        "--fake-pi",
        action="store_true",
        help="drive harness/fake_pi.py instead of real pi (offline; no model, no key)",
    )
    parser.add_argument(
        "--fake-scripts",
        type=Path,
        default=None,
        help="dir of per-seat FakePi scripts (<seat-username>.json / default.json)",
    )
    parser.add_argument(
        "--print-info",
        action="store_true",
        help="print the job matrix only, running nothing (useful before an expensive eval)",
    )
    # `--dry-run` is not an option (printing the job matrix without running it is `--print-info`): declared hidden
    # only so that it is refused.
    parser.add_argument(
        "--dry-run", dest="not_print_info", action="store_true", help=argparse.SUPPRESS
    )
    args = parser.parse_args(argv)
    if args.not_episodes is not None:
        parser.error("unknown option --epochs (episodes per cell is --episodes)")
    if args.not_print_info:
        parser.error(
            "unknown option --dry-run (printing the job matrix without running it is --print-info)"
        )
    if args.fake_scripts is not None and not args.fake_pi:
        parser.error("--fake-scripts needs --fake-pi")
    if args.jobs_file is not None:
        given = [
            flag
            for flag, value in (
                ("--scenario", args.scenario),
                ("--all", args.all),
                ("--hero", args.hero),
                ("--safety", args.safety),
            )
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
        args.formation = list(registry.DEFAULT_FORMATIONS)
    args.episodes = 1 if args.episodes is None else args.episodes
    args.epoch0 = 1 if args.epoch0 is None else args.epoch0
    if args.episodes < 1 or args.epoch0 < 1:
        parser.error("--episodes and --epoch0 are 1-based positive integers")
    return args


#: One planned episode: `(scenario, formation, epoch, mitigation)`.
Planned = tuple[registry.Scenario, str, int, str]


def planned_episodes(args: argparse.Namespace) -> list[Planned]:
    """Every episode of the invocation: the matrix, or `--jobs-file`'s list.

    The matrix skips (loudly) a formation a scenario is not wired for; a jobs file naming one is an error.

    Raises:
        SystemExit: An unknown scenario, a bad jobs file, a formation a listed scenario is not wired
            for, or an arm that does not apply to a formation it would run.
    """
    try:
        if args.jobs_file is not None:
            out: list[Planned] = []
            for job in read_jobs_file(
                args.jobs_file, default_mitigation=args.mitigation
            ):
                row = registry.scenario(job.scenario)
                if job.formation not in row.formations:
                    raise SystemExit(
                        f"--jobs-file {args.jobs_file}: {job.label}: {row.short} is wired for "
                        f"{'/'.join(row.formations)} only ({row.substrate} substrate)"
                    )
                mitigations.validate(job.mitigation, [job.formation])
                out.append((row, job.formation, job.epoch, job.mitigation))
            return out
        planned: list[Planned] = []
        for scenario in selected_scenarios(args):
            formations = tuple(f for f in args.formation if f in scenario.formations)
            skipped = sorted(set(args.formation) - set(formations))
            if skipped:
                print(
                    f"{scenario.short}: formation(s) {', '.join(skipped)} not wired for this "
                    f"scenario ({scenario.substrate} substrate) — skipped",
                    flush=True,
                )
            mitigations.validate(args.mitigation, list(formations))
            planned.extend(
                (scenario, formation, epoch, str(args.mitigation))
                for formation in formations
                for epoch in range(args.epoch0, args.epoch0 + args.episodes)
            )
        return planned
    except (JobsFileError, ValueError) as exc:
        raise SystemExit(str(exc)) from None


def selected_scenarios(args: argparse.Namespace) -> list[registry.Scenario]:
    """The registry rows this invocation runs, in registry order."""
    wanted = set(args.scenario)
    if args.all:
        wanted |= set(registry.SCENARIOS)
    if args.hero:
        wanted |= set(registry.HERO_SHORTS)
    if args.safety:
        wanted |= set(registry.SAFETY_SHORTS)
    if not wanted:
        raise SystemExit(
            "pick scenarios: --scenario <short>..., --hero, --safety or --all"
        )
    for short in sorted(wanted - registry.SCENARIOS.keys()):
        registry.scenario(short)  # exits with the registry listing
    return [row for short, row in registry.SCENARIOS.items() if short in wanted]


def formation_manifest(
    scenario: registry.Scenario, formation: str, mitigation: str = NONE
) -> list[dict[str, Any]]:
    """The exact §5.2 tool surface one formation of a scenario registers as pi tools (under an arm, its own)."""
    if mitigation != NONE:
        return mitigations.tool_manifest(scenario, formation, mitigation)
    if scenario.substrate == "food":
        return tools_manifest(CELLS[scenario.cell(formation)])
    return trip_cart.trip_tools(registry.TOPOLOGY_BY_FORMATION[formation])


#: The wave-dir suffix of a `--context-files on` wave (off-waves keep their name).
CONTEXT_FILES_STAMP = "__ctx-on"


def wave_name(
    short: str, model: str, mitigation: str = NONE, context_files: bool = False
) -> str:
    """A wave dir's name: `<short>__<model>` (+ `__mit-<arm>`, + `__ctx-on`; the control off-wave is unchanged)."""
    ctx = CONTEXT_FILES_STAMP if context_files else ""
    return f"{short}__{path_safe_model(model)}{stamp(mitigation)}{ctx}"


def wave_config(
    scenario: registry.Scenario,
    formations: tuple[str, ...],
    config: RunConfig,
    mitigation: str = NONE,
) -> dict[str, Any]:
    """The immutable per-wave configuration (written once, validated on every resume).

    A mitigation arm's wave records `mitigation` and a context-files wave `"context_files": true`; the
    control off-wave's manifest is unchanged, so a wave created before either existed still resumes.
    """
    record: dict[str, Any] = {
        "schema": WAVE_SCHEMA,
        "scenario": scenario.short,
        "substrate": scenario.substrate,
        "cell_prefix": scenario.cell_prefix,
        "model": config.model,
        "provider": config.provider,
        "thinking": config.thinking,
        "git_sha": config.revision,
        "pi_version": config.pi_version,
        "isolation": config.isolation,
        "fake_pi": config.fake_pi,
        "turn_timeout": config.turn_timeout,
        "hard_cap": config.hard_cap,
        "manifest_sha256": {
            formation: manifest_digest(
                formation_manifest(scenario, formation, mitigation)
            )
            for formation in sorted(formations)
        },
    }
    if mitigation != NONE:
        record["mitigation"] = mitigation
    if config.context_files:
        record["context_files"] = True
    return record


def pinned_revision(wave_dir: Path) -> str | None:
    """The git sha an existing wave was created under, if any.

    The environment pins every completion sidecar and the wave manifest to one revision and refuses a
    resume from another. The eval resumes waves across its own commits by driving them under the
    wave's pinned revision (recorded in `wave_config.json`); the commit that actually ran each
    resume is appended to `resumes.jsonl` beside it, so nothing is hidden.
    """
    path = wave_dir / WAVE_CONFIG_NAME
    if not path.exists():
        return None
    prior: object = json.loads(path.read_bytes())
    if isinstance(prior, dict):
        sha = cast(dict[str, Any], prior).get("git_sha")
        return str(sha) if sha else None
    return None


def note_resume(wave_dir: Path, pinned: str, current: str) -> None:
    """Append the resuming commit when it differs from the wave's pin (fail-open bookkeeping)."""
    if pinned == current:
        return
    with (wave_dir / "resumes.jsonl").open("a") as handle:
        handle.write(json.dumps({"pinned": pinned, "resumed_with": current}) + "\n")


def ensure_wave(wave_dir: Path, expected: dict[str, Any]) -> None:
    """Create the wave manifest or require the existing one to match (the environment's gate).

    A resumed wave may have been created with a SUBSET of this invocation's formations; the
    manifest then grows, but a digest it already carries must not move.
    """
    wave_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = wave_dir / WAVE_CONFIG_NAME
    if not path.exists():
        path.write_text(json.dumps(expected, indent=1, sort_keys=True) + "\n")
        path.chmod(0o600)
        return
    prior: object = json.loads(path.read_bytes())
    if not isinstance(prior, dict):
        raise SystemExit(f"corrupt wave manifest {path}")
    prior_dict = dict(cast(dict[str, Any], prior))
    prior_digests: dict[str, str] = dict(
        cast(dict[str, str], prior_dict.pop("manifest_sha256", {}) or {})
    )
    expected_digests: dict[str, str] = dict(expected["manifest_sha256"])
    drift: dict[str, tuple[Any, Any]] = {
        key: (prior_dict.get(key), value)
        for key, value in expected.items()
        if key != "manifest_sha256" and prior_dict.get(key) != value
    }
    drift.update(
        {
            f"manifest_sha256[{formation}]": (prior_digests[formation], digest)
            for formation, digest in expected_digests.items()
            if formation in prior_digests and prior_digests[formation] != digest
        }
    )
    if drift:
        raise SystemExit(
            f"incompatible wave manifest {path}: {json.dumps(drift, sort_keys=True)} — a "
            "wave is pinned to one revision/model/thinking/surface; use a fresh --runs-root"
        )
    merged: dict[str, Any] = {
        **prior_dict,
        "manifest_sha256": {**prior_digests, **expected_digests},
    }
    if merged["manifest_sha256"] != prior_digests:
        path.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n")


def _prepend_path(directory: Path) -> None:
    """Put `directory` at the head of this process's PATH once (the pi validator probes by name)."""
    entries = os.environ.get("PATH", "").split(os.pathsep)
    if entries[:1] != [str(directory)]:
        os.environ["PATH"] = os.pathsep.join([str(directory), *entries])


def resolve_pi(pi_cmd: str | None, node_dir: Path | None) -> tuple[Path, str]:
    """The pinned pi as an absolute path plus its version, after the twin's runtime validation.

    Seats never search PATH for pi (the resolved path travels to `seat_exec.py` as data); only
    `pi_rpc.validate_runtime` needs `node` on this process's PATH and `EVAL_PI_CMD` set.
    """
    resolved = pi_cmd or shutil.which("pi")
    if not resolved:
        raise SystemExit(
            "pi not found — install @earendil-works/pi-coding-agent@0.77.0 (Node 22+) and "
            "set EVAL_PI_CMD to the absolute path of `pi` (or put it on PATH)"
        )
    pi_path = Path(resolved).resolve()
    if not pi_path.exists():
        raise SystemExit(f"EVAL_PI_CMD={resolved!r} does not exist")
    if node_dir is not None:
        _prepend_path(node_dir)
    if shutil.which("node") is None:
        raise SystemExit(
            "node not found on PATH — set EVAL_NODE_DIR to a Node 22+ bin dir"
        )
    os.environ["EVAL_PI_CMD"] = str(pi_path)
    pi_rpc.validate_runtime()
    return pi_path, pi_rpc.pi_version() or "unknown"


@dataclass(frozen=True)
class Job:
    """One (scenario, formation, epoch[, mitigation]) episode and where its records go."""

    scenario: registry.Scenario
    formation: str
    epoch: int
    wave_dir: Path
    mitigation: str = NONE

    @property
    def label(self) -> str:
        arm = "" if self.mitigation == NONE else f"/{self.mitigation}"
        return f"{self.scenario.short}/{self.formation}/e{self.epoch}{arm}"


def pack_workspaces(run_dir: Path) -> Path | None:
    """Tar a banked episode's seat trees (`agents/`, `agent_dir/`) into `workspaces.tar.gz`; idempotent."""
    import tarfile

    bulky = [
        run_dir / name for name in ("agents", "agent_dir") if (run_dir / name).is_dir()
    ]
    if not bulky:
        return None
    archive = run_dir / "workspaces.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in bulky:
            tar.add(path, arcname=path.name)
    for path in bulky:
        shutil.rmtree(path, ignore_errors=True)
    return archive


def run_job(job: Job, config: RunConfig, api_key: str, *, pack: bool = False) -> str:
    """Run or skip one episode through the environment's own substrate runner.

    `--isolation root` is the paper launchers' call: `root_host=True`, with the code and the runs root as
    boundary roots the seats' OS users must not reach (the paper's runs: the repo, the results volume and
    the wave).
    """
    topology = registry.TOPOLOGY_BY_FORMATION[job.formation]
    root_host = config.isolation == "root"
    common: dict[str, Any] = {
        "model": config.model,
        "api_key": api_key,
        "runs_root": job.wave_dir / "runs",
        "worlds_dir": job.wave_dir / "worlds",
        "turn_timeout": config.turn_timeout,
        "hard_cap": config.hard_cap,
        "revision": config.revision,
        "thinking": config.thinking,
        "root_host": root_host,
        "scenario": job.scenario.short,
        "provider": config.provider,
    }
    if root_host:
        common["boundary_roots"] = (REPO_ROOT, job.wave_dir.parent, job.wave_dir)
    if config.context_files:
        common["context_files"] = True
    if job.mitigation != NONE:
        common.update(
            mitigations.episode_kwargs(job.scenario, job.formation, job.mitigation)
        )
    if job.scenario.substrate == "food":
        status = food_run.run_episode(topology, job.epoch, **common)
    else:
        status = trip_run.run_episode(topology, job.epoch, **common)
    if pack:
        cell = mitigations.episode_cell(job.scenario, job.formation, job.mitigation)
        run_dir = (
            job.wave_dir
            / "runs"
            / f"{cell}__{path_safe_model(config.model)}__e{job.epoch}"
        )
        if (job.wave_dir / "worlds" / f"{cell}__e{job.epoch}.json").exists():
            pack_workspaces(run_dir)
    return status


def _install_local_runtimes() -> None:
    """Point the environment's runners at the local runtime subclasses for this process.

    `food_run.run_episode` / `trip_run.run_episode` build their runtime by module-global name
    (no factory parameter yet); the subclasses are drop-in constructors that add the unprivileged
    mode and defer to the environment's docker path for
    `--isolation docker`.
    """
    food_run.FoodRuntime = local_runtime.LocalFoodRuntime  # type: ignore[misc]
    trip_run.TripRuntime = local_runtime.LocalTripRuntime  # type: ignore[misc]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.list:
        for row in registry.SCENARIOS.values():
            pool = "safety" if row.short in registry.SAFETY_SHORTS else "original"
            flags = " non-committing-flagged" if row.safety_non_committing else ""
            print(
                f"{row.short:32} {row.substrate:5} {pool:9} "
                f"{'/'.join(row.formations)}{flags}"
            )
        return 0
    if args.list_mitigations:
        print(mitigations.listing())
        return 0
    planned = planned_episodes(args)
    context_files = context_files_flag(args.context_files)
    model = registry.model_id(args.model)
    provider = registry.provider_for(model, args.provider)
    thinking = registry.resolve_thinking(provider, args.thinking)
    isolation = local_runtime.resolve_isolation(
        args.isolation, check=not args.print_info
    )
    if isolation == "root" and len(planned) > 1 and not args.print_info:
        raise SystemExit(
            f"--isolation {args.isolation} runs the root-host path, which creates the seats' OS "
            "users (pa-<name>) on this host and never removes them: one episode per single-use "
            f"container (the Modal launcher's shape); this invocation plans {len(planned)}"
        )
    runs_root: Path = args.runs_root.resolve()
    if args.print_info:
        pi_version = "fake" if args.fake_pi else "not-started"
        api_key = ""
    else:
        runs_root.mkdir(parents=True, exist_ok=True)
        if args.fake_pi:
            pi_cmd, pi_version = local_runtime.FAKE_PI, "fake"
            api_key = "fake-not-used"
        else:
            pi_cmd, pi_version = resolve_pi(args.pi_cmd, args.node_dir)
            api_key = resolve_api_key(provider, args.key_env, args.api_key)
        launch = local_runtime.SeatLaunch(
            pi_cmd=pi_cmd,
            node_dir=args.node_dir,
            fake_script_dir=args.fake_scripts.resolve() if args.fake_scripts else None,
        )
        local_runtime.configure(isolation, launch, args.attest_timeout)
        _install_local_runtimes()
    config = RunConfig(
        model=model,
        provider=provider,
        thinking=thinking,
        isolation=isolation,
        fake_pi=bool(args.fake_pi),
        turn_timeout=args.turn_timeout,
        hard_cap=args.hard_cap,
        # `--print-info` resolves no revision and records nothing: its plan prints this placeholder
        revision="not-run" if args.print_info else food_run.git_sha(),
        pi_version=pi_version,
        context_files=context_files,
    )
    # One wave per (scenario, mitigation arm): its manifest pins the formations it runs.
    jobs: list[Job] = []
    waves: dict[Path, tuple[registry.Scenario, str, list[str]]] = {}
    for scenario, formation, epoch, mitigation in planned:
        wave_dir = runs_root / wave_name(
            scenario.short, model, mitigation, context_files
        )
        wave_formations = waves.setdefault(wave_dir, (scenario, mitigation, []))[2]
        if formation not in wave_formations:
            wave_formations.append(formation)
        jobs.append(Job(scenario, formation, epoch, wave_dir, mitigation))
    configs: dict[Path, RunConfig] = {}
    for wave_dir, (scenario, mitigation, formations) in waves.items():
        pinned = pinned_revision(wave_dir) or config.revision
        wave_run_config = replace(config, revision=pinned)
        configs[wave_dir] = wave_run_config
        if not args.print_info:
            ensure_wave(
                wave_dir,
                wave_config(scenario, tuple(formations), wave_run_config, mitigation),
            )
            note_resume(wave_dir, pinned, config.revision)
    if args.jobs_file is not None:
        shape = f"jobs file {args.jobs_file}"
    else:
        shape = (
            f"{len({s.short for s, *_ in planned})} scenario(s) x {args.formation} x "
            f"epochs {args.epoch0}-{args.epoch0 + args.episodes - 1}"
        )
    arms = sorted({job.mitigation for job in jobs})
    print(
        f"{len(jobs)} episode(s): {shape}; model={model} "
        f"provider={provider} thinking={thinking} isolation={config.isolation} "
        f"pi={pi_version} revision={config.revision[:9]} parallel={args.parallel}"
        + (f" mitigation={','.join(arms)}" if arms and arms != [NONE] else "")
        + (" context_files=on" if context_files else ""),
        flush=True,
    )
    if args.print_info:
        for job in jobs:
            print(f"  {job.label:56} -> {job.wave_dir.relative_to(runs_root)}")
        return 0
    failures = 0
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = {
            pool.submit(
                run_job,
                job,
                configs[job.wave_dir],
                api_key,
                pack=bool(args.pack_workspaces),
            ): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                print(f"[{job.label}] {future.result()}", flush=True)
            except Exception:  # noqa: BLE001 — one episode must not destroy resumability
                failures += 1
                print(
                    f"[{job.label}] FAILED (rerun the same command to resume):",
                    flush=True,
                )
                traceback.print_exc()
    print(
        f"{len(jobs) - failures}/{len(jobs)} episodes completed -> {runs_root}",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
