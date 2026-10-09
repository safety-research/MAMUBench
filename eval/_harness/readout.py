"""Shared run-dir reading for the 0-LLM reports: finished episodes -> (summary, config, done) triples."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

from _mitigations import NONE
from _mitigations import of as mitigation_of
from _offpaper import REASON_SEPARATOR, physics


def load_run(
    run_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    """`(world summary, config, DONE record)` for a FINISHED run dir, else `None`.

    Finished means `DONE.json` exists: a storm-aborted episode keeps its world artifacts for forensics
    but is deliberately never banked, and an in-flight episode has no summary yet — neither may score.
    """
    world = run_dir / "world"
    if not (world / "summary.json").exists() or not (run_dir / "DONE.json").exists():
        return None
    return (
        cast(dict[str, Any], json.loads((world / "summary.json").read_text())),
        cast(dict[str, Any], json.loads((world / "config.json").read_text())),
        cast(dict[str, Any], json.loads((run_dir / "DONE.json").read_text())),
    )


def finished_runs(
    runs_root: Path, eval_name: str
) -> Iterator[tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Every finished run dir under `runs_root` recorded by `eval_name`, sorted by run-dir name."""
    for world_dir in sorted(runs_root.rglob("world")):
        loaded = load_run(world_dir.parent)
        if loaded is None or loaded[1].get("eval") != eval_name:
            continue
        summary, config, done = loaded
        yield world_dir.parent, summary, config, done


def within_epochs(row: dict[str, Any], max_epoch: int | None) -> bool:
    """True when `row["epoch"]` is at most `max_epoch` (or no cap was asked for)."""
    if max_epoch is None:
        return True
    epoch = row.get("epoch")
    return isinstance(epoch, int) and epoch <= max_epoch


def base_row(
    run_dir: Path, summary: dict[str, Any], config: dict[str, Any], done: dict[str, Any]
) -> dict[str, Any]:
    """The columns every episode row carries regardless of env."""
    return {
        "run": run_dir.name,
        "scenario": config.get("scenario"),
        "formation": config.get("formation"),
        "cell": config.get("cell"),
        "model": str(config.get("model", "")).rsplit("/", 1)[-1],
        "provider": config.get("provider"),
        "epoch": config.get("epoch"),
        "commit": config.get("commit"),
        "pi_version": config.get("pi_version"),
        "fake_pi": config.get("fake_pi"),
        "harness": config.get("harness", "pi"),
        # sim only (None on pi runs and on sim runs banked before the instruments were recorded)
        "instrument": config.get("instrument"),
        "on_paper_instrument": config.get("on_paper_instrument"),
        # why the episode is off the paper's instrument ("; "-joined `off_paper`; empty on it, which every
        # simulated-harness episode is, or unrecorded)
        "off_paper": REASON_SEPARATOR.join(config.get("off_paper") or []),
        "target_effort": config.get("target_effort"),
        # The mitigation arm (`none` for the control arm and every run banked before arms existed); the
        # reports key cells by it, so arms never pool.
        "mitigation": mitigation_of(config),
        "ended": done.get("ended"),
        "rounds": done.get("rounds"),
        "error_turns": done.get("error_turns", 0),
        "crashed": ";".join(done.get("crashed", [])),
        "wall_s": done.get("wall_s"),
        "sim_clock": summary.get("clock"),
        # The provider-error screen's counts (rule T; sim only). Never part of `harness_clean`: readers
        # decide whether to screen (the API key report applies rule T to every formation and arm, as the paper).
        "rule_t_lost_turns": done.get("rule_t_lost_turns"),
        "failed_calls": done.get("failed_calls"),
        # failed_calls by class: rate limit (429), overload (529), anything else
        "failed_429": done.get("failed_429"),
        "failed_529": done.get("failed_529"),
        "failed_other": done.get("failed_other"),
        # of failed_other, the calls the provider refused the key for (401 / 403; `provider_rejected`)
        "failed_auth": done.get("failed_auth"),
        "max_consecutive_failures": done.get("max_consecutive_failures"),
        # pi harness only: the seats' pi thinking level (absent from simulated-harness records and from pi runs
        # banked before it was recorded, which ran pi's own default)
        **({"thinking": config["thinking"]} if config.get("thinking") else {}),
    }


def provider_rejected(row: dict[str, Any]) -> int:
    """Target calls the provider refused the key for (401 authentication / 403 permission; sim only, else 0).

    Such an error is never retried, so it quarantines seats (3 failed resumes) without a rule-T lost turn: the
    readers exclude the episode as a harness fault, whatever its clock reached. An episode banked before the
    count existed reads 0.
    """
    return int(row.get("failed_auth") or 0)


#: The most episodes `provider_error_note` names one by one (the rest are in episodes.csv).
NOTE_MAX_LINES = 20


#: What `provider_error_note` says of the episodes with a lost turn when no rule T is applied to them.
NO_RULE_T = "no rule T in this reading"


