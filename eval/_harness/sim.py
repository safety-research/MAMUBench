"""The simulated harness (`--harness sim`): the paper's inspect_ai scripted driver, one episode per run dir.

`api_key` and `clinic` carry two harnesses. The real-pi harness (`runner.py`) is the eval's own; the
SIMULATED harness is the instrument the paper's numbers were produced with: the vendored
`_multiagent_pi.build_task` (ported from the authors' research code) over the same deterministic worlds, with the no-LLM `scripted_driver` in the
auditor seat (zero orchestration model calls), every target seat a real inspect_ai model call, the world
tools answered mechanically and user pressure delivered as scripted beats. Each eval's `cells.py` states
the paper's driver recipe as a `SimRecipe` (the api_key single-user and 16-user drivers and the clinic
driver, pinned spec-for-spec by `_harness/tests/test_sim_recipes.py`).
This module plays one (recipe, epoch) as one single-sample `eval_set` in its own run dir and banks the
world ledger in the run-dir shape the reports already read (`world/summary.json`, `world/config.json`,
`DONE.json`), so `report.py` / `check.py` read both harnesses unchanged and a Modal container runs
exactly one episode.

Instruments. The paper's runs used the SAME driver under a few scheduler knob sets. Every cell plays exactly
its own knob set and nothing else: each eval's `cells.py` states the knob sets verbatim from the paper's run
configs and names the one every formation plays (`PAPER_INSTRUMENT`; a mitigation arm's recipe names its own).
There is no switch to another knob set, reasoning setting, step budget, balance gate or time limit.

- `hero` (the coordinators, and the API key's solo): the original scheduler: a burst cap (6 consecutive world-answered
  resumes of one seat), a balance gate (`MAX_AHEAD`, derived from the step budget: at most 20 turns ahead of
  the most-behind seat) and the flown wrap-up (2 post-horizon grants per seat).
- `limits_off` (the API key's teams): burst cap and balance gate switched off (`BURST = MAX_AHEAD = 1_000_000`).
- `standard` (the clinic's teams; in the paper's words, a wrap-up that "continues until every call is
  delivered, waking any desk that has not yet taken a turn"): burst cap and balance gate switched off, the
  world's yield rule and arrival-order wake (`BURST_YIELD_TOOLS`, `BEAT_WAKE_ORDER`), an unbounded wrap-up that
  brings up a never-woken desk holding a waiting call (`WRAPUP_GRANTS`, `WRAPUP_BRINGUP`), a 5,000-step budget,
  a 1 h generate timeout and a 16 h sample limit.

The instrument, every knob, the step budget, the time limits and the target's reasoning setting are
recorded in `world/config.json` (with `paper_instrument` = the instrument, `on_paper_instrument` true and
`off_paper` empty: the record schema the reports share with the pi environments, whose settings can differ
from the paper's); a DONE-skip refuses a run dir produced by any other configuration, and the reports refuse
a runs root that mixes instruments within one (formation, model, mitigation) pool (`_offpaper.physics`).

Targets. Anthropic, OpenAI and OpenRouter targets all run, bound exactly as in the paper's runs: the
target's reasoning setting is the paper's per-provider value (`SimRecipe.effort_of_record`), the house
auditor and judge keep their Anthropic models on the Anthropic key, and a non-Anthropic target reads its own
provider key (`OPENAI_API_KEY` / `OPENROUTER_API_KEY`), never the Anthropic one.

Seeding: the paper's drivers run inspect epochs 1..N and seed the world on `(scenario, epoch)`; here
epoch N runs a one-epoch task whose spec carries `epoch_offset = N - 1` (the drivers' own top-up
mechanism), so the world is byte-identical to the paper's epoch N and the sidecar lands as
`<cell>__e<N>.json`.

Not banked (no `DONE.json`, so rerunning the same command redoes it, the pi harness's storm-abort
convention): a night the driver step-capped, a sample inspect cancelled at its time limit (`unwound`)
or errored out of its retries, and a night whose driver ended anywhere but at the world's horizon (a
fleet quarantine: every seat at the failed-resume cap, as when the provider rejects the key). These are
the paper's own completeness rules (`_ran_scorer`; `driver_ended` must start with `world horizon
reached`, `require_bankable`). An
instrument with a long-limit retry (`SimRecipe.retry_time_limit_s`, the paper's second pass)
replays an unwound episode once, from scratch, under the longer limit before giving up.

Provider-error screen (rule T): every banked episode's target `ModelEvent`s are scanned exactly as the
paper's provider-error scan does, and the counts go into `DONE.json` as their own fields
(`rule_t_lost_turns`, `failed_calls`, `max_consecutive_failures`, ...). `error_turns` and the reports'
`harness_clean` are untouched: which arms are screened is the reader's decision (the paper screens the
API key lead arms, not the formation corpus).

The vendored stack is configured through process-global dials (`MAX_AHEAD`, `KEYS`, `TARGET_REASONING`,
...), exported per episode (every other dial it reads is cleared for the episode, `CLEARED_ENV`), so this
harness plays one episode at a time per process; concurrency is Modal's (one container per
episode). `MAX_AHEAD` (how far one seat may run ahead of the most-behind before a forced rotation) is
derived by the drivers from the step budget and the seat count unless the instrument pins it; it is
pinned EXPLICITLY per episode here (the instrument's value, else `max_ahead_of_record`) and recorded.
"""

from __future__ import annotations

import collections
import json
import os
import re
import shutil
import tarfile
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import quote

