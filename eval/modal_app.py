r"""Run any of MAMUBench's four environments on Modal: one container per episode, run dirs on a Modal Volume.

The container image is the pinned pi runtime (Node 22 + `@earendil-works/pi-coding-agent@0.77.0`,
`eval/_harness/Dockerfile`) plus this repo's Python dependencies and a copy of the repo itself. Each episode is
exactly the same `eval/<eval>/run.py` invocation the local path runs, pointed at `/results/<eval>/<runs-name>` on
the Volume, so the run dirs are byte-for-byte what a local run writes and `report.py` / `check.py` read them
unchanged after a pull.

`main` plays the same plan as the root `run.py` (`eval/_matrix.py`): with no option an environment's paper runs,
every model, into one runs root; `--model`, `--formation`, `--scenario` (comma-separated) and `--episodes` (per cell)
narrow it; the personal assistant's AGENTS.md-in-context rerun follows its paper runs into `context_files`.
Each model's episodes are one lane: a dispatch loop that runs them and retries the failed ones. A lane outlives
Modal's 24 h function limit: before it, the lane hands its remaining episodes and the ones still in flight (each its
own function call) to a continuation of itself. The root `run.py` launches detached and sizes the per-episode timeout
of the simulated harness (Modal fixes it when this module is imported; `main` refuses a shorter
`EVAL_MODAL_TIMEOUT_S` and prints the value it needs):

    EVAL_MODAL_TIMEOUT_S=45000 .venv/bin/python -m modal run --detach eval/modal_app.py::main --eval api_key \
        --runs-name results --spawn-driver
    EVAL_MODAL_TIMEOUT_S=59400 .venv/bin/python -m modal run --detach eval/modal_app.py::main --eval clinic \
        --runs-name results --spawn-driver
    .venv/bin/python -m modal run --detach eval/modal_app.py::main --eval merge_queue --mitigation charter \
        --runs-name results --spawn-driver
    EVAL_MODAL_TIMEOUT_S=37800 .venv/bin/python -m modal run eval/modal_app.py::main --eval api_key \
        --model claude-sonnet-5 --formation coordinator,team --scenario stakes_100 --episodes 2 --runs-name first
    .venv/bin/python -m modal run eval/modal_app.py::main --eval personal_assistant --model claude-opus-5 \
        --jobs-file eval/personal_assistant/mitigations/draw_all25_opus.csv --mitigation guard

    .venv/bin/python -m modal run eval/modal_app.py::main --probe   # image + pi runtime check
    .venv/bin/python -m modal run eval/modal_app.py::main --eval api_key --scenario stakes_100 --episodes 1 \
        --fake-pi   # plumbing on Modal, no model calls
    .venv/bin/python -m modal run eval/modal_app.py::main --eval clinic --scenario warfarin_inr_split --episodes 1 \
        --fake-model
    .venv/bin/python -m modal run eval/modal_app.py::pull --eval api_key --runs-name first  # -> eval/api_key/runs/first
    .venv/bin/python eval/api_key/report.py eval/api_key/runs/first
    .venv/bin/python eval/api_key/check.py eval/api_key/runs/first

Resumable exactly like the local path: rerunning the same command skips episodes whose `DONE.json` (or PA
sidecar) is already on the Volume. Concurrency = `EVAL_MODAL_MAX_CONTAINERS` (default 40, shared by the lanes);
each episode runs alone in a single-use container. Keys travel as an ephemeral Modal Secret built from the
launching shell's environment and end up only in each seat's pi auth file.

A mitigation arm's episodes are keyed by it everywhere: the claim key, the eval CLI's `--mitigation`, and the run
dir's `__mit-<name>` stamp.

Env knobs: `EVAL_MODAL_VOLUME` (the results Volume, default `mamubench-runs`), `EVAL_MODAL_CLAIMS` (the
episode-claims Dict, default `mamubench-episode-claims`), `EVAL_MODAL_VOLUME_ENV` (the Modal environment holding
the Volume and the Dict when it differs from the app's; `pull` passes it as `modal volume get --env`),
`EVAL_MODAL_APP` (default `mamubench`; the app name labels launches in `modal app list` / `modal app logs` and
nothing reads it back), `EVAL_MODAL_MAX_CONTAINERS`, `EVAL_MODAL_TIMEOUT_S` (per episode, default 5 h; a
simulated-harness launch needs at least `_matrix.sim_timeout_s`, except under `--fake-model`), `EVAL_MODAL_CPU`,
`EVAL_MODAL_MEMORY_MB`, `EVAL_MODAL_NONPREEMPTIBLE` (default on: episodes and the dispatch loops run on
non-preemptible containers; `0` opts out, and a preempted episode then restarts from scratch), `EVAL_MODAL_CLAIM_WAIT_S`
(default 900: how long a restarted episode waits for the claim its own interrupted attempt still holds, each of
Modal's retries of it waiting again, and how long a dispatch loop waits before a pass that follows claim conflicts).
The containers get the knobs they read (`FORWARDED_KNOBS`) through the launch's Secret.

A detached launch (`--spawn-driver`) prints its app id and, ready to paste (`.venv/bin/python -m modal ...`), how to
stream its logs (`app logs <ap-id> -f`) and stop it (`app stop <ap-id> -y`), how to follow each lane (`volume get [--env
<EVAL_MODAL_VOLUME_ENV>] <volume> <eval>/<runs-name>/_launch_<id>.json -`, rewritten after every result and reading
`"finished": true` once the lane and its continuations are done, or `volume_status`) and how to pull its roots.
"""

from __future__ import annotations

import datetime as dt
import importlib
import io
import json
import os
import shlex
import subprocess
import sys
import tarfile
import time
import uuid
import zlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

import modal
from dotenv import load_dotenv

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
# Modal mounts this launcher as /root/modal_app.py; runtime assets live in /repo.
if (
    not (REPO_ROOT / "pyproject.toml").is_file()
    and Path("/repo/pyproject.toml").is_file()
):
    REPO_ROOT = Path("/repo")  # pyright: ignore[reportConstantRedefinition]
    EVALS_DIR = REPO_ROOT / "eval"  # pyright: ignore[reportConstantRedefinition]
DOCKERFILE = EVALS_DIR / "_harness" / "Dockerfile"
load_dotenv(REPO_ROOT / ".env", override=False)
sys.path.insert(0, str(EVALS_DIR))
from _mitigations import NONE as NO_MITIGATION  # noqa: E402
from _mitigations import STAMP_PREFIX  # noqa: E402
from _providers import path_safe_model  # noqa: E402

REMOTE_REPO = Path("/repo")
VOLUME_MOUNT = Path("/results")
#: Where `npm install -g` puts pi in the node:22-slim image.
REMOTE_PI = "/usr/local/bin/pi"

