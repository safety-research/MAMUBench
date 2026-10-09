"""Compare a clinic run against the paper: the reproduction contract, mechanized.

    python eval/clinic/check.py runs/<root> [runs/<root2> ...] [--episodes-of-record] [--reference PATH]

By default the run is read on the PAPER's metric and rules (`report.py`: joint success under the named-patient
displacement-chain rule, the paper's validity rules) and compared with `expected/reference.json`, the paper's
frozen numbers (built by `expected/build_reference.py` from `expected/episodes_of_record.csv.gz`):

- per scenario: the run's pooled joint rate and the paper's per-scenario interval of it, against every frozen
  set holding the cell (`corpus_of_record` for the coordinator and the team, `silent_e1_5` for the silent team,
  `mitigations_e1_10` for s1-s3 and, on episodes 1-10, the coordinator and the team they are read against);
- pooled per (model, formation, arm, information condition): the run's scenario average against the paper's
  scenario average over exactly the scenarios the run covered (the frozen row when that is all 12 / 24, else
  the paper's statistic recomputed on those scenarios' frozen episodes);
- the paper's PAIRED silent-team contrasts (`PAIRED`): the silent team minus the peer-to-peer team, and minus
  the coordinator, over the episodes both ran, with the paper's paired bootstrap (`report.paired_rows`), against
  the paper's own contrast over the same scenarios (`reference.json` `paired`).

    PASS  the run's value lies inside the paper's 95% interval
    WARN  outside it, but the run's own interval overlaps the paper's (underpowered)
    MISS  the two intervals are disjoint

The run's interval is the paper's whole-morning bootstrap within scenario. Where a scenario holds fewer than 2 of
the run's mornings that bootstrap cannot vary (it collapses to the point), so the run's interval is instead the 95%
Wilson interval over its contests (an approximation: contests within a morning are not independent; on a pooled
line the mean of its scenarios' Wilson bounds, so it contains the scenario-averaged point), and the line says so. A
PAIRED contrast with fewer than 2 pairs in a scenario has no such fallback: outside the paper's interval it reads
WARN (unresolved), never MISS, and the line says so. A one-morning smoke therefore reads WARN, not MISS, unless it
is far outside the paper's interval. The paper's stored intervals are two-decimal roundings, so they are read with
half a rounding unit of slack (`reference.paper_band`).

`--reference PATH` compares with another reference file in the same schema; a relative path that is not found
from the current directory is looked up under `eval/clinic/` and then under `eval/clinic/expected/`.

A simulated-harness run always plays each paper cell's own settings (`_harness/sim.py`). A real-pi run
(`--harness pi`) is another instrument than the paper's simulated harness: a HARNESS note above its verdicts says
so, and a MISS there is a flag to read the mornings, not a failed reproduction.

A runs root that does not exist is an error (pull a Modal root first). Exit 0 = no MISS and at least one cell
checked; 1 otherwise; 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import bootstrap  # noqa: E402

bootstrap()

from _mitigations import NONE  # noqa: E402
from _mitigations import label as arm_label  # noqa: E402
from _mitigations import of as mitigation_of  # noqa: E402
from _offpaper import harness_banner  # noqa: E402
from _stats import wilson  # noqa: E402

from clinic import metric, record  # noqa: E402
from clinic.reference import (  # noqa: E402
    REFERENCE_PATH,
    PaperReference,
    is_paper,
    paper_band,
)
from clinic.report import (  # noqa: E402
    cell_rows,
    collect,
    conditions_of,
    exclusion_notes,
    missing_roots_message,
    paired_rows,
)

EVAL_ROOT = Path(__file__).resolve().parent
DEFAULT_REFERENCE = REFERENCE_PATH
STATUS_ORDER = ("PASS", "WARN", "SKIP", "MISS")
#: Appended to a line whose run interval is the Wilson interval over contests (`contest_interval`).
WILSON_NOTE = " (fewer than 2 mornings in a scenario: the run's interval is Wilson over its contests)"
#: Appended to a pooled line whose run interval is the mean of its scenarios' Wilson intervals (`scenario_wilson`).
POOLED_WILSON_NOTE = (
    " (fewer than 2 mornings in a scenario: the run's interval is the mean of its scenarios' Wilson intervals "
    "over their contests)"
)
#: Appended to a paired line with fewer than 2 pairs in a scenario (`report.paired_rows` `run_degenerate`).
PAIRED_DEGENERATE_NOTE = (
    " (fewer than 2 pairs in a scenario: the paired bootstrap cannot vary, so outside the paper's interval the "
    "contrast reads WARN, unresolved)"
)


#: What a WARN or MISS line adds after its intervals.
VERDICT_SUFFIX = {
    "MISS": " — intervals disjoint",
    "WARN": " — outside the paper's interval, intervals overlap (underpowered)",
}


def degenerate(mornings_by_scenario: Iterable[Sequence[metric.Morning]]) -> bool:
    """True when some scenario holds fewer than 2 mornings: its within-scenario bootstrap cannot vary.

    The whole-morning bootstrap then collapses to the point, so any value outside the paper's band would be a
    MISS however few mornings back it (a perfect 6/6 on one morning included).
    """
    return any(len(ms) < 2 for ms in mornings_by_scenario)


def contest_interval(joint: int, contests: int) -> tuple[float, float]:
    """The 95% Wilson interval of `joint` of `contests`, in percent: a degenerate cell's interval.

    Contests within a morning are not independent, so this is an approximation, wider than no interval at all.
    """
    lo, hi = wilson(joint, contests)
    return 100 * lo, 100 * hi


def scenario_wilson(
    mornings_by_scenario: dict[str, list[metric.Morning]],
) -> tuple[float, float]:
    """The degenerate pooled interval, in percent: the unweighted mean of the scenarios' Wilson bounds.

    The pooled point is the unweighted mean of the scenarios' rates, and each scenario's Wilson interval contains
    its own rate, so the mean of the bounds contains the point (a Wilson interval over the pooled contests need
    not, when scenarios hold different numbers of contests). A scenario without a contest is left out, as the
    scenario average leaves it out.
    """
    bounds = [
        contest_interval(sum(m.joint for m in ms), sum(m.n for m in ms))
        for ms in mornings_by_scenario.values()
        if ms and sum(m.n for m in ms)
    ]
    if not bounds:
        return math.nan, math.nan
    return (
        sum(lo for lo, _ in bounds) / len(bounds),
        sum(hi for _, hi in bounds) / len(bounds),
    )


def _pct(value: float) -> str:
    return "nan" if math.isnan(value) else f"{value:.1f}"


def compare_paper(
    label: str,
    run: tuple[int, int, float, float, float],
    ref: dict[str, Any],
    ref_label: str,
    note: str = "",
) -> tuple[str, str]:
    """`(status, line)` for one run value against one paper cell or pool.

    `run` = `(joint, contests, value %, lo %, hi %)`; `ref` carries `joint`, `n`, `joint_pct`, `lo`, `hi`; `note`
    ends the line.
    """
    joint, n, value, lo, hi = run
    ref_lo, ref_hi = float(ref["lo"]), float(ref["hi"])
    if math.isnan(ref_lo) or math.isnan(ref_hi):
        status = "SKIP"
        suffix = " — the paper's interval over these scenarios is not recoverable"
    else:
        status = paper_band(value, (lo, hi), (ref_lo, ref_hi))
        suffix = VERDICT_SUFFIX.get(status, "")
    return status, (
        f"{status} {label}: run joint {joint}/{n} = {_pct(value)} [{_pct(lo)}, {_pct(hi)}] vs "
        f"{ref_label} {ref['joint']}/{ref['n']} = {float(ref['joint_pct']):.1f} "
        f"[{_pct(ref_lo)}, {_pct(ref_hi)}]{suffix}{note}"
    )


def _fits(instrument: str, mitigation: str, mornings: Sequence[metric.Morning]) -> bool:
    """The arms' episode-1-10 controls are a reference only for a control run within episodes 1-10."""
    if instrument != record.MITIGATION_SET or mitigation != NONE:
        return True
    return all(m.epoch <= record.MITIGATION_EPOCHS for m in mornings)


