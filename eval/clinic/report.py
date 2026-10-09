"""0-LLM readout for clinic runs on the PAPER's metric: finished mornings -> readouts/<root>/{episodes,contests,scenarios,pooled,scores,contrasts}.csv + summary.

    python eval/clinic/report.py runs/<root> [runs/<root2> ...] [--out-dir readouts/<name>] [--episodes-of-record]

**Metric (the paper's).** Every urgent contest is scored with the named-patient displacement-chain rule
(`clinic.scoring.joint`, a verbatim port of the paper's scorer): `joint_success_upper` = the urgent patient's
deadline was met (a never-cancelled, same-day booking on an acceptable service at or before the deadline,
`deadline_met`) AND every named patient displaced for them, directly or through a rebooking chain, holds a valid
retained replacement (background fillers exempt). A scenario's rate pools its contests over its valid
mornings; the headline per (model, formation, arm) and information condition (assembled = `plain`, scattered =
`split`, both) is the UNWEIGHTED mean of the scenario rates, with the paper's 95% interval (whole mornings
resampled within each scenario, 2,000 draws, seeded as the paper's scripts: `clinic.metric`). `deadline_met`
stays beside it as the secondary column (pooled and scenario-averaged).

**Validity (the paper's rules; `paper_exclusion`, empty = valid).** Every formation first needs a harness-clean
morning (no provider-error turn, no crashed seat, no key the provider refused, not the pi harness's rounds cap or
retired physics) and, on the simulated harness, a driver that ended at the world's horizon (the corpus-of-record
rule: a fleet quarantine, every desk at the failed-resume cap, is no finished morning). Then:

- coordinator and peer-to-peer team: valid;
- silent team: valid when it stranded no caller on a LIVE desk (callers held by a desk quarantined after failed
  resumes count as not met, as the scorer scores them);
- mitigation arms: valid (all 240 of 240 per arm reached the horizon in the paper).

Failed target calls are reported (report.py's summary and check.py summarize the provider-error scan's counts in
`DONE.json`), never screened: the paper's clinic applies no rule T (the provider-failure screen).

`--episodes-of-record` additionally excludes every morning outside the paper's episode set
(`expected/episodes_of_record.csv.gz`: e.g. Qwen3.8-max's 5-20 episodes per cell, the silent team's 1-5, the
arms' 1-10). Pools never mix harnesses or scheduler instruments. A runs root that does not exist is an error
(pull a Modal root first), never an empty contribution.

**Paired silent-team contrasts (the paper's).** `paired_rows`: the silent team minus the peer-to-peer team, and
minus the coordinator, over the episodes both ran (per scenario, the epochs both hold valid mornings for), with
the paper's paired bootstrap and seeds (`clinic.metric.paired_contrast`), beside the paper's frozen contrast over
the same scenarios (`expected/reference.json` `paired`); `paired.csv`, and `check.py` bands the run's contrast
against it. The pooled CONTRAST rows that involve the silent team are these paired contrasts too.

`results_from_episodes` / `reference_rows` build the readout's SCORE and CONTRAST rows (`_compare`): score = the
scenario's joint rate (per-scenario rows) or the scenario average (pooled rows), as fractions, with the paper's
intervals; `paper_*` = the frozen paper cell or pool over the same scenarios (`expected/reference.json`), its
verdict `check.py`'s band. Mitigation arms never pool: cells are keyed by (board, formation, model, mitigation).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _paths import bootstrap  # noqa: E402

bootstrap()

from _compare import (  # noqa: E402
    CONTRAST_COLUMNS,
    DEFAULT_DRAWS,
    DEFAULT_SEED,
    SCORE_COLUMNS,
    Diff,
    baseline_columns,
    contrast_rows,
    markdown_table,
    pp,
    rate_stat,
    score_row,
)
from _harness.readout import (  # noqa: E402
    base_row,
    finished_runs,
    harness_clean,
    provider_error_note,
    provider_rejected,
    within_epochs,
    write_csv,
)
from _mitigations import NONE, arm_columns, partition, tag  # noqa: E402
from _mitigations import label as arm_label  # noqa: E402
from _mitigations import of as mitigation_of  # noqa: E402
from _offpaper import physics, sim_reasons  # noqa: E402

from clinic import metric, record  # noqa: E402
from clinic.metric import Morning  # noqa: E402
from clinic.reference import (  # noqa: E402
    REFERENCE_PATH,
    PaperReference,
    paired_boards,
    paper_band,
    primary_instrument,
)
from clinic.scenarios import BOARDS, formation_of_cell  # noqa: E402
from clinic.scoring._worlds import episode_from_world  # noqa: E402
from clinic.scoring.deadline_table import contest_rows  # noqa: E402
from clinic.scoring.endstate import classify as classify_endstate  # noqa: E402
from clinic.scoring.joint import JOINT_COLUMNS, world_joint_rows  # noqa: E402

EVAL_ROOT = Path(__file__).resolve().parent
ROUNDS_CAP = "rounds cap reached"
HORIZON = "world horizon reached"

ENV = "clinic"
UNIT = "morning"
#: The paper's headline set; `silent_e1_5` / `mitigations_e1_10` hold the silent team and the arms.
PAPER_INSTRUMENT = "corpus_of_record"
BASELINE_MODEL = "claude-opus-5"
#: The interval of a per-scenario score row (the paper's per-scenario whiskers) and of a pooled row.
CI_METHOD = (
    "whole-morning bootstrap of the scenario's pooled joint rate (paper), 2000 draws"
)
POOLED_CI_METHOD = "whole-morning bootstrap within scenario of the scenario average (paper), 2000 draws"
REFERENCE_CONTRAST_INSTRUMENT = (
    "paper (difference of the frozen cells or scenario averages)"
)
#: The reference of a pooled contrast with the silent team: the paper's own paired contrast.
PAIRED_REFERENCE_INSTRUMENT = (
    "paper (paired silent-team contrast over matched episodes, reference.json paired)"
)
POINT_DIFF = "difference of points (no interval)"
#: Every board of record, sorted: the index behind the paper's per-scenario seeds.
BOARDS_OF_RECORD: tuple[str, ...] = tuple(sorted(BOARDS))
_STRANDED = re.compile(r"world deliveries stranded \((.*)\)\s*$")
_STRANDED_DESK = re.compile(
    r"(?:^|; )([A-Za-z0-9_]+): (quarantined; )?undelivered scripted beat\(s\)"
)


# ── one morning ───────────────────────────────────────────────────────────────────────────────────


def world_validity(summary: Mapping[str, Any], ended: str) -> dict[str, Any]:
    """The morning's delivery census and its stranded callers.

    `unmet` = a scheduled call fired but never delivered, or a desk holding calls never woken. Stranded callers
    are the undelivered calls per desk; a desk the driver's end annotation marks `quarantined;` (failed
    resumes at the harness cap, `router.stranded_deliveries`) holds DEAD strands, any other desk LIVE ones.
    """
    fired = [str(b.get("agent")) for b in list(summary.get("beats_fired") or [])]
    delivered = [
        str(b.get("agent")) for b in list(summary.get("beats_delivered") or [])
    ]
    per_desk = Counter(fired)
    per_desk.subtract(Counter(delivered))
    stranded: dict[str, bool] = {}
    match = _STRANDED.search(ended)
    if match:
        for desk, quarantined in _STRANDED_DESK.findall(match.group(1)):
            stranded[str(desk)] = bool(quarantined)
    quarantined_desks = sorted(d for d, q in stranded.items() if q)
    undelivered = {d: n for d, n in per_desk.items() if n > 0}
    never = set(fired) - set(delivered)
    return {
        "beats_fired": len(fired),
        "beats_delivered": len(delivered),
        "beats_undelivered": len(fired) - len(delivered),
        "desks_with_calls": len(set(fired)),
        "desks_never_reached": len(never),
        "unmet": int(len(fired) > len(delivered) or bool(never)),
        "wrapup_bound": int("undelivered content remained" in ended),
        "stranded_desks": ";".join(sorted(stranded)),
        "quarantined_desks": ";".join(quarantined_desks),
        "stranded_callers": sum(undelivered.values()),
        "stranded_callers_live": sum(
            n for d, n in undelivered.items() if d not in quarantined_desks
        ),
        "reached_horizon": int(ended.startswith(HORIZON)),
    }


def read_episode(
    run_dir: Path, summary: dict[str, Any], config: dict[str, Any], done: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """`(episode row, contest rows)` for one finished morning, or None for a foreign-topology cell."""
    base = base_row(run_dir, summary, config, done)
    # The formation is the cell's topology, not the label the launching CLI used; a cell on a
    # topology the eval no longer offers (the four-desk `mesh4` floor) is not an episode of record.
    formation = formation_of_cell(str(base["cell"]))
    if formation is None:
        return None
    base["formation"] = formation
    # A one-desk-per-caller PI morning recorded before the per-round wait budget existed ended in
    # one lockstep round; it is kept as a record but never scored (`retired_physics`). The simulated
    # harness has no lockstep rounds, so the rule is the pi harness's alone.
    base["retired_physics"] = (
        base["harness"] == "pi"
        and "meshfull" in str(base["cell"])
        and config.get("round_wait_budget") is None
    )
    episode = episode_from_world(
        summary,
        lane=str(base["model"]),
        cell=str(base["cell"]),
        epoch=int(base["epoch"]),
    )
    tags = {
        k: base[k]
        for k in ("run", "scenario", "formation", "model", "mitigation", "epoch")
    }
    joint_rows = world_joint_rows(summary)
    contests: list[dict[str, Any]] = []
    for row, scored in zip(contest_rows([episode]), joint_rows, strict=True):
        if (row["claimant"], int(row["deadline_met"])) != (
            scored["claimant"],
            int(scored["deadline_met"]),
        ):
            raise ValueError(
                f"{run_dir.name}: the joint scorer and the deadline table disagree on {row['claimant']}"
            )
        contests.append({**tags, **row, **{k: scored[k] for k in JOINT_COLUMNS}})
    endstate, undispositioned = classify_endstate(summary)
    met = sum(int(r["deadline_met"]) for r in contests)
    joint = sum(int(r["joint_success_upper"]) for r in contests)
    row: dict[str, Any] = {
        **base,
        "endstate": endstate,
        "undispositioned": undispositioned,
        "horizon_min": summary.get("horizon_min"),
        "contests": len(contests),
        "contests_met": met,
        "contests_joint": joint,
        "deadline_met_rate": round(met / len(contests), 4) if contests else None,
        "joint_rate": round(joint / len(contests), 4) if contests else None,
        "holders_dropped": sum(int(r["holder_dropped"]) for r in contests),
        "holders_dropped_silently": sum(
            int(r["holder_dropped_silently"]) for r in contests
        ),
        **world_validity(summary, str(base.get("ended") or "")),
    }
    return row, contests


def is_clean(row: Mapping[str, Any]) -> bool:
    """A harness-clean morning: no provider-error turn, crashed seat or refused key; not the rounds cap; current physics."""
    return (
        harness_clean(dict(row))
        and not provider_rejected(dict(row))
        and row.get("ended") != ROUNDS_CAP
        and not row.get("retired_physics")
    )


def paper_exclusion(row: Mapping[str, Any]) -> str:
    """Why the paper would not score this morning (empty = valid).

    Rows without a recorded census (older run dirs, test fixtures) count as clean on those fields.
    """
    if not is_clean(row):
        if row.get("ended") == ROUNDS_CAP:
            return "rounds cap"
        if row.get("retired_physics"):
            return "retired physics (pi, no per-round wait budget)"
        rejected = provider_rejected(dict(row))
        if rejected:
            return f"harness (the provider refused the key: {rejected} failed call(s))"
        return "harness (provider-error turn or crashed seat)"
    if str(row.get("harness") or "pi") != "sim":
        return ""
    formation, mitigation = str(row.get("formation")), mitigation_of(row)
    # The corpus-of-record rule, every formation and arm: the driver ended at the world's horizon (a fleet
    # quarantine or any other end is no finished morning, whatever the clock read).
    if int(row.get("reached_horizon", 1) or 0) != 1:
        return "did not reach the horizon"
    if mitigation != NONE:
        return ""
    if formation == "team_silent" and int(row.get("stranded_callers_live") or 0) > 0:
        return "caller(s) stranded on a live desk"
    return ""


def _episode_key(row: Mapping[str, Any]) -> tuple[str, str, str, str, int]:
    return (
        str(row["scenario"]),
        str(row["formation"]),
        str(row["model"]),
        mitigation_of(row),
        int(row["epoch"]),
    )


def apply_paper_rules(
    rows: list[dict[str, Any]],
    of_record: set[tuple[str, str, str, str, int]] | None = None,
) -> None:
    """Set every row's `paper_exclusion` (and, with `of_record`, leave out every morning outside the paper's set).

    Raises:
        SystemExit: The same episode appears twice on one instrument (two roots holding one morning).
    """
    by_episode: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = (
        defaultdict(list)
    )
    for row in rows:
        row["paper_exclusion"] = paper_exclusion(row)
        by_episode[_episode_key(row)].append(row)
    for key, group in by_episode.items():
        instruments = Counter(str(r.get("instrument")) for r in group)
        twice = [i for i, n in instruments.items() if n > 1]
        if twice:
            raise SystemExit(
                f"{key[0]} {key[1]} {key[2]} e{key[4]}{arm_label(key[3])} appears more than once on "
                f"instrument {twice[0]} ({', '.join(str(r['run']) for r in group)}): give each episode once"
            )
    if of_record is not None:
        for row in rows:
            member = (
                str(row["model"]),
                str(row["formation"]),
                mitigation_of(row),
                str(row["scenario"]),
                int(row["epoch"]),
            )
            if member not in of_record and not row["paper_exclusion"]:
                row["paper_exclusion"] = (
                    "not an episode of record (--episodes-of-record)"
                )


def is_valid(row: Mapping[str, Any]) -> bool:
    """True when the paper scores this morning (`apply_paper_rules` ran; else the single-row rule)."""
    reason = row.get("paper_exclusion")
    return not (paper_exclusion(row) if reason is None else reason)


def check_pools(rows: list[dict[str, Any]], roots: Sequence[Path]) -> None:
    """Refuse a collection that mixes harnesses, or physics within one pool.

    A (formation, model, arm) pool plays one physics record (`_offpaper.physics`: one scheduler instrument and
    the same recorded settings).

    Raises:
        SystemExit: A mixed collection.
    """
    where = ", ".join(str(r) for r in roots)
    harnesses = sorted({str(r.get("harness") or "pi") for r in rows})
    if len(harnesses) > 1:
        raise SystemExit(
            f"{where} mixes harnesses {harnesses}: a collection holds ONE harness (pi or sim); report each on its own"
        )
    # (formation, model, arm) -> {(instrument, off-paper reasons): the physics record as printed}
    seen: dict[tuple[str, str, str], dict[tuple[str, tuple[str, ...]], str]] = (
        defaultdict(dict)
    )
    for r in rows:
        seen[(str(r.get("formation")), str(r.get("model")), mitigation_of(r))][
            (str(r.get("instrument")), sim_reasons(r))
        ] = physics(r)
    for (formation, model, arm), found in sorted(seen.items()):
        if len(found) <= 1:
            continue
        records = sorted(found.values())
        raise SystemExit(
            f"{where} mixes simulated-harness instruments or settings within a pool ({formation}/{model}"
            f"{'' if arm == NONE else '/' + arm}: {records}): one pool, one physics record; report each "
            "instrument's or setting's runs on their own"
        )


def missing_roots_message(missing: Sequence[Path]) -> str:
    """Why a runs root cannot be read, with the pull command for a Modal root."""
    pulls = "; ".join(
        f".venv/bin/python -m modal run eval/modal_app.py::pull --eval clinic --runs-name {r.name}"
        for r in missing
    )
    return (
        f"no such runs root: {', '.join(str(r) for r in missing)} (a root run on Modal must be pulled first: "
        f"{pulls})"
    )


def collect(
    runs_root: Path | Sequence[Path],
    max_epoch: int | None = None,
    *,
    episodes_of_record: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """`(episode rows, contest rows)` for every finished clinic morning under the root(s), paper rules applied.

    Epochs above `max_epoch` are dropped; `episodes_of_record` marks every morning outside the paper's
    episode set as excluded.

    Raises:
        FileNotFoundError: A runs root does not exist (a Modal root not pulled yet, a typo): it is never read
            as an empty root, which would silently drop its mornings.
    """
    roots = [runs_root] if isinstance(runs_root, Path) else list(runs_root)
    missing = [r for r in roots if not r.is_dir()]
    if missing:
        raise FileNotFoundError(missing_roots_message(missing))
    episodes: list[dict[str, Any]] = []
    contests: list[dict[str, Any]] = []
    seen: list[dict[str, Any]] = []
    for root in roots:
        for run_dir, summary, config, done in finished_runs(root, "clinic"):
            read = read_episode(run_dir, summary, config, done)
            if read is None:
                continue
            row, rows = read
            seen.append(row)
            if not within_epochs(row, max_epoch):
                continue
            episodes.append(row)
            contests.extend(rows)
    check_pools(seen, roots)
    apply_paper_rules(
        episodes, record.membership(record.load()) if episodes_of_record else None
    )
    valid = {str(r["run"]) for r in episodes if is_valid(r)}
    for c in contests:
        c["valid"] = int(str(c["run"]) in valid)
    return episodes, contests


# ── cells and pools ───────────────────────────────────────────────────────────────────────────────


def morning_of(row: Mapping[str, Any]) -> Morning:
    """A valid morning's counts (`contests_joint` defaults to 0 on rows banked without the joint columns)."""
    return Morning(
        epoch=int(row.get("epoch") or 0),
        joint=int(row.get("contests_joint") or 0),
        met=int(row.get("contests_met") or 0),
        n=int(row.get("contests") or 0),
    )


