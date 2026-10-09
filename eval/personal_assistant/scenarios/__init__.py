"""Load the 25 scenarios of record from their own configuration folders."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from dataclasses import dataclass

from functools import cache

from types import ModuleType

from typing import TYPE_CHECKING, Any, Callable, cast

if TYPE_CHECKING:
    from personal_assistant.environment.trip_cart import TripSpec
    from personal_assistant.environment.trip_privacy import TripPrivacy
    from personal_assistant.environment.food.resources import Diner, Store


@dataclass(frozen=True)
class FoodScenario:
    """One food_cart module's registration coordinates (see the module docstrings)."""

    module: str
    tier: str
    diners_attr: str
    stores_attr: str
    no_sharing: bool
    hard_deadline: bool
    #: `Cell.confidential_policy` (a short with NO `_CONFIDENTIAL_ADDENDA` entry keeps
    #: the drawer untouched and only adds the runbook confidentiality norm).
    confidential_policy: str = ""
    #: Wrap the raw cast with the standard broadcast/sign-off assembly exactly as
    #: `personal_assistant.environment.food.venue.venue_diners` does (modules that ship the cast raw).
    venue_assembly: bool = False
    #: Module attr holding item_id -> extra tags to fold into the registered town
    #: (the `TRADEOFF_TAG_ADDS` pattern; requires the tags in `ITEM_TAGS`).
    fold_tags_attr: str | None = None
    #: Build the town with `with_scenario_tags=True` (alphagal's scoreable tags).
    scenario_tag_stores: bool = False
    #: Registry key for this row's cells / `CONTRACTS` entry / `CELL_CONFIGS` entry when
    #: it differs from the contract's own `short`. Only a CONTROL ARM needs this: two
    #: rows that share one authored contract (`split_tab_only`'s breadcrumb-off twin)
    #: would otherwise collide on `conf_<short>_<topology>` and the second cell would
    #: silently overwrite the first with the wrong tier. `None` = use the contract short.
    registry_short: str | None = None
    #: Thread the module's AUTHORED world clock (`CELL_CONFIG["t0_mod"]` /
    #: `CELL_CONFIG["horizon_min"]`) into the registered tier (the round-6
    #: `graduation_banquet_swap` / `sheet_never_had_her` hook: their briefs name
    #: cutoffs the stock 18:05 clock contradicts). Default False = the stock dinner
    #: clock, which every pre-round-6 row was wired and certified against — several
    #: older modules carry a deliberately UNWIRED `t0_mod` in their `CELL_CONFIG`
    #: (`zero_proof_box`, `sendoff_cold_plates`, …, each recording
    #: `t0_mod_rendered=false`), and this flag must never pick those up retroactively.
    authored_clock: bool = False
    #: This module's reason-only CONTROL twins (see `ControlArm`): one extra registered
    #: arm each, sharing every flag on this row and overriding only the principal's
    #: drawer and the contract kwargs. Empty for a module with no twin, and for a twin
    #: that ships as a SIBLING MODULE (`bariatric_birthday_control` and the other five
    #: reason controls) — those carry their own `CONTRACT_KWARGS` and
    #: so are ordinary rows.


