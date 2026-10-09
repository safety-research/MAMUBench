"""The paper's 25 api_key scenarios and the formation vocabulary.

The scenarios are `api_key.environment.resources.STUDY_SCENARIOS`: the three-dose stakes ladder plus
the 8- and 16-seat stakes casts (5) and the 20 certified priced-equality economies (`peq_*`), exactly
the set the paper ran and the reference tables
freeze. Nothing here re-declares a scenario: knobs, rosters and seeds all come from the env.
"""

from __future__ import annotations

from dataclasses import dataclass

from _paths import bootstrap

bootstrap()

from api_key.environment.resources import SCENARIOS as KNOBS  # noqa: E402
from api_key.environment.resources import STUDY_SCENARIOS  # noqa: E402
from api_key.scenarios.roster import roster_for_scenario  # noqa: E402

#: Eval formation -> (env topology, peer mailbox on). `coordinator` = one agent owns every job;
#: `team` = one agent per job owner with peer DMs; `team_silent` = the same team, DM channel removed;
#: `solo` = one agent for ONE owner (Maya) who holds every job (`prompts.build_solo_spec`: the steward's
#: machinery with the single true owner; live pi framing only, so it runs on the simulated harness only).
FORMATIONS: dict[str, tuple[str, bool]] = {
    "coordinator": ("steward", True),
    "team": ("mesh", True),
    "team_silent": ("mesh", False),
    "solo": ("solo", False),
}
#: The formations `run.py` plays when `--formation` is not given (the three multi-principal formations;
#: the paper's matrix adds `solo`: `--formation solo coordinator team team_silent`).
DEFAULT_FORMATIONS: tuple[str, ...] = ("coordinator", "team", "team_silent")
#: Formations with no console framing (so no `--harness pi` cell).
SIM_ONLY_FORMATIONS: frozenset[str] = frozenset({"solo"})


@dataclass(frozen=True)
class Scenario:
    """One of the paper's scenarios: its family, cast size and the two capacity knobs."""

    id: str
    family: str  # "stakes" | "peq"
    n_seats: int
    budget: int
    org_cap: int


def _row(name: str) -> Scenario:
    knobs = KNOBS[name]
    return Scenario(
        id=name,
        family="stakes" if name.startswith("stakes_") else "peq",
        n_seats=roster_for_scenario(name).n_seats,
        budget=knobs.budget,
        org_cap=knobs.org_cap,
    )


#: Registry order = the env's: the stakes family, then the peq registry.
SCENARIOS: dict[str, Scenario] = {name: _row(name) for name in STUDY_SCENARIOS}
assert len(SCENARIOS) == 25, sorted(SCENARIOS)


def scenario(name: str) -> Scenario:
    """Look one scenario up; a typo names the registry instead of raising a bare `KeyError`."""
    try:
        return SCENARIOS[name]
    except KeyError:
        raise SystemExit(
            f"unknown scenario {name!r}; the 25 of record are: {', '.join(SCENARIOS)}"
        ) from None


def select(
    names: list[str], *, all_: bool = False, seats: int | None = None
) -> list[Scenario]:
    """The scenarios an invocation runs, in registry order (`--scenario`, `--all`, `--seats`)."""
    wanted = set(names)
    if all_:
        wanted |= set(SCENARIOS)
    if seats is not None:
        wanted |= {row.id for row in SCENARIOS.values() if row.n_seats == seats}
    if not wanted:
        raise SystemExit(
            "pick scenarios: --scenario <id>..., --seats {4,8,16} or --all"
        )
    for name in sorted(wanted - SCENARIOS.keys()):
        scenario(name)
    return [row for name, row in SCENARIOS.items() if name in wanted]


def listing() -> str:
    """The registry as a table (`run.py --list`)."""
    lines = [f"{'scenario':18} {'family':7} {'seats':>5} {'budget':>12} {'org_cap':>8}"]
    lines += [
        f"{r.id:18} {r.family:7} {r.n_seats:>5} {r.budget:>12,} {r.org_cap:>8,}"
        for r in SCENARIOS.values()
    ]
    return "\n".join(lines)
