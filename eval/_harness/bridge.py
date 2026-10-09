"""The world side of a real-harness episode: an env's own router/world, hosted outside any eval runtime.

One `EpisodeBridge` = one episode's deterministic world (either env), built by an env's `cells.py`
(`api_key/cells.py`, `clinic/cells.py`) from the same spec builders the simulated harness's cells use. The bridge
exposes the small surface the pi fleet needs: typed-tool dispatch, the peer mailbox, the per-turn
beat/notification/mail delivery discipline (delivered ⊆ rendered), and the end-of-day flow.

Parity notes (kept in lock-step with the vendored `_multiagent_pi/routing.py` resume loop):
- Prompt staging order is the sim's: handoff → queued mail → world notifications → beats, one message.
- The mailbox lives here (the sim keeps it in the harness, not the router) — validation is the SAME
  `validate_send_message`, delivery the same `[message from <sender>] <msg>` framing, and the router
  ledgers sends/deliveries through the same `on_dm`/`on_deliver` hooks.
- Routers read exactly two `nstate` keys (`mailbox`, `started`) — both owned here.
- Optional router hooks (`may_end`, `note_turn`, `finalize_world`, `withhold`, `note_generation`,
  `on_deliver`, `on_dm_undeliverable`, `deliver_notifications`) are probed with `getattr`, mirroring the
  sim's routing convention — the api_key world implements all of them, the clinic a subset.

The per-turn WAIT BUDGET: a real harness turn is one uncuttable agentic burst (the sim bounds a seat's
monopoly with its resume-burst cap + wake rotation), so without a cap one seat's wait/standby loop can
advance the shared clock through the whole episode before any peer wakes (an early docker smoke run
went from clock 0 to 915 in one turn). The budget caps the cumulative sim-minutes one turn's wait-tool
calls may advance; an exhausted budget answers with the env's own terse denial (`EnvCell.wait_limit_error`)
— a silent zero-grant taught targets that waiting was broken, which was worse.

Thread-safety: one `RLock` over the public surface. Tool calls arrive on server handler threads while the
runner drives turns from the main thread — normally strictly alternating, but a watchdog-killed turn can
leave an in-flight `dispatch` racing the runner's `end_turn(rendered=False)`.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, cast

# The vendored stack's own mailbox validator and spec type (the sim cells' resume loop uses the same).
from _multiagent_pi.routing import (
    _validate_send_message as validate_send_message,  # noqa: E402  # pyright: ignore[reportPrivateUsage]
)
from _multiagent_pi.scenario import ScenarioSpec  # noqa: E402
from inspect_ai.tool import ToolCall


class Router(Protocol):
    """The required slice of the env routers (optional hooks are probed with `getattr`)."""

    def route(self, agent_id: str, call: ToolCall) -> str | None: ...
    def on_resume(self, agent_id: str) -> None: ...
    def notices(self) -> list[str]: ...
    def summary(self) -> dict[str, Any]: ...
    def deliver_beats(self, agent_id: str) -> list[str]: ...
    def on_turn_completed(self, agent_id: str) -> None: ...
    def on_resume_bounced(self, agent_id: str) -> None: ...
    def wake_priority(self, nstate: dict[str, Any]) -> str | None: ...
    def is_over(self) -> bool: ...
    def on_dm(self, sender_id: str, to_id: str, msg: str) -> None: ...


def fresh_nstate(agent_ids: tuple[str, ...]) -> dict[str, Any]:
    """The two harness-state keys every router reads (`mailbox`, `started`), empty."""
    return {
        "mailbox": {i: [] for i in agent_ids},
        "started": {i: False for i in agent_ids},
    }


@dataclass(frozen=True)
class EnvCell:
    """One episode's env-specific bundle, produced by an env's `cells.py`.

    Attributes:
        env: `"api_key"` or `"clinic"`.
        framing: The cell's toolset framing (`console` everywhere; api_key may run `pi`).
        spec: The scenario spec (agents, tools, prompts) — byte-identical to the simulated harness's cells.
        router: The deterministic router over a fresh world, bound to `nstate`.
        nstate: The harness state dict shared with the router (`mailbox`, `started`).
        wait_tool: The env's clock lever (`labctl_wait` / `clinic_standby`), or None for no budget.
        wait_limit_error: The env-voiced denial for a wait past the turn budget (leak-linted).
        clamp_wait_args: Env hook — clamp a wait call's args to the remaining budget (identity for an
            argument-less wait tool like `clinic_standby`).
        window_min: The world horizon in sim-minutes (`past_window` for the crashed-seat wrap-up).
        clock_hhmm: Renders a sim-minute clock as the `[HH:MM]` continuation stamp.
        native_tools: Harness-native tool names excluded from the typed manifest (empty for both
            console cells; kept as the seam for a framing with real shell tools).
        idle_advance: Advance the world through a fully idle round, the env's own way (api_key:
            `world.advance(minutes)`; clinic: an A54 standby-creep on one desk's behalf — the
            explicit-time contract forbids non-standby drift).
        rounds_max_default / turn_wait_budget_default / turn_timeout_default: Runner defaults tuned per
            env (a clinic morning is 240 sim-minutes; a cluster night is 990).
    """

    env: str
    framing: str
    spec: ScenarioSpec
    router: Router
    nstate: dict[str, Any]
    wait_tool: str | None
    wait_limit_error: str
    clamp_wait_args: Callable[[dict[str, Any], int], dict[str, Any]]
    window_min: int
    clock_hhmm: Callable[[int], str]
    native_tools: frozenset[str]
    idle_advance: Callable[[Router, str, int], None]
    rounds_max_default: int
    turn_wait_budget_default: int
    turn_timeout_default: float
    #: Cumulative wait-tool sim-minutes ALL seats together may advance in one lockstep round (None =
    #: only the per-turn budget). Explicit-time worlds with many seats need it: N seats each waiting
    #: their per-turn budget on one shared clock can end a shift inside a single round.
    round_wait_budget_default: int | None = None


@dataclass
class TurnDelivery:
    """What `begin_turn` staged for a seat, so `end_turn` can confirm or requeue it."""

    seat: str
    prompt: str
    first_wake: bool
    #: Raw (sender_username, message) rows drained from the mailbox — confirmed as delivered on a
    #: rendered turn (`on_deliver`, sender id re-resolved from the username), requeued on a bounce.
    drained_mail: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])


class EpisodeBridge:
    """One episode's deterministic world plus the fleet-facing discipline around it.

    Args:
        cell: The env bundle (spec + router + policies) from the env's `cells.py`.
        ledger_path: Where the harness-level event ledger (JSONL) is appended.
        turn_wait_budget: Cumulative wait-tool sim-minutes one turn may advance (None = uncapped).
        round_wait_budget: Cumulative wait-tool sim-minutes one lockstep ROUND (all seats) may advance
            (None = uncapped); the runner calls `begin_round()` to reset it.
    """

    def __init__(
        self,
        cell: EnvCell,
        *,
        ledger_path: Path,
        turn_wait_budget: int | None,
        round_wait_budget: int | None = None,
    ) -> None:
        self.cell = cell
        self.spec = cell.spec
        self.ids: tuple[str, ...] = tuple(a.id for a in self.spec.agents)
        self.nstate = cell.nstate
        self.router = cell.router
        self.usernames: dict[str, str] = {a.id: a.username for a in self.spec.agents}
        self.recipients: dict[str, str] = {}
        for a in self.spec.agents:
            self.recipients[a.username.lower()] = a.id
            self.recipients[a.display_name.lower()] = a.id
        self.allowed_recipients = (
            dict(self.spec.allowed_recipients)
            if self.spec.allowed_recipients is not None
            else None
        )
        self._handoffs: dict[str, str] = {a.id: a.handoff for a in self.spec.agents}
        self._cwds: dict[str, str] = {a.id: a.cwd for a in self.spec.agents}
        self._system_prompts: dict[str, str | None] = {
            a.id: a.system_prompt for a in self.spec.agents
        }
        self._counts: dict[str, int] = {i: 0 for i in self.ids}
        self._last_turn_had_tool_calls: dict[str, bool] = {i: True for i in self.ids}
        self._ledger_path = ledger_path
        self._seq = 0
        self._summary: dict[str, Any] | None = None
        self._turn_wait_budget = turn_wait_budget
        self._turn_wait_left = turn_wait_budget
        self._round_wait_budget = round_wait_budget
        self._round_wait_left = round_wait_budget
        self._lock = threading.RLock()

    def begin_round(self) -> None:
        """Reset the shared per-round wait budget (the runner calls this at the top of every round)."""
        with self._lock:
            self._round_wait_left = self._round_wait_budget

    # ── manifest / workspace surface ─────────────────────────────────────────────────────────────────────
    def tools_manifest(self) -> list[dict[str, Any]]:
        """The typed toolset as JSON tool specs for the pi extension (name/description/parameters).

        Harness-native tools (`cell.native_tools`) are excluded — they stay real. Everything else is
        registered as a custom tool that round-trips to this bridge, byte-identical schemas to the
        simulated harness's cells.
        """
        tools: list[dict[str, Any]] = []
        for tool in self.spec.target_tools():
            if tool.name in self.cell.native_tools:
                continue
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters.model_dump(exclude_none=True),
                }
            )
        return tools

    def norms_files(self) -> dict[str, str]:
        """Absolute path -> canonical bytes for real files the runner materializes (POLICY.md et al)."""
        norms = getattr(self.router, "norms", None)
        if norms is None:
            return {}
        return {str(p): str(text) for p, text in norms.served.items()}

    def seat_cwd(self, seat: str) -> str:
        """The seat's in-fiction working directory (pi's cwd)."""
        return self._cwds[seat]

    def seat_system_prompt(self, seat: str) -> str | None:
        """The seat's bespoke system prompt (console cells), or None to keep the harness's own."""
        return self._system_prompts[seat]

    # ── clock / status ───────────────────────────────────────────────────────────────────────────────────
    def clock(self) -> int:
        """The current world clock in sim-minutes."""
        return int(cast(Any, self.router).world.clock)

    def clock_hhmm(self) -> str:
        """The world clock rendered `HH:MM`, for continuation-prompt timestamps."""
        return self.cell.clock_hhmm(self.clock())

    def is_over(self) -> bool:
        """Whether the world reports the episode over (horizon reached, deliveries settled)."""
        return bool(self.router.is_over())

    def past_window(self) -> bool:
        """Whether the clock has passed the episode window, regardless of delivery debts.

        `is_over()` can additionally require every debrief RENDERED — which can never happen once a seat
        has crashed. The runner uses this raw clock check to move crashed-seat episodes into the bounded
        wrap-up drain instead of granting alive seats unbounded overtime turns.
        """
        return self.clock() >= self.cell.window_min

    def may_end(self) -> str | None:
        """The router's end-guard: `None` when concluding now is clean, else the blocking reason."""
        may_end = getattr(self.router, "may_end", None)
        return may_end() if may_end is not None else None

    def wake_priority(self) -> str | None:
        """The seat the router wants woken first (an undelivered fired beat), or `None`."""
        return self.router.wake_priority(self.nstate)

    def withheld(self, seat: str) -> str | None:
        """The router's withhold reason for `seat` (quarantine etc.), or `None` if resumable."""
        withhold = getattr(self.router, "withhold", None)
        return withhold(seat) if withhold is not None else None

    def pending_for(self, seat: str) -> bool:
        """Whether `seat` has undelivered mail, a fired beat, or a queued world notification."""
        if self.nstate["mailbox"].get(seat):
            return True
        world = cast(Any, self.router).world
        if bool(world.beat_queue.has_pending(seat)):
            return True
        notice_queue = getattr(world, "notice_queue", None)
        return bool(notice_queue is not None and notice_queue.has_pending(seat))

    def seat_active(self, seat: str) -> bool:
        """Whether the seat's LAST rendered turn made tool calls (the sim's bare-resume refusal)."""
        return self._last_turn_had_tool_calls[seat]

    def idle_nudge(self, minutes: int) -> None:
        """Advance the world through a fully idle round, the env's own way."""
        with self._lock:
            first_alive = self.ids[0]
            self._log("idle_nudge", None, {"minutes": minutes})
            self.cell.idle_advance(self.router, first_alive, minutes)

    def counts(self) -> dict[str, int]:
        """Rendered-turn counts per seat (telemetry + the report's turn accounting)."""
        return dict(self._counts)

    # ── the per-turn discipline ──────────────────────────────────────────────────────────────────────────
    def begin_turn(self, seat: str) -> TurnDelivery:
        """Advance the clock for `seat`'s wake and stage everything it should see this turn.

        Mirrors the sim's resume path: `on_resume` (clock advance / fast-forward) fires BEFORE the
        generation; then the handoff (first wake), queued mail, world notifications, and fired beats
        drain into ONE prompt, in the sim's staging order. The caller must follow with exactly one
        `end_turn(..., rendered=True/False)`.
        """
        with self._lock:
            self.router.on_resume(seat)
            self._turn_wait_left = self._turn_wait_budget
            parts: list[str] = []
            first_wake = not self.nstate["started"][seat]
            if first_wake:
                parts.append(self._handoffs[seat])
            drained_mail: list[tuple[str, str]] = list(
                self.nstate["mailbox"].get(seat, [])
            )
            self.nstate["mailbox"][seat] = []
            for sender, msg in drained_mail:
                parts.append(f"[message from {sender}] {msg}")
            deliver_notifications = getattr(self.router, "deliver_notifications", None)
            if deliver_notifications is not None:
                parts.extend(deliver_notifications(seat))
            parts.extend(self.router.deliver_beats(seat))
            prompt = "\n\n".join(parts) if parts else f"[{self.clock_hhmm()}]"
            self._log(
                "turn_begin",
                seat,
                {
                    "first_wake": first_wake,
                    "mail": len(drained_mail),
                    "prompt_chars": len(prompt),
                },
            )
            return TurnDelivery(
                seat=seat,
                prompt=prompt,
                first_wake=first_wake,
                drained_mail=drained_mail,
            )

    def end_turn(
        self,
        delivery: TurnDelivery,
        *,
        rendered: bool,
        est_tokens: int | None = None,
        had_tool_calls: bool = True,
    ) -> None:
        """Confirm (or roll back) a turn's deliveries and settle its clock/operator effects.

        rendered=True: the harness turn completed — beats/notifications confirm (`on_turn_completed`),
        mail logs delivered (`on_deliver`), the generation is reported (`note_generation`), and a
        text-only turn stages any authored operator reply (`note_turn`). rendered=False (timeout/crash):
        beats/notifications requeue (`on_resume_bounced` — for medical_triage this may also standby-creep
        on the seat's behalf, the router's own A54 semantics), mail requeues at the front, and a first
        wake is undone so the handoff re-stages on the next attempt — delivered ⊆ rendered, exactly the
        sim's contract.
        """
        with self._lock:
            seat = delivery.seat
            if not rendered:
                self.router.on_resume_bounced(seat)
                if delivery.drained_mail:
                    self.nstate["mailbox"][seat] = (
                        delivery.drained_mail + self.nstate["mailbox"][seat]
                    )
                self._log("turn_bounced", seat, {})
                return
            self.nstate["started"][seat] = True
            self._counts[seat] += 1
            if est_tokens is not None:
                # Optional hook — probed like the sim does.
                note_generation = getattr(self.router, "note_generation", None)
                if note_generation is not None:
                    note_generation(seat, max(1, est_tokens))
            on_deliver = getattr(self.router, "on_deliver", None)
            if on_deliver is not None:
                for sender, msg in delivery.drained_mail:
                    on_deliver(seat, self.recipients.get(sender.lower(), sender), msg)
            self.router.on_turn_completed(seat)
            self._last_turn_had_tool_calls[seat] = had_tool_calls
            note_turn = getattr(self.router, "note_turn", None)
            if note_turn is not None:
                note_turn(
                    seat, DuckMessage(tool_calls=[object()] if had_tool_calls else None)
                )
            self._log(
                "turn_end",
                seat,
                {"est_tokens": est_tokens, "had_tool_calls": had_tool_calls},
            )

    # ── tool dispatch (the extension's round-trip) ───────────────────────────────────────────────────────
    def dispatch(self, seat: str, tool: str, args: dict[str, Any]) -> str:
        """Answer one typed tool call from `seat` mechanically; always returns rendered text.

        `SendMessage` runs the harness-level mailbox (same validation + ledger hooks as the sim); the
        env's wait tool goes through the per-turn wait budget; every other registered tool goes straight
        to `router.route`.
        """
        with self._lock:
            self._seq += 1
            call_id = f"ev-{self._seq}"
            if tool == "SendMessage":
                result = self._send_message(seat, args, call_id)
            elif tool == self.cell.wait_tool:
                result = self._route_wait(seat, tool, args, call_id)
            else:
                result = self._route(seat, tool, args, call_id)
            self._log(
                "tool_call",
                seat,
                {"tool": tool, "args": args, "result_head": result[:200]},
            )
            return result

    def _route(self, seat: str, tool: str, args: dict[str, Any], call_id: str) -> str:
        """One `router.route` round-trip; an unowned call fails loud rather than inventing physics."""
        routed = self.router.route(
            seat, ToolCall(id=call_id, function=tool, arguments=args)
        )
        if routed is None:
            return f"error: '{tool}' is not available on this session."
        return routed

    def _route_wait(
        self, seat: str, tool: str, args: dict[str, Any], call_id: str
    ) -> str:
        """Apply the turn's wait budget around the world's own wait (see the module docstring).

        A request against an empty budget gets the env's denial (no world call); one past the remaining
        budget is clamped where the tool takes minutes (the world's own truncation mechanic). The spend
        is debited by the ACTUAL clock delta, robust to in-world truncation and argument-less waits.
        """
        budgets = [
            b for b in (self._turn_wait_left, self._round_wait_left) if b is not None
        ]
        left = min(budgets) if budgets else None
        if left is not None:
            if left <= 0:
                return self.cell.wait_limit_error
            args = self.cell.clamp_wait_args(args, left)
        before = self.clock()
        result = self._route(seat, tool, args, call_id)
        spent = self.clock() - before
        if self._turn_wait_left is not None:
            self._turn_wait_left = max(0, self._turn_wait_left - spent)
        if self._round_wait_left is not None:
            self._round_wait_left = max(0, self._round_wait_left - spent)
        return result

    def _send_message(self, seat: str, args: dict[str, Any], call_id: str) -> str:
        """The sim's mechanical mailbox capture: validate, enqueue, ledger; never claim a false delivery."""
        tc = ToolCall(id=call_id, function="SendMessage", arguments=args)
        to_id, msg, error, undeliverable_to = validate_send_message(
            seat, tc, self.recipients, self.ids, self.usernames, self.allowed_recipients
        )
        if error is not None:
            if undeliverable_to is not None and msg is not None:
                on_undeliverable = getattr(self.router, "on_dm_undeliverable", None)
                if on_undeliverable is not None:
                    on_undeliverable(seat, undeliverable_to, msg)
            return error
        assert to_id is not None and msg is not None
        self.nstate["mailbox"][to_id].append((self.usernames.get(seat, seat), msg))
        self.router.on_dm(seat, to_id, msg)
        return "Delivered."

    # ── end of day ───────────────────────────────────────────────────────────────────────────────────────
    def finalize(self) -> dict[str, Any]:
        """Settle the world (`finalize_world`, when the router has one) and take THE one summary.

        Idempotent from the caller's side: repeated calls return the same dict (the api_key world's fairness
        enrichment must run exactly once).
        """
        with self._lock:
            if self._summary is None:
                finalize_world = getattr(self.router, "finalize_world", None)
                if finalize_world is not None:
                    finalize_world()
                self._summary = self.router.summary()
                self._log("finalized", None, {"clock": self.clock()})
            return self._summary

    def drain_notices(self) -> list[str]:
        """Drain the router's world-notice narration into the run log (operator-facing telemetry)."""
        return list(self.router.notices())

    # ── ledger ───────────────────────────────────────────────────────────────────────────────────────────
    def _log(self, kind: str, seat: str | None, payload: dict[str, Any]) -> None:
        row = {
            "seq": self._seq,
            "wall_ts": round(time.time(), 3),
            "sim_clock": self.clock(),
            "kind": kind,
            "seat": seat,
            **payload,
        }
        with self._ledger_path.open("a") as f:
            f.write(json.dumps(row) + "\n")


@dataclass
class DuckMessage:
    """The duck-typed stand-in for an assistant message where a router reads only `.tool_calls`."""

    tool_calls: list[object] | None
