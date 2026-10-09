"""Offline, deterministic tests for the `ToolRouter` extension of `resume_executor` (no model/network calls).

Covers the observable contracts the gpu_contention experiment depends on:

- router=None keeps valid foreign-result behavior while protecting mechanically staged mailbox-validation
  failures from overwrite;
- the optional `withhold` hook gates resumption (switch to most-behind available, never rotate TO a withheld
  agent, no deadlock when all are withheld) and fires `on_withheld`;
- the optional `on_dm` / `on_deliver` hooks fire at the SendMessage capture + mailbox delivery sites;
- `ScenarioSpec.base_tools` / `target_tools()` and `AgentSpec.model_role` / `system_prompt` defaults;
- drain-before-end (the termination artifact): the day-over gate grants bounded final wrap-up
  turns while any agent holds staged-but-undelivered content, and the scripted driver drains before stopping
  at the horizon.

`ToolCall` / message objects are real Inspect objects; only the target `Controller` (the channel boundary) is
faked, recording what the resume tool stages and returning canned target outputs.

Ported from the authors' research code (the tests of the `routing.py` this directory carries byte-for-byte),
including the env-gated scheduler knobs'
tests (`BURST_YIELD_TOOLS`, `WAKE_ORDER`, `WRAPUP_GRANTS`, `WRAPUP_BRINGUP`: each pins the knob's effect AND
the unset flown default). Dropped here: the nine tests of the LLM auditor's tool allowlist (`audit._tools_for_mode`,
not shipped: this artifact runs the scripted driver only) and two `[cluster]`-line strip tests that expect an
older strip (`"ok"`), which the byte-preserving `strip_world_notification_lines` no longer produces (`"ok\n"`).
Also dropped, with the LLM auditor's tools they tested (`select_agent`, the `resume` tool, the guarded
`send_message` / `send_tool_call_result` / `end_conversation`, rollback-repair): their tests. Kept: a minimal set,
the knob tests plus each test that reaches a line or branch of the vendored stack that no other kept test reaches.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

import pytest
from _multiagent_pi import (
    AgentSpec,
    ScenarioSpec,
    User,
    build_seed,
    resume_executor,
    scripted_driver,
)
from _multiagent_pi.petri import (
    Controller,
    ResponseOutput,
    TargetError,
    init_controller,
)
from _multiagent_pi.routing import (
    _QUARANTINE_K,  # pyright: ignore[reportPrivateUsage]  # white-box: the wedge quarantine threshold
    _WRAPUP_GRANTS,  # pyright: ignore[reportPrivateUsage]  # white-box: the drain-before-end wrap-up budget
    DeadEpisodeError,
    undrained_agents,
)
from inspect_ai.agent import AgentState
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput
from inspect_ai.tool import ToolCall, ToolInfo, ToolParams


# ── test doubles ─────────────────────────────────────────────────────────────────────────────────────────
def _response(text: str, tool_calls: list[ToolCall] | None = None) -> ResponseOutput:
    """A real `ResponseOutput` wrapping one assistant message (optionally with tool calls)."""
    msg = ChatMessageAssistant(content=text, tool_calls=tool_calls)
    return ResponseOutput(
        output=ModelOutput(model="mock", choices=[ChatCompletionChoice(message=msg)])
    )


class _FakeController:
    """Minimal stand-in for the target `Controller`: records staging and returns queued resume outputs."""

    def __init__(self, responses: list[ResponseOutput]) -> None:
        self._responses = list(responses)
        self.staged_system: list[str] = []
        self.staged_user: list[str] = []
        self.staged_results: list[tuple[str, str, str]] = []
        self.resumes = 0
        self.ended = 0
        self._short: dict[object, str] = {}

    def short_id(self, anchor_id: object) -> str:
        if anchor_id not in self._short:
            self._short[anchor_id] = f"M{len(self._short) + 1}"
        return self._short[anchor_id]

    async def stage_system(self, content: str) -> str:
        self.staged_system.append(content)
        return self.short_id(("sys", len(self.staged_system)))

    async def stage_user(self, content: str) -> str:
        self.staged_user.append(content)
        return self.short_id(("user", len(self.staged_user)))

    async def stage(self, slot: object, value: object, *, key: object = None) -> object:
        return None

    async def stage_tool_result(
        self, tool_call_id: str, result: str, status: str = "success"
    ) -> str:
        self.staged_results.append((tool_call_id, result, status))
        return self.short_id(("tr", tool_call_id))

    async def resume(self, *, expected: object = None) -> ResponseOutput:
        self.resumes += 1
        return self._responses.pop(0)

    async def end_conversation(self) -> None:
        self.ended += 1


class _Router:
    """A `ToolRouter` with recording OPTIONAL hooks; `withheld_ids` drives the withhold gate.

    `route_map` maps a tool-call `function` name to a canned world result (else the call is foreign).
    """

    def __init__(
        self,
        *,
        withheld_ids: set[str] | None = None,
        route_map: dict[str, str] | None = None,
        notices: list[str] | None = None,
        wake_want: str | None = None,
        over: bool = False,
    ) -> None:
        self.withheld_ids = withheld_ids or set()
        self.route_map = route_map or {}
        self._notices = list(notices or [])
        self.wake_want = wake_want
        self.over = over
        self.resumed: list[str] = []
        self.dms: list[tuple[str, str, str]] = []
        self.undeliverable: list[tuple[str, str, str]] = []
        self.delivers: list[tuple[str, str, str]] = []
        self.turn_completeds: list[str] = []
        self.bounced: list[str] = []
        self.quarantined: list[tuple[str, int, str]] = []
        self.withheld_events: list[tuple[str, str]] = []

    # required surface
    def route(self, agent_id: str, call: ToolCall) -> str | None:
        return self.route_map.get(call.function)

    def on_resume(self, agent_id: str) -> None:
        self.resumed.append(agent_id)

    def notices(self) -> list[str]:
        drained, self._notices = self._notices, []
        return drained

    def summary(self) -> dict[str, Any]:
        return {"dms": len(self.dms), "delivers": len(self.delivers)}

    # optional hooks
    def withhold(self, agent_id: str) -> str | None:
        return "quiet window" if agent_id in self.withheld_ids else None

    def on_withheld(self, agent_id: str, reason: str) -> None:
        self.withheld_events.append((agent_id, reason))

    def on_dm(self, sender_id: str, to_id: str, msg: str) -> None:
        self.dms.append((sender_id, to_id, msg))

    def on_dm_undeliverable(self, sender_id: str, to_raw: str, msg: str) -> None:
        self.undeliverable.append((sender_id, to_raw, msg))

    def on_deliver(self, to_id: str, sender_id: str, msg: str) -> None:
        self.delivers.append((to_id, sender_id, msg))

    def on_turn_completed(self, agent_id: str) -> None:
        self.turn_completeds.append(agent_id)

    def on_resume_bounced(self, agent_id: str) -> None:
        self.bounced.append(agent_id)

    def quarantine(self, agent_id: str, streak: int, last_error: str = "") -> None:
        self.quarantined.append((agent_id, streak, last_error))

    def wake_priority(self, nstate: dict[str, Any]) -> str | None:
        return self.wake_want

    def is_over(self) -> bool:
        return self.over


class _PlainRouter:
    """A `ToolRouter` with ONLY the required surface — no optional hooks (getattr must tolerate their absence)."""

    def route(self, agent_id: str, call: ToolCall) -> str | None:
        return None

    def on_resume(self, agent_id: str) -> None:
        pass

    def notices(self) -> list[str]:
        return []

    def summary(self) -> dict[str, Any]:
        return {}


def _install(controller: _FakeController) -> None:
    init_controller(cast(Controller, controller))


def _resume_tool(
    nstate: dict[str, Any],
    ids: tuple[str, ...],
    *,
    router: object | None = None,
    allowed_recipients: dict[str, frozenset[str]] | None = None,
    max_ahead: int = 8,
    burst: int = 6,
) -> Callable[[str | None], Awaitable[str]]:
    """A `resume_executor` loop wired for tests (auto-bringup handoffs are trivial)."""
    return resume_executor(
        nstate,
        ids,
        bringup={i: (f"sys-{i}", f"handoff-{i}") for i in ids},
        usernames={i: i.lower() for i in ids},
        recipients={i.lower(): i for i in ids},
        allowed_recipients=allowed_recipients,
        max_ahead=max_ahead,
        router=router,  # type: ignore[arg-type]  # duck-typed ToolRouter test double
        burst=burst,
    )


async def _call(resume: Callable[[str | None], Awaitable[str]]) -> str:
    out = await resume(None)
    assert isinstance(out, str)
    return out


# ── withhold gate ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.anyio
async def test_withheld_current_switches_to_most_behind_available() -> None:
    router = _Router(withheld_ids={"A"})
    nstate: dict[str, Any] = {"cur": "A", "count": {"A": 0, "B": 3, "C": 1}}
    _install(_FakeController([]))  # no resume must occur
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router))
    assert nstate["cur"] == "C"  # most-behind of the AVAILABLE agents (B=3, C=1)
    assert "unavailable" in out and "switched to C" in out
    assert router.resumed == []  # withheld agent is never resumed
    assert router.withheld_events == [("A", "quiet window")]


@pytest.mark.anyio
async def test_balance_never_rotates_to_withheld_agent() -> None:
    # A is far ahead; the overall most-behind (B, count 0) is withheld, so balance must pick C instead.
    router = _Router(withheld_ids={"B"})
    nstate: dict[str, Any] = {"cur": "A", "count": {"A": 10, "B": 0, "C": 1}}
    _install(_FakeController([]))
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router, max_ahead=3))
    assert nstate["cur"] == "C"  # NOT B, even though B is most-behind
    assert "switched you to C" in out
    assert router.resumed == []


@pytest.mark.anyio
async def test_withhold_after_on_resume_switches_away_without_rendering() -> None:
    # R7 item-4 wake-gate: cur passes the PRE-advance withhold check, but on_resume advances the clock INTO a
    # silence window. The post-advance re-check must NOT render cur — log the withheld turn, re-queue cur's
    # drained mail (delivered post-window, never lost), and hand off to an available peer.
    class _WindowRouter(_PlainRouter):
        def __init__(self) -> None:
            self.resumed: list[str] = []
            self.withheld_events: list[tuple[str, str]] = []
            self._entered = False

        def on_resume(self, agent_id: str) -> None:
            self.resumed.append(agent_id)
            if agent_id == "B":
                self._entered = True  # B's wake advanced the clock into its window

        def withhold(self, agent_id: str) -> str | None:
            return "away" if (agent_id == "B" and self._entered) else None

        def on_withheld(self, agent_id: str, reason: str) -> None:
            self.withheld_events.append((agent_id, reason))

    router = _WindowRouter()
    ctrl = _FakeController([])  # no render must happen — the gate fires before resume()
    _install(ctrl)
    nstate: dict[str, Any] = {
        "cur": "B",
        "count": {"A": 0, "B": 0},
        "started": {"A": True, "B": True},
        "mailbox": {"A": [], "B": [("A", "sync on node 0")]},
    }
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert router.resumed == ["B"]  # on_resume ran (advanced the clock)…
    assert ctrl.resumes == 0  # …but the gate fired before any render
    assert router.withheld_events == [
        ("B", "away")
    ]  # withheld turn logged with the in-window clock
    assert nstate["mailbox"]["B"] == [
        ("A", "sync on node 0")
    ]  # mail re-queued, not lost
    assert nstate["cur"] == "A" and "unavailable" in out and "switched to A" in out


@pytest.mark.anyio
async def test_all_withheld_returns_advisory_without_resume() -> None:
    router = _Router(withheld_ids={"A", "B"})
    nstate: dict[str, Any] = {"cur": "A", "count": {"A": 0, "B": 0}}
    _install(_FakeController([]))
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router))
    assert "every other agent" in out  # advisory, no deadlock
    assert nstate["cur"] == "A"  # unchanged — nobody was resumed
    assert router.resumed == []
    assert router.withheld_events == [("A", "quiet window")]


# ── wake priority: router steers the next wake ahead of balance rotation ─────────────────────────────────


@pytest.mark.anyio
async def test_wake_priority_never_switches_to_withheld_target() -> None:
    router = _Router(wake_want="B", withheld_ids={"B"})
    _install(_FakeController([_response("ok")]))
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0},
        "started": {"A": True, "B": True},
    }
    await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert nstate["cur"] == "A"  # B withheld -> priority ignored, cur resumed
    assert router.resumed == ["A"]


@pytest.mark.anyio
async def test_calls_first_knob_wakes_the_waiting_caller_before_mail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A team scheduler with the balance gate off: mail-first let a chatty team's mail queue
    # starve the desks whose callers had waited longest. Under WAKE_ORDER=calls_first the wake-priority target
    # (C, a waiting caller) outranks the mail recipient (B) when cur needs nothing; the recipient is still
    # served as soon as no caller is waiting.
    monkeypatch.setenv("WAKE_ORDER", "calls_first")
    router = _Router(wake_want="C")
    _install(_FakeController([]))  # a switch returns before any resume
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0, "C": 0},
        "started": {"A": True, "B": True, "C": True},
        "mailbox": {"A": [], "B": [("carol", "freeing node 0")], "C": []},
    }
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router, burst=1))
    assert nstate["cur"] == "C" and "switching you to C" in out
    assert nstate["mailbox"]["B"] == [
        ("carol", "freeing node 0")
    ]  # still queued, not lost

    # No caller waiting -> the mail recipient is woken as before.
    router.wake_want = None
    nstate["cur"] = "A"
    _install(_FakeController([]))
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router, burst=1))
    assert nstate["cur"] == "B" and "deliver pending message" in out


def test_wrapup_grants_knob_makes_the_horizon_a_hard_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _multiagent_pi.routing import drainable_agents

    pending = {"A": "staged tool results", "B": "queued mail"}
    monkeypatch.delenv("WRAPUP_GRANTS", raising=False)
    assert (
        drainable_agents({"wrapup_grants": {"A": 1}}, pending) == pending
    )  # flown: 2 grants each
    assert drainable_agents({"wrapup_grants": {"A": 2}}, pending) == {
        "B": "queued mail"
    }
    monkeypatch.setenv("WRAPUP_GRANTS", "0")
    assert drainable_agents({}, pending) == {}  # nobody gets a frozen-clock turn


def test_wrapup_bringup_knob_drains_a_never_started_desk_holding_the_oldest_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _multiagent_pi.routing import undrained_agents

    router = _Router(
        wake_want="C"
    )  # C holds the oldest waiting call but was never woken
    nstate: dict[str, Any] = {
        "started": {"A": True, "B": True, "C": False},
        "mailbox": {},
    }
    monkeypatch.delenv("WRAPUP_BRINGUP", raising=False)
    assert (
        undrained_agents(nstate, ("A", "B", "C"), router) == {}
    )  # flown: never-started desks are skipped
    monkeypatch.setenv("WRAPUP_BRINGUP", "1")
    assert undrained_agents(nstate, ("A", "B", "C"), router) == {
        "C": "a queued world delivery (beat/notification)"
    }


def _send_fixture() -> tuple[_Router, _FakeController, dict[str, Any]]:
    """A's turn ends with a peer message to B (the burst ends on a send)."""
    send = ToolCall(
        id="m1", function="SendMessage", arguments={"to": "b", "message": "ping"}
    )
    router = _Router()
    controller = _FakeController([_response("pinging B", [send])])
    _install(controller)
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0, "C": 0},
        "started": {"A": True, "B": True, "C": True},
        "mailbox": {"A": [], "B": [], "C": []},
    }
    return router, controller, nstate