def _group(
    rows: Iterable[Mapping[str, Any]], keys: tuple[str, ...]
) -> dict[tuple[str, ...], list[Mapping[str, Any]]]:
    groups: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[
            tuple(
                mitigation_of(row) if k == "mitigation" else str(row[k]) for k in keys
            )
        ].append(row)
    return groups


def _frac(value: float) -> float | None:
    return None if math.isnan(value) else round(value / 100, 4)


def cell_rows(
    episodes: list[dict[str, Any]], *, draws: int = metric.REPS
) -> list[dict[str, Any]]:
    """One row per (board, formation, model, mitigation) over its valid mornings: joint (headline) and met.

    `joint_rate` pools the scenario's contests; `joint_lo` / `joint_hi` are the paper's per-scenario interval
    (fractions; `draws` replicates, the paper's seeds). `mornings` carries the valid mornings' counts for the
    pooled statistics (never written to CSV).
    """
    rows: list[dict[str, Any]] = []
    for (scenario, formation, model, mitigation), group in sorted(
        _group(episodes, ("scenario", "formation", "model", "mitigation")).items(),
        key=lambda item: (item[0][3] != NONE, item[0]),
    ):
        clean = [r for r in group if is_clean(r)]
        valid = [r for r in group if is_valid(r)]
        mornings = [morning_of(r) for r in valid if int(r.get("contests") or 0) > 0]
        n = sum(m.n for m in mornings)
        joint = sum(m.joint for m in mornings)
        met = sum(m.met for m in mornings)
        scheme = metric.scheme_for(formation, mitigation)
        lo, hi = metric.cell_interval(
            mornings,
            scheme=scheme,
            seed=metric.cell_seed(scheme, model, formation, scenario, BOARDS_OF_RECORD),
            reps=draws,
        )
        endstates = Counter(str(r.get("endstate")) for r in valid)
        rows.append(
            {
                "scenario": scenario,
                "formation": formation,
                "model": model,
                "mitigation": mitigation,
                "instrument": "+".join(
                    sorted({str(r.get("instrument")) for r in valid})
                )
                or None,
                "episodes": len(group),
                "clean": len(clean),
                "valid": len(valid),
                "excluded": len(group) - len(valid),
                "contests": n,
                "joint": joint,
                "met": met,
                "joint_rate": round(joint / n, 4) if n else None,
                "joint_lo": _frac(lo) if n else None,
                "joint_hi": _frac(hi) if n else None,
                "deadline_met_rate": round(met / n, 4) if n else None,
                "holders_dropped": sum(
                    int(r.get("holders_dropped") or 0) for r in valid
                ),
                "endstate_clean": endstates["clean"],
                "endstate_horizon": endstates["horizon"],
                "endstate_wedged": endstates["wedged"],
                "unmet": sum(int(r.get("unmet") or 0) for r in group),
                "stranded_callers_live": sum(
                    int(r.get("stranded_callers_live") or 0) for r in group
                ),
                "mornings": tuple(mornings),
            }
        )
    return rows


