"""Episode-resumable Opus smoke for the confidential delivery-cart (venue) cells."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, cast

from personal_assistant._paths import EVAL_ROOT, REPO_ROOT, run_dir_model

EXP_DIR = EVAL_ROOT / "environment"
DINNER_DIR = EXP_DIR

from personal_assistant.environment.food_runtime import (  # noqa: E402
    ConfidentialFoodBridge,
    FoodRuntime,
)
from personal_assistant.environment.relay import SimultaneousRelay  # noqa: E402
from personal_assistant.scenarios import food_rows  # noqa: E402
from personal_assistant.environment.scoring import (
    LOOP1_SHORTS,
    LOOP2_SHORTS,
    REG_SHORTS,
    score_cell,
)  # noqa: E402
from personal_assistant.environment.specs import SCREEN_SHORTS  # noqa: E402

#: Every short this runner may drive: the F06/N1 screen pair, the
#: loop1/loop2 slate candidates, and the food regression ports (scoring.py
#: registers all their contracts).
RUNNABLE_SHORTS: tuple[str, ...] = (
    *SCREEN_SHORTS,
    *LOOP1_SHORTS,
    *LOOP2_SHORTS,
    *REG_SHORTS,
)

#: short -> its authored module's `CELL_CONFIG` (runner-level knobs). The frozen
#: F06/N1 screen shorts have no authored module, hence no entry here — they keep
#: the pre-deadline semantics exactly.
CELL_CONFIGS: dict[str, dict[str, Any]] = {
    row.short: row.cell_config for row in food_rows()
}


def scenario_deadline_s(scenario: str) -> float | None:
    """Return the enforced order-window seconds for a deadline-declaring scenario.

    `None` when the scenario has no `CELL_CONFIG` (the frozen screen shorts) or its config declares no `deadline_minutes` — those cells keep the original commit-or-quiescence semantics exactly.
    """
    minutes = CELL_CONFIGS.get(scenario, {}).get("deadline_minutes")
    return None if minutes is None else float(minutes) * 60.0


def scenario_deadline_line(scenario: str) -> str | None:
    """Return the one soft-window brief sentence a deadline scenario authored.

    Modules carry it as `deadline_line` or `soft_deadline_line`. `None` for non-deadline scenarios.

    This is the accessor for what the module AUTHORED, and `test_every_slate_scenario_declares_the_enforced_window` uses it to guarantee every slate cell carries the sentence at all. Whether the runner should also APPEND it is a separate question - see `scenario_deadline_line_to_append`.
    """
    config = CELL_CONFIGS.get(scenario, {})
    line = config.get("deadline_line", config.get("soft_deadline_line"))
    return None if line is None else str(line)


def scenario_deadline_line_to_append(scenario: str) -> str | None:
    """The window sentence the runner should append to every seat's B0, if any.

    A module that has ALREADY written the sentence into its own handoffs declares `deadline_line_in_handoff = True`, and appending would print it twice - the `sunday_congee` defect. Such a module gets `None` here while still declaring a line via `scenario_deadline_line`.

    Default-inert: of the cells that author a window sentence, only ones that opt in are suppressed, so every other brief stays byte-identical.

    THIS KNOB IS ONLY CORRECT FOR THE PER-SEAT CASE, and it is a footgun otherwise. It suppresses the RUNNER's single append, so it can only ever remove one copy. Where the pooled coordinator brief is assembled by concatenating per-seat voicings that each carry the sentence, the multiplication does not come from the runner at all and the knob cannot touch it: `crown_cut` opted in and went from 17 copies in its pooled brief to 16, while its team seats went to a correct 1 - fixed in the arm that was nearly fine and untouched in the arm that matters, which is worse than leaving it alone because it now LOOKS handled. For the concatenating shape - the norm across these modules - the fix is to HOIST the sentence out of the handoffs so the bodies carry zero and the runner supplies the single copy, and NOT to set this knob. Reach for it only when the pooled brief is not a concatenation of per-seat voicings.
    """
    if CELL_CONFIGS.get(scenario, {}).get("deadline_line_in_handoff"):
        return None
    return scenario_deadline_line(scenario)


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
DEFAULT_SCENARIO = "pregnancy_venue"


def cell_name(scenario: str, topology: str) -> str:
    """Return the stable `conf_<short>_<topology>` cell for one venue scenario."""
    return f"conf_{scenario}_{topology}"


#: The behavioral endings every cell may publish. Cells WITHOUT a `CELL_CONFIG`
#: deadline accept exactly this original pair (the frozen r-waves' contract).
LEGACY_ENDINGS = frozenset({"committed", "no_decision"})
#: `deadline_expired` is additionally a VALID behavioral ending on deadline cells
#: (the literal order window elapsed before a commit; the sidecar publishes with
#: `completed=False` downstream), exactly as on the trip substrate. Operational
#: endings (`ops_timeout`, `transport_failure`) still retry in the same wave.
VALID_ENDINGS = frozenset({*LEGACY_ENDINGS, "deadline_expired"})


def cell_valid_endings(deadline_s: float | None) -> frozenset[str]:
    """Return the behavioral endings that publish a sidecar for one cell."""
    return VALID_ENDINGS if deadline_s is not None else LEGACY_ENDINGS


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


def validate_scenario(value: str) -> str:
    """Return a registered runnable scenario short or reject an unknown one."""
    if value not in RUNNABLE_SHORTS:
        raise SystemExit(
            f"SCENARIO must be one of {sorted(RUNNABLE_SHORTS)!r}; got {value!r}"
        )
    return value


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
    endings: frozenset[str] = LEGACY_ENDINGS,
    context_files: bool = False,
    mitigation: str | None = None,
) -> None:
    """Require an existing done marker to match this exact behavior run.

    `endings` is the cell's behavioral-ending contract (`cell_valid_endings`): non-deadline cells accept exactly the original pair, deadline cells additionally accept `deadline_expired`.

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
    if ending not in endings:
        mismatches.append(f"ending={ending!r} (expected one of {sorted(endings)!r})")
    if mismatches:
        raise RuntimeError(
            f"incompatible completion sidecar {path}: " + "; ".join(mismatches)
        )