def check_paper(
    run_cells: list[dict[str, Any]], reference: PaperReference
) -> list[tuple[str, str]]:
    """Verdicts per run cell and per pooled condition against the paper reference (one arm never meets another).

    `run_cells` are `report.cell_rows`: their `mornings` feed the pooled statistics.
    """
    verdicts: list[tuple[str, str]] = []
    covered: dict[tuple[str, str, str, str], dict[str, list[metric.Morning]]] = {}
    for cell in run_cells:
        scenario, formation, model = (
            str(cell["scenario"]),
            str(cell["formation"]),
            str(cell["model"]),
        )
        arm = mitigation_of(cell)
        label = f"{scenario} {formation} {model}{arm_label(arm)}"
        if not cell["contests"]:
            verdicts.append(("SKIP", f"SKIP {label}: no valid morning in this run"))
            continue
        found = reference.cells_for(scenario, formation, model, arm)
        if not found:
            verdicts.append(("SKIP", f"SKIP {label}: no reference cell"))
            continue
        mornings = list(cast(tuple[metric.Morning, ...], cell["mornings"]))
        joint, n = int(cell["joint"]), int(cell["contests"])
        if degenerate([mornings]):
            (lo, hi), note = contest_interval(joint, n), WILSON_NOTE
        else:
            lo, hi = 100 * float(cell["joint_lo"]), 100 * float(cell["joint_hi"])
            note = ""
        run = (joint, n, 100 * float(cell["joint_rate"]), lo, hi)
        for instrument, ref in found:
            if not _fits(instrument, arm, mornings):
                continue
            verdicts.append(
                compare_paper(
                    label, run, ref, f"{instrument} ({ref['episodes']} episodes)", note
                )
            )
            covered.setdefault((model, formation, arm, instrument), {})[scenario] = (
                mornings
            )
    for (model, formation, arm, instrument), boards in sorted(covered.items()):
        scheme = metric.scheme_for(formation, arm)
        for condition in conditions_of(boards):
            subset = {
                b: ms for b, ms in boards.items() if metric.in_condition(b, condition)
            }
            ref = reference.pool(instrument, model, formation, arm, condition, subset)
            if ref is None:
                continue
            # like for like: the run over exactly the scenarios the reference pool holds
            subset = {b: ms for b, ms in subset.items() if b in ref["boards"]}
            avg = metric.scenario_average(
                subset,
                scheme=scheme,
                condition=condition,
                seed=metric.pooled_seed(scheme, model, formation, arm, condition),
            )
            run = (avg.joint, avg.n_contests, avg.pct, avg.lo, avg.hi)
            note = ""
            if degenerate(subset.values()):
                run = (avg.joint, avg.n_contests, avg.pct, *scenario_wilson(subset))
                note = POOLED_WILSON_NOTE
            held = len(reference.boards(instrument, model, formation, arm, condition))
            span = (
                f"{len(subset)} scenarios"
                if len(subset) >= held
                else f"{len(subset)} of {held} scenarios"
            )
            verdicts.append(
                compare_paper(
                    f"POOLED {model} {formation} {condition} ({span}){arm_label(arm)}",
                    run,
                    ref,
                    f"{instrument} ({ref['episodes']} episodes)",
                    note,
                )
            )
    return verdicts


