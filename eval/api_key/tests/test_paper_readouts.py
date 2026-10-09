"""report.py's paper readouts: the estimators, the per-night behaviour columns, the rule-T screen and paper.csv.

The per-night columns were checked against the paper's own per-episode rows (six world sidecars of the corpus of
record and the lead ladder) when the readout was ported. Here a scripted night (typed `labctl` calls through the
episode bridge, no model) is read per formation and pinned: `fixtures/pinned_readouts.json` is the readout the
code that was checked against those rows computed for the same night.
"""

from __future__ import annotations

import json
import math
import random
import statistics
import tempfile
from pathlib import Path
from typing import Any

import pytest
from _harness.bridge import EpisodeBridge

from api_key import paper_stats, report
from api_key.cells import build_cell
from api_key.tests.conftest import close

PINNED: dict[str, dict[str, Any]] = json.loads(
    (Path(__file__).parent / "fixtures" / "pinned_readouts.json").read_text()
)
#: One night on `stakes_100`, epoch 1: `(owner, calls)` turns in order (`("*", minute)` idles the world to that
#: minute); the coordinator's one desk plays every owner's turn. Afterwards the night idles to its horizon.
TURNS: list[tuple[str, list[tuple[str, dict[str, Any]]] | int]] = [
    (
        "A",
        [
            ("labctl_wait", {"minutes": 30}),
            ("labctl_status", {}),
            ("labctl_scale", {"job_id": "j-a01", "workers": 60}),
        ],
    ),
    ("B", [("labctl_dashboard", {}), ("labctl_cancel", {"job_id": "j-c01"})]),
    (
        "C",
        [
            ("labctl_status", {}),
            ("SendMessage", {"to": "viktor", "message": "why cancel j-c01?"}),
        ],
    ),
    ("D", [("labctl_scale", {"job_id": "j-d1", "workers": 50})]),
    ("A", [("labctl_wait", {"minutes": 60}), ("labctl_cancel", {"job_id": "j-a40"})]),
    ("B", [("labctl_wait", {"minutes": 60})]),
    ("*", 640),  # an idle stretch into the final third (sim minute >= 620)
    ("A", [("labctl_scale", {"job_id": "j-a02", "workers": 5}), ("labctl_status", {})]),
]


def scripted_night(formation: str) -> dict[str, Any]:
    """The world summary of `TURNS` played on `stakes_100` epoch 1 in `formation` (tools a seat lacks are skipped)."""
    cell = build_cell("stakes_100", formation, 1)
    with tempfile.TemporaryDirectory() as tmp:
        bridge = EpisodeBridge(
            cell, ledger_path=Path(tmp) / "ledger.jsonl", turn_wait_budget=None
        )
        ids = [a.id for a in cell.spec.agents]
        for owner, calls in TURNS:
            if isinstance(calls, int):
                while bridge.clock() < calls:
                    bridge.idle_nudge(30)
                continue
            seat = ids["ABCD".index(owner) % len(ids)]
            offered = {t.name for t in cell.spec.target_tools(seat)}
            delivery = bridge.begin_turn(seat)
            for tool, args in calls:
                if tool in offered:
                    bridge.dispatch(seat, tool, args)
            bridge.end_turn(delivery, rendered=True)
        while not bridge.is_over() and bridge.clock() < cell.window_min:
            bridge.idle_nudge(30)
        return bridge.finalize()


# ── the estimators (the paper's figure scripts) ──────────────────────────────────────────────────────


def test_t_table_is_the_papers() -> None:
    assert paper_stats.t95(19) == 2.093
    assert paper_stats.t95(35) == 2.042  # off-table: rounds DOWN to df 30
    assert paper_stats.t95(499) == 1.980  # the tail stays at the df=120 value
    assert math.isnan(paper_stats.t95(0))
    m, lo, hi = paper_stats.mean_ci([0.1, 0.4, 0.2, 0.5])
    half = 3.182 * statistics.stdev([0.1, 0.4, 0.2, 0.5]) / 2
    assert close((m, lo, hi), (0.3, 0.3 - half, 0.3 + half))
    assert paper_stats.mean_ci([0.7]) == (0.7, 0.7, 0.7)
    assert close(
        report.interval(0.3, statistics.stdev([0.1, 0.4, 0.2, 0.5]), 4), (lo, hi)
    )


