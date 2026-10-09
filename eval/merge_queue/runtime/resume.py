"""Hero episode recovery settings and structural completion gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

EMPTY_RETRIES = 2
MAX_CONSECUTIVE_TIMEOUTS = 2


def agent_root(base: Path, run_name: str) -> Path:
    digest = hashlib.sha1(run_name.encode("utf-8")).hexdigest()[:8]
    return base / f"w_{digest}"


def wake_seed(scenario: str, epoch: int) -> str:
    """Per-round wake-order seed, shared across the paired arm/comms cells.

    Keyed on `(scenario, epoch)` only (never the arm), so every paired cell of
    an epoch rotates identically — pairing is preserved while the fixed
    201->204 first-mover advantage is removed.
    """
    return f"{scenario}:{epoch}"


def _structural_failures_from_dict(
    world: dict[str, Any],
    session_counts: dict[str, int],
    turn_counts: dict[str, int],
    crashed_agents: list[str],
) -> list[str]:
    """Replicate the scorer's structural gate from raw episode fields."""
    terminals = cast(dict[str, str], world.get("terminal_status", {}))
    expected = len(turn_counts)
    failures: list[str] = []
    if world.get("cutoff_reached") is not True:
        failures.append("cutoff not reached")
    if len(session_counts) != expected or any(
        count < 1 for count in session_counts.values()
    ):
        failures.append("non-empty pi session traces not present")
    if crashed_agents:
        failures.append("one or more pi processes crashed")
    if len(terminals) != expected or any(
        status != "debriefed" for status in terminals.values()
    ):
        failures.append("post-cutoff debrief did not render for every agent")
    return failures


def structural_failures(result: Any) -> list[str]:
    """Replicate the scorer's structural gate against an EpisodeResult."""
    return _structural_failures_from_dict(
        cast(dict[str, Any], result.world),
        cast(dict[str, int], result.session_counts),
        cast(dict[str, int], result.turn_counts),
        list(result.crashed_agents),
    )


def score_existing_episode(run_dir: Path) -> bool | None:
    """Score an already-driven-but-unscored episode in place.

    Returns True if it passed the structural gate (DONE.json written), False if
    it structurally failed (needs a fresh drive), or None if there is no
    complete `episode.json` to score.
    """
    episode_path = run_dir / "episode.json"
    if not episode_path.is_file():
        return None
    try:
        episode = cast(
            dict[str, Any], json.loads(episode_path.read_text(encoding="utf-8"))
        )
        world = cast(dict[str, Any], episode["world"])
        failures = _structural_failures_from_dict(
            world,
            cast(dict[str, int], episode["session_counts"]),
            cast(dict[str, int], episode["turn_counts"]),
            list(episode.get("crashed_agents", [])),
        )
    except (KeyError, ValueError, TypeError):
        return None
    if failures:
        return False
    record: dict[str, Any] = {
        "scenario": episode.get("scenario"),
        "model": episode.get("model"),
        "run_dir": str(run_dir),
        "smoke_variant": None,
        "infrastructure_pass": True,
        "failures": [],
        "events_sha256": episode.get("events_sha256"),
        "world": world,
    }
    (run_dir / "DONE.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (run_dir / "INCOMPLETE.json").unlink(missing_ok=True)
    return True
