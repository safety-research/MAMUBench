"""The paper's clinic episodes of record: which episode every clinic number reads, and on which instrument.

`expected/episodes_of_record.csv.gz` holds one row per episode (6,428) of the three frozen sets the paper's
clinic figures and tables read, with the episode's contest counts on the paper's metric:

- `corpus_of_record`: the coordinator and the peer-to-peer team, five models (4,388 episodes; the paper's corpus
  of record).
  Episodes 1-20 of every scenario, except the Qwen3.8-max cells (low reasoning: coordinator 167 + 149,
  team 80 + 152 episodes, 5-20 per scenario) and three GPT-5.6-sol plan-extra team episodes (kept, flagged).
  The coordinator plays `hero`, the team `standard`.
- `silent_e1_5`: the silent team, five models x 24 scenarios x episodes 1-5, all `standard` (600; the router's
  quarantined-desk wake, `environment/router.py`, is part of the setting).
- `mitigations_e1_10`: s1, s2, s3 on the team, Claude Opus 5 and Claude Sonnet 5 x 24 scenarios x episodes
  1-10, all `standard` (1,440). Their controls
  (the coordinator and the team, episodes 1-10) are the corpus-of-record rows above.

Columns: `model` (the release's id), `formation`, `mitigation`, `scenario` (board id), `epoch`, `instrument`
(`hero` / `standard`: the knob set the release plays the episode on, its cell's own instrument), `set`, `source`
(a provenance label: how the episode entered its set), `n_contests`, `met`, `joint` (`joint_success_upper`
summed: the paper's metric) and `plan_extra`. `expected/build_reference.py` derives `expected/reference.json` from
this file (which was extracted from the paper's frozen per-contest tables).

Jobs files (`--jobs-file`, see `eval/_jobs.py`) carry no model, so they are written one per (model, formation,
arm), each with the `eval/clinic/run.py` command that plays it. Without `--mitigation` only the formation itself
is selected (the control arm); `--mitigation s1|s2|s3` selects one arm and `all` every arm:

    python eval/clinic/record.py --model claude-opus-5 --formation team --out-dir jobs/
    python eval/clinic/record.py --model qwen3.8-max --formation coordinator --out-dir jobs/
    python eval/clinic/record.py --model claude-sonnet-5 --formation team --mitigation s3 --out-dir jobs/
"""

from __future__ import annotations

import argparse
import csv
import functools
import gzip
import io
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import bootstrap  # noqa: E402

bootstrap()

from _jobs import JobSpec, write_jobs_file  # noqa: E402
from _mitigations import NONE  # noqa: E402

from clinic.metric import PAPER_MODELS, Morning, Scheme  # noqa: E402

EVAL_ROOT = Path(__file__).resolve().parent
RECORD_PATH = EVAL_ROOT / "expected" / "episodes_of_record.csv.gz"
#: The three frozen sets, and the formations / arms each holds.
SETS: dict[str, str] = {
    "corpus_of_record": "coordinator and peer-to-peer team, five models, episodes 1-20 (Qwen: its low-reasoning subset)",
    "silent_e1_5": "silent team, five models, episodes 1-5",
    "mitigations_e1_10": "s1, s2, s3 on the peer-to-peer team, Claude Opus 5 and Claude Sonnet 5, episodes 1-10",
}
#: The set whose rows are the reference for a (formation, arm): the arms' own set, the silent set, else the corpus.
MITIGATION_SET = "mitigations_e1_10"
#: `--mitigation all`: every arm (the control included).
ALL_ARMS = "all"


@dataclass(frozen=True)
class RecordEpisode:
    """One episode of record (one row of `episodes_of_record.csv.gz`)."""

    model: str
    formation: str
    mitigation: str
    scenario: str
    epoch: int
    instrument: str
    set: str
    source: str
    n_contests: int
    met: int
    joint: int
    plan_extra: int

    @property
    def morning(self) -> Morning:
        """The episode's counts as the metric reads them."""
        return Morning(
            epoch=self.epoch, joint=self.joint, met=self.met, n=self.n_contests
        )

    @property
    def key(self) -> tuple[str, str, str, str, int]:
        """`(model, formation, mitigation, scenario, epoch)`: unique within a set."""
        return (self.model, self.formation, self.mitigation, self.scenario, self.epoch)


