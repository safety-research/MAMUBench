"""Compare a merge_queue run against `expected/reference.json`: the reproduction contract, mechanized.

Per covered (scenario, formation, model, mitigation) cell, the run's mean `welfare_over_opt` and its
`lost_dearer` rate (Wilson 95%) are compared with the reference cells of the instruments that ran the same
thinking level:

    PASS  inside the reference's 95% band
    WARN  outside it, but the run's own 95% interval overlaps the reference's (underpowered)
    MISS  the two intervals are disjoint

Instruments (`expected/reference.json` `instruments`; all ran the paper's world, thinking off):

- `paper_2026_09_23`: the paper's merge-queue cells (1,809 episodes after rule T, the provider-failure screen): the
  four formations and the `charter` arm on `oversub`, `volunteer_p1`, `volunteer_p3` and `baseline_tight`, 14-20
  episodes per cell. The band is the paper's per-cell percentile bootstrap (2,000 draws, crc32 cell seed), and a run
  cell is banded with the same bootstrap.
- `paper_loop_2026_09_23`: the paper's repair-loop arms (`lead_cut_line`, `priorities`, `charter_stakes`;
  n = 4-5 per cell), same interval.

A run cell of another thinking level prints as SKIP. `--instrument` narrows the comparison to named
instruments. A reference cell with n<5 or a zero-width band is degenerate (any imperfect run is a MISS);
its lines are flagged and should be read as unresolved, not as failures. A RUN cell with fewer than 5 clean
episodes or a zero-width interval (one episode, or identical welfare) is degenerate the same way: its welfare
line is flagged and a disjoint band reads WARN, never MISS (a one-episode smoke cannot fail the check).

Episodes off the paper's instrument (a thinking level other than off, `--no-voicer`) are named in an
OFF-INSTRUMENT banner. Every reference ran the requester voicer, so a `--no-voicer` cell is SKIPped
(`--allow-off-instrument` compares it anyway and marks each such line OFF-INSTRUMENT).

    python eval/merge_queue/check.py runs/<name> [--reference expected/reference.json] [--instrument NAME ...]
        [--allow-off-instrument]

Exit 0 = no MISS and at least one cell checked; 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _mitigations import label as arm_label  # noqa: E402
from _mitigations import of as mitigation_of  # noqa: E402
from _offpaper import (  # noqa: E402
    ALLOW_FLAG,
    ALLOW_HELP,
    banner,
    gated_verdicts,
    split,
)
from _stats import band, wilson  # noqa: E402

from merge_queue.report import (  # noqa: E402
    RELIABLE_N,
    cell_rows,
    collect,
    reference_interval,
    run_interval,
    thinking_level,
    unbanked_note,
    unbanked_runs,
)

EVAL_ROOT = Path(__file__).resolve().parent
DEFAULT_REFERENCE = EVAL_ROOT / "expected" / "reference.json"
STATUS_ORDER = ("PASS", "WARN", "SKIP", "MISS")
#: Appended to a compared line whose reference cell cannot band a run meaningfully.
DEGENERATE_NOTE = " (reference n<5 / sd=0: band degenerate)"
#: Appended to a welfare line whose RUN cell has fewer than `RELIABLE_N` clean episodes or a zero-width interval
#: (n = 1, or identical welfare): its interval cannot be disjoint in any meaningful sense, so a MISS reads WARN.
RUN_DEGENERATE_NOTE = " (run n<5 / zero-width interval: degenerate, read as unresolved)"
#: The paper's merge-queue cells ran pi thinking off (`expected/reference.json` `paper_2026_09_23`).
PAPER_THINKING = "off"
#: Under the OFF-INSTRUMENT banner: which of its episodes are compared with what.
OFF_INSTRUMENT_NOTE = (
    "A cell of another thinking level is compared only with reference cells that ran it (none do); a "
    f"--no-voicer cell is SKIPped unless {ALLOW_FLAG} (every reference ran the requester voicer)."
)


def _suffix(status: str) -> str:
    return {
        "MISS": " — intervals disjoint",
        "WARN": " — outside the band, intervals overlap (underpowered)",
    }.get(status, "")


def voicer_reasons(row: dict[str, Any]) -> list[str]:
    """Why an episode is off every reference's instrument: it ran without the requester voicer."""
    if row.get("voicer", True) is not False:
        return []
    return ["no requester voicer (--no-voicer; every reference ran it)"]


