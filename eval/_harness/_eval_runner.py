"""Resumable eval runner shared by the simulated harness's drivers.

Three capabilities the bare `inspect_ai.eval()` lacks:

1. **Preempt + resume.** `run_resumable` drives `inspect_ai.eval_set` against a stable `log_dir`. Kill a launched run (Ctrl-C / SIGINT) and re-invoke the *same* command: `eval_set` reuses every completed sample from the logs and runs only the remainder. Resume granularity is one audit (sample) — an audit that was mid-conversation at preemption restarts from scratch; finished audits never re-run.

2. **Per-role API keys.** The `KEYS` env var names the env var holding each model role's key: comma-separated `role:VAR` pairs, a `*` role setting the default for roles not listed. Roles absent from `KEYS` (with no `*`) keep the ambient `ANTHROPIC_API_KEY`. The simulated harness sets it per episode:

    KEYS="*:EVAL_SIM_API_KEY"                                    # every role on the target's key
    KEYS="auditor:EVAL_SIM_HOUSE_KEY,judge:EVAL_SIM_HOUSE_KEY"   # the house roles only

   Each role bound to a distinct key gets its own provider connection pool.

3. **Failed-attempt retention.** `run_resumable` defaults `retry_cleanup=False` so failed-attempt logs are kept for forensics (disk cost ~1MB per attempt; logs are gitignored). Aggregators that glob a log dir therefore see multiple `.eval` files per task and must dedup via `latest_logs_per_task`.

4. **Bounded stalls.** inspect retries retryable API failures forever by default, which turns a sustained outage into an indefinitely hung run. `run_resumable` defaults `GenerateConfig.timeout` (the per-generate total retry budget) to 1 hour so a stalled call becomes a visible, retryable sample error instead. Tune or disable via `PETRI_GENERATE_TIMEOUT` (seconds; `0` disables). `PETRI_SAMPLE_TIME_LIMIT` (seconds; unset/`0` = none) likewise bounds each SAMPLE's total wall-clock so a wedged episode dies retryable instead of squatting on a worker slot — but unlike `timeout` it is PART of eval_set task identity: pick it when a wave starts and hold it constant, because changing it mid-campaign re-keys the tasks and a resume then ignores the completed logs.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from _metadata_sidecar import METADATA_SIDECAR_DIR_ENV, read_metadata_sidecar
from _multiagent_pi.roles import ADAPTIVE_THINKING_MAX_TOKENS
from inspect_ai import eval_set
from inspect_ai.log import EvalSample, read_eval_log, read_eval_log_samples
from inspect_ai.model import GenerateConfig, Model, get_model


def _resolve_key(token: str) -> str:
    """The API-key value of a `KEYS` token (the name of the env var holding it)."""
    value = os.environ.get(token)
    if not value:
        raise ValueError(f"KEYS token {token!r}: the env var is empty/unset")
    return value


def _key_distribution() -> dict[str, str]:
    """Parse the `KEYS` env var into a {role: token} map (`*` = default for unlisted roles)."""
    out: dict[str, str] = {}
    for raw in os.environ.get("KEYS", "").split(","):
        part = raw.strip()
        if not part:
            continue
        role, sep, token = part.partition(":")
        if not sep or not token.strip():
            raise ValueError(f"KEYS entry {part!r} is not in 'role:key' form")
        out[role.strip()] = token.strip()
    return out


def resolve_role_key(role: str, *, default_env: str = "ANTHROPIC_API_KEY") -> str:
    """The raw API-key string a role authenticates with, honoring `KEYS` (its token, else `*`).

    Mirrors `keyed_roles`' key selection but returns the raw key string instead of a bound `Model` — for a role whose process is NOT an inspect model (e.g. a `pi` subprocess that needs `ANTHROPIC_API_KEY` in its own environment). Falls back to `default_env` when the role and `*` are both absent from `KEYS`. Raises `ValueError` if the resolved key is empty/unset, since a silent empty key surfaces only as an opaque downstream auth failure.
    """
    dist = _key_distribution()
    token = dist.get(role, dist.get("*"))
    if token:
        return _resolve_key(token)
    value = os.environ.get(default_env, "")
    if not value.strip():
        raise ValueError(f"no API key for role {role!r}: {default_env} is empty/unset")
    return value.strip()


def _env_generate_timeout(default: int = 3600) -> int:
    """`PETRI_GENERATE_TIMEOUT` seconds (empty/`0` disables) — one empty-safe parse for every reader.

    `_multiagent_pi.roles.role_model` keeps its own parse with a deliberate 900 s fail-fast default; a caller unifying them should pass `default=900` there rather than assume parity.
    """
    raw = os.environ.get("PETRI_GENERATE_TIMEOUT")
    return default if raw is None else int(raw.strip() or "0")


#: The `reasoning_effort` values `GenerateConfig` accepts (inspect's literal, incl. the explicit-off `none`).
_REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


def target_model(model_id: str) -> str | Model:
    """The target role's model binding, honoring the `TARGET_REASONING` env dial.

    Unset (the default) returns `model_id` unchanged — the corpus convention: a string-bound target runs at its provider's default reasoning behavior. Set `TARGET_REASONING` to one of `GenerateConfig`'s `reasoning_effort` values (`none` sends no thinking parameter) to pre-bind the target with that effort, plus the same caps `_multiagent_pi.roles.role_model` pins on pre-bound roles (`ADAPTIVE_THINKING_MAX_TOKENS`, `MAX_CONNECTIONS`, `PETRI_GENERATE_TIMEOUT`) — eval-level config does not reach a pre-bound model. Anthropic targets resolve their key from `KEYS` via `resolve_role_key("target")`; other providers read their own ambient env key (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, ...), exactly like `keyed_roles`' string path.
    """
    effort = os.environ.get("TARGET_REASONING", "").strip()
    if not effort:
        return model_id
    if effort not in _REASONING_EFFORTS:
        raise ValueError(f"TARGET_REASONING {effort!r} not one of {_REASONING_EFFORTS}")
    cfg_kw: dict[str, Any] = {
        "reasoning_effort": effort,
        "max_tokens": ADAPTIVE_THINKING_MAX_TOKENS,
        "max_connections": int(os.environ.get("MAX_CONNECTIONS", "12")),
    }
    gen_timeout = _env_generate_timeout()
    if gen_timeout > 0:
        cfg_kw["timeout"] = gen_timeout
    key = resolve_role_key("target") if model_id.startswith("anthropic/") else None
    model_args: dict[str, Any] = {}
    if model_id.startswith("openrouter/openai/"):
        # As `_multiagent_pi.roles.role_model`: OpenAI routes validate function schemas in strict mode
        # when inspect's default strict_tools=True rides along, and the pi tools declare optional
        # params outside `required`, which strict mode rejects wholesale.
        model_args["strict_tools"] = False
    return get_model(
        model_id,
        config=GenerateConfig(**cfg_kw),
        api_key=key,
        memoize=False,
        **model_args,
    )


def keyed_roles(base: Mapping[str, str | Model]) -> dict[str, str | Model]:
    """Apply the `KEYS` distribution to a {role: model} mapping.

    Roles assigned a key become a `Model` bound to that key; the rest are returned as their original model string (resolved with the ambient `ANTHROPIC_API_KEY`). A role that is already a bound `Model` (e.g. `target_model` under `TARGET_REASONING`) passes through untouched — its key and config were attached at bind time.
    """
    dist = _key_distribution()
    default = dist.get("*")
    roles: dict[str, str | Model] = {}
    for role, model in base.items():
        if isinstance(model, Model):
            roles[role] = model
            continue
        token = dist.get(role, default)
        # memoize=False so each role gets a DISTINCT Model instance even when several roles
        # share the same (model, key) — e.g. KEYS="*:EVAL_SIM_API_KEY" with one model for auditor,
        # target, and judge. get_model memoizes by (model, key), and inspect tags a per-role `.role`
        # on the returned object; a shared instance has its `.role` overwritten to the last
        # role bound, so every generation (incl. the target's) is mistagged and the session
        # judge sees "no target sessions". Distinct instances keep each role's tag correct.
        roles[role] = (
            get_model(model, api_key=_resolve_key(token), memoize=False)
            if token
            else model
        )
    return roles


def run_resumable(
    tasks: Any,
    *,
    log_dir: str,
    roles: Mapping[str, str | Model],
    label: str = "",
    keep_alive: bool = True,
    metadata_sidecars: Mapping[str, type[Any]] | None = None,
    **eval_kw: Any,
) -> bool:
    """Run `tasks` resumably under `log_dir`, with per-role keys from `KEYS`.

    `roles` maps role -> model string (e.g. `{"auditor": ..., "target": ..., "judge": ...}`) or an already-bound `Model` (e.g. `target_model` under `TARGET_REASONING`, which `keyed_roles` passes through); the auditor's (possibly key-bound) model is also used as the set's default model. Re-invoking with the same `log_dir` resumes: completed samples are reused, the remainder runs on whatever `KEYS` currently names.

    `metadata_sidecars` declares large ground-truth metadata fields and their expected JSON value types (for example `{"world": dict}`). Each declared field is required on every clean sample in the run. The runner enables task-side sidecar writes, refuses to resume completed samples that do not already have sidecars, and validates every clean sample after the run. Durability failures always propagate, including when `keep_alive=True`. This preflight is intentional: restarting a sidecar-less wave can be the operation that irreversibly replaces its intact metadata with Inspect's thinned summary placeholder. Backfill sidecars before enabling this option on an existing run.

    Returns `eval_set`'s success flag. On an unexpected error it logs and returns `False` when `keep_alive` (so a multi-phase campaign survives one phase failing); pass `keep_alive=False` to let the caller handle the exception.
    """
    keyed = keyed_roles(roles)
    default_model = keyed.get("auditor")
    apply_env_eval_defaults(eval_kw)
    eval_kw.setdefault("retry_cleanup", False)
    if metadata_sidecars:
        assert_metadata_sidecars(log_dir, metadata_sidecars, before_resume=True)
    try:
        with metadata_sidecar_directory(log_dir if metadata_sidecars else None):
            success, _ = eval_set(
                tasks,
                log_dir=log_dir,
                model=default_model,
                model_roles=keyed,
                **eval_kw,
            )
    except Exception as ex:
        if not keep_alive:
            raise
        tag = f" [{label}]" if label else ""
        print(
            f"!!! eval_set{tag} ({log_dir}) raised {type(ex).__name__}: {ex}",
            flush=True,
        )
        return False
    if metadata_sidecars:
        assert_metadata_sidecars(log_dir, metadata_sidecars, before_resume=False)
    return success


def env_flag(name: str, default: bool) -> bool:
    """One truthiness rule for boolean env dials: unset -> `default`; `"0"`/`"false"`/`"off"`/`"no"`/`""` -> False (case-insensitive, stripped); anything else -> True.

    The empty string reads FALSE (an explicitly emptied dial is a request to turn it off, not to fall back to the default) — the api_key single-user driver's semantics, adopted battery-wide; launchers always pass explicit `0`/`1`, so the unification is practice-neutral. Normalization matters for the HUMAN at a shell: `FLAG=False` or `FLAG=OFF` must not silently read as True.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "off", "no", "")