@dataclass(frozen=True)
class FoodRow:
    """One loaded food scenario: contract, tier physics, and cell coordinates."""

    short: str
    loop: str
    tier: str
    cap_cents: int
    fresh_checkout: bool
    confidential_policy: str
    contract_kwargs: dict[str, Any]
    diners: Callable[[], tuple[Diner, ...]]
    stores: Callable[[], tuple[Store, ...]]
    no_sharing: bool
    hard_deadline: bool
    #: Whose name the benefit line, the `dd_search` header and `dd_order_history`
    #: render, from the module's `CELL_CONFIG["company"]`. `None` = the module names
    #: no host, so the world keeps the shared-office default (`resources.COMPANY`).
    company: str | None
    #: `CELL_CONFIG["work_benefit"]`, defaulting True: a private-dinner town sets it
    #: False so the cap renders as a plain group budget with no employer and no card.
    work_benefit: bool
    #: The authored world clock (`FoodScenario.authored_clock` rows only): wall-clock
    #: minutes-of-day at t=0 and the episode horizon in sim-minutes. `None` = the
    #: stock dinner clock (`DINNER_T0_MOD` / `DINNER_HORIZON_MIN`).
    t0_mod: int | None
    horizon_min: int | None
    #: The module's full `CELL_CONFIG` (runner-level knobs: the enforced
    #: `deadline_minutes` window, the `deadline_line`/`soft_deadline_line` brief
    #: sentence, cap framing, per-scenario extras). The runner reads it; the
    #: frozen F06/N1 screen shorts have no authored module and thus no config.
    cell_config: dict[str, Any]


_ROOT = Path(__file__).resolve().parent
CONFIGS = tuple(
    json.loads((_ROOT / short / "hero.json").read_text())
    for short in json.loads((_ROOT / "index.json").read_text())
)
FOOD_SCENARIOS = tuple(
    FoodScenario(module=row["config_module"], **row["food_registration"])
    for row in CONFIGS
    if row["substrate"] == "food"
)
TRIP_MODULES = tuple(
    row["config_module"] for row in CONFIGS if row["substrate"] == "trip"
)
TRIP_CONTROL_ARMS = {}


def _import_scenario(name: str) -> ModuleType:
    return importlib.import_module(name)


def _contract_kwargs(mod: ModuleType, attr: str | None = None) -> dict[str, Any]:
    """The module's `FoodContract` kwargs with its privacy policy normalized in.

    `attr` names a CONTROL ARM's own kwargs (`ControlArm.contract_kwargs_attr`), which
    are returned exactly as authored — no privacy normalization. The module's
    `PRIVACY_KWARGS` / `ANALYSIS_VOCAB` are the TREATMENT's vocabulary, describing a
    secret the control arm does not have; folding them in would score the control's
    assistant for stating its own drawer's reason out loud, which is the one thing that
    arm exists to be allowed to do.
    """
    if attr is not None:
        return dict(getattr(mod, attr))
    kwargs: dict[str, Any] = dict(mod.CONTRACT_KWARGS)
    if "privacy" not in kwargs:
        privacy_kwargs = getattr(mod, "PRIVACY_KWARGS", None)
        vocab = getattr(mod, "ANALYSIS_VOCAB", None)
        if privacy_kwargs is not None:
            from personal_assistant.environment.specs import PrivacyPolicy

            kwargs["privacy"] = PrivacyPolicy(**privacy_kwargs)
        elif vocab is not None:
            # The exact/category/false_cover arms double as the contract's
            # mechanical lists; `linkage` is screen-only (adjudicated, never auto).
            from personal_assistant.environment.specs import PrivacyPolicy

            kwargs["privacy"] = PrivacyPolicy(
                exact_terms=tuple(vocab["exact"]),
                category_terms=tuple(vocab["category"]),
                false_cover_terms=tuple(vocab["false_cover"]),
            )
    return kwargs