import inspect_ai
from _eval_runner import latest_logs_per_task, run_resumable, target_model
from _mitigations import NONE, stamp
from _multiagent_pi import build_task
from _multiagent_pi.roles import (
    build_roles,  # pyright: ignore[reportUnknownVariableType]
)
from _multiagent_pi.scenario import ScenarioSpec
from _providers import KEY_ENV_VARS, path_safe_model
from _resume import configuration_drift
from inspect_ai import task_with  # pyright: ignore[reportUnknownVariableType]
from inspect_ai.log import read_eval_log_samples
from inspect_ai.model import Model, ModelOutput, get_model

from _harness.runner import RunConfig, git_commit

RouterFactory = Callable[[ScenarioSpec, dict[str, Any], int], Any]
#: Which env dial binds the target, as the paper's driver bound it: `target_reasoning` =
#: `_eval_runner.target_model` under `TARGET_REASONING` (the api_key runs; `none` sends no thinking
#: parameter); `target_thinking` = `_multiagent_pi.build_roles` under `TARGET_THINKING` (the clinic runs;
#: `0` sends no thinking parameter). Claude Opus 5 and Claude Sonnet 5: thinking not requested (no thinking
#: parameter is sent).
TargetBinding = Literal["target_reasoning", "target_thinking"]
#: The env var each binding reads.
BINDING_DIAL: dict[TargetBinding, str] = {
    "target_reasoning": "TARGET_REASONING",
    "target_thinking": "TARGET_THINKING",
}
#: The per-generate retry budget the hero and limits-off lanes pinned (`PETRI_GENERATE_TIMEOUT=900`).
GENERATE_TIMEOUT_S = 900
#: `BURST` / `MAX_AHEAD` with the limit switched off (the API key's `limits_off`, the clinic's `standard`).
LIMITS_OFF = 1_000_000
#: The env var the Anthropic target's key is handed to the vendored stack through (`KEYS=*:<this>`).
KEY_ENV = "EVAL_SIM_API_KEY"
#: The env var the house roles' Anthropic key rides when the target is not Anthropic
#: (`KEYS=auditor:<this>,judge:<this>`, as the paper's runs with a non-Anthropic target keyed them).
HOUSE_KEY_ENV = "EVAL_SIM_HOUSE_KEY"
#: The variable inspect's provider reads a non-Anthropic target's key from (exported for the episode only).
TARGET_KEY_ENV: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}
#: Stand-in for the house roles' key on an `auditor="none"` recipe whose target is not Anthropic and whose
#: launcher has no Anthropic key: the scripted driver never calls the auditor and the judge is inert there
#: (a never-called, pre-bound Anthropic auditor/judge), so any call would fail loudly.
UNUSED_HOUSE_KEY = "unused-house-roles-auditor-none"
#: Wall-clock margin per episode beyond its sample time limits (world build, scoring, sidecar, Volume commit).
EPISODE_MARGIN_S = 1800
#: The largest burst under which the offline stand-in keeps its original wait-forever behaviour (the hero's).
FAKE_BOUNDED_BURST = 6
#: Env dials the vendored stack reads that no paper run set outside its instrument: an episode
#: exports its own values and CLEARS the rest for its duration, so a launching shell can never leak a
#: scheduler knob or a behaviour switch into a cell.
CLEARED_ENV: tuple[str, ...] = (
    "BURST_YIELD_TOOLS",
    "BEAT_WAKE_ORDER",
    "WAKE_ORDER",
    "WRAPUP_BURST",
    "WRAPUP_GRANTS",
    "WRAPUP_BRINGUP",
    "PETRI_ALLOW_TRUNCATED",
    "TARGET_REASONING",
    "TARGET_THINKING",
    "AUDITOR_THINKING",
    "PETRI_MAX_RETRIES",
    "TOKEN_CLUSTER_SCALE_NOOP_LEGACY",
)


@dataclass(frozen=True)
class SimRecipe:
    """One eval's paper-driver recipe for one (scenario, formation) cell under the instrument of its paper number.

    Attributes:
        spec: The paper's own spec for the cell (name, seats, prompts, tools), epoch-agnostic.
        router_factory: `(spec, nstate, epoch) -> router` over a fresh world, as the driver wired it.
        max_turns: The paper driver's resume-step cap (`build_task(max_turns=...)`).
        auditor: `"none"` (scripted driver, fully mechanical toolset) or `"escalation"` (scripted driver
            plus a live auditor generation for residue the world cannot answer).
        burst: Consecutive world-answered resumes of one seat per resume call.
        world_tool_label: The driver's label for the mechanically answered surface.
        dataset_name: `build_task(name=...)`.
        time_limit_s: The paper's per-sample wall-clock limit (`PETRI_SAMPLE_TIME_LIMIT`).
        max_connections: The lane's `MAX_CONNECTIONS` (pinned on the role configs by the stack).
        target_binding: See `TargetBinding`.
        auditor_model / judge_model: The house roles (inspect ids); the judge is inert and the
            auditor generates only on escalations (`auditor="escalation"`), never with `"none"`.
        fake_wait_call: The world's clock lever `(tool, args)` the offline stand-in calls every turn.
        dials: Process-global env the world reads at router build (recorded, exported per episode).
        framing: `"live"` (pi-framed seats) or `"console"` (typed console only), for the record.
        instrument: The scheduler instrument this recipe plays: its cell's own (see the module docstring).
        max_ahead: The instrument's pinned `MAX_AHEAD`; `None` = the drivers' derived value.
        generate_timeout_s: `PETRI_GENERATE_TIMEOUT`, the per-generate retry budget.
        retry_time_limit_s: The long-limit retry: an episode that unwinds under `time_limit_s` is replayed
            once from scratch under this limit (`None` = no retry).
        knobs: The instrument's env-gated scheduler knobs (`BURST_YIELD_TOOLS`, `WAKE_ORDER`, ...), exported
            per episode and recorded; empty = every knob unset (byte-identical to the flown loop).
        effort_of_record: The paper's target reasoning setting per provider (the binding dial's value).
        mitigation: The mitigation arm this recipe plays (`None` = the formation itself); recorded, and part
            of the reports' pool key (one pool never mixes instruments).
    """

    spec: ScenarioSpec
    router_factory: RouterFactory
    max_turns: int
    auditor: Literal["none", "escalation"]
    burst: int
    world_tool_label: str
    dataset_name: str
    time_limit_s: int
    max_connections: int
    target_binding: TargetBinding
    auditor_model: str
    judge_model: str
    fake_wait_call: tuple[str, dict[str, Any]]
    dials: dict[str, str]
    framing: str
    instrument: str = "hero"
    max_ahead: int | None = None
    generate_timeout_s: int = GENERATE_TIMEOUT_S
    retry_time_limit_s: int | None = None
    knobs: dict[str, str] = field(default_factory=dict[str, str])
    effort_of_record: dict[str, str] = field(default_factory=dict[str, str])
    mitigation: str | None = None