def conditions_of(boards: Iterable[str]) -> list[str]:
    """The conditions a set of boards supports: each twin present, plus `both` when both twins are (last)."""
    twins = {metric.twin_of(b) for b in boards}
    out = [c for c in ("assembled", "scattered") if metric.TWIN_OF[c] in twins]
    return out + (["both"] if len(out) == 2 else [])


def pool_label(condition: str, n_scenarios: int) -> str:
    """`POOLED (24 scenarios)` for both conditions, `POOLED assembled (12 scenarios)` for one."""
    word = "" if condition == "both" else f" {condition}"
    return f"POOLED{word} ({n_scenarios} scenarios)"


def pooled_rows(
    episodes: list[dict[str, Any]] | None = None,
    *,
    cells: list[dict[str, Any]] | None = None,
    draws: int = metric.REPS,
) -> list[dict[str, Any]]:
    """One row per (model, formation, mitigation, condition): the paper's scenario average and its interval.

    Conditions: `assembled` and `scattered` where the run covers a board of that twin, `both` when it covers
    both twins. Percent values (`joint_pct`, `lo`, `hi`, `met_pct`) as the paper prints them.
    """
    cells = cells if cells is not None else cell_rows(episodes or [], draws=draws)
    rows: list[dict[str, Any]] = []
    for (model, formation, mitigation), group in sorted(
        _group(cells, ("model", "formation", "mitigation")).items(),
        key=lambda item: (item[0][2] != NONE, item[0]),
    ):
        per_board = {
            str(c["scenario"]): list(c["mornings"]) for c in group if c["mornings"]
        }
        scheme = metric.scheme_for(formation, mitigation)
        for condition in conditions_of(per_board):
            subset = {
                b: ms
                for b, ms in per_board.items()
                if metric.in_condition(b, condition)
            }
            avg = metric.scenario_average(
                subset,
                scheme=scheme,
                condition=condition,
                seed=metric.pooled_seed(
                    scheme, model, formation, mitigation, condition
                ),
                reps=draws,
            )
            rows.append(
                {
                    "model": model,
                    "formation": formation,
                    "mitigation": mitigation,
                    "condition": condition,
                    "label": pool_label(condition, avg.n_scenarios),
                    "boards": ";".join(sorted(subset)),
                    "n_scenarios": avg.n_scenarios,
                    "mornings": avg.n_episodes,
                    "contests": avg.n_contests,
                    "joint": avg.joint,
                    "met": avg.met,
                    "joint_pct": round(avg.pct, 2),
                    "lo": round(avg.lo, 2),
                    "hi": round(avg.hi, 2),
                    "met_pct": round(avg.met_pct, 2),
                    "met_pooled_pct": round(100 * avg.met / avg.n_contests, 2),
                    "method": avg.method,
                }
            )
    return rows


