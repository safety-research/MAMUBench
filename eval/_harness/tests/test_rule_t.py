"""Rule T, the paper's provider-error screen, on synthetic events (`sim.rule_t_counts`).

The logic is the paper's provider-error scan's (`scan_eval`) per-sample loop: target `ModelEvent`s attributed to agents by their `trajectory` span, a failure run per agent
reset by any success, one lost turn per 4 consecutive failures (the harness gives up on that resume), errors
classed 429 / 529 / other. These tests build real inspect events so the type-name dispatch is exercised too.
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai.event import Event, InfoEvent, ModelEvent, SpanBeginEvent
from inspect_ai.model import GenerateConfig, ModelOutput

from _harness import sim

RATE = "Error code: 429 - {'type': 'error', 'error': {'type': 'rate_limit_error'}}"
OVERLOAD = "Error code: 529 - {'type': 'error', 'error': {'type': 'overloaded_error'}}"
OTHER = "APIConnectionError: Connection error."


def _span(span_id: str) -> SpanBeginEvent:
    return SpanBeginEvent(id=span_id, name="trajectory")


def _gen(
    span_id: str | None, error: str | None = None, role: str = "target"
) -> ModelEvent:
    return ModelEvent(
        span_id=span_id,
        model="mockllm/model",
        role=role,
        input=[],
        tools=[],
        tool_choice="auto",
        config=GenerateConfig(),
        output=ModelOutput(),
        error=error,
    )


def test_four_consecutive_failures_are_one_lost_turn() -> None:
    events: list[Event] = [
        _span("a"),
        _span("b"),
        _gen("a"),
        _gen("a", RATE),
        _gen("a", RATE),
        _gen("a", OVERLOAD),
        _gen("a", OTHER),  # 4th in a row for agent 0 -> one lost turn
        _gen("a"),  # a success resets the run
        _gen("a", OTHER),
        _gen("a", OTHER),
        _gen("a", OTHER),  # 3 in a row: no lost turn
        _gen("b", OVERLOAD),
        # agent 0's run continues across agent 1's call: 4 in a row -> a second lost turn
        _gen("a", OTHER),
        _gen("b"),
    ]
    counts = sim.rule_t_counts(events)
    assert counts == sim.RuleTCounts(
        ok_calls=3,
        failed_calls=9,
        failed_429=2,
        failed_529=2,
        failed_other=5,
        rule_t_lost_turns=2,
        max_consecutive_failures=4,
        agents_with_lost_turn=1,
    )


def test_eight_in_a_row_is_two_lost_turns_and_non_target_roles_are_ignored() -> None:
    events: list[Event] = [
        _span("a"),
        *[_gen("a", RATE) for _ in range(8)],
        _gen("a", OVERLOAD, role="auditor"),
        _gen(None, OTHER, role="judge"),
        InfoEvent(data="not a model event"),
    ]
    counts = sim.rule_t_counts(events)
    assert (counts.failed_calls, counts.rule_t_lost_turns) == (8, 2)
    assert counts.max_consecutive_failures == 8 and counts.agents_with_lost_turn == 1


def test_events_outside_any_trajectory_span_pool_as_one_agent() -> None:
    events: list[Event] = [
        _gen("orphan-1", OTHER),
        _gen("orphan-2", OTHER),
        _gen(None, OTHER),
        _gen("orphan-1", OTHER),
    ]
    counts = sim.rule_t_counts(events)
    assert counts.rule_t_lost_turns == 1 and counts.agents_with_lost_turn == 1


def test_clean_episode_and_unreadable_log() -> None:
    clean = sim.rule_t_counts([_span("a"), _gen("a"), _gen("a")])
    assert clean.rule_t_lost_turns == 0 and clean.ok_calls == 2
    assert sim.scan_rule_t(Path("/nonexistent/logs")) is None
    fields = sim._rule_t_fields(None)  # pyright: ignore[reportPrivateUsage]
    assert fields["rule_t_scanned"] is False and fields["rule_t_lost_turns"] is None


AUTH = (
    "Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', "
    "'message': 'API key is invalid.'}, 'request_id': None}"
)
KEY_LIMIT = (
    "Error code: 403 - {'error': {'message': 'Key limit exceeded', 'code': 403}}"
)


def test_a_rejected_key_is_counted_apart_and_loses_no_turn() -> None:
    """A 401 / 403 is never retried: each failed resume is one failed call, so rule T sees no lost turn."""
    events: list[Event] = [
        _span("a"),
        _span("b"),
        _gen("a"),
        _gen("a", AUTH),
        _gen("b", KEY_LIMIT),
        _gen("a", AUTH),
        _gen("b", OTHER),
        _gen("a", AUTH),
    ]
    counts = sim.rule_t_counts(events)
    assert counts.failed_other == 5 and counts.failed_auth == 4
    assert counts.rule_t_lost_turns == 0 and counts.max_consecutive_failures == 3
    assert sim.auth_error(AUTH) and sim.auth_error(KEY_LIMIT)
    assert not any(sim.auth_error(t) for t in (RATE, OVERLOAD, OTHER))
