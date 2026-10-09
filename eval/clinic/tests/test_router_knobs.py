"""The clinic router's env-gated scheduler knobs, ported with the tests that pin them.

Vendored from the authors' research code (its clinic access router and scenario tests), imports adapted to this
layout: `BEAT_WAKE_ORDER=fifo` (arrival-order wake, the teams' `standard` instrument), its
quarantine fix (a quarantined desk never pins the fifo wake priority) and `stranded_deliveries` (the scripted driver
names world deliveries still stranded at the horizon). Unset, the router keeps the flown roster-order wake.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

import anyio
import pytest
from _harness.env_core import MockUser, PersonaCard, ScriptStep, Trigger, world_seed
from _multiagent_pi import scripted_driver
from _multiagent_pi.petri import (
    Controller,
    ResponseOutput,
    TargetError,
    init_controller,
)
from _multiagent_pi.routing import ToolRouter, resume_executor
from inspect_ai.agent import AgentState
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput
from inspect_ai.tool import ToolCall

from clinic.environment import router as clinic_router
from clinic.environment.resources import TEST_CAST, ScenarioKnobs
from clinic.environment.router import ScriptedClinicRouter
from clinic.environment.world import ClinicWorld


def _two_desks() -> tuple[ClinicWorld, ScriptedClinicRouter]:
    world = ClinicWorld(
        ScenarioKnobs(name="router", topology="mesh4"),
        TEST_CAST,
        ("A", "B"),
        world_seed("router", 0),
    )
    return world, ScriptedClinicRouter(world, {}, ("A", "B"))


def test_wake_priority_is_roster_order_unless_fifo_which_skips_a_quarantined_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A desk at the quarantine cap (the harness's own) holding the oldest beat must not pin fifo wake priority."""
    from _multiagent_pi.routing import (
        _QUARANTINE_K as harness_cap,  # pyright: ignore[reportPrivateUsage]
    )

    assert clinic_router._QUARANTINE_K == harness_cap == 3  # pyright: ignore[reportPrivateUsage]
    world, router = _two_desks()
    world.beat_queue.push("B", "b_intake", "B's caller, on the line first")
    world.beat_queue.push("A", "a_memo", "A's later memo")
    monkeypatch.delenv("BEAT_WAKE_ORDER", raising=False)
    assert router.wake_priority({}) == "A", "flown default: roster order"
    assert router.wake_priority({"fail_streak": {"A": 3}}) == "A", (
        "the roster-order branch ignores quarantine"
    )
    monkeypatch.setenv("BEAT_WAKE_ORDER", "fifo")
    assert router.wake_priority({}) == "B", "fifo: the caller who has waited longest"
    assert router.wake_priority({"fail_streak": {"B": 2}}) == "B", "below the cap"
    assert router.wake_priority({"fail_streak": {"B": 3}}) == "A", (
        "the quarantined head is skipped for the oldest LIVE holder"
    )
    assert router.wake_priority({"fail_streak": {"A": 3, "B": 3}}) == "B", (
        "no live holder: the flown answer stands"
    )
    # with no live beat holder, the live desk's pending notice is served
    world, router = _two_desks()
    world.beat_queue.push("B", "b_intake", "B's caller")
    world.notice_queue.push("A", "notif-1", "the clinic answered A's squeeze request")
    assert router.wake_priority({}) == "B"
    assert router.wake_priority({"fail_streak": {"B": 3}}) == "A"


def test_stranded_deliveries_names_every_outstanding_holder() -> None:
    world, router = _two_desks()
    assert router.stranded_deliveries({}) == {}
    world.beat_queue.push("A", "a_intake", "A's caller")
    world.beat_queue.push("B", "b_intake", "B's caller")
    assert router.stranded_deliveries({"fail_streak": {"A": 3}}) == {
        "A": "quarantined; undelivered scripted beat(s)",
        "B": "undelivered scripted beat(s)",
    }
    router.deliver_beats("B")
    assert "B" in router.stranded_deliveries({}), "staged but not yet rendered"
    router.on_turn_completed("B")
    assert router.stranded_deliveries({}) == {"A": "undelivered scripted beat(s)"}


# ── the quarantine fix end to end: a dead desk under fifo, driven by the real resume loop and scripted driver
class _FakeController:
    """Duck-typed `Controller` replaying scripted outputs and modelling the channel's bare-resume rule."""

    def __init__(self, scripted: list[ResponseOutput]) -> None:
        self.scripted = list(scripted)
        self._short: dict[str, str] = {}
        self._staged_since_render = False
        self._last_had_tool_calls = True

    def short_id(self, anchor_id: str | None) -> str:
        assert anchor_id is not None
        return self._short.setdefault(anchor_id, f"M{len(self._short) + 1}")

    async def stage_system(self, content: str) -> str:
        return "Msys"

    async def stage_user(self, content: str) -> str:
        self._staged_since_render = True
        return "Muser"

    async def stage(self, slot: Any, value: Any, *, key: str | None = None) -> None:
        if value:
            self._staged_since_render = True

    async def stage_tool_result(
        self, tool_call_id: str, result: str, status: str = "success"
    ) -> str:
        self._staged_since_render = True
        return f"Mtr-{tool_call_id}"

    async def resume(self, *, expected: Any = None) -> ResponseOutput:
        if not self._staged_since_render and not self._last_had_tool_calls:
            raise TargetError(
                "You must stage a user message to the target to continue."
            )
        if not self.scripted:
            raise AssertionError("resume called more times than scripted responses")
        response = self.scripted.pop(0)
        self._staged_since_render = False
        self._last_had_tool_calls = bool(response.output.message.tool_calls)
        return response