def check_paired(paired: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Verdicts for the run's paired silent-team contrasts (`report.paired_rows`) against the paper's.

    The band is the run's difference and interval against the paper's paired interval over the same scenarios.
    """
    verdicts: list[tuple[str, str]] = []
    for row in paired:
        label = (
            f"PAIRED {row['model']} {row['contrast']} {row['condition']} "
            f"({row['n_scenarios']} scenarios, {row['n_pairs']} pairs)"
        )
        run = (
            f"run {float(row['silent_pct']):.1f} vs {float(row['reference_pct']):.1f}, "
            f"{float(row['diff_pp']):+.1f} [{float(row['lo_pp']):+.1f}, {float(row['hi_pp']):+.1f}]"
        )
        if row["paper_diff_pp"] is None:
            verdicts.append(("SKIP", f"SKIP {label}: {run}; no paper contrast"))
            continue
        status = str(row["paper_verdict"])
        suffix = VERDICT_SUFFIX.get(status, "")
        if row.get("run_degenerate"):
            suffix = (
                " — outside the paper's interval" if status == "WARN" else ""
            ) + PAIRED_DEGENERATE_NOTE
        verdicts.append(
            (
                status,
                f"{status} {label}: {run} vs paper {row['paper_label']} "
                f"{float(row['paper_diff_pp']):+.2f} [{float(row['paper_lo_pp']):+.2f}, "
                f"{float(row['paper_hi_pp']):+.2f}] ({row['paper_scenarios']} scenarios, "
                f"{row['paper_n_pairs']} pairs){suffix}",
            )
        )
    return verdicts


def resolve_reference(path: Path) -> Path:
    """`--reference` as given, else (relative) under `eval/clinic/`, else under `eval/clinic/expected/`.

    Raises:
        SystemExit: No candidate exists.
    """
    candidates = [path]
    if not path.is_absolute():
        candidates += [EVAL_ROOT / path, EVAL_ROOT / "expected" / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit(
        f"--reference {path}: not found (tried {', '.join(str(c) for c in candidates)})"
    )


def check(
    run_cells: list[dict[str, Any]], reference: dict[str, Any]
) -> list[tuple[str, str]]:
    """Verdicts for `run_cells` (`report.cell_rows`) against a reference document in the paper's schema.

    A mitigation arm's cell is compared only with reference cells of the same arm (a reference cell without a
    `mitigation` key is a control cell); arms never pool.

    Raises:
        SystemExit: The document is not in the paper's reference schema.
    """
    if not is_paper(reference):
        raise SystemExit(
            f"not a clinic reference in the paper's schema (schema {reference.get('schema')!r})"
        )
    return check_paper(run_cells, PaperReference(reference))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("runs_root", nargs="*", type=Path, default=[EVAL_ROOT / "runs"])
    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="a reference file in the paper's schema (default: expected/reference.json)",
    )
    parser.add_argument(
        "--max-epoch",
        type=int,
        default=None,
        help="read only epochs <= N (balances cells when an earlier deeper launch banked extra epochs)",
    )
    parser.add_argument(
        "--episodes-of-record",
        action="store_true",
        help="score only the paper's episodes (expected/episodes_of_record.csv.gz)",
    )
    args = parser.parse_args(argv)
    reference_path = resolve_reference(args.reference)
    reference = cast(dict[str, Any], json.loads(reference_path.read_text()))
    roots = [r.resolve() for r in (args.runs_root or [EVAL_ROOT / "runs"])]
    missing = [r for r in roots if not r.is_dir()]
    if missing:
        parser.error(missing_roots_message(missing))
    episodes, _contests = collect(
        roots, args.max_epoch, episodes_of_record=args.episodes_of_record
    )

    verdicts = check(cell_rows(episodes), reference)
    verdicts += check_paired(paired_rows(episodes, reference=PaperReference(reference)))
    for note in exclusion_notes(episodes):
        print(note)
    print("reference: paper (joint success, scenario-averaged)")
    for line in harness_banner(episodes):
        print(line)
    for status in STATUS_ORDER:
        for s, line in verdicts:
            if s == status:
                print(line)
    counts = Counter(s for s, _ in verdicts)
    checked = counts["PASS"] + counts["WARN"] + counts["MISS"]
    print(
        f"\n{counts['PASS']} PASS, {counts['WARN']} WARN, {counts['MISS']} MISS ({checked} compared; {counts['SKIP']} skipped)"
    )
    if checked == 0:
        print(
            "NOTHING CHECKED — no covered cell had a reference and a valid morning; this is not a pass"
        )
        return 1
    return 1 if counts["MISS"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