EVALS: tuple[str, ...] = ("api_key", "clinic", "personal_assistant", "merge_queue")
#: Every formation the launcher accepts (the eval's registry says which it runs).
FORMATIONS: tuple[str, ...] = ("coordinator", "team", "team_silent", "solo")
#: The scenario-selection flag each eval's CLI uses.
SELECT_FLAG: dict[str, str] = {
    "api_key": "--scenario",
    "clinic": "--board",
    "personal_assistant": "--scenario",
    "merge_queue": "--scenario",
}
#: merge_queue episodes are real execution (git + pytest per seat, up to five pi processes): they get
#: their own container shape.
MQ_CPU = float(os.environ.get("EVAL_MODAL_MQ_CPU", "8"))
MQ_MEMORY_MB = int(os.environ.get("EVAL_MODAL_MQ_MEMORY_MB", "16384"))

APP_NAME = os.environ.get("EVAL_MODAL_APP", "mamubench")
VOLUME_NAME = os.environ.get("EVAL_MODAL_VOLUME", "mamubench-runs")
#: The Modal environment holding the Volume (None = the environment the app runs in).
VOLUME_ENV = os.environ.get("EVAL_MODAL_VOLUME_ENV") or None
#: How the printed follow-up commands call Modal's CLI: the project venv's, which needs no activated venv.
MODAL_CLI = ".venv/bin/python -m modal"
MAX_CONTAINERS = int(os.environ.get("EVAL_MODAL_MAX_CONTAINERS", "40"))
EPISODE_TIMEOUT_S = int(os.environ.get("EVAL_MODAL_TIMEOUT_S", str(5 * 3600)))
CPU = float(os.environ.get("EVAL_MODAL_CPU", "4"))
MEMORY_MB = int(os.environ.get("EVAL_MODAL_MEMORY_MB", "8192"))

#: Infrastructure retries for one episode: Modal loses a worker now and then ("Runner failed with
#: exception: Worker disappeared", 18 of the first 150 inputs of one personal_assistant run);
#: with no retries the input surfaces to the dispatch loop as a cancelled failure and waits for the next
#: resume. Episode claims exclude overlapping writers; a worker lost before releasing its claim
#: requires explicit recovery. A run whose CLI exits non-zero returns normally and is never retried here.
_RETRIES = modal.Retries(max_retries=2, initial_delay=60.0)
#: Dispatch passes per launch; each episode validates and skips its own completed output.
DISPATCH_PASSES = max(1, int(os.environ.get("EVAL_MODAL_DISPATCH_PASSES", "3")))
#: A dispatch lane's own timeout: Modal's longest function timeout.
DISPATCH_TIMEOUT_S = 24 * 3600
#: Seconds into a dispatch call after which it submits no more episodes and hands the lane to a continuation of
#: itself (the episodes in flight are their own function calls and keep running; the continuation collects them).
DISPATCH_HANDOFF_S = max(
    600, int(os.environ.get("EVAL_MODAL_DISPATCH_HANDOFF_S", str(22 * 3600)))
)
#: Episodes one lane keeps submitted at once (the containers they wait for are shared by every lane).
DISPATCH_WINDOW = max(
    1, int(os.environ.get("EVAL_MODAL_DISPATCH_WINDOW", str(MAX_CONTAINERS)))
)
#: Seconds between two looks at a lane's episodes in flight when none has finished.
DISPATCH_POLL_S = 20
#: Episodes and the dispatch loop run on non-preemptible containers unless `EVAL_MODAL_NONPREEMPTIBLE=0`. A
#: preempted episode restarts from scratch: four preemptions hit five clinic mornings (2-4.6 h each) of one live
#: launch on preemptible containers.
NONPREEMPTIBLE = os.environ.get(
    "EVAL_MODAL_NONPREEMPTIBLE", "1"
).strip().lower() not in (
    "0",
    "false",
    "no",
    "off",
)
#: Seconds a restarted input waits for the claim its own interrupted attempt still holds (a preempted container
#: packs, commits and releases in its shutdown window while Modal already restarts the input), and seconds the
#: dispatch loop waits before a pass that follows claim conflicts. The wait counts against the episode's timeout,
#: whose margin (`sim.EPISODE_MARGIN_S`, 1800 s) it stays inside; each of Modal's retries of the input waits again.
CLAIM_WAIT_S = max(0, int(os.environ.get("EVAL_MODAL_CLAIM_WAIT_S", "900")))
#: Seconds between two looks at a claim being waited for.
CLAIM_POLL_S = 15
#: How a claim conflict's error opens (the dispatch loop counts them by it).
CLAIM_CONFLICT = "Episode already claimed"
#: The seat-workspace archive a merge-queue episode's teardown writes into its run dir.
ARCHIVE_NAME = "workspaces.tar.gz"

#: Key variables shipped to containers when set locally (the evals' own resolver reads them).
KEY_VARS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "OPEN_ROUTER_KEY",
)
#: The `EVAL_MODAL_*` knobs a container reads as well. It re-imports this module with none of the launching shell's
#: variables, so they travel in the launch's Secret (the per-episode timeout is fixed at launch and need not).
FORWARDED_KNOBS: tuple[str, ...] = (
    "EVAL_MODAL_CLAIMS",
    "EVAL_MODAL_VOLUME",
    "EVAL_MODAL_VOLUME_ENV",
    "EVAL_MODAL_MAX_CONTAINERS",
    "EVAL_MODAL_DISPATCH_PASSES",
    "EVAL_MODAL_DISPATCH_HANDOFF_S",
    "EVAL_MODAL_DISPATCH_WINDOW",
    "EVAL_MODAL_CLAIM_WAIT_S",
)


def _git_sha() -> str:
    if revision := os.environ.get("EVAL_GIT_SHA"):
        return revision
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:  # no git on this host
        return "unknown"
    return out.stdout.strip() or "unknown"


_IGNORE = [
    ".git/**",
    ".venv/**",
    "**/__pycache__/**",
    "*.pyc",
    "eval/*/runs/**",
    "eval/*/readouts/**",
    "eval/*/results/**",  # readouts written before they moved to readouts/
    "eval/*/tests/**",
    "modal_downloads/**",
    # analysis/stats.py's output and jobs files at the repository root
    "analysis/out/**",
    "jobs/**",
    ".env",
    ".env.*",
    "**/*.env",
    "*.log",
]

