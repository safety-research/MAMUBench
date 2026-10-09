"""Mechanical beat delivery bookkeeping (the harness invariant: delivered ⊆ rendered).

Generalizes the delivery pipeline the gpu-contention router proved out: a fired beat is `push`ed, a resume
`drain`s it into an awaiting-confirmation buffer (its text is staged as a user turn), and only when that
turn actually RENDERS does `confirm` log it delivered; a bounced/withheld resume `requeue`s it instead, so a
beat is never recorded as seen by a turn that never happened, and never lost.

Wire the three router hooks straight through: `deliver_beats -> drain`, `on_turn_completed -> confirm`,
`on_resume_bounced -> requeue`.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from itertools import count


@dataclass
class BeatQueue:
    """Per-agent FIFO of fired-but-not-yet-rendered beats, deduped by beat id."""

    _pending: dict[str, list[tuple[str, str]]] = field(
        default_factory=dict[str, list[tuple[str, str]]]
    )
    _awaiting: dict[str, list[tuple[str, str]]] = field(
        default_factory=dict[str, list[tuple[str, str]]]
    )
    _seen: set[str] = field(default_factory=set[str])
    #: Push order per beat id — the fire order, since the world pushes a beat the moment it fires. Backs the
    #: arrival-order wake priority (`oldest_pending_agent`); a requeued beat keeps its original position.
    _fired_at: dict[str, int] = field(default_factory=dict[str, int])
    _seq: Iterator[int] = field(default_factory=count)
    #: Called as `(agent, beat_ids)` the moment beats are staged into that agent's turn — the earliest point
    #: anything can know the agent is about to SEE them. A world with state that the rendered turn itself
    #: reads has to hang it here: `confirm` fires from `on_turn_completed`, after the agent has acted, and
    #: the push is earlier still (a beat can sit queued through several of the agent's own turns before it
    #: is shown). clinic_access hangs call liveness on it — a desk must be able to answer the caller on the
    #: turn it first reads the intake. On the queue rather than at each call site so that no drain path can
    #: quietly skip it.
    on_drain: Callable[[str, tuple[str, ...]], None] | None = None

    def push(self, agent: str, beat_id: str, text: str) -> bool:
        """Queue a fired beat for `agent`; a duplicate `beat_id` is ignored (returns False)."""
        if beat_id in self._seen:
            return False
        self._seen.add(beat_id)
        self._fired_at[beat_id] = next(self._seq)
        self._pending.setdefault(agent, []).append((beat_id, text))
        return True

    def drain(self, agent: str) -> list[str]:
        """Move `agent`'s pending beats to awaiting-confirmation and return their texts (staging order)."""
        beats = self._pending.pop(agent, [])
        if beats:
            self._awaiting.setdefault(agent, []).extend(beats)
            if self.on_drain is not None:
                self.on_drain(agent, tuple(beat_id for beat_id, _ in beats))
        return [text for _, text in beats]

    def confirm(self, agent: str) -> list[str]:
        """The turn rendered: clear `agent`'s awaiting beats, returning their ids (log them delivered now)."""
        return [beat_id for beat_id, _ in self._awaiting.pop(agent, [])]

    def requeue(self, agent: str) -> None:
        """The resume bounced before rendering: put `agent`'s awaiting beats back at the FRONT of pending."""
        beats = self._awaiting.pop(agent, [])
        if beats:
            self._pending[agent] = beats + self._pending.get(agent, [])

    def has_pending(self, agent: str) -> bool:
        return bool(self._pending.get(agent))

    def has_outstanding(self, agent: str) -> bool:
        """True while `agent` has any beat pending OR awaiting confirmation (per-agent `outstanding`)."""
        return bool(self._pending.get(agent)) or bool(self._awaiting.get(agent))

    def first_pending_agent(self, ids: tuple[str, ...]) -> str | None:
        """The first agent (in `ids` order) with an undelivered beat — the `wake_priority` target."""
        return next((i for i in ids if self._pending.get(i)), None)

    def oldest_pending_agent(self, ids: tuple[str, ...]) -> str | None:
        """The agent whose HEAD pending beat fired earliest (ties broken in `ids` order): arrival-order wake priority.

        `first_pending_agent` serves the roster in id order, which is harmless while a balance gate rotates to the least-run agent but starves the back of the roster once that gate is off: an early desk's follow-ups always outrank a later desk's untouched intake (in a smoke run with the gate off, 34 of 52 desks never resumed). Arrival order is the world's own queue discipline — the caller who has waited longest is answered first.
        """
        best: tuple[int, int, str] | None = None
        for index, agent in enumerate(ids):
            beats = self._pending.get(agent)
            if not beats:
                continue
            key = (self._fired_at.get(beats[0][0], -1), index, agent)
            if best is None or key < best:
                best = key
        return best[2] if best is not None else None

    def outstanding(self) -> bool:
        """True while ANY beat is still pending or awaiting confirmation (an `is_over` guard)."""
        return any(self._pending.values()) or any(self._awaiting.values())
