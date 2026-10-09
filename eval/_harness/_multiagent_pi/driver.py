"""`scripted_driver` — a deterministic, no-LLM stand-in for the auditor seat.

When a scenario's every target-visible surface is mechanical — a deterministic world answers the world
tools, comms tools are router-owned, and user pressure arrives as scripted verbatim beats — the LLM auditor
has nothing left to decide: the resume loop's own wake gates (mail → wake-priority → balance) already pick
who runs next by mutating `nstate["cur"]`, and the router's `is_over` says when the day is done. This driver
simply calls the shared `resume_executor` until that signal (precedent: the debrief-probe scripted
coroutine), making such runs model-invariant on the pressure side and auditor-token-free.

The one auditor decision the wake gates do NOT make for it: an agent whose last turn was pure text cannot be
bare-resumed (the channel refuses until something is staged for it — mail, a beat, a notification). The LLM
auditor reads that advisory and drives another agent; the driver does the mechanical equivalent — on any
call that renders nothing it rotates `nstate["cur"]` to the next agent. Each attempt still advances the
world clock (`on_resume` runs before the refusal), so a fully text-idle fleet fast-forwards through quiet
stretches until the next scripted beat (ultimately the debrief) revives someone — the day always resolves.

Without an `escalate` hook it is NOT a general auditor replacement: any foreign (auditor-owned) tool call —
bash in a pi toolset, an unanswered comms call — is a hard error, because nothing is present to answer it.
`build_task` validates the toolset up front via the router's `owns_tool`; the runtime check here is the
backstop. With `escalate` (the mechanical-first mode), the hook is invoked after every step and
answers whatever residue the router left — foreign tool calls and unscripted operator addresses — via a
scoped live-auditor generation (`escalation.EscalationHandler.resolve`), so the auditor model runs ONLY on
escalations while the driver keeps it off the per-resume critical path.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from inspect_ai.agent import Agent, AgentState, agent
from inspect_ai.log import transcript
from inspect_ai.model import ModelOutput

from .routing import (
    _QUARANTINE_K,
    ToolRouter,
    drain_listing,
    drainable_agents,
    undrained_agents,
)

#: Consecutive resume calls with NO agent rendering before the driver declares the run wedged. Sized for the
#: worst legitimate case — a fully text-idle fleet riding clock advances from lights-out to the debrief beat
#: (fast-forward covers ≥ tens of sim-minutes per attempt, so real runs revive within a few dozen calls).
_STALL_K = 200


@agent
def scripted_driver(
    *,
    resume: Callable[[str | None], Awaitable[str]],
    nstate: dict[str, Any],
    router: ToolRouter,
    ids: tuple[str, ...],
    max_steps: int,
    escalate: Callable[[], Awaitable[int]] | None = None,
) -> Agent:
    """Drive the whole episode mechanically: resume until the router's `is_over` (or the step cap).

    Args:
        resume: The shared `resume_executor` closure (the same loop the LLM auditor's resume tool wraps).
        nstate: The per-sample state dict (read for renders/rotation and the foreign-call backstop).
        router: The deterministic world router; its `is_over` hook ends the day — after any agent still holding staged-but-undelivered content has been drained with final wrap-up turns at the frozen clock.
        ids: The agent ids in play (the rotation order for a refused text-idle agent).
        max_steps: Hard cap on resume calls (a generous backstop above the world's own horizon).
        escalate: Optional exception handler (`EscalationHandler.resolve`), awaited after every step; it
            answers residual foreign calls / unscripted addresses with a scoped auditor generation and
            returns how many it handled. `None` keeps the strict auditorless contract (foreign = error).
    """
    is_over_fn: Callable[[], bool] | None = getattr(router, "is_over", None)
    # PROGRESS GUARANTEE plumbing: the resume gates' early advisories (a wake-priority/mail switch, a
    # validate-first owe, a withhold) return WITHOUT running `on_resume`, so a cycle of advisory <->
    # failed-resume steps can leave the world clock frozen — 200 such steps once wedged a mesh smoke
    # run. The LLM auditor tolerates that cycle (it burns turns until its cap); the driver mirrors
    # the failed-resume path instead — every no-render step that left the clock untouched advances the
    # world one baseline tick, so scheduled beats still fire and the day always reaches `is_over` (or the
    # step cap). Duck-typed off the shared `WorldRouter` shape; a router without a clocked world keeps the
    # old hard-wedge backstop.
    world = getattr(router, "world", None)
    advance_fn: Callable[[int], None] | None = getattr(world, "advance", None)
    # The keep-the-day-moving stall nudge is the router's per-turn gap.
    raw_nudge = getattr(router, "baseline_advance_min", 2)
    nudge_min: int = 2 if raw_nudge is None else int(raw_nudge)
    if nudge_min <= 0:
        # An explicit-time-only clock contract (`baseline_advance_min == 0`, e.g. food_order's console
        # worlds or the api_key world's paper clock) must NEVER be nudged — a silent 2-min advance
        # would warp the very clock the contract freezes. Dropping the advance hook keeps the hard-wedge
        # backstop below, so a permanent gate-cycle fails loudly instead of time-warping the world.
        advance_fn = None

    def _clock() -> int | None:
        value = getattr(world, "clock", None)
        return int(value) if isinstance(value, int) else None

    def _rendered() -> int:
        return sum(nstate.get("count", {}).values())

    async def execute(state: AgentState) -> AgentState:
        transcript().info(
            "### Scripted driver\n\nNo LLM auditor on the resume path: the deterministic world answers "
            "every tool call it can, scripted beats deliver the user pressure, and this loop resumes "
            "agents until the world reports the day is over."
            + (
                " Residual calls escalate to a scoped auditor generation."
                if escalate is not None
                else ""
            )
        )
        steps = 0
        stall = 0
        escalations = 0
        nudges = 0
        ended = "step cap reached"
        while steps < max_steps:
            # Stop at the horizon only once the fleet's GRANTABLE drain is done: while an agent still holds
            # staged-but-undelivered content AND has wrap-up budget left, keep calling resume — the day-over
            # gate inside the executor steers those calls into bounded final wrap-up turns at the frozen
            # clock (the termination-artifact fix). `drainable_agents` is the budgeted view, so a
            # capped agent can never loop this; the truth predicate keeps any capped remainder visible to the
            # end guard's annotation.
            if is_over_fn is not None and is_over_fn():
                undrained = undrained_agents(nstate, ids, router)
                if not drainable_agents(nstate, undrained):
                    # No end_conversation guard runs in the auditorless arm, so the driver itself carries
                    # the annotated-end guarantee: a capped strand is named in the episode summary, never a
                    # silent clean ending.
                    ended = "world horizon reached"
                    if undrained:
                        ended += f" — undelivered content remained ({drain_listing(undrained)})"
                    # `undrained_agents` names a beat-holder only when it is the single
                    # wake-priority target and never a quarantined one, so a world whose router can enumerate
                    # its own stranded deliveries adds them here — the annotated-end guarantee for callers the
                    # drain could not reach. Empty on every clean day; only the clinic router defines the hook.
                    stranded_fn = getattr(router, "stranded_deliveries", None)
                    if stranded_fn is not None:
                        stranded: dict[str, str] = stranded_fn(nstate)
                        left = {
                            i: why for i, why in stranded.items() if i not in undrained
                        }
                        if left:
                            ended += (
                                f" — world deliveries stranded ({drain_listing(left)})"
                            )
                    break
            before_rendered = _rendered()
            before_cur = nstate.get("cur")
            before_clock = _clock()
            await resume(None)
            steps += 1
            if escalate is not None:
                escalations += await escalate()
            # Foreign-call backstop: with no escalation hook nothing exists to answer an auditor-owned
            # call, and even with one a lingering owe means it failed — fail loudly, never silently stall.
            owed = {
                a: tc_ids
                for a, tc_ids in nstate.get("owed_foreign", {}).items()
                if tc_ids
            }
            if owed:
                raise RuntimeError(
                    f"scripted driver cannot answer foreign tool calls {owed}; auditorless runs need a "
                    "fully mechanical toolset (or an escalate hook that resolves the residue)"
                )
            if _rendered() > before_rendered:
                stall = 0
                continue
            # Nothing rendered. Distinguish the two cases STRUCTURALLY (not by advisory prose): a wake-gate
            # switch already re-pointed nstate["cur"], so leave it; a refused bare resume (text-idle agent
            # with nothing staged) leaves cur unchanged — rotate to the next agent, the LLM auditor's "drive
            # someone else". Either way clock progress (below) carries the world toward its next beat.
            stall += 1
            if nstate.get("cur") == before_cur:
                cur = before_cur or ids[0]
                nstate["cur"] = (
                    ids[(ids.index(cur) + 1) % len(ids)] if cur in ids else ids[0]
                )
            # FLEET QUARANTINED (renders > 0): every agent is at the failure cap, so steering has no
            # legal target and nothing can render — the only remaining moves are advisory no-ops, which
            # would grind to _STALL_K while re-attempting huge-context generates. End as annotated DATA
            # (a retry would re-grind hours to the same terminal); the zero-render twin
            # (DeadEpisodeError) still errors for retry — that one is a backend outage, not an outcome.
            streaks = nstate.get("fail_streak") or {}
            if _rendered() > 0 and all(streaks.get(i, 0) >= _QUARANTINE_K for i in ids):
                ended = (
                    f"fleet quarantined — every agent at {_QUARANTINE_K}+ consecutive failed resumes "
                    f"(last target error: {nstate.get('last_failure', 'none recorded')})"
                )
                break
            if (
                stall
                >= 3  # a persisting stretch — a lone gate advisory is followed by a render
                and advance_fn is not None
                and before_clock is not None
                and _clock() == before_clock
            ):
                advance_fn(
                    nudge_min
                )  # an advisory-only step: pass baseline time anyway
                nudges += 1
            if stall == _STALL_K // 4:
                # Diagnostic breadcrumb well before any cap: the gate-cycle shape for a post-mortem.
                transcript().info(
                    f"scripted driver: {stall} consecutive no-render steps (cur={nstate.get('cur')!r}, "
                    f"clock={_clock()!r}, nudges={nudges}, steps={steps}) — continuing; the clock is "
                    "kept moving so the day resolves at its horizon or the step cap."
                )
            if stall >= _STALL_K and advance_fn is None:
                # Only a router with NO advanceable world can truly freeze; with the nudge above the day
                # always terminates via is_over/max_steps, mirroring the LLM auditor's turn-cap tolerance.
                raise RuntimeError(
                    f"scripted driver wedged: {stall} consecutive resume calls with no render "
                    f"(clock frozen at cur={nstate.get('cur')!r}; fail_streaks={nstate.get('fail_streak')}; "
                    f"last target error: {nstate.get('last_failure', 'none recorded')})"
                )
        # Stamp the driver's verdict DURABLY (finalize copies it into the world sidecar): a step-cap exit
        # on a world that has its own end signal means the day never concluded — the same truncation shape
        # as an unwind, so the completeness gate must be able to refuse it rather than bank a settled
        # "clean" night. A router with no `is_over` ends by design at the cap; that is not truncation.
        nstate["driver_ended"] = ended
        nstate["driver_step_capped"] = (
            ended == "step cap reached" and is_over_fn is not None
        )
        summary = f"scripted driver: {ended} after {steps} resume steps"
        if escalate is not None:
            summary += f" ({escalations} escalations)"
        if nudges:
            summary += f" [{nudges} idle clock nudges]"
        transcript().info(summary)
        state.output = ModelOutput.from_content("scripted-driver", summary)
        return state

    return execute