@pytest.mark.anyio
async def test_post_send_handoff_is_the_flown_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WAKE_ORDER", raising=False)
    router, _controller, nstate = _send_fixture()
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router, burst=1))
    assert (
        nstate["cur"] == "B" and "now switch to B" in out
    )  # the recipient is the next wake
    assert nstate["mailbox"]["B"] == [("a", "ping")]


@pytest.mark.anyio
async def test_calls_first_skips_the_post_send_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Otherwise every message would still jump the queue ahead of waiting callers: the wake gates decide.
    monkeypatch.setenv("WAKE_ORDER", "calls_first")
    router, _controller, nstate = _send_fixture()
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router, burst=1))
    assert nstate["cur"] == "A" and "now switch to B" not in out
    assert nstate["mailbox"]["B"] == [
        ("a", "ping")
    ]  # queued for the mail gate, never lost


@pytest.mark.anyio
async def test_wake_order_unset_keeps_mail_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WAKE_ORDER", raising=False)
    router = _Router(wake_want="C")
    _install(_FakeController([]))
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0, "C": 0},
        "started": {"A": True, "B": True, "C": True},
        "mailbox": {"A": [], "B": [("carol", "freeing node 0")], "C": []},
    }
    out = await _call(_resume_tool(nstate, ("A", "B", "C"), router=router, burst=1))
    assert (
        nstate["cur"] == "B" and "deliver pending message" in out
    )  # the flown default


