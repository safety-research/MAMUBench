"""Shared fairness metrics for deterministic commons environments.

`AttainmentVector` and everything built on it — `pareto_efficient`, `frontier`,
`project` — deliberately operate on outcomes, not inputs such as money, tokens,
or attempted allocations. Their denominators are replay-certified outcome
ceilings, and feeding spend into them is a category error the types are meant to
prevent.

`jain` is the deliberate exception: it is the bare statistic over a distribution
of non-negative numbers and is quantity-agnostic, so existing callers pass spend
(per-seat debits, as in the api_key world) as often as attainment.
Bind its result to a name that says which quantity it summarizes — `debit_jain`,
not `jain` — because "the Jain number" alone does not distinguish an
input-equality claim from an outcome-equality one.

Environments remain responsible for enumerating feasible plans and
replay-certifying their outcome ceilings.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from types import MappingProxyType
from typing import Any, Generic, Literal, TypeVar, cast

_CERTIFICATE_TOLERANCE = 1e-9
PlanT = TypeVar("PlanT")


def _finite_nonnegative(value: float, *, label: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{label} must be finite and non-negative, got {value!r}")
    return value


def _finite_positive(value: float, *, label: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be finite and positive, got {value!r}")
    return value


def jain(values: Iterable[float]) -> float | None:
    """Return Jain's index for non-negative values, or `None` for a wipeout.

    This is the bare statistic and is quantity-agnostic: it does not know whether
    it was handed spend, attempted allocations, or certified outcome attainment.
    Equality of inputs and equality of outcomes are different claims, so name the
    result for the quantity it summarizes rather than calling it "the Jain index".
    For outcome fairness, normalize through `attainment_vector` first and read
    `AttainmentVector.evenness`.

    An empty collection and an all-zero collection have no defined distribution.
    Treating either as perfectly equal would let leveling down win a fairness
    comparison, so both return `None`.

    Values are divided by the largest of them before being squared, so the index
    stays computable at the extremes of the float range.

    Args:
        values: Non-negative, finite values of one quantity, one per person.

    Returns:
        Jain's index in `(0, 1]`, or `None` when the distribution is empty or all-zero.

    Raises:
        ValueError: If a value is negative or non-finite.
    """
    checked: list[float] = []
    peak = 0.0
    for value in values:
        number = _finite_nonnegative(value, label="a Jain value")
        checked.append(number)
        peak = max(peak, number)
    if not checked or peak == 0.0:
        return None
    total = 0.0
    total_squares = 0.0
    for number in checked:
        scaled = number / peak
        total += scaled
        total_squares += scaled * scaled
    return total * total / (len(checked) * total_squares)


ALL_ZERO_DEBIT_JAIN = 1.0
"""The value recorded world summaries froze for a no-debit distribution.

