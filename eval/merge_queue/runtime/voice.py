"""Reply-only user voicing contract for live episodes.

A voicer answers only after a completed agent turn, sees only that agent's
private operator channel plus public PR status, and returns at most one owner
reply (or `None`). Load-bearing pressure stays scripted and verbatim; the
voicer exists so a target that asks its operator a direct question does not
meet unexplained silence. The captain is never voiced: captain authority
exists only as scripted steps, and the mechanical approval check (captain
actor + marker comment) makes a voiced approval impossible by construction.

A voiced reply is consumed a full turn after it is produced -- staged as a
beat, drained at that agent's *next* wake -- so the call does not belong on
the turn loop's critical path. `DeferredVoicer` moves it between those two
points; see that class for why that is a wall-clock change and not a scenario
change.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from merge_queue.environment._core.users import PersonaCard

ChannelRole = str  # "owner" | "agent"


@dataclass(frozen=True)
class VoiceRequest:
    """Everything a reply-only voicer may see for one completed agent turn."""

    agent_id: str
    minute: int
    personas: tuple[PersonaCard, ...]
    channel: tuple[tuple[ChannelRole, str], ...]
    pr_status_lines: tuple[str, ...]


#: Must be thread-safe: `DeferredVoicer` may have one call per seat in flight.
Voicer = Callable[[VoiceRequest], str | None]


@runtime_checkable
class JoinRecorder(Protocol):
    """A voicer that also logs what the driver's wait for a deferred call cost.

    Deferring hides the call behind peer turns, so the call's own duration stops
    being what the episode paid for it. `waited_seconds` is what it actually
    paid; the overlap is the difference between that and the call duration the
    voicer already logs.
    """

    def record_join(
        self,
        agent_id: str,
        *,
        minute: int,
        waited_seconds: float,
        timed_out: bool,
    ) -> None:
        """Record that `agent_id`'s deferred call was joined at sim-minute `minute`."""
        ...


class DeferredVoicer:
    """Run a `Voicer` off the driver's critical path, one call per agent in flight.

    The driver builds a `VoiceRequest` when an agent's turn ends but cannot use
    the reply until that agent's next wake, three peer turns later. Voicing is
    ~3s of network wait against a ~40s turn, so doing it inline costs ~22% of
    episode wall-clock (measured over 63 g3/g4 episodes) for a reply that sits
    idle either way.

    `submit` snapshots the request -- byte-identical to the synchronous
    construction, since `VoiceRequest` is frozen and built at the same point --
    and starts the call in a worker thread. `take` blocks for that agent's
    result at its next wake, before any beat is drained.

    Only the voicer call itself moves off-thread. Every world/beat mutation
    still happens on the driver thread inside `take`, in the same per-agent
    order, so what an agent sees and when it sees it are unchanged. What does
    move is where the resulting `user_message`/`beat_status` pair lands in the
    ledger: after that round's peer turns rather than interleaved with them.
    Neither type is a `notification_events` type, so no peer's digest can
    observe the difference, and nothing in the driver reads beat pendency, so
    the wake rotation cannot either.

    A voicer exception is re-raised from `take`; the driver swallows it exactly
    as it swallowed the synchronous one. Every join is bounded by
    `join_timeout`, so a hung call cannot reintroduce the stall this removes:
    on timeout the join is recorded, nothing is delivered, and the episode goes
    on. `discard` hands a retired seat's call to `close`, which joins and
    records it too, so `voicer.jsonl` ends complete for every call fired.

    Two consequences for `Voicer` implementations: a call per seat can now be in
    flight at once, so a voicer must be thread-safe; and `max_workers` must stay
    above the seat count or submits would queue behind each other and quietly
    re-serialize. A voicer that also implements `JoinRecorder` is told what each
    join cost the driver, which is what makes serial-vs-overlapped time
    computable after the fact.
    """

    def __init__(
        self,
        voicer: Voicer,
        *,
        join_timeout: float = 300.0,
        max_workers: int = 8,
    ) -> None:
        self._voicer = voicer
        # Above the voicer's own compound worst case (SonnetVoicer: 60s timeout
        # x 2 tries x 2 attempts ~= 245s), so a healthy call is never cut short
        # and a wedged one is still bounded.
        self._join_timeout = join_timeout
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="voicer"
        )
        self._pending: dict[str, Future[str | None]] = {}
        self._orphaned: list[tuple[str, Future[str | None]]] = []

    def submit(self, request: VoiceRequest) -> None:
        """Start `request` in the background as `request.agent_id`'s pending call."""
        if request.agent_id in self._pending:
            raise RuntimeError(
                f"voice already in flight for {request.agent_id!r}; "
                "take() it before the agent's next turn"
            )
        self._pending[request.agent_id] = self._pool.submit(self._voicer, request)

    def pending_agents(self) -> tuple[str, ...]:
        """Agents with a call out, in submission order (this round's wake order)."""
        return tuple(self._pending)

    def take(self, agent_id: str, *, minute: int) -> str | None:
        """Block for `agent_id`'s pending reply, or `None` when it has no call out."""
        pending = self._pending.pop(agent_id, None)
        return None if pending is None else self._join(agent_id, pending, minute)

    def discard(self, agent_id: str) -> None:
        """Stop waiting on `agent_id`'s call here; `close` still joins and records it."""
        pending = self._pending.pop(agent_id, None)
        if pending is not None:
            self._orphaned.append((agent_id, pending))

    def close(self, *, minute: int) -> None:
        """Join and record every call still out, then release the pool.

        The bound is per call rather than overall: the voicer's own timeout
        discipline is what keeps the total finite, and cutting a call short here
        would only lose its accounting row.
        """
        outstanding = [*self._pending.items(), *self._orphaned]
        self._pending.clear()
        self._orphaned.clear()
        for agent_id, pending in outstanding:
            try:
                self._join(agent_id, pending, minute)
            except Exception:
                # Already recorded by `_join`; teardown must not raise.
                pass
        self._pool.shutdown(wait=True)

    def _join(
        self, agent_id: str, pending: Future[str | None], minute: int
    ) -> str | None:
        """Wait out one call, telling a `JoinRecorder` voicer what the wait cost."""
        started = time.monotonic()
        timed_out = False
        try:
            return pending.result(timeout=self._join_timeout)
        except TimeoutError:
            timed_out = True
            return None
        finally:
            if isinstance(self._voicer, JoinRecorder):
                self._voicer.record_join(
                    agent_id,
                    minute=minute,
                    waited_seconds=time.monotonic() - started,
                    timed_out=timed_out,
                )


__all__ = [
    "ChannelRole",
    "DeferredVoicer",
    "JoinRecorder",
    "VoiceRequest",
    "Voicer",
]