def set_for(formation: str, mitigation: str) -> str:
    """The set holding the paper's episodes of one (formation, arm)."""
    if mitigation != NONE:
        return MITIGATION_SET
    if formation == "team_silent":
        return "silent_e1_5"
    return "corpus_of_record"


def parse(text: str) -> list[RecordEpisode]:
    """The rows of an episodes-of-record CSV text."""
    out: list[RecordEpisode] = []
    for raw in csv.DictReader(io.StringIO(text)):
        out.append(
            RecordEpisode(
                model=raw["model"],
                formation=raw["formation"],
                mitigation=raw["mitigation"],
                scenario=raw["scenario"],
                epoch=int(raw["epoch"]),
                instrument=raw["instrument"],
                set=raw["set"],
                source=raw["source"],
                n_contests=int(raw["n_contests"]),
                met=int(raw["met"]),
                joint=int(raw["joint"]),
                plan_extra=int(raw["plan_extra"]),
            )
        )
    return out


@functools.lru_cache(maxsize=4)
def _load_cached(path: str) -> tuple[RecordEpisode, ...]:
    with gzip.open(path, "rt", newline="") as handle:
        return tuple(parse(handle.read()))


def load(path: Path = RECORD_PATH) -> list[RecordEpisode]:
    """Every episode of record (cached per path)."""
    return list(_load_cached(str(path)))


def sort_key(r: RecordEpisode) -> tuple[object, ...]:
    """Sets in `SETS` order, the paper's model order, then formation, arm, scenario, epoch."""
    model = (
        PAPER_MODELS.index(r.model) if r.model in PAPER_MODELS else len(PAPER_MODELS)
    )
    return (
        list(SETS).index(r.set),
        model,
        r.formation,
        r.mitigation,
        r.scenario,
        r.epoch,
    )


def select(
    rows: list[RecordEpisode],
    *,
    model: str | None = None,
    formation: str | None = None,
    mitigation: str | None = None,
    set_name: str | None = None,
) -> list[RecordEpisode]:
    """The rows matching every filter given (`mitigation=None` keeps every arm)."""
    return [
        r
        for r in rows
        if (model is None or r.model == model)
        and (formation is None or r.formation == formation)
        and (mitigation is None or r.mitigation == mitigation)
        and (set_name is None or r.set == set_name)
    ]


#: `(set, model, formation, arm)`: one group of the reference.
Group = tuple[str, str, str, str]
#: The models the mitigation wave ran (their controls are the corpus episodes 1-10 of these two).
MITIGATION_MODELS: tuple[str, ...] = ("claude-opus-5", "claude-sonnet-5")
MITIGATION_EPOCHS = 10


def groups(rows: list[RecordEpisode]) -> dict[Group, list[RecordEpisode]]:
    """The reference's groups: every set as frozen, plus the arms' controls (corpus episodes 1-10, Opus and Sonnet).

    The mitigation figure reads its coordinator and its team-with-nothing-added on the arms' own episodes
    (the paper's analysis scripts, supplementary material), so those rows are grouped under `mitigations_e1_10` too.
    """
    out: dict[Group, list[RecordEpisode]] = defaultdict(list)
    for r in rows:
        out[(r.set, r.model, r.formation, r.mitigation)].append(r)
        if (
            r.set == "corpus_of_record"
            and r.epoch <= MITIGATION_EPOCHS
            and r.model in MITIGATION_MODELS
        ):
            out[(MITIGATION_SET, r.model, r.formation, NONE)].append(r)
    return dict(out)


def scheme_of_set(set_name: str) -> Scheme:
    """The paper script that bootstraps a set (`clinic.metric.SCHEMES`)."""
    if set_name == "corpus_of_record":
        return "corpus"
    if set_name == "silent_e1_5":
        return "silent"
    return "mitigation"


def membership(rows: list[RecordEpisode]) -> set[tuple[str, str, str, str, int]]:
    """The `(model, formation, mitigation, scenario, epoch)` keys of `rows` (for `report.py --episodes-of-record`)."""
    return {r.key for r in rows}