@pytest.mark.anyio
async def test_bounced_resume_logs_neither_delivery_nor_turn_completed() -> None:
    # Item-2 core (G2): if a resume never renders (the empty-user re-prompt bounces and raises), the mail
    # staged for that wake must NOT be logged delivered and no turn is marked completed — deferring both logs
    # past the render is what stops a delivered-but-never-seen ghost from surviving in the world log.
    class _RaisingController(_FakeController):
        async def resume(self, *, expected: object = None) -> ResponseOutput:
            raise RuntimeError("bounced: no user message staged")

    _install(_RaisingController([]))
    router = _Router()
    nstate: dict[str, Any] = {
        "cur": "B",
        "count": {"A": 0, "B": 0},
        "started": {"A": True, "B": True},
        "mailbox": {"A": [], "B": [("A", "sync on node 0")]},
    }
    with pytest.raises(RuntimeError, match="bounced"):
        await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert router.delivers == []
    assert router.turn_completeds == []


@pytest.mark.anyio
async def test_target_error_bounce_requeues_mail_and_compensates() -> None:
    # R7 item-1: a resume the channel REFUSES (TargetError — auditor protocol slip) must not lose or false-log
    # the wake's drained content. The bounce handler calls on_resume_bounced (router re-queues beats/notifs),
    # re-queues the mail drained this wake, logs NO dm_delivered/turn_completed, and returns the advisory — so
    # the same content redelivers on the next real wake (delivered ⊆ rendered by construction).
    class _BounceController(_FakeController):
        async def resume(self, *, expected: object = None) -> ResponseOutput:
            raise TargetError("Missing tool results for tool call ids: {'x1'}")

    _install(_BounceController([]))
    router = _Router()
    nstate: dict[str, Any] = {
        "cur": "B",
        "count": {"A": 0, "B": 0},
        "started": {"A": True, "B": True},
        "mailbox": {"A": [], "B": [("A", "sync on node 0")]},
    }
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert router.bounced == ["B"]  # compensation hook fired
    assert (
        router.delivers == [] and router.turn_completeds == []
    )  # nothing rendered -> nothing logged
    assert nstate["mailbox"]["B"] == [
        ("A", "sync on node 0")
    ]  # mail re-queued, not lost
    assert "did not render" in out and "redeliver" in out  # advisory guides the auditor
    # count-all: any refusal reaching the except counts toward the stuck-streak (a render would reset it to 0)
    assert nstate.get("fail_streak", {}).get("B", 0) == 1


