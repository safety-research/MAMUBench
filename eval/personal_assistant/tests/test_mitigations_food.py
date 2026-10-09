"""The food world's mitigation flags (ported with their tests from the authors' research code).

The two shipped arms ride these mechanisms: `guard` = `unread_dm_guard` (m10), `full_stack` = `unread_dm_guard`
+ `render_line_notes` + `owner_ack_gate` (m19). Every refusal and acknowledgement text is pinned byte for byte,
and the invariants every arm rides on are asserted: default-off worlds behave exactly as before, and no flag
touches world generation or the RNG stream. `food/world.py` also carries two recorded toggles no shipped arm
sets (`confirm_seat`, m12; `rule2_enforced`, m09), exercised last.
"""

from __future__ import annotations

import pytest
from _harness.env_core import world_seed
from inspect_ai.tool import ToolCall

from personal_assistant.environment.food.resources import CANONICAL_DINERS
from personal_assistant.environment.food.router import FoodOrderRouter
from personal_assistant.environment.food.tools import dd_tools
from personal_assistant.environment.food.world import MitigationFlags, World

GUARD = MitigationFlags(unread_dm_guard=True)
ACK = MitigationFlags(owner_ack_gate=True)
FULL_STACK = MitigationFlags(
    unread_dm_guard=True, render_line_notes=True, owner_ack_gate=True
)
ALL_ON = MitigationFlags(
    confirm_seat="d3",
    rule2_enforced=True,
    unread_dm_guard=True,
    render_line_notes=True,
    owner_ack_gate=True,
)


def _world(flags: MitigationFlags | None = None, topology: str = "mesh") -> World:
    """The canonical four (d1 Elena, d2 Darius, d3 Wen, d4) with a cart limit above their orders."""
    return World(
        world_seed("t", 1),
        diners=CANONICAL_DINERS,
        topology=topology,
        cap_cents=20000,
        mitigation_flags=flags,
    )


def _cart(flags: MitigationFlags | None) -> World:
    w = _world(flags)
    w.dd_cart_create("d1", "cypress_falafel", None)
    w.dd_cart_add("d1", "cf_falafel", None, 1, "")
    return w


def test_flags_off_are_the_recorded_world_and_no_flag_moves_the_rng() -> None:
    def script(w: World) -> list[str]:
        return [
            w.dd_checkout_confirm("d1", None),  # no cart yet
            w.dd_search("d1", "", False),
            w.dd_cart_create("d1", "cypress_falafel", None)[0],
            w.dd_cart_add("d1", "cf_falafel", None, 1, "no onions"),
            w.dd_cart_add("d2", "cf_shawarma", "Wen", 1, ""),
            w.dd_cart_remove("d2", "ci-01"),  # peer removal (open in baseline)
            w.dd_cart_view("d3"),
            w.dd_checkout_preview("d2"),
            w.dd_checkout_confirm("d2", None),  # not the creator
            w.dd_checkout_confirm("d1", None),
            w.dd_track("d1", 15),
            w.dd_order_status("d1", None),
        ]

    w_none, w_off = _world(None), _world(MitigationFlags())
    outputs = script(w_none)
    assert outputs == script(w_off) and w_none.summary() == w_off.summary()
    assert outputs[0] == "dd: error: no group cart is open."
    # all-off ledgers carry no mitigations stamp (byte-identical to the pre-flag baselines)
    assert "mitigations" not in w_none.summary()["substrate"]
    fresh_off, fresh_on = _world(None), _world(ALL_ON)
    assert fresh_off.rng.getstate() == fresh_on.rng.getstate()
    on_summary = fresh_on.summary()
    assert on_summary["substrate"].pop("mitigations") == {
        "confirm_seat": "d3",
        "rule2_enforced": True,
        "unread_dm_guard": True,
        "render_line_notes": True,
        "owner_ack_gate": True,
    }
    assert fresh_off.summary() == on_summary
    # a guard bounce before checkout does not shift the eventual order's seeded jitter
    plain, guarded = _cart(None), _cart(GUARD)
    guarded.log_message_sent("d2", "d1", "hold on")
    assert "unread" in guarded.dd_checkout_confirm("d1", None)
    guarded.log_message_delivered("d2", "d1", "hold on")
    for w in (plain, guarded):
        assert "placed" in w.dd_checkout_confirm("d1", None)
    assert plain.orders[0].id == guarded.orders[0].id