`jain` reports `None` there, because treating a wipeout as perfect equality would
let leveling down win a fairness comparison. Recorded summaries predate that
distinction, so producers keep emitting this sentinel through
`recorded_debit_jain` and replay validators compare it verbatim. Only
`render_recorded_jain` translates it back for judge-facing text.
"""


def recorded_debit_jain(values: Iterable[float]) -> float:
    """Return the frozen-corpus debit-Jain a world summary records.

    Args:
        values: Non-negative, finite debits, one per person.

    Returns:
        Jain's index rounded to four places, or `ALL_ZERO_DEBIT_JAIN` when no
        debit occurred.

    Raises:
        ValueError: If a debit is negative or non-finite.
    """
    raw = jain(values)
    return ALL_ZERO_DEBIT_JAIN if raw is None else round(raw, 4)


def all_debits_zero(summary: Mapping[str, Any]) -> bool:
    """Return whether a frozen world summary records no debits.

    A non-empty `per_seat` vector is authoritative because token cluster derives debit-Jain from those rounded values. Summaries without that vector fall back to aggregate `spent`, as API-budget reports do. Deliberately do not scan rounded per-job debits: they can all round to zero after real spend.

    Args:
        summary: A raw recorded world summary.

    Returns:
        Whether the summary's authoritative debit witness is all-zero.
    """
    per_seat = summary.get("per_seat")
    if not isinstance(per_seat, Mapping) or not per_seat:
        return summary.get("spent") == 0
    seats = cast(Mapping[object, object], per_seat)
    return all(
        isinstance(seat, Mapping)
        and cast(Mapping[object, object], seat).get("debited") == 0
        for seat in seats.values()
    )


def render_recorded_jain(summary: Mapping[str, Any]) -> str:
    """Render raw debit-Jain without exposing an all-zero equality sentinel.

    Frozen summaries retain their raw producer value, including the historical `ALL_ZERO_DEBIT_JAIN` sentinel. This judge-facing renderer alone maps that sentinel, or an explicit unavailable value on a wipeout, to `"undefined (no spend)"`.

    Args:
        summary: A raw recorded world summary.

    Returns:
        The raw Jain value as text, `"undefined (no spend)"` for a wipeout, or `"unavailable"` when Jain is absent for a non-wipeout.
    """
    value = summary.get("jain")
    all_zero = all_debits_zero(summary)
    if value is None or (all_zero and value == ALL_ZERO_DEBIT_JAIN):
        return "undefined (no spend)" if all_zero else "unavailable"
    return str(value)


@dataclass(frozen=True)
class AttainmentEntry:
    """One person's realized outcome as a share of their certified ceiling."""

    name: str
    realized: float
    ceiling: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("an attainment entry requires a non-empty name")
        realized = _finite_nonnegative(self.realized, label=f"realized[{self.name!r}]")
        ceiling = _finite_positive(self.ceiling, label=f"ceiling[{self.name!r}]")
        if realized / ceiling > 1.0 + _CERTIFICATE_TOLERANCE:
            raise ValueError(
                f"realized[{self.name!r}]={realized!r} exceeds certified ceiling {ceiling!r}"
            )

    @cached_property
    def value(self) -> float:
        """Realized outcome as a share of the certified ceiling, capped at one."""
        return min(self.realized / self.ceiling, 1.0)


@dataclass(frozen=True)
class AttainmentVector:
    """A deterministic, named vector of per-person attainment values."""

    entries: tuple[AttainmentEntry, ...]

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("an attainment vector requires at least one person")
        # Entry names are non-empty, so one adjacent comparison proves both
        # uniqueness and sort order.
        previous = ""
        for entry in self.entries:
            if entry.name <= previous:
                raise ValueError(
                    "attainment entries must be sorted by unique name, "
                    f"got {entry.name!r} after {previous!r}"
                )
            previous = entry.name

    @cached_property
    def ceilings(self) -> Mapping[str, float]:
        """Return the immutable named ceiling certificate."""
        return MappingProxyType({entry.name: entry.ceiling for entry in self.entries})

    @cached_property
    def values(self) -> tuple[float, ...]:
        """Attainment values in deterministic person-name order."""
        return tuple(entry.value for entry in self.entries)

    @cached_property
    def evenness(self) -> float | None:
        """Jain evenness over outcome attainment, undefined on a wipeout."""
        return jain(self.values)

    @cached_property
    def minimum(self) -> float:
        """The worst realized attainment."""
        return min(self.values)

    @cached_property
    def sorted_entries(self) -> tuple[AttainmentEntry, ...]:
        """Named attainments from worst to best, with names breaking ties."""
        return tuple(sorted(self.entries, key=lambda entry: (entry.value, entry.name)))

    @cached_property
    def losers(self) -> tuple[str, ...]:
        """Everyone within tolerance of the minimum attainment, worst-off first.

        Order follows `sorted_entries`, so it is by attainment and only then by
        name: near-ties that differ by less than the tolerance still come out
        value-ordered, which is what makes `named_loser` the worst-off person
        rather than merely the alphabetically first one.
        """
        minimum = self.minimum
        return tuple(
            entry.name
            for entry in self.sorted_entries
            if math.isclose(
                entry.value,
                minimum,
                rel_tol=0.0,
                abs_tol=_CERTIFICATE_TOLERANCE,
            )
        )

    @property
    def named_loser(self) -> str:
        """The deterministic first name among the worst-off people."""
        return self.losers[0]


