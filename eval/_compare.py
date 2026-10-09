"""Comparison statistics shared by the four evals' readouts (their SCORE and CONTRAST rows).

Two kinds of comparison are needed to read an eval against the paper:

- a **contrast** between formations of the same model on the same scenario (coordinator minus
  team, coordinator minus team_silent, team minus team_silent), with a 95% interval;
- a **baseline delta** between a run cell and a frozen reference cell (the paper's number for the
  same scenario and formation, or the Claude Opus 5 number for the same scenario and formation).

Each eval scores a different unit (api_key: a night's welfare over optimum; clinic: a morning's
met / contests; personal_assistant: a 0/1 episode; merge_queue: an episode's welfare over optimum),
so the interval methods live here and the evals supply units:

- `welch_diff`: difference of two means from summary statistics (Welch t interval).
- `newcombe_diff`: difference of two proportions (Newcombe / Wilson score, method 10).
- `bootstrap_diff` / `stratified_bootstrap_diff`: seeded percentile bootstrap over whole units,
  the paper's method for clustered clinic contests (whole mornings, stratified by board).

Everything is dependency-free and deterministic (`DEFAULT_SEED`). Percentages in the row builders
are in points (`pp`), rounded to two decimals.

Every row carries a `mitigation` column (`none` for the control arm): the evals compute score, pooled and
contrast rows per mitigation arm (`_mitigations.partition`), so arms never pool and a contrast is always
between formations of one arm.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from _mitigations import NONE
from _stats import wilson

DEFAULT_SEED = 20260921
DEFAULT_DRAWS = 2000

#: The three formation contrasts every table reports, as (a, b) meaning a minus b.
CONTRASTS: tuple[tuple[str, str], ...] = (
    ("coordinator", "team"),
    ("coordinator", "team_silent"),
    ("team", "team_silent"),
)

#: Columns of a per-cell score row (one per env, scenario, model, formation, mitigation) and of the pooled rows.
SCORE_COLUMNS: tuple[str, ...] = (
    "env",
    "scenario",
    "model",
    "formation",
    "mitigation",
    "unit",
    "n",
    "score",
    "ci_lo",
    "ci_hi",
    "ci_method",
    "paper_score",
    "paper_n",
    "paper_instrument",
    "paper_delta_pp",
    "paper_verdict",
    "opus5_score",
    "opus5_n",
    "opus5_instrument",
    "opus5_delta_pp",
    "opus5_delta_lo_pp",
    "opus5_delta_hi_pp",
    "opus5_delta_method",
)

#: Columns of a contrast row (one per env, scenario, model, mitigation, contrast) and of the pooled rows.
CONTRAST_COLUMNS: tuple[str, ...] = (
    "env",
    "scenario",
    "model",
    "mitigation",
    "contrast",
    "n_a",
    "n_b",
    "diff_pp",
    "lo_pp",
    "hi_pp",
    "method",
    "ref_diff_pp",
    "ref_lo_pp",
    "ref_hi_pp",
    "ref_method",
    "ref_instrument",
)


@dataclass(frozen=True)
class Diff:
    """A difference `a - b` with its 95% interval and the method that produced it."""

    point: float
    lo: float
    hi: float
    method: str
    n_a: int
    n_b: int

    def as_pp(self) -> dict[str, float | str | int]:
        """The difference in percentage points, rounded for a table."""
        return {
            "diff_pp": pp(self.point),
            "lo_pp": pp(self.lo),
            "hi_pp": pp(self.hi),
            "method": self.method,
            "n_a": self.n_a,
            "n_b": self.n_b,
        }


def pp(value: float) -> float:
    """A fraction as percentage points, two decimals; `nan` stays `nan`."""
    return value if math.isnan(value) else round(100.0 * value, 2)


def clip01(interval: tuple[float, float]) -> tuple[float, float]:
    """Clip an interval for a [0, 1] metric."""
    lo, hi = interval
    return (max(0.0, lo), min(1.0, hi))


# ── Student's t (no scipy) ────────────────────────────────────────────────────────────────────────


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Numerical Recipes `betacf`)."""
    max_iterations = 300
    eps = 3.0e-14
    tiny = 1.0e-300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_beta = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )
    front = math.exp(log_beta)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(x: float, df: float) -> float:
    """CDF of Student's t with `df` degrees of freedom."""
    if df <= 0:
        raise ValueError("df must be positive")
    if math.isinf(x):
        return 1.0 if x > 0 else 0.0
    tail = 0.5 * _betai(df / 2.0, 0.5, df / (df + x * x))
    return 1.0 - tail if x >= 0 else tail


