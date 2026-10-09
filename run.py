"""MAMUBench: play an environment's paper runs on Modal (default) or on this machine.

    python run.py api_key                         # every scenario, formation, model and episode the paper ran
    python run.py clinic --mitigation all         # every mitigation arm's paper runs (one arm: --mitigation s3)
    python run.py merge_queue --model claude-opus-5 --formation team --episodes 2 --backend local
    python run.py personal_assistant --print-info # the plan; nothing runs (--verbose: every episode)

With no option a command plays its environment's paper matrix (`eval/<env>/matrix.py`) into one runs root,
`results` (`eval/<env>/runs/results` locally, `<env>/results` on the Modal Volume), every model in it; the personal
assistant's AGENTS.md-in-context run follows into `context_files`. `--model`, `--formation`, `--scenario` and
`--episodes` (per cell) narrow it. `--mitigation all` plays every mitigation arm's paper runs instead
(`eval/<env>/mitigations/`), `--mitigation ARM` one arm's. A Modal launch returns once it is dispatched and prints
how to follow and pull it; rerunning the same command resumes it. `--print-info` prints what a launch would do
without running anything, which is useful before an expensive eval. Options this launcher does not know
(`--fake-model`, `--fake-pi`, `--context-files on|off`, ...) go to `eval/<env>/run.py` (merge_queue has no
`--fake-pi`: `--print-info --render-to DIR` writes its planned episodes' records and briefs instead).
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from _matrix import Root

ROOT = Path(__file__).resolve().parent
EVALS = ("api_key", "clinic", "merge_queue", "personal_assistant")
FORMATIONS = ("solo", "coordinator", "team_silent", "team")
#: Options that act on the LOCAL `--print-info` only (merge_queue's `--render-to DIR` writes the briefs it plans): a
#: Modal launch's `--print-info` renders on this machine, and the Modal command it prints leaves them out.
LOCAL_PRINT_INFO_OPTIONS: tuple[str, ...] = ("--render-to",)
#: Options a Modal container cannot honour: it reads the shipped provider keys and writes the Volume's root.
LOCAL_ONLY_OPTIONS: tuple[str, ...] = ("--key-env", "--api-key", "--runs-root")
#: `--epochs` and the abbreviations argparse would have read as it: not options (episodes per cell is `--episodes`).
#: Refused here rather than forwarded, where a launch would plan the full matrix and `eval/<env>/run.py` would
#: refuse them (`--epoch N` would otherwise reach it as `--epoch0 N`).
NOT_EPISODES_OPTIONS: tuple[str, ...] = ("--epo", "--epoc", "--epoch", "--epochs")
#: `--dry-run` and the abbreviations argparse would have read as it: not options (printing what a launch would do
#: without running it is `--print-info`). Refused here rather than forwarded, where the launch would go on to
#: `eval/<env>/run.py` or Modal before being refused.
NOT_PRINT_INFO_OPTIONS: tuple[str, ...] = (
    "--d",
    "--dr",
    "--dry",
    "--dry-",
    "--dry-r",
    "--dry-ru",
    "--dry-run",
)


def _eval_path() -> None:
    """Put `eval/` (and its shared runtime) on `sys.path`, as the eval runners do."""
    if str(ROOT / "eval") not in sys.path:
        sys.path.insert(0, str(ROOT / "eval"))
    from _paths import bootstrap

    bootstrap()


def parse_args(argv: list[str] | None = None) -> tuple[argparse.Namespace, list[str]]:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("environment", choices=EVALS)
    parser.add_argument(
        "--model", nargs="+", default=[], help="default: the paper's models"
    )
    parser.add_argument("--formation", nargs="+", default=[], choices=FORMATIONS)
    parser.add_argument(
        "--scenario", nargs="+", default=[], help="scenario ids (see --list)"
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=None,
        help="episodes per cell: 1..N (the first N where the paper holds a list)",
    )
    parser.add_argument(
        "--mitigation",
        default="none",
        help="play this mitigation arm's paper runs, or `all`: every arm's (see --list-mitigations)",
    )
    parser.add_argument(
        "--jobs-file",
        type=Path,
        default=None,
        help="explicit episodes (scenario,formation,epoch[,mitigation]) instead of the matrix, played by each "
        "--model (default claude-sonnet-5)",
    )
    parser.add_argument(
        "--harness",
        choices=("sim", "pi"),
        default=None,
        help="api_key / clinic: sim (default, the paper's) or pi (real pi seats)",
    )
    parser.add_argument("--backend", choices=("modal", "local"), default="modal")
    parser.add_argument(
        "--runs-name", default=None, help="the runs root (default: results)"
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=ROOT / ".env",
        help="dotenv file read first (fills unset variables only)",
    )
    parser.add_argument(
        "--print-info",
        action="store_true",
        help="print what the launch would do without running anything (useful before an expensive eval)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="with --print-info: every episode, as each model's eval runner plans it",
    )
    parser.add_argument(
        "--list", action="store_true", help="print the scenario registry"
    )
    parser.add_argument(
        "--list-mitigations", action="store_true", help="print the mitigation arms"
    )
    args, extra = parser.parse_known_args(argv)
    for option in NOT_EPISODES_OPTIONS:
        if has_option(extra, option):
            parser.error(f"unknown option {option} (episodes per cell is --episodes)")
    for option in NOT_PRINT_INFO_OPTIONS:
        if has_option(extra, option):
            parser.error(
                f"unknown option {option} (printing what a launch would do without running it is --print-info)"
            )
    env = args.environment
    if args.harness is None:
        args.harness = (
            "sim" if env in ("api_key", "clinic") and "--fake-pi" not in extra else "pi"
        )
    if args.harness == "sim" and env not in ("api_key", "clinic"):
        parser.error("--harness sim is available for api_key and clinic")
    if env == "merge_queue" and has_option(extra, "--fake-pi"):
        parser.error(
            "merge_queue has no offline stand-in (--fake-pi); `--print-info --render-to DIR` writes every planned "
            "episode's record and briefs without a key or pi"
        )
    if args.jobs_file is not None:
        given = [
            flag
            for flag, value in (
                ("--formation", args.formation),
                ("--scenario", args.scenario),
                ("--episodes", args.episodes),
            )
            if value not in (None, [])
        ]
        if given:
            parser.error(f"--jobs-file lists every episode; drop {', '.join(given)}")
        args.jobs_file = args.jobs_file.resolve()
    if args.episodes is not None and args.episodes < 1:
        parser.error("--episodes must be positive")
    if args.runs_name and (
        Path(args.runs_name).name != args.runs_name or args.runs_name in (".", "..")
    ):
        parser.error("--runs-name must be a single directory name")
    if args.backend == "modal":
        for option in LOCAL_ONLY_OPTIONS:
            if has_option(extra, option):
                parser.error(
                    f"{option} is local only: Modal containers read ANTHROPIC_API_KEY / OPENAI_API_KEY / "
                    "OPENROUTER_API_KEY (or the variable EVAL_KEY_ENV names) and write the Volume root --runs-name"
                )
    return args, extra


def has_option(extra: list[str], name: str) -> bool:
    """Whether a forwarded option `name` is among `extra` (as `--name value` or `--name=value`)."""
    return any(item == name or item.startswith(f"{name}=") for item in extra)


def pop_option(extra: list[str], name: str) -> tuple[list[str], str | None]:
    """`(extra without option name and its value, the value)`."""
    kept: list[str] = []
    value: str | None = None
    items = iter(extra)
    for item in items:
        if item == name:
            value = next(items, None)
        elif item.startswith(f"{name}="):
            value = item.split("=", 1)[1]
        else:
            kept.append(item)
    return kept, value


def without_local_print_info_options(extra: list[str]) -> tuple[list[str], list[str]]:
    """`(extra without LOCAL_PRINT_INFO_OPTIONS and their values, the options removed)`."""
    kept: list[str] = []
    removed: list[str] = []
    skip_value = False
    for item in extra:
        if skip_value:
            removed.append(item)
            skip_value = False
            continue
        name = item.split("=", 1)[0]
        if name in LOCAL_PRINT_INFO_OPTIONS:
            removed.append(item)
            skip_value = "=" not in item
            continue
        kept.append(item)
    return kept, removed


def modal_command(args: argparse.Namespace, extra: list[str], name: str) -> list[str]:
    """The detached `modal run eval/modal_app.py::main` of this launch (the app resolves the same plan)."""
    command = [
        sys.executable,
        "-m",
        "modal",
        "run",
        "--detach",
        str(ROOT / "eval" / "modal_app.py") + "::main",
        "--eval",
        args.environment,
        "--harness",
        args.harness,
        "--runs-name",
        name,
    ]
    for flag, values in (
        ("--model", args.model),
        ("--formation", args.formation),
        ("--scenario", args.scenario),
    ):
        if values:
            command += [flag, ",".join(values)]
    if args.episodes is not None:
        command += ["--episodes", str(args.episodes)]
    if args.mitigation != "none":
        command += ["--mitigation", args.mitigation]
    if args.jobs_file is not None:
        command += ["--jobs-file", str(args.jobs_file)]
    command.append("--spawn-driver")
    remaining = list(extra)
    for flag in (
        "--fake-model",
        "--fake-pi",
    ):  # first-class Modal options: they take part in its validation
        if flag in remaining:
            command.append(flag)
            remaining.remove(flag)
    if remaining:
        command += ["--extra", shlex.join(remaining)]
    return command


def eval_command(
    args: argparse.Namespace,
    model: str,
    jobs_file: Path,
    runs_root: Path,
    extra: list[str],
) -> list[str]:
    """`eval/<env>/run.py` playing one model's episodes (a jobs file) into `runs_root`."""
    command = [
        sys.executable,
        str(ROOT / "eval" / args.environment / "run.py"),
        "--model",
        model,
        "--jobs-file",
        str(jobs_file),
        "--runs-root",
        str(runs_root),
    ]
    if args.environment in ("api_key", "clinic"):
        command += ["--harness", args.harness]
    if args.print_info:
        command.append("--print-info")
    return [*command, *extra]


