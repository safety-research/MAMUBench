"""N-target audit solver: one auditor live-drives N walled-off model targets over ONE shared world.

Ported from the authors' research code. One auditor maintains a
single consistent shared world and routes every staging call to a selected agent (via a routing-proxy
controller — see `routing.py`). Each agent gets its own
`(Channel, Controller, History)` triple; the auditor and the N targets run as concurrent `anyio` tasks;
per-agent target timelines plus one combined auditor timeline are emitted for the judge/viewer.

Agent ids are "A", "B", "C", … (`agent_ids(n)`); each target timeline is keyed on `f"agent{ID}-target"`
(`audit_name(id)`), which the judge/viewer parse to score every agent independently.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

import anyio
from inspect_ai.agent import Agent, AgentState
from inspect_ai.event import timeline_build
from inspect_ai.log import transcript
from inspect_ai.model import user_prompt
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolInfo
from inspect_ai.util import span
from shortuuid import uuid

from ._target import (
    _events_outside_spans,
    _run_target,
)
from .petri import Channel, Controller, History, init_controller

#: What a per-sample `setup(state)` returns: (auditor_factory, targets, target_tools, finalize).
#: `auditor_factory(controllers)` builds the auditor closing over the {id: Controller} map;
#: `targets` is the list of N `target_agent()` model instances; `finalize(state)` runs after the audit.
TargetToolsets = list[ToolInfo] | dict[str, list[ToolInfo]]

NSetup = tuple[
    Callable[[dict[str, Controller]], Agent],
    "list[Agent] | dict[str, Agent]",
    TargetToolsets,
    Callable[[TaskState], None],
]


UNWOUND_STORE_KEY = "multiagent_pi:unwound"
"""Store flag set by the solver's finally block: `True` when the sample is unwinding (a time-limit cancel or error cancelled the task group before the world ran its course), `False` on a clean finish. The scorer reads it to refuse limit-truncated nights (see `TruncatedNightError` in `audit.py`)."""


def agent_ids(n: int) -> tuple[str, ...]:
    """Agent ids "A", "B", …, for `n` targets (n <= 26)."""
    if not 1 <= n <= 26:
        raise ValueError(f"n must be in 1..26, got {n}")
    return tuple(chr(ord("A") + i) for i in range(n))


def audit_name(agent_id: str) -> str:
    """The timeline name the judge/viewer key on for an agent id."""
    return f"agent{agent_id}"


