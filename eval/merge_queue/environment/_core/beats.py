# Vendored verbatim from the authors' research code (the shared env core's beats module).
"""Mechanical beat delivery bookkeeping (the harness invariant: delivered ⊆ rendered).

Generalizes the delivery pipeline the gpu-contention router proved out: a fired beat is `push`ed, a resume
`drain`s it into an awaiting-confirmation buffer (its text is staged as a user turn), and only when that
turn actually RENDERS does `confirm` log it delivered; a bounced/withheld resume `requeue`s it instead, so a
beat is never recorded as seen by a turn that never happened, and never lost.

Wire the three router hooks straight through: `deliver_beats -> drain`, `on_turn_completed -> confirm`,
`on_resume_bounced -> requeue`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BeatQueue:
    """Per-agent FIFO of fired-but-not-yet-rendered beats, deduped by beat id."""

    _pending: dict[str, list[tuple[str, str]]] = field(default_factory=dict[str, list[tuple[str, str]]])
    _awaiting: dict[str, list[tuple[str, str]]] = field(default_factory=dict[str, list[tuple[str, str]]])
    _seen: set[str] = field(default_factory=set[str])

    def push(self, agent: str, beat_id: str, text: str) -> bool:
        """Queue a fired beat for `agent`; a duplicate `beat_id` is ignored (returns False)."""
        if beat_id in self._seen:
            return False
        self._seen.add(beat_id)
        self._pending.setdefault(agent, []).append((beat_id, text))
        return True

    def drain(self, agent: str) -> list[str]:
        """Move `agent`'s pending beats to awaiting-confirmation and return their texts (staging order)."""
        beats = self._pending.pop(agent, [])
        if beats:
            self._awaiting.setdefault(agent, []).extend(beats)
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

    def first_pending_agent(self, ids: tuple[str, ...]) -> str | None:
        """The first agent (in `ids` order) with an undelivered beat — the `wake_priority` target."""
        return next((i for i in ids if self._pending.get(i)), None)

    def outstanding(self) -> bool:
        """True while ANY beat is still pending or awaiting confirmation (an `is_over` guard)."""
        return any(self._pending.values()) or any(self._awaiting.values())
