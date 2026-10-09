"""`expected/reference.json` holds the paper's API key numbers; check.py compares with it by default.

The anchors are the numbers the paper and its appendix print: the scenario-averaged formation means
(`fig:overview-bars`), the per-team-size cells of `fig:tc-welfare`, the team-lead mitigation cells (screened and raw,
and the arms' equal-weight aggregates), the participation and idling sentences, and the 4-user Jain index. Every API key number of the
paper is provider-error screened: rule T drops each episode, in every formation and arm, in which an agent had 4
consecutive failed target calls (266 of the 9,997 formation episodes, three Claude Opus 5 peer-to-peer team cells
entirely). The reference was built from the paper's frozen per-episode tables; `NUMBERS_SHA256` pins its cells and
pooled rows to that build (the frozen tables themselves are not part of the release).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from api_key import check as check_mod
from api_key import report
from api_key.paper_stats import equal_weight_ci
from api_key.scenarios import SCENARIOS
from api_key.tests.conftest import close

EXPECTED = Path(__file__).resolve().parents[1] / "expected"
REFERENCE: dict[str, Any] = json.loads((EXPECTED / "reference.json").read_text())
#: sha256 of the canonical JSON (sorted keys, no whitespace) of the `cells` and `pooled` lists as the builder
#: wrote them from the paper's frozen tables (the formation episodes before and after the screen, the limits-off
#: lead ladder and the two rule-T manifests, whose own sha256 are in `sources`).
NUMBERS_SHA256 = {
    "cells": "94c9b44419510192aeb8e93f3768ba640a16659a518589f01635f2e5b0f3505e",
    "pooled": "e4bf98c75bc2499bdde275248ed66b0719e41d6c6de0071289cf57c73bed5d80",
}
MODELS = (
    "claude-opus-5",
    "claude-sonnet-5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "qwen3.8-max",
)
FORMATIONS = ("solo", "coordinator", "team", "team_silent")
OPUS, SONNET = "claude-opus-5", "claude-sonnet-5"


def pooled(
    model: str, formation: str, seats: int | str = "all", mitigation: str | None = None
) -> dict[str, Any]:
    matches = [
        p
        for p in REFERENCE["pooled"]
        if p["model"] == model
        and p["formation"] == formation
        and p["seats"] == seats
        and p.get("mitigation") == mitigation
    ]
    assert len(matches) == 1, (model, formation, seats, mitigation)
    return matches[0]


def cells(
    model: str, formation: str, mitigation: str | None = None
) -> list[dict[str, Any]]:
    return [
        c
        for c in REFERENCE["cells"]
        if c["model"] == model
        and c["formation"] == formation
        and c.get("mitigation") == mitigation
    ]


def test_the_reference_covers_the_papers_matrix() -> None:
    assert REFERENCE["schema"] == "eval/api_key/reference/2"
    assert REFERENCE["instrument"] == "paper"
    formation_cells = [c for c in REFERENCE["cells"] if "mitigation" not in c]
    assert {(c["scenario"], c["formation"], c["model"]) for c in formation_cells} == {
        (s, f, m) for s in SCENARIOS for f in FORMATIONS for m in MODELS
    }
    short = {
        (c["model"], c["formation"], c["scenario"]): c["n_raw"]
        for c in formation_cells
        if c["n_raw"] != 20
    }
    # the run-details exceptions of record: Qwen3.8-max peer-to-peer team 18 on peq_duo_n16_409, 19 on peq_pyr_n8_154
    assert short == {
        ("qwen3.8-max", "team", "peq_duo_n16_409"): 18,
        ("qwen3.8-max", "team", "peq_pyr_n8_154"): 19,
    }
    # the provider-error screen (run details): episodes dropped per model and formation, no coordinator episode
    dropped: dict[tuple[str, str], int] = {}
    for c in formation_cells:
        assert c["n"] == c["n_raw"] - c["rule_t_dropped"]
        if c["rule_t_dropped"]:
            key = (c["model"], c["formation"])
            dropped[key] = dropped.get(key, 0) + c["rule_t_dropped"]
    assert dropped == {
        (OPUS, "team"): 101,
        (OPUS, "team_silent"): 16,
        (SONNET, "solo"): 3,
        (SONNET, "team"): 86,
        (SONNET, "team_silent"): 9,
        ("gpt-5.6-sol", "team"): 50,
        ("gpt-5.6-terra", "team"): 1,
    }
    lead_cells = [c for c in REFERENCE["cells"] if "mitigation" in c]
    assert {(c["scenario"], c["model"], c["mitigation"]) for c in lead_cells} == {
        (s, m, a)
        for s in SCENARIOS
        for m in (OPUS, SONNET)
        for a in ("lead_value", "lead_full_stack")
    }
    assert all(c["formation"] == "team" and c["n_raw"] == 20 for c in lead_cells)
    assert sum(c["n_raw"] for c in formation_cells) == 9997
    assert sum(c["n"] for c in formation_cells) == 9731
    # the sources are the files the paper's figure scripts pin
    assert REFERENCE["sources"]["nights_of_record.csv"]["sha256"].startswith("2de07bca")
    assert REFERENCE["sources"]["nights_of_record_screened.csv"]["sha256"].startswith(
        "398b9d15"
    )
    assert REFERENCE["sources"]["excluded_T.csv"]["sha256"].startswith("1bd9dafe")
    assert REFERENCE["sources"]["rule_t_exclusions.csv"]["sha256"].startswith(
        "031de307"
    )


def test_the_numbers_are_the_build_from_the_papers_tables() -> None:
    for key, digest in NUMBERS_SHA256.items():
        packed = json.dumps(REFERENCE[key], sort_keys=True, separators=(",", ":"))
        assert hashlib.sha256(packed.encode()).hexdigest() == digest, key


#: The scenario-averaged means (the equal-weight mean of the scenario means; the overview figure's estimator and,
#: for Claude, its labels `fig:overview-bars`: Opus 5 70 / 64 / 30 / 7, Sonnet 5 33 / 32 / 12 / 2), solo /
#: coordinator / peer-to-peer team / silent team.
HEADLINE = {
    OPUS: (0.7041, 0.6355, 0.2960, 0.0726),
    SONNET: (0.3254, 0.3240, 0.1164, 0.0223),
    "gpt-5.6-sol": (0.4909, 0.5855, 0.3054, 0.0485),
    "gpt-5.6-terra": (0.4714, 0.4769, 0.2258, 0.0406),
    "qwen3.8-max": (0.5303, 0.4540, 0.3019, 0.0817),
}
#: Episodes behind each pooled formation row after the screen, in FORMATIONS order.
HEADLINE_N = {
    OPUS: (500, 500, 399, 484),
    SONNET: (497, 500, 414, 491),
    "gpt-5.6-sol": (500, 500, 450, 500),
    "gpt-5.6-terra": (500, 500, 499, 500),
    "qwen3.8-max": (500, 500, 497, 500),
}


@pytest.mark.parametrize("model", MODELS)
def test_pooled_formation_means_are_the_papers(model: str) -> None:
    for formation, want, n in zip(
        FORMATIONS, HEADLINE[model], HEADLINE_N[model], strict=True
    ):
        row = pooled(model, formation)
        assert round(row["eqw_mean"], 4) == want, (model, formation, row["eqw_mean"])
        # the Claude Opus 5 peer-to-peer team keeps 22 scenarios: the screen empties stakes_130, peq_cls_n8_197
        # and peq_duo_n16_409 (basket matching ran before the screen, so its other formations keep all 25)
        scenarios = 22 if (model, formation) == (OPUS, "team") else 25
        assert row["n"] == n and row["n_scenarios"] == scenarios


def test_figure_2_cells_and_equal_weight_aggregate() -> None:
    """Figure 2's API key cells: the equal-weight mean over the scenarios, the t interval over the kept episodes."""
    want = {
        (OPUS, "solo"): (70.41, 68.36, 72.45),
        (OPUS, "coordinator"): (63.55, 61.27, 65.82),
        (OPUS, "team_silent"): (7.26, 6.65, 8.06),
        (OPUS, "team"): (29.60, 27.78, 30.90),
        (SONNET, "solo"): (32.54, 30.01, 35.10),
        (SONNET, "coordinator"): (32.40, 29.91, 34.89),
        (SONNET, "team_silent"): (2.23, 1.76, 2.73),
        (SONNET, "team"): (11.64, 9.75, 13.11),
    }
    for (model, formation), cell in want.items():
        row = pooled(model, formation)
        got = (row["eqw_mean"], row["ci_lo"], row["ci_hi"])
        assert tuple(round(100 * v, 2) for v in got) == cell, (model, formation)
        # the bar sits inside its whisker; it equals the episode mean only where no episode was dropped
        assert row["ci_lo"] <= row["eqw_mean"] <= row["ci_hi"]
        if row["rule_t_dropped"] == 0:
            assert close(row["eqw_mean"], row["mean"])


