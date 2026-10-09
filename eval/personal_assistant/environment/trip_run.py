"""Episode-resumable Opus smoke for cart-shaped trip mesh and steward topologies."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import cast

from personal_assistant._paths import EVAL_ROOT, REPO_ROOT, run_dir_model

EXP_DIR = EVAL_ROOT / "environment"
DINNER_DIR = EXP_DIR

from personal_assistant.environment.relay import DecisionFreeRelay  # noqa: E402
from personal_assistant.scenarios import register_trip_specs  # noqa: E402
from personal_assistant.environment.trip_cart import (
    TripCartScenario,
    TripMitigationFlags,
    resolve_trip_spec,
    score_trip,
)  # noqa: E402
from personal_assistant.environment.trip_runtime import (  # noqa: E402
    TripBridge,
    TripRuntime,
)

# The 15 trip scenarios of the confidential-planning slate (loader-registered, idempotent), so
# SCENARIO=<registry key> resolves through `resolve_trip_spec`.
register_trip_specs()

TARGETS = {
    "opus": "claude-opus-5",
    "sonnet": "claude-sonnet-5",
    # The GPT pilot: ids verified against OpenAI `/v1/models` (exact match).
    "sol": "gpt-5.6-sol",
    "terra": "gpt-5.6-terra",
}
#: pi provider per target name; drives auth.json, `--provider`, and the thinking gate.
PROVIDERS = {
    "opus": "anthropic",
    "sonnet": "anthropic",
    "sol": "openai",
    "terra": "openai",
}
#: The pi thinking level per provider (a design decision: GPT seats run
#: reasoning effort MEDIUM — pi maps its thinking level onto the Responses API's
#: `reasoning.effort`; the Anthropic paths stay thinking-off, byte-identical).
THINKING_BY_PROVIDER = {"anthropic": "off", "openai": "medium", "openrouter": "off"}
DEFAULT_SCENARIO = "demo_sofa"


def cell_prefix(scenario: str) -> str:
    """Return the stable cell prefix for one registered trip scenario."""
    return f"trip_{scenario}"


CELL_PREFIX = cell_prefix(DEFAULT_SCENARIO)

#: `deadline_expired` is a VALID behavioral ending on the trip substrate: the
#: literal booking window elapsed before a commit, and the sidecar publishes with
#: `completed=False`. Operational endings (`ops_timeout`, `transport_failure`)
#: still retry in the same wave.
VALID_ENDINGS = frozenset({"committed", "no_decision", "deadline_expired"})


def validate_thinking(value: str, provider: str = "anthropic") -> str:
    """Return a normalized pi thinking level or reject an invalid setting.

    Anthropic waves are thinking-off exactly (the paper's standing surface). OpenAI (GPT-pilot) waves carry a real pi thinking level — pi maps it onto the Responses API's `reasoning.effort` — validated against pi 0.77.0's level set.
    """
    from personal_assistant.environment.pi_runtime import PI_THINKING_LEVELS

    thinking = value.strip().lower()
    if provider == "anthropic":
        if thinking != "off":
            raise SystemExit(f"PI_THINKING must be 'off' for this wave; got {value!r}")
    elif thinking not in PI_THINKING_LEVELS:
        raise SystemExit(
            f"PI_THINKING must be one of {PI_THINKING_LEVELS} for {provider}; "
            f"got {value!r}"
        )
    return thinking


def _private_dir(path: Path) -> None:
    """Create a runner-owned directory and keep it owner-only."""
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def _write_sidecar(path: Path, record: Mapping[str, object]) -> None:
    """Atomically publish one owner-readable completion sidecar."""
    _private_dir(path.parent)
    draft = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            draft,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            0o600,
        )
        with os.fdopen(descriptor, "w") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=1)
        draft.chmod(0o600)
        draft.replace(path)
        path.chmod(0o600)
    finally:
        draft.unlink(missing_ok=True)


def _validate_completion_sidecar(
    path: Path,
    *,
    cell: str,
    epoch: int,
    model: str,
    thinking: str,
    revision: str,
    context_files: bool = False,
    mitigation: str | None = None,
) -> None:
    """Require an existing done marker to match this exact behavior run.

    `context_files` must match too: an on-sidecar records `"context_files": true`, and an off-run never resumes one (a run-of-record sidecar carries no such field).

    `mitigation`: when set, the sidecar must record exactly that arm — a mismatch fails the resume check the same way a `git_sha` mismatch does; the control (`None`) refuses a sidecar that records an arm.
    """
    try:
        parsed: object = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"corrupt completion sidecar {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"corrupt completion sidecar {path}: expected JSON object")
    record = cast(dict[str, object], parsed)
    expected: dict[str, object] = {
        "cell": cell,
        "epoch": epoch,
        "model": model,
        "thinking": thinking,
        "git_sha": revision,
    }
    if context_files:
        expected["context_files"] = True
    elif record.get("context_files"):
        expected["context_files"] = None
    if mitigation is not None:
        expected["mitigation"] = mitigation
    elif record.get("mitigation"):
        expected["mitigation"] = None
    mismatches = [
        f"{field}={record.get(field)!r} (expected {value!r})"
        for field, value in expected.items()
        if record.get(field) != value
    ]
    ending = record.get("ending")
    if ending not in VALID_ENDINGS:
        mismatches.append(
            f"ending={ending!r} (expected one of {sorted(VALID_ENDINGS)!r})"
        )
    if mismatches:
        raise RuntimeError(
            f"incompatible completion sidecar {path}: " + "; ".join(mismatches)
        )


def _attest_hook(
    attest: Callable[[TripBridge], dict[str, object]] | None,
    sink: dict[str, object],
) -> Callable[[TripBridge], None] | None:
    """Wrap a launcher attestation so its result lands in `sink` (None ⇒ no hook)."""
    if attest is None:
        return None

    def hook(bridge: TripBridge) -> None:
        sink.update(attest(bridge))

    return hook


def git_sha() -> str:
    """Return the exact code revision stamped beside every live episode.

    `EVAL_GIT_SHA` overrides the lookup where the code runs without its `.git` (a Modal container);
    without either the revision is `unknown` (see `food_run.git_sha`).
    """
    if override := os.environ.get("EVAL_GIT_SHA", "").strip():
        return override
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    return (out.stdout.strip() if out.returncode == 0 else "") or "unknown"


def run_episode(
    topology: str,
    epoch: int,
    *,
    model: str,
    api_key: str,
    runs_root: Path,
    worlds_dir: Path,
    turn_timeout: float,
    hard_cap: float,
    revision: str,
    thinking: str,
    root_host: bool,
    boundary_roots: tuple[Path, ...] = (),
    scenario: str = DEFAULT_SCENARIO,
    provider: str = "anthropic",
    context_files: bool = False,
    mitigation: str | None = None,
    extra_norm_line: str = "",
    confirm_seat: str | None = None,
    mitigation_flags: TripMitigationFlags | None = None,
    mitigation_attest: Callable[[TripBridge], dict[str, object]] | None = None,
) -> str:
    """Run or idempotently skip one stable trip scenario topology/epoch.

    `context_files` selects the pi launch (`pi_runtime._spawn_seat`): `False` is the run-of-record `--no-context-files` launch, `True` lets pi load each seat's cwd AGENTS.md. It is validated on resume and, when on, recorded in the sidecar beside `thinking` together with every seat's full pi argv.

    `mitigation` / `extra_norm_line` / `confirm_seat` (all default-off): `mitigation` is the arm recorded into the completion sidecar and required to match on resume; `extra_norm_line` is a trip-voiced norm paragraph threaded into every seat's `AGENTS.md`; `confirm_seat` pins draft cancel/confirm to one traveller id (M12). `mitigation_flags` (default `None` = all-off) carries the enforced arms' `TripMitigationFlags` into the world and its tool manifest. `mitigation_attest` (default `None`) is called with the live `TripBridge` before any seat starts; it raises when the world's flags or the served manifest differ from what the wave pinned, and the mapping it returns is written into the sidecar verbatim. The hooks forward straight through `TripRuntime` into its `TripBridge`; with all of them left at their defaults every surface, including the sidecar bytes, is identical to before the parameters existed.
    """
    spec = resolve_trip_spec(scenario)
    if spec.deadline_minutes * 60.0 >= hard_cap:
        raise SystemExit(
            f"OPS_HARD_CAP_SECONDS ({hard_cap}) must exceed the scenario deadline "
            f"({spec.deadline_minutes * 60.0}s); episodes would end ops_timeout forever."
        )
    for boundary_root in boundary_roots:
        _private_dir(boundary_root)
    _private_dir(runs_root)
    _private_dir(worlds_dir)
    cell = f"{cell_prefix(scenario)}_{topology}"
    sidecar = worlds_dir / f"{cell}__e{epoch}.json"
    if sidecar.exists():
        _validate_completion_sidecar(
            sidecar,
            cell=cell,
            epoch=epoch,
            model=model,
            thinking=thinking,
            revision=revision,
            context_files=context_files,
            mitigation=mitigation,
        )
        return f"{cell} e{epoch}: already done"
    runtime = TripRuntime(
        topology,
        runs_root / f"{cell}__{run_dir_model(model)}__e{epoch}",
        model=model,
        provider=provider,
        api_key=api_key,
        turn_timeout=turn_timeout,
        thinking=thinking,
        root_host=root_host,
        protected_roots=(*boundary_roots, runs_root, worlds_dir),
        scenario=scenario,
        context_files=context_files,
        extra_norm_line=extra_norm_line,
        confirm_seat=confirm_seat,
        mitigation_flags=mitigation_flags,
        on_bridge=_attest_hook(mitigation_attest, attested := {}),
    )
    record: dict[str, object]
    try:
        relay = DecisionFreeRelay(
            runtime,
            TripCartScenario(topology, spec, extra_norm_line),
            hard_cap_s=hard_cap,
            deadline_s=spec.deadline_minutes * 60.0,
        )
        ending = relay.run()
        summary = runtime.finalize_summary()
        if ending not in VALID_ENDINGS:
            raise RuntimeError(
                f"{cell} e{epoch} ended {ending!r}; no completion sidecar published"
            )
        record = {
            "cell": cell,
            "scenario": scenario,
            "model": model,
            "thinking": thinking,
            "epoch": epoch,
            "git_sha": revision,
            # Recorded only when on / under an arm, so a run-of-record sidecar stays
            # byte-identical (research wrote `context_files` and `pi_argv` on every sidecar).
            **(
                {"context_files": True, "pi_argv": runtime.pi_argv}
                if context_files
                else {}
            ),
            **({} if mitigation is None else {"mitigation": mitigation}),
            **attested,
            **runtime.sidecar_notes,
            "ending": ending,
            "turns": relay.turns,
            "metrics": score_trip(summary, spec, ending),
            "world": summary,
        }
    finally:
        runtime.stop()
    _write_sidecar(sidecar, record)
    return f"{cell} e{epoch}: {ending} ({relay.turns} turns)"