@pytest.mark.anyio
async def test_dead_episode_raises_deadepisodeerror_at_zero_renders() -> None:
    # DEAD-EPISODE GUARD (the fix for the W2 36%-empty bug): every agent quarantined with ZERO renders
    # in the whole episode = the target never came up (persistent generate failure — API window /
    # model_not_found). The guard RAISES DeadEpisodeError instead of returning the advisory, so the
    # sample ERRORS and eval_set retries — rather than the auditor ending status=success but EMPTY.
    # Single-agent (steward) edge: quarantined == all-agents-quarantined at K (guardrail 3).
    class _DeadCell(_FakeController):
        async def resume(self, *, expected: object = None) -> ResponseOutput:
            raise TargetError("Target generate failed: RetryError[APIStatusError 529]")

    _install(_DeadCell([]))
    router = _Router()
    nstate: dict[str, Any] = {"cur": "S", "count": {"S": 0}, "started": {"S": True}}
    for _ in range(
        _QUARANTINE_K - 1
    ):  # advisories until the last agent trips quarantine at K
        out = await _call(_resume_tool(nstate, ("S",), router=router, burst=1))
        assert "did not render" in out
    with pytest.raises(
        DeadEpisodeError, match="0 renders"
    ):  # Kth failure: 0 renders + S quarantined
        await _call(_resume_tool(nstate, ("S",), router=router, burst=1))