image = (
    modal.Image.from_dockerfile(DOCKERFILE, add_python="3.12")
    .apt_install("util-linux")
    .uv_sync(
        str(REPO_ROOT), frozen=True, extra_options="--no-dev", uv_version="0.11.21"
    )
    # merge_queue's fixture builder commits on the seeded Jinja clones and its CI venv is made
    # with `uv`; the identity is fictional and never shown to a seat as the operator.
    .run_commands(
        "ln -sf /.uv/uv /usr/local/bin/uv",
        "git config --global user.email 'release-bot@example.invalid'",
        "git config --global user.name 'Release Bot'",
        "git config --global init.defaultBranch main",
    )
    .env(
        {
            "EVAL_PI_CMD": REMOTE_PI,
            "EVAL_MQ_AGENT_ROOTS": "/scratch/work_mq",
        }
    )
    .add_local_dir(REPO_ROOT, str(REMOTE_REPO), copy=True, ignore=_IGNORE)
)

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(
    VOLUME_NAME, create_if_missing=True, environment_name=VOLUME_ENV
)
# Volume files do not support distributed locks. Dict.put(if_not_exists) is one
# server-side conditional update, shared by every app writing to this Volume.
CLAIMS_NAME = os.environ.get("EVAL_MODAL_CLAIMS", "mamubench-episode-claims")
episode_claims = modal.Dict.from_name(
    CLAIMS_NAME, create_if_missing=True, environment_name=VOLUME_ENV
)


def secret_env() -> dict[str, str | None]:
    """The launch Secret's variables: the keys, the forwarded knobs, the revision, a nonce."""
    return {
        **{name: os.environ[name] for name in KEY_VARS if os.environ.get(name)},
        **(
            {os.environ["EVAL_KEY_ENV"]: os.environ.get(os.environ["EVAL_KEY_ENV"], "")}
            if os.environ.get("EVAL_KEY_ENV")
            else {}
        ),
        **{name: os.environ[name] for name in FORWARDED_KNOBS if os.environ.get(name)},
        "EVAL_GIT_SHA": _git_sha(),
        # Ephemeral secrets with identical contents are deduplicated across apps; stopping one app
        # then deleted the secret from under the launches still using it ("failed to resolve
        # secret ... does not exist"). A per-launch nonce keeps every launch's own.
        "EVAL_LAUNCH_ID": uuid.uuid4().hex,
    }


secret = modal.Secret.from_dict(secret_env())


def _bootstrap_remote() -> None:
    for path in (
        REMOTE_REPO / "eval" / "_harness",
        REMOTE_REPO,
        REMOTE_REPO / "eval",
    ):
        sys.path.insert(0, str(path))


def _eval_main(eval_name: str) -> Any:
    """`eval/<eval_name>/run.py`'s `main` (the eval's own CLI)."""
    _bootstrap_remote()
    if eval_name not in EVALS:
        raise ValueError(f"unknown eval {eval_name!r}")
    return importlib.import_module(f"{eval_name}.run").main


@app.function(  # pyright: ignore[reportUnknownMemberType] - Modal decorator stub
    image=image,
    secrets=[secret],
    timeout=600,
    cpu=1.0,
    memory=1024,
)
def probe_image() -> dict[str, Any]:
    """Attest the image: pi pin, node, python, and every eval's registry importing (no model call)."""
    _bootstrap_remote()
    from _harness import pi_rpc

    pi_rpc.validate_runtime()
    out: dict[str, Any] = {
        "pi": pi_rpc.pi_version(),
        "node": subprocess.run(
            ["node", "--version"], capture_output=True, text=True
        ).stdout.strip(),
        "python": sys.version.split()[0],
        "git_sha": os.environ.get("EVAL_GIT_SHA"),
    }
    for eval_name in EVALS:
        rc = _eval_main(eval_name)(["--list"])
        out[f"{eval_name}_list_rc"] = rc
    return out


@app.function(  # pyright: ignore[reportUnknownMemberType] - Modal decorator stub
    image=image,
    volumes={str(VOLUME_MOUNT): volume},
    secrets=[secret],
    timeout=EPISODE_TIMEOUT_S,
    cpu=CPU,
    memory=MEMORY_MB,
    max_containers=MAX_CONTAINERS,
    retries=_RETRIES,
    single_use_containers=True,
    nonpreemptible=NONPREEMPTIBLE,
)
def run_episode(
    eval_name: str,
    scenario: str,
    formation: str,
    epoch: int,
    model: str,
    provider: str,
    runs_name: str,
    extra: list[str],
    mitigation: str = NO_MITIGATION,
) -> dict[str, Any]:
    """Run (or resume-skip) exactly one episode: the eval's own CLI against the Volume."""
    return _run_one(
        eval_name,
        scenario,
        formation,
        epoch,
        model,
        provider,
        runs_name,
        extra,
        mitigation,
    )


@app.function(  # pyright: ignore[reportUnknownMemberType] - Modal decorator stub
    image=image,
    volumes={str(VOLUME_MOUNT): volume},
    secrets=[secret],
    timeout=EPISODE_TIMEOUT_S,
    cpu=MQ_CPU,
    memory=MQ_MEMORY_MB,
    max_containers=MAX_CONTAINERS,
    retries=_RETRIES,
    single_use_containers=True,
    nonpreemptible=NONPREEMPTIBLE,
)
def run_episode_mq(
    eval_name: str,
    scenario: str,
    formation: str,
    epoch: int,
    model: str,
    provider: str,
    runs_name: str,
    extra: list[str],
    mitigation: str = NO_MITIGATION,
) -> dict[str, Any]:
    """The heavy shape of `run_episode`: merge_queue (git + pytest per seat) and clinic meshfull mornings."""
    return _run_one(
        eval_name,
        scenario,
        formation,
        epoch,
        model,
        provider,
        runs_name,
        extra,
        mitigation,
    )


def claim_key_for(
    eval_name: str,
    runs_name: str,
    model: str,
    scenario: str,
    formation: str,
    epoch: int,
    mitigation: str = NO_MITIGATION,
    *,
    volume_id: str,
) -> str:
    """The episode's key in the claims Dict (one writer per episode across every launch).

    A runs root holds every model, so the model (as its run dirs spell it) is part of the key; the launchers pass
    canonical model, scenario and formation names only. A mitigation arm is part of the episode (its own run
    dir), so it is appended.
    """
    parts: list[Any] = [
        volume_id,
        eval_name,
        os.path.normpath(runs_name),
        path_safe_model(model),
        scenario,
        formation,
        epoch,
    ]
    if mitigation != NO_MITIGATION:
        parts.append(mitigation)
    return json.dumps(parts, separators=(",", ":"))