def _scenario_rows(scenario: FoodScenario) -> tuple[FoodRow, ...]:
    """The treatment row for one module, followed by one row per control arm."""
    mod = _import_scenario(scenario.module)
    cell_config: dict[str, Any] = dict(mod.CELL_CONFIG)
    diners: Callable[[], tuple[Diner, ...]] = getattr(mod, scenario.diners_attr)
    if scenario.scenario_tag_stores:
        town: Callable[..., tuple[Store, ...]] = getattr(mod, scenario.stores_attr)

        def stores(
            _town: Callable[..., tuple[Store, ...]] = town,
        ) -> tuple[Store, ...]:
            return _town(with_scenario_tags=True)
    else:
        stores = getattr(mod, scenario.stores_attr)
    contract_kwargs = _contract_kwargs(mod)
    company = cell_config.get("company")
    treatment = FoodRow(
        short=scenario.registry_short or str(contract_kwargs["short"]),
        loop=str(mod.LOOP),
        tier=scenario.tier,
        cap_cents=int(cell_config["cap_cents"]),
        fresh_checkout=bool(cell_config["fresh_checkout"]),
        confidential_policy=scenario.confidential_policy,
        contract_kwargs=contract_kwargs,
        diners=diners,
        stores=stores,
        no_sharing=scenario.no_sharing,
        hard_deadline=scenario.hard_deadline,
        company=None if company is None else str(company),
        work_benefit=bool(cell_config.get("work_benefit", True)),
        t0_mod=int(cell_config["t0_mod"]) if scenario.authored_clock else None,
        horizon_min=(
            int(cell_config["horizon_min"]) if scenario.authored_clock else None
        ),
        cell_config=cell_config,
    )
    return (treatment,)


@cache
def food_rows() -> tuple[FoodRow, ...]:
    """Load every food scenario module once and return its registration row(s)."""
    return tuple(row for sc in FOOD_SCENARIOS for row in _scenario_rows(sc))


@cache
def register_food_tiers() -> None:
    """Register every food scenario tier into `personal_assistant.environment.food.tiers` (idempotent)."""
    rows = food_rows()  # first: module loading also puts the repo root on sys.path
    from personal_assistant.environment.food.tiers import (
        Family,
        register_extension_family,
    )

    for row in rows:
        register_extension_family(
            row.tier,
            Family(
                variant="conf_planning",
                cap_cents=lambda _t, _cap=row.cap_cents: _cap,
                diners=lambda _n, _d=row.diners: _d(),
                stores=lambda _t, _s=row.stores: _s(),
                rung=lambda _t: None,
                single_order=True,
                no_sharing=row.no_sharing,
                hard_deadline=row.hard_deadline,
                no_capacity_phrase=True,
                scenario_tag=row.tier,
                company=row.company,
                work_benefit=row.work_benefit,
                t0_mod=row.t0_mod,
                horizon_min=row.horizon_min,
            ),
        )


def _trip_registry_key(mod: ModuleType) -> str:
    """One module's registry key (`SCENARIO_KEY` / `REGISTRY_KEY`, else `SPEC.name`)."""
    key = getattr(mod, "SCENARIO_KEY", None) or getattr(mod, "REGISTRY_KEY", None)
    if key is not None:
        return str(key)
    spec: TripSpec = mod.SPEC
    return spec.name


def _secret_surface_persons(
    mod: ModuleType, surface_attr: str | None = None
) -> frozenset[str]:
    """Return the traveller ids named by a module's `memory:<id>` secret surfaces.

    `surface_attr` names a CONTROL ARM's own surface value — a `memory:<id>` string or
    an iterable of them (`TripControlArm.secret_surface_attr`) — for a twin whose
    surface set differs from the treatment's; `None` reads the module's
    `SECRET_SURFACE` / `SECRET_SURFACES`, the treatment convention.
    """
    surfaces: list[str] = []
    if surface_attr is not None:
        value: object = getattr(mod, surface_attr)
        if isinstance(value, str):
            surfaces.append(value)
        else:
            surfaces.extend(str(surface) for surface in cast("frozenset[str]", value))
    else:
        single = getattr(mod, "SECRET_SURFACE", None)
        if isinstance(single, str):
            surfaces.append(single)
        plural = getattr(mod, "SECRET_SURFACES", None)
        if plural is not None:
            surfaces.extend(str(surface) for surface in cast("frozenset[str]", plural))
    return frozenset(
        surface.removeprefix("memory:")
        for surface in surfaces
        if surface.startswith("memory:")
    )


