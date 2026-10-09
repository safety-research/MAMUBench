"""The paper's clinic reference (`expected/reference.json`, schema 2), indexed for the reports and the check.

The file holds, per frozen set of the paper (`corpus_of_record`, `silent_e1_5`, `mitigations_e1_10`; see
`clinic/record.py`), one CELL per (scenario, formation, model, arm) — the scenario's joint success pooled over its
episodes, with the paper's per-scenario interval — and one POOLED row per (model, formation, arm, condition) —
the scenario average with the paper's interval. A set is called the cell's `instrument`. `pool(..., boards=...)`
returns the reference over exactly the scenarios a run covered: the frozen row when they are the condition's full
set, else the same statistic recomputed on those scenarios' frozen episodes (`expected/episodes_of_record.csv.gz`),
so a partial run is compared like for like.

It also freezes the paper's PAIRED silent-team contrasts (`paired`: the silent team minus the peer-to-peer team,
and minus the coordinator, over the episodes both ran, with the paper's paired bootstrap; `clinic.metric
.paired_contrast`), one row per (model, reference formation, condition); `paired_contrast(..., boards=...)` returns
the frozen row, or the same statistic recomputed on the frozen episodes of a run's scenarios.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

from _mitigations import NONE
from _mitigations import of as mitigation_of
from _stats import band

from clinic import metric, record
from clinic.metric import Morning

EVAL_ROOT = Path(__file__).resolve().parent
REFERENCE_PATH = EVAL_ROOT / "expected" / "reference.json"
SCHEMA = "mamubench/clinic/reference/2"
#: The set a (formation, arm) is primarily read against (listed first), then any other set holding it.
PRIMARY_ORDER: tuple[str, ...] = tuple(record.SETS)

CellKey = tuple[
    str, str, str, str, str
]  # (instrument, scenario, formation, model, mitigation)
PoolKey = tuple[
    str, str, str, str, str
]  # (instrument, model, formation, mitigation, condition)
PairedKey = tuple[str, str, str]  # (model, reference formation, condition)
#: The silent team's set and the set its paired references come from.
SILENT_SET = "silent_e1_5"
PAIRED_REFERENCE_SET = "corpus_of_record"
#: The reference stores its percentages at two decimals (`round(x, 2)`), so its interval is read with half that
#: rounding unit of slack: a run value equal to the paper's (200/3 = 66.667 against a stored 66.67) lies inside it.
ROUNDING_SLACK_PP = 0.005


def paper_band(
    point: float,
    interval: tuple[float, float],
    reference: tuple[float, float],
    *,
    unit: float = 1.0,
) -> str:
    """`_stats.band` against a reference interval widened by `ROUNDING_SLACK_PP` (`unit` = 0.01 for fractions)."""
    slack = ROUNDING_SLACK_PP * unit
    return band(point, interval, (reference[0] - slack, reference[1] + slack))


def is_paper(document: Mapping[str, Any]) -> bool:
    """True for a document in the paper reference's schema (`SCHEMA`)."""
    return document.get("schema") == SCHEMA


def primary_instrument(formation: str, mitigation: str) -> str:
    """The frozen set the paper reads a (formation, arm) from."""
    return record.set_for(formation, mitigation)


def paired_record(
    model: str, reference_formation: str, condition: str, paired: metric.Paired
) -> dict[str, Any]:
    """One paired-contrast row as `reference.json` freezes it (percent, two decimals; `contrast` = silent - ref)."""
    return {
        "set": SILENT_SET,
        "reference_set": PAIRED_REFERENCE_SET,
        "model": model,
        "formation": "team_silent",
        "reference_formation": reference_formation,
        "contrast": f"team_silent-{reference_formation}",
        "paper_label": metric.PAIRED_PAPER_LABEL[reference_formation],
        "condition": condition,
        "n_scenarios": paired.n_scenarios,
        "n_pairs": paired.n_pairs,
        "silent_pct": round(paired.silent_pct, 2),
        "silent_lo": round(paired.silent_lo, 2),
        "silent_hi": round(paired.silent_hi, 2),
        "reference_pct": round(paired.reference_pct, 2),
        "reference_lo": round(paired.reference_lo, 2),
        "reference_hi": round(paired.reference_hi, 2),
        "diff_pp": round(paired.diff, 2),
        "lo": round(paired.lo, 2),
        "hi": round(paired.hi, 2),
        "silent_ahead": paired.silent_ahead,
        "reference_ahead": paired.reference_ahead,
        "ties": paired.ties,
        "seed": metric.paired_seed(model, reference_formation, condition),
    }


