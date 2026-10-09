"""The paper cells this eval builds: three drive-side scenarios, four formations, the lead topology.

Ported from the authors' research code (`cells.py`), narrowed to
what the paper ran: arm `none` only (the pressure arms are not ported), topologies `no_captain` (the
leaderless baseline every formation runs) and `live_captain` (a fifth, gh-only team-lead seat; the lead
mitigation arms run it, comms on). Cell names keep the research grammar, so a run dir named here joins the
paper's frozen episode rows on sight.
"""

from dataclasses import dataclass

#: The drive-side scenario builders (`scenarios/<name>/config.py`). The paper's `volunteer_p1` and
#: `volunteer_p3` are two merge profiles of `volunteer`, selected by the epoch (`scenarios.SCENARIOS`).
SCENARIO_NAMES: tuple[str, ...] = ("baseline_tight", "oversub", "volunteer")
#: The only pressure arm this eval runs (the research code's other four are not ported).
ARM_NAMES: tuple[str, ...] = ("none",)
DEFAULT_TOPOLOGY = "no_captain"
TOPOLOGIES: tuple[str, ...] = ("no_captain", "live_captain")
CAPTAINED_TOPOLOGIES: tuple[str, ...] = ("live_captain",)
#: The research code's mitigation-ladder scenario surface (`cells.LADDER_SCENARIOS`): the world
#: variants and the mitigation clauses are certified on exactly these builders.
LADDER_SCENARIOS: tuple[str, ...] = SCENARIO_NAMES


@dataclass(frozen=True)
class Cell:
    """One grid cell (model- and epoch-independent), exactly the research `cells.Cell` for the cells ported.

    Attributes:
        scenario: The drive-side scenario builder (`SCENARIO_NAMES`).
        arm: The pressure arm; `none` only.
        comms: Peer comments visible (`team`) or hidden (`team_silent`); off for single-seat cells.
        steward: The coordinator: one seat holding every PR, the requesters message it.
        solo: The steward seat minus the mid-episode owner traffic (post-freeze debriefs stay).
        topology: `no_captain` (every formation) or `live_captain` (the lead arms' fifth seat).
    """

    scenario: str
    arm: str
    comms: bool
    steward: bool = False
    solo: bool = False
    topology: str = DEFAULT_TOPOLOGY

    def __post_init__(self) -> None:
        if self.scenario not in SCENARIO_NAMES:
            raise ValueError(f"unknown scenario {self.scenario!r}")
        if self.arm not in ARM_NAMES:
            raise ValueError(
                f"only the arm the paper ran (none) is supported, not {self.arm!r}"
            )
        if self.topology not in TOPOLOGIES:
            raise ValueError(f"unknown topology {self.topology!r}")
        if self.steward and self.solo:
            raise ValueError("steward and solo are distinct single-seat cells")
        if (self.steward or self.solo) and self.comms:
            raise ValueError("single-seat cells (steward/solo) have their comms axis off")
        if (self.steward or self.solo) and self.topology != DEFAULT_TOPOLOGY:
            raise ValueError(
                "single-seat cells (steward/solo) run the no_captain baseline topology"
            )
        if self.topology == "live_captain" and not self.comms:
            raise ValueError(
                "the live_captain (team lead) cells this eval runs are comms-on (the paper's lead arms)"
            )

    @property
    def name(self) -> str:
        """The research cell name: `<scenario>__steward`, `__solo`, `__none__<comms>[__live_captain]`."""
        if self.steward:
            return f"{self.scenario}__steward"
        if self.solo:
            return f"{self.scenario}__solo"
        base = f"{self.scenario}__{self.arm}__{'comms' if self.comms else 'nocomms'}"
        if self.topology != DEFAULT_TOPOLOGY:
            return f"{base}__{self.topology}"
        return base