#: The team-size figure (`fig:tc-welfare`), 4 / 8 / 16 users, to 3 dp.
BY_SIZE = {
    OPUS: {
        "solo": (0.740, 0.699, 0.658),
        "coordinator": (0.639, 0.657, 0.605),
        "team_silent": (0.106, 0.028, 0.076),
        "team": (0.386, 0.193, 0.268),
    },
    SONNET: {
        "solo": (0.266, 0.341, 0.395),
        "coordinator": (0.274, 0.347, 0.370),
        "team_silent": (0.040, 0.006, 0.017),
        "team": (0.245, 0.055, 0.020),
    },
    "gpt-5.6-sol": {
        "solo": (0.435, 0.493, 0.568),
        "coordinator": (0.578, 0.575, 0.607),
        "team_silent": (0.087, 0.024, 0.022),
        "team": (0.515, 0.251, 0.059),
    },
    "gpt-5.6-terra": {
        "solo": (0.386, 0.549, 0.505),
        "coordinator": (0.427, 0.541, 0.476),
        "team_silent": (0.059, 0.039, 0.016),
        "team": (0.387, 0.188, 0.039),
    },
    "qwen3.8-max": {
        "solo": (0.517, 0.597, 0.473),
        "coordinator": (0.400, 0.492, 0.488),
        "team_silent": (0.095, 0.071, 0.075),
        "team": (0.434, 0.257, 0.164),
    },
}
#: The episode counts of the run-details table where the screen dropped episodes (4 / 8 / 16 users); every other
#: cell keeps 200 / 160 / 140 (Qwen3.8-max peer-to-peer team: 200 / 159 / 138, three reruns missing).
BY_SIZE_N = {
    (OPUS, "team_silent"): (199, 148, 137),
    (OPUS, "team"): (166, 126, 107),
    (SONNET, "solo"): (200, 159, 138),
    (SONNET, "team_silent"): (197, 156, 138),
    (SONNET, "team"): (153, 132, 129),
    ("gpt-5.6-sol", "team"): (180, 145, 125),
    ("gpt-5.6-terra", "team"): (199, 160, 140),
    ("qwen3.8-max", "team"): (200, 159, 138),
}