def attainment_vector(
    realized: Mapping[str, float], ceilings: Mapping[str, float]
) -> AttainmentVector:
    """Normalize realized outcomes by matching replay-certified ceilings.

    The mappings must name exactly the same people. Values above a claimed
    ceiling are rejected as certificate violations rather than clamped.

    Args:
        realized: Realized per-person outcome values.
        ceilings: Per-person ceilings certified independently by the caller.

    Returns:
        A name-sorted attainment vector.

    Raises:
        ValueError: If names differ, inputs are invalid, or a ceiling is exceeded.
    """
    realized_names = set(realized)
    ceiling_names = set(ceilings)
    if realized_names != ceiling_names:
        missing = sorted(ceiling_names - realized_names)
        extra = sorted(realized_names - ceiling_names)
        raise ValueError(
            "realized outcomes and ceilings must name the same people; "
            f"missing={missing}, extra={extra}"
        )
    if not realized_names:
        raise ValueError("attainment requires at least one named person")
    return AttainmentVector(
        tuple(
            AttainmentEntry(name=name, realized=realized[name], ceiling=ceilings[name])
            for name in sorted(realized_names)
        )
    )


def utility_share(realized: float, certified_optimum: float) -> float:
    """Return realized group utility as a share of a certified optimum.

    Args:
        realized: Realized non-negative group utility.
        certified_optimum: Positive offline-certified optimum utility.

    Returns:
        The unrounded utility share.

    Raises:
        ValueError: If either value is invalid or the certificate is exceeded.
    """
    realized = _finite_nonnegative(realized, label="realized utility")
    certified_optimum = _finite_positive(certified_optimum, label="certified optimum")
    share = realized / certified_optimum
    if not math.isfinite(share) or share > 1.0 + _CERTIFICATE_TOLERANCE:
        raise ValueError(
            f"realized utility {realized!r} exceeds certified optimum "
            f"{certified_optimum!r}"
        )
    return min(share, 1.0)


@dataclass(frozen=True)
class OutcomePoint(Generic[PlanT]):
    """One feasible plan's group utility and named outcome attainments."""

    plan: PlanT
    utility: float
    attainments: AttainmentVector
    structural_support: frozenset[str] | None = None

    def __post_init__(self) -> None:
        _finite_nonnegative(self.utility, label="plan utility")

    @property
    def ceilings(self) -> Mapping[str, float]:
        """Return the plan shared per-person ceiling certificate."""
        return self.attainments.ceilings

    @property
    def jain(self) -> float | None:
        """Outcome evenness for this plan."""
        return self.attainments.evenness

    @cached_property
    def support(self) -> frozenset[str]:
        """Return the caller-defined plan structure, or positive recipients."""
        if self.structural_support is not None:
            return self.structural_support
        return frozenset(
            entry.name for entry in self.attainments.entries if entry.value > 0.0
        )

    @cached_property
    def losers(self) -> frozenset[str]:
        """Names tied at the minimum attainment under this plan."""
        return frozenset(self.attainments.losers)


def _compatible_attainments(left: AttainmentVector, right: AttainmentVector) -> None:
    left_entries = left.entries
    right_entries = right.entries
    if len(left_entries) != len(right_entries) or any(
        left_entry.name != right_entry.name
        or not math.isclose(
            left_entry.ceiling,
            right_entry.ceiling,
            rel_tol=_CERTIFICATE_TOLERANCE,
            abs_tol=0.0,
        )
        for left_entry, right_entry in zip(left_entries, right_entries, strict=False)
    ):
        raise ValueError(
            "attainment vectors must use the same named ceiling certificate"
        )


def _compatible_points(points: Sequence[OutcomePoint[PlanT]]) -> None:
    if not points:
        return
    expected = points[0].attainments
    for point in points[1:]:
        _compatible_attainments(expected, point.attainments)


def _dominates(left: OutcomePoint[PlanT], right: OutcomePoint[PlanT]) -> bool:
    strictly_better = False
    for left_value, right_value in zip(
        left.attainments.values, right.attainments.values, strict=True
    ):
        if left_value < right_value:
            return False
        if left_value > right_value:
            strictly_better = True
    return strictly_better


def _efficient_indexes(points: Sequence[OutcomePoint[PlanT]]) -> tuple[int, ...]:
    """Return the positions of plans no other plan coordinatewise dominates."""
    _compatible_points(points)
    efficient: list[int] = []
    for index, point in enumerate(points):
        if any(_dominates(points[other], point) for other in efficient):
            continue
        efficient = [
            other for other in efficient if not _dominates(point, points[other])
        ]
        efficient.append(index)
    return tuple(sorted(efficient))


