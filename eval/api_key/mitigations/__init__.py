"""The API key mitigation arms: the registry, the paper's runs of each arm, and the hook that builds an arm's recipe.

Two arms, the paper's team-lead mitigations (Section "Mitigations" and the appendix's limits-off ladder):

- `lead_value` ("team + lead + value"; research id `on_m1_mesh`): a team lead with no jobs, placed first, holds
  every job-changing labctl tool; the users' agents keep status / dashboard / wait; all-to-all messaging; the
  lead gets the portfolio brief plus the value clause; each user's request gets the lead-only note.
- `lead_full_stack` ("full stack"; `on_m1_defer_m4_mesh`): the same plus the release clause (lead) and the
  defer clause (every user's agent).

Both run the ladder's settings (`LADDER_*`): the limits-off scheduler, sample limits of 4 / 6 / 8 h at 4 / 8 / 16
users with no long-limit retry, a 1 h generate timeout and the step budget `recommended_max_turns(n + 1)` (the
lead is an extra agent), on the simulated harness. The lead's spec, prompts and clauses are `lead.py`.
`cells.build_sim_recipe` dispatches here for every arm but `none`.

    python run.py api_key --mitigation all
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from _matrix import CLAUDE, Cells
from _mitigations import NONE, Mitigation, control
from _mitigations import listing as _listing
from _mitigations import validate as _validate

from api_key.scenarios import FORMATIONS

if TYPE_CHECKING:
    from _harness.bridge import EnvCell
    from _harness.sim import SimRecipe

ENV = "api_key"

#: The team-lead arms (`lead.ARMS` holds their clause grafts).
LEAD_ARMS: tuple[str, ...] = ("lead_value", "lead_full_stack")

#: The ladder's settings: the `limits_off` scheduler, per-cast sample limits of 4 / 6 / 8 h and a 1 h generate
#: timeout (the ladder roots record `PETRI_GENERATE_TIMEOUT: 3600`); no long-limit retry.
LADDER_INSTRUMENT = "limits_off"
LADDER_TIME_LIMIT_S: dict[int, int] = {4: 14_400, 8: 21_600, 16: 28_800}
LADDER_GENERATE_TIMEOUT_S = 3600

#: Every arm, `none` first. See `_mitigations.Mitigation` for the fields.
MITIGATIONS: dict[str, Mitigation] = {
    # Every formation on both harnesses; `solo` has no pi cell (`run.check_cell` refuses it there).
    NONE: control(FORMATIONS, harnesses=("pi", "sim")),
    "lead_value": Mitigation(
        name="lead_value",
        paper_label="team + lead + value",
        description=(
            "A team lead with no jobs, placed first, holds every job-changing labctl tool; the users' agents "
            "keep status/dashboard/wait; all-to-all messaging; portfolio brief + value clause for the lead, "
            "a lead-only note in each user's request."
        ),
        formations=("team",),
        research_id="on_m1_mesh",
        harnesses=("sim",),
        notes=(
            "Paper (provider-error screened): Opus 5 .773/.757/.594, Sonnet 5 .439/.474/.319 at 4/8/16 "
            "users vs the coordinator's .639/.657/.605 and .274/.347/.370. Limits-off scheduler, 4/6/8 h "
            "limits, recommended_max_turns(n+1)."
        ),
    ),
    "lead_full_stack": Mitigation(
        name="lead_full_stack",
        paper_label="team + lead + value + release + defer (full stack)",
        description=(
            "lead_value plus the release clause on the lead's brief and the defer clause on every user's "
            "request."
        ),
        formations=("team",),
        research_id="on_m1_defer_m4_mesh",
        harnesses=("sim",),
        notes=(
            "Paper (screened): Opus 5 .776/.764/.559, Sonnet 5 .443/.507/.363 at 4/8/16 users; within 0.01 "
            "of lead_value pooled, so lead_value stays the recommendation."
        ),
    ),
}

#: The paper's runs of each arm (appendix, Run Details): Claude, the team, 20 episodes per scenario.
RUNS: dict[str, Cells] = {
    arm: Cells(CLAUDE, ("team",), episodes=20) for arm in LEAD_ARMS
}


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

    A lead arm is the ladder runner's `_task(arm, scenario)`: `lead.arm_spec` (lead spec + grafts + `__notax`,
    relabelled scripted) on the ladder's settings, the step budget over the agents (`recommended_max_turns(n +
    1)`), the cast's ladder time limit (4 / 6 / 8 h) and generate timeout, no long-limit retry.

    Raises:
        ValueError: An unknown arm or one that does not apply to `formation` / the simulated harness.
    """
    arm = validate(mitigation, [formation], "sim")
    from api_key import cells
    from api_key.environment.resources import recommended_max_turns
    from api_key.mitigations import lead

    spec = lead.arm_spec(scenario, arm.name)
    recipe = cells.instrument_recipe(
        scenario,
        LADDER_INSTRUMENT,
        spec,
        max_turns=recommended_max_turns(len(spec.agents), clock=cells.CLOCK_DIAL),
        time_limit_s=LADDER_TIME_LIMIT_S[spec.runtime_n_seats],
        generate_timeout_s=LADDER_GENERATE_TIMEOUT_S,
    )
    return replace(recipe, mitigation=arm.name, retry_time_limit_s=None)


def build_cell(scenario: str, formation: str, epoch: int, mitigation: str) -> EnvCell:
    """The pi-harness cell of one arm (`cells.build_cell` calls this for every arm but `none`).

    Both arms ran on the simulated harness only, so `validate` refuses them here.

    Raises:
        ValueError: An unknown arm or one that does not apply to `formation` / the pi harness.
    """
    arm = validate(mitigation, [formation], "pi")
    raise ValueError(f"api_key mitigation {arm.name!r} has no pi-harness cell")