@pytest.mark.anyio
async def test_validate_first_refuses_resume_with_unstaged_foreign_results() -> None:
    # R7 item-1 cond. A (validate-first): after cur makes a foreign tool call, the resume loop records the owed
    # result; a resume BEFORE the auditor stages it is refused with ZERO side-effects (on_resume never runs) —
    # preventing the dominant "Missing tool results" bounce and its ghost clock/turn_granted. Clearing the
    # owe (as `EscalationHandler.resolve` does once it stages the answer) lifts the gate.
    fcall = ToolCall(id="f1", function="bash", arguments={"cmd": "ls"})
    router = (
        _Router()
    )  # route() returns None for bash -> a foreign call the auditor owes a result for
    _install(
        _FakeController([_response("running ls", tool_calls=[fcall]), _response("ok")])
    )
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0},
        "started": {"A": True, "B": True},
    }
    await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert nstate["owed_foreign"]["A"] == {
        "f1"
    }  # burst recorded the owed foreign result
    resumed_before = list(router.resumed)
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert "have not sent yet" in out and "f1" in out  # refused with guidance
    assert (
        router.resumed == resumed_before
    )  # ZERO side-effects: on_resume was NOT called
    # once the owe is cleared, the gate lets A resume again
    nstate["owed_foreign"]["A"].discard("f1")
    await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert router.resumed == [*resumed_before, "A"]


@pytest.mark.anyio
async def test_forced_wake_hard_overrides_selection_and_resumes_this_turn() -> None:
    # R6 S6 ENFORCEMENT: when the router's forced_wake reports a stale-inbound agent, the gate HARD-wakes it —
    # overrides cur and resumes it THIS turn (not an advisory the auditor can ignore forever). No stale
    # inbound can sit past the cap even while the auditor drives elsewhere.
    class _ForceRouter(_PlainRouter):
        def __init__(self) -> None:
            self.resumed: list[str] = []

        def on_resume(self, agent_id: str) -> None:
            self.resumed.append(agent_id)

        def forced_wake(self, nstate: dict[str, Any]) -> str | None:
            return "B"  # B has held unread inbound past the cap

    router = _ForceRouter()
    ctrl = _FakeController([_response("ok")])
    _install(ctrl)
    nstate: dict[str, Any] = {"cur": "A", "started": {"A": True, "B": True}}
    await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    # B was hard-woken + RESUMED this turn though the auditor had selected A (the enforcement invariant). The
    # postlude may then idle-switch away after B's turn — fine; the point is B's stale inbound was serviced now.
    assert router.resumed == ["B"]


# ── byte-identical no-router path (the wake redesign must not perturb plain pi audits) ───────────────────


@pytest.mark.anyio
async def test_no_router_hard_balance_forces_most_behind() -> None:
    _install(_FakeController([]))
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 20, "B": 0},
        "started": {"A": True, "B": True},
        "mailbox": {"A": [], "B": []},
    }
    out = await _call(_resume_tool(nstate, ("A", "B"), router=None, max_ahead=8))
    assert nstate["cur"] == "B" and "keep ALL agents alive" in out


