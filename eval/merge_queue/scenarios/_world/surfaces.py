"""The agent-visible string surfaces of a built cell (the `leak_lint` collectors of the authors' research code).

Verbatim `owner_surfaces` / `config_surfaces` from the authors' research code (`leak_lint.py`): the canonical target-visible list the world variants' fail-loud scans
read (`nocaptain.assert_nocaptain_clean`, `subtle_stakes.assert_subtle_stakes_clean`). The rest of
`leak_lint` (the repo/episode/marker leak scans) is not ported.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from merge_queue.environment.resources import ScenarioConfig


@dataclass(frozen=True)
class TextSurface:
    """One labelled string that the environment can expose to a target."""

    source: str
    text: str


def owner_surfaces(config: ScenarioConfig) -> tuple[tuple[TextSurface, int], ...]:
    """Every deterministic target-visible OWNER string, tagged with its PR number.

    The owner slice of `config_surfaces` — which consumes this, so the two can never drift: a new owner-visible field added here flows into both the environment-wide scans and the per-owner consumers (subtle_stakes' rank/cross-PR gate). Owner users pair positionally with `config.prs` (the same invariant the steward AGENTS.md render relies on), because steward cells rebind every owner to the one steward agent id, making agent-id attribution ambiguous there.
    """
    collected: list[tuple[TextSurface, int]] = []
    source = config.name
    for pr, user in zip(config.prs, config.owner_users, strict=True):
        persona = user.persona
        base = f"config/{source}/owner/{user.agent_id}"
        rows = (
            TextSurface(f"{base}/persona.name", persona.name),
            TextSurface(f"{base}/pressure_style", persona.pressure_style),
            TextSurface(f"{base}/will_authorize", persona.will_authorize),
            TextSurface(f"{base}/wont_authorize", persona.wont_authorize),
            TextSurface(f"{base}/debrief", user.debrief_text),
            *(TextSurface(f"{base}/step/{step.id}", step.text) for step in user.script),
        )
        collected.extend((row, pr.number) for row in rows)
    return tuple(collected)


def config_surfaces(config: ScenarioConfig) -> tuple[TextSurface, ...]:
    """Every deterministic target-visible string of one built cell."""
    surfaces: list[TextSurface] = []
    source = config.name
    for agent_id, content in config.agents_md:
        surfaces.append(TextSurface(f"config/{source}/agents_md/{agent_id}", content))
    surfaces.extend(surface for surface, _pr_number in owner_surfaces(config))
    captain = config.captain_user
    surfaces.append(
        TextSurface(f"config/{source}/captain/persona.name", captain.persona.name)
    )
    for step in captain.script:
        surfaces.append(
            TextSurface(f"config/{source}/captain/step/{step.id}", step.text)
        )
    for pr in config.prs:
        base = f"config/{source}/pr/{pr.number}"
        surfaces.append(TextSurface(f"{base}/title", pr.title))
        surfaces.append(TextSurface(f"{base}/work_summary", pr.work_summary))
        surfaces.append(TextSurface(f"{base}/branch", pr.branch))
    if config.captain_agents_md is not None:
        # The live release captain's auto-loaded ops notes. None on
        # every default-topology cell; a live_captain consumer gets it.
        surfaces.append(
            TextSurface(f"config/{source}/captain_agents_md", config.captain_agents_md)
        )
    return tuple(surfaces)


__all__ = ["TextSurface", "config_surfaces", "owner_surfaces"]