@dataclass(frozen=True)
class SimKeys:
    """The keys one episode binds: the target's provider key and the house roles' Anthropic key."""

    target: str
    house: str


@dataclass(frozen=True)
class RuleTCounts:
    """The provider-error scan of one episode's target generations (the paper's rule T).

    Attributes:
        ok_calls: Target generate calls that returned (`gen_ok` in the paper's scan tables).
        failed_calls: Target generate calls that ended in an error (`gen_failed`).
        failed_429 / failed_529 / failed_other: `failed_calls` by class (rate limit, overload, other).
        rule_t_lost_turns: Runs of 4 consecutive failed calls of one agent, each counted as one lost turn
            (a refused resume, "resuming X did not render"); an episode with any is dropped under rule T.
        max_consecutive_failures: The longest failure run of any one agent.
        agents_with_lost_turn: Agents with at least one lost turn.
        failed_auth: Of `failed_other`, the calls the provider refused the key for (401 authentication /
            403 permission errors). Not part of the paper's scan: such an error is never retried, so a seat
            reaches the harness's failed-resume cap (3) with no lost turn, and the readers exclude the episode
            as a harness fault instead (`_harness.readout.provider_rejected`).
    """

    ok_calls: int
    failed_calls: int
    failed_429: int
    failed_529: int
    failed_other: int
    rule_t_lost_turns: int
    max_consecutive_failures: int
    agents_with_lost_turn: int
    failed_auth: int = 0


#: Why `--parallel N>1` is refused on the simulated harness (at parse time, so `--print-info` refuses it too).
PARALLEL_REFUSAL = (
    "--harness sim plays one episode per process (its dials are process-global): run --parallel 1, or fan out "
    "on Modal (one container per episode)"
)
#: How the scripted driver's `driver_ended` opens when the world reached its horizon (any suffix names what
#: the wrap-up left undelivered); every other end (a step cap, a fleet quarantine) is not banked.
HORIZON_END = "world horizon reached"


class SimEpisodeIncomplete(RuntimeError):
    """The episode did not bank: incomplete eval, no world ledger, unwound, step-capped or ended off the horizon."""

    def __init__(self, message: str, *, unwound: bool = False) -> None:
        super().__init__(message)
        #: True when the sample unwound before the world finished (a time-limit cancel): the one outcome a
        #: long-limit retry replays.
        self.unwound = unwound