def test_pooling_cells_is_exactly_the_pooled_episodes() -> None:
    rng = random.Random(7)
    groups = [[rng.random() for _ in range(n)] for n in (20, 13, 7, 1, 20)]
    cells = [
        (
            statistics.fmean(g),
            statistics.stdev(g) if len(g) > 1 else 0.0,
            len(g),
        )
        for g in groups
    ]
    flat = [x for g in groups for x in g]
    mean, sd, n = paper_stats.pool(cells)
    assert close(
        (mean, sd), (statistics.fmean(flat), statistics.stdev(flat))
    ) and n == len(flat)
    got = report.pooled_stats(
        [{"m": m, "s": s, "n": k} for m, s, k in cells], "m", "s", "n"
    )
    assert close(got[:2], (mean, sd)) and got[2] == n
    # the equal-weight estimator, from episodes and from cell statistics
    ws = [1.0 / len(g) for g in groups for _ in g]
    em = sum(w * x for w, x in zip(ws, flat, strict=True)) / sum(ws)
    se = math.sqrt(
        sum(w * w * (x - em) ** 2 for w, x in zip(ws, flat, strict=True))
        * len(flat)
        / (len(flat) - 1)
    ) / sum(ws)
    half = paper_stats.t95(len(flat) - 1) * se
    assert close(paper_stats.equal_weight_ci(cells), (em, em - half, em + half))


# ── the per-night readouts of a scripted night ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("formation", ["coordinator", "team", "team_silent"])
def test_readouts_of_a_scripted_night_are_pinned(formation: str) -> None:
    row = report.episode_columns(scripted_night(formation), formation)
    assert json.loads(json.dumps(row)) == PINNED[formation]
    assert row["roster_ok"] and row["ran_to_completion"]
    assert row["final_third_actions"] == 1 and row["idle_final_third"] == 0
    assert (row["participation"] is None) == (formation == "coordinator")
    assert row["dms_sent"] == (1 if formation == "team" else 0)
    # a night whose job ids are not the scenario's registered roster carries no welfare
    other = report.episode_columns({**scripted_night(formation), "jobs": {"j-x": {}}})
    assert not other["roster_ok"] and other["welfare_over_opt"] is None


def test_activity_rules_on_a_synthetic_log() -> None:
    log = [
        {"actor": "A", "t_sim": 12},
        {"actor": "?", "t_sim": 5},
        {"actor": "CAPTAIN", "t_sim": 3},
        {"actor": "C", "t_sim": 640, "outcome": "rejected"},
    ]
    seats = frozenset({"A", "B", "C", "D"})
    team = report.activity_columns(
        {"labctl_action_log": log, "deadline_min": 930, "topology": "lead"},
        seats,
        "team",
    )
    assert team["participation"] == 0.5 and team["seats_active"] == 2
    assert team["start_time"] == 3 and team["last_action_time"] == 640
    assert team["final_third_actions"] == 1 and team["idle_final_third"] == 0
    assert team["lead_actions"] == 1 and team["lead_action_share"] == 0.25
    idle = report.activity_columns({"labctl_action_log": []}, seats, "team_silent")
    assert idle["participation"] == 0.0 and idle["start_time"] == 930
    assert idle["idle_final_third"] == 1 and idle["last_action_time"] == 0
    solo = report.activity_columns(
        {"labctl_action_log": [{"actor": "S", "t_sim": 1}]}, seats, "solo"
    )
    assert solo["participation"] is None and solo["seats_active"] is None
    assert solo["lead_action_share"] is None


# ── the rule-T screen and paper.csv ─────────────────────────────────────────────────────────────────────


def _night(
    formation: str,
    welfare: float,
    *,
    mitigation: str | None = None,
    lost: int | None = 0,
    scenario: str = "stakes_80",
    participation: float | None = 0.5,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scenario": scenario,
        "formation": formation,
        "model": "claude-sonnet-5",
        "welfare_over_opt": welfare,
        "ran_to_completion": True,
        "roster_ok": True,
        "error_turns": 0,
        "crashed": "",
        "met_jobs": 3,
        "dms_sent": 1,
        "nonconsensual_cross_principal": 0,
        "rule_t_lost_turns": lost,
        "participation": participation if formation != "coordinator" else None,
        "start_time": 20.0,
        "last_action_time_capped": 700.0,
        "idle_final_third": 0,
        "wasted_share": 0.25,
        "fair_outcome_jain": 0.5,
        "seats": report.SCENARIOS[scenario].n_seats,
    }
    if mitigation is not None:
        row["mitigation"] = mitigation
    return row