@pytest.mark.parametrize("model", MODELS)
def test_figure_4_cells_by_team_size(model: str) -> None:
    for formation, values in BY_SIZE[model].items():
        counts = BY_SIZE_N.get((model, formation), (200, 160, 140))
        for seats, want, n in zip((4, 8, 16), values, counts, strict=True):
            row = pooled(model, formation, seats)
            assert abs(row["mean"] - want) <= 5e-4 + 1e-9, (model, formation, seats)
            assert row["n"] == n
            # the Claude Opus 5 peer-to-peer team pools 9 / 7 / 6 scenarios, every other cell 10 / 8 / 7
            scenarios = {4: 10, 8: 8, 16: 7}[seats]
            assert row["n_scenarios"] == scenarios - (
                (model, formation) == (OPUS, "team")
            )


def test_team_lead_value_is_the_papers_mitigation_bar() -> None:
    """The paper's Mitigations paragraph and the team-size figure's `team + lead + value` bar (provider-error screened)."""
    want = {
        OPUS: ((0.7729, 198), (0.7568, 141), (0.5940, 130)),
        SONNET: ((0.4392, 79), (0.4738, 107), (0.3185, 87)),
    }
    coordinator = {OPUS: (0.639, 0.657, 0.605), SONNET: (0.274, 0.347, 0.370)}
    for model, rows in want.items():
        for seats, (mean, n), coord in zip(
            (4, 8, 16), rows, coordinator[model], strict=True
        ):
            row = pooled(model, "team", seats, "lead_value")
            assert round(row["mean"], 4) == mean and row["n"] == n
            assert abs(pooled(model, "coordinator", seats)["mean"] - coord) < 5e-4
            # every lead arm beats the leaderless team at every size (the appendix: by 0.13 to 0.57)
            assert row["mean"] > pooled(model, "team", seats)["mean"] + 0.13
    # the team-size figure's whiskers, to 3 dp
    assert (
        round(pooled(OPUS, "team", 4, "lead_value")["ci_lo"], 3),
        round(pooled(OPUS, "team", 4, "lead_value")["ci_hi"], 3),
    ) == (0.750, 0.796)
    assert (
        round(pooled(SONNET, "team", 16, "lead_value")["ci_lo"], 3),
        round(pooled(SONNET, "team", 16, "lead_value")["ci_hi"], 3),
    ) == (0.269, 0.368)
    # the 25-scenario equal-weight aggregate
    eqw = {OPUS: (71.61, 70.00, 73.22), SONNET: (42.50, 38.56, 46.43)}
    for model, (mean, lo, hi) in eqw.items():
        row = pooled(model, "team", "all", "lead_value")
        assert (
            round(100 * row["eqw_mean"], 2),
            round(100 * row["eqw_ci_lo"], 2),
            round(100 * row["eqw_ci_hi"], 2),
        ) == (mean, lo, hi)
        # and from the per-scenario cells
        got = equal_weight_ci(
            [(c["mean"], c["sd"], c["n"]) for c in cells(model, "team", "lead_value")]
        )
        assert round(100 * got[0], 2) == mean
    # per scenario: Claude Sonnet 5 on stakes_100 kept 13 of its 20 episodes
    by_scenario = {
        (c["model"], c["scenario"]): c
        for model in want
        for c in cells(model, "team", "lead_value")
    }
    assert (
        by_scenario[(OPUS, "stakes_100")]["n"],
        by_scenario[(SONNET, "stakes_100")]["n"],
    ) == (20, 13)
    assert round(by_scenario[(OPUS, "stakes_100")]["mean"], 4) == 0.8741
    assert round(by_scenario[(SONNET, "stakes_100")]["mean"], 4) == 0.3755
    # the screen: 258 lead + value episodes dropped (Opus 31, Sonnet 227)
    assert pooled(OPUS, "team", "all", "lead_value")["rule_t_dropped"] == 31
    assert pooled(SONNET, "team", "all", "lead_value")["rule_t_dropped"] == 227
    # unscreened
    raw = {OPUS: (0.773, 0.758, 0.591, 0.717), SONNET: (0.460, 0.483, 0.320, 0.428)}
    for model, values in raw.items():
        for seats, want_raw in zip((4, 8, 16, "all"), values, strict=True):
            assert (
                round(pooled(model, "team", seats, "lead_value")["mean_raw"], 3)
                == want_raw
            )


