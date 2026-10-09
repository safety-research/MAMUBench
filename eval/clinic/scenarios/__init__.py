"""The 24 clinic boards of record and the formation vocabulary.

The boards are the registered `clinic.scenarios._boards` pairs (P01..P12): each pair is one
drug-interaction theme authored as a `plain` twin (each claimant's evidence arrives assembled) and a
`split` twin (the same evidence scattered across carriers), so every same-day deadline contest exists
in both. Exactly the 24 the paper ran. Nothing here re-declares a board.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from _paths import bootstrap

bootstrap()

import clinic.scenarios._boards  # noqa: E402, F401  # pyright: ignore[reportUnusedImport]  (registers the 24 boards)
from clinic.environment import board_registry  # noqa: E402
from clinic.environment.resources import ScenarioKnobs  # noqa: E402
from clinic.scenarios.pressure import seeding_for  # noqa: E402

#: Eval formation -> (env topology, comms arm). `coordinator` = one desk holds the whole book (the
#: clinic's one-agent condition; there is no separate solo); `team` = one desk per inbound caller
#: (17-52 desks, the env's `meshfull`), every desk able to DM every other; `team_silent` = the same
#: floor with the DM channel removed. The research code's four-desk floor (`mesh4`) is not an eval
#: formation; mornings recorded on it read as foreign cells and are not scored.
FORMATIONS: dict[str, tuple[str, str]] = {
    "coordinator": ("steward", "nocomms"),
    "team": ("meshfull", "comms"),
    "team_silent": ("meshfull", "nocomms"),
}
#: The paper runs' `{topology}_{arm}` keys for the same formations.
CAMPAIGN_TOPO: dict[str, str] = {f: f"{t}_{a}" for f, (t, a) in FORMATIONS.items()}
FORMATION_BY_TOPO: dict[str, str] = {topo: f for f, topo in CAMPAIGN_TOPO.items()}
FRAMING = "f_all_closed"


def formation_of_cell(cell: str) -> str | None:
    """The eval formation a cell name encodes (`clinic_<board>_<topology>_<arm>_tight_scripted`), if any."""
    stem = cell.removeprefix("clinic_").removesuffix("_tight_scripted")
    for topo, formation in FORMATION_BY_TOPO.items():
        if stem.endswith(f"_{topo}"):
            return formation
    return None


#: The paper driver's check-in-less default: the end-of-shift debrief beat re-timed past the horizon.
DEBRIEF_MIN = 9999


@dataclass(frozen=True)
class Board:
    """One board of record: its pair, twin, contest count, shift length and the env's turn budget."""

    id: str
    pair: str
    twin: str
    theme: str
    contests: int
    callers: int
    horizon: int
    turns_hint: int


def _row(board_id: str) -> Board:
    spec = board_registry.board(board_id)
    return Board(
        id=board_id,
        pair=spec.pair_id,
        twin=spec.twin,
        theme=spec.theme_slug,
        contests=spec.size,
        callers=len(spec.callers()),
        horizon=int(seeding_for(board_id).horizons[0]),
        turns_hint=spec.max_turns_hint(),
    )


#: Registration order = the paper's assignment order (P01..P12, plain before split).
BOARDS: dict[str, Board] = {
    board_id: _row(board_id) for board_id in board_registry.board_ids()
}
assert len(BOARDS) == 24, sorted(BOARDS)


def board(board_id: str) -> Board:
    """Look one board up; a typo names the registry instead of raising a bare `KeyError`."""
    try:
        return BOARDS[board_id]
    except KeyError:
        raise SystemExit(
            f"unknown board {board_id!r}; the 24 of record are: {', '.join(BOARDS)}"
        ) from None


def select(
    names: list[str], *, all_: bool = False, twin: str | None = None
) -> list[Board]:
    """The boards an invocation runs, in registry order (`--board`, `--all`, `--twin`)."""
    wanted = set(names)
    if all_:
        wanted |= set(BOARDS)
    if twin is not None:
        wanted |= {b.id for b in BOARDS.values() if b.twin == twin}
    if not wanted:
        raise SystemExit("pick boards: --board <id>..., --twin {plain,split} or --all")
    for name in sorted(wanted - BOARDS.keys()):
        board(name)
    return [b for name, b in BOARDS.items() if name in wanted]


#: The shift every board plays on the paper's simulated harness: the knobs' default horizon (`cells.sim_knobs`).
SIM_HORIZON_MIN = int(
    next(str(f.default) for f in fields(ScenarioKnobs) if f.name == "horizon")
)


def listing() -> str:
    """The registry as a table (`run.py --list`), with a note on which harness plays the declared values."""
    lines = [
        f"{'board':34} {'pair':32} {'twin':5} {'contests':>8} {'callers':>7} {'declared':>8} {'pi turns':>8}"
    ]
    lines += [
        f"{b.id:34} {b.pair:32} {b.twin:5} {b.contests:>8} {b.callers:>7} {b.horizon:>8} {b.turns_hint:>8}"
        for b in BOARDS.values()
    ]
    lines += [
        "",
        "declared: the board's declared shift in minutes; pi turns: its turn budget. The pi harness plays both.",
        f"The paper's simulated harness (the default) plays every board at {SIM_HORIZON_MIN} minutes with each "
        "formation's step budget (run.py --print-info prints it per cell).",
    ]
    return "\n".join(lines)
