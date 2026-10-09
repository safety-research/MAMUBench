"""Task builder for multi-agent pi audits: turn `ScenarioSpec`s into an Inspect `Task`.

`build_task(specs, ...)` makes one N-target sample per spec, wiring the canonical solver, the routing
controller, and the scripted driver over `resume_executor` (`auditor="none"`, or `"escalation"` with a live
auditor generation for what the world cannot answer).

A per-sample `detector_factory(spec, nstate) -> OnResponse` lets the caller flag antisocial tool calls for
mechanical scoring; whatever it records under `nstate["flags"]` is stashed into the sample metadata by
`finalize`.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import Any, Literal

from _metadata_sidecar import write_metadata_sidecar
from inspect_ai import Task
from inspect_ai.agent import Agent
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import Score, Target, mean, scorer
from inspect_ai.solver import TaskState

from .driver import scripted_driver
from .escalation import EscalationHandler
from .petri import Controller, init_controller, target_agent
from .routing import (
    OnResponse,
    RoutingController,
    ToolRouter,
    resume_executor,
)
from .scenario import ScenarioSpec, build_seed
from .solver import UNWOUND_STORE_KEY, n_model_audit_solver

#: Builds the per-sample mechanical-scoring hook, closing over the sample's mutable `nstate`.
DetectorFactory = Callable[[ScenarioSpec, dict[str, Any]], OnResponse]

#: Builds the per-sample deterministic world, closing over the spec, the mutable `nstate`, and the SEED
#: epoch — `state.epoch + spec.epoch_offset`, so per-epoch scenarios get distinct seeds and a top-up task
#: rebuilds exactly the source run's epochs. Returning `None` opts a sample out of routing (behaviour is
#: then byte-identical to a plain multi-agent pi audit). Stashed under `nstate["router"]`.
RouterFactory = Callable[[ScenarioSpec, dict[str, Any], int], "ToolRouter | None"]


def _max_ahead(max_turns: int, n: int) -> int:
    """Consecutive resumes one agent may get ahead of the most-behind before a forced rotation.

    Scaled to each agent's share of the turn budget so a thread can develop a discovery+decision arc
    (floored at 8, capped at 20 so a small fleet still rotates). `MAX_AHEAD` env overrides.
    """
    env = os.environ.get("MAX_AHEAD")
    if env:
        return max(1, int(env))
    return min(20, max(8, (max_turns // max(1, n)) // 4))


def validate_auditorless(spec: ScenarioSpec, router: ToolRouter | None) -> None:
    """Raise unless `spec` can run with NO auditor over `router` (nothing exists to answer a foreign call).

    Requires a voiceless interaction (`tool_only`/`scripted`) and a router whose `owns_tool` covers every
    target tool — i.e. a fully mechanical toolset (world tools + router-owned comms only, no bash).
    """
    if spec.interaction not in ("tool_only", "scripted"):
        raise ValueError(
            f"auditor='none' needs a tool_only or scripted interaction, got {spec.interaction!r} "
            "(interactive voicing requires an LLM auditor)"
        )
    owns = getattr(router, "owns_tool", None)
    if router is None or owns is None:
        raise ValueError(
            "auditor='none' needs a router_factory whose router exposes owns_tool(name)"
        )
    foreign = [t.name for t in spec.target_tools() if not owns(t.name)]
    if foreign:
        raise ValueError(
            f"auditor='none': the router does not answer {foreign} and no auditor exists to — "
            "restrict spec.base_tools to the world's mechanical surface"
        )


class TruncatedNightError(Exception):
    """The sample was cut short by an external limit before the world ran its course.

    inspect ends limit-hit samples GRACEFULLY (`error=None`) and still scores them, and the solver's finalize-on-cancellation path settles the world at horizon — so without this guard a night truncated by `PETRI_SAMPLE_TIME_LIMIT` is banked as a clean, scored outcome (silent zero nights during a provider outage). Raising in the scorer turns the sample into a retryable failure that `eval_set` re-runs on resume. Set `PETRI_ALLOW_TRUNCATED=1` to accept truncated nights instead (forensics / deliberate partial reads).
    """


@scorer(metrics=[mean()])
def _ran_scorer():  # noqa: ANN202
    """Trivial-but-guarded scorer — audits are judged post-hoc per agent timeline (see the experiment's report); limit-truncated nights raise `TruncatedNightError` so they retry instead of entering the corpus as clean outcomes."""

    async def score(state: TaskState, target: Target) -> Score:  # noqa: ARG001
        allow_truncated = os.environ.get("PETRI_ALLOW_TRUNCATED", "") == "1"
        if state.store.get(UNWOUND_STORE_KEY, False) and not allow_truncated:
            raise TruncatedNightError(
                "sample unwound before the world finished (time-limit cancel or error); "
                "failing the sample so eval_set retries it instead of banking a truncated "
                "night as a clean outcome (set PETRI_ALLOW_TRUNCATED=1 to accept)"
            )
        world = state.metadata.get("world")
        if (
            isinstance(world, dict)
            and bool(world.get("driver_step_capped", False))
            and not allow_truncated
        ):
            raise TruncatedNightError(
                "the scripted driver hit its step cap before the world's own end signal fired — "
                "the night never concluded; failing the sample so eval_set retries it instead of "
                "banking a truncated night as a clean outcome (set PETRI_ALLOW_TRUNCATED=1 to accept)"
            )
        return Score(value=1, answer="multi-agent pi audit ran")

    return score


def build_task(
    specs: Sequence[ScenarioSpec],
    *,
    max_turns: int,
    detector_factory: DetectorFactory | None = None,
    router_factory: RouterFactory | None = None,
    burst: int = 6,
    world_tool_label: str = "world",
    name: str = "multiagent_pi",
    auditor: Literal["none", "escalation"] = "none",
    epochs: int | None = None,
    task_name: str | None = None,
) -> Task:
    """One Task whose dataset is `specs` — each spec runs as a separate N-target sample.

    Args:
        specs: The scenarios to run (each becomes one sample; `spec.name` is the sample id).
        max_turns: The auditor's turn budget per sample (for `auditor="none"`/`"escalation"`: the driver's
            resume-step cap).
        detector_factory: Optional `(spec, nstate) -> OnResponse` building the per-sample mechanical-scoring
            hook; whatever it records under `nstate["flags"]` is copied to the sample metadata.
        router_factory: Optional `(spec, nstate, epoch) -> ToolRouter | None` building the per-sample
            deterministic world. When it returns a router, the resume loop answers that world's tool calls
            mechanically (burst loop), and the world's `summary()` is stashed under the sample metadata
            `"world"` key. Default `None` keeps the
            audit byte-identical to a plain multi-agent pi audit.
        burst: Max consecutive world-answered resumes of one agent per resume call (only used with a router).
        world_tool_label: Names the mechanically-answered tool surface (e.g. `"cluster"`, `"labctl"`). Only an
            LLM auditor's result tool read it; the scripted driver and the escalation handler do not.
        name: Dataset name.
        auditor: `"none"` (default) puts the deterministic
            `scripted_driver` in the auditor seat — zero auditor model calls; requires a `tool_only` or
            `scripted` interaction, a router, and a fully mechanical toolset (every target tool answered by
            the router's `owns_tool`), since nothing exists to answer a foreign call. `"escalation"`
            (mechanical-first mode) also runs the `scripted_driver` — zero auditor generations
            on the resume path — but keeps the LIVE `auditor` model role wired as an EXCEPTION handler
            (`EscalationHandler`): a residual foreign call or an unscripted operator address is answered by
            one scoped auditor generation. Requires a router; the toolset may include auditor-answered
            surfaces (e.g. pi bash).
        epochs: Optional per-`Task` epoch count (`Task(epochs=...)`). When tasks with DIFFERENT epoch
            counts share one `eval_set` root (a top-up run), per-task epochs is the only correct carrier —
            an eval-level `epochs` overrides every task identically (inspect merges `task.epochs` into the
            eval config only when the eval-level value is `None`). Default `None` defers to the eval level,
            as before.
        task_name: Optional `Task` name. A dynamically-built `Task` is otherwise named `"task"`, and
            `eval_set` requires distinct task identities within one log dir — multi-task roots must name
            each task uniquely and stably. Default `None` keeps the stock name, preserving the resume
            identity of every existing root.
    """
    by_name = {s.name: s for s in specs}
    if len(by_name) != len(specs):
        raise ValueError("ScenarioSpec names must be unique (they are the sample ids)")

    def setup(state: TaskState):  # noqa: ANN202
        spec = by_name[str(state.metadata["scenario"])]
        # The spec's OWN agent ids (positionally identical to agent_ids(n) for A/B/C/... specs,
        # and correct for bespoke ids like the single-agent steward "S").
        ids = tuple(a.id for a in spec.agents)
        usernames = {a.id: a.username for a in spec.agents}
        # Resolve a SendMessage `to` against BOTH usernames and display names (lowercased).
        recipients = {
            key: a.id
            for a in spec.agents
            for key in (a.username.lower(), a.display_name.lower())
        }
        # `system_message` resolves each agent's auto-bringup prompt (custom `system_prompt` or pi's default).
        bringup = {a.id: (a.system_message(spec.date), a.handoff) for a in spec.agents}
        nstate: dict[str, Any] = {"cur": None}
        on_response = detector_factory(spec, nstate) if detector_factory else None
        # Build the deterministic world (if any). Keyed on `state.epoch` so per-epoch runs get distinct world seeds;
        # `spec.epoch_offset` shifts that key so a top-up task regenerates exactly the tail epochs a source
        # run lacks (sample epoch e -> seed epoch e + offset).
        router = (
            router_factory(spec, nstate, state.epoch + spec.epoch_offset)
            if router_factory
            else None
        )
        nstate["router"] = router

        if auditor == "none":
            validate_auditorless(spec, router)
        handler: EscalationHandler | None = None
        if auditor == "escalation":
            # Unlike auditor="none", escalation does NOT gate on spec.interaction: scheduled pressure
            # arrives as scripted verbatim beats (see driver.py's contract) and the escalate hook answers
            # the interactive residue — foreign tool calls AND unscripted operator addresses — with a
            # scoped live-auditor generation, so an `interactive` spec loses no planned intervention.
            # Batteries of thousands of episodes (pi-framed `interactive` specs, beats verified firing)
            # ran exactly this pairing, so the only gate is the real requirement — the mechanical router
            # below.
            if router is None:
                raise ValueError(
                    "auditor='escalation' needs a router_factory (the mechanical layer that answers "
                    "everything answerable before the auditor is consulted)"
                )
            handler = EscalationHandler(spec, nstate, bringup=bringup)
            inner_response = on_response

            def composed(agent_id: str, message: object) -> None:
                # The caller's detector (which may feed the router's reply staging) runs FIRST, so the
                # handler sees the post-note_turn voicing gate when flagging an unscripted address.
                if inner_response is not None:
                    inner_response(agent_id, message)
                assert handler is not None
                handler.on_response(agent_id, message)

            on_response = composed

        def auditor_factory(controllers: dict[str, Controller]) -> Agent:
            # Route every controller()-based staging/resume call to the SELECTED agent via the routing proxy
            # (set once as the global). pi's tools are pre-registered on every target.
            init_controller(RoutingController(controllers, nstate))
            if auditor in ("none", "escalation"):
                assert router is not None  # validated above
                return scripted_driver(
                    resume=resume_executor(
                        nstate,
                        ids,
                        bringup=bringup,
                        usernames=usernames,
                        recipients=recipients,
                        allowed_recipients=(
                            dict(spec.allowed_recipients)
                            if spec.allowed_recipients is not None
                            else None
                        ),
                        max_ahead=_max_ahead(max_turns, len(ids)),
                        on_response=on_response,
                        router=router,
                        burst=burst,
                    ),
                    nstate=nstate,
                    router=router,
                    ids=ids,
                    max_steps=max_turns,
                    escalate=handler.resolve if handler is not None else None,
                )
            raise ValueError(f"unsupported auditor {auditor!r}; use none or escalation")

        def finalize(s: TaskState) -> None:
            s.metadata["n_agents"] = len(ids)
            s.metadata["flags"] = nstate.get("flags", {})
            if router is not None:
                # Optional hook: let a router run a SETTLED world out to its horizon before the summary is
                # captured, so an audit the auditor ended early (fleet quiescent, sim-clock short of the
                # deadline) is recorded as the completed day it is rather than frozen at the early clock.
                # No-op for routers that don't define it (behaviour unchanged for every other env).
                finalize_world = getattr(router, "finalize_world", None)
                if callable(finalize_world):
                    finalize_world()
                world = router.summary()
                # Stamp the unwind flag into the DURABLE evidence: on the cancellation path finalize_world
                # settles the world to horizon, which makes a limit-truncated night indistinguishable from a
                # completed one by clock alone (the completeness gate's blind spot). Old sidecars lack the
                # key (read as
                # False), so pre-existing corpora are unaffected.
                world["unwound"] = bool(s.store.get(UNWOUND_STORE_KEY, False))
                # The scripted driver's exit verdict (auditorless/escalation arms): a step-cap exit on a
                # world with its own end signal is a truncated night — `_ran_scorer` refuses it like an
                # unwind, and the artifact-side completeness gates can too. Absent for LLM-auditor runs.
                if "driver_ended" in nstate:
                    world["driver_ended"] = str(nstate["driver_ended"])
                world["driver_step_capped"] = bool(
                    nstate.get("driver_step_capped", False)
                )
                s.metadata["world"] = world
                # The sidecar filename carries the SEED epoch (`<cell>__e<epoch + offset>.json`), matching
                # the world the router actually built, so a top-up run's worlds are mergeable with the
                # source run's roots with no filename collisions.
                write_metadata_sidecar(
                    s.sample_id, s.epoch + spec.epoch_offset, "world", world
                )

        # Per-agent `model_role` supports a mixed-model roster (default "target" keeps every agent on one).
        targets = {a.id: target_agent(model_role=a.model_role) for a in spec.agents}
        return auditor_factory, targets, spec.solver_tools(), finalize

    samples = [
        Sample(
            input=build_seed(s),
            id=s.name,
            metadata={
                "scenario": s.name,
                "mode": s.interaction,
                "comms": s.comms,
                "n_agents": len(s.agents),
                # Stamped only when shifted, keeping every existing run's samples byte-identical. Readers
                # (e.g. `_metadata_sidecar.read_metadata_sidecar`) use it to map the logged sample epoch to
                # the true seed epoch.
                **({"epoch_offset": s.epoch_offset} if s.epoch_offset else {}),
            },
        )
        for s in specs
    ]
    return Task(
        dataset=MemoryDataset(samples, name=name),
        solver=[n_model_audit_solver(setup=setup)],
        scorer=_ran_scorer(),
        metadata={"multiagent_pi": True},
        epochs=epochs,
        name=task_name,
    )


__all__ = ["build_task", "DetectorFactory", "RouterFactory"]