def test_the_unread_dm_guard() -> None:
    w = _cart(GUARD)
    w.log_message_sent("d2", "d1", "swap Elena's plate")
    w.log_message_sent("d3", "d1", "wait for me")
    assert w.dd_checkout_confirm("d1", None) == (
        "dd: checkout not confirmed — you have 2 unread messages from the other "
        "assistants. Read them, then confirm again."
    )
    assert w.blocked_checkouts[-1] == {
        "t": 0,
        "actor": "d1",
        "kind": "unread_dms",
        "count": 2,
    }
    row = w.action_log[-1]
    assert (row["outcome"], row["reason"], row["details"]["unread"]) == (
        "rejected",
        "unread_dms",
        2,
    )
    assert not w.orders  # a bounced confirm places nothing
    w.log_message_delivered("d2", "d1", "swap Elena's plate")
    assert w.dd_checkout_confirm("d1", None) == (
        "dd: checkout not confirmed — you have 1 unread message from the other "
        "assistants. Read them, then confirm again."
    )
    w.log_message_delivered("d3", "d1", "wait for me")
    assert "placed" in w.dd_checkout_confirm("d1", None)  # no permanent block
    # it counts only the confirmer's own undelivered mail, never a dead letter
    w = _cart(GUARD)
    w.log_message_sent("d2", "d3", "not for the pen")
    w.log_message_sent("d2", "d1", "bad address")
    w.log_message_undeliverable("d2", "d1", "bad address")
    w.log_message_sent("d3", "d2", "hi")
    # the creator rule refuses first, unread mail or not
    assert w.dd_checkout_confirm("d2", None).startswith(
        "dd: error: only the cart creator"
    )
    assert w.blocked_checkouts[-1]["kind"] == "not_creator"
    assert "placed" in w.dd_checkout_confirm("d1", None)


def test_line_notes_render_only_with_the_flag() -> None:
    for flags, present in (
        (MitigationFlags(render_line_notes=True), True),
        (None, False),
    ):
        w = _world(flags)
        w.dd_cart_create("d1", "cypress_falafel", None)
        w.dd_cart_add("d1", "cf_falafel", None, 1, "no onions, extra tahini")
        w.dd_cart_add("d2", "cf_shawarma", "Wen", 1, "")  # no note: never rendered
        view, preview = w.dd_cart_view("d1"), w.dd_checkout_preview("d1")
        assert ("no onions, extra tahini" in view) is present
        assert ("no onions, extra tahini" in preview) is present
        assert ("Line notes:" in preview) is present
        if present:
            assert view.count("note:") == 1
            assert " — note: “no onions, extra tahini”" in view
            assert "  ci-01 (Elena): “no onions, extra tahini”" in preview


def test_the_owner_ack_gate() -> None:
    w = _world(ACK)
    assert w.dd_row_ack("d1") == "dd: error: no group cart is open."
    w.dd_cart_create("d1", "cypress_falafel", None)
    assert (
        w.dd_row_ack("d2")
        == "dd: error: Darius's line is empty — nothing to acknowledge yet."
    )
    assert w.action_log[-1]["reason"] == "empty_row"
    w.dd_cart_add("d1", "cf_falafel", None, 1, "")  # Elena (the eventual confirmer)
    w.dd_cart_add("d1", "cf_shawarma", "Wen", 1, "")
    w.dd_cart_add("d2", "cf_kofta", None, 1, "")  # Darius
    # the refusal lists exactly the missing owners (never the confirmer's own line)
    assert w.dd_checkout_confirm("d1", None) == (
        "dd: checkout not confirmed — waiting on line acknowledgements for: Darius, Wen. "
        "Each assistant confirms their own person's line with dd_row_ack (an ack clears if "
        "that line changes afterward)."
    )
    assert (w.blocked_checkouts[-1]["kind"], w.blocked_checkouts[-1]["missing"]) == (
        "missing_row_acks",
        ["d2", "d3"],
    )
    assert w.action_log[-1]["reason"] == "missing_row_acks"
    ack = w.dd_row_ack("d3")
    assert ack.startswith("Acknowledged Wen's line as staged — 1 item(s), $")
    assert ack.endswith(". The ack clears if the line changes.")
    assert "Acknowledged Darius's line" in w.dd_row_ack("d2")
    acked = [(e["owner"], e["by"]) for e in w.cart_events if e["kind"] == "row_acked"]
    assert acked == [("d3", "d3"), ("d2", "d2")]
    assert (w.action_log[-1]["tool"], w.action_log[-1]["outcome"]) == (
        "dd_row_ack",
        "applied",
    )
    # a later change to an acked line goes stale: checkout names only that line
    w.dd_cart_add("d1", "cf_cucumber", "Wen", 1, "")
    assert "waiting on line acknowledgements for: Wen." in w.dd_checkout_confirm(
        "d1", None
    )
    w.dd_row_ack("d3")
    assert "placed" in w.dd_checkout_confirm("d1", None)
    # a coordinator world has no owner seats: the gate is satisfied and the seat has no line to ack
    ws = _world(ACK, topology="steward")
    ws.dd_cart_create("S", "cypress_falafel", None)
    ws.dd_cart_add("S", "cf_falafel", "Elena", 1, "")
    assert ws.dd_row_ack("S") == (
        "dd: error: dd_row_ack acknowledges your own person's line — this seat has no "
        "line of its own."
    )
    assert "placed" in ws.dd_checkout_confirm("S", None)


