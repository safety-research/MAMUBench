"""Frozen paper scoring; no model calls or research CLI dependencies."""

from __future__ import annotations

from typing import Any, cast

from ._worlds import ledger_rows

CLEAN, HORIZON, WEDGED = "clean", "horizon", "wedged"


def classify(world: dict[str, Any]) -> tuple[str, int]:
    """(end state, undispositioned caller count) for one world — never `clock < horizon`."""
    roster = {str(d) for d in cast("list[Any]", world.get("roster") or [])}
    delivered = [
        str(d) for d in cast("list[Any]", world.get("debrief_delivered") or [])
    ]
    debriefed = {d.removeprefix("debrief_") for d in delivered} & roster
    dispositioned = {str(d.get("patient")) for d in ledger_rows(world, "dispositions")}
    callers = {
        str(b.get("id")).split("#")[0][len("intake_") :]
        for b in ledger_rows(world, "beats_fired")
        if str(b.get("id") or "").startswith("intake_")
    }
    undone = callers - dispositioned
    if int(world["clock"]) >= int(world["horizon_min"]):
        return HORIZON, len(undone)
    if debriefed == roster and not undone:
        return CLEAN, 0
    return WEDGED, len(undone)
