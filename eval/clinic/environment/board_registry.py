"""The registered-board index — the ONE leaf both layers of the stack share.

`board_spec.register_board` writes here; `world` / `values` / `design_check` read membership through `is_board` so a registered board inherits the reprio-family semantics (slot-serves-one physics, credit-held-bookings, scoped-wrong-specialty, norm-licensed-rehome, the v2/v3 surface policies, cross-tier N/A) WITHOUT any author ever editing those modules. This module deliberately imports nothing from the package — it sits below `resources` — so every consumer can reach it without a cycle: `board_spec` (which imports half the package) fills the dict, and the low modules only ever ask "is this scenario a registered board?" at call time, which is what makes membership dynamic rather than frozen at import.

Landed scenarios are untouched by construction: `is_board` is False for every id that was ever flown, so every predicate that consults it composes as `name in LANDED_SET or is_board(name)` and the landed branch is byte-identical.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .board_spec import BoardSpec

#: `board_id -> its spec`, in registration order. Filled ONLY by `board_spec.register_board` (and drained
#: only by its test-facing `unregister_board`); everything else treats this as read-only.
REGISTERED: dict[str, BoardSpec] = {}


def is_board(scenario_id: str) -> bool:
    """Whether `scenario_id` is a registered board (and so carries the reprio-family semantics)."""
    return scenario_id in REGISTERED


def board(scenario_id: str) -> BoardSpec:
    """The registered spec for `scenario_id`.

    Raises:
        KeyError: If the scenario is not a registered board.
    """
    return REGISTERED[scenario_id]


def board_ids() -> tuple[str, ...]:
    """Every registered board id, in registration order."""
    return tuple(REGISTERED)


__all__ = ["REGISTERED", "board", "board_ids", "is_board"]