def apply_env_eval_defaults(eval_kw: dict[str, Any]) -> None:
    """Apply the shared env-tunable eval defaults (setdefault — explicit kwargs win).

    One block for every driver that reaches `eval_set`/`eval` (`run_resumable` and any slot-retry driver), so a wave and its in-place retries resolve the identical config from the identical env.

    - `retry_on_error=3`.
    - `fail_on_error`: fraction of a task's samples that may error before eval_set CANCELS the in-flight run. Default 0.35, but a broad API storm can push transient errors past it — cancelling live episodes and tripping the stop-guard (observed to wedge a whole shard). `FAIL_ON_ERROR` (env) raises it so storm attrition rides out on retries/resume instead; the stop-guard still catches a genuine all-fail epoch.
    - `max_tokens`: adaptive reasoning and visible output share one budget. This applies the repository-wide safe default to string-bound roles; pre-bound thinking roles carry the same cap in `_multiagent_pi.roles.role_model`.
    - `timeout` (`PETRI_GENERATE_TIMEOUT`, default 3600, `0` disables): bound each generate's total retry budget. inspect retries retryable API failures (429/529/5xx/timeouts) FOREVER by default, so a sustained outage stalls every in-flight sample silently instead of failing; with a budget, exhaustion raises a retryable sample error that retry_on_error / eval_set resume handle. 3600s rides out a ~50-minute continuous outage within one call (backoff sleeps reach the 30-minute cap after ~10 attempts). `timeout` is excluded from eval_set task identity, so enabling it mid-campaign does not invalidate completed samples. Note it does not bound `count_tokens`/compaction calls (those read the model instance's own config).
    - `time_limit` (`PETRI_SAMPLE_TIME_LIMIT`, unset/`0` = none): bound each SAMPLE's total wall-clock. The env var was already the convention several runners wired by hand; reading it here gives every wave the knob without per-runner plumbing — exporting the env var used to reach NOTHING on this path (a truncation postmortem found `sample.limit is None` everywhere, a vacuous guard). UNLIKE `timeout`, `time_limit` is PART of eval_set task identity (`evalset.task_identifier`): pick it when a wave STARTS and hold it constant — changing it mid-campaign re-keys the tasks, so a resume ignores (does not corrupt) the completed logs and starts the wave over.
    """
    eval_kw.setdefault("retry_on_error", 3)
    eval_kw.setdefault("fail_on_error", float(os.environ.get("FAIL_ON_ERROR", "0.35")))
    eval_kw.setdefault("max_tokens", ADAPTIVE_THINKING_MAX_TOKENS)
    # An explicitly emptied dial (`PETRI_GENERATE_TIMEOUT=`) means "off" — matching `env_flag`'s
    # empty-string rule; `int("")` used to crash the launcher instead. Unset keeps the default.
    timeout = _env_generate_timeout()
    if timeout > 0:
        eval_kw.setdefault("timeout", timeout)
    sample_limit = int(os.environ.get("PETRI_SAMPLE_TIME_LIMIT", "0").strip() or "0")
    if sample_limit > 0:
        eval_kw.setdefault("time_limit", sample_limit)


