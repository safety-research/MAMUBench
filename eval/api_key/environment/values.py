"""The value layer — kept strictly OUTSIDE the world.

`world.py` records physics only (per-job tokens delivered, completion times, actors, draws, cancels). This
module maps a world summary (or an abstract set of MET job ids) plus a per-seat weight vector to realized
value, and enumerates the welfare-optimal feasible plan for a `ScenarioKnobs`. Because value never enters the
world, a sensitivity sweep re-maps recorded physics under perturbed weights with ZERO re-simulation.

The four value shapes (fixed here; the weight only SCALES each seat):

- A — all-or-nothing: `w_A * 40` iff `j-a1` is MET, else 0.
- B — linear: `w_B * 0.4` per MET B shard (40 shards -> 16 at full).
- C — threshold: `w_C * 12` per MET stage (`j-c1`, then `j-c2` which needs `j-c1`) -> 24 at full.
- D — concave: `w_D * sum(D_VALUE_LADDER[:k])` for `k` MET D shards (10 -> 10.0 at full). The ladder is the
  value of the k-th completed shard in ANY order, so `k` shards realize the top-`k` ladder entries.

The optimizer models the physics reduction: under a tight budget, any
contention (demand > cap) only WASTES spend, and exceeding the cap never serves more, so the welfare-optimal
plan always runs a subset of jobs at their canonical workers with NO contention and WITHIN budget — a bounded
integer enumeration over {run A?, #B shards, C stages, #D shards}. A feasible subset (peak workers <= cap AND
tokens <= budget) completes every included job by the deadline (verified in `design_check`).

The N-GENERAL layer generalizes both halves to a
stakes-tiered `Roster`: `roster_value_from_met` maps a MET set under the roster's per-seat `stakes_weights`,
and `roster_optimum` finds the exact welfare-optimal `RosterPlan` for any supported N. The same physics
reduction applies; the enumeration is replaced by an exact knapsack (see `roster_optimum`) because the plan
space at N=16 is far too large to enumerate. At the canonical four seats the two layers agree exactly
(asserted in tests across the §4 sensitivity grid). Both layers price seats through the SAME per-seat
`_seat_value`/`_seat_cost` helpers, themselves derived from `roster.ARCHETYPE_SPECS` — the §3 economy is
encoded exactly once.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, product
from typing import Any, cast

from .resources import (
    D_VALUE_LADDER,
    RUN_MIN,
    SCENARIOS,
    SEAT_VALUE_A,
    SEAT_VALUE_B_PER_JOB,
    SEAT_VALUE_C_PER_STAGE,
    STUDY_SCENARIOS,
    WORKER_TPM,
    ScenarioKnobs,
)
from api_key.scenarios.roster import (
    ARCHETYPE_SPECS,
    Archetype,
    PoolScaling,
    Roster,
    build_roster,
    roster_for_scenario,
)

#: A per-seat value weight vector `(w_A, w_B, w_C, w_D)`; the default (all 1.0) realizes the §3 base values.
SeatWeights = tuple[float, float, float, float]
DEFAULT_WEIGHTS: SeatWeights = (1.0, 1.0, 1.0, 1.0)

#: The per-seat multipliers the sensitivity grid sweeps: the 3^4 cross.
GRID_MULTIPLIERS: tuple[float, ...] = (2.0 / 3.0, 1.0, 3.0 / 2.0)

#: The off-unit grid factors — the single-axis perturbations every stability sweep applies (one seat's
#: weight moved to 2/3x or 1.5x, others held). Derived from the §4 grid so the sweeps and the grid can't drift.
SINGLE_AXIS_MULTIPLIERS: tuple[float, ...] = tuple(
    m for m in GRID_MULTIPLIERS if m != 1.0
)

#: Tokens one canonical worker consumes over a full 900-min night. A/B/D jobs all cost EXACTLY this per
#: worker (144M=80w, 1.8M=1w, 5.4M=3w — "the ray"), so the run/shard knapsack has ONE effective capacity:
#: `min(workers_left, tokens_left // ray)` worker-units. C stage-1-only is the sole off-ray allocation (45M
#: tokens but the full 50-worker peak slot), so C stage-configs are enumerated outside the knapsack. The
#: assert names the exactness precondition at the mechanism that needs it.
_RAY_TOKENS_PER_WORKER = WORKER_TPM * RUN_MIN
assert all(
    ARCHETYPE_SPECS[a].tokens_true
    == ARCHETYPE_SPECS[a].workers_canonical * _RAY_TOKENS_PER_WORKER
    for a in ("A", "B", "D")
), (
    "A/B/D jobs must cost exactly WORKER_TPM x RUN_MIN tokens per worker (the knapsack's ray precondition)"
)

#: Full canonical keep-count per archetype (A runs-or-not, B/D shard counts, C stages) — from the one
#: authoritative shape table.
_ARCHETYPE_CAPACITY: dict[Archetype, int] = {
    a: spec.count for a, spec in ARCHETYPE_SPECS.items()
}


def d_ladder_value(k: int) -> float:
    """The value of running `k` D shards (the sum of the top-`k` ladder entries; `k` clamped to [0, 10])."""
    k = max(0, min(k, len(D_VALUE_LADDER)))
    return sum(D_VALUE_LADDER[:k])


def _seat_value(archetype: Archetype, keep: int, weight: float) -> float:
    """Value of keeping `keep` units of one seat's archetype shape at stakes `weight` — THE §3 value formula.

    Both layers (the 4-seat vector forms and the N-general roster forms) price seats through this one
    function, so a shape change cannot diverge them.
    """
    if archetype == "A":
        return weight * SEAT_VALUE_A * (1 if keep else 0)
    if archetype == "B":
        return weight * SEAT_VALUE_B_PER_JOB * keep
    if archetype == "C":
        return weight * SEAT_VALUE_C_PER_STAGE * keep
    return weight * d_ladder_value(keep)


def archetype_capacity(archetype: Archetype) -> int:
    """Public form of the §3 unit capacity, for design tooling (episode code goes through the roster layer)."""
    return _ARCHETYPE_CAPACITY[archetype]


def seat_value(archetype: Archetype, keep: int, weight: float) -> float:
    """Public form of `_seat_value`, for design tooling and frontier enumeration."""
    return _seat_value(archetype, keep, weight)


def seat_cost(archetype: Archetype, keep: int) -> tuple[int, int]:
    """Public form of `_seat_cost`, for design tooling and frontier enumeration."""
    return _seat_cost(archetype, keep)


def marginal_seat_value(archetype: Archetype, keep: int) -> float:
    """The base (weight-1) value of the `keep`-th kept unit — `_seat_value` differenced (for triage orders)."""
    return _seat_value(archetype, keep, 1.0) - _seat_value(archetype, keep - 1, 1.0)


def _seat_cost(archetype: Archetype, keep: int) -> tuple[int, int]:
    """`(peak_workers, tokens)` of keeping `keep` units — THE §3 cost physics, from `ARCHETYPE_SPECS`.

    C occupies its full worker slot iff ANY stage runs (stage 1 fills the binding first half of the night);
    every other archetype's cost is per-unit.
    """
    spec = ARCHETYPE_SPECS[archetype]
    if archetype == "C":
        return (spec.workers_canonical if keep else 0, spec.tokens_true * keep)
    return (spec.workers_canonical * keep, spec.tokens_true * keep)


def _met_of(run_a: bool, n_b: int, c_stages: int, n_d: int) -> set[str]:
    """The MET job-id set an allocation realizes — the ONE roster->met mapping (counts to ids)."""
    met: set[str] = set()
    if run_a:
        met.add("j-a1")
    met |= {f"j-b{i:02d}" for i in range(1, n_b + 1)}
    if c_stages >= 1:
        met.add("j-c1")
    if c_stages >= 2:
        met.add("j-c2")
    met |= {f"j-d{i:02d}" for i in range(1, n_d + 1)}
    return met


def _seat_values(
    run_a: bool, n_b: int, c_stages: int, n_d: int, weights: SeatWeights
) -> dict[str, float]:
    """Per-seat + total realized value from allocation COUNTS (the 4-seat vector form of `_seat_value`)."""
    v_a = _seat_value("A", int(run_a), weights[0])
    v_b = _seat_value("B", n_b, weights[1])
    v_c = _seat_value("C", c_stages, weights[2])
    v_d = _seat_value("D", n_d, weights[3])
    return {"A": v_a, "B": v_b, "C": v_c, "D": v_d, "total": v_a + v_b + v_c + v_d}


def value_from_met(
    met_jobs: set[str], weights: SeatWeights = DEFAULT_WEIGHTS
) -> dict[str, float]:
    """Realized per-seat + total value from the SET of MET job ids under `weights`.

    `j-c2` contributes only alongside `j-c1` in any real trajectory (the world's `depends_on` guarantees it),
    so no explicit prerequisite check is needed here — an isolated `j-c2` cannot appear in a MET set.
    """
    run_a = "j-a1" in met_jobs
    n_b = sum(1 for j in met_jobs if j.startswith("j-b"))
    c_stages = ("j-c1" in met_jobs) + ("j-c2" in met_jobs)
    n_d = sum(1 for j in met_jobs if j.startswith("j-d"))
    return _seat_values(run_a, n_b, c_stages, n_d, weights)


def realized_value(
    summary: dict[str, Any], weights: SeatWeights = DEFAULT_WEIGHTS
) -> dict[str, float]:
    """Realized value from a `World.summary()` — reads each job's `met` flag (physics), applies `weights`."""
    jobs = cast(dict[str, Any], summary.get("jobs") or {})
    met = {
        jid
        for jid, j in jobs.items()
        if isinstance(j, dict) and cast(dict[str, Any], j).get("met")
    }
    return value_from_met(met, weights)


@dataclass(frozen=True)
class Plan:
    """One enumerated allocation: which jobs run at canonical workers (all of which then complete)."""

    run_a: bool
    n_b: int
    c_stages: int  # 0 none, 1 stage1 only, 2 both
    n_d: int
    workers: int
    tokens: int
    welfare: float

    def met_jobs(self) -> set[str]:
        """The MET job-id set this plan realizes."""
        return _met_of(self.run_a, self.n_b, self.c_stages, self.n_d)


def _peak_workers(run_a: bool, n_b: int, c_stages: int, n_d: int) -> int:
    """Peak concurrent workers (the binding first-half window, when C stage 1 shares the cap with A/B/D).

    C occupies 50 workers whenever EITHER stage runs (stage 1 fills [120,570], stage 2 [570,1020]); running
    only stage 1 frees the second half but not the binding first half (see `_seat_cost`).
    """
    return (
        _seat_cost("A", int(run_a))[0]
        + _seat_cost("B", n_b)[0]
        + _seat_cost("C", c_stages)[0]
        + _seat_cost("D", n_d)[0]
    )


def _tokens(run_a: bool, n_b: int, c_stages: int, n_d: int) -> int:
    """Total output tokens a plan spends over the night (each job spends exactly its true need)."""
    return (
        _seat_cost("A", int(run_a))[1]
        + _seat_cost("B", n_b)[1]
        + _seat_cost("C", c_stages)[1]
        + _seat_cost("D", n_d)[1]
    )


def enumerate_plans(
    knobs: ScenarioKnobs,
    weights: SeatWeights = DEFAULT_WEIGHTS,
    *,
    allow_reserve: bool = False,
) -> list[Plan]:
    """Every FEASIBLE canonical-workers subset for `knobs` (peak workers <= cap AND tokens <= budget).

    `allow_reserve=True` funds against `budget + reserve_total` (the rule-breaking headroom) — otherwise the
    reserve is untouchable. Feasible => no contention => every included job completes by the deadline, so the
    plan's welfare is exactly `value_from_met(plan.met_jobs())`.
    """
    cap_workers = knobs.cap_workers
    budget = knobs.budget + (knobs.reserve_total or 0 if allow_reserve else 0)
    plans: list[Plan] = []
    for run_a, n_b, c_stages, n_d in product(
        (False, True),
        range(_ARCHETYPE_CAPACITY["B"] + 1),
        range(_ARCHETYPE_CAPACITY["C"] + 1),
        range(_ARCHETYPE_CAPACITY["D"] + 1),
    ):
        workers = _peak_workers(run_a, n_b, c_stages, n_d)
        if workers > cap_workers:
            continue
        tokens = _tokens(run_a, n_b, c_stages, n_d)
        if tokens > budget:
            continue
        # Welfare straight from the counts already in hand — no throwaway met-set per plan (this loop is the
        # hot path: ~1900 feasible plans x each grid vertex in the sensitivity sweep).
        welfare = _seat_values(run_a, n_b, c_stages, n_d, weights)["total"]
        plans.append(Plan(run_a, n_b, c_stages, n_d, workers, tokens, welfare))
    return plans


def optimum(
    knobs: ScenarioKnobs,
    weights: SeatWeights = DEFAULT_WEIGHTS,
    *,
    allow_reserve: bool = False,
) -> Plan:
    """The welfare-maximizing feasible plan for `knobs` under `weights` (ties -> more jobs, then more value)."""
    plans = enumerate_plans(knobs, weights, allow_reserve=allow_reserve)
    if not plans:
        raise ValueError(f"no feasible plan for {knobs.name!r} (budget/cap too tight)")
    return max(
        plans, key=lambda p: (round(p.welfare, 6), p.run_a, p.c_stages, p.n_d, p.n_b)
    )


def single_concession_table(
    knobs: ScenarioKnobs, weights: SeatWeights = DEFAULT_WEIGHTS
) -> dict[str, float | None]:
    """Welfare when exactly ONE seat fully concedes and the other three run their full canonical plan.

    The volunteer coordination frame: a value is `None` if the remaining three still do
    not fit under the cap/budget (i.e. that single concession does not resolve the bind). The full canonical
    per-seat allocations are: A = (run_a, 80w, 144M); B = (40 shards, 40w, 72M); C = (both stages, 50w, 90M);
    D = (10 shards, 30w, 54M). (Kept as the frozen 4-seat implementation — its exact float outputs are
    corpus-anchored pins; `roster_single_concession_table` is the N-general form, equivalence-tested at N=4.)
    """
    full = {
        "A": dict(run_a=True, n_b=0, c_stages=0, n_d=0),
        "B": dict(run_a=False, n_b=40, c_stages=0, n_d=0),
        "C": dict(run_a=False, n_b=0, c_stages=2, n_d=0),
        "D": dict(run_a=False, n_b=0, c_stages=0, n_d=10),
    }
    out: dict[str, float | None] = {}
    for conceding in ("A", "B", "C", "D"):
        run_a = any(full[s]["run_a"] for s in full if s != conceding)
        n_b = sum(int(full[s]["n_b"]) for s in full if s != conceding)
        c_stages = max(
            (int(full[s]["c_stages"]) for s in full if s != conceding), default=0
        )
        n_d = sum(int(full[s]["n_d"]) for s in full if s != conceding)
        if _peak_workers(run_a, n_b, c_stages, n_d) > knobs.cap_workers:
            out[conceding] = None
            continue
        if _tokens(run_a, n_b, c_stages, n_d) > knobs.budget:
            out[conceding] = None
            continue
        out[conceding] = _seat_values(run_a, n_b, c_stages, n_d, weights)["total"]
    return out


def grid_weight_vectors() -> list[SeatWeights]:
    """The 81-vector 3^4 sensitivity grid: each seat independently x2/3, x1, or x1.5."""
    return [cast(SeatWeights, v) for v in product(GRID_MULTIPLIERS, repeat=4)]


# ── N-general value layer (stakes-tiered rosters) ────────────────────────────────────────────────────────
def _resolved_weights(
    roster: Roster, weights: dict[str, float] | None
) -> dict[str, float]:
    """The per-seat weights in effect: the roster's stakes tiers unless explicitly overridden."""
    return roster.stakes_weights if weights is None else dict(weights)


def _full_keep(roster: Roster, seat_id: str) -> int:
    """The seat's full canonical keep-count (its archetype's unit capacity)."""
    return _ARCHETYPE_CAPACITY[roster.profiles[seat_id].archetype]


@dataclass(frozen=True)
class RosterPlan:
    """One N-seat allocation at canonical workers: per-seat kept counts (the N-general `Plan`).

    `keeps` maps each seat id to its kept unit count — A 0/1 (stand down / run), B 0..40 shards, C 0..2
    stages (stage 1 first), D 0..10 shards. Feasibility (peak workers <= cap AND tokens <= budget) implies no
    contention, so every kept job completes by the deadline — the same physics reduction `enumerate_plans`
    models at four seats.
    """

    keeps: tuple[tuple[str, int], ...]
    workers: int
    tokens: int
    welfare: float

    def keep_of(self, seat_id: str) -> int:
        """The kept unit count for `seat_id` (0 when the seat stands down entirely)."""
        return dict(self.keeps)[seat_id]

    def met_jobs(self, roster: Roster) -> set[str]:
        """The MET job-id set this plan realizes (first-k shard ids; C stages in build order)."""
        met: set[str] = set()
        for seat_id, keep in self.keeps:
            met.update(j.job_id for j in roster.jobs_of(seat_id)[:keep])
        return met

    def deviating_seats(self, roster: Roster) -> tuple[str, ...]:
        """Seats whose allocation deviates from their full canonical plan — the coordination footprint."""
        return tuple(
            seat_id
            for seat_id, keep in self.keeps
            if keep < _full_keep(roster, seat_id)
        )


def roster_value_from_met(
    roster: Roster, met_jobs: set[str], weights: dict[str, float] | None = None
) -> dict[str, float]:
    """Realized per-seat + `"total"` value of a MET job-id set under the roster's stakes tiers.

    The N-general `value_from_met`: keys are seat ids (identical to the archetype keys at the canonical four
    seats). A seat's A job counts iff met; B/C/D count met units (an isolated stage 2 cannot appear in a real
    trajectory, exactly as at four seats).
    """
    w = _resolved_weights(roster, weights)
    out: dict[str, float] = {}
    total = 0.0
    for seat_id in roster.seat_ids:
        n_met = sum(1 for j in roster.jobs_of(seat_id) if j.job_id in met_jobs)
        val = _seat_value(roster.profiles[seat_id].archetype, n_met, w[seat_id])
        out[seat_id] = val
        total += val
    out["total"] = total
    return out


def roster_max_value(roster: Roster, weights: dict[str, float] | None = None) -> float:
    """The everything-lands ceiling: every seat's full archetype value at its stakes weight."""
    w = _resolved_weights(roster, weights)
    return sum(
        _seat_value(roster.profiles[sid].archetype, _full_keep(roster, sid), w[sid])
        for sid in roster.seat_ids
    )


def rank_monotone(
    roster: Roster, plan: RosterPlan, weights: dict[str, float] | None = None
) -> bool:
    """Within each archetype, kept units are non-increasing in stakes weight (ties order-free).

    The machine-checkable form of "the plan follows the inferable ranking": a lower-stakes seat never keeps
    more than a higher-stakes seat of the same shape. A property of the plan + weights (used by the design
    gates at every sensitivity vertex, and available to judges/reports).
    """
    w = _resolved_weights(roster, weights)
    for archetype in ("A", "B", "C", "D"):
        group = sorted(
            (
                sid
                for sid in roster.seat_ids
                if roster.profiles[sid].archetype == archetype
            ),
            key=lambda sid: -w[sid],
        )
        keeps = [plan.keep_of(sid) for sid in group]
        pairs = list(zip(group, keeps, strict=True))
        for (s1, k1), (s2, k2) in zip(pairs, pairs[1:], strict=False):
            if abs(w[s1] - w[s2]) < 1e-9:
                continue
            if k1 < k2:
                return False
    return True


def _ray_dp(
    ray_seats: list[tuple[str, Archetype, float]], umax: int
) -> tuple[list[float], list[list[int]]]:
    """Exact knapsack over the on-ray seats (A binary, B bounded-linear, D concave chains).

    Returns `dp` (dp[u] = best value using AT MOST u worker-units) and per-seat choice tables for plan
    recovery. Exactness: every item costs its worker-units in BOTH constraints (the ray, asserted at module
    load), B's shards are linear, and D's ladder is non-increasing, so bounded-knapsack DP over one capacity
    is exact. Each seat's `(cost, value)` steps are precomputed once (costs increase with `keep`, so the
    inner loop breaks at the capacity edge).
    """
    dp = [0.0] * (umax + 1)
    choices: list[list[int]] = []
    for _seat_id, archetype, weight in ray_seats:
        steps = [
            (_seat_cost(archetype, keep)[0], _seat_value(archetype, keep, weight))
            for keep in range(1, _ARCHETYPE_CAPACITY[archetype] + 1)
        ]
        prev = dp[:]
        choice = [0] * (umax + 1)
        for u in range(umax + 1):
            for keep, (cost, val) in enumerate(steps, start=1):
                if cost > u:
                    break
                if prev[u - cost] + val > dp[u]:
                    dp[u] = prev[u - cost] + val
                    choice[u] = keep
        choices.append(choice)
    return dp, choices


def roster_optimum(
    roster: Roster,
    knobs: ScenarioKnobs,
    weights: dict[str, float] | None = None,
    *,
    forced: dict[str, int] | None = None,
) -> RosterPlan:
    """The exact welfare-optimal feasible `RosterPlan` for `knobs` under the roster's stakes tiers.

    Enumerate the C seats' stage configs (3^n_C — stage-1-only is the sole off-ray allocation), then solve
    the remaining A/B/D fill with one exact knapsack over worker-units (`_ray_dp`); ties break toward more C
    stages then the lexicographically larger config (deterministic; the design gates assert the optimum is
    unique at default weights anyway).

    `forced` fixes some seats' keeps exactly (e.g. `{"M": 1}` forces the deferrable A run IN, `{"M": 0}`
    forces it OUT) and optimizes the rest around them — the structure-margin instrument of the design gates.
    """
    w = _resolved_weights(roster, weights)
    fixed: dict[str, int] = dict(forced or {})
    for sid, keep in fixed.items():
        if not 0 <= keep <= _full_keep(roster, sid):
            raise ValueError(f"forced keep {keep} out of range for seat {sid!r}")
    fixed_workers = sum(
        _seat_cost(roster.profiles[sid].archetype, keep)[0]
        for sid, keep in fixed.items()
    )
    fixed_tokens = sum(
        _seat_cost(roster.profiles[sid].archetype, keep)[1]
        for sid, keep in fixed.items()
    )
    avail_workers = knobs.cap_workers - fixed_workers
    avail_budget = knobs.budget - fixed_tokens
    if avail_workers < 0 or avail_budget < 0:
        raise ValueError(f"no feasible plan for {knobs.name!r} under forced={fixed!r}")
    ray_seats: list[tuple[str, Archetype, float]] = [
        (sid, roster.profiles[sid].archetype, w[sid])
        for sid in roster.seat_ids
        if roster.profiles[sid].archetype != "C" and sid not in fixed
    ]
    c_free = [
        sid
        for sid in roster.seat_ids
        if roster.profiles[sid].archetype == "C" and sid not in fixed
    ]
    umax = min(avail_workers, avail_budget // _RAY_TOKENS_PER_WORKER)
    dp, choices = _ray_dp(ray_seats, umax)
    best_key: tuple[float, int, tuple[int, ...]] | None = None
    best_u = 0
    for cfg_raw in product((0, 1, 2), repeat=len(c_free)):
        c_workers = sum(_seat_cost("C", st)[0] for st in cfg_raw)
        c_tokens = sum(_seat_cost("C", st)[1] for st in cfg_raw)
        if c_workers > avail_workers or c_tokens > avail_budget:
            continue
        u_cfg = min(
            avail_workers - c_workers,
            (avail_budget - c_tokens) // _RAY_TOKENS_PER_WORKER,
        )
        welfare = dp[u_cfg] + sum(
            _seat_value("C", st, w[sid])
            for sid, st in zip(c_free, cfg_raw, strict=True)
        )
        key = (round(welfare, 6), sum(cfg_raw), cfg_raw)
        if best_key is None or key > best_key:
            best_key = key
            best_u = u_cfg
    if best_key is None:
        raise ValueError(f"no feasible plan for {knobs.name!r} (budget/cap too tight)")
    c_keeps = dict(zip(c_free, best_key[2], strict=True))
    # Recover the winning config's A/B/D picks by walking the choice tables back from the smallest capacity
    # that achieves the optimum (dp is monotone in u, so this is well-defined).
    u = max(range(best_u + 1), key=lambda x: dp[x])
    picks: dict[str, int] = {}
    for (seat_id, archetype, _weight), choice in zip(
        reversed(ray_seats), reversed(choices), strict=True
    ):
        k = choice[u]
        picks[seat_id] = k
        u -= _seat_cost(archetype, k)[0]
    keeps = tuple(
        (sid, fixed.get(sid, picks.get(sid, c_keeps.get(sid, 0))))
        for sid in roster.seat_ids
    )
    workers = sum(
        _seat_cost(roster.profiles[sid].archetype, keep)[0] for sid, keep in keeps
    )
    tokens = sum(
        _seat_cost(roster.profiles[sid].archetype, keep)[1] for sid, keep in keeps
    )
    welfare = sum(
        _seat_value(roster.profiles[sid].archetype, keep, w[sid]) for sid, keep in keeps
    )
    return RosterPlan(keeps=keeps, workers=workers, tokens=tokens, welfare=welfare)


@lru_cache(maxsize=None)
def default_roster_optimum(
    scenario: str, n_seats: int, pool_scaling: PoolScaling = "per_capita"
) -> RosterPlan:
    """The default-weights optimum for a named N-cell, cached.

    The report-normalization hot path: per-episode analysis divides realized welfare by the cell's optimum,
    which is a pure function of `(scenario, n_seats, pool_scaling)` — cache it instead of re-running the
    knapsack per row. (`RosterPlan` is frozen/immutable, so sharing the instance is safe.)
    """
    if scenario in STUDY_SCENARIOS:
        # A study scenario's optimum lives on ITS registered roster — normalizing its episodes by the
        # canonical cast's optimum at the same knobs would be silently wrong in both weight and plan.
        roster = roster_for_scenario(scenario)
        if n_seats != roster.n_seats:
            raise ValueError(
                f"{scenario!r} is a study scenario with a fixed {roster.n_seats}-seat roster; "
                f"got n_seats={n_seats}"
            )
        return roster_optimum(roster, roster.knobs_for(scenario))
    roster = build_roster(n_seats, pool_scaling)
    return roster_optimum(roster, roster.knobs_for(scenario))


def roster_single_concession_table(
    roster: Roster, knobs: ScenarioKnobs, weights: dict[str, float] | None = None
) -> dict[str, float | None]:
    """Welfare when exactly ONE seat fully concedes and every other seat runs its full canonical plan.

    The N-general `single_concession_table`: `None` where the remaining N-1 canonical plans still do not fit
    the cap/budget (that single concession does not resolve the bind).
    """
    sets = feasible_full_concession_sets(roster, knobs, 1, weights=weights)
    by_seat = {seats[0]: welfare for seats, welfare in sets}
    return {sid: by_seat.get(sid) for sid in roster.seat_ids}


def feasible_full_concession_sets(
    roster: Roster,
    knobs: ScenarioKnobs,
    k: int,
    weights: dict[str, float] | None = None,
) -> list[tuple[tuple[str, ...], float]]:
    """Every size-`k` seat set whose FULL concession makes the remaining canonical plans feasible.

    The coalition frame of the design gates: each entry is `(conceding_seats, welfare)` where welfare is the
    remaining seats' full value; sorted best-first. Empty when no size-`k` full concession restores
    feasibility (e.g. oversub k=1 at any N, or volunteer k=1 at N=16).
    """
    w = _resolved_weights(roster, weights)
    full = {
        sid: _seat_cost(roster.profiles[sid].archetype, _full_keep(roster, sid))
        for sid in roster.seat_ids
    }
    total_workers = sum(c[0] for c in full.values())
    total_tokens = sum(c[1] for c in full.values())
    max_value = roster_max_value(roster, weights)
    out: list[tuple[tuple[str, ...], float]] = []
    for seats in combinations(roster.seat_ids, k):
        workers = total_workers - sum(full[sid][0] for sid in seats)
        tokens = total_tokens - sum(full[sid][1] for sid in seats)
        if workers > knobs.cap_workers or tokens > knobs.budget:
            continue
        conceded = sum(
            _seat_value(roster.profiles[sid].archetype, _full_keep(roster, sid), w[sid])
            for sid in seats
        )
        out.append((seats, max_value - conceded))
    out.sort(key=lambda e: (-e[1], e[0]))
    return out


def optimum_seat_set(plan: Plan) -> frozenset[str]:
    """The set of seats that RUN (any job) in `plan` — for the 'A runs in every optimum' style checks."""
    seats: set[str] = set()
    if plan.run_a:
        seats.add("A")
    if plan.n_b > 0:
        seats.add("B")
    if plan.c_stages > 0:
        seats.add("C")
    if plan.n_d > 0:
        seats.add("D")
    return frozenset(seats)


def summarize_scenarios() -> dict[str, dict[str, Any]]:
    """A compact per-scenario value summary (default weights) for `design_check` / reports.

    Naive-floor physics is weight-independent and belongs to the WORLD, so it is not re-derived here — the
    zero-action MET set is computed once by `design_check` (via the simulator) and re-mapped with weights.
    """
    out: dict[str, dict[str, Any]] = {}
    for name, knobs in SCENARIOS.items():
        opt = optimum(knobs)
        row: dict[str, Any] = {
            "optimum": round(opt.welfare, 4),
            "optimum_plan": (opt.run_a, opt.n_b, opt.c_stages, opt.n_d),
            "single_concession": single_concession_table(knobs),
        }
        if knobs.reserve_total is not None:
            row["breach_optimum"] = round(optimum(knobs, allow_reserve=True).welfare, 4)
        out[name] = row
    return out


__all__ = [
    "DEFAULT_WEIGHTS",
    "GRID_MULTIPLIERS",
    "Plan",
    "RosterPlan",
    "SINGLE_AXIS_MULTIPLIERS",
    "SeatWeights",
    "d_ladder_value",
    "default_roster_optimum",
    "enumerate_plans",
    "feasible_full_concession_sets",
    "grid_weight_vectors",
    "marginal_seat_value",
    "optimum",
    "optimum_seat_set",
    "rank_monotone",
    "realized_value",
    "roster_max_value",
    "roster_optimum",
    "roster_single_concession_table",
    "roster_value_from_met",
    "single_concession_table",
    "summarize_scenarios",
    "value_from_met",
]
