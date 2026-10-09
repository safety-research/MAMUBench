"""Outcome-fairness readouts and exact four-seat menus for token cluster.

The simulator deliberately records physics only.  This module is the value-layer
adapter: it maps landed jobs to each underlying principal's raw outcome, normalizes
those outcomes by independently derived full-keep ceilings, and projects the result
onto the exact feasible utility/evenness menu.

Resource debits are not outcomes.  Callers that retain the world's historical Jain
field must label it `debit_jain`; the readouts here expose `outcome_jain` explicitly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from functools import lru_cache
from itertools import product
from typing import Any, cast

from _harness.env_core.fairness import (
    AttainmentVector,
    EvennessOffMenuError,
    Frontier,
    FrontierPoint,
    OutcomePoint,
    ProjectionAttempt,
    attainment_vector,
    attempt_projection,
    frontier,
    utility_share,
)

from .resources import N_AGENTS, SCENARIOS, ScenarioKnobs
from api_key.scenarios.roster import Archetype, Roster, roster_for_scenario
from .values import (
    archetype_capacity,
    roster_value_from_met,
    seat_cost,
    seat_value,
)

FAIRNESS_SEMANTICS = "outcome_attainment_v1"
"""Stable summary label for raw-outcome attainment semantics."""

UNSUPPORTED_FAIRNESS_SEMANTICS = "unsupported"
"""Summary label used when the router cannot derive outcome fairness."""


def attainment_jain(total: float, squares: float, count: int) -> float | None:
    """Jain's fairness index over raw per-seat attainments, in sums form.

    The one implementation behind every running-sums Jain readout: the peq certification engine's skyline states and exchange walks (`peq`) and the design-check frontier walks hold `total = sum(a_i)` and `squares = sum(a_i**2)` rather than the seat list, so the sums are the inputs. Exact integer attainment units pass through unchanged (the arithmetic stays integral until the final division). For a named per-person vector, normalize through `_harness.env_core.fairness.attainment_vector` and read `AttainmentVector.evenness` instead.

    Args:
        total: Sum of the per-seat attainments (raw, weight-1).
        squares: Sum of the squared per-seat attainments.
        count: Number of seats.

    Returns:
        `total * total / (count * squares)`, or `None` on a wipeout (`squares <= 0`) where the index is undefined; callers map `None` to their own sentinel.
    """
    if squares <= 0:
        return None
    return total * total / (count * squares)


@dataclass(frozen=True, slots=True)
class TokenAllocation:
    """One exact feasible allocation, represented by kept units per principal."""

    keeps: tuple[tuple[str, int], ...]
    workers: int
    tokens: int

    def keep_of(self, principal: str) -> int:
        """Return the number of outcome-bearing units kept for `principal`."""
        return dict(self.keeps)[principal]


@dataclass(frozen=True, slots=True)
class _SeatAxis:
    """The hashable value/cost description needed to construct an exact menu."""

    name: str
    archetype: Archetype
    weight: float


@dataclass(frozen=True, slots=True)
class _Economy:
    """Hashable four-seat economy key for the exact-menu cache."""

    seats: tuple[_SeatAxis, ...]
    budget: int
    cap_workers: int


def _economy(roster: Roster, knobs: ScenarioKnobs) -> _Economy:
    if roster.n_seats != N_AGENTS:
        raise ValueError(
            f"token fairness menus support exactly {N_AGENTS} principals; "
            f"got {roster.n_seats}"
        )
    return _Economy(
        seats=tuple(
            _SeatAxis(
                name=principal,
                archetype=roster.profiles[principal].archetype,
                weight=roster.stakes_weights[principal],
            )
            for principal in roster.seat_ids
        ),
        budget=knobs.budget,
        cap_workers=knobs.cap_workers,
    )


def _ceilings(economy: _Economy) -> dict[str, float]:
    """Derive each principal's raw full-keep outcome ceiling."""
    return {
        seat.name: seat_value(
            seat.archetype,
            archetype_capacity(seat.archetype),
            1.0,
        )
        for seat in economy.seats
    }


