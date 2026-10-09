"""The statistics every eval's `check.py` shares: two 95% intervals and the PASS / WARN / MISS band.

Kept dependency-free so a check can run on a saved readout without importing any world.
"""

from __future__ import annotations

import math
import statistics

Z95 = 1.959964


def wilson(successes: int, trials: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion; `(nan, nan)` when `trials == 0`."""
    if trials <= 0:
        return (math.nan, math.nan)
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = (p + z * z / (2.0 * trials)) / denominator
    half = (
        z
        * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
        / denominator
    )
    return (max(0.0, centre - half), min(1.0, centre + half))


def mean_interval(
    mean: float, sd: float, n: int, z: float = Z95
) -> tuple[float, float]:
    """Normal-approximation interval for a mean from its summary statistics; degenerate at `n < 2`."""
    if n < 2:
        return (mean, mean)
    half = z * sd / math.sqrt(n)
    return (mean - half, mean + half)


def describe(values: list[float]) -> tuple[float, float, int]:
    """`(mean, sample sd, n)` of a non-empty list; sd is 0 for a single value."""
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if n > 1 else 0.0
    return (mean, sd, n)


def band(
    point: float, interval: tuple[float, float], reference: tuple[float, float]
) -> str:
    """The reproduction contract: PASS inside the reference band, MISS when disjoint, else WARN.

    WARN is the expected verdict at small n (the run's own interval still overlaps the reference's):
    read it as "not resolved", never as "reproduced".
    """
    lo, hi = interval
    ref_lo, ref_hi = reference
    if ref_lo - 1e-12 <= point <= ref_hi + 1e-12:
        return "PASS"
    if hi < ref_lo or lo > ref_hi:
        return "MISS"
    return "WARN"
