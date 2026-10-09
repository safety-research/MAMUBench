"""Rule T: find the seat turns of an episode's scored attempt that ended on a provider error (0 LLM calls).

The paper drops an episode when any seat turn of the scored attempt ended on a provider error: a pi
assistant message with `stopReason == "error"` whose next assistant/user message is a user prompt, or
nothing (pi's own in-turn retry did not recover it). It removed 70 of the 1,879 merge-queue episodes of
record. This is the paper's corrupted-data audit scan (`session_stats`), over a run dir's
`agents/<seat>/sessions/*.jsonl`: a run dir can also hold the sessions of earlier, unscored attempts, and
`episode.json` records `session_counts` per seat for the scored one, so only the LAST `session_counts[seat]`
session files of each seat (filenames sort by their start timestamp) are read. A run dir the Modal
launcher packed (`workspaces.tar.gz`, `modal_app._pack_merge_queue_workspaces`) is read from its tarball.
"""

from __future__ import annotations

import json
import tarfile
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class SessionStats:
    """One pi session's provider-error counts.

    Attributes:
        assistant_messages: Assistant messages in the session.
        error_messages: Assistant messages with `stopReason == "error"`.
        turns_ended_by_error: Error messages whose next assistant/user message is a user prompt or nothing.
        unrecovered: 1 when no successful assistant/toolResult message follows the last error.
        by_kind: Error messages by kind (`529` overloaded, `429` rate limit, `other`).
    """

    assistant_messages: int
    error_messages: int
    turns_ended_by_error: int
    unrecovered: int
    by_kind: tuple[tuple[str, int], ...]


def session_stats(text: str) -> SessionStats:
    """Rule-T counts of one pi 0.77 session JSONL (the audit's `session_stats`, same decisions)."""
    messages: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            parsed: Any = json.loads(line)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        record = cast(dict[str, Any], parsed)
        if record.get("type") == "message":
            messages.append(cast(dict[str, Any], record.get("message") or {}))
    assistant = errors = lost = 0
    kinds: Counter[str] = Counter()
    last_error = -1
    for index, message in enumerate(messages):
        if message.get("role") != "assistant":
            continue
        assistant += 1
        if message.get("stopReason") != "error":
            continue
        errors += 1
        last_error = index
        text_error = str(message.get("errorMessage", ""))
        kinds[
            "529"
            if "overloaded" in text_error
            else "429"
            if ("rate_limit" in text_error or text_error.startswith("429"))
            else "other"
        ] += 1
        following = next(
            (
                str(later.get("role"))
                for later in messages[index + 1 :]
                if later.get("role") in ("assistant", "user")
            ),
            None,
        )
        if following != "assistant":
            lost += 1
    unrecovered = 0
    if last_error >= 0:
        unrecovered = (
            0
            if any(
                later.get("role") in ("assistant", "toolResult")
                and later.get("stopReason") != "error"
                for later in messages[last_error + 1 :]
            )
            else 1
        )
    return SessionStats(
        assistant_messages=assistant,
        error_messages=errors,
        turns_ended_by_error=lost,
        unrecovered=unrecovered,
        by_kind=tuple(sorted(kinds.items())),
    )


#: The tarball the Modal launcher packs a merge-queue run dir's seat trees into (`modal_app`).
WORKSPACES_TAR = "workspaces.tar.gz"


def _sessions_by_seat(run_dir: Path) -> dict[str, list[tuple[str, str]]]:
    """`seat -> [(session file name, text)]`, from `agents/` or, for a Modal-packed run dir, its tarball."""
    by_seat: dict[str, list[tuple[str, str]]] = {}
    agents = run_dir / "agents"
    if agents.is_dir():
        for path in sorted(agents.glob("*/sessions/*.jsonl")):
            by_seat.setdefault(path.parent.parent.name, []).append(
                (path.name, path.read_text(encoding="utf-8", errors="replace"))
            )
    archive = run_dir / WORKSPACES_TAR
    if not by_seat and archive.is_file():
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar:
                parts = member.name.lstrip("./").split("/")
                if not (
                    member.isfile()
                    and len(parts) == 4
                    and parts[0] == "agents"
                    and parts[2] == "sessions"
                    and parts[3].endswith(".jsonl")
                ):
                    continue
                handle = tar.extractfile(member)
                if handle is not None:
                    by_seat.setdefault(parts[1], []).append(
                        (parts[3], handle.read().decode("utf-8", "replace"))
                    )
    return {seat: sorted(files) for seat, files in by_seat.items()}


def scored_sessions(
    run_dir: Path, session_counts: Mapping[str, Any] | None
) -> list[tuple[str, str, str]] | None:
    """`(seat, file name, text)` of the scored attempt's sessions, or None when the run dir keeps none.

    With `session_counts` (from `episode.json`) only each seat's last `session_counts[seat]` files are
    kept; without it every session file counts (the audit's fallback). A Modal-packed run dir's sessions
    are read from its `workspaces.tar.gz`.
    """
    by_seat = _sessions_by_seat(run_dir)
    if not by_seat:
        return None
    if not session_counts:
        return [(seat, name, text) for seat, files in by_seat.items() for name, text in files]
    kept: list[tuple[str, str, str]] = []
    for seat, count in session_counts.items():
        k = int(count)
        if k > 0:
            kept += [
                (str(seat), name, text) for name, text in by_seat.get(str(seat), [])[-k:]
            ]
    return kept


def turns_ended_by_error(
    run_dir: Path, session_counts: Mapping[str, Any] | None
) -> int | None:
    """Seat turns of the scored attempt that ended on a provider error; None when no session is kept.

    A positive count excludes the episode under rule T (`report.is_clean`).
    """
    sessions = scored_sessions(run_dir, session_counts)
    if sessions is None:
        return None
    return sum(session_stats(text).turns_ended_by_error for _seat, _name, text in sessions)


def key_rejected(error_message: str) -> bool:
    """A pi error message of the provider refusing the key: 401 `authentication_error` / 403 `permission_error`.

    E.g. `401 {"type":"error","error":{"type":"authentication_error","message":"API key is invalid."}}`.
    """
    return (
        "authentication_error" in error_message
        or "permission_error" in error_message
        or error_message.startswith(("401", "403"))
    )


def rejected_key_errors(
    run_dir: Path, session_counts: Mapping[str, Any] | None
) -> int:
    """Assistant messages of the scored attempt's sessions that ended on the provider refusing the key.

    Such an attempt is not a transient failure: every re-drive fails the same way (`_drive` stops instead).
    """
    count = 0
    for _seat, _name, text in scored_sessions(run_dir, session_counts) or []:
        for line in text.splitlines():
            try:
                parsed: Any = json.loads(line)
            except ValueError:
                continue
            if not isinstance(parsed, dict):
                continue
            message = cast(dict[str, Any], parsed).get("message")
            if (
                isinstance(message, dict)
                and cast(dict[str, Any], message).get("stopReason") == "error"
                and key_rejected(str(cast(dict[str, Any], message).get("errorMessage", "")))
            ):
                count += 1
    return count


__all__ = [
    "WORKSPACES_TAR",
    "SessionStats",
    "key_rejected",
    "rejected_key_errors",
    "scored_sessions",
    "session_stats",
    "turns_ended_by_error",
]