@solver
def n_model_audit_solver(*, setup: Callable[[TaskState], NSetup]) -> Solver:
    """One auditor (voicing the shared world + any operators) driving N walled-off model targets.

    Args:
        setup: Called once per sample (per epoch) to produce `(auditor_factory, targets, target_tools, finalize)`. `auditor_factory(controllers)` must build the auditor with the routed tools (closing over the {id: Controller} map) and `eager_resume=False`. `targets` are plain `target_agent()` instances; `target_tools` are the synthetic tools threaded into every Channel and `_run_target` call. `finalize(state)` stashes per-sample ground truth for the scorer.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        auditor_factory, targets, target_tools, finalize = setup(state)
        # Dict targets carry the spec's OWN agent ids (e.g. a single-agent "S" steward); a plain list
        # keeps the legacy positional "A", "B", ... naming (all existing 4/8-agent specs coincide).
        if isinstance(targets, dict):
            ids = tuple(targets.keys())
            targets_by_id = dict(targets)
        else:
            ids = agent_ids(len(targets)) if targets else ()
            targets_by_id = dict(zip(ids, targets, strict=True))
        if isinstance(target_tools, dict):
            missing = set(ids) - set(target_tools)
            extra = set(target_tools) - set(ids)
            if missing or extra:
                raise ValueError(
                    "per-agent target tools must match target ids exactly "
                    f"(missing={sorted(missing)}, extra={sorted(extra)})"
                )
            tools_by_id = target_tools
        else:
            tools_by_id = {i: target_tools for i in ids}
        # A batch post-pass can deliberately return no targets for an item that has no
        # resumable target timeline. Finalize that sample as an explicit coverage gap;
        # do not turn item N of M into an exception that cancels the other samples.
        if not ids:
            finalize(state)
            return state
        seed = user_prompt(state.messages).text

        channels = {
            i: Channel(
                seed_instructions=seed,
                seed_tools=tools_by_id[i],
                metadata=state.metadata,
            )
            for i in ids
        }
        controllers = {i: Controller(channels[i]) for i in ids}
        # The global controller is read by the auditor agent only for prompt-building (seed/metadata,
        # identical across channels); the routed tools drive each agent via explicit controllers. The
        # auditor_factory sets a routing-proxy controller as the real global (see routing.RoutingController).
        init_controller(controllers[ids[0]])

        auditor = auditor_factory(controllers)
        auditor_state = AgentState(messages=state.messages)
        histories = {i: History() for i in ids}
        spans = {i: uuid() for i in ids}
        span_auditor = uuid()

        try:
            async with anyio.create_task_group() as tg:
                tg.start_soon(
                    _run_auditor_n,
                    auditor,
                    auditor_state,
                    span_auditor,
                    tuple(controllers.values()),
                )
                for i in ids:
                    tg.start_soon(
                        _run_target,
                        targets_by_id[i],
                        channels[i],
                        tools_by_id[i],
                        histories[i],
                        spans[i],
                    )
        finally:
            try:
                _add_n_timelines(histories, spans)
            except Exception:
                # Never let a timeline-build failure mask the run outcome.
                pass
            # Durable outputs must be written on the CANCELLATION path too: a sample time limit cancels
            # the task group and skips everything after this block, and `finalize` is what persists the
            # world metadata + sidecar. Every worldless-but-scored N=16 mesh episode (six cells lost
            # exactly on the slow tail) was a time-limit cancel unwinding past a finalize that
            # sat below this block. `finalize` is synchronous, so cancellation cannot interrupt it here.
            state.output = auditor_state.output
            state.messages[:] = auditor_state.messages
            if sys.exc_info()[0] is None:
                state.store.set(UNWOUND_STORE_KEY, False)
                finalize(state)
            else:
                # Unwinding (time-limit cancel or error): persist best-effort, and never let a finalize
                # failure replace the exception inspect uses to account for the sample's outcome. Stamp
                # the store so the scorer can refuse to treat a limit-truncated night as a legitimate
                # outcome: inspect ends limit-hit samples GRACEFULLY (error=None) and still scores them,
                # which is how never-ran nights during a provider outage once entered a corpus as clean
                # zeros.
                state.store.set(UNWOUND_STORE_KEY, True)
                try:
                    finalize(state)
                except Exception:
                    pass

        return state

    return solve


async def _run_auditor_n(
    auditor: Agent, state: AgentState, span_id: str, controllers: tuple[Controller, ...]
) -> None:
    """Run the auditor, then end EVERY conversation so all targets unblock and exit (idempotent)."""
    async with span(name="auditor", id=span_id):
        transcript().info(
            f"### Seed Instructions\n\n{controllers[0].state.seed_instructions}"
        )
        await auditor(state)
        for ctrl in controllers:
            await ctrl.end_conversation()


def _add_n_timelines(histories: dict[str, History], spans: dict[str, str]) -> None:
    """Add one per-agent target timeline plus one combined auditor timeline."""
    events = list(transcript().events)
    for i in histories:
        outside = {id(event) for event in _events_outside_spans(events, [spans[i]])}
        transcript().add_timeline(
            timeline_build(
                events=[event for event in events if id(event) not in outside],
                name=f"{audit_name(i)}-target",
            )
        )
    auditor_events = _events_outside_spans(
        list(transcript().events), list(spans.values())
    )
    auditor_timeline = timeline_build(events=auditor_events, name="auditor")
    transcript().add_timeline(auditor_timeline)


__all__ = [
    "n_model_audit_solver",
    "agent_ids",
    "audit_name",
    "NSetup",
    "TargetToolsets",
]
