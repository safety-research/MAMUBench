"""Episodes run off the paper's instrument: the pool key and the `check.py` banner the environments share.

The pi environments record the settings that define their instrument: personal_assistant the pi thinking level and
context files, merge_queue the world, the thinking level and the requester voicer; a setting other than the paper's is
an off-paper reason. A simulated-harness episode (api_key, clinic) records its scheduler instrument in the same
schema (`world/config.json` `instrument`, `on_paper_instrument`, `off_paper`), and always on the paper's settings: the
harness plays each cell's settings of record with no override (`_harness/sim.py`). The readers use those records
twice:

- **Pools**: one (formation, model, arm) pool holds ONE physics record, so episodes with different settings never
  average into one cell (`physics`, keyed by `_harness.readout.single_instrument` and `clinic.report.check_pools`).
- **Checks**: the personal_assistant and merge_queue `check.py` print an OFF-INSTRUMENT banner naming every reason
  with its episode count and, when they compare with the paper's reference, SKIP the cells of those episodes: a PASS
  or MISS there would read as a verdict on the paper's numbers from a different instrument.
  `--allow-off-instrument` compares them anyway and marks each of their lines OFF-INSTRUMENT.

A run banked before instruments were recorded is never flagged here. A pi-harness run of a simulated-harness env
(api_key, clinic) records no instrument; `harness_banner` names it above the verdicts instead, which are kept: they
compare another instrument with the paper's numbers, so a MISS there is a flag to read the episodes, not a failed
reproduction.

Kept dependency-free, like `_stats`, so every `check.py` can import it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, Literal, TypeVar, cast

#: The marker on the banner and on every compared line of an off-instrument cell.
OFF_INSTRUMENT = "OFF-INSTRUMENT"
#: The `check.py` option that compares off-instrument cells instead of skipping them.
ALLOW_FLAG = "--allow-off-instrument"
ALLOW_HELP = (
    "compare the cells of episodes recorded off the paper's instrument with the paper's reference anyway "
    f"(default: SKIP them); their lines are marked {OFF_INSTRUMENT}"
)
#: How `off_paper` reasons are joined in an episode row (`_harness.readout.base_row`).
REASON_SEPARATOR = "; "
#: What the episodes are off, as the banner and the SKIP lines name it (a check against another paper
#: reference, e.g. personal_assistant's `context_files` rerun, names that reference's instead).
PAPER_INSTRUMENT = "the paper's instrument"

#: `skip`: the reference is the paper's and the off cells are skipped; `marked`: compared, lines marked
#: (`--allow-off-instrument`); `info`: the reference is not the paper's, so the cells are compared as they are.
#: (`None` to `banner`: the caller's own note says what happens to them.)
Mode = Literal["skip", "marked", "info"]
#: The harness behind the api_key and clinic references (`world/config.json` `harness`).
PAPER_HARNESS = "sim"
#: The marker on the banner above the verdicts of a run on another harness.
HARNESS = "HARNESS"
T = TypeVar("T")


def recorded_reasons(value: Any) -> tuple[str, ...]:
    """An `off_paper` record (a config's list, or a row's `"; "`-joined string) as a tuple of reasons."""
    if isinstance(value, str):
        return tuple(r for r in value.split(REASON_SEPARATOR) if r)
    if isinstance(value, (list, tuple)):
        items = cast(Sequence[object], value)
        return tuple(str(r) for r in items if r)
    return ()


def sim_reasons(row: Mapping[str, Any]) -> tuple[str, ...]:
    """Why a simulated-harness episode row ran off the paper's instrument (empty: on it, or unrecorded)."""
    reasons = recorded_reasons(row.get("off_paper"))
    if not reasons and row.get("on_paper_instrument") is False:
        return ("recorded off the paper's instrument",)
    return reasons


def physics(row: Mapping[str, Any]) -> str:
    """A pool's physics record: the scheduler instrument plus every recorded off-paper reason.

    Two episodes pool only when this is equal: the same instrument, and the same deviations from the paper's (the
    reasons name the setting and its value, e.g. `TARGET_REASONING=high`, `max_turns 50`).
    """
    instrument = str(row.get("instrument"))
    reasons = sim_reasons(row)
    return (
        instrument
        if not reasons
        else f"{instrument} [off paper: {REASON_SEPARATOR.join(reasons)}]"
    )