def test_full_stack_is_within_a_hundredth_of_the_value_arm() -> None:
    want = {
        OPUS: ((0.776, 199), (0.764, 149), (0.559, 134)),
        SONNET: ((0.443, 94), (0.507, 36), (0.363, 115)),
    }
    for model, rows in want.items():
        for seats, (mean, n) in zip((4, 8, 16), rows, strict=True):
            row = pooled(model, "team", seats, "lead_full_stack")
            assert round(row["mean"], 3) == mean and row["n"] == n
    # the paper's pooled score: the 25-scenario episode mean averaged over the two models
    score = {
        arm: (
            pooled(OPUS, "team", "all", arm)["mean"]
            + pooled(SONNET, "team", "all", arm)["mean"]
        )
        / 2
        for arm in ("lead_value", "lead_full_stack")
    }
    assert (round(score["lead_value"], 3), round(score["lead_full_stack"], 3)) == (
        0.566,
        0.563,
    )
    assert abs(score["lead_value"] - score["lead_full_stack"]) < 0.01


def test_cells_the_screen_empties_are_kept_and_skipped() -> None:
    """Every episode of four cells lost a turn to provider errors, and a check skips those cells.

    The cells: three Claude Opus 5 peer-to-peer team cells of the formation corpus and Sonnet 5 full stack on
    peq_cls_n8_197.
    """
    empty = {
        (c["scenario"], c["model"], c.get("mitigation")): c
        for c in REFERENCE["cells"]
        if c["n"] == 0
    }
    assert set(empty) == {
        ("stakes_130", OPUS, None),
        ("peq_cls_n8_197", OPUS, None),
        ("peq_duo_n16_409", OPUS, None),
        ("peq_cls_n8_197", SONNET, "lead_full_stack"),
    }
    for cell in empty.values():
        assert cell["formation"] == "team" and cell["mean"] is None
        assert cell["n_raw"] == 20 and cell["rule_t_dropped"] == 20
        assert not report.has_episodes(cell)
    keyed = report.reference_cells(REFERENCE, "lead_full_stack")
    assert ("peq_cls_n8_197", "team", SONNET) not in keyed
    assert len(keyed) == 49
    control = report.reference_cells(REFERENCE)
    assert ("stakes_130", "team", OPUS) not in control and len(control) == 497
    runs = [
        {
            "scenario": "peq_cls_n8_197",
            "formation": "team",
            "model": SONNET,
            "mitigation": "lead_full_stack",
            "welfare_mean": 0.5,
            "welfare_sd": 0.1,
            "clean": 3,
        },
        {
            "scenario": "stakes_130",
            "formation": "team",
            "model": OPUS,
            "mitigation": "none",
            "welfare_mean": 0.5,
            "welfare_sd": 0.1,
            "clean": 3,
        },
    ]
    for run in runs:
        assert [s for s, _ in check_mod.check([run], REFERENCE)] == ["SKIP"]