def play_here(
    args: argparse.Namespace,
    extra: list[str],
    roots: Sequence[Root],
) -> int:
    """Play each model's episodes (or print their plan) root by root with the eval's own runner."""
    from _jobs import JobSpec, write_jobs_file
    from _providers import path_safe_model

    failed = 0
    models = dict.fromkeys(e.model for root in roots for e in root.episodes)
    with tempfile.TemporaryDirectory(prefix="mamubench-") as tmp:
        for model in models:
            for root in roots:
                mine = [e for e in root.episodes if e.model == model]
                if not mine:
                    continue
                runs_root = root_path(args, extra, root.name)
                jobs = Path(tmp) / f"{path_safe_model(model)}__{root.name}.csv"
                write_jobs_file(
                    jobs,
                    [
                        JobSpec(e.scenario, e.formation, e.epoch, e.mitigation)
                        for e in mine
                    ],
                )
                command = eval_command(
                    args, model, jobs, runs_root, [*without_root(extra), *root.options]
                )
                failed += subprocess.run(command, cwd=ROOT).returncode != 0
    return 1 if failed else 0


def root_path(args: argparse.Namespace, extra: list[str], name: str) -> Path:
    """Where a runs root lands on this machine: `eval/<env>/runs/<name>`.

    A local `--runs-root` moves the first root; the personal assistant's second one lands beside it
    (`<runs root>_context_files`).
    """
    import _matrix

    override = pop_option(extra, "--runs-root")[1]
    if override is None:
        return ROOT / "eval" / args.environment / "runs" / name
    first = Path(override).resolve()
    if name == args.first_root:
        return first
    return first.with_name(first.name + _matrix.CONTEXT_FILES_SUFFIX)


