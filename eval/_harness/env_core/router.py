"""`WorldRouter` — the shared shape of a deterministic-world `ToolRouter`.

Both shipped world routers (api-budget `LabctlRouter`, gpu `GpuClusterRouter`) independently implemented the
same scaffolding: prefix-dispatch of world tool calls with CLI-style error rendering, a mutating-call tracker
feeding an idle fast-forward, notice draining with a ground-truth digest, and duplicated argument parsers.
This base extracts that scaffolding; an env subclass supplies only its dispatch table, its wording, and its
schedule edges.

The class structurally satisfies `_multiagent_pi.ToolRouter` (route / on_resume / notices / summary) without
importing it — `env_core` stays dependency-light so its pieces unit-test without the harness import chain.

Contract notes (kept in lock-step with `_multiagent_pi.routing`): `route` is called at most once per
tool-call id (the helper memoizes results and never re-calls on rollback replay), so a world mutation inside
a handler runs exactly once; `on_resume` fires immediately before EVERY resume, including mid-burst, so its
clock advance is intentionally additive (deterministic for a fixed action script).
"""

from __future__ import annotations

from typing import Any, Protocol, cast

from inspect_ai.tool import ToolCall


class RoutedWorld(Protocol):
    """What the base needs from a world: a clock, an advancer, a notice queue, a ground-truth summary."""

    clock: int

    def advance(self, minutes: int) -> None: ...

    def drain_notices(self) -> list[str]: ...

    def summary(self) -> dict[str, Any]: ...


class ArgError(Exception):
    """Raised for a missing/malformed tool argument; rendered as CLI error text by `route` (never raises)."""


def req_str(args: dict[str, Any], key: str) -> str:
    if key not in args or args[key] is None:
        raise ArgError(f"missing required argument '{key}'")
    return str(args[key])


def opt_str(args: dict[str, Any], key: str, default: str) -> str:
    v = args.get(key)
    return default if v is None else str(v)


def req_int(args: dict[str, Any], key: str) -> int:
    if key not in args or args[key] is None:
        raise ArgError(f"missing required argument '{key}'")
    try:
        return int(args[key])
    except (TypeError, ValueError):
        raise ArgError(
            f"argument '{key}' must be an integer (got {args[key]!r})"
        ) from None


def opt_int(args: dict[str, Any], key: str, default: int) -> int:
    v = args.get(key)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ArgError(f"argument '{key}' must be an integer (got {v!r})") from None


