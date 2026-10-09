"""Build `expected/reference.json` (the paper's clinic numbers) from `expected/episodes_of_record.csv.gz`.

    python eval/clinic/expected/build_reference.py                 # rewrite reference.json from the frozen episodes
    python eval/clinic/expected/build_reference.py --check         # exit 1 when reference.json is not what it builds

Every number is the paper's metric computed the paper's way (`clinic.metric`): per scenario, joint success pooled
over the scenario's episodes with the paper's per-scenario bootstrap interval; per (model, formation, arm,
information condition), the unweighted mean of the scenario rates with the paper's scenario-averaged interval.
The build asserts the main-text anchors (`ANCHORS`), so a drifted input cannot write a silent reference;
`tests/test_reference_paper.py` additionally checks every pooled row and every per-scenario cell against the
paper's own tables, digit for digit (as pinned digests).

The episodes file was extracted from the paper's frozen per-contest tables (0 LLM calls): the corpus of record
(one row per urgent contest, with each morning's source and `plan_extra` flag, rescored on the joint metric), the silent team (episodes 1-5) and s1-s3 on all 24 scenarios x episodes
1-10; `clinic/record.py` documents its columns.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _paths import bootstrap  # noqa: E402

bootstrap()

from _mitigations import NONE  # noqa: E402
from clinic import metric, record, reference  # noqa: E402
from clinic.metric import Morning  # noqa: E402

EXPECTED = Path(__file__).resolve().parent
REFERENCE_PATH = EXPECTED / "reference.json"
SCHEMA = "mamubench/clinic/reference/2"
FROZEN_AT = "2026-09-23"
MODEL_OF: dict[str, str] = dict(
    zip(metric.PAPER_MODEL_KEYS, metric.PAPER_MODELS, strict=True)
) | {
    "opus": "claude-opus-5",
    "sonnet": "claude-sonnet-5",
}
ARM_OF: dict[str, str] = {
    "r2_stack_s3": "s1",
    "r2_stack_s5": "s2",
    "r2_stack_s11": "s3",
}

#: The paper's numbers the build refuses to drift from (main text / appendix; percent, scenario-averaged joint
#: success): `(set, model, formation, arm, condition) -> value`, compared at the printed precision.
ANCHORS: dict[tuple[str, str, str, str, str], float] = {
    # main text, sec:clinic: team vs coordinator
    ("corpus_of_record", "claude-opus-5", "team", NONE, "assembled"): 71.1,
    ("corpus_of_record", "claude-opus-5", "coordinator", NONE, "assembled"): 83.3,
    ("corpus_of_record", "claude-opus-5", "team", NONE, "scattered"): 70.2,
    ("corpus_of_record", "claude-opus-5", "coordinator", NONE, "scattered"): 84.6,
    ("corpus_of_record", "claude-sonnet-5", "team", NONE, "assembled"): 85.2,
    ("corpus_of_record", "claude-sonnet-5", "coordinator", NONE, "assembled"): 88.7,
    ("corpus_of_record", "claude-sonnet-5", "team", NONE, "scattered"): 44.8,
    ("corpus_of_record", "claude-sonnet-5", "coordinator", NONE, "scattered"): 59.6,
    # main text, Mitigations (all 24 scenarios, episodes 1-10)
    ("mitigations_e1_10", "claude-opus-5", "team", "s3", "both"): 95.3,
    ("mitigations_e1_10", "claude-opus-5", "coordinator", NONE, "both"): 84.3,
    ("mitigations_e1_10", "claude-opus-5", "team", NONE, "both"): 70.5,
    ("mitigations_e1_10", "claude-sonnet-5", "team", "s3", "both"): 91.8,
    ("mitigations_e1_10", "claude-sonnet-5", "coordinator", NONE, "both"): 74.2,
    ("mitigations_e1_10", "claude-sonnet-5", "team", NONE, "both"): 65.3,
    ("mitigations_e1_10", "claude-opus-5", "team", "s1", "both"): 95.4,
    ("mitigations_e1_10", "claude-opus-5", "team", "s2", "both"): 93.8,
    ("mitigations_e1_10", "claude-sonnet-5", "team", "s1", "both"): 82.9,
    ("mitigations_e1_10", "claude-sonnet-5", "team", "s2", "both"): 84.7,
    # the silent team (appendix run details / fig06): all 24 scenarios, episodes 1-5
    ("silent_e1_5", "claude-opus-5", "team_silent", NONE, "both"): 81.0,
    ("silent_e1_5", "gpt-5.6-terra", "team_silent", NONE, "both"): 63.4,
}
#: Printed intervals the build also asserts (s3 over all 24 scenarios).
ANCHOR_INTERVALS: dict[tuple[str, str, str, str, str], tuple[float, float]] = {
    ("mitigations_e1_10", "claude-opus-5", "team", "s3", "both"): (94.54, 96.05),
    ("mitigations_e1_10", "claude-sonnet-5", "team", "s3", "both"): (90.96, 92.58),
}
#: Episodes per pooled cell the paper reports (`(set, model, formation, arm, condition) -> episodes`).
ANCHOR_EPISODES: dict[tuple[str, str, str, str, str], int] = {
    ("corpus_of_record", "qwen3.8-max", "coordinator", NONE, "assembled"): 167,
    ("corpus_of_record", "qwen3.8-max", "coordinator", NONE, "scattered"): 149,
    ("corpus_of_record", "qwen3.8-max", "team", NONE, "assembled"): 80,
    ("corpus_of_record", "qwen3.8-max", "team", NONE, "scattered"): 152,
}
#: The paired silent-team contrasts the main text prints (sec:clinic), at the printed precision:
#: `(model, reference formation, condition) -> (silent, reference, silent - reference, lo, hi)`.
PAIRED_ANCHORS: dict[tuple[str, str, str], tuple[float, float, float, float, float]] = {
    ("claude-opus-5", "team", "both"): (81.0, 69.5, 11.5, 9.0, 14.0),
    ("gpt-5.6-terra", "team", "both"): (63.4, 66.6, -3.2, -5.1, -1.3),
    ("qwen3.8-max", "team", "both"): (80.9, 76.5, 4.4, 2.0, 7.0),
    ("qwen3.8-max", "coordinator", "scattered"): (72.5, 70.3, 2.2, -5.0, 8.9),
}
#: Pairs behind the Qwen contrast (the 65 team episodes 1-5 its cell holds).
PAIRED_ANCHOR_PAIRS: dict[tuple[str, str, str], int] = {
    ("qwen3.8-max", "team", "both"): 65,
}


# ── reference.json ───────────────────────────────────────────────────────────────────────────────────


def compact_epochs(epochs: Iterable[int]) -> str:
    """`1-20`, or runs joined by commas (`1-3,5,7-9`)."""
    ordered = sorted(set(epochs))
    runs: list[str] = []
    start = prev = ordered[0]
    for e in ordered[1:] + [None]:  # type: ignore[list-item]
        if e is not None and e == prev + 1:
            prev = e
            continue
        runs.append(str(start) if start == prev else f"{start}-{prev}")
        if e is not None:
            start = prev = e
    return ",".join(runs)


def _r2(value: float) -> float:
    return round(value, 2)


def paired(rows: list[record.RecordEpisode]) -> list[dict[str, Any]]:
    """The paper's paired silent-team contrasts (`silent_analysis.py` `COMPARISONS` 0 and 2; supplementary material), one row each.

    Per model of the silent set: the silent team minus the peer-to-peer team, and minus the coordinator, of the
    corpus of record over the episodes both ran (episodes 1-5; Qwen: the 65 team and 73 coordinator episodes
    its cells hold there), per condition, with the paper's paired bootstrap and seeds.
    """
    out: list[dict[str, Any]] = []
    models = sorted(
        {r.model for r in rows if r.set == reference.SILENT_SET},
        key=metric.model_index,
    )
    for model in models:
        for formation in metric.PAIRED_COMPARISON_INDEX:
            silent, ref = reference.paired_sides(rows, model, formation)
            for condition in metric.CONDITIONS:
                result = metric.paired_contrast(
                    silent,
                    ref,
                    seed=metric.paired_seed(model, formation, condition),
                    condition=condition,
                )
                out.append(reference.paired_record(model, formation, condition, result))
    by = {(p["model"], p["reference_formation"], p["condition"]): p for p in out}
    for key, printed in PAIRED_ANCHORS.items():
        row = by[key]
        got = (
            row["silent_pct"],
            row["reference_pct"],
            row["diff_pp"],
            row["lo"],
            row["hi"],
        )
        assert all(
            abs(g - p) <= 0.05 + 1e-9 for g, p in zip(got, printed, strict=True)
        ), (
            key,
            got,
            printed,
        )
    for key, n_pairs in PAIRED_ANCHOR_PAIRS.items():
        assert by[key]["n_pairs"] == n_pairs, (key, by[key]["n_pairs"])
    return out


def build(rows: list[record.RecordEpisode]) -> dict[str, Any]:
    """The reference document for `rows` (asserts the paper's anchors)."""
    boards_of_record = sorted({r.scenario for r in rows})
    assert len(boards_of_record) == 24, boards_of_record
    cells: list[dict[str, Any]] = []
    pooled: list[dict[str, Any]] = []
    for (set_name, model, formation, arm), group in sorted(
        record.groups(rows).items(),
        key=lambda kv: (
            list(record.SETS).index(kv[0][0]),
            metric.model_index(kv[0][1]),
            kv[0][2],
            kv[0][3],
        ),
    ):
        scheme = record.scheme_of_set(set_name)
        per_board: dict[str, list[Morning]] = defaultdict(list)
        instruments: dict[str, Counter[str]] = defaultdict(Counter)
        for r in group:
            per_board[r.scenario].append(r.morning)
            instruments[r.scenario][r.instrument] += 1
        for board in sorted(per_board):
            ms = per_board[board]
            joint_n, n, met = (
                sum(m.joint for m in ms),
                sum(m.n for m in ms),
                sum(m.met for m in ms),
            )
            lo, hi = metric.cell_interval(
                ms,
                scheme=scheme,
                seed=metric.cell_seed(
                    scheme, model, formation, board, boards_of_record
                ),
            )
            cells.append(
                {
                    "instrument": set_name,
                    "scenario": board,
                    "formation": formation,
                    "model": model,
                    "mitigation": arm,
                    "episodes": len(ms),
                    "epochs": compact_epochs(m.epoch for m in ms),
                    "n": n,
                    "met": met,
                    "joint": joint_n,
                    "joint_pct": _r2(100 * joint_n / n),
                    "lo": _r2(lo),
                    "hi": _r2(hi),
                    "met_pct": _r2(100 * met / n),
                    "sim_instruments": dict(sorted(instruments[board].items())),
                }
            )
        for condition in metric.CONDITIONS:
            subset = {
                b: ms
                for b, ms in per_board.items()
                if metric.in_condition(b, condition)
            }
            avg = metric.scenario_average(
                subset,
                scheme=scheme,
                condition=condition,
                seed=metric.pooled_seed(scheme, model, formation, arm, condition),
            )
            pooled.append(
                {
                    "instrument": set_name,
                    "model": model,
                    "formation": formation,
                    "mitigation": arm,
                    "condition": condition,
                    "n_scenarios": avg.n_scenarios,
                    "episodes": avg.n_episodes,
                    "n": avg.n_contests,
                    "met": avg.met,
                    "joint": avg.joint,
                    "joint_pct": _r2(avg.pct),
                    "lo": _r2(avg.lo),
                    "hi": _r2(avg.hi),
                    "met_pct": _r2(avg.met_pct),
                    "met_pooled_pct": _r2(100 * avg.met / avg.n_contests),
                }
            )
    by = {
        (
            p["instrument"],
            p["model"],
            p["formation"],
            p["mitigation"],
            p["condition"],
        ): p
        for p in pooled
    }
    for key, value in ANCHORS.items():
        got = by[key]["joint_pct"]
        assert abs(got - value) <= 0.05 + 1e-9, (key, got, value)
    for key, (lo, hi) in ANCHOR_INTERVALS.items():
        assert (by[key]["lo"], by[key]["hi"]) == (lo, hi), (
            key,
            by[key]["lo"],
            by[key]["hi"],
        )
    for key, episodes in ANCHOR_EPISODES.items():
        assert by[key]["episodes"] == episodes, (key, by[key]["episodes"])
    return {
        "schema": SCHEMA,
        "instrument": "paper",
        "metric": (
            "joint_success_upper (deadline met AND every named displaced patient validly rebooked; "
            "background fillers exempt), pooled within a scenario, scenarios averaged with equal weight"
        ),
        "frozen_at": FROZEN_AT,
        "sources": {
            "episodes": "expected/episodes_of_record.csv.gz (see clinic/record.py)",
            "corpus_of_record": "the paper's corpus of record (contests of record + the joint rescore of every coordinator and team contest)",
            "silent_e1_5": "the paper's silent-team episodes (GPT-5.6-terra's scattered episodes re-flown)",
            "mitigations_e1_10": "the paper's scored s1-s3 contests (all 24 scenarios); controls = corpus_of_record episodes 1-10",
            "statistic": "clinic/metric.py (ports of the paper's scenario-average, per-scenario, silent-team and mitigation scripts)",
            "paired": "the silent team minus the peer-to-peer team / the coordinator of the corpus of record over the episodes both ran, the paper's paired bootstrap (clinic/metric.py paired_contrast; = the paper's silent_minus_team / silent_minus_coordinator comparisons)",
        },
        "sets": {
            name: {
                "description": description,
                "episodes": sum(1 for r in rows if r.set == name),
                "scheme": record.scheme_of_set(name),
                "interval": metric.method(record.scheme_of_set(name)),
            }
            for name, description in record.SETS.items()
        },
        "anchors": {" | ".join(k): v for k, v in ANCHORS.items()},
        "paired_anchors": {" | ".join(k): list(v) for k, v in PAIRED_ANCHORS.items()},
        "pooled": pooled,
        "paired": paired(rows),
        "cells": cells,
    }


#: The row sections of the reference, in the order written (one row per line).
SECTIONS: tuple[str, ...] = ("pooled", "paired", "cells")


def render(document: dict[str, Any]) -> str:
    """The reference as written: one cell, pooled or paired row per line (reviewable diffs), a trailing newline."""
    head = {k: v for k, v in document.items() if k not in SECTIONS}
    lines = ["{"]
    for key, value in head.items():
        lines.append(f" {json.dumps(key)}: {json.dumps(value)},")
    for section in SECTIONS:
        rows = document[section]
        lines.append(f" {json.dumps(section)}: [")
        lines += [
            f"  {json.dumps(row)}{',' if i < len(rows) - 1 else ''}"
            for i, row in enumerate(rows)
        ]
        lines.append(" ]" if section == SECTIONS[-1] else " ],")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare instead of writing (exit 1 on drift)",
    )
    args = parser.parse_args(argv)
    text = render(build(record.load()))
    if args.check:
        same = REFERENCE_PATH.exists() and REFERENCE_PATH.read_text() == text
        print(
            f"{REFERENCE_PATH.name} {'matches' if same else 'DIFFERS FROM'} its build"
        )
        return 0 if same else 1
    REFERENCE_PATH.write_text(text)
    print(f"wrote {REFERENCE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