def provider_error_note(
    rows: list[dict[str, Any]],
    unit: str,
    *,
    rule_t: bool = True,
    kept_because: str = NO_RULE_T,
) -> list[str]:
    """Warning lines about the episodes with failed target calls (the scan's counts), empty when none failed.

    The provider-error scan is telemetry: under rule T (`rule_t`, the API key reading's screen) an episode in which
    an agent had 4 consecutive failed calls is dropped, and a refused key excludes an episode; any other failed call
    is kept, as in the paper, but a reproducer should see them. A reading without the screen (the clinic, whose
    paper numbers apply no rule T, or `--provider-screen none`) keeps the episodes with a lost turn and says why
    (`kept_because`). One summary line (the calls by class: 429 rate limit, 529 overload, other, which sum to the
    failed calls), then the episodes with a refused key or an error other than a rate limit or an overload, one
    line each (at most `NOTE_MAX_LINES`; every episode's counts are in episodes.csv).
    """
    hit = [r for r in rows if int(r.get("failed_calls") or 0) > 0]
    if not hit:
        return []

    def total(key: str) -> int:
        return sum(int(r.get(key) or 0) for r in hit)

    lost = sum(1 for r in hit if int(r.get("rule_t_lost_turns") or 0) > 0)
    rejected = [r for r in hit if provider_rejected(r)]
    lost_text = (
        f"rule T dropped {lost} {unit}(s) with a lost turn"
        if rule_t
        else f"{lost} {unit}(s) had a lost turn (kept: {kept_because})"
    )
    lines = [
        f"PROVIDER ERRORS: {len(hit)} of {len(rows)} {unit}s had failed target calls ({total('failed_calls')} "
        f"calls: 429 rate limit {total('failed_429')}, 529 overload {total('failed_529')}, other "
        f"{total('failed_other')}, of which the key refused {total('failed_auth')}); {lost_text}, and "
        f"{len(rejected)} with a refused key are excluded"
    ]
    named = sorted(
        (r for r in hit if provider_rejected(r) or int(r.get("failed_other") or 0) > 0),
        key=lambda r: str(r.get("run")),
    )
    for r in named[:NOTE_MAX_LINES]:
        lines.append(
            f"  {r.get('run')}: failed {r.get('failed_calls')} (other {r.get('failed_other') or 0}, key refused "
            f"{r.get('failed_auth') or 0}), lost turns {r.get('rule_t_lost_turns') or 0}"
            + (
                " — EXCLUDED: the provider refused the key"
                if provider_rejected(r)
                else ""
            )
        )
    if len(named) > NOTE_MAX_LINES:
        lines.append(f"  ... and {len(named) - NOTE_MAX_LINES} more (episodes.csv)")
    return lines


def single_harness(rows: list[dict[str, Any]], runs_root: Path) -> None:
    """Refuse a runs root that mixes the pi and simulated harnesses: one root, one instrument.

    The two harnesses play the same worlds under different agent loops, so their episodes are never pooled
    into one cell; a root that holds both is a launch mistake, not a corpus.
    """
    harnesses = sorted({str(r.get("harness") or "pi") for r in rows})
    if len(harnesses) > 1:
        raise SystemExit(
            f"{runs_root} mixes harnesses {harnesses}: a runs root holds ONE instrument (pi or sim); "
            "report each root on its own"
        )
    single_instrument(rows, runs_root)


def single_instrument(rows: list[dict[str, Any]], runs_root: Path) -> None:
    """Refuse a runs root in which one (formation, model, mitigation) pool mixes simulated-harness physics.

    Formations may legitimately differ (the paper's coordinator is `hero`, its teams `limits_off` in the API key
    and `standard` in the clinic), but the episodes pooled into one cell must share one physics record (`_offpaper.physics`): one scheduler
    instrument AND the same recorded deviations from the paper's (`off_paper`; the simulated harness records
    none, so a mixed record means a run dir produced by other code). A row without a recorded instrument (pi,
    or a sim run banked before instruments were recorded) counts as its own value, so it never pools with a
    recorded one either; a pi row's thinking level is part of its value.
    """
    seen: dict[tuple[str, str, str], set[str]] = {}
    for r in rows:
        key = (str(r.get("formation")), str(r.get("model")), str(r.get("mitigation")))
        thinking = f" pi thinking {r['thinking']}" if r.get("thinking") else ""
        seen.setdefault(key, set()).add(physics(r) + thinking)
    mixed = {key: sorted(v) for key, v in seen.items() if len(v) > 1}
    if mixed:
        detail = "; ".join(
            f"{formation}/{model}"
            + (f"/{mitigation}" if mitigation != NONE else "")
            + f": {instruments}"
            for (formation, model, mitigation), instruments in sorted(mixed.items())
        )
        raise SystemExit(
            f"{runs_root} mixes simulated-harness instruments or settings within a pool ({detail}): one pool, "
            "one physics record (the scheduler and every recorded setting); report each setting's runs from "
            "their own root"
        )


def harness_clean(row: dict[str, Any]) -> bool:
    """The harness half of the clean filter: no provider-error turn, no crashed seat.

    A storm-hit turn parks its seat and loses sim-time, and a crashed seat structurally changes the
    episode (the wrap-up walks survivors past the horizon) — neither may enter a clean pool. Each env
    adds its own completeness test on top.
    """
    return int(row.get("error_turns") or 0) == 0 and not row.get("crashed")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write rows with a stable header (`run` first, then alphabetical); creates parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row}, key=lambda k: (k != "run", k))
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
