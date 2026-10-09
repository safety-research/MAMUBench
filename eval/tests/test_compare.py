"""`_compare`: the comparison statistics every readout's SCORE and CONTRAST rows share."""

from __future__ import annotations

import math

import pytest
from _compare import (
    CONTRAST_COLUMNS,
    SCORE_COLUMNS,
    baseline_columns,
    bootstrap_diff,
    contrast_rows,
    markdown_table,
    mean_stat,
    newcombe_diff,
    rate_stat,
    score_row,
    stratified_bootstrap_diff,
    t_cdf,
    t_quantile,
    welch_diff,
)


@pytest.mark.parametrize(
    ("df", "expected"),
    [(1, 12.7062), (9, 2.2622), (100, 1.9840)],
)
def test_t_quantile_matches_tables(df: int, expected: float) -> None:
    assert abs(t_quantile(0.975, df) - expected) < 5e-4
    assert abs(t_quantile(0.025, df) + expected) < 5e-4


def test_t_cdf_is_symmetric_and_tends_to_normal() -> None:
    assert abs(t_cdf(0.0, 5) - 0.5) < 1e-12
    assert abs(t_cdf(1.5, 5) + t_cdf(-1.5, 5) - 1.0) < 1e-12
    assert abs(t_quantile(0.975, 1e7) - 1.959964) < 1e-6


def test_welch_diff_reduces_to_pooled_case() -> None:
    d = welch_diff(0.6, 0.2, 20, 0.4, 0.2, 20)
    assert abs(d.point - 0.2) < 1e-12
    se = math.sqrt(0.04 / 20 + 0.04 / 20)
    assert abs((d.hi - d.lo) / 2 - t_quantile(0.975, 38) * se) < 1e-9
    assert d.method == "welch"
    tiny = welch_diff(0.5, 0.0, 1, 0.4, 0.1, 5)
    assert math.isnan(tiny.lo) and abs(tiny.point - 0.1) < 1e-12


def test_newcombe_matches_the_published_example() -> None:
    # Newcombe (1998), Table II, method 10: 56/70 vs 48/80 -> 0.2000 [0.0524, 0.3339].
    d = newcombe_diff(56, 70, 48, 80)
    assert abs(d.point - 0.2) < 1e-12
    assert abs(d.lo - 0.0524) < 1e-3
    assert abs(d.hi - 0.3339) < 1e-3
    empty = newcombe_diff(0, 0, 3, 5)
    assert math.isnan(empty.point)


def test_bootstrap_is_seeded_and_brackets_the_point() -> None:
    a = [0.9, 0.8, 0.85, 0.7, 0.95]
    b = [0.3, 0.4, 0.2, 0.35, 0.5]
    first = bootstrap_diff(a, b, mean_stat, draws=500)
    second = bootstrap_diff(a, b, mean_stat, draws=500)
    assert first == second
    assert first.lo <= first.point <= first.hi
    assert abs(first.point - (mean_stat(a) - mean_stat(b))) < 1e-12
    constant = bootstrap_diff([1.0, 1.0], [0.0, 0.0], mean_stat, draws=50)
    assert constant.lo == constant.hi == 1.0


def test_rate_statistic_pools_contests_and_strata_mean_equal_weights() -> None:
    strata = {
        "board_a": ([(6, 6), (5, 6)], [(2, 6), (3, 6)]),
        "board_b": ([(20, 30)], [(10, 30)]),
    }
    units = stratified_bootstrap_diff(strata, rate_stat, combine="units", draws=200)
    strata_mean = stratified_bootstrap_diff(
        strata, rate_stat, combine="strata", draws=200
    )
    assert abs(units.point - ((31 / 42) - (15 / 42))) < 1e-12
    expected = (((11 / 12) - (5 / 12)) + ((20 / 30) - (10 / 30))) / 2
    assert abs(strata_mean.point - expected) < 1e-12
    assert units.n_a == 3 and units.n_b == 3
    empty = stratified_bootstrap_diff({"x": ([], [(1, 2)])}, rate_stat, draws=10)
    assert math.isnan(empty.point)


def test_contrast_rows_cover_every_available_pair() -> None:
    units = {
        ("s1", "m", "coordinator"): [0.8, 0.9, 0.7],
        ("s1", "m", "team"): [0.4, 0.5, 0.3],
        ("s2", "m", "coordinator"): [0.6, 0.7],
        ("s2", "m", "team"): [0.2, 0.1],
        ("s2", "m", "team_silent"): [0.0, 0.1],
    }

    def reference(scenario: str | None, model: str, a: str, b: str):  # noqa: ANN202
        return welch_diff(0.7, 0.1, 20, 0.3, 0.1, 20) if scenario == "s1" else None

    rows, pooled = contrast_rows(
        "api_key",
        units,
        mean_stat,
        reference=reference,
        reference_instrument="instrument_a",
        draws=100,
    )
    labels = {(r["scenario"], r["contrast"]) for r in rows}
    assert labels == {
        ("s1", "coordinator-team"),
        ("s2", "coordinator-team"),
        ("s2", "coordinator-team_silent"),
        ("s2", "team-team_silent"),
    }
    s1 = next(r for r in rows if r["scenario"] == "s1")
    assert s1["ref_diff_pp"] == 40.0 and s1["ref_instrument"] == "instrument_a"
    assert all(set(r) == set(CONTRAST_COLUMNS) for r in rows + pooled)
    pooled_ct = next(r for r in pooled if r["contrast"] == "coordinator-team")
    assert pooled_ct["scenario"] == "POOLED (2 scenarios)"
    assert pooled_ct["n_a"] == 5 and pooled_ct["n_b"] == 5


def test_score_row_and_baseline_columns() -> None:
    columns = baseline_columns(
        welch_diff(0.5, 0.1, 5, 0.4, 0.1, 20),
        {"score": 0.4, "n": 20, "instrument": "instrument_a"},
        prefix="opus5",
    )
    assert columns["opus5_score"] == 0.4 and columns["opus5_delta_pp"] == 10.0
    assert columns["opus5_delta_method"] == "welch"
    assert baseline_columns(None, None, prefix="paper")["paper_score"] is None
    row = score_row("clinic", scenario="x", n=3, **columns)
    assert set(row) == set(SCORE_COLUMNS) and row["env"] == "clinic"
    with pytest.raises(KeyError):
        score_row("clinic", bogus=1)
    text = markdown_table([row], ("env", "scenario", "opus5_delta_pp"))
    assert text.splitlines()[2] == "| clinic | x | 10.00 |"