@pytest.mark.anyio
async def test_is_over_ends_audit_without_resuming() -> None:
    # once the router reports the world is over, the resume tool must NOT resume (no spin at a frozen clock).
    router = _Router(over=True)
    _install(_FakeController([]))  # no response queued — a resume would raise
    nstate: dict[str, Any] = {"cur": "A", "started": {"A": True, "B": True}}
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router))
    assert "day has ended" in out and "end_conversation" in out
    assert router.resumed == []


@pytest.mark.anyio
async def test_quiet_collapse_hook_observes_rendered_turn_and_surfaces_notice() -> None:
    class _QuietRouter(_Router):
        def __init__(self) -> None:
            super().__init__()
            self.quiet_calls: list[tuple[str, tuple[ToolCall, ...], str | None]] = []

        def collapse_quiet(
            self,
            agent_id: str,
            tool_calls: tuple[ToolCall, ...],
            sent_to: str | None,
        ) -> str | None:
            self.quiet_calls.append((agent_id, tool_calls, sent_to))
            return "routine work advanced to the next edge"

    router = _QuietRouter()
    _install(_FakeController([_response("monitoring")]))
    nstate: dict[str, Any] = {"cur": "A", "started": {"A": True, "B": True}}

    out = await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))

    assert router.quiet_calls == [("A", (), None)]
    assert "[WORLD] routine work advanced to the next edge" in out


# ── resume with a router: world calls answered mechanically; router=None stages nothing ──────────────────


@pytest.mark.anyio
async def test_router_none_second_resume_not_blocked_by_owed_foreign() -> None:
    # Regression (R7 owed_foreign, shared-surface): the validate-first gate must NOT fire on the
    # router=None path. There the auditor uses the STOCK send_tool_call_result, which never populates or
    # clears owed_foreign; gating on it would refuse the agent forever after its first tool-using turn,
    # deadlocking every plain multi-agent pi audit (pi_peer_conflict, meal_safety_conflict, the
    # multiagent-pi-audit skill). A second resume of the same agent must proceed.
    ctrl = _FakeController(
        [
            _response(
                "turn 1",
                [ToolCall(id="b1", function="bash", arguments={"command": "ls"})],
            ),
            _response("turn 2", []),
        ]
    )
    _install(ctrl)
    nstate: dict[str, Any] = {"cur": "A", "started": {"A": True, "B": True}}
    tool = _resume_tool(nstate, ("A", "B"), router=None)
    await _call(tool)  # A makes a foreign (bash) tool call — pending, so cur stays A
    assert nstate.get("cur") == "A"
    out = await _call(tool)  # second resume of A must NOT be refused
    assert "have not sent yet" not in out
    assert ctrl.resumes == 2  # both resumes actually happened (no deadlock)


# ── scenario model: base_tools / target_tools + AgentSpec defaults ───────────────────────────────────────
_AGENT = AgentSpec(
    id="A",
    username="alex",
    display_name="Alex",
    cwd="/home/alex",
    role="r",
    handoff="h",
)
_USERS = (User(name="u", drives=("A",), persona="p"),)


def _spec(**kw: Any) -> ScenarioSpec:
    base = dict(
        name="s",
        interaction="tool_only",
        intro="i",
        world="w",
        agents=(_AGENT,),
        users=_USERS,
        observe="o",
    )
    base.update(kw)
    return ScenarioSpec(**base)  # type: ignore[arg-type]


def test_role_specific_tools_are_resolved_per_agent() -> None:
    seller = AgentSpec(
        id="S",
        username="merchant",
        display_name="Merchant",
        cwd="/merchant",
        role="seller",
        handoff="sell",
    )
    buy = ToolInfo(name="buy", description="buy", parameters=ToolParams())
    admin = ToolInfo(name="admin", description="admin", parameters=ToolParams())
    spec = _spec(
        agents=(_AGENT, seller),
        tools_by_agent={"A": (buy,), "S": (admin,)},
    )
    assert [t.name for t in spec.target_tools("A")] == ["buy"]
    assert [t.name for t in spec.target_tools("S")] == ["admin"]
    assert [t.name for t in spec.target_tools()] == ["buy", "admin"]
    assert {
        key: [tool.name for tool in tools]
        for key, tools in spec.solver_tools().items()  # type: ignore[union-attr]
    } == {"A": ["buy"], "S": ["admin"]}


def test_agent_spec_model_role_and_system_prompt_defaults() -> None:
    assert _AGENT.model_role == "target"
    assert _AGENT.system_prompt is None
    custom = AgentSpec(
        id="B",
        username="b",
        display_name="B",
        cwd="/b",
        role="r",
        handoff="h",
        model_role="target_b",
        system_prompt="custom system",
    )
    assert custom.model_role == "target_b"
    assert custom.system_prompt == "custom system"


# ── build_seed: base_tools worlds get scenario-neutral prose (no pi file tools / find_agents) ─────────────
_CLUSTER = (
    ToolInfo(name="submit_job", description="submit", parameters=ToolParams()),
    ToolInfo(name="SendMessage", description="dm", parameters=ToolParams()),
)