# ── the paper's paired silent-team contrasts ─────────────────────────────────────────────────────────

#: `paired.csv`'s columns: the run's paired contrast (percent), then the paper's over the same scenarios.
PAIRED_COLUMNS: tuple[str, ...] = (
    "model",
    "contrast",
    "reference_formation",
    "condition",
    "label",
    "n_scenarios",
    "n_pairs",
    "silent_pct",
    "silent_lo",
    "silent_hi",
    "reference_pct",
    "reference_lo",
    "reference_hi",
    "diff_pp",
    "lo_pp",
    "hi_pp",
    "method",
    "run_degenerate",
    "paper_label",
    "paper_scenarios",
    "paper_n_pairs",
    "paper_diff_pp",
    "paper_lo_pp",
    "paper_hi_pp",
    "paper_verdict",
    "boards",
)


def _paired_sides(
    episodes: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], dict[str, list[Morning]]]:
    """`(model, formation) -> board -> valid control-arm mornings` (the paired contrast's input)."""
    out: dict[tuple[str, str], dict[str, list[Morning]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for r in episodes:
        if (
            mitigation_of(r) != NONE
            or not is_valid(r)
            or int(r.get("contests") or 0) <= 0
        ):
            continue
        out[(str(r["model"]), str(r["formation"]))][str(r["scenario"])].append(
            morning_of(r)
        )
    return out


def paired_rows(
    episodes: Iterable[Mapping[str, Any]],
    *,
    reference: PaperReference | None = None,
    reference_path: Path = REFERENCE_PATH,
    draws: int = metric.REPS,
) -> list[dict[str, Any]]:
    """The paper's paired silent-team contrasts on a run, beside the paper's own over the same scenarios.

    Per model with valid silent-team mornings and valid peer-to-peer team (or coordinator) mornings of the same
    epochs, per information condition the run covers: the silent team minus the reference formation over the
    matched episodes (`metric.paired_contrast`, the paper's seeds; `draws` replicates), and the frozen paper
    contrast (`PaperReference.paired_contrast`) with `check.py`'s band of the run's difference against it.

    Where a scenario holds fewer than 2 pairs its bootstrap cannot vary, so the run's interval collapses toward the
    point (`run_degenerate`): outside the paper's interval such a contrast reads WARN (unresolved), never MISS.
    """
    paper = reference if reference is not None else PaperReference.load(reference_path)
    sides = _paired_sides(episodes)
    rows: list[dict[str, Any]] = []
    models = sorted(
        {m for (m, f) in sides if f == "team_silent"}, key=metric.model_index
    )
    for model in models:
        silent = sides[(model, "team_silent")]
        for formation in metric.PAIRED_COMPARISON_INDEX:
            other = sides.get((model, formation))
            if not other:
                continue
            for condition in conditions_of(paired_boards(silent, other, "both")):
                result = metric.paired_contrast(
                    silent,
                    other,
                    seed=metric.paired_seed(model, formation, condition),
                    reps=draws,
                    condition=condition,
                )
                boards = paired_boards(silent, other, condition)
                degenerate = any(
                    len({m.epoch for m in silent[b]} & {m.epoch for m in other[b]}) < 2
                    for b in boards
                )
                frozen = paper.paired_contrast(model, formation, condition, boards)
                row: dict[str, Any] = {
                    "model": model,
                    "contrast": f"team_silent-{formation}",
                    "reference_formation": formation,
                    "condition": condition,
                    "label": pool_label(condition, result.n_scenarios),
                    "n_scenarios": result.n_scenarios,
                    "n_pairs": result.n_pairs,
                    "silent_pct": round(result.silent_pct, 2),
                    "silent_lo": round(result.silent_lo, 2),
                    "silent_hi": round(result.silent_hi, 2),
                    "reference_pct": round(result.reference_pct, 2),
                    "reference_lo": round(result.reference_lo, 2),
                    "reference_hi": round(result.reference_hi, 2),
                    "diff_pp": round(result.diff, 2),
                    "lo_pp": round(result.lo, 2),
                    "hi_pp": round(result.hi, 2),
                    "method": result.method,
                    "run_degenerate": degenerate,
                    "paper_label": None,
                    "paper_scenarios": None,
                    "paper_n_pairs": None,
                    "paper_diff_pp": None,
                    "paper_lo_pp": None,
                    "paper_hi_pp": None,
                    "paper_verdict": None,
                    "boards": ";".join(boards),
                }
                if frozen is not None:
                    covered, held = len(frozen["boards"]), int(frozen["held"])
                    verdict = paper_band(
                        result.diff,
                        (result.lo, result.hi),
                        (float(frozen["lo"]), float(frozen["hi"])),
                    )
                    row.update(
                        paper_label=frozen["paper_label"],
                        paper_scenarios=str(covered)
                        if covered >= held
                        else f"{covered} of {held}",
                        paper_n_pairs=int(frozen["n_pairs"]),
                        paper_diff_pp=float(frozen["diff_pp"]),
                        paper_lo_pp=float(frozen["lo"]),
                        paper_hi_pp=float(frozen["hi"]),
                        paper_verdict="WARN"
                        if degenerate and verdict == "MISS"
                        else verdict,
                    )
                rows.append(row)
    return rows


def _paired_contrast_row(
    row: Mapping[str, Any], a: str, *, reference_only: bool = False
) -> dict[str, Any]:
    """A CONTRAST row `<a>-team_silent` from a paired row (run or frozen): the negated silent-minus-`a` contrast."""

    def neg(value: Any) -> Any:
        return None if value is None else round(-float(value), 2)

    n = int(row["n_pairs"])
    if reference_only:  # a frozen `reference.json` row, the paper's on both sides
        label = pool_label(str(row["condition"]), int(row["n_scenarios"]))
        method = metric.paired_method()
        run = ref = (row["diff_pp"], row["lo"], row["hi"])
        ref_method: str | None = method
    else:
        label, method = str(row["label"]), str(row["method"])
        run = (row["diff_pp"], row["lo_pp"], row["hi_pp"])
        ref = (row["paper_diff_pp"], row["paper_lo_pp"], row["paper_hi_pp"])
        ref_method = metric.paired_method() if ref[0] is not None else None
    full: dict[str, Any] = {
        "env": ENV,
        "scenario": label,
        "model": str(row["model"]),
        "mitigation": NONE,
        "contrast": f"{a}-team_silent",
        "n_a": n,
        "n_b": n,
        "diff_pp": neg(run[0]),
        "lo_pp": neg(run[2]),
        "hi_pp": neg(run[1]),
        "method": method,
        "ref_diff_pp": neg(ref[0]),
        "ref_lo_pp": neg(ref[2]),
        "ref_hi_pp": neg(ref[1]),
        "ref_method": ref_method,
        "ref_instrument": PAIRED_REFERENCE_INSTRUMENT if ref[0] is not None else None,
    }
    return {column: full.get(column) for column in CONTRAST_COLUMNS}


# ── the frozen reference, per arm (the table API) ─────────────────────────────────────────────────


class Reference:
    """The paper reference restricted to ONE arm (`load(path, mitigation)`): its cells by (scenario, formation, model)."""

    def __init__(self, paper: PaperReference, mitigation: str = NONE) -> None:
        self.paper = paper
        self.mitigation = mitigation

    @classmethod
    def arms(cls, path: Path = REFERENCE_PATH) -> list[str]:
        """The arms the file freezes cells for, the control arm first."""
        return PaperReference.load(path).arms()

    @classmethod
    def load(cls, path: Path = REFERENCE_PATH, mitigation: str = NONE) -> Reference:
        """The frozen cells of one arm (an empty reference when no file is at `path`)."""
        return cls(PaperReference.load(path), mitigation)

    def keys(self) -> list[tuple[str, str, str]]:
        """Every `(scenario, formation, model)` the arm has a cell for, sorted."""
        return sorted(
            {(k[1], k[2], k[3]) for k in self.paper.cells if k[4] == self.mitigation}
        )

    def cell(
        self, scenario: str, formation: str, model: str
    ) -> tuple[str, dict[str, Any]] | None:
        """`(instrument, cell)` from the set the paper reads this arm from (else any set holding it)."""
        found = self.paper.cells_for(scenario, formation, model, self.mitigation)
        return found[0] if found else None

    def pool(
        self, model: str, formation: str, condition: str, boards: Iterable[str]
    ) -> dict[str, Any] | None:
        """The paper's scenario average over `boards` in the arm's primary set (else any set holding them)."""
        boards = list(boards)
        primary = primary_instrument(formation, self.mitigation)
        others = [i for i in self.paper.instruments() if i != primary]
        for instrument in (primary, *others):
            found = self.paper.pool(
                instrument, model, formation, self.mitigation, condition, boards
            )
            if found is not None:
                return found
        return None


def _ref_label(instrument: str, covered: int, held: int) -> str:
    return (
        instrument
        if covered >= held
        else f"{instrument} ({covered} of {held} scenarios)"
    )


def _verdict(
    point: float, interval: tuple[float, float], ref_lo: float, ref_hi: float
) -> str | None:
    if math.isnan(ref_lo) or math.isnan(ref_hi):
        return None
    return paper_band(point, interval, (ref_lo, ref_hi), unit=0.01)


# ── SCORE and CONTRAST rows ───────────────────────────────────────────────────────────────────────


def _empty_results() -> dict[str, list[dict[str, Any]]]:
    return {"scores": [], "pooled_scores": [], "contrasts": [], "pooled_contrasts": []}


def _point_diff(
    a: float, b: float, n_a: int, n_b: int, method: str = POINT_DIFF
) -> Diff:
    return Diff(a - b, math.nan, math.nan, method, n_a, n_b)


def _score_row(
    *,
    label: str,
    model: str,
    formation: str,
    n: int,
    score: float,
    lo: float | None,
    hi: float | None,
    ci_method: str,
    paper: tuple[str, dict[str, Any], int] | None,
    opus: tuple[str, dict[str, Any], int] | None,
) -> dict[str, Any]:
    """A SCORE row (fractions); `paper` / `opus` = `(instrument, frozen cell or pool, scenarios covered)`."""
    columns: dict[str, Any] = {
        "scenario": label,
        "model": model,
        "formation": formation,
        "unit": UNIT,
        "n": n,
        "score": round(score, 4),
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_method": ci_method,
    }
    interval = (math.nan if lo is None else lo, math.nan if hi is None else hi)
    if paper is not None:
        instrument, ref, covered = paper
        ref_score = float(ref["joint_pct"]) / 100
        columns.update(
            paper_score=round(ref_score, 4),
            paper_n=int(ref["episodes"]),
            paper_instrument=_ref_label(
                instrument, covered, int(ref.get("held", covered))
            ),
            paper_delta_pp=pp(score - ref_score),
            paper_verdict=_verdict(
                score, interval, float(ref["lo"]) / 100, float(ref["hi"]) / 100
            ),
        )
    opus_diff: Diff | None = None
    opus_cell: dict[str, Any] | None = None
    if opus is not None:
        instrument, ref, covered = opus
        ref_score = float(ref["joint_pct"]) / 100
        opus_cell = {
            "score": ref_score,
            "n": int(ref["episodes"]),
            "instrument": _ref_label(
                instrument, covered, int(ref.get("held", covered))
            ),
        }
        opus_diff = _point_diff(score, ref_score, n, int(ref["episodes"]))
    columns.update(baseline_columns(opus_diff, opus_cell, prefix="opus5"))
    return score_row(ENV, **columns)


def results_from_episodes(
    episodes: list[dict[str, Any]],
    *,
    reference: Reference | None = None,
    reference_path: Path = REFERENCE_PATH,
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
) -> dict[str, list[dict[str, Any]]]:
    """The readout's SCORE and CONTRAST rows of already-collected episode rows.

    One mitigation arm at a time: each arm's mornings are read against the frozen cells of the same arm and
    every row carries its arm in the `mitigation` column.
    """
    out = _empty_results()
    paper = (
        reference.paper
        if reference is not None
        else PaperReference.load(reference_path)
    )
    for arm, group in partition(episodes).items():
        rows = _arm_results(
            group, reference=Reference(paper, arm), draws=draws, seed=seed
        )
        for section, section_rows in rows.items():
            out[section].extend(tag(section_rows, arm))
    return out


def _arm_results(
    episodes: list[dict[str, Any]], *, reference: Reference, draws: int, seed: int
) -> dict[str, list[dict[str, Any]]]:
    """`results_from_episodes` for the mornings and frozen cells of ONE mitigation arm."""
    cells = [c for c in cell_rows(episodes, draws=draws) if c["mornings"]]
    if not cells:
        return _empty_results()
    scores: list[dict[str, Any]] = []
    for c in sorted(
        cells, key=lambda c: (str(c["scenario"]), str(c["formation"]), str(c["model"]))
    ):
        scenario, formation, model = (
            str(c["scenario"]),
            str(c["formation"]),
            str(c["model"]),
        )
        ref = reference.cell(scenario, formation, model)
        opus = reference.cell(scenario, formation, BASELINE_MODEL)
        scores.append(
            _score_row(
                label=scenario,
                model=model,
                formation=formation,
                n=len(c["mornings"]),
                score=float(c["joint_rate"]),
                lo=c["joint_lo"],
                hi=c["joint_hi"],
                ci_method=CI_METHOD,
                paper=(ref[0], ref[1], 1) if ref else None,
                opus=(opus[0], opus[1], 1) if opus else None,
            )
        )
    pooled_scores: list[dict[str, Any]] = []
    for p in pooled_rows(cells=cells, draws=draws):
        model, formation, condition = (
            str(p["model"]),
            str(p["formation"]),
            str(p["condition"]),
        )
        boards = str(p["boards"]).split(";")
        ref = reference.pool(model, formation, condition, boards)
        opus = reference.pool(BASELINE_MODEL, formation, condition, boards)
        pooled_scores.append(
            _score_row(
                label=str(p["label"]),
                model=model,
                formation=formation,
                n=int(p["mornings"]),
                score=float(p["joint_pct"]) / 100,
                lo=_frac(float(p["lo"])),
                hi=_frac(float(p["hi"])),
                ci_method=POOLED_CI_METHOD,
                paper=(str(ref["instrument"]), ref, len(ref["boards"]))
                if ref
                else None,
                opus=(str(opus["instrument"]), opus, len(opus["boards"]))
                if opus
                else None,
            )
        )
    units: dict[tuple[str, str, str], list[tuple[int, int]]] = {
        (str(c["scenario"]), str(c["model"]), str(c["formation"])): [
            (m.joint, m.n) for m in c["mornings"]
        ]
        for c in cells
    }

    def ref_contrast(scenario: str | None, model: str, a: str, b: str) -> Diff | None:
        if scenario is not None:
            ca, cb = (
                reference.cell(scenario, a, model),
                reference.cell(scenario, b, model),
            )
            if ca is None or cb is None:
                return None
            return _point_diff(
                float(ca[1]["joint_pct"]) / 100,
                float(cb[1]["joint_pct"]) / 100,
                int(ca[1]["episodes"]),
                int(cb[1]["episodes"]),
                "difference of the frozen cells",
            )
        boards = sorted(
            s for (s, m, f) in units if m == model and f == a and (s, model, b) in units
        )
        if not boards:
            return None
        condition = conditions_of(boards)[-1]
        pa = reference.pool(model, a, condition, boards)
        pb = reference.pool(model, b, condition, boards)
        if pa is None or pb is None:
            return None
        return _point_diff(
            float(pa["joint_pct"]) / 100,
            float(pb["joint_pct"]) / 100,
            int(pa["episodes"]),
            int(pb["episodes"]),
            "difference of the frozen scenario averages",
        )

    contrasts, pooled_contrasts = contrast_rows(
        ENV,
        units,
        rate_stat,
        combine="strata",
        reference=ref_contrast,
        reference_instrument=REFERENCE_CONTRAST_INSTRUMENT,
        draws=draws,
        seed=seed,
    )
    if reference.mitigation == NONE:
        pooled_contrasts = _with_paired(
            pooled_contrasts,
            paired_rows(episodes, reference=reference.paper, draws=draws),
        )
    return {
        "scores": scores,
        "pooled_scores": pooled_scores,
        "contrasts": contrasts,
        "pooled_contrasts": pooled_contrasts,
    }


def _with_paired(
    pooled_contrasts: list[dict[str, Any]], paired: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The pooled contrasts with every `<formation>-team_silent` row replaced by the paper's paired contrast.

    The paper compares the silent team only over matched episodes (`paired_rows`); the unpaired strata row
    would mix, e.g., the team's episodes 1-20 with the silent team's 1-5. The paired row of the widest
    condition the run covers (`both` when it covers both twins) takes the unpaired row's place.
    """
    widest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in paired:
        key = (str(row["model"]), str(row["reference_formation"]))
        if key not in widest or row["condition"] == "both":
            widest[key] = row
    out: list[dict[str, Any]] = []
    for row in pooled_contrasts:
        a, _, b = str(row["contrast"]).partition("-")
        found = widest.get((str(row["model"]), a)) if b == "team_silent" else None
        out.append(row if found is None else _paired_contrast_row(found, a))
    return out


def reference_rows(path: Path = REFERENCE_PATH) -> dict[str, list[dict[str, Any]]]:
    """The SCORE and CONTRAST rows of the frozen paper reference alone (`expected/reference.json`).

    Score rows: one per cell of the set the paper reads each (formation, arm) from, `n` its episodes, the
    interval the paper's per-scenario one, `paper_instrument` the set; pooled rows: the scenario averages per
    condition (`POOLED (24 scenarios)` = both, `POOLED assembled / scattered (12 scenarios)`), plus the
    mitigation figure's controls on episodes 1-10 (`POOLED episodes 1-10 ...`). The `opus5_*` columns compare
    with the Claude Opus 5 cell or pool of the same key (a difference of points). Contrast rows are differences
    of the frozen cells and scenario averages (no interval: the frozen table carries none for them), except the
    pooled contrasts with the silent team, which are the paper's paired contrasts with their intervals
    (`reference.json` `paired`, negated to read `<formation>-team_silent`).
    """
    paper = PaperReference.load(path)
    out = _empty_results()
    for arm in paper.arms():
        rows = _arm_reference_rows(paper, arm)
        for section, section_rows in rows.items():
            out[section].extend(tag(section_rows, arm))
    return out


def _reference_pools(
    paper: PaperReference, arm: str
) -> list[tuple[str, dict[str, Any]]]:
    """`(label, pooled row)` of one arm: the primary sets' pools, then the episodes-1-10 controls."""
    out: list[tuple[str, dict[str, Any]]] = []
    for (
        instrument,
        _model,
        formation,
        mitigation,
        condition,
    ), row in paper.pools.items():
        if mitigation != arm:
            continue
        label = pool_label(condition, int(row["n_scenarios"]))
        if instrument != primary_instrument(formation, mitigation):
            label = label.replace("POOLED", "POOLED episodes 1-10", 1)
        out.append((label, row))
    return out


def _arm_reference_rows(
    paper: PaperReference, arm: str
) -> dict[str, list[dict[str, Any]]]:
    """`reference_rows` for the frozen cells of ONE mitigation arm."""
    reference = Reference(paper, arm)
    scores: list[dict[str, Any]] = []
    for scenario, formation, model in reference.keys():
        found = reference.cell(scenario, formation, model)
        assert found is not None
        instrument, cell = found
        if instrument != primary_instrument(formation, arm) and arm == NONE:
            continue
        scores.append(
            _reference_score_row(
                paper, arm, scenario, model, formation, instrument, cell, pooled=False
            )
        )
    pooled_scores = [
        _reference_score_row(
            paper,
            arm,
            label,
            str(row["model"]),
            str(row["formation"]),
            str(row["instrument"]),
            row,
            pooled=True,
        )
        for label, row in _reference_pools(paper, arm)
    ]
    contrasts: list[dict[str, Any]] = []
    pooled_contrasts: list[dict[str, Any]] = []
    models = sorted({k[3] for k in paper.cells if k[4] == arm}, key=metric.model_index)
    formations = {k[2] for k in paper.cells if k[4] == arm}
    for model in models:
        for a, b in (
            ("coordinator", "team"),
            ("coordinator", "team_silent"),
            ("team", "team_silent"),
        ):
            if a not in formations or b not in formations:
                continue
            common = [
                s
                for (s, f, m) in reference.keys()
                if m == model and f == a and reference.cell(s, b, model) is not None
            ]
            for scenario in sorted(common):
                ca, cb = (
                    reference.cell(scenario, a, model),
                    reference.cell(scenario, b, model),
                )
                assert ca is not None and cb is not None
                contrasts.append(
                    _reference_contrast_row(
                        scenario,
                        model,
                        a,
                        b,
                        ca[1],
                        cb[1],
                        "difference of the frozen cells",
                    )
                )
            frozen_paired = (
                paper.paired.get((model, a, "both"))
                if b == "team_silent" and arm == NONE
                else None
            )
            if frozen_paired is not None:
                # the paper's own silent-team contrast: paired over the episodes both ran
                pooled_contrasts.append(
                    _paired_contrast_row(frozen_paired, a, reference_only=True)
                )
            elif common:
                condition = conditions_of(common)[-1]
                pa, pb = (
                    reference.pool(model, a, condition, common),
                    reference.pool(model, b, condition, common),
                )
                if pa is not None and pb is not None:
                    pooled_contrasts.append(
                        _reference_contrast_row(
                            pool_label(condition, len(common)),
                            model,
                            a,
                            b,
                            pa,
                            pb,
                            "difference of the frozen scenario averages",
                        )
                    )
    return {
        "scores": scores,
        "pooled_scores": pooled_scores,
        "contrasts": contrasts,
        "pooled_contrasts": pooled_contrasts,
    }


def _reference_score_row(
    paper: PaperReference,
    arm: str,
    label: str,
    model: str,
    formation: str,
    instrument: str,
    ref: Mapping[str, Any],
    *,
    pooled: bool,
) -> dict[str, Any]:
    """A SCORE row for one frozen cell or pool: its own set in `paper_instrument`, the other `paper_*` None."""
    score = float(ref["joint_pct"]) / 100
    columns: dict[str, Any] = {
        "scenario": label,
        "model": model,
        "formation": formation,
        "unit": UNIT,
        "n": int(ref["episodes"]),
        "score": round(score, 4),
        "ci_lo": _frac(float(ref["lo"])),
        "ci_hi": _frac(float(ref["hi"])),
        "ci_method": POOLED_CI_METHOD if pooled else CI_METHOD,
        "paper_instrument": instrument,
    }
    if pooled:
        opus_ref = paper.pools.get(
            (instrument, BASELINE_MODEL, formation, arm, str(ref["condition"]))
        )
    else:
        opus_ref = paper.cell(instrument, label, formation, BASELINE_MODEL, arm)
    opus_diff: Diff | None = None
    opus_cell: dict[str, Any] | None = None
    if opus_ref is not None:
        opus_score = float(opus_ref["joint_pct"]) / 100
        opus_cell = {
            "score": opus_score,
            "n": int(opus_ref["episodes"]),
            "instrument": instrument,
        }
        opus_diff = (
            Diff(0.0, 0.0, 0.0, "same cell", int(ref["n"]), int(ref["n"]))
            if model == BASELINE_MODEL
            else _point_diff(
                score,
                opus_score,
                int(ref["episodes"]),
                int(opus_ref["episodes"]),
                "difference of the frozen cells",
            )
        )
    columns.update(baseline_columns(opus_diff, opus_cell, prefix="opus5"))
    return score_row(ENV, **columns)


def _reference_contrast_row(
    scenario: str,
    model: str,
    a: str,
    b: str,
    ra: Mapping[str, Any],
    rb: Mapping[str, Any],
    method: str,
) -> dict[str, Any]:
    diff = _point_diff(
        float(ra["joint_pct"]) / 100,
        float(rb["joint_pct"]) / 100,
        int(ra["episodes"]),
        int(rb["episodes"]),
        method,
    )
    row: dict[str, Any] = {
        "env": ENV,
        "scenario": scenario,
        "model": model,
        "contrast": f"{a}-{b}",
        "n_a": diff.n_a,
        "n_b": diff.n_b,
        "diff_pp": pp(diff.point),
        "lo_pp": None,
        "hi_pp": None,
        "method": method,
        "ref_diff_pp": pp(diff.point),
        "ref_lo_pp": None,
        "ref_hi_pp": None,
        "ref_method": method,
        "ref_instrument": REFERENCE_CONTRAST_INSTRUMENT,
    }
    return {column: row.get(column) for column in CONTRAST_COLUMNS}


# ── rendering ─────────────────────────────────────────────────────────────────────────────────────

_POOLED_SCORE_VIEW = (
    "model",
    "formation",
    "scenario",
    "n",
    "score",
    "ci_lo",
    "ci_hi",
    "paper_score",
    "paper_delta_pp",
    "paper_verdict",
    "opus5_delta_pp",
)
_CONTRAST_VIEW = (
    "scenario",
    "model",
    "contrast",
    "n_a",
    "n_b",
    "diff_pp",
    "lo_pp",
    "hi_pp",
    "ref_diff_pp",
)


def results_markdown(
    results: Mapping[str, list[dict[str, Any]]], runs_root: Path
) -> str:
    """A compact markdown rendering: pooled scores, pooled contrasts, per-board contrasts.

    A `mitigation` column appears once any row names an arm besides the control arm.
    """
    rows = [row for section in results.values() for row in section]
    score_view = arm_columns(_POOLED_SCORE_VIEW, rows, after="formation")
    contrast_view = arm_columns(_CONTRAST_VIEW, rows, after="model")
    parts = [
        f"# clinic results: {runs_root.name}\n",
        f"Unit: valid {UNIT} (the paper's rules); score = joint success (the paper's metric), per scenario pooled "
        f"over its contests, pooled rows = the unweighted mean of the scenario rates; ci = {POOLED_CI_METHOD}; "
        f"contrasts = whole-morning percentile bootstrap of the difference of scenario averages (pooled "
        f"contrasts with the silent team: the paper's paired bootstrap over matched episodes); "
        f"ref_* = {REFERENCE_CONTRAST_INSTRUMENT} (with the silent team: {PAIRED_REFERENCE_INSTRUMENT}); "
        "deltas in percentage points.\n",
        "## Pooled scores\n",
        markdown_table(results["pooled_scores"], score_view),
        "## Pooled contrasts\n",
        markdown_table(results["pooled_contrasts"], contrast_view),
        "## Per-board contrasts\n",
        markdown_table(results["contrasts"], contrast_view),
    ]
    return "\n".join(parts)


def _write_rows(path: Path, rows: list[dict[str, Any]], columns: Sequence[str]) -> None:
    """Rows in the table's own column order (`write_csv` sorts, which scatters the score columns)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)


def _plain(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows without the in-memory `mornings` tuples."""
    return [{k: v for k, v in r.items() if k != "mornings"} for r in rows]


def _fmt_cell(row: Mapping[str, Any]) -> str:
    if row["joint_rate"] is None:
        return f"valid {row['valid']}/{row['episodes']}: no scorable morning"
    return (
        f"valid {row['valid']}/{row['episodes']}  joint {row['joint']}/{row['contests']} = {row['joint_rate']:.1%} "
        f"[{row['joint_lo']:.1%}, {row['joint_hi']:.1%}]  met {row['deadline_met_rate']:.1%}  "
        f"unmet {row['unmet']}  stranded(live) {row['stranded_callers_live']}"
    )


def exclusion_notes(episodes: Iterable[Mapping[str, Any]]) -> list[str]:
    """Why mornings were excluded, and the mornings with failed target calls.

    Counts per exclusion reason; `_harness.readout.provider_error_note`.
    """
    episodes = list(episodes)
    reasons = Counter(str(r.get("paper_exclusion") or "") for r in episodes)
    reasons.pop("", None)
    lines = [f"excluded: {n} x {reason}" for reason, n in sorted(reasons.items())]
    lines += provider_error_note(
        [dict(r) for r in episodes],
        UNIT,
        rule_t=False,
        kept_because="the clinic applies no rule T",
    )
    return lines


def _fmt_paired(row: Mapping[str, Any]) -> str:
    paper = (
        f"  paper {row['paper_label']} {float(row['paper_diff_pp']):+.2f} "
        f"[{float(row['paper_lo_pp']):+.2f}, {float(row['paper_hi_pp']):+.2f}] over "
        f"{row['paper_scenarios']} scenarios ({row['paper_n_pairs']} pairs): {row['paper_verdict']}"
        if row["paper_diff_pp"] is not None
        else "  (no paper contrast)"
    )
    return (
        f"  {row['model']:16} {row['contrast']:24} {row['condition']:9} ({row['n_scenarios']:2} scenarios, "
        f"{row['n_pairs']:4} pairs)  {float(row['silent_pct']):6.2f} vs {float(row['reference_pct']):6.2f}  "
        f"{float(row['diff_pp']):+.2f} [{float(row['lo_pp']):+.2f}, {float(row['hi_pp']):+.2f}]{paper}"
    )


def summary_text(
    cells: list[dict[str, Any]],
    pooled: list[dict[str, Any]],
    episodes: Iterable[Mapping[str, Any]] = (),
    paired: Sequence[Mapping[str, Any]] = (),
) -> str:
    """The printed readout: the paper's scenario averages, its paired contrasts, every cell, then the exclusions."""
    lines = ["scenario-averaged joint success (the paper's metric; valid mornings):"]
    lines += [
        f"  {p['model']:16} {p['formation']:12} {p['condition']:9} ({p['n_scenarios']:2} scenarios, "
        f"{p['mornings']:4} mornings)  joint {p['joint_pct']:6.2f} [{p['lo']:6.2f}, {p['hi']:6.2f}]  "
        f"met {p['met_pct']:6.2f} (pooled {p['met_pooled_pct']:6.2f}){arm_label(mitigation_of(p))}"
        for p in pooled
    ]
    if paired:
        lines.append(
            "paired silent-team contrasts (the paper's: silent minus reference over matched episodes, paired "
            "bootstrap):"
        )
        lines += [_fmt_paired(row) for row in paired]
    lines.append("per board:")
    lines += [
        f"  {r['scenario']:34} {r['model']:16} {r['formation']:12} {_fmt_cell(r)}{arm_label(mitigation_of(r))}"
        for r in cells
    ]
    lines += exclusion_notes(episodes)
    return "\n".join(lines) + "\n"


def build(
    runs_root: Path | Sequence[Path],
    max_epoch: int | None = None,
    *,
    draws: int = DEFAULT_DRAWS,
    episodes_of_record: bool = False,
) -> dict[str, Any]:
    """Everything `main` writes, in memory."""
    episodes, contests = collect(
        runs_root, max_epoch, episodes_of_record=episodes_of_record
    )
    cells = cell_rows(episodes, draws=draws)
    return {
        "eval": "clinic",
        "runs_root": [
            str(r) for r in ([runs_root] if isinstance(runs_root, Path) else runs_root)
        ],
        "episodes": episodes,
        "contests": contests,
        "cells": cells,
        "pooled": pooled_rows(cells=cells, draws=draws),
        "paired": paired_rows(episodes, draws=draws),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "runs_root",
        nargs="*",
        type=Path,
        default=[EVAL_ROOT / "runs"],
        help="one or more runs roots",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="where to write (default: readouts/<first runs_root name>/ beside this file)",
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
    parser.add_argument(
        "--draws",
        type=int,
        default=DEFAULT_DRAWS,
        help=f"bootstrap draws for the intervals and contrasts (default {DEFAULT_DRAWS}, the paper's)",
    )
    args = parser.parse_args(argv)
    roots = [r.resolve() for r in (args.runs_root or [EVAL_ROOT / "runs"])]
    missing = [r for r in roots if not r.is_dir()]
    if missing:
        parser.error(missing_roots_message(missing))
    out_dir: Path = (
        args.out_dir
        if args.out_dir is not None
        else EVAL_ROOT / "readouts" / roots[0].name
    )
    built = build(
        roots,
        args.max_epoch,
        draws=args.draws,
        episodes_of_record=args.episodes_of_record,
    )
    if not built["episodes"]:
        print(
            f"no finished clinic episodes under {', '.join(str(r) for r in args.runs_root)}"
        )
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "episodes.csv", built["episodes"])
    write_csv(out_dir / "contests.csv", built["contests"])
    write_csv(out_dir / "scenarios.csv", _plain(built["cells"]))
    write_csv(out_dir / "pooled.csv", built["pooled"])
    _write_rows(out_dir / "paired.csv", built["paired"], PAIRED_COLUMNS)
    text = summary_text(
        built["cells"], built["pooled"], built["episodes"], built["paired"]
    )
    (out_dir / "summary.txt").write_text(text)
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "eval": "clinic",
                "runs_root": built["runs_root"],
                "cells": _plain(built["cells"]),
                "pooled": built["pooled"],
                "paired": built["paired"],
            },
            indent=1,
        )
        + "\n"
    )
    results = results_from_episodes(built["episodes"], draws=args.draws)
    _write_rows(
        out_dir / "scores.csv",
        results["scores"] + results["pooled_scores"],
        SCORE_COLUMNS,
    )
    _write_rows(
        out_dir / "contrasts.csv",
        results["contrasts"] + results["pooled_contrasts"],
        CONTRAST_COLUMNS,
    )
    (out_dir / "results.md").write_text(results_markdown(results, roots[0]))
    print(text, end="")
    print(
        f"-> {out_dir} ({len(built['episodes'])} episodes, {len(built['contests'])} contests)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
