"""Decision-free simultaneous relay: concurrent B0, pushed DMs, commit or quiescence."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol

from personal_assistant.environment.worlds import (  # noqa: E402
    Cell,
    cell_diners,
    seat_debrief,
    seat_opening_brief,
)

_POLL_SECONDS = 0.5


@dataclass(frozen=True)
class RelayPrompt:
    """One principal-authored prompt delivered by the decision-free relay."""

    principal: str
    text: str


class PushScenario(Protocol):
    """Domain adapter for a push-driven shared-plan episode."""

    def opening(self, seat: str) -> RelayPrompt:
        """Return the seat's initial principal brief."""
        ...

    def debrief(self, seat: str) -> RelayPrompt:
        """Return the seat's post-commit principal receipt prompt."""
        ...


class PushEpisode(Protocol):
    """Minimal runtime contract shared by the food and trip MCP domains."""

    ids: tuple[str, ...]
    crashed: dict[str, str]
    turn_timeout: float
    record_turn_text: bool

    def ensure_started(self) -> None: ...

    def turn(self, seat: str, prompt: str) -> object: ...

    def status(self) -> dict[str, Any]: ...

    def dm_drain(self, seat: str) -> list[str]: ...

    def dm_requeue(self, seat: str, rows: list[str]) -> None: ...

    def record_diner_msg(
        self, seat: str, principal: str, beat: str, text: str
    ) -> None: ...

    def post_event(self, body: dict[str, Any]) -> None: ...


class DecisionFreeRelay:
    """Run one auditorless push episode without rounds, cron, or a fake deadline."""

    def __init__(
        self,
        episode: PushEpisode,
        scenario: PushScenario,
        *,
        hard_cap_s: float = 2700.0,
        deadline_s: float | None = None,
    ) -> None:
        self.episode = episode
        self.scenario = scenario
        self.hard_cap_s = hard_cap_s
        #: Optional in-fiction booking-window cutoff, measured from B0 dispatch.
        #: `None` (the default) preserves the original commit-or-quiescence
        #: semantics exactly; the ops hard cap stays as the backstop above it.
        self.deadline_s = deadline_s
        self.threads: dict[str, threading.Thread] = {}
        self.pending_retry: dict[str, tuple[str, str]] = {}
        self.turns = 0
        self._count_lock = threading.Lock()

    def _live(self) -> list[str]:
        return [seat for seat in self.episode.ids if seat not in self.episode.crashed]

    def _running(self) -> list[str]:
        return [seat for seat, thread in self.threads.items() if thread.is_alive()]

    def _turn(self, seat: str, prompt: str, reason: str) -> None:
        started = time.time()
        try:
            self.episode.turn(seat, prompt)
        except RuntimeError as exc:
            if type(exc).__name__ == "TransientSeatError":
                if reason == "dm":
                    self.episode.dm_requeue(seat, prompt.split("\n\n"))
                else:
                    self.pending_retry[seat] = (prompt, reason)
        except TimeoutError:
            pass
        finally:
            with self._count_lock:
                self.turns += 1
            self.episode.post_event(
                {
                    "kind": "turn_span",
                    "seat": seat,
                    "payload": {
                        "wake_reason": reason,
                        "t_start_wall": round(started, 3),
                        "t_end_wall": round(time.time(), 3),
                    },
                }
            )

    def _wake(self, seat: str, prompt: str, reason: str) -> None:
        thread = threading.Thread(
            target=self._turn,
            args=(seat, prompt, reason),
            name=f"conf-{seat}-{reason}",
            daemon=True,
        )
        self.threads[seat] = thread
        thread.start()

    def run(self) -> str:
        """Return the terminal ending for one push episode.

        `committed`, `no_decision`, `ops_timeout`, or `transport_failure`; a relay
        constructed with `deadline_s` may also return `deadline_expired` (the window
        elapsed before a commit: new wakes stop, in-flight turns join, and a commit
        that still lands wins).
        """
        self.episode.record_turn_text = True
        self.episode.ensure_started()
        for seat in self._live():
            prompt = self.scenario.opening(seat)
            self.episode.record_diner_msg(seat, prompt.principal, "B0", prompt.text)
            self._wake(seat, prompt.text, "b0")

        began = time.monotonic()
        ending = "ops_timeout"
        while time.monotonic() - began < self.hard_cap_s:
            time.sleep(_POLL_SECONDS)
            status = self.episode.status()
            if int(status.get("orders_placed", 0)) == 1:
                ending = "committed"
                break

            if (
                self.deadline_s is not None
                and time.monotonic() - began > self.deadline_s
            ):
                ending = "deadline_expired"
                break

            if not self._live():
                # every seat is down (crashed, or refused by the provider): nothing can wake again
                break

            running = self._running()
            woke = False
            for seat in self._live():
                if seat in running:
                    continue
                retry = self.pending_retry.pop(seat, None)
                if retry is not None:
                    self._wake(seat, *retry)
                    woke = True
                    continue
                if int(status.get("dm_pending", {}).get(seat, 0)):
                    lines = self.episode.dm_drain(seat)
                    if lines:
                        self._wake(seat, "\n\n".join(lines), "dm")
                        woke = True

            if not woke and not self._running() and not self.pending_retry:
                final_status = self.episode.status()
                if not any(int(v) for v in final_status.get("dm_pending", {}).values()):
                    ending = (
                        "transport_failure" if self.episode.crashed else "no_decision"
                    )
                    break

        for thread in self.threads.values():
            thread.join(timeout=self.episode.turn_timeout + 30)
        if ending == "ops_timeout" and self.episode.crashed:
            ending = "transport_failure"
        if int(self.episode.status().get("orders_placed", 0)) == 1:
            ending = "committed"
            self._debrief()
        self.episode.post_event(
            {
                "kind": "sim_done",
                "seat": None,
                "payload": {"ending": ending, "turns": self.turns},
            }
        )
        return ending

    def _debrief(self) -> None:
        """Send the committed receipt as one final concurrent wake, then stop."""
        for seat in self._live():
            lines = self.episode.dm_drain(seat)
            prompt = self.scenario.debrief(seat)
            self.episode.record_diner_msg(seat, prompt.principal, "B3", prompt.text)
            self._wake(seat, "\n\n".join([*lines, prompt.text]), "debrief")
        for thread in self.threads.values():
            thread.join(timeout=self.episode.turn_timeout + 30)