def _trip_principals(
    mod: ModuleType, spec: TripSpec, surface_attr: str | None = None
) -> frozenset[str]:
    """Return the travellers whose own drawer carries the secret.

    Resolution, in order, over the three conventions the authored trip modules use: an
    explicit `PRINCIPAL_ID` / `PRINCIPAL`, else the `SECRET_SURFACE(S)` drawers that are
    also request persons — which is what keeps an ADVERSARY's drawer (the reporter in
    `foliage_window8`, whose surface must hold the rumor it reacts to) out of the
    instructed column. Fails closed: a module that ships a disclosure vocabulary the
    loader cannot attribute to a principal would otherwise be scored author-blind and
    silently charge peers with the principal's instruction.
    """
    by_id = spec.by_id()
    for attr in ("PRINCIPAL_ID", "PRINCIPAL"):
        named = getattr(mod, attr, None)
        if isinstance(named, str) and named in by_id:
            return frozenset({named})
    requested = {request.person for request in spec.requests}
    principals = _secret_surface_persons(mod, surface_attr) & set(by_id) & requested
    if not principals:
        raise ValueError(
            f"trip scenario {spec.name!r} ships ANALYSIS_VOCAB but names no principal: "
            "set PRINCIPAL_ID, or a SECRET_SURFACE on a request person's drawer"
        )
    return principals


def _trip_policy(
    mod: ModuleType,
    spec: TripSpec,
    vocab: dict[str, list[str]],
    surface_attr: str | None = None,
) -> TripPrivacy:
    """Build one arm's `TripPrivacy` from its vocabulary against its own drawers."""
    from personal_assistant.environment.trip_privacy import (
        TripPrivacy,
        admissible_cover_terms,
        instructs_refusal_hygiene,
    )

    principals = _trip_principals(mod, spec, surface_attr)
    by_id = spec.by_id()
    memory = "\n".join(by_id[person].memory for person in sorted(principals))
    scored_covers, dropped = admissible_cover_terms(
        tuple(vocab.get("false_cover", ())), memory
    )
    return TripPrivacy(
        principals=principals,
        exact_terms=tuple(vocab.get("exact", ())),
        category_terms=tuple(vocab.get("category", ())),
        false_cover_terms=scored_covers,
        linkage_terms=tuple(vocab.get("linkage", ())),
        adversaries=(
            _secret_surface_persons(mod, surface_attr) & set(by_id)
        ).difference(principals),
        inadmissible_cover_terms=dropped,
        refusal_hygiene_instructed=instructs_refusal_hygiene(memory),
    )


def register_trip_privacy() -> None:
    """Register every trip disclosure policy into `trip_privacy.TRIP_PRIVACY`."""
    from personal_assistant.environment import trip_privacy

    for key, policy in trip_privacy_rows():
        existing = trip_privacy.TRIP_PRIVACY.setdefault(key, policy)
        if existing != policy:
            raise ValueError(
                f"trip scenario key {key!r} is already registered to a different policy"
            )


def register_trip_specs() -> None:
    """Register every trip scenario `SPEC` and disclosure policy (idempotent)."""
    from personal_assistant.environment import trip_cart

    for key, spec in trip_rows():
        existing = trip_cart.TRIP_SPECS.setdefault(key, spec)
        if existing is not spec and existing != spec:
            raise ValueError(
                f"trip scenario key {key!r} is already registered to a different spec"
            )
    register_trip_privacy()


@cache
def trip_rows() -> tuple[tuple[str, TripSpec], ...]:
    return tuple(
        (_trip_registry_key(mod), mod.SPEC)
        for mod in map(_import_scenario, TRIP_MODULES)
    )


@cache
def trip_privacy_rows() -> tuple[tuple[str, TripPrivacy], ...]:
    return tuple(
        (mod.SPEC.name, _trip_policy(mod, mod.SPEC, mod.ANALYSIS_VOCAB))
        for mod in map(_import_scenario, TRIP_MODULES)
        if getattr(mod, "ANALYSIS_VOCAB", None)
    )


def trip_seed_scenario(key: str) -> str:
    return key
