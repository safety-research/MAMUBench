"""Target execution extracted from the original simulated harness's auditor.py (one trajectory per target: nothing rolls back)."""

from collections.abc import Iterable

from inspect_ai.agent import Agent, AgentState
from inspect_ai.event import Event, SpanBeginEvent
from inspect_ai.log import transcript
from inspect_ai.tool import ToolInfo
from inspect_ai.util import span, span_id_provider

from .petri import (
    Channel,
    History,
    TargetContext,
    Trajectory,
    channel,
    make_span_id_provider,
)


async def _run_target(
    target: Agent,
    ch: Channel,
    tools: list[ToolInfo] | None,
    history: History,
    span_id: str,
) -> None:
    async with span(name="target", id=span_id):
        _transcript_info_seed_instructions()
        await _run_trajectory(target, ch, tools, history.root)


async def _run_trajectory(
    target: Agent,
    ch: Channel,
    tools: list[ToolInfo] | None,
    trajectory: Trajectory,
) -> None:
    """Run the target's trajectory to completion."""
    state = AgentState(messages=[])
    context = TargetContext(ch, trajectory, messages=state.messages, tools=tools)
    async with span(name="trajectory", id=trajectory.span_id):
        with span_id_provider(make_span_id_provider(trajectory)):
            await target(state, context)


def _events_outside_spans(events: list[Event], root_ids: Iterable[str]) -> list[Event]:
    """Return events that are not under (or the begin/end of) any span in `root_ids`."""
    inside = set(root_ids)
    for e in events:
        if isinstance(e, SpanBeginEvent) and e.parent_id in inside:
            inside.add(e.id)
    return [e for e in events if e.span_id not in inside]


def _transcript_info_seed_instructions() -> None:
    seed = channel().state.seed_instructions
    transcript().info(f"### Seed Instructions\n\n{seed}")