def test_build_seed_base_tools_world_drops_pi_prose() -> None:
    seed = build_seed(_spec(base_tools=_CLUSTER, comms=True))
    # the real tool surface is named; pi file tools + "answer every tool call" prose are gone
    assert "submit_job" in seed
    assert "read/bash/edit/write" not in seed
    assert "answer every tool call with send_tool_call_result" not in seed
    assert "MECHANICALLY" in seed
    # comms present (SendMessage) but no find_agents in this world
    assert "SendMessage" in seed
    assert "find_agents" not in seed


@pytest.mark.anyio
async def test_role_scoped_sendmessage_rejects_disallowed_recipient() -> None:
    sm = ToolCall(
        id="s1",
        function="SendMessage",
        arguments={"to": "b", "message": "private buyer coordination"},
    )
    router = _Router()
    ctrl = _FakeController([_response("sending", tool_calls=[sm])])
    _install(ctrl)
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0, "S": 0},
        "started": {"A": True, "B": True, "S": True},
    }
    tool = _resume_tool(
        nstate,
        ("A", "B", "S"),
        router=router,
        burst=1,
        allowed_recipients={
            "A": frozenset({"S"}),
            "B": frozenset({"S"}),
            "S": frozenset({"A", "B"}),
        },
    )
    await _call(tool)
    assert any(
        tcid == "s1" and "outside your allowed communication scope" in result
        for tcid, result, _status in ctrl.staged_results
    )
    assert nstate["mailbox"]["B"] == []
    assert router.dms == []
    assert router.undeliverable == [("A", "b", "private buyer coordination")]


@pytest.mark.anyio
async def test_unrestricted_sendmessage_preserves_legacy_self_send_behavior() -> None:
    sm = ToolCall(
        id="s1",
        function="SendMessage",
        arguments={"to": "a", "message": "note to self"},
    )
    router = _Router()
    ctrl = _FakeController([_response("sending", tool_calls=[sm])])
    _install(ctrl)
    nstate: dict[str, Any] = {
        "cur": "A",
        "count": {"A": 0, "B": 0},
        "started": {"A": True, "B": True},
    }
    await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    # Role scoping must not change unscoped self-send handling: it stays the legacy
    # validation error (owned mechanically by the mailbox validator), never a scope
    # denial and never an undeliverable-DM callback.
    assert router.dms == []
    assert router.undeliverable == []
    assert any(
        tcid == "s1"
        and result == "error: that's your own username — message a teammate."
        for tcid, result, _status in ctrl.staged_results
    )


# ── drain before end (the termination artifact): no episode ends over undelivered content ────────────────


@pytest.mark.anyio
async def test_day_over_switches_to_the_agent_holding_undelivered_content() -> None:
    # cur is clean but a peer still holds staged results: the gate must steer the auditor to the peer
    # (switch + advisory, no resume this call) instead of advising end_conversation.
    router = _Router(over=True)
    _install(_FakeController([]))  # the switch advisory returns before any resume
    nstate: dict[str, Any] = {
        "cur": "A",
        "started": {"A": True, "B": True},
        "anchors": {"B": ["mB"]},
        "anchor_calls": {"mB": ["w9"]},
    }
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router))
    assert nstate["cur"] == "B"
    assert "day has ended" in out and "w9" in out and "resume it" in out
    assert router.resumed == []  # advisory only — the drain is the auditor's next call


@pytest.mark.anyio
async def test_day_over_drains_queued_peer_mail_with_a_final_turn() -> None:
    # Queued peer mail is staged-but-undelivered content too: the recipient gets a final turn that
    # actually delivers the message (on_deliver fires) before the episode may end.
    router = _Router(over=True)
    ctrl = _FakeController([_response("got it, wrapping up")])
    _install(ctrl)
    nstate: dict[str, Any] = {
        "cur": "B",
        "started": {"A": True, "B": True},
        "mailbox": {"A": [], "B": [("a", "please cover pt_marsh")]},
    }
    out = await _call(_resume_tool(nstate, ("A", "B"), router=router, burst=1))
    assert ctrl.resumes == 1
    assert "[message from a] please cover pt_marsh" in ctrl.staged_user
    assert router.delivers == [("B", "A", "please cover pt_marsh")]
    assert "wrap-up pass is complete" in out


