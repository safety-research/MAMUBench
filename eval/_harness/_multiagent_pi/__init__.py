"""Shared helper for multi-agent pi audits — one auditor live-driving N walled-off pi-framed targets.

Ported from the authors' research code: the N-target solver, the routing controller + N-way resume balance + peer mailbox, the exact pi system
prompt/tools, and opus role binding. On top of it sits a declarative scenario model (`ScenarioSpec` with an
`AgentSpec` per target and a `User` topology) plus a seed builder, supporting the two interaction modes the
skill exists for:

- `interactive` — the auditor also voices the user(s) (one operator per agent, several operators, or one
  operator driving several agents).
- `tool_only` — the auditor is ONLY the environment: one initial handoff per agent, then nothing but tool
  results.
- `scripted` — the operators' messages are scripted verbatim beats a deterministic world delivers
  mechanically (the evals' `environment/` worlds); the auditor never voices a user, and with a fully mechanical toolset
  `build_task(auditor="none")` replaces it with the no-LLM `scripted_driver` entirely.

Typical use (the audit skill and experiments this served live in the authors' research code, not released; in
this artifact `eval/_harness/sim.py` is the caller):

    from _multiagent_pi import AgentSpec, ScenarioSpec, User, build_task, build_roles
    spec = ScenarioSpec(name="...", interaction="tool_only", intro="...", world="...",
                        agents=(AgentSpec(...), AgentSpec(...)), users=(User(...),), observe="...")
    task = build_task([spec], max_turns=120, detector_factory=...)
"""

from __future__ import annotations

from .audit import DetectorFactory, RouterFactory, build_task, validate_auditorless
from .driver import scripted_driver
from .escalation import EscalationHandler, GenerateFn
from .pi_exact import pi_prompt_with_context, pi_system_prompt, pi_tools
from .roles import FAST_BETA, build_roles, role_model
from .routing import (
    OnResponse,
    RoutingController,
    ToolRouter,
    drainable_agents,
    find_agents_tool,
    resume_executor,
    send_message_tool,
    undrained_agents,
)
from .scenario import AgentSpec, Interaction, ScenarioSpec, User, build_seed
from .solver import NSetup, TargetToolsets, agent_ids, audit_name, n_model_audit_solver

__all__ = [
    # scenario model + seed
    "AgentSpec",
    "User",
    "ScenarioSpec",
    "Interaction",
    "build_seed",
    # task
    "build_task",
    "DetectorFactory",
    "RouterFactory",
    "validate_auditorless",
    # solver
    "n_model_audit_solver",
    "agent_ids",
    "audit_name",
    "NSetup",
    "TargetToolsets",
    # routing
    "RoutingController",
    "resume_executor",
    "scripted_driver",
    "EscalationHandler",
    "GenerateFn",
    "send_message_tool",
    "find_agents_tool",
    "drainable_agents",
    "undrained_agents",
    "OnResponse",
    "ToolRouter",
    # roles
    "role_model",
    "build_roles",
    "FAST_BETA",
    # pi prompt
    "pi_prompt_with_context",
    "pi_system_prompt",
    "pi_tools",
]