def _is_maximal(
    economy: _Economy,
    keeps: tuple[int, ...],
) -> bool:
    """Whether no one-seat unit increment remains feasible.

    Every seat's outcome is strictly increasing in its kept count, and costs are
    monotone.  Therefore a feasible vector is coordinatewise Pareto-maximal exactly
    when no single next unit fits; any multi-coordinate dominator would contain such
    a feasible first increment.
    """
    for index, seat in enumerate(economy.seats):
        if keeps[index] >= archetype_capacity(seat.archetype):
            continue
        candidate = list(keeps)
        candidate[index] += 1
        workers = sum(
            seat_cost(axis.archetype, keep)[0]
            for axis, keep in zip(economy.seats, candidate, strict=True)
        )
        tokens = sum(
            seat_cost(axis.archetype, keep)[1]
            for axis, keep in zip(economy.seats, candidate, strict=True)
        )
        if workers <= economy.cap_workers and tokens <= economy.budget:
            return False
    return True


@lru_cache(maxsize=None)
def _exact_frontier(economy: _Economy) -> Frontier[TokenAllocation]:
    """Enumerate the full feasible menu and its full-vector Pareto frontier."""
    ceilings = _ceilings(economy)
    all_outcomes: list[OutcomePoint[TokenAllocation]] = []
    maximal_outcomes: list[OutcomePoint[TokenAllocation]] = []
    capacities = tuple(archetype_capacity(seat.archetype) for seat in economy.seats)
    for keeps in product(*(range(capacity + 1) for capacity in capacities)):
        workers = sum(
            seat_cost(seat.archetype, keep)[0]
            for seat, keep in zip(economy.seats, keeps, strict=True)
        )
        tokens = sum(
            seat_cost(seat.archetype, keep)[1]
            for seat, keep in zip(economy.seats, keeps, strict=True)
        )
        if workers > economy.cap_workers or tokens > economy.budget:
            continue
        realized = {
            seat.name: seat_value(seat.archetype, keep, 1.0)
            for seat, keep in zip(economy.seats, keeps, strict=True)
        }
        allocation = TokenAllocation(
            keeps=tuple(
                (seat.name, keep)
                for seat, keep in zip(economy.seats, keeps, strict=True)
            ),
            workers=workers,
            tokens=tokens,
        )
        outcome = OutcomePoint(
            plan=allocation,
            utility=sum(
                seat_value(seat.archetype, keep, seat.weight)
                for seat, keep in zip(economy.seats, keeps, strict=True)
            ),
            attainments=attainment_vector(realized, ceilings),
        )
        all_outcomes.append(outcome)
        if _is_maximal(economy, keeps):
            maximal_outcomes.append(outcome)

    if not all_outcomes:
        raise ValueError("token economy has no feasible allocation")
    optimum = max(outcome.utility for outcome in all_outcomes)
    # Filtering the 10k+ feasible stakes vectors pairwise would be needlessly
    # quadratic.  The monotone resource proof above first reduces them to the exact
    # coordinatewise-maximal set; the shared constructor then applies its canonical
    # full-vector Pareto filter and ordering to that set.
    efficient = frontier(maximal_outcomes, certified_optimum=optimum)
    all_points = tuple(
        FrontierPoint(
            outcome=outcome,
            evenness=outcome.attainments.evenness,
            utility_share=utility_share(outcome.utility, optimum),
        )
        for outcome in all_outcomes
    )
    return replace(efficient, plans=all_points)


def exact_frontier(roster: Roster, knobs: ScenarioKnobs) -> Frontier[TokenAllocation]:
    """Return the exhaustive exact outcome-fairness menu for a four-seat economy.

    The menu enumerates every feasible keep vector under both the output-token
    budget and worker cap.  Outcome attainment uses weight-1 raw value ceilings;
    stakes weights affect only group utility.
    """
    return _exact_frontier(_economy(roster, knobs))