@pytest.mark.anyio
async def test_wrapup_budget_bounds_an_agent_that_never_stops_calling_tools() -> None:
    # A target that keeps issuing world calls at the frozen clock must not hold the episode open: after
    # `_WRAPUP_GRANTS` rendered wrap-up calls the GRANTING view stops steering to it — while the truth
    # predicate keeps it visible, so both advisories name the strand and promise the annotated end.
    router = _Router(route_map={"clinic_slots": "still 3 open slots"}, over=True)
    responses = [
        _response(
            f"t{i}", [ToolCall(id=f"w{i}", function="clinic_slots", arguments={})]
        )
        for i in range(_WRAPUP_GRANTS + 2)
    ]
    ctrl = _FakeController(responses)
    _install(ctrl)
    nstate: dict[str, Any] = {
        "cur": "A",
        "started": {"A": True},
        "anchors": {"A": ["m_prior"]},
        "anchor_calls": {"m_prior": ["w_prior"]},
    }
    tool = _resume_tool(nstate, ("A",), router=router, burst=1)
    out = await _call(tool)  # grant 1: renders, but the turn leaves new staged results
    assert "wrap-up continues" in out
    out = await _call(tool)  # grant 2: budget spent with results still staged
    assert "wrap-up budget is spent" in out and "annotated" in out
    out = await _call(tool)  # no grants left: the gate concedes without resuming again
    assert ctrl.resumes == _WRAPUP_GRANTS  # exactly the granted wrap-up turns
    assert "wrap-up budget is spent" in out and "end_conversation" in out


@pytest.mark.anyio
async def test_scripted_driver_drains_staged_content_before_stopping() -> None:
    # The auditorless path: the driver must not stop at the horizon while an agent holds staged results —
    # it keeps calling resume (the day-over gate turns those calls into wrap-up turns) and breaks only
    # once the fleet is drained.
    class _OverAfterFirstRender(_Router):
        def on_resume(self, agent_id: str) -> None:
            super().on_resume(agent_id)
            self.over = True  # the clock lands on the horizon during the first wake

    router = _OverAfterFirstRender(route_map={"clinic_slots": "3 open slots"})
    call = ToolCall(id="w1", function="clinic_slots", arguments={})
    ctrl = _FakeController([_response("searching", [call]), _response("done")])
    _install(ctrl)
    nstate: dict[str, Any] = {"cur": "A", "started": {"A": True}}
    resume = resume_executor(
        nstate,
        ("A",),
        bringup={"A": ("sys-A", "handoff-A")},
        usernames={"A": "a"},
        recipients={"a": "A"},
        router=router,  # type: ignore[arg-type]  # duck-typed ToolRouter test double
        burst=1,
    )
    drv = scripted_driver(
        resume=resume,
        nstate=nstate,
        router=router,  # type: ignore[arg-type]  # duck-typed ToolRouter test double
        ids=("A",),
        max_steps=10,
    )
    state = await drv(AgentState(messages=[]))
    assert ctrl.resumes == 2  # the horizon render + exactly one wrap-up turn
    assert undrained_agents(nstate, ("A",), router) == {}
    assert "world horizon reached" in (state.output.completion or "")


# ── BURST_YIELD_TOOLS: the world's "I'm waiting" verb ends a burst once answered ──────────────────────────
def _yield_fixture() -> tuple[_Router, _FakeController, dict[str, Any]]:
    """A router answering a write and a standby; the target writes, stands by, then writes again."""
    write = ToolCall(id="w1", function="world_write", arguments={})
    standby = ToolCall(id="s1", function="world_standby", arguments={})
    write2 = ToolCall(id="w2", function="world_write", arguments={})
    router = _Router(
        route_map={
            "world_write": "ok",
            "world_standby": "Waited at your desk until 08:20.",
        }
    )
    controller = _FakeController(
        [
            _response("working", [write]),
            _response("nothing to do, waiting", [standby]),
            _response("back to it", [write2]),
            _response("done"),
        ]
    )
    _install(controller)
    nstate: dict[str, Any] = {"cur": "A", "started": {"A": True, "B": True}}
    return router, controller, nstate


@pytest.mark.anyio
async def test_burst_yield_tool_ends_burst_after_being_answered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BURST_YIELD_TOOLS", "world_standby")
    router, controller, nstate = _yield_fixture()

    out = await _call(
        _resume_tool(nstate, ("A", "B"), router=router, burst=100, max_ahead=100)
    )

    # The write continued the burst; the standby was answered and then ENDED it — the target was never
    # asked for a third response, and the yield is named in the advisory.
    assert controller.resumes == 2
    assert [tcid for tcid, _, _ in controller.staged_results] == ["w1", "s1"]
    assert "A yielded (world_standby answered)" in out


@pytest.mark.anyio
async def test_burst_yield_tools_unset_keeps_the_burst_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BURST_YIELD_TOOLS", raising=False)
    router, controller, nstate = _yield_fixture()

    out = await _call(
        _resume_tool(nstate, ("A", "B"), router=router, burst=100, max_ahead=100)
    )

    # Byte-identical to the pre-knob loop: the standby is just another world call, so the burst runs on
    # through the second write and only the text-only response ends it.
    assert controller.resumes == 4
    assert [tcid for tcid, _, _ in controller.staged_results] == ["w1", "s1", "w2"]
    assert "yielded" not in out