def paper_reasons(row: dict[str, Any]) -> list[str]:
    """Why an episode is off the paper's instrument: its thinking level, the requester voicer."""
    reasons: list[str] = []
    thinking = thinking_level(row.get("thinking"))
    if thinking != PAPER_THINKING:
        reasons.append(
            f"pi thinking {thinking or 'unrecorded'} (the paper's cells ran {PAPER_THINKING})"
        )
    return reasons + voicer_reasons(row)


def compare_mean(
    label: str,
    run: tuple[float, tuple[float, float], int],
    ref: tuple[float, tuple[float, float]],
    ref_label: str,
) -> tuple[str, str]:
    """`(status, line)` of a run mean and interval against a reference mean and band.

    A degenerate run (fewer than `RELIABLE_N` clean episodes or a zero-width interval) cannot be disjoint in
    any meaningful sense: a MISS reads WARN and the line says so.
    """
    mean, interval, n = run
    ref_mean, reference = ref
    status = band(mean, interval, reference)
    suffix = _suffix(status)
    degenerate = n < RELIABLE_N or interval[1] - interval[0] <= 0.0
    if degenerate and status == "MISS":
        status, suffix = "WARN", " — outside the band"
    return status, (
        f"{status} {label}: run {mean:.3f} [{interval[0]:.3f}, {interval[1]:.3f}] (n={n}) vs "
        f"{ref_label} {ref_mean:.3f} [{reference[0]:.3f}, {reference[1]:.3f}]{suffix}"
        + (RUN_DEGENERATE_NOTE if degenerate else "")
    )


def compare_rate(
    label: str, hits: int, n: int, ref_hits: int, ref_n: int, ref_label: str
) -> tuple[str, str]:
    interval = wilson(hits, n)
    reference = wilson(ref_hits, ref_n)
    status = band(hits / n, interval, reference)
    return status, (
        f"{status} {label}: run {hits}/{n} = {hits / n:.1%} [{interval[0]:.1%}, {interval[1]:.1%}] vs "
        f"{ref_label} {ref_hits}/{ref_n} = {ref_hits / ref_n:.1%} [{reference[0]:.1%}, {reference[1]:.1%}]{_suffix(status)}"
    )