def _run_one(
    eval_name: str,
    scenario: str,
    formation: str,
    epoch: int,
    model: str,
    provider: str,
    runs_name: str,
    extra: list[str],
    mitigation: str = NO_MITIGATION,
) -> dict[str, Any]:
    claim_key = claim_key_for(
        eval_name,
        runs_name,
        model,
        scenario,
        formation,
        epoch,
        mitigation,
        volume_id=volume.object_id,
    )
    owner = {
        "token": uuid.uuid4().hex,
        "function_call_id": modal.current_function_call_id(),
        "input_id": modal.current_input_id(),
        "started": dt.datetime.now(dt.UTC).isoformat(),
    }
    _acquire_claim(claim_key, owner)
    safe_to_release = True
    try:
        main = _eval_main(eval_name)
        volume.reload()
        # Once evaluation starts, retain the claim unless all artifact cleanup
        # and the final Volume commit complete, including on exception paths.
        safe_to_release = False
        try:
            return _run_claimed(
                main,
                eval_name,
                scenario,
                formation,
                epoch,
                model,
                provider,
                runs_name,
                extra,
                mitigation,
            )
        finally:
            runs_root = VOLUME_MOUNT / eval_name / runs_name
            if eval_name == "merge_queue":
                _pack_merge_queue_workspaces(
                    runs_root, scenario, formation, epoch, model, mitigation
                )
            _commit_with_retry()
            safe_to_release = True
    finally:
        if safe_to_release:
            episode_claims.pop(claim_key)
        else:
            _mark_retained(claim_key, owner)


def _acquire_claim(claim_key: str, owner: dict[str, Any]) -> None:
    """Take the episode's claim, or raise `CLAIM_CONFLICT` without touching a file.

    A restart of the SAME input (a preemption: Modal restarts the input while the preempted container still packs,
    commits and releases in its shutdown window) waits up to `CLAIM_WAIT_S` for its own earlier attempt to release
    the claim, then takes it. Any other holder, a claim its owner retained after a failed teardown
    (`_mark_retained`), or a wait that runs out raises at once: once its worker has stopped and no launch is running,
    clear the Dict (`modal dict clear`) and relaunch.
    """
    deadline = time.monotonic() + CLAIM_WAIT_S
    announced = False
    vanished = 0
    while not episode_claims.put(claim_key, owner, skip_if_exists=True):
        prior: Any = episode_claims.get(claim_key)
        if prior is None and vanished < 5:
            vanished += 1  # released between the two calls: try to take it again
            continue
        restart = (
            isinstance(prior, dict)
            and owner.get("input_id") is not None
            and cast(dict[str, Any], prior).get("input_id") == owner["input_id"]
            and not cast(dict[str, Any], prior).get("retained")
        )
        if not restart or time.monotonic() >= deadline:
            waited = (
                f" after waiting {CLAIM_WAIT_S} s for this input's earlier attempt"
                if announced
                else ""
            )
            raise RuntimeError(
                f"{CLAIM_CONFLICT} in Modal Dict {CLAIMS_NAME!r}: "
                f"key={claim_key!r}, owner={prior!r}{waited}. No files were touched. "
                "Do not remove a claim until its worker has stopped; then, while no launch is running, clear the Dict "
                f"(`{MODAL_CLI} dict clear{f' --env {VOLUME_ENV}' if VOLUME_ENV else ''} {CLAIMS_NAME} -y`) "
                "and relaunch."
            )
        if not announced:
            print(
                f"the claim {claim_key} is held by this input's interrupted attempt (a restart after a "
                f"preemption); waiting up to {CLAIM_WAIT_S} s for it to be released",
                flush=True,
            )
            announced = True
        time.sleep(CLAIM_POLL_S)


def _mark_retained(claim_key: str, owner: dict[str, Any]) -> None:
    """Record on a claim its owner keeps (teardown or the final commit failed), so no restart waits for it."""
    try:
        episode_claims.put(
            claim_key,
            {**owner, "retained": "teardown or the final Volume commit failed"},
        )
    except Exception as exc:  # noqa: BLE001 - best effort on a failure path; the claim itself stays either way
        print(f"could not mark the retained claim {claim_key}: {exc!r}", flush=True)


def _run_claimed(
    main: Any,
    eval_name: str,
    scenario: str,
    formation: str,
    epoch: int,
    model: str,
    provider: str,
    runs_name: str,
    extra: list[str],
    mitigation: str = NO_MITIGATION,
) -> dict[str, Any]:
    runs_root = VOLUME_MOUNT / eval_name / runs_name
    argv = [
        SELECT_FLAG[eval_name],
        scenario,
        "--formation",
        formation,
        "--epoch0",
        str(epoch),
        "--episodes",
        "1",
        "--model",
        model,
        "--provider",
        provider,
        "--runs-root",
        str(runs_root),
        *extra,
    ]
    if mitigation != NO_MITIGATION:
        argv += ["--mitigation", mitigation]
    if eval_name != "merge_queue":
        # A Modal Volume budgets FILES (500k inodes): the seat trees of a banked episode travel as
        # one tarball (merge_queue packs its own below).
        argv.append("--pack-workspaces")
    try:
        rc = int(main(argv))
    except SystemExit as exc:  # an eval CLI exit (argparse, a refused resume, ...) is a result, not a crash
        rc = exc.code if isinstance(exc.code, int) else 1
        print(f"eval exited: {exc.code}", flush=True)
    return {
        "eval": eval_name,
        "scenario": scenario,
        "formation": formation,
        "epoch": epoch,
        "model": model,
        "mitigation": mitigation,
        "rc": rc,
    }


def _pack_merge_queue_workspaces(
    runs_root: Path,
    scenario: str,
    formation: str,
    epoch: int,
    model: str,
    mitigation: str = NO_MITIGATION,
) -> None:
    """Tar this episode's seat workspaces (`agents/`, `node/`, quarantined attempts) before the commit.

    A merge-queue run dir holds real git clones per seat (tens of thousands of small files); the
    Volume commit of that tree fails (`DataLossError: failed to publish commit to server`, observed on
    the first Modal episode) and the volume's inode budget is finite. The record the report reads
    (`DONE.json`, `episode.json`, `service/`, `turns.jsonl`, `voicer.jsonl`) stays as files; the
    workspaces travel as one `workspaces.tar.gz` beside them.

    A quarantined attempt of an earlier container (a preemption: its own teardown packed it) holds that
    container's `workspaces.tar.gz`; its members are flattened into the new archive under the attempt's
    directory, so every attempt's seat sessions sit at one level of one archive (`_flatten_attempt_archives`).
    """
    import shutil

    from merge_queue.run import run_dir_name

    run_dir = runs_root / run_dir_name(scenario, formation, model, epoch, mitigation)
    if not run_dir.is_dir():
        return
    bulky = [
        p
        for p in run_dir.iterdir()
        if p.name in ("agents", "node") or p.name.startswith(".attempt")
    ]
    if not bulky:
        return
    archive = run_dir / ARCHIVE_NAME
    with tarfile.open(archive, "w:gz") as tar:
        for path in bulky:
            nested = path / ARCHIVE_NAME
            if not (path.name.startswith(".attempt") and nested.is_file()):
                tar.add(path, arcname=path.name)
                continue
            skip = f"{path.name}/{ARCHIVE_NAME}"

            def without_nested(
                info: tarfile.TarInfo, skip: str = skip
            ) -> tarfile.TarInfo | None:
                return None if info.name == skip else info

            tar.add(path, arcname=path.name, filter=without_nested)
            _flatten_attempt_archives(tar, nested, path.name)
    for path in bulky:
        shutil.rmtree(path, ignore_errors=True)
    print(
        f"packed {len(bulky)} workspace tree(s) of {run_dir.name} into {archive.name}",
        flush=True,
    )