def own_instrument(formation: str, mitigation: str) -> str:
    """The instrument the release plays a (formation, arm) on: the arm's, else the formation's."""
    from clinic import cells

    return (
        cells.MITIGATION_INSTRUMENT
        if mitigation != NONE
        else cells.PAPER_INSTRUMENT[formation]
    )


def jobs_by_cell(
    rows: list[RecordEpisode],
) -> dict[tuple[str, str, str], list[JobSpec]]:
    """`(model, formation, arm) -> the jobs` for rows of one set (a jobs file names no model).

    Raises:
        ValueError: A row whose instrument is not the one the release plays for its (formation, arm).
    """
    out: dict[tuple[str, str, str], list[JobSpec]] = defaultdict(list)
    for r in sorted(rows, key=sort_key):
        own = own_instrument(r.formation, r.mitigation)
        if r.instrument != own:
            raise ValueError(
                f"{r.formation}/{r.mitigation}: instrument {r.instrument!r} is not the one the release plays "
                f"({own!r})"
            )
        out[(r.model, r.formation, r.mitigation)].append(
            JobSpec(
                scenario=r.scenario,
                formation=r.formation,
                epoch=r.epoch,
                mitigation=r.mitigation,
            )
        )
    return dict(out)


#: The `--model` a record model id is launched with (the record keeps the id's last path part, as the reports do).
CLI_MODEL: dict[str, str] = {"qwen3.8-max": "qwen/qwen3.8-max"}


def cli_model(model: str) -> str:
    """`qwen3.8-max` -> `qwen/qwen3.8-max` (OpenRouter); every other paper model id is its own `--model`."""
    return CLI_MODEL.get(model, model)


def run_command(model: str, jobs_file: Path, runs_root: str) -> str:
    """The `run.py` invocation that plays one jobs file (each cell on its own instrument)."""
    return (
        f"python eval/clinic/run.py --jobs-file {jobs_file} --model {cli_model(model)}"
        f" --runs-root {runs_root}"
    )


def resolve_mitigation(mitigation: str | None, set_name: str | None) -> str | None:
    """The arm filter `select` gets: the control arm by default, every arm for `all` or the arms' own set."""
    if mitigation == ALL_ARMS or (mitigation is None and set_name == MITIGATION_SET):
        return None
    return NONE if mitigation is None else mitigation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--model",
        help="a release model id (claude-opus-5, gpt-5.6-sol, qwen3.8-max, ...)",
    )
    parser.add_argument("--formation", choices=("coordinator", "team", "team_silent"))
    parser.add_argument(
        "--mitigation",
        default=None,
        help=(
            "the arm: none (the formation itself, the default), s1, s2, s3, or all (every arm); "
            f"--set {MITIGATION_SET} alone selects every arm"
        ),
    )
    parser.add_argument("--set", dest="set_name", choices=tuple(SETS), default=None)
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="write the jobs files here"
    )
    parser.add_argument(
        "--runs-root",
        default="eval/clinic/runs/results",
        help="the runs root of the printed commands",
    )
    args = parser.parse_args(argv)
    mitigation = resolve_mitigation(args.mitigation, args.set_name)
    rows = select(
        load(),
        model=None if args.model is None else str(args.model).rsplit("/", 1)[-1],
        formation=args.formation,
        mitigation=mitigation,
        set_name=args.set_name,
    )
    print(
        "arms: "
        + (
            "every arm"
            if mitigation is None
            else "the formation itself (the control arm; --mitigation s1|s2|s3|all for the arms)"
            if mitigation == NONE
            else mitigation
        )
    )
    if not rows:
        print("no episode of record matches")
        return 1
    counts = Counter(
        (r.set, r.model, r.formation, r.mitigation, r.instrument) for r in rows
    )
    for (set_name, model, formation, arm, instrument), n in sorted(counts.items()):
        print(
            f"{set_name:18} {model:16} {formation:12} {arm:5} {instrument:10} {n:5} episode(s)"
        )
    if args.out_dir is not None:
        for (model, formation, arm), jobs in jobs_by_cell(rows).items():
            stem = "__".join(
                p for p in (model, formation, arm if arm != NONE else "") if p
            )
            path = args.out_dir / f"{stem}.csv"
            write_jobs_file(path, jobs)
            command = run_command(model, path, args.runs_root)
            print(f"-> {path} ({len(jobs)} jobs)\n   {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
