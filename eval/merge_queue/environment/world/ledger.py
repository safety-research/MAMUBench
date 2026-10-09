"""Versioned append-only accounting ledger for the merge-queue world."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import cast

LEDGER_VERSION = 1
_RESERVED_FIELDS = frozenset({"v", "seq", "minute", "type"})


class LedgerError(ValueError):
    """Raised when a ledger is malformed or an invalid event is appended."""


class EventLedger:
    """Write ordered JSONL events and keep an in-memory read view.

    A fresh world requires a fresh ledger path. This is intentional: sample-level
    resume rebuilds an episode rather than attempting to resume live processes.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self._events: list[dict[str, object]] = []
        if path.exists() and path.stat().st_size:
            raise LedgerError(f"refusing to append a new episode to {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

    @property
    def events(self) -> tuple[Mapping[str, object], ...]:
        """Return an immutable view of events written so far."""
        with self._lock:
            return tuple(dict(event) for event in self._events)

    def append(
        self,
        event_type: str,
        minute: int,
        payload: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        """Append and return one event."""
        if not event_type:
            raise LedgerError("event type must be non-empty")
        if minute < 0:
            raise LedgerError("event minute must be non-negative")
        data = dict(payload or {})
        collision = _RESERVED_FIELDS.intersection(data)
        if collision:
            names = ", ".join(sorted(collision))
            raise LedgerError(f"payload overrides reserved ledger fields: {names}")
        with self._lock:
            event: dict[str, object] = {
                "v": LEDGER_VERSION,
                "seq": len(self._events) + 1,
                "minute": minute,
                "type": event_type,
                **data,
            }
            line = json.dumps(event, sort_keys=True, separators=(",", ":"))
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(line + "\n")
                stream.flush()
            self._events.append(event)
            return dict(event)


def read_ledger(path: Path) -> tuple[Mapping[str, object], ...]:
    """Read and validate a version-1 JSONL ledger."""
    if not path.exists():
        raise LedgerError(f"ledger does not exist: {path}")
    events: list[Mapping[str, object]] = []
    previous_minute = -1
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        try:
            decoded = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise LedgerError(f"invalid JSON at {path}:{line_number}") from exc
        if not isinstance(decoded, dict):
            raise LedgerError(f"ledger event {line_number} is not an object")
        event = cast(dict[str, object], decoded)
        expected_seq = len(events) + 1
        if event.get("v") != LEDGER_VERSION:
            raise LedgerError(f"unsupported ledger version at event {expected_seq}")
        if event.get("seq") != expected_seq:
            raise LedgerError(f"non-contiguous ledger sequence at event {expected_seq}")
        minute = event.get("minute")
        if not isinstance(minute, int) or isinstance(minute, bool) or minute < 0:
            raise LedgerError(f"invalid minute at event {expected_seq}")
        if minute < previous_minute:
            raise LedgerError(f"ledger time moved backwards at event {expected_seq}")
        event_type = event.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise LedgerError(f"invalid type at event {expected_seq}")
        previous_minute = minute
        events.append(event)
    return tuple(events)


def validate_events(
    events: Iterable[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    """Validate already-loaded events using the same ordering invariants."""
    materialized = tuple(events)
    previous_minute = -1
    for expected_seq, event in enumerate(materialized, start=1):
        if event.get("v") != LEDGER_VERSION or event.get("seq") != expected_seq:
            raise LedgerError(f"invalid ledger envelope at event {expected_seq}")
        minute = event.get("minute")
        event_type = event.get("type")
        if not isinstance(minute, int) or isinstance(minute, bool):
            raise LedgerError(f"invalid minute at event {expected_seq}")
        if minute < previous_minute:
            raise LedgerError(f"ledger time moved backwards at event {expected_seq}")
        if not isinstance(event_type, str) or not event_type:
            raise LedgerError(f"invalid type at event {expected_seq}")
        previous_minute = minute
    return materialized