def split(
    rows: Iterable[T], reasons_of: Callable[[T], Sequence[str]]
) -> tuple[list[T], list[T], Counter[str]]:
    """`(on rows, off rows, episodes per reason)`: the rows on the instrument and those off it."""
    on: list[T] = []
    off: list[T] = []
    reasons: Counter[str] = Counter()
    for row in rows:
        found = reasons_of(row)
        (off if found else on).append(row)
        reasons.update(found)
    return on, off, reasons


def banner(
    reasons: Mapping[str, int],
    off: int,
    total: int,
    mode: Mode | None,
    note: str = "",
    instrument: str = PAPER_INSTRUMENT,
) -> list[str]:
    """The OFF-INSTRUMENT banner `check.py` prints above its verdicts; empty when no episode is off."""
    if not off:
        return []
    lines = [f"{OFF_INSTRUMENT}: {off} of {total} episode(s) ran off {instrument}:"]
    lines += [
        f"  {n:>6}  {reason}"
        for reason, n in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    if mode == "skip":
        lines.append(
            "  Their cells are SKIPped: a PASS or MISS against the paper's numbers would not be a reproduction. "
            f"{ALLOW_FLAG} compares them anyway (each such line is marked {OFF_INSTRUMENT})."
        )
    elif mode == "marked":
        lines.append(
            f"  {ALLOW_FLAG}: their cells are compared and each such line is marked {OFF_INSTRUMENT}; none of "
            "those verdicts is a reproduction of the paper."
        )
    elif mode == "info":
        lines.append(
            "  The reference is not the paper's, so they are compared as they are: check that the reference ran "
            "their instrument."
        )
    if note:
        lines.append(f"  {note}")
    return lines


def harness_banner(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """The note `check.py` prints above verdicts against a simulated-harness reference for pi-harness episodes.

    Empty when every episode ran the reference's harness. A runs root holds one harness
    (`_harness.readout.single_harness`), so the note covers the whole run.
    """
    other = sum(1 for r in rows if str(r.get("harness") or "pi") != PAPER_HARNESS)
    if not other:
        return []
    return [
        f"{HARNESS}: {other} of {len(rows)} episode(s) ran the real-pi harness, a different instrument from the "
        "paper's simulated harness.",
        "  The verdicts below compare that instrument with the paper's numbers: a PASS is not a reproduction, and "
        "a MISS is a flag to read the episodes, not a failed one.",
    ]


def skip_lines(
    off: Iterable[T],
    label_of: Callable[[T], str],
    reasons_of: Callable[[T], Sequence[str]],
    instrument: str = PAPER_INSTRUMENT,
) -> list[str]:
    """One `SKIP` line per cell (label) of the off-instrument episodes, naming the reasons, in label order."""
    cells: dict[str, set[str]] = {}
    for row in off:
        cells.setdefault(label_of(row), set()).update(reasons_of(row))
    return [
        f"SKIP {label}: ran off {instrument} ({REASON_SEPARATOR.join(sorted(reasons))}); "
        f"{ALLOW_FLAG} compares it anyway"
        for label, reasons in sorted(cells.items())
    ]


def mark(line: str) -> str:
    """A compared line of an off-instrument cell, marked so it never reads as a reproduction."""
    return f"{OFF_INSTRUMENT} {line}"


def gated_verdicts(
    rows: Sequence[T],
    reasons_of: Callable[[T], Sequence[str]],
    compare: Callable[[list[T]], list[tuple[str, str]]],
    label_of: Callable[[T], str],
    *,
    paper: bool,
    allow: bool,
    note: str = "",
) -> tuple[list[str], list[tuple[str, str]]]:
    """`(banner, verdicts)` of a check whose `compare` maps episode rows to `(status, line)` verdicts.

    Against the paper's reference (`paper`) the off-instrument episodes' cells are SKIPped, or compared and marked
    when `allow`; against any other reference every episode is compared as it is (the banner still names the
    reasons). A pool never mixes on- and off-instrument episodes (`physics`), so comparing the two groups apart
    leaves every on-instrument cell and pool exactly as before.
    """
    on, off, reasons = split(rows, reasons_of)
    mode: Mode = ("marked" if allow else "skip") if paper else "info"
    lines = banner(reasons, len(off), len(rows), mode, note)
    if not off or not paper:
        return lines, compare(list(rows))
    if allow:
        return lines, compare(on) + [(s, mark(line)) for s, line in compare(off)]
    return lines, compare(on) + [
        ("SKIP", line) for line in skip_lines(off, label_of, reasons_of)
    ]
