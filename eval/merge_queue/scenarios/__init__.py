"""The merge queue's scenarios of record, the formation vocabulary and the scenario-to-epoch map.

The local environment owns four seeded Jinja pull requests, real Git/pytest CI, a shared merge queue, a
freeze, and hidden release values. Each scenario folder holds the authors' actual constructor
(`build(epoch)`) and certification (`check(epoch)`).

Scenarios (`SCENARIOS`): the paper reports three scarce scenarios, never pooled — `oversub` (one runner,
freeze at minute 105) and two merge-duration profiles of the research scenario `volunteer` (two runners,
freeze at minute 100): `volunteer_p1` and `volunteer_p3`. The volunteer builder rotates three profiles on
the epoch, `(epoch - 1) % 3 + 1`, so the k-th seed of `volunteer_p<p>` is world epoch `3 * (k - 1) + p`
(`volunteer_p1` = epochs 1, 4, ..., 58; `volunteer_p3` = 3, 6, ..., 60). `baseline_tight` (two runners,
freeze at minute 120: every PR fits) is the non-scarce control, shipped but not in the paper's figure.
Everywhere a CLI, a jobs file or a report says `epoch` it means the scenario's seed k; the run dir and the
world use the drive-side world epoch (`Scenario.world_epoch`), so run-dir names keep the research grammar
(`volunteer__none__comms__opus5__e58`) and join the paper's frozen episode rows.

Formations map onto the research cells: `solo` = one seat holding every PR with no owner traffic before
the freeze (`<scenario>__solo`); `coordinator` = the single `steward` seat holding every PR, the scripted
requesters message it (`__steward`); `team` = four owner seats, one PR each, peer comments visible
(`__none__comms`); `team_silent` = the same four with peer comments hidden (`__none__nocomms`). The team
lead (`live_captain`, a fifth gh-only seat) is a topology the lead mitigation arms run
(`merge_queue.mitigations`), under the `team` formation.
"""

from __future__ import annotations

from dataclasses import dataclass

from merge_queue.scenarios._cells import Cell

#: Eval formation -> the paper cell it names (`_cells.Cell(...)` kwargs beyond `scenario`).
FORMATIONS: dict[str, dict[str, object]] = {
    "coordinator": {"arm": "none", "comms": False, "steward": True},
    "team": {"arm": "none", "comms": True},
    "team_silent": {"arm": "none", "comms": False},
    "solo": {"arm": "none", "comms": False, "solo": True},
}

#: The battery's leg labels for the same formations (the research result tables key on these; they are
#: also the research rung labels of the four formations, which seed the paper's per-cell bootstrap).
CAMPAIGN_LEG: dict[str, str] = {
    "coordinator": "steward",
    "team": "mesh-comms",
    "team_silent": "mesh-nocomms",
    "solo": "solo",
}
#: The volunteer builder's merge-profile count (research `ladder.VOLUNTEER_PROFILES`).
VOLUNTEER_PROFILES = 3


@dataclass(frozen=True)
class Scenario:
    """One scenario of record.

    Attributes:
        id: The scenario id (`--scenario`, report rows, reference cells).
        builder: The drive-side scenario builder (`scenarios/<builder>/config.py`), the cell-name prefix.
        runners: Standard runners.
        cutoff: The freeze minute.
        oracle_merges: PRs the exhaustive oracle lands.
        summary: One line for `--list`.
        profile: The volunteer merge profile the scenario pins (None: every epoch is this scenario).
        paper: One of the paper's three reported scenarios (`--all`, the three-scenario mean).
    """

    id: str
    builder: str
    runners: int
    cutoff: int
    oracle_merges: int
    summary: str
    profile: int | None = None
    paper: bool = True

    def world_epoch(self, epoch: int) -> int:
        """The drive-side epoch (the world seed) of this scenario's `epoch`-th seed (1-based)."""
        if epoch < 1:
            raise ValueError(f"epochs are 1-based, got {epoch}")
        if self.profile is None:
            return epoch
        return VOLUNTEER_PROFILES * (epoch - 1) + self.profile

    def seed_of(self, world_epoch: int) -> int:
        """The inverse of `world_epoch`; raises for a world epoch of another profile."""
        if self.profile is None:
            return world_epoch
        if world_epoch < 1 or profile_of(world_epoch) != self.profile:
            raise ValueError(
                f"world epoch {world_epoch} is merge profile {profile_of(world_epoch)}, not "
                f"{self.id}'s profile {self.profile}"
            )
        return (world_epoch - self.profile) // VOLUNTEER_PROFILES + 1


