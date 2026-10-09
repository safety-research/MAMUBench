"""The paper's estimators for the API key numbers, dependency-free (report.py and check.py).

- `t95` / `mean_ci`: the helpers of the paper's figure scripts (supplementary material), verbatim (the paper's ONE interval: a two-sided 95% Student-t
  interval on a mean over episodes; the t critical values are its table, off-table degrees of freedom round DOWN so
  an interval is never narrower than the true one, and the tail stays at the df=120 value).
- `pool`: per-cell `(mean, sd, n)` pooled into the `(mean, sd, n)` of the pooled episodes EXACTLY (sd is the
  sample sd over every episode, `sum((n_i - 1) sd_i^2 + n_i (m_i - m)^2) / (N - 1)`), so a pooled interval from
  cells equals `mean_ci` over the pooled episodes, as the team-size figure (`fig:tc-welfare`) pools per team size.
- `equal_weight_ci`: the equal-weight mean of scenario means with the 95% t interval in which every episode is
  weighted 1 / (its scenario's episode count), computed from cell statistics. With equal counts it reduces to the pooled interval; the provider-error screen leaves 0-20
  episodes per scenario, where it does not (the overview figure keeps the equal-weight mean as its bar and the
  pooled interval as its whisker).
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence

#: Two-sided 95% Student-t critical values (the figure scripts' `_T95` table, exact to 3 dp).
T95_TABLE: dict[int, float] = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
    40: 2.021,
    50: 2.009,
    60: 2.000,
    80: 1.990,
    100: 1.984,
    120: 1.980,
}
Z95 = 1.959964
#: One (mean, sd, n) summary.
Stats = tuple[float, float, int]


def t95(df: int) -> float:
    """Two-sided 95% Student-t critical value for `df` degrees of freedom (as the figure scripts' `t95`).

    Off-table values round DOWN to the nearest tabulated df, so an interval is never narrower than the true one.
    """
    if df <= 0:
        return float("nan")
    below = [k for k in T95_TABLE if k <= df]
    return T95_TABLE[max(below)] if below else Z95


def mean_ci(values: Sequence[float]) -> tuple[float, float, float]:
    """`(mean, lo, hi)`: the 95% t interval on the mean (as the figure scripts' `mean_ci`); zero width at n < 2."""
    n = len(values)
    if n == 0:
        return (math.nan, math.nan, math.nan)
    m = statistics.fmean(values)
    if n < 2:
        return m, m, m
    half = t95(n - 1) * statistics.stdev(values) / math.sqrt(n)
    return m, m - half, m + half


def t_interval(mean: float, sd: float, n: int) -> tuple[float, float]:
    """The 95% t interval of a mean from its summary statistics (`mean_ci` of the same episodes)."""
    if n < 2:
        return (mean, mean)
    half = t95(n - 1) * sd / math.sqrt(n)
    return (mean - half, mean + half)


def pool(cells: Sequence[Stats]) -> Stats:
    """The exact `(mean, sample sd, n)` of the episodes behind `cells` (each a `(mean, sample sd, n)`)."""
    total = sum(n for _, _, n in cells)
    if total == 0:
        return (float("nan"), float("nan"), 0)
    mean = sum(m * n for m, _, n in cells) / total
    if total < 2:
        return (mean, 0.0, total)
    ss = sum((n - 1) * sd * sd + n * (m - mean) ** 2 for m, sd, n in cells)
    return (mean, math.sqrt(max(ss, 0.0) / (total - 1)), total)


def equal_weight_ci(cells: Sequence[Stats]) -> tuple[float, float, float]:
    """`(mean, lo, hi)`: equal-weight mean of the cell means, episodes weighted 1 / n_cell (`scenario_mean_ci`).

    `se = sqrt(sum_i w_i^2 sum_j (x_ij - m)^2 * N / (N - 1)) / K` with `w_i = 1 / n_i`, `K` cells and `N`
    episodes; `sum_j (x_ij - m)^2 = (n_i - 1) sd_i^2 + n_i (m_i - m)^2`.
    """
    live = [(m, sd, n) for m, sd, n in cells if n > 0]
    k = len(live)
    total = sum(n for _, _, n in live)
    if k == 0:
        return (math.nan, math.nan, math.nan)
    mean = sum(m for m, _, _ in live) / k
    if total < 2:
        return mean, mean, mean
    acc = sum(((n - 1) * sd * sd + n * (m - mean) ** 2) / (n * n) for m, sd, n in live)
    se = math.sqrt(acc * total / (total - 1)) / k
    half = t95(total - 1) * se
    return mean, mean - half, mean + half