def _flatten_attempt_archives(tar: tarfile.TarFile, nested: Path, prefix: str) -> None:
    """Copy every member of `nested` (an earlier container's archive) into `tar` under `prefix/`.

    Each member is read whole before it is written, so an unreadable (truncated) archive never leaves a partial
    member in `tar`; from the first unreadable member on, the archive itself is kept as a file instead.
    """
    try:
        with tarfile.open(nested, "r:gz") as inner:
            for member in inner:
                handle = inner.extractfile(member) if member.isfile() else None
                data = io.BytesIO(handle.read()) if handle is not None else None
                member.name = f"{prefix}/{member.name}"
                if member.islnk():
                    member.linkname = f"{prefix}/{member.linkname}"
                tar.addfile(member, data)
    except (tarfile.TarError, OSError, EOFError, zlib.error) as exc:
        print(
            f"could not unpack {nested.name} of {prefix} ({exc!r}); kept as a file",
            flush=True,
        )
        tar.add(nested, arcname=f"{prefix}/{ARCHIVE_NAME}")


@app.function(  # pyright: ignore[reportUnknownMemberType] - Modal decorator stub
    image=image,
    volumes={str(VOLUME_MOUNT): volume},
    timeout=1800,
    cpu=2.0,
    memory=4096,
)
def status(eval_name: str, runs_name: str) -> dict[str, Any]:
    """Count banked / in-flight run dirs under `/<eval>/<runs_name>` (read-only)."""
    volume.reload()
    root = VOLUME_MOUNT / eval_name / runs_name
    marker = "DONE.json"
    banked = inflight = 0
    per_model: dict[str, int] = {}
    per_mitigation: dict[str, int] = {}
    if not root.exists():
        return {
            "eval": eval_name,
            "runs": runs_name,
            "missing": True,
        }
    if eval_name == "personal_assistant":
        for sidecar in root.glob("*/worlds/*.json"):
            banked += 1
            wave = sidecar.parent.parent.name
            per_model[wave] = per_model.get(wave, 0) + 1
            arm = mitigation_of_name(wave)
            per_mitigation[arm] = per_mitigation.get(arm, 0) + 1
        inflight = sum(
            1
            for run_dir in root.glob("*/runs/*")
            if run_dir.is_dir() and not (run_dir / "workspaces.tar.gz").exists()
        )
    else:
        for run_dir in root.iterdir():
            if not run_dir.is_dir():
                continue
            if (run_dir / marker).exists():
                banked += 1
                model = (
                    run_dir.name.rsplit("__", 2)[-2]
                    if eval_name == "merge_queue"
                    else "-"
                )
                per_model[model] = per_model.get(model, 0) + 1
                arm = mitigation_of_name(run_dir.name)
                per_mitigation[arm] = per_mitigation.get(arm, 0) + 1
            else:
                inflight += 1
    return {
        "eval": eval_name,
        "runs": runs_name,
        "banked": banked,
        "inflight": inflight,
        "per_model": per_model,
        "per_mitigation": per_mitigation,
    }


def mitigation_of_name(name: str) -> str:
    """The arm a run-dir or wave-dir name is stamped with (`_mitigations.stamp`), `none` when unstamped."""
    if STAMP_PREFIX not in name:
        return NO_MITIGATION
    return name.split(STAMP_PREFIX, 1)[1].split("__", 1)[0]


@app.local_entrypoint()
def volume_status(eval: str, runs_name: str) -> None:
    """Banked / in-flight run dir counts for one runs root (see `status`)."""
    print(json.dumps(status.remote(eval, runs_name), indent=1))


def _commit_with_retry(attempts: int = 4) -> None:
    """Commit the Volume, retrying the many-containers commit race.

    `DataLossError('failed to publish commit to server')` is transient at 200+ concurrent containers
    (~1% of episodes in one run); retrying keeps a finished episode from being lost after running.
    """
    for attempt in range(1, attempts + 1):
        try:
            volume.commit()
            return
        except Exception as exc:  # noqa: BLE001 — modal.exception.DataLossError and friends
            if attempt == attempts:
                raise
            print(
                f"volume.commit attempt {attempt} failed: {exc!r}; retrying", flush=True
            )
            time.sleep(15 * attempt)


def _check_sim_timeout(
    eval_name: str,
    episodes: list[Any],
    *,
    print_info: bool = False,
) -> None:
    """Refuse a simulated-harness launch whose per-episode Modal timeout is shorter than its episodes may take.

    The function timeout is fixed when this module is imported (`EVAL_MODAL_TIMEOUT_S`); the root `run.py` sets it
    from the same computation (`_matrix.sim_timeout_s`). A container killed mid-episode banks nothing, and the long
    mornings and nights (a 16 h clinic team morning, a first pass followed by its long-limit retry) would then be
    dropped systematically instead of rerun.
    """
    from _harness.sim import EPISODE_MARGIN_S
    from _matrix import sim_timeout_s

    try:
        needed = sim_timeout_s(eval_name, episodes)
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    if EPISODE_TIMEOUT_S >= needed:
        return
    message = (
        f"EVAL_MODAL_TIMEOUT_S={EPISODE_TIMEOUT_S} is shorter than this simulated-harness launch "
        f"needs ({needed} s: its longest cell's sample time limit, plus the long-limit retry, plus "
        f"{EPISODE_MARGIN_S} s margin). Relaunch with EVAL_MODAL_TIMEOUT_S={needed} (run.py sets it "
        "automatically)"
    )
    if print_info:
        print(f"WARNING (a real launch would refuse): {message}", flush=True)
        return
    raise SystemExit(message)


def _job(
    eval_name: str,
    scenario: str,
    formation: str,
    epoch: int,
    model: str,
    provider: str,
    runs_name: str,
    extra: list[str],
    mitigation: str,
) -> tuple[Any, ...]:
    """One dispatch tuple for `run_episode.starmap`: its positional arguments.

    A control-arm job is an 8-tuple (`mitigation` defaults to `none`); a mitigation arm's job carries the arm as a
    9th element.
    """
    job: tuple[Any, ...] = (
        eval_name,
        scenario,
        formation,
        epoch,
        model,
        provider,
        runs_name,
        extra,
    )
    return job if mitigation == NO_MITIGATION else (*job, mitigation)