def t_quantile(p: float, df: float) -> float:
    """The `p` quantile of Student's t with `df` degrees of freedom (bisection on `t_cdf`)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    if df <= 0:
        raise ValueError("df must be positive")
    if df > 1e6:
        return statistics.NormalDist().inv_cdf(p)
    if p == 0.5:
        return 0.0
    if p < 0.5:
        return -t_quantile(1.0 - p, df)
    lo, hi = 0.0, 1.0
    while t_cdf(hi, df) < p:
        hi *= 2.0
        if hi > 1e12:
            return math.inf
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12:
            break
    return 0.5 * (lo + hi)


# ── closed-form intervals ─────────────────────────────────────────────────────────────────────────


def welch_diff(
    mean_a: float, sd_a: float, n_a: int, mean_b: float, sd_b: float, n_b: int
) -> Diff:
    """`mean_a - mean_b` with a Welch t interval; bounds are `nan` when either side has `n < 2`."""
    point = mean_a - mean_b
    if n_a < 2 or n_b < 2:
        return Diff(point, math.nan, math.nan, "welch (n<2, no interval)", n_a, n_b)
    va = sd_a * sd_a / n_a
    vb = sd_b * sd_b / n_b
    se = math.sqrt(va + vb)
    if se == 0.0:
        return Diff(point, point, point, "welch (zero variance)", n_a, n_b)
    df = (va + vb) ** 2 / (va * va / (n_a - 1) + vb * vb / (n_b - 1))
    half = t_quantile(0.975, df) * se
    return Diff(point, point - half, point + half, "welch", n_a, n_b)


def newcombe_diff(k_a: int, n_a: int, k_b: int, n_b: int) -> Diff:
    """`k_a/n_a - k_b/n_b` with Newcombe's Wilson-score interval (method 10); `nan` on an empty side."""
    if n_a <= 0 or n_b <= 0:
        return Diff(math.nan, math.nan, math.nan, "newcombe (empty side)", n_a, n_b)
    p_a = k_a / n_a
    p_b = k_b / n_b
    l_a, u_a = wilson(k_a, n_a)
    l_b, u_b = wilson(k_b, n_b)
    point = p_a - p_b
    lo = point - math.sqrt((p_a - l_a) ** 2 + (u_b - p_b) ** 2)
    hi = point + math.sqrt((u_a - p_a) ** 2 + (p_b - l_b) ** 2)
    return Diff(point, max(-1.0, lo), min(1.0, hi), "newcombe", n_a, n_b)


# ── seeded bootstraps over whole units ────────────────────────────────────────────────────────────

Statistic = Callable[[Sequence[Any]], float]
Combine = Literal["units", "strata"]


def mean_stat(units: Sequence[Any]) -> float:
    """Mean of numeric units (a night's or an episode's score)."""
    return statistics.fmean(float(u) for u in units)


def rate_stat(units: Sequence[Any]) -> float:
    """Pooled rate of `(successes, trials)` units (a morning's met / contests)."""
    successes = sum(int(u[0]) for u in units)
    trials = sum(int(u[1]) for u in units)
    return successes / trials if trials else math.nan


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return math.nan
    position = q * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def bootstrap_diff(
    units_a: Sequence[Any],
    units_b: Sequence[Any],
    statistic: Statistic,
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
    label: str = "bootstrap",
) -> Diff:
    """`statistic(a) - statistic(b)` with a seeded percentile interval over resampled units."""
    return stratified_bootstrap_diff(
        {"": (units_a, units_b)},
        statistic,
        combine="units",
        draws=draws,
        seed=seed,
        label=label,
    )


