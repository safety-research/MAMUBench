"""`expected/reference.json` holds the paper's clinic numbers, built the paper's way from the frozen episodes.

- The committed reference is exactly what `expected/build_reference.py` builds from
  `expected/episodes_of_record.csv.gz` (so the statistic in `clinic.metric` produced it).
- Every pooled row and every per-scenario cell equals the paper's own tables digit for digit, intervals included:
  `metrics_board_avg_joint.csv` and `clinic_by_scenario_cells.csv` (coordinator and team, five models),
  `silent_cells.csv` (silent team), `all24_cells.csv` and `clinic_mitigations_scenarios_cells.csv` (s1-s3 and
  their episode-1-10 controls). `fixtures/pinned_tables.json` holds, per table, the keys of its rows and the
  sha256 of their values (six decimals) as the paper's table prints them; the same projection of the reference
  must hash the same.
- The main text's numbers are asserted as printed.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

from clinic import metric, record
from clinic.reference import REFERENCE_PATH, PaperReference, is_paper

PINNED: dict[str, Any] = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "pinned_tables.json").read_text()
)
BUILD = Path(__file__).resolve().parents[1] / "expected" / "build_reference.py"
PAPER = PaperReference.load()
OPUS, SONNET = "claude-opus-5", "claude-sonnet-5"


def _pool(*key: str) -> dict[str, Any]:
    row = PAPER.pools.get(key)  # type: ignore[arg-type]
    assert row is not None, key
    return row


def test_reference_is_what_the_build_writes() -> None:
    spec = importlib.util.spec_from_file_location("clinic_build_reference", BUILD)
    assert spec is not None and spec.loader is not None
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    reference = REFERENCE_PATH.read_text()
    assert is_paper(json.loads(reference)) and PAPER.document["schema"] == build.SCHEMA
    assert build.render(build.build(record.load())) == reference


def test_episodes_of_record_hold_the_papers_sets() -> None:
    rows = record.load()
    assert Counter(r.set for r in rows) == {
        "corpus_of_record": 4388,
        "silent_e1_5": 600,
        "mitigations_e1_10": 1440,
    }
    assert len({(r.set, *r.key) for r in rows}) == len(rows)
    corpus = record.select(rows, set_name="corpus_of_record")
    assert (
        sum(r.n_contests for r in corpus) == 75765
    )  # joint_common_of_record.csv.gz, row for row
    by_cell = Counter((r.model, r.formation, r.instrument) for r in corpus)
    # the coordinator plays hero, the team standard
    assert by_cell[(OPUS, "coordinator", "hero")] == 480
    assert by_cell[("qwen3.8-max", "coordinator", "hero")] == 316
    for model, n in {
        OPUS: 480,
        SONNET: 480,
        "gpt-5.6-sol": 480,
        "gpt-5.6-terra": 480,
        "qwen3.8-max": 232,
    }.items():
        assert by_cell[(model, "team", "standard")] == n, model
    assert {r.instrument for r in corpus} == {"hero", "standard"}
    assert sum(r.plan_extra for r in corpus) == 3
    silent = record.select(rows, set_name="silent_e1_5")
    assert {r.instrument for r in silent} == {"standard"}
    assert {r.epoch for r in silent} == set(range(1, 6))
    assert (
        sum(r.source == "all24_e5_fix4" for r in silent) == 60
    )  # GPT-5.6-terra scattered, re-flown
    arms = record.select(rows, set_name="mitigations_e1_10")
    assert Counter((r.model, r.mitigation) for r in arms) == {
        (m, a): 240 for m in (OPUS, SONNET) for a in ("s1", "s2", "s3")
    }
    assert {r.epoch for r in arms} == set(range(1, 11))
    assert {r.instrument for r in arms} == {"standard"}


#: `table -> (what a key names, the columns hashed, rows)`: `pool` keys are (set, model, formation, arm,
#: condition), `cell` keys (set, scenario, formation, model, arm), `tagged` keys either, led by which.
TABLES: dict[str, tuple[str, tuple[str, ...], int]] = {
    "corpus_pools": (
        "pool",
        (
            "joint_pct",
            "lo",
            "hi",
            "met_pct",
            "met_pooled_pct",
            "episodes",
            "n",
            "met",
            "joint",
        ),
        30,
    ),
    "corpus_cells": ("cell", ("joint_pct", "lo", "hi", "episodes", "n", "joint"), 240),
    "silent": ("tagged", ("joint_pct", "lo", "hi", "episodes"), 5 * 27),
    "mitigation_pools": (
        "pool",
        ("joint_pct", "lo", "hi", "met_pct", "episodes", "n", "joint"),
        2 * 5 * 3,
    ),
    "mitigation_cells": (
        "cell",
        ("joint_pct", "lo", "hi", "met_pct", "episodes", "joint"),
        2 * 5 * 24,
    ),
}


def test_every_frozen_row_equals_the_papers_tables() -> None:
    for table, (kind, columns, n) in TABLES.items():
        pin = PINNED[table]
        assert len(pin["keys"]) == n, table
        rows: list[list[Any]] = []
        for key in pin["keys"]:
            which, rest = (key[0], key[1:]) if kind == "tagged" else (kind, key)
            ours = _pool(*rest) if which == "pool" else PAPER.cell(*rest)
            assert ours is not None, key
            rows.append([key, [f"{float(ours[c]):.6f}" for c in columns]])
        packed = json.dumps(
            rows, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        assert hashlib.sha256(packed.encode()).hexdigest() == pin["sha256"], table
    for model in metric.PAPER_MODELS:
        for formation, set_name in (
            ("coordinator", "corpus_of_record"),
            ("team", "corpus_of_record"),
            ("team_silent", "silent_e1_5"),
        ):
            for condition in metric.CONDITIONS:
                row = _pool(set_name, model, formation, "none", condition)
                assert row["n_scenarios"] == (24 if condition == "both" else 12)
    assert {k[4] for k in PAPER.cells} == {"none", "s1", "s2", "s3"}
    assert PAPER.arms() == ["none", "s1", "s2", "s3"]
    assert len(PAPER.cells) == 240 + 120 + 144 + 96


def test_the_main_texts_numbers_as_printed() -> None:
    corpus, arms = "corpus_of_record", "mitigations_e1_10"
    for key, printed in {
        # sec:clinic (assembled / scattered): team vs coordinator
        (corpus, OPUS, "team", "none", "assembled"): 71.1,
        (corpus, OPUS, "coordinator", "none", "assembled"): 83.3,
        (corpus, OPUS, "team", "none", "scattered"): 70.2,
        (corpus, OPUS, "coordinator", "none", "scattered"): 84.6,
        (corpus, SONNET, "team", "none", "assembled"): 85.2,
        (corpus, SONNET, "coordinator", "none", "assembled"): 88.7,
        (corpus, SONNET, "team", "none", "scattered"): 44.8,
        (corpus, SONNET, "coordinator", "none", "scattered"): 59.6,
        # Mitigations: s3 on all 24 scenarios vs the coordinator and the control, episodes 1-10
        (arms, OPUS, "team", "s3", "both"): 95.3,
        (arms, OPUS, "coordinator", "none", "both"): 84.3,
        (arms, SONNET, "team", "s3", "both"): 91.8,
        (arms, SONNET, "coordinator", "none", "both"): 74.2,
        (arms, OPUS, "team", "none", "both"): 70.5,
        (arms, SONNET, "team", "none", "both"): 65.3,
        # the Qwen3.8-max low-reasoning coordinator (appendix run details)
        (corpus, "qwen3.8-max", "coordinator", "none", "assembled"): 92.1,
        (corpus, "qwen3.8-max", "coordinator", "none", "scattered"): 76.3,
    }.items():
        assert round(float(_pool(*key)["joint_pct"]), 1) == printed, key
    opus, sonnet = (_pool(arms, m, "team", "s3", "both") for m in (OPUS, SONNET))
    assert (opus["lo"], opus["hi"], sonnet["lo"], sonnet["hi"]) == (
        94.54,
        96.05,
        90.96,
        92.58,
    )


def test_subset_pool_recomputes_the_papers_statistic() -> None:
    """A partial run is compared with the paper's scenario average over exactly its scenarios."""
    full = PAPER.pool("corpus_of_record", OPUS, "team", "none", "assembled")
    assert full is not None and full["joint_pct"] == 71.14 and len(full["boards"]) == 12
    two = ["warfarin_inr_plain", "mtx_trimethoprim_plain"]
    sub = PAPER.pool("corpus_of_record", OPUS, "team", "none", "assembled", two)
    assert sub is not None and sub["n_scenarios"] == 2 and sub["boards"] == sorted(two)
    cells = [PAPER.cell("corpus_of_record", b, "team", OPUS) for b in two]
    mean = sum(float(c["joint_pct"]) for c in cells if c is not None) / 2
    assert abs(sub["joint_pct"] - mean) <= 0.006
    assert sub["lo"] <= sub["joint_pct"] <= sub["hi"]
    assert (
        PAPER.pool(
            "corpus_of_record",
            OPUS,
            "team",
            "none",
            "assembled",
            ["warfarin_inr_split"],
        )
        is None
    )
