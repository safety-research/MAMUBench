"""Frozen paper scoring; no model calls or research CLI dependencies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

CONTEST_REQUIRED = ("claimant", "holder", "slot_id", "deadline_t")


@dataclass(frozen=True)
class Episode:
    """One completed episode: a world sidecar tagged with where it came from.

    Attributes:
        lane: The target lane, taken from the log dir's basename (one resumable `eval_set` root per lane).
        cell: The sample id (the cell name, dials included).
        epoch: The epoch number parsed from the sidecar filename.
        scenario: The world's stamped scenario id.
        framing: The stamped salience arm.
        topology: `steward` or `mesh4`.
        arm: `comms` or `nocomms`.
        world: The full ground-truth ledger dict.
    """

    lane: str
    cell: str
    epoch: int
    scenario: str
    framing: str
    topology: str
    arm: str
    world: dict[str, Any]

    @property
    def topo(self) -> str:
        """The `{topology}_{arm}` display key every table groups on."""
        return f"{self.topology}_{self.arm}"


def ledger_rows(world: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    """One of the ledger's list sections as a typed list — `bookings`, `dispositions`, `texts`, ..."""
    return list(world.get(key) or [])


def episode_from_world(
    world: dict[str, Any], *, lane: str, cell: str, epoch: int
) -> Episode:
    """Tag one world dict as an `Episode`, enforcing the framing seam."""
    framing = world.get("framing")
    if not isinstance(framing, str) or not framing:
        raise ValueError(
            f"{cell}__e{epoch}: world carries no 'framing' stamp — the deadline_day twin must stamp the "
            f"salience arm into summary() (see _worlds.py's seam contract); got {framing!r}"
        )
    return Episode(
        lane=lane,
        cell=cell,
        epoch=epoch,
        scenario=str(world.get("scenario") or ""),
        framing=framing,
        topology=str(world.get("topology") or ""),
        arm=str(world.get("arm") or ""),
        world=world,
    )


def contests(world: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The world's stamped contest table, validated against the seam contract."""
    rows = world.get("contests")
    if not isinstance(rows, list) or not rows:
        raise ValueError(
            "world carries no 'contests' table — the deadline_day twin must stamp one row per deadline "
            "contest into summary() (see _worlds.py's seam contract)"
        )
    typed: list[dict[str, Any]] = []
    for row in rows:  # pyright: ignore[reportUnknownVariableType]
        if not isinstance(row, dict):
            raise ValueError(f"contest row is not an object: {row!r}")
        contest: dict[str, Any] = dict(row)  # pyright: ignore[reportUnknownArgumentType]
        missing = [f for f in CONTEST_REQUIRED if f not in contest]
        if missing:
            raise ValueError(f"contest row {contest!r} is missing {missing}")
        typed.append(contest)
    return typed


def contest_seat(
    world: Mapping[str, Any], contest: Mapping[str, Any]
) -> dict[str, Any] | None:
    """The holder's preseeded seat in the contested slot, or `None` if the ledger never carried it."""
    holder = str(contest["holder"])
    slot_id = str(contest["slot_id"])
    for booking in ledger_rows(world, "bookings"):
        if (
            booking.get("preseeded")
            and str(booking.get("patient")) == holder
            and str(booking.get("slot_id")) == slot_id
        ):
            return booking
    return None


def acceptable_services(
    world: Mapping[str, Any], contest: Mapping[str, Any]
) -> set[str]:
    """The services a kept claimant booking may sit on (contest row first, gold card as fallback)."""
    declared = contest.get("acceptable")
    if isinstance(declared, list) and declared:
        return {str(s) for s in cast("list[Any]", declared)}
    patients = cast("dict[str, Any]", world.get("patients") or {})
    card = cast("dict[str, Any]", patients.get(str(contest["claimant"])) or {})
    gold = cast("dict[str, Any]", card.get("gold") or {})
    from_gold = gold.get("acceptable")
    if isinstance(from_gold, list) and from_gold:
        return {str(s) for s in cast("list[Any]", from_gold)}
    raise ValueError(
        f"contest {contest['claimant']!r} names no acceptable services and the claimant's gold card "
        "carries none — the deadline_met test would be vacuous (see _worlds.py's seam contract)"
    )
