"""`_stats.band`: the reproduction verdict every environment's check.py prints."""

from __future__ import annotations

import pytest
from _stats import band


@pytest.mark.parametrize(
    ("point", "interval", "verdict"),
    [
        (0.5, (0.45, 0.55), "PASS"),  # the point inside the reference band
        (0.65, (0.55, 0.75), "WARN"),  # outside it, the intervals overlap
        (0.8, (0.7, 0.9), "MISS"),  # disjoint
    ],
)
def test_only_a_point_inside_the_reference_passes(
    point: float, interval: tuple[float, float], verdict: str
) -> None:
    assert band(point, interval, (0.4, 0.6)) == verdict
