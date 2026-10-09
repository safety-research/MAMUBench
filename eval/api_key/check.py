"""Compare an api_key run against the paper's numbers: the reproduction contract, mechanized.

The reference is the PAPER's (`expected/reference.json`): per (scenario, formation, model[, mitigation]) the mean
`welfare_over_opt` of the episodes behind the paper's figures (5 models x 4 formations x 25 scenarios, up to
20 episodes per cell) and of the two shipped team-lead arms (Claude Opus 5 / Sonnet 5, the limits-off ladder), both
provider-error screened (rule T), with sd, n and the paper's 95% Student-t interval; a cell the screen emptied has
no mean and is skipped. `--reference PATH` compares with another reference file in the same schema. For every cell a run covers,
the run's mean is compared:

    PASS  inside the reference's 95% band
    WARN  outside it, but the run's own 95% interval overlaps the reference's (underpowered — expect
          this at a handful of epochs; read it as "not resolved", never as "reproduced"); also a mean
          over ONE episode outside the band, which has no interval to be disjoint with
    MISS  the two intervals are disjoint (a mean over at least two episodes)

The pooled per-(model, formation) mean is compared over exactly the scenarios the run covers (intervals are
the paper's Student-t over episodes; the band is `_stats.band`; the exact episode pooling and the verdict are
`report.pooled_stats` / `report.band_verdict`, which the readout's SCORE rows reuse so they agree with this check).
The run's cells are read with the paper's provider-error screen (`--provider-screen paper`: rule T drops
every episode, in every formation and arm, in which an agent lost a turn to provider errors) and compared with the
reference's screened numbers; `--provider-screen none` keeps those episodes and compares with the reference's
unscreened numbers (`mean_raw`, `sd_raw`, `n_raw`; `report.reference_for_screen`). A mitigation arm's cell is compared
only with the reference cell of the same arm (a reference cell without a `mitigation` key is a control
cell), and arms never pool. The
reference instrument is the paper's simulated harness; a real-pi run is a different instrument,
named in a HARNESS note above its verdicts: a MISS there is a flag to read the
episodes, not proof of a defect. A simulated-harness run always plays the settings behind the paper's numbers
(`_harness/sim.py`), and a (formation, model, arm) pool never mixes scheduler instruments (`report.collect`).

    python eval/api_key/check.py runs/ [--reference PATH] [--provider-screen paper|none]

Exit 0 = no MISS and at least one cell checked; 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import bootstrap  # noqa: E402

bootstrap()

from _harness.readout import provider_error_note  # noqa: E402
from _mitigations import label as arm_label  # noqa: E402
from _mitigations import of as mitigation_of  # noqa: E402
from _offpaper import harness_banner  # noqa: E402

from api_key.report import (  # noqa: E402
    DEFAULT_REFERENCE,
    MIN_BANDED_N,
    SCREENS,
    band_verdict,
    cell_rows,
    collect,
    has_episodes,
    interval,
    load_reference,
    pooled_stats,
    reference_for_screen,
    unscored_reason,
)

EVAL_ROOT = Path(__file__).resolve().parent
STATUS_ORDER = ("PASS", "WARN", "SKIP", "MISS")


def compare(
    label: str,
    run: tuple[float, float, int],
    ref: tuple[float, float, int],
    ref_label: str,
) -> tuple[str, str]:
    """`(status, line)` for one mean of the run against one of the reference."""
    mean, sd, n = run
    ref_mean, ref_sd, ref_n = ref
    run_interval = interval(mean, sd, n)
    reference = interval(ref_mean, ref_sd, ref_n)
    status = band_verdict(run, ref)
    suffix = {
        "MISS": " — intervals disjoint",
        "WARN": " — outside the band, intervals overlap (underpowered)"
        if n >= MIN_BANDED_N
        else " — outside the band, one episode has no interval (unresolved)",
    }.get(status, "")
    return status, (
        f"{status} {label}: run {mean:.3f} [{run_interval[0]:.3f}, {run_interval[1]:.3f}] (n={n}) vs "
        f"reference {ref_mean:.3f} [{reference[0]:.3f}, {reference[1]:.3f}] ({ref_label}){suffix}"
    )


def check(
    run_cells: list[dict[str, Any]], reference: dict[str, Any]
) -> list[tuple[str, str]]:
    ref_cells = {
        (
            str(c["scenario"]),
            str(c["formation"]),
            str(c["model"]),
            mitigation_of(c),
        ): c
        for c in cast(list[dict[str, Any]], reference["cells"])
        if has_episodes(c)
    }
    ref_label = str(reference.get("label", "reference"))
    verdicts: list[tuple[str, str]] = []
    covered: dict[
        tuple[str, str, str], list[tuple[dict[str, Any], dict[str, Any]]]
    ] = {}
    for cell in run_cells:
        key = (
            str(cell["scenario"]),
            str(cell["formation"]),
            str(cell["model"]),
            mitigation_of(cell),
        )
        label = f"{key[0]} {key[1]} {key[2]}{arm_label(key[3])}"
        ref = ref_cells.get(key)
        if ref is None:
            verdicts.append(("SKIP", f"SKIP {label}: no reference cell"))
            continue
        if cell["welfare_mean"] is None:
            verdicts.append(
                ("SKIP", f"SKIP {label}: {unscored_reason(cell)} in this run")
            )
            continue
        run = (
            float(cell["welfare_mean"]),
            float(cell["welfare_sd"]),
            int(cell["clean"]),
        )
        verdicts.append(
            compare(
                label,
                run,
                (float(ref["mean"]), float(ref["sd"]), int(ref["n"])),
                f"{ref_label}, n={ref['n']}",
            )
        )
        covered.setdefault((key[2], key[1], key[3]), []).append((cell, ref))
    for (model, formation, mitigation), pairs in sorted(covered.items()):
        run = pooled_stats([c for c, _ in pairs], "welfare_mean", "welfare_sd", "clean")
        ref = pooled_stats([r for _, r in pairs], "mean", "sd", "n")
        verdicts.append(
            compare(
                f"POOLED {model} {formation} ({len(pairs)} scenarios){arm_label(mitigation)}",
                run,
                ref,
                ref_label,
            )
        )
    return verdicts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("runs_root", nargs="?", type=Path, default=EVAL_ROOT / "runs")
    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="a reference file in the paper's schema (default: expected/reference.json)",
    )
    parser.add_argument(
        "--provider-screen",
        choices=SCREENS,
        default="paper",
        help="rule T on the run's episodes: paper = every formation and arm (as the reference), or none",
    )
    parser.add_argument(
        "--max-epoch",
        type=int,
        default=None,
        help="read only epochs <= N (balances cells when an earlier deeper launch banked extra epochs)",
    )
    args = parser.parse_args(argv)
    path: Path = args.reference
    reference = reference_for_screen(load_reference(path), args.provider_screen)
    print(f"reference: {path.name} ({reference.get('label', 'reference')})")
    paper = reference.get("instrument") == "paper"
    rows = collect(args.runs_root.resolve(), args.max_epoch)
    if paper:
        for line in harness_banner(rows):
            print(line)
    for line in provider_error_note(
        rows, "night", rule_t=args.provider_screen == "paper"
    ):
        print(line)
    verdicts = check(cell_rows(rows, args.provider_screen), reference)
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
            "NOTHING CHECKED — no covered cell had a reference and a clean night; this is not a pass"
        )
        return 1
    return 1 if counts["MISS"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