class _FoodScenario:
    """Adapt a food `Cell` to the shared push-relay contract.

    `deadline_line` (deadline cells only) is the one soft-window sentence from the
    scenario module's `CELL_CONFIG`; it is appended to every seat's B0 opening
    brief. `None` (the default) leaves every brief byte-identical to before.
    """

    def __init__(self, cell: Cell, *, deadline_line: str | None = None) -> None:
        self.cell = cell
        self.deadline_line = deadline_line
        self.diners = cell_diners(cell)

    def _principal(self, seat: str) -> str:
        """The ledger label for the seat's briefing principal.

        Mesh: the seat's own diner. Steward: the pooled "team" label. Solo: Maya, the
        one organizer principal the `bat_*_solo` construction briefs through.
        """
        if self.cell.topology == "solo":
            from personal_assistant.environment.food.resources import ORGANIZER_FIRST

            return ORGANIZER_FIRST
        diner = next((row for row in self.diners if row.id == seat), None)
        return diner.first if diner is not None else "team"

    def opening(self, seat: str) -> RelayPrompt:
        text = seat_opening_brief(self.cell, seat, self.diners)
        if self.deadline_line is not None:
            text = f"{text}\n\n{self.deadline_line}"
        return RelayPrompt(principal=self._principal(seat), text=text)

    def debrief(self, seat: str) -> RelayPrompt:
        return RelayPrompt(
            principal=self._principal(seat),
            text=seat_debrief(self.cell, seat, self.diners),
        )


class SimultaneousRelay(DecisionFreeRelay):
    """Backward-compatible food adapter over the generic push relay.

    Deadline cells pass `deadline_s` (the enforced order window, seconds from B0
    dispatch — the relay finalizes as `deadline_expired` unless a commit landed
    first) and `deadline_line` (the CELL_CONFIG brief sentence). The defaults
    preserve the original commit-or-quiescence semantics and briefs exactly.
    """

    def __init__(
        self,
        episode: PushEpisode,
        cell: Cell,
        *,
        hard_cap_s: float = 2700.0,
        deadline_s: float | None = None,
        deadline_line: str | None = None,
    ) -> None:
        super().__init__(
            episode,
            _FoodScenario(cell, deadline_line=deadline_line),
            hard_cap_s=hard_cap_s,
            deadline_s=deadline_s,
        )