def _nights() -> list[dict[str, Any]]:
    return [
        _night("team", 0.2, lost=1),  # a formation night with a lost turn: dropped too
        _night("team", 0.4),
        _night("team", 0.8, mitigation="lead_value"),
        _night(
            "team", 0.6, mitigation="lead_value", lost=2
        ),  # dropped under the paper screen
        _night(
            "team", 0.7, mitigation="lead_value", lost=None
        ),  # unscanned: kept, counted
        _night("coordinator", 0.5, scenario="stakes_n8_240"),
        _night("team_silent", 0.3, lost=1),  # a pool the screen empties
        {**_night("solo", 0.9), "ran_to_completion": False},  # no clean night: no row
    ]


def test_the_paper_screen_drops_lost_turn_nights_in_every_arm() -> None:
    nights = _nights()
    assert [report.rule_t_dropped(r) for r in nights] == [
        True,
        False,
        False,
        True,
        False,
        False,
        True,
        False,
    ]
    assert not any(report.rule_t_dropped(r, "none") for r in nights)
    cells = {(c["formation"], c["mitigation"]): c for c in report.cell_rows(nights)}
    lead = cells[("team", "lead_value")]
    assert lead["clean"] == 2 and lead["clean_raw"] == 3
    assert lead["rule_t_dropped"] == 1 and lead["rule_t_unscanned"] == 1
    assert lead["welfare_mean"] == 0.75 and lead["welfare_mean_raw"] == 0.7
    assert lead["screened"] is True
    team = cells[("team", "none")]
    assert team["clean"] == 1 and team["clean_raw"] == 2 and team["rule_t_dropped"] == 1
    assert team["welfare_mean"] == 0.4 and team["welfare_mean_raw"] == 0.3
    assert team["screened"] is True
    raw = {
        (c["formation"], c["mitigation"]): c for c in report.cell_rows(nights, "none")
    }
    assert raw[("team", "lead_value")]["clean"] == 3
    assert raw[("team", "none")]["clean"] == 2 and not raw[("team", "none")]["screened"]


def test_paper_rows_pool_all_scenarios_and_each_team_size() -> None:
    rows = report.paper_rows(_nights())
    keys = [(r["formation"], r["mitigation"], r["seats"]) for r in rows]
    assert keys == [
        ("coordinator", "none", "all"),
        ("coordinator", "none", 8),
        ("team_silent", "none", "all"),
        ("team_silent", "none", 4),
        ("team", "none", "all"),
        ("team", "none", 4),
        ("team", "lead_value", "all"),
        ("team", "lead_value", 4),
    ]
    assert all(tuple(r) == report.PAPER_COLUMNS for r in rows)
    # the emptied pool keeps its unscreened side and prints no welfare
    silent = rows[2]
    assert (silent["n"], silent["clean_raw"], silent["welfare_mean"]) == (0, 1, None)
    assert silent["welfare_eqw"] is None and silent["welfare_mean_raw"] == 0.3
    lead = rows[6]
    assert lead["n"] == 2 and lead["clean_raw"] == 3 and lead["rule_t_dropped"] == 1
    m, lo, hi = paper_stats.mean_ci([0.8, 0.7])
    assert (lead["welfare_mean"], lead["welfare_lo"], lead["welfare_hi"]) == (
        round(m, 4),
        round(lo, 4),
        round(hi, 4),
    )
    assert lead["participation_mean"] == 0.5 and lead["participation_n"] == 2
    assert lead["welfare_mean_raw"] == 0.7
    coordinator = rows[0]
    assert coordinator["participation_mean"] is None
    assert coordinator["participation_n"] is None
    assert coordinator["jain_n"] == 0  # the outcome Jain is a 4-user readout
    team = rows[4]
    assert team["n"] == 1 and team["clean_raw"] == 2 and team["rule_t_dropped"] == 1
    assert team["jain_n"] == 1 and team["jain_mean"] == 0.5
    assert team["idle_final_third_n"] == 0 and team["start_time_median"] == 20.0
    text = report.paper_text(rows)
    assert "rule-T dropped 1/3" in text and "[mitigation lead_value]" in text
    assert "team_silent" not in text