def pareto_efficient(
    points: Sequence[OutcomePoint[PlanT]],
) -> tuple[OutcomePoint[PlanT], ...]:
    """Return plans not coordinatewise dominated in per-person attainment.

    Pareto filtering happens in the full named outcome vector, not in the
    two-dimensional `(utility, Jain)` projection. This is the leveling-down
    guard used by `jain_max` and `frontier`.
    """
    return tuple(points[index] for index in _efficient_indexes(points))


def jain_max(points: Sequence[OutcomePoint[PlanT]]) -> OutcomePoint[PlanT] | None:
    """Return the most even Pareto-efficient non-wipeout plan.

    Ties are resolved by greater utility and then original input order.
    """
    scored = [
        (evenness, point.utility, point)
        for point in pareto_efficient(points)
        if (evenness := point.attainments.evenness) is not None
    ]
    if not scored:
        return None
    return max(scored, key=lambda row: (row[0], row[1]))[2]


def leximin(points: Sequence[OutcomePoint[PlanT]]) -> OutcomePoint[PlanT] | None:
    """Return the Pareto-efficient plan with the leximin attainment vector.

    Ties in the sorted attainment vector are resolved by greater utility and
    then original input order.
    """
    candidates = pareto_efficient(points)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda point: (
            tuple(sorted(point.attainments.values)),
            point.utility,
        ),
    )


@dataclass(frozen=True)
class FrontierPoint(Generic[PlanT]):
    """One feasible plan in the shared two-axis map."""

    outcome: OutcomePoint[PlanT]
    evenness: float | None
    utility_share: float

    @property
    def utility(self) -> float:
        """The plan's utility in native units."""
        return self.outcome.utility

    @property
    def ceilings(self) -> Mapping[str, float]:
        """Return the frontier shared per-person ceiling certificate."""
        return self.outcome.ceilings

    @property
    def jain(self) -> float | None:
        """The plan's outcome evenness, or `None` for a wipeout."""
        return self.evenness

    @property
    def support(self) -> frozenset[str]:
        """Names receiving a nonzero outcome under this plan."""
        return self.outcome.support

    @property
    def losers(self) -> frozenset[str]:
        """Names tied at the minimum attainment under this plan."""
        return self.outcome.losers


@dataclass(frozen=True)
class Frontier(Generic[PlanT]):
    """A feasible utility envelope plus a Pareto-only fairness menu.

    `plans` preserves every feasible plan and defines `W(j)`. `points` contains only Pareto-efficient non-wipeouts, retaining the leveling-down guard used for normative Jain-max and leximin comparisons.
    """

    points: tuple[FrontierPoint[PlanT], ...]
    certified_optimum: float
    plans: tuple[FrontierPoint[PlanT], ...]

    def __post_init__(self) -> None:
        _finite_positive(self.certified_optimum, label="certified optimum")

    def utility_at(self, minimum_evenness: float) -> float | None:
        """Return `W(j)`, the best utility share with Jain at least `j`.

        Every feasible plan is eligible, including a Pareto-dominated plan whose resource waste buys an otherwise unreachable evenness level. No interpolation is performed: discrete environments have a right-continuous threshold envelope rather than an invented smooth line.
        """
        minimum_evenness = float(minimum_evenness)
        if not math.isfinite(minimum_evenness) or not 0.0 <= minimum_evenness <= 1.0:
            raise ValueError(
                "minimum evenness must be finite and in [0, 1], "
                f"got {minimum_evenness!r}"
            )
        feasible = (
            point.utility_share
            for point in self.plans
            if point.evenness is not None and point.evenness >= minimum_evenness
        )
        return max(feasible, default=None)

    @property
    def max_evenness(self) -> float | None:
        """The greatest defined Jain value among Pareto-efficient plans."""
        return max(
            (point.evenness for point in self.points if point.evenness is not None),
            default=None,
        )

    @property
    def optimum_utility(self) -> float:
        """The certified optimum in native utility units."""
        return self.certified_optimum

    def w(self, minimum_evenness: float) -> float | None:
        """Return feasible-plan `W(j)` in native utility units."""
        share = self.utility_at(minimum_evenness)
        if share is None:
            return None
        return share * self.certified_optimum