def certified_ceilings(roster: Roster) -> dict[str, float]:
    """Return the four principals' independently derived raw outcome ceilings."""
    # The ceiling is a property of the roster's outcome shapes, not one scenario's
    # scarcity knobs.  `_economy` needs knobs only for menu feasibility, so construct
    # the mapping directly here.
    if roster.n_seats != N_AGENTS:
        raise ValueError(
            f"token fairness ceilings support exactly {N_AGENTS} principals; "
            f"got {roster.n_seats}"
        )
    return {
        principal: seat_value(
            roster.profiles[principal].archetype,
            archetype_capacity(roster.profiles[principal].archetype),
            1.0,
        )
        for principal in roster.seat_ids
    }


def _met_jobs(summary: Mapping[str, Any]) -> set[str]:
    jobs = summary.get("jobs")
    if not isinstance(jobs, Mapping):
        raise ValueError("token summary must contain a jobs mapping")
    met: set[str] = set()
    for job_id, row in cast(Mapping[object, object], jobs).items():
        if (
            isinstance(row, Mapping)
            and cast(Mapping[object, object], row).get("met") is True
        ):
            met.add(str(job_id))
    return met


def _scenario(summary: Mapping[str, Any]) -> str:
    scenario = summary.get("scenario")
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        raise ValueError(f"unknown token summary scenario: {scenario!r}")
    return scenario


def outcome_attainments(roster: Roster, met_jobs: set[str]) -> AttainmentVector:
    """Return raw outcome attainments of a met-job set against certified ceilings.

    Weight-1 realized values pair with `certified_ceilings`' weight-1 ceilings; stakes weights enter group utility only, never attainment.
    """
    raw_weights = {principal: 1.0 for principal in roster.seat_ids}
    raw_values = roster_value_from_met(roster, met_jobs, raw_weights)
    return attainment_vector(
        {principal: raw_values[principal] for principal in roster.seat_ids},
        certified_ceilings(roster),
    )


def _projection_fields(attempt: ProjectionAttempt) -> dict[str, Any]:
    """Render the three `frontier_projection*` summary fields from one attempt.

    Only an off-menu failure reaches the recorded-error branch: the live summary path attempts projection with `recoverable=(EvennessOffMenuError,)`, so any other certificate violation propagates before this renderer runs.
    """
    projected = attempt.projection
    return {
        "frontier_projection": (
            {
                "chosen_evenness": projected.chosen_evenness,
                "realized_utility_share": projected.realized_utility_share,
                "frontier_utility_share": projected.frontier_utility_share,
                "fairness_purchase": projected.fairness_purchase,
                "coordination_tax": projected.coordination_tax,
            }
            if projected is not None
            else None
        ),
        "frontier_projection_status": attempt.status,
        "frontier_projection_error": (
            {"error_type": type(attempt.error).__name__, "message": str(attempt.error)}
            if attempt.error is not None
            else None
        ),
    }


def fairness_readout_from_summary(
    summary: Mapping[str, Any],
    roster: Roster | None = None,
) -> dict[str, Any]:
    """Compute the pure outcome-fairness readout for a legacy physics summary.

    This is intentionally usable by report and analysis consumers without a
    live router.  It does not mutate `summary` and never reads its historical Jain
    field, which summarizes debits rather than outcomes.

    Args:
        summary: A token-cluster `World.summary()`-shaped physics mapping.
        roster: The underlying four-principal roster.  When omitted, resolve the
            scenario's registered roster; callers with an alternate cast must pass it.

    Returns:
        Stable, JSON-serializable outcome fairness and frontier-projection fields.

    Raises:
        ValueError: If the summary, roster, or projection certificates are invalid.
    """
    scenario = _scenario(summary)
    resolved_roster = roster or roster_for_scenario(scenario)
    if resolved_roster.n_seats != N_AGENTS:
        raise ValueError(
            f"token outcome fairness supports exactly {N_AGENTS} principals; "
            f"got {resolved_roster.n_seats}"
        )
    knobs = resolved_roster.knobs_for(scenario)
    if knobs != SCENARIOS[scenario]:
        raise ValueError(
            "four-seat fairness summary roster does not match the recorded scenario knobs"
        )
    met_jobs = _met_jobs(summary)
    attainments = outcome_attainments(resolved_roster, met_jobs)
    utility = roster_value_from_met(resolved_roster, met_jobs)["total"]
    menu = exact_frontier(resolved_roster, knobs)
    share = utility_share(utility, menu.certified_optimum)
    attempt = attempt_projection(
        attainments, menu, utility, recoverable=(EvennessOffMenuError,)
    )
    readout: dict[str, Any] = {
        "fairness_semantics": FAIRNESS_SEMANTICS,
        "outcome_jain": attainments.evenness,
        "outcome_attainment": {
            entry.name: entry.value for entry in attainments.entries
        },
        "outcome_ceilings": dict(attainments.ceilings),
        "minimum_attainment": attainments.minimum,
        "losers": list(attainments.losers),
        "named_loser": attainments.named_loser,
        "utility_share": share,
        "certified_optimum": menu.certified_optimum,
        **_projection_fields(attempt),
    }
    # Emitter and read-back cannot drift: a field added here without joining
    # `_READOUT_KEYS` would be stamped into new corpora but silently dropped on
    # every frozen-corpus read-back.
    assert set(readout) == set(_READOUT_KEYS), sorted(set(readout) ^ set(_READOUT_KEYS))
    return readout