def without_root(extra: list[str]) -> list[str]:
    """`extra` without a local `--runs-root` (each root's own is passed explicitly)."""
    return pop_option(extra, "--runs-root")[0]


def main(argv: list[str] | None = None) -> int:
    args, extra = parse_args(argv)
    load_dotenv(args.env_file, override=False)
    env = args.environment
    if args.list or args.list_mitigations:
        flag = "--list" if args.list else "--list-mitigations"
        return subprocess.run(
            [sys.executable, str(ROOT / "eval" / env / "run.py"), flag], cwd=ROOT
        ).returncode
    _eval_path()
    import _matrix

    fake = _matrix.is_fake(extra)
    try:
        roots = _matrix.launch_roots(
            env,
            models=args.model,
            formations=args.formation,
            scenarios=args.scenario,
            epochs=args.episodes,
            mitigation=args.mitigation,
            jobs_file=args.jobs_file,
            harness=args.harness,
            extra=extra,
            runs_name=args.runs_name,
        )
    except ValueError as exc:
        print(f"run.py: error: {exc}", file=sys.stderr)
        return 2
    if not roots[0].episodes:
        why = _matrix.nothing_to_run(
            env, mitigation=args.mitigation, jobs_file=args.jobs_file, extra=extra
        )
        print(f"run.py: error: nothing to run: {why}", file=sys.stderr)
        return 2
    args.first_root = roots[0].name
    episodes = [e for root in roots for e in root.episodes]
    for root in roots:
        if args.backend == "modal":
            shown = f"Modal Volume {env}/{root.name}"
        else:
            shown = str(root_path(args, extra, root.name))
        print(
            _matrix.summary(
                env,
                root.episodes,
                shown,
                note=" (AGENTS.md in context)"
                if "--context-files" in root.options
                else "",
            ),
            flush=True,
        )
    if not (args.print_info or fake):
        # a Modal container reads the target key from the variable EVAL_KEY_ENV names, when it is set
        key_env = os.environ.get("EVAL_KEY_ENV") if args.backend == "modal" else None
        refusal = _matrix.missing_keys(
            env,
            dict.fromkeys(e.model for e in episodes),
            args.harness,
            os.environ,
            [*extra, "--key-env", key_env] if key_env else extra,
        )
        if refusal:
            print(f"run.py: error: {refusal}", file=sys.stderr)
            return 2
    if args.backend == "local":
        if args.print_info and not (args.verbose or has_local_print_info_option(extra)):
            return 0
        return play_here(args, extra, roots)
    environ = os.environ.copy()
    if args.harness == "sim" and not fake and "EVAL_MODAL_TIMEOUT_S" not in environ:
        # Modal fixes a function's timeout when the app module is imported: size it to the launch's longest
        # episode (its time limit, long-limit retry and margin).
        environ["EVAL_MODAL_TIMEOUT_S"] = str(_matrix.sim_timeout_s(env, episodes))
        print(f"EVAL_MODAL_TIMEOUT_S={environ['EVAL_MODAL_TIMEOUT_S']}", flush=True)
    if not args.print_info:
        return subprocess.run(
            modal_command(args, extra, args.first_root), cwd=ROOT, env=environ
        ).returncode
    modal_extra, local_only = without_local_print_info_options(extra)
    print(
        "Modal command: "
        + shlex.join(modal_command(args, modal_extra, args.first_root)),
        flush=True,
    )
    if not (args.verbose or local_only):
        return 0
    if local_only:
        print(
            f"(left out of the Modal command: {shlex.join(local_only)} acts on this plan, which renders here)",
            flush=True,
        )
    print(
        f"(each model's plan below as its eval runner prints it; its runs root stands for the Modal Volume's "
        f"{env}/<root>)",
        flush=True,
    )
    if env == "personal_assistant" and not has_option(extra, "--isolation"):
        # `--isolation auto` is root inside a Modal container (the paper's per-seat OS users), not this host's none.
        extra = [*extra, "--isolation", "root"]
        print(
            "(isolation: `auto` resolves to root inside each Modal container; the plan below shows that)",
            flush=True,
        )
    return play_here(args, extra, roots)


def has_local_print_info_option(extra: list[str]) -> bool:
    """Whether `extra` holds an option that acts on the local `--print-info` itself (`LOCAL_PRINT_INFO_OPTIONS`)."""
    return bool(without_local_print_info_options(extra)[1])


if __name__ == "__main__":
    raise SystemExit(main())
