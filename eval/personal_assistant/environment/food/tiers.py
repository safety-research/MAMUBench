"""Tier → physics: the ONE family table shared by `scenario`, `bots`, and `design_check`.

Every tier's world-side properties (store table, roster, cap, rung stamp, world rules) are stated
here exactly once, so a new family cannot half-land across modules (the shape of an earlier bug:
a knob that reaches rendering but not every consumer). Deliberately light — no harness imports —
so the `design_check` CLI and the bots can build tier-exact worlds without pulling the pi stack.
The hidden-score layer (`values.py`) stays out of this table by contract; its variant dispatch
keys on the `menu_variant` this factory stamps into the ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from _harness.env_core import ScriptStep
from .resources import (
    DINNER_HORIZON_MIN,
    DINNER_T0_MOD,
    Diner,
    Store,
    profile_memory_files,
)
from .world import MitigationFlags, World

SEED_TIER_ALIASES = {"reg_food_silent_side_deadline": "silent_side"}


def seed_tier(tier: str) -> str:
    """The tier whose name keys world jitter (soft ablation twins alias their hard twin)."""
    return SEED_TIER_ALIASES.get(tier, tier)


@dataclass(frozen=True)
class Family:
    """One menu family's world-side properties (stated once; consumed by `build_world`)."""

    variant: str
    cap_cents: Callable[[str], int]
    diners: Callable[[int], tuple[Diner, ...]]
    stores: Callable[[str], tuple[Store, ...]]
    rung: Callable[[str], str | None]
    single_order: bool
    no_sharing: bool
    hard_deadline: bool = False
    soft_guidance: bool = False
    no_capacity_phrase: bool = False
    #: Ledgered scenario id for families whose SCORING is per-tier (the consent registry);
    #: None everywhere else.
    scenario_tag: str | None = None
    #: Whose name the benefit line, the `dd_search` header and `dd_order_history` render;
    #: None everywhere else (the shared-office default, `resources.COMPANY`).
    company: str | None = None
    #: False = a private dinner: the cap renders as a plain group budget with no employer
    #: and no company card. True (the default) everywhere else.
    work_benefit: bool = True
    #: Diner ids whose profile notes every mesh seat holds (the common-knowledge structural arm);
    #: empty everywhere else — the canonical private-drawer topology.
    common_knowledge: frozenset[str] = frozenset()
    #: Wall-clock minutes-of-day at t=0; None everywhere else (the stock dinner clock,
    #: `DINNER_T0_MOD`). An extension family whose authored briefs name clock-derived
    #: cutoffs sets it so the rendered world matches them.
    t0_mod: int | None = None
    #: Episode horizon in sim-minutes; None everywhere else (`DINNER_HORIZON_MIN`).
    horizon_min: int | None = None


_FAMILIES: tuple[tuple[tuple[str, ...], Family], ...] = ()

_EXTENSION_FAMILIES: dict[str, Family] = {}


def register_extension_family(tier: str, family: Family) -> None:
    """Register one experiment-owned tier family (idempotent for the same object)."""
    if any(tier in tiers for tiers, _ in _FAMILIES):
        raise ValueError(f"tier {tier!r} shadows a built-in family")
    existing = _EXTENSION_FAMILIES.get(tier)
    if existing is not None and existing is not family:
        raise ValueError(f"tier {tier!r} is already registered to a different family")
    _EXTENSION_FAMILIES[tier] = family


def _family(tier: str) -> Family:
    for tiers, family in _FAMILIES:
        if tier in tiers:
            return family
    extension = _EXTENSION_FAMILIES.get(tier)
    if extension is not None:
        return extension
    raise ValueError(f"unknown tier {tier!r}; one of {known_tiers()}")


def known_tiers() -> tuple[str, ...]:
    """Every buildable tier name (the scenario builder's validation set)."""
    return tuple(t for tiers, _ in _FAMILIES for t in tiers) + tuple(
        _EXTENSION_FAMILIES
    )


def scenario_stores(tier: str) -> tuple[Store, ...]:
    """The store table a tier's world renders (no throwaway `World` needed to read it)."""
    return _family(tier).stores(tier)


def scenario_cap_cents(tier: str) -> int:
    return _family(tier).cap_cents(tier)


def scenario_hard_deadline(tier: str) -> bool:
    """Whether a tier renders the courier cutoff (benefit line + preview warning + world prose)."""
    return _family(tier).hard_deadline


def scenario_common_knowledge(tier: str) -> frozenset[str]:
    """Diner ids whose notes sit in every mesh seat's drawer (the structural arm; usually empty)."""
    return _family(tier).common_knowledge


def mesh_memory_files(
    tier: str, d: Diner, diners: tuple[Diner, ...]
) -> tuple[tuple[str, str], ...]:
    """One mesh seat's drawer: its own person's notes + any common-knowledge principals' notes.

    Lives here rather than in `scenario` so the gates can check the drawer a live cell installs
    without importing the harness. The principal's own drawer is never extended (a seat does not
    get a second copy of its own person's notes), so the arm moves only the PEERS' access.
    """
    common = scenario_common_knowledge(tier)
    shared = tuple(
        f
        for other in diners
        if other.id in common and other.id != d.id
        for f in profile_memory_files(other)
    )
    return (*d.memory_files, *shared)


def scenario_diners(tier: str, n: int) -> tuple[Diner, ...]:
    """The roster for a tier (the tradeoff families pin the canonical four with variant profiles)."""
    return _family(tier).diners(n)


def build_world(
    tier: str,
    seed: int,
    *,
    diners: tuple[Diner, ...],
    topology: str = "solo",
    script: tuple[ScriptStep, ...] = (),
    mitigation_flags: MitigationFlags | None = None,
) -> World:
    """One tier's physics for a fresh `World` — the single factory every consumer goes through.

    `build_router` (live cells), the scripted-policy bots, and `design_check`'s knob gates all
    build here, so the zero-model band and the provers run the SAME physics a live cell does.

    `mitigation_flags` is a pure passthrough to `World`: runtime
    guards/rendering only, default None = baseline, never part of the tier's physics table.
    """
    family = _family(tier)
    return World(
        seed,
        diners=diners,
        topology=topology,
        mitigation_flags=mitigation_flags,
        cap_cents=scenario_cap_cents(tier),
        script=script,
        stores=family.stores(tier),
        single_order=family.single_order,
        menu_rung=family.rung(tier),
        menu_variant=family.variant,
        no_sharing=family.no_sharing,
        hard_deadline=family.hard_deadline,
        soft_guidance=family.soft_guidance,
        no_capacity_phrase=family.no_capacity_phrase,
        # Fake-clock default: time is a STATED comfortable placement window ("it's X now; order in
        # by X+63"), not machinery — the courier-arrival warning surface is suppressed and nothing
        # enforces the stated time. Scale family first; extended to the 4-person consent
        # family (silent_side's final battery). Pre-change batteries ran the legacy
        # cutoff surface, so never pool across it.
        comfort_window_min=None,
        scenario_tag=family.scenario_tag,
        company=family.company,
        work_benefit=family.work_benefit,
        t0_mod=family.t0_mod if family.t0_mod is not None else DINNER_T0_MOD,
        horizon_min=(
            family.horizon_min if family.horizon_min is not None else DINNER_HORIZON_MIN
        ),
    )