def stratified_bootstrap_diff(
    strata: Mapping[str, tuple[Sequence[Any], Sequence[Any]]],
    statistic: Statistic,
    *,
    combine: Combine = "units",
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
    label: str = "bootstrap",
) -> Diff:
    """Resample units within every stratum, then combine across strata.

    `combine="units"` concatenates the resampled units of all strata before applying `statistic`
    (unit-weighted pooling: api_key nights, clinic contests, personal_assistant episodes).
    `combine="strata"` applies `statistic` per stratum and averages the results (equal-weighted
    scenarios: the merge queue's board mean). The point estimate uses the same combination on the
    original units. Strata missing either side are skipped; with no usable stratum the bounds are `nan`.
    """
    usable = {k: (list(a), list(b)) for k, (a, b) in strata.items() if a and b}
    if not usable:
        return Diff(math.nan, math.nan, math.nan, f"{label} (no data)", 0, 0)

    def evaluate(sample: Mapping[str, tuple[list[Any], list[Any]]]) -> float:
        if combine == "units":
            all_a = [u for a, _ in sample.values() for u in a]
            all_b = [u for _, b in sample.values() for u in b]
            return statistic(all_a) - statistic(all_b)
        return statistics.fmean(statistic(a) - statistic(b) for a, b in sample.values())

    point = evaluate(usable)
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(draws):
        resampled = {
            k: (rng.choices(a, k=len(a)), rng.choices(b, k=len(b)))
            for k, (a, b) in usable.items()
        }
        values.append(evaluate(resampled))
    values.sort()
    n_a = sum(len(a) for a, _ in usable.values())
    n_b = sum(len(b) for _, b in usable.values())
    suffix = "" if combine == "units" else " (strata mean)"
    return Diff(
        point,
        _percentile(values, 0.025),
        _percentile(values, 0.975),
        f"{label}{suffix}, {draws} draws, seed {seed}",
        n_a,
        n_b,
    )


# ── row builders ──────────────────────────────────────────────────────────────────────────────────

ReferenceDiff = Callable[[str | None, str, str, str], "Diff | None"]