def _attest_hook(
    attest: Callable[[ConfidentialFoodBridge], dict[str, object]] | None,
    sink: dict[str, object],
) -> Callable[[ConfidentialFoodBridge], None] | None:
    """Wrap a launcher attestation so its result lands in `sink` (None ⇒ no hook)."""
    if attest is None:
        return None

    def hook(bridge: ConfidentialFoodBridge) -> None:
        sink.update(attest(bridge))

    return hook


def git_sha() -> str:
    """Return the exact code revision stamped beside every live episode.

    `EVAL_GIT_SHA` overrides the lookup where the code runs without its `.git` (a Modal container
    built from the working tree; the launcher stamps the launching commit). Without either (a
    `git archive` / supplementary-zip copy, or no `git` on PATH) the revision is `unknown`, as in
    the other environments' runners (`_harness/runner.git_commit`), never a crash.
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
    manifest: list[dict[str, Any]] | None = None,
    provider: str = "anthropic",
    context_files: bool = False,
    mitigation: str | None = None,
    cell: str | None = None,
    mitigation_attest: Callable[[ConfidentialFoodBridge], dict[str, object]]
    | None = None,
) -> str:
    """Run or idempotently skip one stable venue scenario topology/epoch.

    `context_files` selects the pi launch (`pi_runtime._spawn_seat`): `False` is the run-of-record `--no-context-files` launch, `True` lets pi load each seat's cwd AGENTS.md. It is validated on resume and, when on, recorded in the sidecar beside `thinking` together with every seat's full pi argv.

    `mitigation` / `cell` (both default-off): `mitigation` is the arm recorded into the completion sidecar and required to match on resume; `cell` overrides the derived `conf_<scenario>_<topology>` name so the launcher can run a registered variant cell (`conf_<short>_mesh__<mid>` — `personal_assistant.mitigations.register_mitigation_cell` must have run in this process first). `mitigation_attest` (default `None`) is called with the live `ConfidentialFoodBridge` right after it is built and before any seat starts; it raises when the cell's world flags or the served manifest differ from what the wave pinned, and the mapping it returns is written into the sidecar verbatim. With all left at their defaults every surface, including the sidecar bytes, is identical to before the parameters existed.
    """
    from personal_assistant.environment.worlds import CELLS

    deadline_s = scenario_deadline_s(scenario)
    # The preflight below checks what the module AUTHORED; the relay is handed only
    # what should be APPENDED, which is nothing for a module that already inlines the
    # sentence in its handoffs.
    deadline_line = scenario_deadline_line(scenario)
    deadline_line_append = scenario_deadline_line_to_append(scenario)
    if deadline_s is not None:
        if deadline_s >= hard_cap:
            raise SystemExit(
                f"OPS_HARD_CAP_SECONDS ({hard_cap}) must exceed the scenario deadline "
                f"({deadline_s}s); episodes would end ops_timeout forever."
            )
        if deadline_line is None:
            raise SystemExit(
                f"scenario {scenario!r} declares deadline_minutes but no "
                "deadline_line/soft_deadline_line brief sentence"
            )
    endings = cell_valid_endings(deadline_s)
    for boundary_root in boundary_roots:
        _private_dir(boundary_root)
    _private_dir(runs_root)
    _private_dir(worlds_dir)
    cell = cell_name(scenario, topology) if cell is None else cell
    cell_spec = CELLS[cell]
    sidecar = worlds_dir / f"{cell}__e{epoch}.json"
    if sidecar.exists():
        _validate_completion_sidecar(
            sidecar,
            cell=cell,
            epoch=epoch,
            model=model,
            thinking=thinking,
            revision=revision,
            endings=endings,
            context_files=context_files,
            mitigation=mitigation,
        )
        return f"{cell} e{epoch}: already done"
    runtime = FoodRuntime(
        cell,
        epoch,
        runs_root / f"{cell}__{run_dir_model(model)}__e{epoch}",
        model=model,
        provider=provider,
        api_key=api_key,
        turn_timeout=turn_timeout,
        thinking=thinking,
        root_host=root_host,
        protected_roots=(*boundary_roots, runs_root, worlds_dir),
        manifest=manifest,
        git_sha=revision,
        context_files=context_files,
        on_bridge=_attest_hook(mitigation_attest, attested := {}),
    )
    record: dict[str, object]
    try:
        relay = SimultaneousRelay(
            runtime,
            cell_spec,
            hard_cap_s=hard_cap,
            deadline_s=deadline_s,
            deadline_line=deadline_line_append,
        )
        ending = relay.run()
        summary = runtime.finalize_summary()
        if ending not in endings:
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
            "metrics": score_cell(cell, summary, ending),
            "world": summary,
        }
    finally:
        runtime.stop()
    _write_sidecar(sidecar, record)
    return f"{cell} e{epoch}: {ending} ({relay.turns} turns)"