def check(
    run_cells: list[dict[str, Any]],
    reference: dict[str, Any],
    *,
    instruments: tuple[str, ...] = (),
) -> list[tuple[str, str]]:
    """Verdict lines for every run cell: compared against the same-thinking instruments, SKIP otherwise.

    A mitigation arm's cell is compared only with reference cells of the same arm (a reference cell
    without a `mitigation` key is a control cell). `instruments`, when given, keeps only those.
    """
    refs: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for cell in cast(list[dict[str, Any]], reference["cells"]):
        if instruments and str(cell["instrument"]) not in instruments:
            continue
        refs.setdefault(
            (
                str(cell["scenario"]),
                str(cell["formation"]),
                str(cell["model"]),
                mitigation_of(cell),
            ),
            [],
        ).append(cell)
    verdicts: list[tuple[str, str]] = []
    for cell in run_cells:
        key = (
            str(cell["scenario"]),
            str(cell["formation"]),
            str(cell["model"]),
            mitigation_of(cell),
        )
        label = " ".join(key[:3]) + arm_label(key[3])
        if key not in refs:
            verdicts.append(("SKIP", f"SKIP {label}: no reference cell"))
            continue
        if cell["welfare_mean"] is None:
            verdicts.append(("SKIP", f"SKIP {label}: no clean episode in this run"))
            continue
        thinking = thinking_level(cell.get("thinking"))
        for ref in refs[key]:
            ref_label = f"{ref['instrument']} (n={ref['n']})"
            ref_thinking = thinking_level(ref.get("thinking"))
            if ref_thinking != thinking:
                verdicts.append(
                    (
                        "SKIP",
                        f"SKIP {label}: {ref_label} ran thinking {ref_thinking or 'unrecorded'}, this run "
                        f"ran {thinking or 'unrecorded'} — the two levels are never compared",
                    )
                )
                continue
            ref_n = int(ref["n"])
            ref_band = reference_interval(ref)
            status, line = compare_mean(
                label,
                (float(cell["welfare_mean"]), run_interval(cell), int(cell["clean"])),
                (float(ref["welfare_mean"]), ref_band),
                ref_label,
            )
            if ref_n < RELIABLE_N or ref_band[1] - ref_band[0] <= 0.0:
                line += DEGENERATE_NOTE
            verdicts.append((status, line))
            status, line = compare_rate(
                f"{label} :: lost dearer",
                int(cell["lost_dearer"]),
                int(cell["clean"]),
                int(ref["lost_dearer"]),
                ref_n,
                ref_label,
            )
            if ref_n < RELIABLE_N:
                line += DEGENERATE_NOTE
            verdicts.append((status, line))
    return verdicts


def failed_cells(
    rows: list[dict[str, Any]], unbanked: list[dict[str, Any]]
) -> list[tuple[str, str]]:
    """A SKIP line per cell the run planned whose every episode failed (only `INCOMPLETE.json` run dirs)."""

    def key(r: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            str(r["scenario"]),
            str(r["formation"]),
            str(r["model"]),
            mitigation_of(r),
        )

    banked = {key(r) for r in rows}
    failed: dict[tuple[str, str, str, str], list[str]] = {}
    for r in unbanked:
        if key(r) not in banked:
            failed.setdefault(key(r), []).append(str(r["run"]))
    return [
        (
            "SKIP",
            f"SKIP {' '.join(k[:3])}{arm_label(k[3])}: every episode failed ({', '.join(runs)}); nothing to compare",
        )
        for k, runs in sorted(failed.items())
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("runs_root", nargs="?", type=Path, default=EVAL_ROOT / "runs")
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument(
        "--instrument",
        nargs="+",
        default=[],
        help="compare only with these reference instruments (default: every instrument)",
    )
    parser.add_argument(
        "--keep-provider-errors",
        action="store_true",
        help="do not apply rule T (keep episodes a provider error ended a seat turn of)",
    )
    parser.add_argument(
        ALLOW_FLAG, dest="allow_off_instrument", action="store_true", help=ALLOW_HELP
    )
    args = parser.parse_args(argv)
    reference = cast(dict[str, Any], json.loads(args.reference.read_text()))
    rows = collect(args.runs_root.resolve(), screen=not args.keep_provider_errors)
    _, off, reasons = split(rows, paper_reasons)
    for line in banner(reasons, len(off), len(rows), None, OFF_INSTRUMENT_NOTE):
        print(line)
    _, verdicts = gated_verdicts(
        rows,
        voicer_reasons,
        lambda group: check(
            cell_rows(group), reference, instruments=tuple(args.instrument)
        ),
        lambda r: (
            f"{r['scenario']} {r['formation']} {r['model']}{arm_label(mitigation_of(r))}"
        ),
        paper=True,
        allow=args.allow_off_instrument,
    )
    unbanked = unbanked_runs(args.runs_root.resolve())
    for line in unbanked_note(unbanked):
        print(line)
    verdicts += failed_cells(rows, unbanked)
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
            "NOTHING CHECKED — no covered cell had a reference and a clean episode; this is not a pass"
        )
        return 1
    return 1 if counts["MISS"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