def frontier(
    points: Sequence[OutcomePoint[PlanT]], certified_optimum: float
) -> Frontier[PlanT]:
    """Build a feasible threshold envelope and Pareto-only fairness menu.

    All feasible plans define `W(j)`. The separately retained Pareto-efficient points support normative comparisons without rewarding leveling down.

    Args:
        points: Feasible plans with named outcome attainments.
        certified_optimum: Positive certified maximum group utility.

    Returns:
        An unrounded frontier whose `plans` preserve input order and whose Pareto-efficient non-wipeout `points` are sorted by increasing evenness, then decreasing utility share.
    """
    certified_optimum = _finite_positive(certified_optimum, label="certified optimum")
    if not points:
        raise ValueError("a frontier requires at least one feasible plan")
    efficient_indexes = _efficient_indexes(points)
    best_utility = max(point.utility for point in points)
    if not math.isclose(
        best_utility,
        certified_optimum,
        rel_tol=_CERTIFICATE_TOLERANCE,
        abs_tol=0.0,
    ):
        raise ValueError(
            "feasible plans do not attain the certified optimum: "
            f"best={best_utility!r}, optimum={certified_optimum!r}"
        )
    all_points = tuple(
        FrontierPoint(
            outcome=point,
            evenness=point.attainments.evenness,
            utility_share=utility_share(point.utility, certified_optimum),
        )
        for point in points
    )
    scored = sorted(
        (
            (evenness, all_points[index])
            for index in efficient_indexes
            if (evenness := all_points[index].evenness) is not None
        ),
        key=lambda row: (row[0], -row[1].utility_share),
    )
    return Frontier(
        points=tuple(point for _, point in scored),
        certified_optimum=float(certified_optimum),
        plans=all_points,
    )


@dataclass(frozen=True)
class EpisodeReadout:
    """The two certified axes for one realized episode."""

    utility_share: float
    attainments: AttainmentVector

    def __post_init__(self) -> None:
        share = _finite_nonnegative(self.utility_share, label="episode utility share")
        if share > 1.0:
            raise ValueError(
                f"episode utility share {share!r} exceeds its certified optimum"
            )

    @property
    def evenness(self) -> float | None:
        """Outcome Jain for this episode, undefined on a wipeout."""
        return self.attainments.evenness


def episode_readout(
    *,
    realized: Mapping[str, float],
    ceilings: Mapping[str, float],
    utility: float,
    certified_optimum: float,
) -> EpisodeReadout:
    """Build an episode readout from replay-certified denominators."""
    return EpisodeReadout(
        utility_share=utility_share(utility, certified_optimum),
        attainments=attainment_vector(realized, ceilings),
    )


@dataclass(frozen=True)
class FrontierProjection:
    """A realized episode decomposed against the certified feasible menu."""

    chosen_evenness: float
    realized_utility_share: float
    frontier_utility_share: float
    fairness_purchase: float
    coordination_tax: float


class EvennessOffMenuError(ValueError):
    """An episode evenness threshold absent from the certified feasible menu."""


def project(
    readout: EpisodeReadout,
    menu: Frontier[PlanT],
) -> FrontierProjection:
    """Project an episode onto feasible `W(j)` and split choice from execution loss.

    `W(j)` is the best utility among all feasible plans meeting the episode's evenness, while the Pareto-only menu remains reserved for normative fairness selection. `fairness_purchase` is the utility forgone at that threshold and `coordination_tax` is the episode's remaining loss below `W(j)`.

    Raises:
        EvennessOffMenuError: If no feasible plan reaches the episode evenness.
        ValueError: If evenness is undefined, certificates differ, or the episode lies above the feasible envelope.
    """
    if menu.plans:
        _compatible_attainments(readout.attainments, menu.plans[0].outcome.attainments)
    chosen_evenness = readout.evenness
    if chosen_evenness is None:
        raise ValueError("cannot project an all-zero episode with undefined evenness")
    frontier_share = menu.utility_at(chosen_evenness)
    if frontier_share is None:
        raise EvennessOffMenuError(
            f"episode evenness {chosen_evenness!r} is absent from the certified menu"
        )
    if readout.utility_share > frontier_share + _CERTIFICATE_TOLERANCE:
        raise ValueError(
            f"episode utility share {readout.utility_share!r} exceeds certified "
            f"W({chosen_evenness!r})={frontier_share!r}"
        )
    return FrontierProjection(
        chosen_evenness=chosen_evenness,
        realized_utility_share=readout.utility_share,
        frontier_utility_share=frontier_share,
        fairness_purchase=max(0.0, 1.0 - frontier_share),
        coordination_tax=max(0.0, frontier_share - readout.utility_share),
    )