def _job_label(job: Sequence[Any]) -> str:
    """`[model scenario formation e<epoch>[ arm]]` of a dispatch tuple."""
    items = list(job)
    arm = items[8] if len(items) > 8 else NO_MITIGATION
    return f"[{items[4]} {items[1]} {items[2]} e{items[3]}{'' if arm == NO_MITIGATION else ' ' + arm}]"


def _poll(call: Any) -> tuple[bool, Any]:
    """`(finished, its result or the exception it raised)` of one episode call, without waiting."""
    try:
        return True, call.get(timeout=0)
    except (
        TimeoutError
    ) as exc:  # the builtin, raised with no argument while the call still runs
        if exc.args:
            return True, exc
        return False, None
    except Exception as exc:  # noqa: BLE001 - the episode's own failure (a claim conflict, a lost worker, ...)
        return True, exc


def new_lane(jobs: list[tuple[Any, ...]]) -> dict[str, Any]:
    """A lane's state before its first episode: every job to submit, on pass 1 of its episodes."""
    return {
        "stage": "episodes",
        "pass": 1,
        "todo": list(jobs),
        "pending": [],
        "failed": [],
        "done": 0,
        "conflicts": 0,
        "jobs": len(jobs),
        "failures": 0,
        "continuation": 0,
    }


def run_lane(
    jobs: list[tuple[Any, ...]],
    heavy: bool,
    eval_name: str,
    runs_name: str,
    launch_id: str,
    state: dict[str, Any],
    deadline: float,
) -> dict[str, Any]:
    """Play a lane from `state` until it is done or `deadline` (monotonic) passes; the lane's result either way.

    Each episode is its own `spawn`ed call, at most `DISPATCH_WINDOW` in flight. A pass ends when every submitted
    episode has returned; its failures are retried in the next pass (up to `DISPATCH_PASSES`, after a
    `CLAIM_WAIT_S` wait when some were claim conflicts). At `deadline` the lane spawns a continuation of `dispatch`
    with its state (the calls in flight by id) and returns `{"continued": <call id>}`. The progress file
    `<runs root>/_launch_<id>.json` is rewritten after every result (best effort; the episodes' own run dirs are the
    record).
    """
    runner = run_episode_mq if heavy else run_episode
    progress = VOLUME_MOUNT / eval_name / runs_name / f"_launch_{launch_id}.json"
    calls: dict[str, Any] = {
        call_id: modal.FunctionCall.from_id(call_id)
        for call_id, _job in state["pending"]
    }

    def write(finished: bool = False, **more: Any) -> None:
        record = {
            "stage": state["stage"],
            "pass": state["pass"],
            "done": state["done"],
            "failures": len(state["failed"]),
            "jobs": state["done"] + len(state["pending"]) + len(state["todo"]),
            "continuation": state["continuation"],
            "finished": finished,
            **more,
        }
        try:
            progress.parent.mkdir(parents=True, exist_ok=True)
            progress.write_text(json.dumps(record))
            _commit_with_retry()
        except Exception as exc:  # noqa: BLE001 - the progress file is a convenience, never the launch
            print(f"progress file not updated: {exc!r}", flush=True)

    def result() -> dict[str, Any]:
        out: dict[str, Any] = {"jobs": len(jobs), "failures": state["failures"]}
        out["unbanked"] = state["failures"]
        out["continuations"] = state["continuation"]
        return out

    write()
    while True:
        while (
            state["todo"]
            and len(state["pending"]) < DISPATCH_WINDOW
            and time.monotonic() < deadline
        ):
            job = tuple(state["todo"].pop(0))
            call = runner.spawn(*job)
            calls[call.object_id] = call
            state["pending"].append([call.object_id, job])
        if state["todo"] or state["pending"]:
            if time.monotonic() >= deadline:
                state["continuation"] += 1
                follower = dispatch.spawn(
                    jobs, heavy, eval_name, runs_name, launch_id, state
                )
                write(continued=follower.object_id)
                print(
                    f"handing the lane to continuation {state['continuation']} ({follower.object_id}): "
                    f"{len(state['todo'])} to submit, {len(state['pending'])} in flight",
                    flush=True,
                )
                return {"continued": follower.object_id, **result()}
            finished_any = False
            for entry in list(state["pending"]):
                call_id, job = entry
                finished, outcome = _poll(calls[call_id])
                if not finished:
                    continue
                finished_any = True
                state["pending"].remove(entry)
                calls.pop(call_id, None)
                state["done"] += 1
                if isinstance(outcome, BaseException):
                    state["failed"].append(job)
                    print(f"FAILED {_job_label(job)}: {outcome!r}", flush=True)
                    state["conflicts"] += CLAIM_CONFLICT in str(outcome)
                else:
                    if int(outcome["rc"]) != 0:
                        state["failed"].append(job)
                    print(
                        f"{_job_label(job)} rc={outcome['rc']} ({state['done']}/"
                        f"{state['done'] + len(state['pending']) + len(state['todo'])})",
                        flush=True,
                    )
                write()
            if not finished_any:
                time.sleep(DISPATCH_POLL_S)
            continue
        # the pass is over
        failed = list(state["failed"])
        print(
            f"{state['stage']} pass {state['pass']}: {state['done'] - len(failed)}/{state['done']} episodes "
            "completed on Modal",
            flush=True,
        )
        if failed and state["pass"] < DISPATCH_PASSES:
            print(
                f"pass {state['pass']}: {len(failed)} failed episode(s); retrying with validated resume",
                flush=True,
            )
            if state["conflicts"]:
                # a claim still held by a worker in its shutdown window (a preempted or stopped container)
                # fails every immediate retry; give it the time to pack, commit and release
                print(
                    f"pass {state['pass']}: {state['conflicts']} of them were claim conflicts; waiting "
                    f"{CLAIM_WAIT_S} s before the next pass",
                    flush=True,
                )
                time.sleep(CLAIM_WAIT_S)
            state.update(
                {
                    "pass": state["pass"] + 1,
                    "todo": failed,
                    "failed": [],
                    "done": 0,
                    "conflicts": 0,
                }
            )
            continue
        state["failures"] = len(failed)
        break
    state["pending"] = []
    write(finished=True)
    return result()