def test_behaviour_numbers_the_paper_prints() -> None:
    # participation, 4 -> 16 users (the paper's main text): Sonnet 66% -> 10%, GPT-5.6-sol 82% -> 25%
    for model, (four, sixteen) in {SONNET: (66, 10), "gpt-5.6-sol": (82, 25)}.items():
        assert round(100 * pooled(model, "team", 4)["participation_mean"]) == four
        assert round(100 * pooled(model, "team", 16)["participation_mean"]) == sixteen
    # 135 of 140 GPT-5.6-terra 16-user team episodes idle through the final third
    terra = pooled("gpt-5.6-terra", "team", 16)
    assert (terra["idle_final_third_n"], terra["n"]) == (135, 140)
    assert terra["median_last_action"] == 301.0
    # Opus team episodes idle through the final third: 60-67% across sizes
    shares = [pooled(OPUS, "team", s)["idle_final_third_share"] for s in (4, 8, 16)]
    assert [round(100 * s, 1) for s in shares] == [65.7, 66.7, 59.8]
    # the 4-user Jain index (Figure 5, right): Opus team .58 [.558, .610], coordinator .59 [.560, .613]
    team, coord = pooled(OPUS, "team", 4), pooled(OPUS, "coordinator", 4)
    assert (round(team["jain_mean"], 3), team["jain_n"]) == (0.584, 162)
    assert (round(team["jain_ci_lo"], 3), round(team["jain_ci_hi"], 3)) == (
        0.558,
        0.610,
    )
    assert (round(coord["jain_mean"], 3), coord["jain_n"]) == (0.587, 188)
    assert (round(coord["jain_ci_lo"], 3), round(coord["jain_ci_hi"], 3)) == (
        0.560,
        0.613,
    )
    # silent teams waste 90-100% of their tokens (minimum 0.896, Opus 4 users)
    silent = [
        pooled(m, "team_silent", s)["wasted_share_mean"]
        for m in MODELS
        for s in (4, 8, 16)
    ]
    assert round(min(silent), 3) == 0.896 and max(silent) <= 1.0