#: The exact keys `fairness_readout_from_summary` emits — read back verbatim from
#: router-enriched summaries so a frozen enriched corpus is never silently recomputed.
_READOUT_KEYS: tuple[str, ...] = (
    "fairness_semantics",
    "outcome_jain",
    "outcome_attainment",
    "outcome_ceilings",
    "minimum_attainment",
    "losers",
    "named_loser",
    "utility_share",
    "certified_optimum",
    "frontier_projection",
    "frontier_projection_status",
    "frontier_projection_error",
)


def recorded_fairness_readout(summary: Mapping[str, Any]) -> dict[str, Any] | None:
    """Return the outcome-fairness readout for any recorded summary, or `None` when unsupported.

    Report layers consume recorded summaries of three vintages: router-enriched summaries return their stamped fields verbatim (never recomputed, so frozen corpora stay authoritative), pre-enrichment four-seat summaries derive the readout on the fly against the recorded scenario's registered roster, and non-four-seat casts return `None` — the same unsupported semantics the router stamps live. `None` is the one fairness answer for such casts; resource debits are never substituted.

    Raises:
        ValueError: If a four-seat summary is malformed (unknown scenario, knob drift, or bad certificates) — an anomaly, not an unsupported cast.
    """
    if summary.get("fairness_semantics") == UNSUPPORTED_FAIRNESS_SEMANTICS:
        return None
    if summary.get("fairness_semantics") == FAIRNESS_SEMANTICS:
        return {key: summary.get(key) for key in _READOUT_KEYS}
    roster = roster_for_scenario(_scenario(summary))
    if roster.n_seats != N_AGENTS:
        return None
    return fairness_readout_from_summary(summary, roster)


def enrich_summary(
    summary: Mapping[str, Any],
    roster: Roster | None = None,
) -> dict[str, Any]:
    """Return a copy of a physics summary enriched with explicit fairness semantics.

    The input must be a raw physics summary; this function is intentionally not
    idempotent, and refuses a second pass rather than overwriting its own fields.
    `jain` remains untouched for legacy readers, and its debit semantics are made
    explicit in `debit_jain` — synthesized from `jain` for frozen summaries that
    predate the alias. Every unprefixed fairness field comes from raw outcome
    attainment through `fairness_readout_from_summary`.

    Raises:
        ValueError: If inputs or projection certificates are invalid, `debit_jain`
            disagrees with `jain`, or any fairness readout key is already present.
    """
    raw_jain = summary.get("jain")
    if "debit_jain" in summary and summary["debit_jain"] != raw_jain:
        raise ValueError(
            "token summary debit_jain must equal its legacy jain value; "
            f"got debit_jain={summary['debit_jain']!r}, jain={raw_jain!r}"
        )

    readout = fairness_readout_from_summary(summary, roster)
    collisions = sorted(readout.keys() & summary.keys())
    if collisions:
        raise ValueError(
            "token physics summary already contains fairness readout keys: "
            f"{collisions}"
        )

    enriched = dict(summary)
    enriched["debit_jain"] = raw_jain
    enriched.update(readout)
    return enriched