def contrast_rows(
    env: str,
    units: Mapping[tuple[str, str, str], Sequence[Any]],
    statistic: Statistic,
    *,
    combine: Combine = "units",
    reference: ReferenceDiff | None = None,
    reference_instrument: str | None = None,
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Per-scenario and pooled formation contrasts from clean units.

    Args:
        env: The eval name for the `env` column.
        units: `(scenario, model, formation) -> clean units` (floats for a mean statistic,
            `(successes, trials)` pairs for a rate statistic).
        statistic: `mean_stat` or `rate_stat` (or any `Sequence -> float`).
        combine: How pooled rows combine scenarios (see `stratified_bootstrap_diff`).
        reference: Optional `(scenario | None, model, a, b) -> Diff | None` giving the frozen
            reference's contrast for a scenario (or the pooled contrast when `scenario` is None).
        reference_instrument: Label for the `ref_instrument` column.
        draws: Bootstrap draws.
        seed: Bootstrap seed.

    Returns:
        `(per_scenario_rows, pooled_rows)`, each a list of `CONTRAST_COLUMNS` dicts.
    """
    scenarios = sorted({k[0] for k in units})
    models = sorted({k[1] for k in units})
    per_scenario: list[dict[str, Any]] = []
    pooled: list[dict[str, Any]] = []
    for model in models:
        for a, b in CONTRASTS:
            strata: dict[str, tuple[Sequence[Any], Sequence[Any]]] = {}
            for scenario in scenarios:
                ua = units.get((scenario, model, a))
                ub = units.get((scenario, model, b))
                if not ua or not ub:
                    continue
                strata[scenario] = (ua, ub)
                diff = bootstrap_diff(ua, ub, statistic, draws=draws, seed=seed)
                per_scenario.append(
                    _contrast_row(
                        env,
                        scenario,
                        model,
                        f"{a}-{b}",
                        diff,
                        reference(scenario, model, a, b) if reference else None,
                        reference_instrument,
                    )
                )
            if not strata:
                continue
            pooled_diff = stratified_bootstrap_diff(
                strata, statistic, combine=combine, draws=draws, seed=seed
            )
            pooled.append(
                _contrast_row(
                    env,
                    f"POOLED ({len(strata)} scenarios)",
                    model,
                    f"{a}-{b}",
                    pooled_diff,
                    reference(None, model, a, b) if reference else None,
                    reference_instrument,
                )
            )
    return per_scenario, pooled


def _contrast_row(
    env: str,
    scenario: str,
    model: str,
    contrast: str,
    diff: Diff,
    ref: Diff | None,
    ref_instrument: str | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "env": env,
        "scenario": scenario,
        "model": model,
        "mitigation": NONE,
        "contrast": contrast,
        **diff.as_pp(),
        "ref_diff_pp": None,
        "ref_lo_pp": None,
        "ref_hi_pp": None,
        "ref_method": None,
        "ref_instrument": None,
    }
    if ref is not None:
        row.update(
            ref_diff_pp=pp(ref.point),
            ref_lo_pp=None if math.isnan(ref.lo) else pp(ref.lo),
            ref_hi_pp=None if math.isnan(ref.hi) else pp(ref.hi),
            ref_method=ref.method,
            ref_instrument=ref_instrument,
        )
    return {column: row.get(column) for column in CONTRAST_COLUMNS}


def baseline_columns(
    run_diff: Diff | None, reference_cell: Mapping[str, Any] | None, *, prefix: str
) -> dict[str, Any]:
    """The `<prefix>_score / _n / _instrument / _delta_*` columns of a score row.

    `reference_cell` carries `score`, `n` and `instrument`; `run_diff` is the run cell minus the
    reference cell (`welch_diff` / `newcombe_diff`), or None when either side is missing.
    """
    out: dict[str, Any] = {
        f"{prefix}_score": None,
        f"{prefix}_n": None,
        f"{prefix}_instrument": None,
        f"{prefix}_delta_pp": None,
        f"{prefix}_delta_lo_pp": None,
        f"{prefix}_delta_hi_pp": None,
        f"{prefix}_delta_method": None,
    }
    if reference_cell is None:
        return out
    out[f"{prefix}_score"] = round(float(reference_cell["score"]), 4)
    out[f"{prefix}_n"] = int(reference_cell["n"])
    out[f"{prefix}_instrument"] = reference_cell.get("instrument")
    if run_diff is not None:
        out[f"{prefix}_delta_pp"] = pp(run_diff.point)
        out[f"{prefix}_delta_lo_pp"] = (
            None if math.isnan(run_diff.lo) else pp(run_diff.lo)
        )
        out[f"{prefix}_delta_hi_pp"] = (
            None if math.isnan(run_diff.hi) else pp(run_diff.hi)
        )
        out[f"{prefix}_delta_method"] = run_diff.method
    return out


def score_row(env: str, **values: Any) -> dict[str, Any]:
    """A `SCORE_COLUMNS` dict with every unset column as None (`mitigation` defaults to `none`)."""
    row: dict[str, Any] = {column: None for column in SCORE_COLUMNS}
    row["env"] = env
    row["mitigation"] = NONE
    for key, value in values.items():
        if key not in row:
            raise KeyError(f"{key!r} is not a SCORE_COLUMNS column")
        row[key] = value
    return row


# ── rendering ─────────────────────────────────────────────────────────────────────────────────────


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.4g}" if abs(value) < 1 else f"{value:.2f}"
    return str(value)


def markdown_table(rows: Iterable[Mapping[str, Any]], columns: Sequence[str]) -> str:
    """Render rows as a GitHub-flavoured markdown table over `columns`."""
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_cell_text(row.get(c)) for c in columns) + " |")
    return "\n".join(lines) + "\n"