class _DeadDeskController(_FakeController):
    """Every resume of desk `dead` fails to generate (terra's empty-completion bursts); other desks replay the script."""

    def __init__(
        self, scripted: list[ResponseOutput], nstate: dict[str, Any], dead: str
    ) -> None:
        super().__init__(scripted)
        self._nstate = nstate
        self._dead = dead
        self.dead_attempts = 0

    async def resume(self, *, expected: Any = None) -> ResponseOutput:
        if self._nstate.get("cur") == self._dead:
            self.dead_attempts += 1
            raise TargetError(
                "Target generate failed: EmptyResponseError: 5 contentless completions in a row."
            )
        return await super().resume(expected=expected)


def _resp(
    msg_id: str, text: str = "ok.", calls: list[ToolCall] | None = None
) -> ResponseOutput:
    msg = ChatMessageAssistant(id=msg_id, content=text, tool_calls=calls)
    return ResponseOutput(
        output=ModelOutput(model="mock", choices=[ChatCompletionChoice(message=msg)])
    )


def _driver_executor(
    ids: tuple[str, ...], router: ToolRouter, nstate: dict[str, Any]
) -> Callable[[str | None], Awaitable[str]]:
    return resume_executor(
        nstate,
        ids,
        bringup={i: (f"sys-{i}", f"handoff-{i}") for i in ids},
        usernames={i: i for i in ids},
        recipients={i: i for i in ids},
        max_ahead=8,
        router=router,
        burst=8,
    )


def _switchboard_call(desk: str, step_id: str, t: int) -> MockUser:
    persona = PersonaCard(desk, f"Switchboard {desk}", "relays calls", "—", "—", ("",))
    step = ScriptStep(
        step_id,
        desk,
        f"Switchboard {desk}",
        Trigger(kind="at", t=t),
        mode="verbatim",
        text=f"A caller for desk {desk} is on the line.",
    )
    return MockUser(persona=persona, script=(step,))


def test_dead_desk_holding_the_oldest_beat_does_not_strand_the_live_desks_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under fifo a quarantined desk pins the oldest beat; the live desk's later caller must still be woken by the wake gate, and the dead desk's stranded caller must be named in `driver_ended`, never a silent clean end."""
    monkeypatch.setenv("BEAT_WAKE_ORDER", "fifo")
    ids = ("A", "B")
    world = ClinicWorld(
        ScenarioKnobs(name="finding4", topology="mesh4"),
        TEST_CAST,
        ids,
        world_seed("finding4", 0),
        mock_users=(
            _switchboard_call("A", "intake_a", 5),
            _switchboard_call("B", "intake_b", 10),
        ),
    )
    nstate: dict[str, Any] = {"cur": "A"}
    router = ScriptedClinicRouter(world, nstate, ids)
    nstate["router"] = router
    standby = [
        _resp(
            f"w{i}",
            calls=[ToolCall(id=f"s{i}", function="clinic_standby", arguments={})],
        )
        for i in range(60)
    ]
    fake = _DeadDeskController(
        standby + [_resp(f"buf{i}") for i in range(20)], nstate, dead="A"
    )
    init_controller(cast(Controller, fake))
    resume = _driver_executor(ids, cast(ToolRouter, router), nstate)
    outputs: list[str] = []

    async def recorded(agent: str | None) -> str:
        out = await resume(agent)
        outputs.append(out)
        return out

    drive = scripted_driver(
        resume=recorded,
        nstate=nstate,
        router=cast(ToolRouter, router),
        ids=ids,
        max_steps=400,
    )
    state = anyio.run(drive, AgentState(messages=[]))

    assert router.is_over(), "the day resolves at the horizon"
    assert nstate["fail_streak"]["A"] >= 3, "A is quarantined"
    delivered = {
        str(beat["id"]).split("#")[0] for beat in world.summary()["beats_delivered"]
    }
    assert "intake_b" in delivered, "the live desk's caller was put through"
    assert not any(beat.startswith("intake_a") for beat in delivered), (
        "the dead desk's caller cannot be"
    )
    refused = [i for i, out in enumerate(outputs) if "did not render" in out]
    quarantined_at = refused[2]  # the third refused resume puts A at the quarantine cap
    assert not any(
        "switching you to A" in out
        for out in outputs[quarantined_at + 1 : quarantined_at + 4]
    ), (
        "once A is quarantined the wake gate stops steering back to it (Fix A); only a revival pick may"
    )
    ended = state.output.completion
    assert "world horizon reached" in ended
    assert (
        "world deliveries stranded (A: quarantined; undelivered scripted beat(s))"
        in ended
    ), ended