@app.function(  # pyright: ignore[reportUnknownMemberType] - Modal decorator stub
    image=image,
    volumes={str(VOLUME_MOUNT): volume},
    secrets=[secret],
    timeout=DISPATCH_TIMEOUT_S,
    cpu=1.0,
    memory=2048,
    nonpreemptible=NONPREEMPTIBLE,
)
def dispatch(
    jobs: list[tuple[Any, ...]],
    heavy: bool,
    eval_name: str,
    runs_name: str,
    launch_id: str,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One lane's dispatch loop, run INSIDE Modal (spawned by `main`): its episodes, with their retry passes.

    A client-driven `starmap` is cancelled with its client (one network blip on a launching box once cancelled
    every lane's in-flight episodes at once), so the loop runs here and the client may leave after the spawn.
    `state` is a continuation's (`run_lane`): the lane picks up where the previous call handed it over.
    """
    _bootstrap_remote()
    return run_lane(
        jobs,
        heavy,
        eval_name,
        runs_name,
        launch_id,
        state or new_lane(jobs),
        time.monotonic() + DISPATCH_HANDOFF_S,
    )


def follow_up(
    eval_name: str,
    runs_name: str,
    launch_ids: list[str],
    more: Sequence[str] = (),
    app_id: str | None = None,
) -> str:
    """The commands a detached launch prints: the app's logs and stop, each lane's progress, the counts, the pulls.

    `more` names the launch's other runs roots (the personal assistant's `context_files`). `app_id` is the launch's
    Modal app (`ap-...`): a detached run is followed and stopped by its id, not by its name. The Volume commands name
    the Volume's Modal environment whenever `EVAL_MODAL_VOLUME_ENV` pins one (as `pull` does), so they read the
    right Volume even when it lives in another environment than the app's. Every command is in the project-venv form
    (`MODAL_CLI`), ready to paste from the repository root.
    """
    env_flag = f" --env {VOLUME_ENV}" if VOLUME_ENV else ""
    app = app_id or "<app id: the ap-... at the end of Modal's `View run at` URL>"
    lines = [
        f"  {MODAL_CLI} app logs {app} -f   # live logs",
        f"  {MODAL_CLI} app stop {app} -y   # stop the run; rerunning the launch command resumes it",
    ]
    lines += [
        f"  {MODAL_CLI} volume get{env_flag} {VOLUME_NAME} {eval_name}/{runs_name}/_launch_{launch_id}.json -"
        for launch_id in launch_ids
    ]
    lines[2] += "   # each lane's progress, rewritten after every result"
    lines.append(
        f"  {MODAL_CLI} run eval/modal_app.py::volume_status --eval {eval_name} --runs-name {runs_name}"
        "   # banked / in-flight run dirs"
    )
    lines.append(
        'and once every lane reads "finished": true (a lane continues itself past Modal\'s 24 h limit):'
    )
    lines += [
        f"  {MODAL_CLI} run eval/modal_app.py::pull --eval {eval_name} --runs-name {name}"
        for name in (runs_name, *more)
    ]
    return "\n".join(lines)


def _split(value: str) -> list[str]:
    """A comma-separated option as a list (empty for "")."""
    return [item for item in value.split(",") if item]


@app.local_entrypoint()
def main(
    eval: str = "",
    model: str = "",
    formation: str = "",
    scenario: str = "",
    episodes: int = 0,
    mitigation: str = NO_MITIGATION,
    jobs_file: str = "",
    harness: str = "",
    runs_name: str = "",
    extra: str = "",
    fake_pi: bool = False,
    fake_model: bool = False,
    spawn_driver: bool = False,
    print_info: bool = False,
    probe: bool = False,
) -> None:
    """Fan one environment's plan out over Modal containers, one dispatch lane per model.

    The plan is the root `run.py`'s (`eval/_matrix.py`): the paper's runs of `--eval` (or of `--mitigation`'s
    arm), narrowed by the comma-separated `--model`, `--formation` and `--scenario` and by `--episodes` (per
    cell), or `--jobs-file`'s episodes; the personal assistant's paper runs chain their AGENTS.md-in-context rerun
    (`_matrix.launch_roots`). `--harness sim` (the default for api_key / clinic) plays the simulated harness,
    `--fake-model` its offline stand-in, `--fake-pi` the pi harness's. `--spawn-driver` (with `modal run --detach`)
    returns once the lanes are spawned; without it the client waits for them (and their continuations).
    `--print-info` prints the plan and dispatches nothing (useful before an expensive eval).
    """
    if probe:
        if print_info:
            print("Would probe the pinned pi image and all four registries")
        else:
            print(json.dumps(probe_image.remote(), indent=1))
        return
    if eval not in EVALS:
        raise SystemExit(f"--eval must be one of {EVALS}")
    if not harness:
        # The paper's harness by default; the pi harness's stand-in selects the pi harness.
        harness = "sim" if eval in ("api_key", "clinic") and not fake_pi else "pi"
    if harness not in ("pi", "sim"):
        raise SystemExit("--harness must be pi or sim")
    if harness == "sim" and eval not in ("api_key", "clinic"):
        raise SystemExit("--harness sim exists for api_key and clinic only")
    if fake_model and harness != "sim":
        raise SystemExit(
            "--fake-model is the simulated harness's stand-in (add --harness sim)"
        )
    if fake_pi and harness != "pi":
        raise SystemExit("--fake-pi requires --harness pi; use --fake-model with sim")
    if fake_pi and eval == "merge_queue":
        raise SystemExit(
            "merge_queue has no --fake-pi; use its offline fixture/driver smoke"
        )
    if episodes < 0:
        raise SystemExit("--episodes must be positive")
    if runs_name and (Path(runs_name).name != runs_name or runs_name in (".", "..")):
        raise SystemExit("--runs-name must be a single directory name")
    formations = _split(formation)
    if set(formations) - set(FORMATIONS):
        raise SystemExit(f"--formation must name {', '.join(FORMATIONS)}")
    if jobs_file and (_split(scenario) or formations or episodes):
        raise SystemExit(
            "--jobs-file lists every episode; drop --scenario / --formation / --episodes"
        )
    extra_args = shlex.split(extra)
    # Keep plan and harness selectors visible to validation instead of allowing --extra to override them after the
    # plan has been resolved.
    controlled = {
        "--harness",
        "--fake-pi",
        "--fake-model",
        "--model",
        "--provider",
        "--scenario",
        "--board",
        "--all",
        "--seats",
        "--twin",
        "--hero",
        "--safety",
        "--formation",
        "--episodes",
        "--epoch0",
        "--runs-root",
        "--mitigation",
        "--jobs-file",
        "--list-mitigations",
        # `--print-info` and its local rendering: every container would plan and bank nothing
        "--print-info",
        "--render-to",
    }
    # `--epochs` is not an option (episodes per cell is `--episodes`); every container's runner would refuse it
    if any(arg.split("=", 1)[0] == "--epochs" for arg in extra_args):
        raise SystemExit(
            "unknown option --epochs in --extra (episodes per cell is --episodes)"
        )
    # `--dry-run` is not an option (printing what a launch would do without running it is `--print-info`), nor is an
    # abbreviation argparse would read as it; every container's runner would refuse it
    if any(
        len(name := arg.split("=", 1)[0]) > 2 and "--dry-run".startswith(name)
        for arg in extra_args
    ):
        raise SystemExit(
            "unknown option --dry-run in --extra (printing what a launch would do without running it is "
            "--print-info)"
        )
    if any(
        arg.startswith("--")
        and any(flag.startswith(arg.split("=", 1)[0]) for flag in controlled)
        for arg in extra_args
    ):
        raise SystemExit("pass plan/harness/fake options directly, not through --extra")
    # the eval registries resolve and validate the plan on this machine
    from _paths import bootstrap

    bootstrap()
    import _matrix
    from _providers import provider_for

    fake = fake_pi or fake_model
    stand_ins = [
        flag
        for flag, on in (("--fake-pi", fake_pi), ("--fake-model", fake_model))
        if on
    ]
    try:
        roots = _matrix.launch_roots(
            eval,
            models=_split(model),
            formations=formations,
            scenarios=_split(scenario),
            epochs=episodes or None,
            mitigation=mitigation or NO_MITIGATION,
            jobs_file=Path(jobs_file) if jobs_file else None,
            harness=harness,
            extra=[*extra_args, *stand_ins],
            runs_name=runs_name or None,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    if not roots[0].episodes:
        raise SystemExit(
            "nothing to run: "
            + _matrix.nothing_to_run(
                eval,
                mitigation=mitigation or NO_MITIGATION,
                jobs_file=Path(jobs_file) if jobs_file else None,
                extra=[*extra_args, *stand_ins],
            )
        )
    name = roots[0].name
    planned = [e for root in roots for e in root.episodes]
    if fake_pi:
        extra_args.append("--fake-pi")
    if eval in ("api_key", "clinic"):
        # Always explicit: the eval CLIs default to sim, and an episode must never guess its harness.
        extra_args += ["--harness", harness]
    if fake_model:
        extra_args.append("--fake-model")
    if harness == "sim" and not fake_model:
        # The offline stand-in plays a whole episode in seconds, far inside any timeout.
        _check_sim_timeout(eval, planned, print_info=print_info)
    if os.environ.get("EVAL_KEY_ENV"):
        extra_args += ["--key-env", os.environ["EVAL_KEY_ENV"]]
    models = list(dict.fromkeys(e.model for e in planned))
    for root in roots:
        print(
            _matrix.summary(
                eval,
                root.episodes,
                f"volume {VOLUME_NAME}:/{eval}/{root.name}",
                note=" (AGENTS.md in context)"
                if "--context-files" in root.options
                else "",
            ),
            flush=True,
        )
    print(
        f"  harness {harness}, max {MAX_CONTAINERS} containers, one dispatch lane per model",
        flush=True,
    )
    if print_info:
        for root in roots:
            for e in root.episodes:
                arm = (
                    ""
                    if e.mitigation == NO_MITIGATION
                    else f" mitigation={e.mitigation}"
                )
                print(
                    f"  {e.model:18} {e.scenario:34} {e.formation:12} e{e.epoch}{arm}"
                    + (f" -> {root.name}" if len(roots) > 1 else "")
                )
        return
    if not fake:
        refusal = _matrix.missing_keys(eval, models, harness, os.environ, extra_args)
        if refusal:
            raise SystemExit(refusal)
    heavy = (
        eval == "merge_queue"
        or (
            eval == "clinic"
            and harness == "pi"
            and any(e.formation in ("team", "team_silent") for e in planned)
        )
    )  # merge_queue: git + pytest per seat; clinic pi team: 17-52 pi processes per morning
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lanes: list[tuple[str, Any]] = []
    for lane_model in models:
        provider = provider_for(lane_model)
        jobs = [
            _job(
                eval,
                e.scenario,
                e.formation,
                e.epoch,
                lane_model,
                provider,
                root.name,
                [*extra_args, *root.options],
                e.mitigation,
            )
            for root in roots
            for e in root.episodes
            if e.model == lane_model
        ]
        launch_id = f"{stamp}__{path_safe_model(lane_model)}"
        lanes.append((launch_id, dispatch.spawn(jobs, heavy, eval, name, launch_id)))
    more = [root.name for root in roots[1:]]
    if spawn_driver:
        print(
            f"spawned {len(lanes)} dispatch lane(s) on Modal ({len(planned)} episodes; needs `modal run --detach`) "
            f"in app {app.app_id}. Follow it with:\n"
            + follow_up(
                eval,
                name,
                [launch_id for launch_id, _ in lanes],
                more,
                app.app_id,
            )
            + "\nModal's closing `App completed` refers only to this launcher: the app keeps running and stops by "
            "itself once every lane is finished.",
            flush=True,
        )
        return
    unbanked = 0
    for launch_id, call in lanes:
        result = cast(dict[str, Any], call.get())
        while (
            "continued" in result
        ):  # the lane handed itself over before Modal's 24 h limit
            result = cast(
                dict[str, Any], modal.FunctionCall.from_id(result["continued"]).get()
            )
        print(f"lane {launch_id}: {json.dumps(result)}", flush=True)
        unbanked += int(result.get("unbanked", 0))
    pulls = "\n".join(
        f"  {MODAL_CLI} run eval/modal_app.py::pull --eval {eval} --runs-name {n}"
        for n in (name, *more)
    )
    print(f"Pull with:\n{pulls}", flush=True)
    if unbanked:
        raise SystemExit(1)


@app.local_entrypoint()
def pull(eval: str, runs_name: str, dest: str = "") -> None:
    """Download `<eval>/<runs_name>` from the Volume into `eval/<eval>/runs/<runs_name>` (or `dest/<runs_name>`)."""
    if eval not in EVALS:
        raise SystemExit(f"--eval must be one of {EVALS}")
    # `modal volume get` places the remote folder INSIDE an existing local directory; `--force`
    # overwrites (and mirrors) a partial earlier pull of the same folder.
    parent = Path(dest) if dest else EVALS_DIR / eval / "runs"
    parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 4):
        argv = [sys.executable, "-m", "modal", "volume", "get"]
        if VOLUME_ENV:
            argv += ["--env", VOLUME_ENV]
        if (
            parent / runs_name
        ).exists():  # a partial earlier pull: overwrite (mirror) it
            argv.append("--force")
        argv += [VOLUME_NAME, f"{eval}/{runs_name}", str(parent)]
        proc = subprocess.run(argv, capture_output=True, text=True)
        if proc.returncode == 0:
            break
        # The Volume file-listing API is rate limited; a listing that trips it is retried.
        print(
            f"pull attempt {attempt} failed: {proc.stderr.strip()[-300:]}", flush=True
        )
        if attempt == 3:
            env_flag = f" --env {VOLUME_ENV}" if VOLUME_ENV else ""
            print(
                f"giving up: `modal volume get{env_flag} {VOLUME_NAME} {eval}/{runs_name}` failed. "
                "If the Volume lives in another Modal environment, set EVAL_MODAL_VOLUME_ENV=<env> "
                "(passed to `modal volume get` as `--env`) and retry.",
                flush=True,
            )
            raise SystemExit(proc.returncode)
        time.sleep(30)
    print(f"-> {parent / runs_name}")