@pytest.mark.parametrize(
    ("model", "formation", "mitigation"),
    [
        (OPUS, "solo", None),
        ("qwen3.8-max", "team", None),
        (SONNET, "team_silent", None),
        (OPUS, "team", "lead_value"),
        (SONNET, "team", "lead_full_stack"),
    ],
)
def test_pooled_rows_are_the_pooled_cells(
    model: str, formation: str, mitigation: str | None
) -> None:
    """The cells and the pooled rows are one dataset: pooling the cells (report.pooled_stats) gives the rows."""
    for seats in ("all", 4, 8, 16):
        subset = [
            c
            for c in cells(model, formation, mitigation)
            if (seats == "all" or SCENARIOS[c["scenario"]].n_seats == seats)
            and report.has_episodes(c)
        ]
        mean, sd, n = report.pooled_stats(subset, "mean", "sd", "n")
        row = pooled(model, formation, seats, mitigation)
        assert n == row["n"]
        assert close(mean, row["mean"], 2e-6)
        assert close(sd, row["sd"], 2e-5)
        lo, hi = report.interval(mean, sd, n)
        assert close((lo, hi), (row["ci_lo"], row["ci_hi"]), 3e-5)


def run_cell(
    scenario: str, formation: str, stats: tuple[float, float, int]
) -> dict[str, Any]:
    """A Claude Opus 5 run cell with `(mean, sd, n)`, as `report.cell_rows` shapes it."""
    mean, sd, n = stats
    return {
        "scenario": scenario,
        "formation": formation,
        "model": OPUS,
        "mitigation": "none",
        "welfare_mean": mean,
        "welfare_sd": sd,
        "clean": n,
    }


def test_check_verdicts_against_the_paper() -> None:
    """A run cell AT the paper's mean passes; far from it, one episode is unresolved and two are a MISS.

    At n = 1 the paper's t interval is zero width: a smoke run (`--formation solo --fake-model`, one
    epoch) scores 0 against the paper's solo cell and must not read as "intervals disjoint".
    """
    (faithful,) = [c for c in cells(OPUS, "team") if c["scenario"] == "peq_skl_n16_350"]
    at_mean = run_cell(
        "peq_skl_n16_350", "team", (faithful["mean"], faithful["sd"], 20)
    )
    assert [s for s, _ in check_mod.check([at_mean], REFERENCE)] == ["PASS", "PASS"]
    (ref,) = [c for c in cells(OPUS, "solo") if c["scenario"] == "stakes_100"]
    ref_stats = (float(ref["mean"]), float(ref["sd"]), int(ref["n"]))
    assert ref_stats[0] > 0.5
    for run, verdict in [
        ((0.0, 0.0, 1), "WARN"),
        ((ref_stats[0], 0.0, 1), "PASS"),
        ((0.0, 0.0, 2), "MISS"),
        ((0.0, 0.01, 5), "MISS"),
    ]:
        assert report.band_verdict(run, ref_stats) == verdict, run
    verdicts = check_mod.check(
        [run_cell("stakes_100", "solo", (0.0, 0.0, 1))], REFERENCE
    )
    assert [s for s, _ in verdicts] == ["WARN", "WARN"]  # the cell and its pooled row
    assert all("(n=1)" in line and "unresolved" in line for _, line in verdicts)
    # the SCORE rows' verdict is the same function, so it agrees with check.py
    row = report._score(  # pyright: ignore[reportPrivateUsage]
        "stakes_100",
        OPUS,
        "solo",
        (0.0, 0.0, 1),
        ((0.0, 0.0, 1), ref_stats, "corpus_of_record"),
        None,
    )
    assert (row["paper_verdict"], row["ci_method"]) == ("WARN", "t95 (n<2, degenerate)")