class WorldRouter:
    #: Whether the zero-baseline RESOLUTION GUARANTEE (see `on_resume`) may advance a frozen clock.
    #: True for regimes whose day-resolution rides on between-turn time (baseline creep or the idle
    #: fast-forward). Explicit-time-only routers — where the clock moves ONLY by a declared action, so
    #: silent stasis is legal physics — override this to False alongside `_should_fast_forward`.
    resolution_guarantee: bool = True
    """Answer the agents' world tool calls mechanically from one shared deterministic world.

    Args:
        world: The deterministic simulator (built with `world_seed(spec.name, epoch)`).
        nstate: The per-sample state dict shared with `resume_executor` — read for undelivered mail.
        ids: The agent ids in play (mailbox scan + delivery ordering).
        prefix: The world tool-name prefix (e.g. `"labctl_"`); non-prefixed calls fall through to
            `route_unprefixed` (default: foreign — the auditor answers them).
        tool_names: The known world tool names; a prefixed-but-unknown call renders `unknown_command`.
        mutating: The tool names that MUTATE the world — a resume whose last generation ran one is "active"
            and blocks a fast-forward (fine-grained simulation right after a state change).
        baseline_advance_min: Minutes the clock advances before an ordinary (non-fast-forward) resume.
        ff_max_jump_min: A fast-forward never jumps further than this at once (each edge is a chance for an
            agent to react).
        ff_segment_min: Maximum minutes passed to one `world.advance` call while fast-forwarding. Longer
            quiet gaps are split into narrated segments so no single resume-side world update looks like an
            implausible multi-hour clock jump.
        ff_min_gap_min: Don't fast-forward when the next scheduled edge is this close — let the baseline
            cadence reach it naturally.
        ff_stops_short_of_edge: Make that promise hold for the JUMP too — a fast-forward lands
            `ff_min_gap_min` short of the next edge instead of on it, so the final approach to every edge is
            always simulated at the baseline cadence. Opt-in (see the attribute docstring).
    """

    def __init__(
        self,
        world: RoutedWorld,
        nstate: dict[str, Any],
        ids: tuple[str, ...],
        *,
        prefix: str,
        tool_names: frozenset[str],
        mutating: frozenset[str],
        baseline_advance_min: int = 2,
        ff_max_jump_min: int = 90,
        ff_segment_min: int = 30,
        ff_min_gap_min: int = 15,
        hold_until_all_started: bool = False,
        ff_stops_short_of_edge: bool = False,
    ) -> None:
        if ff_segment_min <= 0:
            raise ValueError("ff_segment_min must be positive")
        self.world = world
        self.nstate = nstate
        self.ids = ids
        self.prefix = prefix
        self.tool_names = tool_names
        self.mutating = mutating
        self.baseline_advance_min = baseline_advance_min
        self.ff_max_jump_min = ff_max_jump_min
        self.ff_segment_min = ff_segment_min
        self.ff_min_gap_min = ff_min_gap_min
        #: Hold the clock short of the next scheduled edge until EVERY seat has been brought up at least once,
        #: so a scheduled event (e.g. the first tick) never fires before a not-yet-started seat can act on it
        #: (the pass-0 race). Opt-in — off by default so the mature single-edge worlds stay byte-identical.
        self.hold_until_all_started = hold_until_all_started
        #: Never let a fast-forward JUMP land on (or past) the next scheduled edge — clamp it to
        #: `next_edge() - ff_min_gap_min`, so the last `ff_min_gap_min` minutes before every edge are always
        #: simulated at the baseline cadence and each seat gets rendered turns while the edge is still
        #: pending (and, for a world whose edges are commitment deadlines, still committable).
        #:
        #: `ff_min_gap_min` already promised this ("let the baseline cadence reach it naturally") but only
        #: honored it for the DECISION: a fast-forward starting further out than the gap jumped straight onto
        #: the edge, and `advance` fires an edge that the clock lands exactly on — so the resumed seat's turn
        #: came after the deadline it was supposed to act before. Opt-in — off by default so the mature
        #: single-edge worlds (api-budget, token-cluster) stay byte-identical.
        self.ff_stops_short_of_edge = ff_stops_short_of_edge
        #: Agents that have been resumed at least once (the "started" set for the fast-forward rule).
        self._seen: set[str] = set()
        #: Whether an agent's IN-PROGRESS generation has issued a mutating world call yet.
        self._this_gen: dict[str, bool] = {}
        #: Whether an agent's IN-PROGRESS generation has issued a known read-only world call.
        self._this_gen_read: dict[str, bool] = {}
        #: Whether an agent's most-recently-FINISHED generation was mutating (snapshotted at its next resume).
        self._last_mutating: dict[str, bool] = {}
        #: Whether an agent's most-recently-FINISHED generation contained reads but no mutation.
        self._last_read_only: dict[str, bool] = {}
        #: Router-local quiet-time narration awaiting a drain.
        self._pending: list[str] = []
        #: Consecutive resumes with NO tool activity, NO reported generation, and NO clock movement — the
        #: dead-rotation detector behind the zero-baseline resolution guarantee (see `on_resume`).
        self._dead_rotation = 0

    # ── ToolRouter surface ───────────────────────────────────────────────────────────────────────────────
    def route(self, agent_id: str, call: ToolCall) -> str | None:
        """Answer a world call, or return `None` for a foreign (auditor-owned) call."""
        fn = getattr(call, "function", "") or ""
        if not fn.startswith(self.prefix):
            return self.route_unprefixed(agent_id, call)
        raw_args: object = getattr(call, "arguments", None)
        args = cast(dict[str, Any], raw_args) if isinstance(raw_args, dict) else {}
        if fn in self.tool_names:
            self._dead_rotation = 0  # any tool activity ends a dead rotation
            if fn in self.mutating:
                self._this_gen[agent_id] = True
            else:
                self._this_gen_read[agent_id] = True
        if fn not in self.tool_names:
            return self.unknown_command(fn)
        try:
            return self.dispatch(agent_id, fn, args)
        except ArgError as e:
            return self.arg_error(str(e))

    def on_resume(self, agent_id: str) -> None:
        """Advance the clock a baseline step, or fast-forward to the next edge when the fleet is idle.

        RESOLUTION GUARANTEE under zero-baseline clocks: the scripted driver's "the day always resolves" contract historically rode the baseline advance — every resume moved the clock, so a fleet spinning on channel refusals still crept to its horizon. At `baseline_advance_min == 0` any state that pins the fast-forward (an outstanding beat or mail whose recipient never renders, a stale edge clamping `_ff_target` behind the clock) froze the night outright and the driver's 200-step guard aborted the episode (a stall diagnosed at clock=909/930 with zero model calls in the dead stretch). The dead-rotation detector restores the contract exactly there: after more than two full fleet rotations of consecutive resumes with no tool call, no reported generation, and no clock movement, each further resume advances one minute regardless of vetoes. Healthy fleets never reach the threshold (an idle rotation either fast-forwards or renders within one lap), so frozen-regime and completed-episode physics are byte-identical.
        """
        clock_before = self.world.clock
        # Snapshot the generation that just finished for this agent (its route() calls have landed since its
        # last on_resume), then reset the accumulator for the generation about to run.
        if agent_id in self._seen:
            was_mutating = self._this_gen.get(agent_id, False)
            self._last_mutating[agent_id] = was_mutating
            self._last_read_only[agent_id] = (
                self._this_gen_read.get(agent_id, False) and not was_mutating
            )
        self._this_gen[agent_id] = False
        self._this_gen_read[agent_id] = False
        # Pass-0 guard (opt-in): hold the clock short of the next scheduled edge until every seat has been
        # brought up AND had its first generation, so no tick executes before any seat can act on it.
        # `on_resume` fires BEFORE this seat's generation, so "every seat has acted once" is exactly "every
        # seat was already in `_seen` at the START of this resume" — evaluate before adding the current seat,
        # and short-circuit on the flag so worlds that don't opt in do no extra work.
        holding = self.hold_until_all_started and not self._seen >= set(self.ids)
        fast_forward = not holding and bool(self._seen) and self._should_fast_forward()
        self._seen.add(agent_id)
        if holding:
            self.world.advance(self._held_step())
            return
        if fast_forward:
            # A clamped target can already be behind the clock (a subclass that fast-forwards without the
            # edge-gap check); fall back to the ordinary between-turn advance — under the active clock
            # economics, not a raw baseline step — so a quiet fleet can never stall the clock.
            target = self._ff_target()
            if target <= self.world.clock:
                # Stale-edge clamp: fall through (no early return) so the dead-rotation
                # detector below still sees this resume — at baseline 0 this exact path
                # is the frozen-clock state the resolution guarantee exists for.
                self._advance_baseline(agent_id)
                target = self.world.clock  # skip the jump loop
            while self.world.clock < target:
                before = self.world.clock
                self.world.advance(min(self.ff_segment_min, target - before))
                if self.world.clock <= before:
                    break
                self._pending.append(
                    f"quiet work continued; current time is {self.clock_marker()}"
                )
        else:
            self._advance_baseline(agent_id)
        if self.world.clock != clock_before:
            self._dead_rotation = 0
        elif self.resolution_guarantee:
            self._dead_rotation += 1
            threshold = 2 * max(1, len(self.ids)) + 2
            if self._dead_rotation > threshold:
                # Escalating creep: one more full rotation at 1 min gives any near-term event a chance
                # to revive a seat; past that, jump in fast-forward segments — the scripted driver's
                # no-render guard fires at a fixed step count whether or not the clock moves, so a dead
                # rotation must reach the horizon within tens of resumes, not hundreds (a mid-night
                # 1-min-per-resume creep lost that race in observed stalls).
                deep = self._dead_rotation > threshold + max(1, len(self.ids))
                self.world.advance(self.ff_segment_min if deep else 1)

    def note_generation(self, agent_id: str, est_tokens: int) -> None:
        """Report the size of `agent_id`'s just-rendered generation.

        Any reported generation ends a dead rotation (the agent rendered SOMETHING). Callers may probe with
        `getattr` (routers predating this hook exist).
        """
        if est_tokens > 0:
            self._dead_rotation = 0

    def _advance_baseline(self, agent_id: str) -> None:
        """The ordinary between-turn advance: every resume costs `baseline_advance_min`."""
        self.world.advance(self.baseline_advance_min)

    def _held_step(self) -> int:
        """The baseline step, capped so the clock stays strictly short of the next scheduled edge.

        Used only during bring-up (`hold_until_all_started`): planning still burns a little clock, but the
        edge (e.g. the first tick launch) is not crossed until every seat has resumed at least once.
        """
        nxt = self.next_edge()
        if nxt is None:
            return self.baseline_advance_min
        return max(0, min(self.baseline_advance_min, nxt - 1 - self.world.clock))

    def notices(self) -> list[str]:
        """Drain world + router notices; append the ground-truth digest when non-empty."""
        lines = self.world.drain_notices() + self._pending
        self._pending = []
        if lines:
            digest = self.digest()
            if digest is not None:
                lines.append(digest)
        return lines

    def summary(self) -> dict[str, Any]:
        """The world's ground-truth summary (stashed under `sample.metadata['world']` at finalize)."""
        return self.world.summary()

    def owns_tool(self, name: str) -> bool:
        """Whether this router answers `name` mechanically (the auditorless toolset validation).

        Subclasses that own extra surfaces in `route_unprefixed` (e.g. comms tools) must extend this to
        match, or `build_task(auditor="none")` will refuse the toolset.
        """
        return name in self.tool_names or name.startswith(self.prefix)

    # ── subclass hooks ───────────────────────────────────────────────────────────────────────────────────
    def dispatch(self, agent_id: str, fn: str, args: dict[str, Any]) -> str:
        """Answer the known world tool `fn`; raise `ArgError` for malformed arguments."""
        raise NotImplementedError

    def route_unprefixed(self, agent_id: str, call: ToolCall) -> str | None:  # noqa: ARG002
        """Optionally own a non-prefixed call (e.g. comms tools in scripted mode); default: foreign."""
        return None

    def unknown_command(self, fn: str) -> str:
        """The error text for a prefixed-but-unknown tool name."""
        return f"error: unknown command '{fn}'."

    def arg_error(self, msg: str) -> str:
        """The error text wrapping an `ArgError` (env CLIs word this their own way)."""
        return f"error: {msg}"

    def clock_marker(self) -> str:
        """The human clock rendering used in the fast-forward notice (e.g. `HH:MM`)."""
        return f"t={self.world.clock}"

    def digest(self) -> str | None:
        """The ground-truth digest appended after any notices (None to omit)."""
        return None

    def next_edge(self) -> int | None:
        """The next scheduled world minute an agent should get a chance to react to (None if none)."""
        return None

    # ── fast-forward decision ────────────────────────────────────────────────────────────────────────────
    def _should_fast_forward(self) -> bool:
        """Fast-forward only when every started agent last idled, no mail is pending, no edge is imminent.

        The read-cadence and edge-imminent vetoes are CREEP-GATED (`baseline_advance_min > 0`): both exist so ordinary between-turn creep, not a jump, covers a read's cadence and the final approach to a scheduled edge. Under a zero-baseline clock (`free_turns`/`no_time_tax`) there is no creep — with the vetoes active an idle fleet freezes exactly `ff_min_gap_min` short of every edge and the scripted driver trips its no-render wedge guard (seen in a mechanical free-clock smoke run: `cur` rotating with the clock frozen). Frozen regimes (baseline 2) keep both vetoes byte-identically.
        """
        # An agent's most recent finished generation lives in `_this_gen` until ITS next resume snapshots it
        # into `_last_mutating` (the resuming agent was snapshotted just before this check) — so consult both,
        # or another agent's fresh mutation would be invisible and a fast-forward could jump right past the
        # fine-grained window after a state change.
        if any(
            self._this_gen.get(a, False) or self._last_mutating.get(a, False)
            for a in self._seen
        ):
            return False
        # A dashboard/status read should never be the action that appears to make hours pass. Treat a
        # read-only generation as active for one baseline cadence; a later genuinely idle generation can
        # still unlock the normal edge-aware fast-forward. (Creep-gated: at baseline 0 a polling loop
        # would hold this veto forever — the clock's only mover is the fast-forward it vetoes.)
        if self.baseline_advance_min > 0 and any(
            (self._this_gen_read.get(a, False) and not self._this_gen.get(a, False))
            or self._last_read_only.get(a, False)
            for a in self._seen
        ):
            return False
        mailbox: dict[str, list[Any]] = self.nstate.get("mailbox", {})
        if any(mailbox.get(i) for i in self.ids):
            return False
        nxt = self.next_edge()
        if (
            self.baseline_advance_min > 0
            and nxt is not None
            and nxt - self.world.clock <= self.ff_min_gap_min
        ):
            return False
        return True

    def _ff_target(self) -> int:
        """Where a fast-forward lands: the next scheduled edge, capped at clock + `ff_max_jump_min`.

        Under `ff_stops_short_of_edge` the edge itself is never the target — the jump stops `ff_min_gap_min`
        minutes short of it. That target is always strictly ahead of the clock, because a fast-forward only
        fires when the edge is more than `ff_min_gap_min` away (`_should_fast_forward`), so clamping cannot
        stall the clock. Both halves of that contract assume baseline creep crosses the final gap, so at
        `baseline_advance_min == 0` the jump lands ON the edge instead (the edge fires; nothing else could
        carry the clock there).
        """
        nxt = self.next_edge()
        cap = self.world.clock + self.ff_max_jump_min
        if nxt is None:
            return cap
        if self.ff_stops_short_of_edge and self.baseline_advance_min > 0:
            nxt -= self.ff_min_gap_min
        return min(nxt, cap)
