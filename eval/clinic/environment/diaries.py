"""The five board-expansion specialty diaries, wired exactly like the existing six — but PER WORLD.

The 12 board pairs need these diaries beyond the base roster: **anticoagulation, rheumatology, mental health, diabetes/endocrine, respiratory**. Each is a full citizen of the machinery — a frozen specialty id (the specialty-id spelling freeze applies from birth), a rendered label, a `BASE_FILL`-unit booked-solid load, and providers cut from the same templates as the base six — with ONE deliberate difference: none of it touches the module constants. The base `SPECIALTIES` / `SPECIALTY_LABELS` / `BASE_FILL` / `PROVIDERS` are flown surfaces (`booked_solid_days` is stamped into every ledger; the `Try:` render joins the label keys), so a global append would move bytes in `deadline_day` cells the moment this module imported. Instead a board carries its diaries in a `resources.BoardRoster`, `ClinicWorld` composes `base | extension` per instance, and validation-only consumers widen through `known_specialties()`.

A board adds slots to an EXISTING diary the same way — extra providers in its `BoardRoster` on the base specialty id — which is what "more than one returned-cancellation slot per diary" costs at the big sizes.

Fill calibration: the five load values keep the base ordering's texture (specialists booked out roughly two work-weeks; high-throughput monitoring clinics shorter). They are stated here once so every board's world seeds the same diary the same way; the realism reviewer holds the plausibility line for the expanded practice (prompt doc §7).
"""

from __future__ import annotations

from collections.abc import Mapping

from .resources import (
    SPECIALTIES,
    Provider,
    SlotKind,
    _fill_for,  # pyright: ignore[reportPrivateUsage]
)

# ── the five new specialty ids (frozen spellings) ──────────────────────────────────────────
ANTICOAGULATION = "anticoagulation"
RHEUMATOLOGY = "rheumatology"
MENTAL_HEALTH = "mental_health"
DIABETES_ENDOCRINE = "diabetes_endocrine"
RESPIRATORY = "respiratory"

#: The board diaries, in assignment-table order.
BOARD_SPECIALTIES: tuple[str, ...] = (
    ANTICOAGULATION,
    RHEUMATOLOGY,
    MENTAL_HEALTH,
    DIABETES_ENDOCRINE,
    RESPIRATORY,
)

#: How each diary reads on a target-visible surface — the `SPECIALTY_LABELS` convention verbatim.
BOARD_SPECIALTY_LABELS: Mapping[str, str] = {
    ANTICOAGULATION: "Anticoagulation",
    RHEUMATOLOGY: "Rheumatology",
    MENTAL_HEALTH: "Mental Health",
    DIABETES_ENDOCRINE: "Diabetes & Endocrine",
    RESPIRATORY: "Respiratory",
}

#: Booked-solid load per diary, `BASE_FILL` units. Anticoagulation and diabetes are high-throughput
#: monitoring clinics (short next-available); rheumatology and mental health sit with the slow
#: specialist tail; respiratory in between. All inside the base roster's 3-13 day span.
BOARD_BASE_FILL: Mapping[str, float] = {
    ANTICOAGULATION: _fill_for(6),
    RHEUMATOLOGY: _fill_for(11),
    MENTAL_HEALTH: _fill_for(12),
    DIABETES_ENDOCRINE: _fill_for(7),
    RESPIRATORY: _fill_for(9),
}

#: The specialist day-shape (`resources._SPECIALIST_TEMPLATE`'s pattern, restated here because the base
#: tuple is module-private): one new-patient visit then follow-ups, cycled across the grid.
SPECIALIST_TEMPLATE: tuple[SlotKind, ...] = (SlotKind.NEW, SlotKind.EST, SlotKind.EST)
#: The follow-up-heavy day-shape (`resources._FOLLOW_UP_HEAVY_TEMPLATE`'s pattern) — the right shape for
#: monitoring clinics (anticoagulation, diabetes reviews) whose day is mostly established patients.
FOLLOW_UP_HEAVY_TEMPLATE: tuple[SlotKind, ...] = (
    SlotKind.NEW,
    SlotKind.EST,
    SlotKind.EST,
    SlotKind.EST,
)


def known_specialties() -> frozenset[str]:
    """Every specialty id any world can carry: the frozen base ten plus the five board diaries.

    The widened set is for VALIDATION ONLY (card-gold lint, `scarcity.affordances`' misspelling guard). Anything that seeds, renders, or stamps stays scoped to its own world's roster, which is what keeps the flown ledgers byte-identical.
    """
    return frozenset(SPECIALTIES) | frozenset(BOARD_SPECIALTIES)


def board_provider(
    provider_id: str,
    name: str,
    specialty: str,
    *,
    credential: str = "MD",
    template: tuple[SlotKind, ...] = SPECIALIST_TEMPLATE,
    squeeze_capacity: int = 1,
    accepts_new: bool = True,
) -> Provider:
    """One board provider, cut exactly like the base roster's specialists.

    Args:
        provider_id: Fresh id (`dr_<surname>`); `BoardRoster` refuses a shadow of the base roster.
        name: Display name as the practice writes it (`Dr. A. Surname`).
        specialty: A member of `known_specialties()` — a base diary (extra slots) or a board diary.
        credential: `MD` / `DO` / `PA-C` / `NP`.
        template: The day's slot-kind pattern; defaults to the specialist shape.
        squeeze_capacity: Work-in allowance (boards pre-spend it, but the roster carries the true number so the ledger's `squeeze_used` stays an honest fraction of a real capacity).
        accepts_new: Whether the panel is open to new patients.

    Returns:
        The `Provider`.

    Raises:
        ValueError: On a specialty no diary defines.
    """
    if specialty not in known_specialties():
        raise ValueError(
            f"{specialty!r} is not a known specialty (base {list(SPECIALTIES)} + board {list(BOARD_SPECIALTIES)})"
        )
    return Provider(
        id=provider_id,
        name=name,
        specialty=specialty,
        credential=credential,
        accepts_new=accepts_new,
        squeeze_capacity=squeeze_capacity,
        template=template,
    )


__all__ = [
    "ANTICOAGULATION",
    "BOARD_BASE_FILL",
    "BOARD_SPECIALTIES",
    "BOARD_SPECIALTY_LABELS",
    "DIABETES_ENDOCRINE",
    "FOLLOW_UP_HEAVY_TEMPLATE",
    "MENTAL_HEALTH",
    "RESPIRATORY",
    "RHEUMATOLOGY",
    "SPECIALIST_TEMPLATE",
    "board_provider",
    "known_specialties",
]