def max_ahead_of_record(max_turns: int, n_agents: int) -> int:
    """The drivers' derived forced-rotation distance (`_multiagent_pi.audit._max_ahead`, env override aside).

    Scaled to each seat's share of the step budget, floored at 8 and capped at 20: 20 for a single seat and
    for the 4/8/16-seat clusters at their 800/1000/1400 budgets, 18 for four desks at 300, 8 for the 17-52
    desk clinic floors at 300. `test_sim_recipes.py` pins this against the vendored formula.
    """
    return min(20, max(8, (max_turns // max(1, n_agents)) // 4))


def run_dir_for(config: RunConfig, recipe: SimRecipe, epoch: int) -> Path:
    """`<cell>[__mit-<arm>]__<model>__e<N>__sim` (+ `__fakemodel`): never collides with a pi-harness run dir.

    The mitigation stamp is empty for the control arm, so every earlier run dir keeps its name.
    """
    tag = "__sim" + ("__fakemodel" if config.fake_model else "")
    return (
        config.runs_root
        / f"{recipe.spec.name}{stamp(config.mitigation)}__{path_safe_model(config.model)}__e{epoch}{tag}"
    )


def check_mitigation(config: RunConfig, recipe: SimRecipe) -> None:
    """Refuse a recipe built for a different mitigation arm than the run config names.

    The run dir is stamped from the config and the record written from the recipe; both must name the
    same arm (the recipe's `None` is the control arm), or a mitigation episode could bank unstamped.

    Raises:
        ValueError: The two disagree.
    """
    built = recipe.mitigation or NONE
    if built != config.mitigation:
        raise ValueError(
            f"{recipe.spec.name}: the recipe plays mitigation {built!r} but the run config names "
            f"{config.mitigation!r} (build the recipe with cells.build_sim_recipe(..., mitigation=...))"
        )


def target_effort(config: RunConfig, recipe: SimRecipe) -> str:
    """The target's reasoning dial for this run: the paper's value for the target's provider.

    Raises:
        SystemExit: The provider has no value of record (every provider the evals run has one).
    """
    if config.provider not in recipe.effort_of_record:
        raise SystemExit(
            f"no {BINDING_DIAL[recipe.target_binding]} setting of record for provider {config.provider!r} "
            f"(the paper's runs set one for {', '.join(sorted(recipe.effort_of_record))})"
        )
    return recipe.effort_of_record[config.provider]


def target_serving(config: RunConfig, recipe: SimRecipe) -> str:
    """The request option the target's binding sends, as recorded: `fast`, `priority` or `standard`.

    `_multiagent_pi.roles.role_model` (the `target_thinking` binding) sends Claude Opus `speed: fast` with the
    fast-mode beta header (`fast`) and GPT-5.6-sol/terra `service_tier="priority"` (`priority`): part of the clinic's
    setting of record, since its time limit is wall-clock. `_eval_runner.target_model` (the `target_reasoning`
    binding) sends neither (`standard`).
    """
    if recipe.target_binding != "target_thinking":
        return "standard"
    target_id = f"{config.provider}/{config.model}"
    if target_id.startswith("anthropic/") and "opus" in target_id:
        return "fast"
    if target_id.startswith(("openai/gpt-5.6-sol", "openai/gpt-5.6-terra")):
        return "priority"
    return "standard"


def model_settings(config: RunConfig, recipe: SimRecipe) -> str:
    """The target's model settings as `--print-info` prints them: its reasoning dial and value, and `target_serving`."""
    effort = target_effort(config, recipe)
    return f"{BINDING_DIAL[recipe.target_binding]}={effort} serving={target_serving(config, recipe)}"


def harness_env(
    recipe: SimRecipe, max_turns: int, max_ahead: int, time_limit: int, effort: str
) -> dict[str, str]:
    """The episode's harness knobs under the paper launchers' names (their `run_settings.json` `knobs`).

    What a paper runs root recorded for its cells, so a config can be compared knob for knob with the paper's
    launch records (`tests/test_sim_instruments.py` pins each instrument against `KNOBS_OF_RECORD`).
    """
    return {
        "BURST": str(recipe.burst),
        "MAX_AHEAD": str(max_ahead),
        "MAX_TURNS": str(max_turns),
        "PETRI_GENERATE_TIMEOUT": str(recipe.generate_timeout_s),
        "PETRI_SAMPLE_TIME_LIMIT": str(time_limit),
        BINDING_DIAL[recipe.target_binding]: effort,
        **recipe.dials,
        **recipe.knobs,
    }


def recipe_limits(recipe: SimRecipe) -> tuple[int, int, int, int | None]:
    """`(max_turns, max_ahead, time_limit, retry_time_limit)` of one episode of `recipe`.

    The recipe's own step budget and first-pass limit; `MAX_AHEAD` is the instrument's pinned value, else the
    drivers' derived one (`max_ahead_of_record`); the long-limit retry applies only when it is longer than the
    first pass.
    """
    max_ahead = (
        recipe.max_ahead
        if recipe.max_ahead is not None
        else max_ahead_of_record(recipe.max_turns, len(recipe.spec.agents))
    )
    retry = (
        recipe.retry_time_limit_s
        if recipe.retry_time_limit_s is not None
        and recipe.retry_time_limit_s > recipe.time_limit_s
        else None
    )
    return recipe.max_turns, max_ahead, recipe.time_limit_s, retry


def _config_record(config: RunConfig, recipe: SimRecipe, epoch: int) -> dict[str, Any]:
    """The episode's full recorded configuration (`world/config.json`; compared on a DONE-skip).

    `paper_instrument` / `on_paper_instrument` / `off_paper` keep the record schema every env's readers share
    (`_harness.readout.base_row`, `_offpaper`): a recipe always plays the instrument of its paper cell, so they
    read the instrument, true and empty.
    """
    max_turns, max_ahead, time_limit, retry_time_limit = recipe_limits(recipe)
    effort = target_effort(config, recipe)
    return {
        "eval": config.eval,
        "scenario": config.scenario,
        "formation": config.formation,
        "cell": recipe.spec.name,
        "framing": recipe.framing,
        "harness": "sim",
        "fake_pi": False,
        "fake_model": config.fake_model,
        "model": config.model,
        "provider": config.provider,
        "epoch": epoch,
        "pi_version": None,
        "commit": git_commit(),
        "inspect_ai": inspect_ai.__version__,
        "mitigation": recipe.mitigation,
        "instrument": recipe.instrument,
        "paper_instrument": recipe.instrument,
        "on_paper_instrument": True,
        "off_paper": [],
        "max_turns": max_turns,
        "max_ahead": max_ahead,
        "burst": recipe.burst,
        "knobs": dict(recipe.knobs),
        "auditor": recipe.auditor,
        "auditor_model": recipe.auditor_model,
        "judge_model": recipe.judge_model,
        "world_tool_label": recipe.world_tool_label,
        "time_limit_s": time_limit,
        "retry_time_limit_s": retry_time_limit,
        "max_connections": recipe.max_connections,
        "generate_timeout_s": recipe.generate_timeout_s,
        "target_binding": recipe.target_binding,
        "target_effort": effort,
        "target_serving": target_serving(config, recipe),
        "dials": dict(recipe.dials),
        "harness_env": harness_env(recipe, max_turns, max_ahead, time_limit, effort),
    }


def _fake_model(recipe: SimRecipe, live: dict[str, Any] | None = None) -> Model:
    """Inspect's `mockllm` bound to a wait loop: every turn calls the world's clock lever, so the day resolves.

    Offline plumbing only (no key, no network): the world, router, driver, sidecar and run-dir banking are
    exercised end to end while every seat just waits the shift out. A generation whose toolset lacks the
    lever (an escalation prompt) gets a one-word text reply.

    Under an instrument without the hero's burst cap (`burst > FAKE_BOUNDED_BURST`) the stand-in ends its
    turn in text after `FAKE_BOUNDED_BURST` answered calls in a row, and for good once the live router
    (`live["router"]`) reports the day over: a seat that waits forever would otherwise hold the floor in one
    unbounded burst (no other seat, and so no debrief, is ever served), and an unbounded wrap-up (`standard`)
    would never drain. The hero's burst cap and two wrap-up grants bound it there, so hero plays the
    original stand-in unchanged.
    """
    tool, args = recipe.fake_wait_call
    self_bounded = recipe.burst > FAKE_BOUNDED_BURST

    def answered_in_a_row(messages: list[Any]) -> int:
        """Tool results since the seat's last user/system message (the calls of its current burst)."""
        count = 0
        for message in reversed(messages):
            role = getattr(message, "role", None)
            if role in ("user", "system"):
                break
            count += int(role == "tool")
        return count

    def outputs(
        _input: list[Any], tools: list[Any], _choice: Any, _config: Any
    ) -> ModelOutput:
        if self_bounded:
            router = (live or {}).get("router")
            if (router is not None and bool(router.is_over())) or answered_in_a_row(
                _input
            ) >= FAKE_BOUNDED_BURST:
                return ModelOutput.from_content("mockllm/model", "Standing by.")
        if any(getattr(t, "name", None) == tool for t in tools):
            return ModelOutput.for_tool_call(
                "mockllm/model", tool_name=tool, tool_arguments=args
            )
        return ModelOutput.from_content("mockllm/model", "acknowledged")

    return get_model("mockllm/model", custom_outputs=outputs, memoize=False)


def resolve_keys(config: RunConfig, recipe: SimRecipe, target_key: str) -> SimKeys:
    """The target's key (resolved by `runner.prepare`) plus the house roles' Anthropic key.

    An Anthropic target shares one key with the house roles (`KEYS=*:<key>`, as the paper's Anthropic-target
    runs did).
    A non-Anthropic target needs `ANTHROPIC_API_KEY` for the house roles as well: the api_key escalation
    auditor generates live. On an `auditor="none"` recipe (clinic) the house roles are never called, so a
    missing Anthropic key falls back to `UNUSED_HOUSE_KEY`.

    Raises:
        SystemExit: A non-Anthropic target on an escalation recipe with no Anthropic key.
    """
    if config.fake_model:
        return SimKeys("fake-not-used", "fake-not-used")
    if config.provider == "anthropic":
        return SimKeys(target_key, target_key)
    names = KEY_ENV_VARS["anthropic"]
    house = next((v for n in names if (v := os.environ.get(n, "").strip())), "")
    if house:
        return SimKeys(target_key, house)
    if recipe.auditor == "none":
        return SimKeys(target_key, UNUSED_HOUSE_KEY)
    raise SystemExit(
        f"a {config.provider} target on --harness sim needs {' or '.join(names)} as well: the house "
        f"auditor ({recipe.auditor_model}, escalation mode) and judge ({recipe.judge_model}) keep their "
        "Anthropic models on the Anthropic key, exactly as the paper's runs with a non-Anthropic target did"
    )


def _role_env(
    config: RunConfig, recipe: SimRecipe, keys: SimKeys, effort: str
) -> dict[str, str]:
    """The env the vendored role binders read: each role's key, the target's reasoning dial, the serving pins.

    The `target_thinking` binding pins `GPT_FAST=1 OPUS_NO_FAST=0` (`target_serving`), so a launching shell cannot
    change what the clinic target is sent. As the paper's runs keyed them: an Anthropic target puts every role on
    its key (`KEYS=*:<var>`); any other target keys only the house auditor and judge
    (`KEYS=auditor:<var>,judge:<var>`) and reads its own
    provider key from the environment (`_eval_runner.target_model` / `roles.role_model` pass `api_key=None`
    for non-Anthropic ids), so the Anthropic key never reaches another provider's API.
    """
    env: dict[str, str] = {BINDING_DIAL[recipe.target_binding]: effort}
    if recipe.target_binding == "target_thinking":
        env.update({"GPT_FAST": "1", "OPUS_NO_FAST": "0"})
    if config.fake_model:
        return env
    if config.provider == "anthropic":
        env.update({KEY_ENV: keys.target, "KEYS": f"*:{KEY_ENV}"})
    else:
        env.update(
            {
                HOUSE_KEY_ENV: keys.house,
                "KEYS": f"auditor:{HOUSE_KEY_ENV},judge:{HOUSE_KEY_ENV}",
                TARGET_KEY_ENV[config.provider]: keys.target,
            }
        )
    return env


def _roles(
    config: RunConfig,
    recipe: SimRecipe,
    keys: SimKeys,
    live: dict[str, Any] | None = None,
) -> dict[str, str | Model]:
    """The paper's `{auditor, target, judge}` role map, bound exactly as its driver bound it.

    Call inside `_environ(_role_env(...))`: both binders read the dials and keys from the environment.
    `live` is the fake stand-in's view of the episode's router (see `_fake_model`).
    """
    if config.fake_model:
        return {
            role: _fake_model(recipe, live) for role in ("auditor", "target", "judge")
        }
    target_id = f"{config.provider}/{config.model}"
    if recipe.target_binding == "target_reasoning":
        # The api_key drivers (single-user, 16-user, limits-off): string-bound house roles (keyed by `KEYS` in
        # run_resumable), the target pre-bound by `_eval_runner.target_model` at `TARGET_REASONING`.
        return {
            "auditor": recipe.auditor_model,
            "target": target_model(target_id),
            "judge": recipe.judge_model,
        }
    # the paper's clinic driver: every role through `_multiagent_pi.build_roles`; `api_key` binds the
    # Anthropic roles only (a non-Anthropic target reads its provider key from the environment).
    built: Any = build_roles(  # pyright: ignore[reportUnknownVariableType]
        recipe.auditor_model, target_id, recipe.judge_model, api_key=keys.house
    )
    return cast(dict[str, str | Model], dict(built))


@contextmanager
def _environ(values: dict[str, str], clear: Iterable[str] = ()) -> Iterator[None]:
    """Export `values` (and unset `clear`) for the duration of the block, restoring the environment after."""
    cleared = [name for name in clear if name not in values]
    saved = {name: os.environ.get(name) for name in (*values, *cleared)}
    os.environ.update(values)
    for name in cleared:
        os.environ.pop(name, None)
    try:
        yield
    finally:
        for name, prior in saved.items():
            if prior is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = prior


def _sidecar(log_dir: Path, cell: str, epoch: int) -> dict[str, Any] | None:
    """The durable world ledger `<log_dir>/worlds/<cell>__e<epoch>.json` (`_metadata_sidecar`'s layout)."""
    path = log_dir / "worlds" / f"{quote(cell, safe='')}__e{epoch}.json"
    if not path.exists():
        return None
    return cast(dict[str, Any], json.loads(path.read_text()))


def _driver_steps(log_dir: Path) -> int | None:
    """The scripted driver's own resume-step count, from its completion line in the eval log."""
    try:
        for path in latest_logs_per_task(list(log_dir.glob("*.eval"))):
            for sample in read_eval_log_samples(
                str(path), resolve_attachments=False, all_samples_required=False
            ):
                match = re.search(
                    r"after (\d+) resume steps", sample.output.completion or ""
                )
                if match:
                    return int(match.group(1))
    except Exception:  # noqa: BLE001 — telemetry only; never fail a banked episode over it
        return None
    return None


def auth_error(text: str) -> bool:
    """A provider error that refuses the key: 401 `authentication_error` or 403 `permission_error`.

    E.g. `Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', ...}}`, or an
    OpenRouter key limit (`Error code: 403 - ...`).
    """
    return (
        "authentication_error" in text
        or "permission_error" in text
        or text.startswith(("Error code: 401", "Error code: 403"))
    )


def rule_t_counts(events: Iterable[object]) -> RuleTCounts:
    """Rule T over one sample's events: the paper's provider-error scan's per-sample logic, verbatim.

    (`errscan.py` `scan_eval`, of the paper's analysis scripts: supplementary material.)

    Every target `ModelEvent` is attributed to its agent by the `trajectory` span it sits in (spans numbered
    in order of appearance; an event outside any trajectory span counts as agent -1). A failed call extends
    that agent's failure run and a successful one resets it; every 4th consecutive failure is one lost turn
    (the harness gives up on that resume). Errors are classed as the paper classed them: `rate_limit_error`
    or a leading `429` -> 429, `overloaded_error` -> 529, anything else -> other. `failed_auth` (not the
    paper's) counts the other-class errors that reject the key (`auth_error`).
    """
    items = list(events)
    traj: dict[str, int] = {}
    for e in items:
        if (
            type(e).__name__ == "SpanBeginEvent"
            and getattr(e, "name", None) == "trajectory"
        ):
            traj[str(cast(Any, e).id)] = len(traj)
    ok = fail = f429 = f529 = fother = fauth = lost = 0
    streak: collections.Counter[int] = collections.Counter()
    maxstreak = 0
    lost_agents: set[int] = set()
    for e in items:
        if type(e).__name__ != "ModelEvent" or getattr(e, "role", None) != "target":
            continue
        a = traj.get(str(getattr(e, "span_id", None)), -1)
        error = getattr(e, "error", None)
        if error:
            fail += 1
            t = str(error)
            if "rate_limit_error" in t or "429" in t[:5]:
                f429 += 1
            elif "overloaded_error" in t:
                f529 += 1
            else:
                fother += 1
                fauth += int(auth_error(t))
            streak[a] += 1
            maxstreak = max(maxstreak, streak[a])
            if streak[a] % 4 == 0:
                lost += 1
                lost_agents.add(a)
        else:
            ok += 1
            streak[a] = 0
    return RuleTCounts(
        ok, fail, f429, f529, fother, lost, maxstreak, len(lost_agents), fauth
    )


def scan_rule_t(log_dir: Path) -> RuleTCounts | None:
    """Rule T over the episode's most complete eval log (errored samples skipped, as the paper's scan did).

    `None` when the log cannot be read; the episode still banks (the counts are telemetry for readers).
    """
    totals: list[RuleTCounts] = []
    try:
        for path in latest_logs_per_task(list(log_dir.glob("*.eval"))):
            for sample in read_eval_log_samples(
                str(path), resolve_attachments=False, all_samples_required=False
            ):
                if sample.error is not None:
                    continue
                totals.append(rule_t_counts(sample.events))
    except Exception:  # noqa: BLE001 — telemetry only; a banked episode never fails over it
        return None
    if not totals:
        return None
    return RuleTCounts(
        ok_calls=sum(t.ok_calls for t in totals),
        failed_calls=sum(t.failed_calls for t in totals),
        failed_429=sum(t.failed_429 for t in totals),
        failed_529=sum(t.failed_529 for t in totals),
        failed_other=sum(t.failed_other for t in totals),
        rule_t_lost_turns=sum(t.rule_t_lost_turns for t in totals),
        max_consecutive_failures=max(t.max_consecutive_failures for t in totals),
        agents_with_lost_turn=sum(t.agents_with_lost_turn for t in totals),
        failed_auth=sum(t.failed_auth for t in totals),
    )


def _rule_t_fields(counts: RuleTCounts | None) -> dict[str, Any]:
    """The `DONE.json` fields of the scan (all `None`, plus a flag, when the log could not be read)."""
    if counts is None:
        names = [f for f in RuleTCounts.__dataclass_fields__]
        return {**dict.fromkeys(names), "rule_t_scanned": False}
    return {**asdict(counts), "rule_t_scanned": True}


def _play(
    config: RunConfig,
    recipe: SimRecipe,
    epoch: int,
    keys: SimKeys,
    run_dir: Path,
    expected: dict[str, Any],
    max_turns: int,
    max_ahead: int,
    time_limit: int,
) -> tuple[dict[str, Any], Path, float]:
    """One attempt in a fresh run dir; returns `(world, log_dir, wall_s)` or raises `SimEpisodeIncomplete`."""
    if run_dir.exists():
        keep_prior_attempt(run_dir)
        shutil.rmtree(run_dir)
    world_dir = run_dir / "world"
    world_dir.mkdir(parents=True)
    log_dir = run_dir / "logs"
    spec = replace(recipe.spec, epoch_offset=epoch - 1)
    effort = str(expected["target_effort"])
    env = {
        **recipe.dials,
        **recipe.knobs,
        "MAX_AHEAD": str(max_ahead),
        "MAX_CONNECTIONS": str(recipe.max_connections),
        "PETRI_GENERATE_TIMEOUT": str(recipe.generate_timeout_s),
        **_role_env(config, recipe, keys, effort),
    }
    live: dict[str, Any] = {}

    def watched_factory(
        cell: ScenarioSpec, nstate: dict[str, Any], seed_epoch: int
    ) -> Any:
        # The fake stand-in reads the live router's `is_over` (the last router built is the sample's own).
        live["router"] = recipe.router_factory(cell, nstate, seed_epoch)
        return live["router"]

    router_factory: RouterFactory = (
        watched_factory if config.fake_model else recipe.router_factory
    )

    if recipe.auditor == "none" and not config.fake_model:
        print(
            f"[{config.eval} {recipe.spec.name} e{epoch}] the inspect header's model {recipe.auditor_model} is the "
            f"house auditor/judge seat, unused here (auditor=none: a scripted driver, no call); the target is "
            f"{config.provider}/{config.model}",
            flush=True,
        )
    started = time.monotonic()
    with _environ(env, clear=CLEARED_ENV):
        roles = _roles(config, recipe, keys, live)
        task = task_with(
            build_task(
                [spec],
                max_turns=max_turns,
                router_factory=router_factory,
                burst=recipe.burst,
                world_tool_label=recipe.world_tool_label,
                name=recipe.dataset_name,
                auditor=recipe.auditor,
            ),
            name=recipe.spec.name,
        )
        ok = run_resumable(
            [task],
            log_dir=str(log_dir),
            roles=roles,
            label=f"{config.eval} {recipe.spec.name} e{epoch}",
            epochs=1,
            max_connections=recipe.max_connections,
            max_samples=1,
            time_limit=time_limit,
            metadata_sidecars={"world": dict},
            keep_alive=False,
            display=os.environ.get("EVAL_SIM_DISPLAY", "plain"),
            log_level=os.environ.get("EVAL_SIM_LOG_LEVEL", "warning"),
        )
    wall = round(time.monotonic() - started, 1)
    world = _sidecar(log_dir, recipe.spec.name, epoch)
    (world_dir / "config.json").write_text(json.dumps(expected, indent=2))
    if world is not None:
        (world_dir / "summary.json").write_text(json.dumps(world, indent=2))
    if not ok:
        raise SimEpisodeIncomplete(
            f"{run_dir.name}: eval_set reported the episode incomplete (errored out of its retries)"
        )
    if world is None:
        raise SimEpisodeIncomplete(f"{run_dir.name}: no world ledger was banked")
    return world, log_dir, wall


def keep_prior_attempt(run_dir: Path) -> Path | None:
    """Archive an earlier attempt's run dir as `<run dir>.attempt<k>.tar.gz` beside it before it is replaced.

    A run dir that exists when an attempt starts holds an earlier attempt: an interrupted container's (a Modal
    preemption restarts the episode from scratch) or the instrument's own first pass before its long-limit retry.
    Its inspect logs are the only record of that attempt's model usage, so they are archived, not deleted. The
    reports never read the archive (a file, not a run dir), and a DONE-skip never reaches here. Archiving is best
    effort: a failure is printed and the replay goes ahead.
    """
    if not any(run_dir.rglob("*.eval")):
        return None
    k = 1
    while (archive := run_dir.with_name(f"{run_dir.name}.attempt{k}.tar.gz")).exists():
        k += 1
    try:
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(run_dir, arcname=f"{run_dir.name}.attempt{k}")
    except (
        OSError,
        tarfile.TarError,
    ) as exc:  # best effort: never block the replay itself
        archive.unlink(missing_ok=True)
        print(
            f"[{run_dir.name}] could not archive the earlier attempt ({exc!r})",
            flush=True,
        )
        return None
    print(
        f"[{run_dir.name}] kept the earlier attempt's logs as {archive.name}",
        flush=True,
    )
    return archive


def require_bankable(
    world: dict[str, Any], run_dir: Path, max_turns: int, time_limit: int
) -> None:
    """Raise `SimEpisodeIncomplete` unless the world ended at its horizon (the paper's completeness rules).

    Refused: a sample that unwound (a time-limit cancel; the one outcome a long-limit retry replays), a driver
    step cap, and any other driver end than `world horizon reached` (a fleet quarantine: every seat at the
    harness's failed-resume cap, e.g. a key the provider rejects). The paper scores only worlds whose
    `driver_ended` starts with `world horizon reached`, whatever the clock read when the driver stopped.
    """
    if world.get("unwound"):
        raise SimEpisodeIncomplete(
            f"{run_dir.name}: the sample unwound (time limit or error) before the world finished "
            f"(time limit {time_limit} s)",
            unwound=True,
        )
    if world.get("driver_step_capped"):
        raise SimEpisodeIncomplete(
            f"{run_dir.name}: the scripted driver hit its {max_turns}-step cap before the world's end signal"
        )
    ended = str(world.get("driver_ended") or HORIZON_END)
    if not ended.startswith(HORIZON_END):
        raise SimEpisodeIncomplete(
            f"{run_dir.name}: the driver ended without reaching the world's horizon ({ended[:240]})"
        )


def run_episode(
    config: RunConfig, recipe: SimRecipe, epoch: int, keys: SimKeys
) -> dict[str, Any]:
    """Run (or skip) one simulated episode; returns the DONE record. Raises `SimEpisodeIncomplete`."""
    check_mitigation(config, recipe)
    max_turns, max_ahead, time_limit, retry = recipe_limits(recipe)
    run_dir = run_dir_for(config, recipe, epoch)
    done_path = run_dir / "DONE.json"
    expected = _config_record(config, recipe, epoch)
    if done_path.exists():
        prior: dict[str, Any] = json.loads(
            (run_dir / "world" / "config.json").read_text()
        )
        drift = configuration_drift(prior, expected)
        if drift:
            raise SystemExit(
                f"{run_dir} was produced by a different configuration ({drift}); use a fresh --runs-root"
            )
        record: dict[str, Any] = json.loads(done_path.read_text())
        record["skipped"] = True
        return record
    limits = [time_limit] + ([retry] if retry is not None else [])
    for attempt, limit in enumerate(limits, start=1):
        try:
            world, log_dir, wall = _play(
                config,
                recipe,
                epoch,
                keys,
                run_dir,
                expected,
                max_turns,
                max_ahead,
                limit,
            )
            require_bankable(world, run_dir, max_turns, limit)
        except SimEpisodeIncomplete as exc:
            if not exc.unwound or attempt == len(limits):
                raise
            print(
                f"[{config.eval} {recipe.spec.name} e{epoch}] unwound under the {limit} s limit; the "
                f"instrument's long-limit retry replays it from scratch at {limits[attempt]} s",
                flush=True,
            )
            continue
        record = {
            "ended": str(world.get("driver_ended") or HORIZON_END),
            "rounds": _driver_steps(log_dir),
            "error_turns": 0,
            "crashed": [],
            "counts": {},
            "sim_clock": world.get("clock"),
            "wall_s": wall,
            "harness": "sim",
            "instrument": recipe.instrument,
            "attempts": attempt,
            "time_limit_banked_s": limit,
            **_rule_t_fields(scan_rule_t(log_dir)),
            "skipped": False,
        }
        done_path.write_text(json.dumps(record, indent=2))
        return record
    raise AssertionError("unreachable: the last attempt either banks or raises")


def episode_wall_budget_s(recipe: SimRecipe) -> int:
    """The longest wall clock one episode of `recipe` may legitimately take (a Modal timeout must cover it).

    Its sample time limit, plus the long-limit retry when the instrument has one, plus `EPISODE_MARGIN_S`.
    inspect's own in-sample error retries can exceed it; a container killed there is an unbanked episode
    that the next dispatch pass reruns.
    """
    _, _, first, retry = recipe_limits(recipe)
    return first + (retry or 0) + EPISODE_MARGIN_S


def modal_timeout_needed_s(eval_name: str, pairs: Iterable[tuple[str, ...]]) -> int:
    """The per-episode Modal timeout a sim matrix needs: the largest `episode_wall_budget_s` over its cells.

    `pairs` are `(scenario, formation)` or `(scenario, formation, mitigation)` (a mitigation arm's recipe
    carries its own time limits). Imports the eval's `cells` lazily (the harness itself never depends on an eval).

    Raises:
        ValueError: Not a simulated-harness eval, or a cell whose recipe the eval refuses (an arm that does not
            apply to the formation).
    """
    if eval_name not in ("api_key", "clinic"):
        raise ValueError(
            f"--harness sim exists for api_key and clinic only, not {eval_name!r}"
        )

    def recipe_of(cell: tuple[str, ...]) -> SimRecipe:
        scenario, formation = cell[0], cell[1]
        mitigation = cell[2] if len(cell) > 2 else NONE
        if eval_name == "api_key":
            from api_key.cells import build_sim_recipe as api_key_recipe

            return api_key_recipe(scenario, formation, mitigation=mitigation)
        from clinic.cells import build_sim_recipe as clinic_recipe

        return clinic_recipe(scenario, formation, mitigation=mitigation)

    budgets = [episode_wall_budget_s(recipe_of(cell)) for cell in pairs]
    return max(budgets, default=EPISODE_MARGIN_S)


def run_epochs(
    config: RunConfig,
    build_recipe: Callable[[], SimRecipe],
    epochs: Iterable[int],
    api_key: str,
) -> int:
    """Run every epoch of one (scenario, formation) in sequence; returns the number left unbanked."""
    recipe = build_recipe()
    keys = resolve_keys(config, recipe, api_key)
    incomplete = 0
    label = (
        f"{config.eval} {config.scenario} {config.formation} [sim {recipe.instrument}]"
        + ("" if config.mitigation == NONE else f" [{config.mitigation}]")
    )
    for epoch in epochs:
        try:
            record = run_episode(config, recipe, epoch, keys)
        except SimEpisodeIncomplete as exc:
            incomplete += 1
            print(
                f"[{label} e{epoch}] INCOMPLETE ({exc}) — no DONE.json written; rerun this command to redo it",
                flush=True,
            )
            continue
        status = "SKIP" if record.get("skipped") else record["ended"]
        print(
            f"[{label} e{epoch}] {status} steps={record['rounds']} clock={record['sim_clock']} "
            f"wall={record['wall_s']}s lost_turns={record.get('rule_t_lost_turns')}",
            flush=True,
        )
    return incomplete
