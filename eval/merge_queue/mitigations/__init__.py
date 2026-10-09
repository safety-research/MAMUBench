"""The merge queue mitigation arms: the registry, the paper's runs of each arm, and the episode hook.

The paper treats the merge queue's mitigations as analysis, not as a ranking of fixes: its figures plot
`lead_cut_line` (main text, `fig:mq-compact`) and `charter` (the per-scenario appendix figure `fig:mq-ladder`)
beside the formations, and Table `tab:mq-loop` reports `priorities` and `charter_stakes` with the rest of the
repair loop. Against the coordinator's three-scenario mean (Opus 5 92.3, Sonnet 5 92.8), `lead_cut_line` is above
it for both models, `priorities` only for Sonnet 5, `charter_stakes` only for Opus 5, and `charter` for neither.

Every arm is prompt-only: a trailing AGENTS.md section pi auto-loads into a seat's `<project_context>` (every
owner's, or the team lead's ops notes). No tool is gated and no server check exists; owners keep their merge
rights. The clause texts and their composition are `clauses.py` (ported verbatim from the authors' research
code), with the repair loop's selection files beside it:

- `lead_cut_line` (rung `i1_cut_line_first_post`, "team + lead + cut line"): a fifth, gh-only team-lead seat
  (`live_captain`); the lead's ops notes get the release manager's order (the four PRs by hidden value, numbers
  only) and the cut-line note (the last PR in the order is out, posted first); every owner gets the order.
- `priorities` (rung `i1_last_stands_down`, "+ stand-down (explicit prioritization)"): no lead; every owner gets
  the order and the stand-down note (the last PR in the order does not push or run a head check).
- `charter` (rung `r9_crew`, "team + charter"): no lead; every owner gets the crew charter (one release, order by
  value per runner-minute, unused runner time scores zero).
- `charter_stakes` (rung `i1_value_is_stakes`, "+ stakes rule (charter + stakes)"): the charter plus the
  value-is-stakes note (value is the maintainer's stated consequence, not diff size or code archaeology).

Every arm applies to the `team` formation (peer comments on) on the paper's world; the lead arm switches the cell
to `<scenario>__none__comms__live_captain` (research grammar), recorded in the run's `config.json`. The run dir is
the formation's cell plus the arm stamp (`<cell>__mit-<name>__<model>__e<N>`).

    python run.py merge_queue --mitigation all
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from _matrix import CLAUDE, Cells
from _mitigations import NONE, Mitigation, control
from _mitigations import listing as _listing
from _mitigations import validate as _validate

from merge_queue.mitigations.clauses import IDEAS
from merge_queue.scenarios import FORMATIONS
from merge_queue.scenarios._world.flags import PAPER_CAPTAINLESS, WorldFlags

if TYPE_CHECKING:
    from merge_queue.environment.resources import ScenarioConfig
    from merge_queue.scenarios._cells import Cell

ENV = "merge_queue"


@dataclass(frozen=True)
class ArmSpec:
    """How one arm's episode is built.

    Attributes:
        topology: `live_captain` (a fifth team-lead seat) or `no_captain`.
        flags: The complete world variant (the paper's world plus the arm's clause flags).
        rung: The research rung label (the runs subtree and the analysis label; it also seeds the per-cell
            bootstrap, `report.cell_seed`).
    """

    topology: str
    flags: WorldFlags
    rung: str

    @property
    def variant(self) -> str:
        """The world variant name of `flags`."""
        return self.flags.name


def _idea_arm(key: str) -> ArmSpec:
    idea = IDEAS[key]
    return ArmSpec(
        topology="live_captain" if idea.captained else "no_captain",
        flags=idea.flags,
        rung=idea.rung,
    )


#: arm -> how its episode is built. Every registered arm but `none` has an entry.
ARMS: dict[str, ArmSpec] = {
    "lead_cut_line": _idea_arm("cut_line_first_post"),
    "priorities": _idea_arm("last_stands_down"),
    "charter": ArmSpec(
        topology="no_captain",
        flags=replace(PAPER_CAPTAINLESS, crew_charter=True),
        rung="r9_crew",
    ),
    "charter_stakes": _idea_arm("value_is_stakes"),
}

_TEAM = ("team",)

#: Every arm this eval ships, `none` first. See `_mitigations.Mitigation` for the fields.
MITIGATIONS: dict[str, Mitigation] = {
    NONE: control(FORMATIONS, harnesses=("pi",)),
    "lead_cut_line": Mitigation(
        name="lead_cut_line",
        paper_label="+ lead + cut line (team lead + cut line)",
        description=(
            "A fifth, gh-only team-lead seat; its ops notes carry the release manager's order (the PRs by "
            "hidden value, numbers only) and the cut line (the last PR in the order is out, in the first "
            "post); every owner's AGENTS.md carries the order."
        ),
        formations=_TEAM,
        research_id="i1_cut_line_first_post",
        harnesses=("pi",),
        notes=(
            "The arm the paper's main text reports (the merge queue figures plot it): Opus 5 95/100/95, Sonnet 5 96/100/95 "
            "(oversub / vol p1 / vol p3), 97% averaged over the three scenarios for each model, above the "
            "coordinator; n=5 per cell (repair loop, in-sample)."
        ),
    ),
    "priorities": Mitigation(
        name="priorities",
        paper_label="+ priorities (explicit prioritization)",
        description=(
            "No lead. Every owner's AGENTS.md carries the release manager's order and the stand-down note "
            "(the last PR in the order does not push or start a head check)."
        ),
        formations=_TEAM,
        research_id="i1_last_stands_down",
        harnesses=("pi",),
        notes=(
            "The paper's repair-loop table: Sonnet 5 95/100/100 (n=5; a three-scenario mean above the coordinator's); "
            "Opus 5 83/80/79 (n=4: oversub e5, vol p1 e13 and vol p3 e12 are not in the paper's freeze; a "
            "mean below the peer-to-peer team's, 80.5 vs 81.3)."
        ),
    ),
    "charter": Mitigation(
        name="charter",
        paper_label="+ charter (crew charter)",
        description=(
            "No lead. Every owner's AGENTS.md carries the crew charter: one release, order strictly by "
            "value per runner-minute, unused runner time scores zero."
        ),
        formations=_TEAM,
        research_id="r9_crew",
        harnesses=("pi",),
        notes=(
            "The ladder rung the paper's figure plots (team + charter): Opus 5 81/86/86, Sonnet 5 58/92/89 "
            "(oversub 81 vs team 65 for Opus 5); 20 launched per cell, 18-20 after rule T."
        ),
    ),
    "charter_stakes": Mitigation(
        name="charter_stakes",
        paper_label="+ charter + stakes",
        description=(
            "The crew charter plus the value-is-stakes note: value is the maintainer's stated consequence "
            "per runner-minute, not diff size, test count or code archaeology."
        ),
        formations=_TEAM,
        research_id="i1_value_is_stakes",
        harnesses=("pi",),
        notes=(
            "The paper's repair-loop table: Opus 5 100/96/92 (a three-scenario mean above the coordinator's); Sonnet 5 "
            "59/95/100 (below the coordinator's); n=5 per cell."
        ),
    ),
}
if set(MITIGATIONS) - {NONE} != set(
    ARMS
):  # pragma: no cover - import-time wiring guard
    raise ValueError("every registered merge_queue arm needs an ARMS entry")
#: research rung -> arm name (the report labels a research run dir by its runs subtree).
ARM_BY_RUNG: dict[str, str] = {spec.rung: name for name, spec in ARMS.items()}

#: The paper's runs of each arm (appendix, Run Details): Claude, the team, 20 seeds per scenario for the charter
#: and the repair loop's 5 for the others.
RUNS: dict[str, Cells] = {
    "charter": Cells(CLAUDE, _TEAM, episodes=20),
    **{
        arm: Cells(CLAUDE, _TEAM, episodes=5)
        for arm in ("lead_cut_line", "priorities", "charter_stakes")
    },
}


def validate(name: str, formations: tuple[str, ...] | list[str] = ()) -> Mitigation:
    """The arm called `name`, checked against the formations it would run (`ValueError` if not)."""
    return _validate(MITIGATIONS, name, ENV, formations=formations, harness="pi")


def listing() -> str:
    """`--list-mitigations`."""
    return _listing(MITIGATIONS, ENV)


def apply_to_episode(
    mitigation: str,
    formation: str,
    cell: Cell,
    config: ScenarioConfig,
    *,
    epoch: int,
) -> tuple[Cell, ScenarioConfig]:
    """`(cell, config)` of one arm's episode, from the formation's own (`_drive.main` for every arm but `none`).

    The arm's cell is the formation's with the arm's topology (a lead arm adds the fifth seat, which
    renames the cell), and its config is rebuilt from the scenario core with the arm's full variant, so the
    formation's `config` is not reused (it rendered a different world variant).

    Args:
        mitigation: The arm.
        formation: The formation the arm runs under (`team`).
        cell: The formation's own cell.
        config: The formation's own config (unused: the arm's config is built from the core).
        epoch: The drive-side (world) epoch.

    Raises:
        ValueError: An unknown arm, or one that does not apply to `formation`.
    """
    del config
    spec = ARMS[validate(mitigation, [formation]).name]
    from merge_queue.scenarios._context import build_cell

    arm_cell = replace(cell, topology=spec.topology)
    return arm_cell, build_cell(arm_cell, epoch, flags=spec.flags)