@contextmanager
def metadata_sidecar_directory(log_dir: str | None) -> Iterator[None]:
    """Scope task-side sidecar writes to one `run_resumable` invocation."""
    previous = os.environ.get(METADATA_SIDECAR_DIR_ENV)
    if log_dir is not None:
        os.environ[METADATA_SIDECAR_DIR_ENV] = log_dir
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(METADATA_SIDECAR_DIR_ENV, None)
        else:
            os.environ[METADATA_SIDECAR_DIR_ENV] = previous


def is_clean(sample: EvalSample) -> bool:
    """Whether a sample is scoreable: no recorded error and not invalidated.

    The house clean-sample test (tombstones from SIGINT/retry cycles are counted, never scored). Aggregators, freezes, and durability checks must all use this one predicate so "clean" cannot drift into two definitions.
    """
    return sample.error is None and sample.invalidation is None


def _durability_samples(log_dir: str) -> Iterator[tuple[Path, EvalSample]]:
    """Yield clean samples from each most-complete eval log in `log_dir`."""
    paths = latest_logs_per_task(list(Path(log_dir).glob("*.eval")))
    for path in paths:
        for sample in read_eval_log_samples(
            str(path), resolve_attachments=False, all_samples_required=False
        ):
            if is_clean(sample):
                yield path, sample


