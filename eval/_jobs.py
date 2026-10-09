"""`--jobs-file`: a CSV of explicit episodes instead of a (scenario x formation x epoch) matrix.

Used where the episodes of record are a list, not a grid: the personal-assistant mitigation draws (a
re-run of previously failed team episodes, an explicit (scenario, epoch) list) and the clinic episodes of
record. The same file drives a local run (`run.py <env> --backend local --jobs-file F`, or the eval's own
`run.py --jobs-file F`) and a Modal launch (`modal_app.py::main --jobs-file F`, read on the launching
machine), and `--print-info` prints the resolved episodes.

Format: a header row, then one episode per row.

    scenario,formation,epoch,mitigation
    kestrel_quiz_booth,team,7,guard
    kestrel_quiz_booth,team,12,
    # a comment line (first cell starts with '#') and blank lines are skipped

- `scenario`, `formation`, `epoch` are required; `epoch` is a positive integer (the world seed, as with
  `--epoch0`); `scenario` is the eval's own id (clinic: the board id).
- `mitigation` is optional; an empty cell (or no column) means the invocation's `--mitigation` (default
  `none`).
- No other column is accepted and an episode may appear only once (a typo'd header or a pasted duplicate
  fails before anything runs). Registry checks (does the scenario exist, does the formation run on it,
  does the arm apply to the formation) are the eval runner's, which knows its registry.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from _mitigations import NONE

REQUIRED_COLUMNS: tuple[str, ...] = ("scenario", "formation", "epoch")
OPTIONAL_COLUMNS: tuple[str, ...] = ("mitigation",)


@dataclass(frozen=True)
class JobSpec:
    """One explicit episode of a jobs file."""

    scenario: str
    formation: str
    epoch: int
    mitigation: str = NONE

    @property
    def label(self) -> str:
        """`scenario/formation/eN` (+ `/mitigation` for an arm)."""
        arm = "" if self.mitigation == NONE else f"/{self.mitigation}"
        return f"{self.scenario}/{self.formation}/e{self.epoch}{arm}"


class JobsFileError(ValueError):
    """A jobs file that cannot be read as a list of episodes (the message names the file and line)."""


def read_jobs_file(path: Path, *, default_mitigation: str = NONE) -> list[JobSpec]:
    """Every episode of a jobs file, in file order.

    Args:
        path: The CSV (see the module docstring).
        default_mitigation: The arm of a row whose `mitigation` cell is empty or absent.

    Raises:
        JobsFileError: A missing file, a bad header, a bad epoch, an empty required cell, a duplicate
            episode, or no episode at all.
    """
    if not path.is_file():
        raise JobsFileError(f"--jobs-file {path}: no such file")
    kept = [
        (number, line)
        for number, line in enumerate(path.read_text().splitlines(), start=1)
        if line.strip() and not line.lstrip().startswith("#")
    ]
    lines = [line for _, line in kept]
    if not lines:
        raise JobsFileError(f"--jobs-file {path}: no header and no episode")
    reader = csv.DictReader(lines)
    header = [name.strip() for name in reader.fieldnames or []]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    unknown = [c for c in header if c not in (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)]
    if missing or unknown:
        raise JobsFileError(
            f"--jobs-file {path}: header {header} must name {', '.join(REQUIRED_COLUMNS)} "
            f"(+ optional {', '.join(OPTIONAL_COLUMNS)})"
            + (f"; missing {missing}" if missing else "")
            + (f"; unknown {unknown}" if unknown else "")
        )
    reader.fieldnames = header
    jobs: list[JobSpec] = []
    seen: dict[JobSpec, int] = {}
    for index, raw in enumerate(reader, start=1):
        number = kept[min(index, len(kept) - 1)][0]
        if None in raw:
            raise JobsFileError(
                f"--jobs-file {path} line {number}: more cells than the header"
            )
        row = {k: (v or "").strip() for k, v in raw.items()}
        empty = [c for c in REQUIRED_COLUMNS if not row.get(c)]
        if empty:
            raise JobsFileError(
                f"--jobs-file {path} line {number}: empty {', '.join(empty)}"
            )
        try:
            epoch = int(row["epoch"])
        except ValueError:
            epoch = 0
        if epoch < 1:
            raise JobsFileError(
                f"--jobs-file {path} line {number}: epoch {row['epoch']!r} is not a positive integer"
            )
        job = JobSpec(
            scenario=row["scenario"],
            formation=row["formation"],
            epoch=epoch,
            mitigation=row.get("mitigation") or default_mitigation,
        )
        if job in seen:
            raise JobsFileError(
                f"--jobs-file {path} line {number}: {job.label} repeats line {seen[job]}"
            )
        seen[job] = number
        jobs.append(job)
    if not jobs:
        raise JobsFileError(f"--jobs-file {path}: a header but no episode")
    return jobs


def write_jobs_file(path: Path, jobs: list[JobSpec]) -> None:
    """Write `jobs` in the format `read_jobs_file` reads (tests and tools build files with it)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS])
        for job in jobs:
            writer.writerow([job.scenario, job.formation, job.epoch, job.mitigation])
