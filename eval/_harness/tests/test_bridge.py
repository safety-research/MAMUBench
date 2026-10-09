"""Bridge unit tests: manifest, mailbox, wait budget, delivery discipline — offline, deterministic."""

from __future__ import annotations

from pathlib import Path

import pytest
from api_key import cells as api_key_cells
from clinic import cells as clinic_cells

from _harness.tests.conftest import bridge_for


@pytest.mark.parametrize(
    ("eval_name", "formation", "world_tools", "seats", "prompt_marker"),
    [
        (
            "api_key",
            "team",
            {"labctl_status", "labctl_dashboard", "labctl_wait"},
            4,
            "labctl",
        ),
        ("api_key", "team_silent", {"labctl_status"}, 4, "labctl"),
        ("api_key", "coordinator", {"labctl_status"}, 1, "labctl"),
        ("clinic", "team", {"clinic_standby", "clinic_book"}, 17, "Standing procedure"),
        ("clinic", "team_silent", {"clinic_standby"}, 17, "Standing procedure"),
        ("clinic", "coordinator", {"clinic_standby"}, 1, "Standing procedure"),
    ],
)
def test_the_seats_see_the_console_surface_and_a_mailbox_only_in_a_team(
    tmp_path: Path,
    eval_name: str,
    formation: str,
    world_tools: set[str],
    seats: int,
    prompt_marker: str,
) -> None:
    bridge = bridge_for(tmp_path, eval_name, formation)
    manifest = bridge.tools_manifest()
    names = {t["name"] for t in manifest}
    assert not names & {"read", "bash", "edit", "write"} and world_tools <= names
    assert ({"SendMessage", "find_agents"} <= names) == (formation == "team")
    # f_all_closed: the clinic's work-in tool leaves the surface
    assert "clinic_squeeze_request" not in names
    for tool in manifest:
        assert set(tool) == {"name", "description", "parameters"}
        assert tool["parameters"]["type"] == "object"
    assert len(bridge.ids) == seats
    for seat in bridge.ids:
        prompt = bridge.seat_system_prompt(seat)
        assert prompt is not None and prompt_marker in prompt


def test_first_wake_stages_handoff_then_mail_then_beats(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "api_key", "team")
    seat, peer = bridge.ids[0], bridge.ids[1]
    assert (
        bridge.dispatch(
            peer, "SendMessage", {"to": bridge.usernames[seat], "message": "ping"}
        )
        == "Delivered."
    )
    delivery = bridge.begin_turn(seat)
    assert delivery.first_wake
    assert delivery.prompt.startswith(bridge._handoffs[seat][:40])  # pyright: ignore[reportPrivateUsage]
    assert f"[message from {bridge.usernames[peer]}] ping" in delivery.prompt
    bridge.end_turn(delivery, rendered=True, had_tool_calls=True)
    second = bridge.begin_turn(seat)  # nothing staged: the bare [HH:MM] stamp
    assert not second.first_wake
    assert second.prompt.startswith("[") and second.prompt.endswith("]")
    bridge.end_turn(second, rendered=True)


def test_bounced_turn_requeues_mail_and_handoff(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "api_key", "team")
    seat, peer = bridge.ids[0], bridge.ids[1]
    bridge.dispatch(
        peer, "SendMessage", {"to": bridge.usernames[seat], "message": "ping"}
    )
    bridge.end_turn(bridge.begin_turn(seat), rendered=False)
    assert bridge.pending_for(seat)
    retry = bridge.begin_turn(seat)
    assert retry.first_wake and "ping" in retry.prompt


def test_sendmessage_validation_errors(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "api_key", "team")
    seat = bridge.ids[0]
    assert "unknown recipient" in bridge.dispatch(
        seat, "SendMessage", {"to": "nobody", "message": "x"}
    )
    assert "must be non-empty" in bridge.dispatch(
        seat, "SendMessage", {"to": " ", "message": "x"}
    )
    assert "your own username" in bridge.dispatch(
        seat, "SendMessage", {"to": bridge.usernames[seat], "message": "x"}
    )


def test_api_key_wait_budget_clamps_then_denies(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "api_key", "team", budget=30)
    seat = bridge.ids[0]
    delivery = bridge.begin_turn(seat)
    before = bridge.clock()
    bridge.dispatch(seat, "labctl_wait", {"minutes": 200})  # clamped to 30
    assert bridge.clock() - before <= 30
    assert (
        bridge.dispatch(seat, "labctl_wait", {"minutes": 5})
        == api_key_cells.WAIT_LIMIT_ERROR
    )
    bridge.end_turn(delivery, rendered=True)
    second = bridge.begin_turn(seat)  # the budget resets next turn
    assert (
        bridge.dispatch(seat, "labctl_wait", {"minutes": 1})
        != api_key_cells.WAIT_LIMIT_ERROR
    )
    bridge.end_turn(second, rendered=True)


def test_clinic_standby_budget_denies_when_spent(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "clinic", "coordinator", budget=25)
    seat = bridge.ids[0]
    delivery = bridge.begin_turn(seat)
    spent, denied = 0, False
    for _ in range(20):
        out = bridge.dispatch(seat, "clinic_standby", {})
        if out == clinic_cells.WAIT_LIMIT_ERROR:
            denied = True
            break
        spent = bridge.clock()
    assert denied, "standby never hit the per-turn budget"
    assert spent <= 25 + 20  # one 20-minute edge step may straddle the budget line
    bridge.end_turn(delivery, rendered=True)


def test_clinic_idle_advance_creeps_by_standby_only(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "clinic", "coordinator", budget=None)
    before = bridge.clock()
    bridge.idle_nudge(10)
    assert 0 < bridge.clock() - before <= 20  # one edge step, never a raw drift


def test_api_key_finalize_is_idempotent(tmp_path: Path) -> None:
    bridge = bridge_for(tmp_path, "api_key", "team", budget=None)
    first = bridge.finalize()
    assert first is bridge.finalize()
    assert first["scenario"] == "stakes_100" and "jobs" in first


def test_unknown_formations_are_refused() -> None:
    with pytest.raises(ValueError, match="unknown formation"):
        api_key_cells.build_cell("stakes_100", "captain", 1)
    with pytest.raises(ValueError, match="unknown formation"):
        clinic_cells.build_cell("warfarin_inr_split", "meshfull", 1)
