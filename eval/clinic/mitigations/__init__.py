"""The clinic mitigation arms: the registry, the paper's runs of each arm, and the hook that builds an arm's recipe.

The paper's three working clinic mitigations (main text, "Mitigations"; appendix "Clinic mitigations") are arms
of the peer-to-peer team:

    s1 = registry r2_stack_s3  = A + B + D   stricter booking behavior, look once then act, book before ending the call
    s2 = registry r2_stack_s5  = A + B + E   stricter booking behavior, look once then act, cancel and book as one action
    s3 = registry r2_stack_s11 = A + C + D   stricter booking behavior, act on what you hear, book before ending the call

Every arm is prompt text only (`rules.py`), added to every team desk: the tools, the world, the seeds and the peer
channel are unchanged, and the cell id stays `clinic_<board>_meshfull_comms_tight_scripted`. They ran under the
teams' standard scheduler (`cells.MITIGATION_INSTRUMENT`) on the simulated harness, which is what `build_sim_recipe`
plays. `cells.build_sim_recipe` dispatches here for every arm but `none`.

    python run.py clinic --mitigation all
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from _matrix import CLAUDE, Cells
from _mitigations import NONE, Mitigation, control
from _mitigations import listing as _listing
from _mitigations import validate as _validate

from clinic.mitigations.rules import (
    DATE_MARKER,
    RULES,
    SOP_MARKER,
    STACKS,
    Rule,
    Stack,
    patched_agents,
    resolve,
)
from clinic.scenarios import FORMATIONS

if TYPE_CHECKING:
    from _harness.bridge import EnvCell
    from _harness.sim import SimRecipe

ENV = "clinic"

_TEAM = ("team",)
_HARNESSES = ("sim",)

#: Every arm, `none` first. See `_mitigations.Mitigation` for the fields.
MITIGATIONS: dict[str, Mitigation] = {
    NONE: control(FORMATIONS, harnesses=("pi", "sim")),
    "s1": Mitigation(
        name="s1",
        paper_label="s1: stricter booking behavior + look once, then act + book before ending the call",
        description=(
            "Prompt text only, every team desk: rule A after the pinned standing procedure; rules B and D "
            "as paragraphs above it. Peer channel, tools and world unchanged; the standard scheduler."
        ),
        formations=_TEAM,
        research_id="r2_stack_s3",
        harnesses=_HARNESSES,
        notes=(
            "paper (all 24 scenarios, episodes 1-10, joint success scenario-averaged): Opus 5 95.4, "
            "Sonnet 5 82.9 (control 70.5 / 65.3, coordinator 84.3 / 74.2)"
        ),
    ),
    "s2": Mitigation(
        name="s2",
        paper_label="s2: stricter booking behavior + look once, then act + cancel and book as one action",
        description=(
            "Prompt text only, every team desk: rules A and E after the pinned standing procedure; rule B "
            "as a paragraph above it. Peer channel, tools and world unchanged; the standard scheduler."
        ),
        formations=_TEAM,
        research_id="r2_stack_s5",
        harnesses=_HARNESSES,
        notes=(
            "paper (all 24 scenarios, episodes 1-10, joint success scenario-averaged): Opus 5 93.8, "
            "Sonnet 5 84.7 (control 70.5 / 65.3, coordinator 84.3 / 74.2)"
        ),
    ),
    "s3": Mitigation(
        name="s3",
        paper_label="s3: stricter booking behavior + act on what you hear + book before ending the call",
        description=(
            "The recommended clinic mitigation. Prompt text only, every team desk: rule A after the pinned "
            "standing procedure; rules C and D as paragraphs above it. Peer channel, tools and world "
            "unchanged; the standard scheduler."
        ),
        formations=_TEAM,
        research_id="r2_stack_s11",
        harnesses=_HARNESSES,
        notes=(
            "paper (all 24 scenarios, episodes 1-10, joint success scenario-averaged): Opus 5 95.3 "
            "[94.5, 96.1], Sonnet 5 91.8 [91.0, 92.6] (control 70.5 / 65.3, coordinator 84.3 / 74.2)"
        ),
    ),
}

#: The paper's runs of each arm (appendix, Run Details): Claude, the team, episodes 1-10 of every scenario.
RUNS: dict[str, Cells] = {arm: Cells(CLAUDE, _TEAM, episodes=10) for arm in STACKS}


def validate(
    name: str, formations: tuple[str, ...] | list[str] = (), harness: str | None = None
) -> Mitigation:
    """The arm called `name`, checked against the formations and harness it would run (`ValueError` if not)."""
    return _validate(MITIGATIONS, name, ENV, formations=formations, harness=harness)


def listing() -> str:
    """`--list-mitigations`."""
    return _listing(MITIGATIONS, ENV)


def build_sim_recipe(scenario: str, formation: str, mitigation: str) -> SimRecipe:
    """The simulated-harness recipe of one arm (`cells.build_sim_recipe` calls this for every arm but `none`).

    The formation's own spec with the arm's texts in every desk prompt (same cell id, same roster, tools
    and world), under the standard scheduler the paper's arms ran (`cells.MITIGATION_INSTRUMENT`).

    Raises:
        ValueError: An unknown arm or one that does not apply to `formation` / the simulated harness.
    """
    arm = validate(mitigation, [formation], "sim")
    from clinic import cells

    spec = cells.sim_spec(scenario, formation)
    patched = replace(spec, agents=patched_agents(arm.name, spec.agents))
    recipe = cells.instrument_recipe(scenario, cells.MITIGATION_INSTRUMENT, patched)
    return replace(recipe, mitigation=arm.name)


def build_cell(scenario: str, formation: str, epoch: int, mitigation: str) -> EnvCell:
    """The pi-harness cell of one arm (`cells.build_cell` calls this for every arm but `none`).

    The paper's arms ran on the simulated harness only, so `validate` refuses them here.

    Raises:
        ValueError: An unknown arm or one that does not apply to `formation` / the pi harness.
    """
    arm = validate(mitigation, [formation], "pi")
    raise ValueError(f"clinic mitigation {arm.name!r} has no pi-harness cell")


__all__ = [
    "DATE_MARKER",
    "MITIGATIONS",
    "RULES",
    "RUNS",
    "SOP_MARKER",
    "STACKS",
    "Rule",
    "Stack",
    "build_cell",
    "build_sim_recipe",
    "listing",
    "patched_agents",
    "resolve",
    "validate",
]