def paired_sides(
    rows: Iterable[record.RecordEpisode], model: str, reference_formation: str
) -> tuple[dict[str, list[Morning]], dict[str, list[Morning]]]:
    """`(silent, reference)` mornings per board of one model from episodes of record (the paired contrast's input)."""
    silent: dict[str, list[Morning]] = defaultdict(list)
    reference: dict[str, list[Morning]] = defaultdict(list)
    for r in rows:
        if r.model != model or r.mitigation != NONE:
            continue
        if r.set == SILENT_SET and r.formation == "team_silent":
            silent[r.scenario].append(r.morning)
        elif r.set == PAIRED_REFERENCE_SET and r.formation == reference_formation:
            reference[r.scenario].append(r.morning)
    return dict(silent), dict(reference)


def paired_boards(
    silent: Mapping[str, list[Morning]],
    reference: Mapping[str, list[Morning]],
    condition: str,
) -> list[str]:
    """The boards of a condition on which the two sides share at least one epoch (the scenarios a pairing covers)."""
    return sorted(
        b
        for b in set(silent) & set(reference)
        if metric.in_condition(b, condition)
        and {m.epoch for m in silent[b]} & {m.epoch for m in reference[b]}
    )


class PaperReference:
    """`expected/reference.json` (schema 2) indexed by cell and by pool."""

    def __init__(
        self,
        document: Mapping[str, Any],
        episodes: list[record.RecordEpisode] | None = None,
    ) -> None:
        self.document = document
        self.cells: dict[CellKey, dict[str, Any]] = {}
        for raw in cast(list[dict[str, Any]], document.get("cells", [])):
            key = (
                str(raw["instrument"]),
                str(raw["scenario"]),
                str(raw["formation"]),
                str(raw["model"]),
                mitigation_of(raw),
            )
            self.cells[key] = raw
        self.pools: dict[PoolKey, dict[str, Any]] = {
            (
                str(raw["instrument"]),
                str(raw["model"]),
                str(raw["formation"]),
                mitigation_of(raw),
                str(raw["condition"]),
            ): raw
            for raw in cast(list[dict[str, Any]], document.get("pooled", []))
        }
        self.paired: dict[PairedKey, dict[str, Any]] = {
            (
                str(raw["model"]),
                str(raw["reference_formation"]),
                str(raw["condition"]),
            ): raw
            for raw in cast(list[dict[str, Any]], document.get("paired", []))
        }
        self._episodes = episodes

    @classmethod
    def load(cls, path: Path = REFERENCE_PATH) -> PaperReference:
        """The reference at `path` (an empty one when the file is absent)."""
        if not path.exists():
            return cls({})
        return cls(cast(dict[str, Any], json.loads(path.read_text())))

    def arms(self) -> list[str]:
        """The arms the file freezes cells for, the control arm first."""
        return sorted({k[4] for k in self.cells}, key=lambda n: (n != NONE, n))

    def instruments(self) -> list[str]:
        """The sets present, in the paper's order (unknown ones after)."""
        found = {k[0] for k in self.cells} | {k[0] for k in self.pools}
        return sorted(
            found,
            key=lambda s: (
                PRIMARY_ORDER.index(s) if s in PRIMARY_ORDER else len(PRIMARY_ORDER),
                s,
            ),
        )

    def cell(
        self,
        instrument: str,
        scenario: str,
        formation: str,
        model: str,
        mitigation: str = NONE,
    ) -> dict[str, Any] | None:
        """One frozen cell, or None."""
        return self.cells.get((instrument, scenario, formation, model, mitigation))

    def cells_for(
        self, scenario: str, formation: str, model: str, mitigation: str = NONE
    ) -> list[tuple[str, dict[str, Any]]]:
        """`(instrument, cell)` for every set holding the cell, the primary set first."""
        primary = primary_instrument(formation, mitigation)
        found = [
            (inst, c)
            for inst in self.instruments()
            if (c := self.cell(inst, scenario, formation, model, mitigation))
            is not None
        ]
        return sorted(found, key=lambda ic: ic[0] != primary)

    def boards(
        self,
        instrument: str,
        model: str,
        formation: str,
        mitigation: str,
        condition: str,
    ) -> list[str]:
        """The scenarios the set holds for a (model, formation, arm) within a condition."""
        return sorted(
            k[1]
            for k in self.cells
            if (k[0], k[3], k[2], k[4]) == (instrument, model, formation, mitigation)
            and metric.in_condition(k[1], condition)
        )

    def _record_episodes(self) -> list[record.RecordEpisode]:
        if self._episodes is None:
            try:
                self._episodes = record.load()
            except OSError:
                self._episodes = []
        return self._episodes

    def paired_contrast(
        self,
        model: str,
        reference_formation: str,
        condition: str,
        boards: Iterable[str] | None = None,
    ) -> dict[str, Any] | None:
        """The paper's paired silent-minus-reference contrast over `boards` (every paired scenario when None).

        The frozen row when `boards` covers every scenario the paper's pairing covers; otherwise the paper's
        statistic (`metric.paired_contrast`, the paper's seed) recomputed on the frozen episodes of the scenarios
        both cover. None when the file freezes no such contrast or no scenario is left. The row carries the
        `boards` it covers.
        """
        frozen = self.paired.get((model, reference_formation, condition))
        if frozen is None:
            return None
        silent, reference = paired_sides(
            self._record_episodes(), model, reference_formation
        )
        held = paired_boards(silent, reference, condition)
        wanted = held if boards is None else sorted(set(boards) & set(held))
        if not wanted:
            return None
        if wanted == held:
            return {**frozen, "boards": wanted, "held": len(held)}
        paired = metric.paired_contrast(
            {b: silent[b] for b in wanted},
            {b: reference[b] for b in wanted},
            seed=metric.paired_seed(model, reference_formation, condition),
            condition=condition,
        )
        return {
            **paired_record(model, reference_formation, condition, paired),
            "boards": wanted,
            "held": len(held),
        }

    def _record_mornings(
        self, instrument: str, model: str, formation: str, mitigation: str
    ) -> dict[str, list[Morning]]:
        group = record.groups(self._record_episodes()).get(
            (instrument, model, formation, mitigation), []
        )
        per_board: dict[str, list[Morning]] = defaultdict(list)
        for r in group:
            per_board[r.scenario].append(r.morning)
        return dict(per_board)

    def pool(
        self,
        instrument: str,
        model: str,
        formation: str,
        mitigation: str,
        condition: str,
        boards: Iterable[str] | None = None,
    ) -> dict[str, Any] | None:
        """The reference's scenario average over `boards` (the condition's full set when None), or None.

        The frozen pooled row when `boards` is the set's full scenario list for the condition; otherwise the
        paper's statistic recomputed on the frozen episodes of those scenarios; failing those (an arm the
        episodes file does not hold), the mean of the cells' rates with a single cell's own interval.
        """
        held = self.boards(instrument, model, formation, mitigation, condition)
        wanted = held if boards is None else sorted(set(boards) & set(held))
        if not wanted:
            return None
        frozen = self.pools.get((instrument, model, formation, mitigation, condition))
        if frozen is not None and wanted == held:
            return {**frozen, "boards": wanted, "held": len(held)}
        per_board = self._record_mornings(instrument, model, formation, mitigation)
        if all(b in per_board for b in wanted):
            scheme = record.scheme_of_set(instrument)
            avg = metric.scenario_average(
                {b: per_board[b] for b in wanted},
                scheme=scheme,
                condition=condition,
                seed=metric.pooled_seed(
                    scheme, model, formation, mitigation, condition
                ),
            )
            return {
                "instrument": instrument,
                "model": model,
                "formation": formation,
                "mitigation": mitigation,
                "condition": condition,
                "n_scenarios": avg.n_scenarios,
                "episodes": avg.n_episodes,
                "n": avg.n_contests,
                "met": avg.met,
                "joint": avg.joint,
                "joint_pct": round(avg.pct, 2),
                "lo": round(avg.lo, 2),
                "hi": round(avg.hi, 2),
                "met_pct": round(avg.met_pct, 2),
                "boards": wanted,
                "held": len(held),
            }
        cells = [
            self.cells[(instrument, b, formation, model, mitigation)] for b in wanted
        ]
        single = cells[0] if len(cells) == 1 else None
        return {
            "instrument": instrument,
            "model": model,
            "formation": formation,
            "mitigation": mitigation,
            "condition": condition,
            "n_scenarios": len(cells),
            "episodes": sum(int(c["episodes"]) for c in cells),
            "n": sum(int(c["n"]) for c in cells),
            "met": sum(int(c["met"]) for c in cells),
            "joint": sum(int(c["joint"]) for c in cells),
            "joint_pct": round(
                sum(float(c["joint_pct"]) for c in cells) / len(cells), 2
            ),
            "lo": float(single["lo"]) if single is not None else math.nan,
            "hi": float(single["hi"]) if single is not None else math.nan,
            "met_pct": round(sum(float(c["met_pct"]) for c in cells) / len(cells), 2),
            "boards": wanted,
            "held": len(held),
        }