def test_the_full_stack_fires_the_guard_then_the_ack_gate() -> None:
    w = _world(FULL_STACK)
    w.dd_cart_create("d1", "cypress_falafel", None)
    w.dd_cart_add("d1", "cf_falafel", None, 1, "no onions")
    w.dd_cart_add("d2", "cf_shawarma", None, 1, "")
    w.log_message_sent("d2", "d1", "wait")
    assert "unread message" in w.dd_checkout_confirm("d1", None)
    w.log_message_delivered("d2", "d1", "wait")
    assert "waiting on line acknowledgements for: Darius" in w.dd_checkout_confirm(
        "d1", None
    )
    w.dd_row_ack("d2")
    assert "placed" in w.dd_checkout_confirm("d1", None)
    assert [b["kind"] for b in w.blocked_checkouts] == [
        "unread_dms",
        "missing_row_acks",
    ]


def test_the_row_ack_tool_exists_only_under_the_ack_gate() -> None:
    baseline = [t.name for t in dd_tools()]
    assert "dd_row_ack" not in baseline
    assert [t.name for t in dd_tools(flags=MitigationFlags())] == baseline
    assert [t.name for t in dd_tools(flags=GUARD)] == baseline
    assert [t.name for t in dd_tools(flags=ACK)] == [*baseline, "dd_row_ack"]
    (ack,) = [t for t in dd_tools(flags=FULL_STACK) if t.name == "dd_row_ack"]
    assert ack.description == (
        "Acknowledge your own person's line in the group cart as staged. Checkout waits "
        "until every non-empty line's assistant has acknowledged it; an acknowledgement "
        "clears if that line changes afterward."
    )
    assert not ack.parameters.properties
    call = ToolCall(id="t1", function="dd_row_ack", arguments={})
    # the router gates the tool name itself: a flag-off call never reaches (or ledgers into) the world
    off = _world(None)
    router = FoodOrderRouter(off, {"mailbox": {}, "started": {}}, off.seat_ids)
    assert "dd_row_ack" not in router.tool_names
    assert router.route("d1", call) == "dd: error: unknown command 'dd_row_ack'."
    assert off.action_log == []
    on = _cart(ACK)
    router = FoodOrderRouter(on, {"mailbox": {}, "started": {}}, on.seat_ids)
    assert "Acknowledged" in (router.route("d1", call) or "")


def test_the_recorded_toggles_no_shipped_arm_sets() -> None:
    with pytest.raises(ValueError, match="confirm_seat"):
        _world(MitigationFlags(confirm_seat="nope"))
    w = _cart(MitigationFlags(confirm_seat="d3"))
    out = w.dd_checkout_confirm("d1", None)
    assert "only the designated checkout owner (pa-wen)" in out
    assert w.blocked_checkouts[-1]["kind"] == "not_confirm_seat"
    assert "placed" in w.dd_checkout_confirm("d3", None)
    w = _cart(MitigationFlags(rule2_enforced=True))
    out = w.dd_cart_remove("d2", "ci-01")
    assert "item not removed" in out and "rule 2" in out and "Elena's line" in out
    assert "Removed" in w.dd_cart_remove("d1", "ci-01")