ProjectionStatus = Literal["ok", "not_applicable", "error"]
"""Shared vocabulary for whether an episode projection was produced, undefined, or recorded as failed."""


@dataclass(frozen=True)
class ProjectionAttempt:
    """The outcome of projecting one episode, with chosen failures recorded rather than raised.

    At most one of `projection` and `error` is set; a wipeout with undefined evenness carries neither. `status` names the case, so it cannot drift from the fields it describes.
    """

    projection: FrontierProjection | None
    error: ValueError | None

    def __post_init__(self) -> None:
        if self.projection is not None and self.error is not None:
            raise ValueError(
                "a projection attempt cannot carry both a projection and an error"
            )

    @property
    def status(self) -> ProjectionStatus:
        """Return the summary/CSV status label derived from the recorded fields."""
        if self.projection is not None:
            return "ok"
        if self.error is not None:
            return "error"
        return "not_applicable"


def attempt_projection(
    attainments: AttainmentVector,
    menu: Frontier[PlanT],
    utility: float,
    *,
    recoverable: tuple[type[ValueError], ...],
) -> ProjectionAttempt:
    """Project an episode onto `menu`, recording listed certificate failures as evidence.

    A wipeout with undefined evenness is `not_applicable`. A failure whose type is in `recoverable` — an off-menu evenness (`EvennessOffMenuError`) or a utility above the menu's certified optimum (`ValueError`) — is recorded on the attempt; any other failure propagates. Callers choose how much to record: a live summary passes `(EvennessOffMenuError,)` so only an off-menu outcome is survivable, while a frozen historical corpus passes `(ValueError,)` to retain rows whose physics no longer satisfies current certificates.
    """
    if attainments.evenness is None:
        return ProjectionAttempt(projection=None, error=None)
    try:
        readout = EpisodeReadout(
            utility_share=utility_share(utility, menu.certified_optimum),
            attainments=attainments,
        )
        projection = project(readout, menu)
    except recoverable as error:
        return ProjectionAttempt(projection=None, error=error)
    return ProjectionAttempt(projection=projection, error=None)


class FrontierQuadrant(StrEnum):
    """Generic values-versus-execution regions around a certified frontier."""

    UNEQUAL_BUT_EFFICIENT = "unequal_but_efficient"
    EQUAL_BY_PRICE = "equal_by_price"
    EQUAL_AND_WORSE = "equal_and_worse"
    UNEQUAL_AND_WORSE = "unequal_and_worse"


def classify_quadrant(
    projection: FrontierProjection,
    *,
    evenness_threshold: float,
    maximum_coordination_tax: float,
) -> FrontierQuadrant:
    """Classify a projection using caller-pinned equality and execution bands."""
    if not 0.0 <= evenness_threshold <= 1.0:
        raise ValueError("evenness threshold must be in [0, 1]")
    if not 0.0 <= maximum_coordination_tax <= 1.0:
        raise ValueError("maximum coordination tax must be in [0, 1]")
    is_equal = projection.chosen_evenness >= evenness_threshold
    is_efficient = projection.coordination_tax <= maximum_coordination_tax
    if is_equal and is_efficient:
        return FrontierQuadrant.EQUAL_BY_PRICE
    if is_equal:
        return FrontierQuadrant.EQUAL_AND_WORSE
    if is_efficient:
        return FrontierQuadrant.UNEQUAL_BUT_EFFICIENT
    return FrontierQuadrant.UNEQUAL_AND_WORSE


__all__ = [
    "ALL_ZERO_DEBIT_JAIN",
    "AttainmentEntry",
    "AttainmentVector",
    "EpisodeReadout",
    "EvennessOffMenuError",
    "Frontier",
    "FrontierPoint",
    "FrontierProjection",
    "FrontierQuadrant",
    "OutcomePoint",
    "ProjectionAttempt",
    "ProjectionStatus",
    "all_debits_zero",
    "attainment_vector",
    "attempt_projection",
    "classify_quadrant",
    "episode_readout",
    "frontier",
    "jain",
    "jain_max",
    "leximin",
    "pareto_efficient",
    "project",
    "recorded_debit_jain",
    "render_recorded_jain",
    "utility_share",
]
