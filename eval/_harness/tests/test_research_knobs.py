"""The shared stack's env-gated scheduler knobs: the beat queue's arrival order (`BEAT_WAKE_ORDER`).

`BeatQueue.oldest_pending_agent` is vendored with its test from the authors' research code. The routing knobs' own tests (`BURST_YIELD_TOOLS`, `WAKE_ORDER`,
`WRAPUP_GRANTS`, `WRAPUP_BRINGUP`, each with its unset flown default) are the vendored
`_multiagent_pi/tests/test_routing.py`; `test_sim_golden.py` pins that a hero episode is byte-identical to the
pre-port release with every knob unset.
"""

from __future__ import annotations

from _harness.env_core import BeatQueue


def test_oldest_pending_agent_orders_by_fire_order_then_ids() -> None:
    q = BeatQueue()
    q.push("C", "c1", "fired first")
    q.push("B", "b1", "fired second")
    q.push("A", "a1", "fired third")
    assert q.oldest_pending_agent(("A", "B", "C")) == "C", (
        "arrival order beats id order"
    )
    assert q.first_pending_agent(("A", "B", "C")) == "A", (
        "the flown id-order pick is unchanged"
    )
    q.drain("C")
    q.confirm("C")
    assert q.oldest_pending_agent(("A", "B", "C")) == "B"
    # A bounced (requeued) beat keeps its original place in the arrival order.
    q.drain("B")
    q.push("A", "a2", "fired fourth")
    q.requeue("B")
    assert q.oldest_pending_agent(("A", "B")) == "B"
    assert q.oldest_pending_agent(("A",)) == "A"
    assert q.oldest_pending_agent(("Z",)) is None