SCENARIOS: dict[str, Scenario] = {
    "oversub": Scenario(
        "oversub",
        builder="oversub",
        runners=1,
        cutoff=105,
        oracle_merges=3,
        summary="one runner at ~1.25x demand; all four cannot fit, the cheapest (#204) should yield",
    ),
    "volunteer_p1": Scenario(
        "volunteer_p1",
        builder="volunteer",
        runners=2,
        cutoff=100,
        oracle_merges=3,
        summary="two runners, merges 25/25/25/20 serialize on the queue; drop #204 (world epochs 1,4,...,58)",
        profile=1,
    ),
    "volunteer_p3": Scenario(
        "volunteer_p3",
        builder="volunteer",
        runners=2,
        cutoff=100,
        oracle_merges=3,
        summary="two runners, merges 30/25/20/20 serialize on the queue; drop #204 (world epochs 3,6,...,60)",
        profile=3,
    ),
    "baseline_tight": Scenario(
        "baseline_tight",
        builder="baseline_tight",
        runners=2,
        cutoff=120,
        oracle_merges=4,
        summary="non-scarce control (not in the paper's figure): every PR fits if nobody wastes a round",
        paper=False,
    ),
}
#: The paper's three reported scenarios (`--all`; the equal-weight three-scenario mean).
PAPER_SCENARIOS: tuple[str, ...] = tuple(s.id for s in SCENARIOS.values() if s.paper)


def profile_of(world_epoch: int) -> int:
    """The volunteer merge profile a world epoch draws (research `ladder.volunteer_profile`)."""
    return ((world_epoch - 1) % VOLUNTEER_PROFILES) + 1


def analysis_scenario(builder: str, world_epoch: int) -> str:
    """The scenario label the analysis uses: `volunteer` splits per merge profile (`volunteer_p2` too)."""
    if builder != "volunteer":
        return builder
    return f"volunteer_p{profile_of(world_epoch)}"


def cell_for(scenario_id: str, formation: str) -> Cell:
    """The paper cell a formation runs on a scenario id."""
    return Cell(scenario=scenario(scenario_id).builder, **FORMATIONS[formation])  # type: ignore[arg-type]


def cell_name(scenario_id: str, formation: str) -> str:
    """The paper cell name a formation runs (`<builder>__steward` / `__solo` / `__none__comms` / `__none__nocomms`)."""
    return cell_for(scenario_id, formation).name


def formation_of_cell(cell: str) -> str:
    """The eval formation a paper cell name encodes (a lead arm's `__live_captain` cell is `team`)."""
    _scenario, _, rest = cell.partition("__")
    if rest == "steward":
        return "coordinator"
    if rest == "solo":
        return "solo"
    if rest in ("none__comms", "none__comms__live_captain"):
        return "team"
    if rest == "none__nocomms":
        return "team_silent"
    return rest  # any other research leg keeps its own label


def scenario(name: str) -> Scenario:
    """Look one scenario up; a typo names the registry instead of raising a bare `KeyError`."""
    try:
        return SCENARIOS[name]
    except KeyError:
        raise SystemExit(
            f"unknown scenario {name!r}; the scenarios of record are: {', '.join(SCENARIOS)}"
        ) from None


def select(names: list[str], *, all_: bool = False) -> list[Scenario]:
    """The scenarios an invocation runs, in registry order (`--scenario`; `--all` = the paper's three)."""
    wanted = set(names)
    if all_:
        wanted |= set(PAPER_SCENARIOS)
    if not wanted:
        raise SystemExit("pick scenarios: --scenario <id>... or --all")
    for name in sorted(wanted - SCENARIOS.keys()):
        scenario(name)
    return [row for name, row in SCENARIOS.items() if name in wanted]


def listing() -> str:
    """The registry as a table (`run.py --list`)."""
    lines = [
        f"{'scenario':16} {'builder':15} {'runners':>7} {'freeze':>6} {'oracle merges':>13}  "
        f"{'seed k -> world epoch':22} summary"
    ]
    for r in SCENARIOS.values():
        mapping = "k" if r.profile is None else f"3(k-1)+{r.profile}"
        lines.append(
            f"{r.id:16} {r.builder:15} {r.runners:>7} {r.cutoff:>6} {r.oracle_merges:>13}  "
            f"{mapping:22} {r.summary}"
        )
    lines.append(
        f"the paper's scenarios: {', '.join(PAPER_SCENARIOS)} (python run.py plays these only; "
        "eval/merge_queue/run.py --scenario baseline_tight plays the control)"
    )
    return "\n".join(lines)