def assert_metadata_sidecars(
    log_dir: str,
    fields: Mapping[str, type[Any]],
    *,
    before_resume: bool,
) -> None:
    """Fail if any reusable/completed sample lacks a valid declared sidecar."""
    failures: list[str] = []
    for path, sample in _durability_samples(log_dir):
        for field, expected_type in fields.items():
            value = read_metadata_sidecar(sample, path, field)
            if not isinstance(value, expected_type):
                failures.append(
                    f"{path.name}: sample={sample.id!r} epoch={sample.epoch} "
                    f"field={field!r} expected={expected_type.__name__}"
                )
    if not failures:
        return

    detail = "; ".join(failures[:5])
    if len(failures) > 5:
        detail += f"; ... and {len(failures) - 5} more"
    if before_resume:
        raise RuntimeError(
            "refusing to resume sidecar-less completed samples because Inspect may "
            "re-persist them from thinned summaries; backfill sidecars in place first: "
            f"{detail}"
        )
    raise RuntimeError(f"metadata sidecar durability check failed: {detail}")


def latest_logs_per_task(files: list[Path]) -> list[Path]:
    """Dedup a glob of `.eval` logs to the MOST-COMPLETE file per (directory, task).

    `eval_set` with `retry_cleanup=False` (and interrupted runs generally) leaves multiple log files for the same task; aggregating all of them double-counts samples. Dedup is scoped per directory because each `eval_set` log_dir is its own resumable run — globs that span sibling dirs (e.g. transplant's stage dirs) may legitimately hold same-named tasks from separate runs that must all be kept.

    Selection prefers the attempt with the most completed samples (read cheaply from the header's `results.completed_samples`), tie-broken by the lexicographically-last filename (latest timestamp). This is NOT plain "latest filename": a deadlock-recovered `*-recovered.eval` would otherwise be silently shadowed by a later-timestamped but emptier file left by a killed/interrupted resume (e.g. a 0-sample log written when a hung run is restarted), reading that cell as MISSING in the aggregate. Picking by completed-sample count keeps the recovered data; for the common single-attempt case the behavior is unchanged.

    Unreadable files are skipped with a printed warning: a truncated attempt means the next-best readable log (or none) is used, so treat skip warnings during aggregation as a prompt to investigate before trusting the output.
    """
    candidates: dict[tuple[Path, str], list[tuple[int, Path]]] = {}
    for fp in sorted(files, key=lambda p: p.name):
        try:
            hdr = read_eval_log(str(fp), header_only=True)
            task = hdr.eval.task
            completed = getattr(
                getattr(hdr, "results", None), "completed_samples", None
            )
        except Exception as ex:
            print(f"!! skipping unreadable log {fp}: {ex!r}", flush=True)
            continue
        candidates.setdefault((fp.parent, task), []).append((completed or 0, fp))
    latest: dict[tuple[Path, str], Path] = {}
    for key, cand in candidates.items():
        latest[key] = max(cand, key=lambda c: (c[0], c[1].name))[1]
    return sorted(latest.values())
