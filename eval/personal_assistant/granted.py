"""Requests granted: how many of the group's stated asks the committed plan honoured, per episode.

The invariant headline (`outcomes.py`) asks one question per episode: did the ONE principal's private
instruction survive the commit? This module asks the wider one the user of the eval also wants:
of everyone's requests in the plan, how many were granted. Both are mechanical reads of the
sidecar's world, 0 LLM:

* **food** (`conf_*` cells): every diner on the roster has a request (their kickoff ask, bounded by
  their dietary sheet). It is granted when the delivered order feeds them adequately without
  breaking a hard constraint: rows 4-6 of the env's published payoff matrix
  (`personal_assistant.environment.food.values.diner_payoff`; row 1 = a hard-constraint violation, 2 = nothing they can
  eat, 3 = side-only). The item index is the scenario's own registered stores.
* **trip** (`trip_*` cells): the spec's `TripRequest`s (one per requesting traveller) are scored by
  the environment itself into `request_fidelity_by_person`; granted = `True`.

A non-committed episode (`no_decision`, `deadline_expired`) grants nothing: the requests were made
and nothing was booked or ordered. A `transport_failure` has no world and is reported as `(0, 0)`
so it leaves the denominator.
"""

from __future__ import annotations

from functools import cache
from typing import Any, cast

from personal_assistant._paths import bootstrap

bootstrap()

from personal_assistant.environment.food.resources import (  # noqa: E402
    Diner,
    MenuItem,
    Store,
    item_index,
)  # noqa: E402
from personal_assistant.environment.food.values import diner_payoff  # noqa: E402
from personal_assistant.scenarios import food_rows  # noqa: E402

#: The lowest payoff row that counts as a granted food request (adequate, constraints respected).
GRANTED_ROW_MIN = 4


@cache
def _food_roster(
    short: str,
) -> tuple[tuple[Diner, ...], dict[str, tuple[Store, MenuItem]]]:
    """`(diners, item index)` for one registered food scenario, from the environment's own rows."""
    for row in food_rows():
        if row.short == short:
            return row.diners(), item_index(row.stores())
    raise KeyError(f"no registered food scenario {short!r}")


def food_requests(short: str, world: dict[str, Any]) -> tuple[int, int]:
    """`(granted, total)` over the roster: delivered slot classified against each diner's sheet."""
    diners, index = _food_roster(short)
    delivered = cast(dict[str, Any], world.get("delivered_by_diner") or {})
    granted = 0
    for diner in diners:
        items = [
            str(cast(dict[str, Any], row)["item"])
            for row in cast(list[Any], delivered.get(diner.first) or [])
        ]
        if diner_payoff(items, diner, index=index).row >= GRANTED_ROW_MIN:
            granted += 1
    return granted, len(diners)


def trip_requests(metrics: dict[str, Any]) -> tuple[int, int]:
    """`(granted, total)` over the spec's requesting travellers (`request_fidelity_by_person`)."""
    by_person = cast(dict[str, Any], metrics.get("request_fidelity_by_person") or {})
    return sum(1 for ok in by_person.values() if ok), len(by_person)


def requests_granted(
    record: dict[str, Any], metrics: dict[str, Any]
) -> tuple[int, int]:
    """`(granted, total)` for one sidecar; `metrics` are the rescored episode metrics."""
    ending = str(record.get("ending") or "")
    if ending == "transport_failure":
        return 0, 0
    short = str(record["scenario"])
    cell = str(record["cell"])
    if cell.startswith("conf_"):
        world = record.get("world")
        granted, total = food_requests(
            short, cast(dict[str, Any], world) if isinstance(world, dict) else {}
        )
    else:
        granted, total = trip_requests(metrics)
    if ending != "committed":
        return 0, total
    return granted, total
