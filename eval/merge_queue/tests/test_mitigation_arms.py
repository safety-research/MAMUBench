"""The merge_queue mitigation arms: the registry, the team-only gate, and the clauses' build-time gates.

The arms' rendered briefs are pinned against the paper's run dirs through the launcher's `--print-info`
(`test_release_layout.py`), and every arm's config against the research builds (`test_world.py`).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from typing import Any, cast

import pytest
from _mitigations import NONE

from merge_queue import _drive, mitigations
from merge_queue.mitigations.clauses import (
    IDEAS,
    SELECTED_DIR,
    scan_clause_texts,
)
from merge_queue.run import parse_args, plan
from merge_queue.scenarios import FORMATIONS, cell_for
from merge_queue.scenarios._cells import Cell
from merge_queue.scenarios._context import build_cell
from merge_queue.scenarios._world import PAPER_CAPTAINLESS, WorldFlags

#: the paper's repair-loop selection files
SELECTED_SHA256 = {
    "selected_round1.json": "c3940116f0a65ca425555f237d2cbe2796078bc78f7a12cf1709c5ad0b6be7ad",
    "selected_round2.json": "1928d285fb91fc42113f11edd51cd8ee1c40683fd398ae8d1f352310c1983a58",
}
#: arm -> (research rung = the registry's research_id, the world variant `config.json` records, topology)
ARMS = {
    "lead_cut_line": (
        "i1_cut_line_first_post",
        "noprio_subtle_stakes_briefs_only_lead_priorities_seat_priorities_idea_cut_line_first_post",
        "live_captain",
    ),
    "priorities": (
        "i1_last_stands_down",
        "noprio_nocaptain_subtle_stakes_briefs_only_seat_priorities_idea_last_stands_down",
        "no_captain",
    ),
    "charter": (
        "r9_crew",
        "noprio_nocaptain_subtle_stakes_briefs_only_crew_charter",
        "no_captain",
    ),
    "charter_stakes": (
        "i1_value_is_stakes",
        "noprio_nocaptain_subtle_stakes_briefs_only_crew_charter_idea_value_is_stakes",
        "no_captain",
    ),
}


def test_the_registry_ships_the_papers_arms() -> None:
    arms = mitigations.MITIGATIONS
    assert list(arms) == [NONE, *ARMS]
    assert arms[NONE].formations == tuple(FORMATIONS)
    for name, (rung, variant, topology) in ARMS.items():
        spec = mitigations.ARMS[name]
        assert (arms[name].research_id, spec.rung) == (rung, rung)
        assert (spec.variant, spec.topology) == (variant, topology)
        assert arms[name].formations == ("team",)
    assert all(arm.harnesses == ("pi",) for arm in arms.values())
    # the research registry names each repair-loop idea's variant as its flags do
    assert all(idea.variant == idea.flags.name for idea in IDEAS.values())
    assert mitigations.ARM_BY_RUNG == {
        rung: name for name, (rung, _, _) in ARMS.items()
    }
    for name, digest in SELECTED_SHA256.items():
        assert hashlib.sha256((SELECTED_DIR / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize("formation", ["coordinator", "team_silent", "solo"])
def test_an_arm_is_refused_outside_the_team(formation: str) -> None:
    """By the launcher's plan, by the episode hook, and by `_drive.py` before anything is built."""
    with pytest.raises(SystemExit, match="applies to formation"):
        plan(
            parse_args(
                [
                    "--scenario",
                    "oversub",
                    "--formation",
                    formation,
                    "--mitigation",
                    "charter",
                ]
            )
        )
    with pytest.raises(
        ValueError, match=rf"applies to formation\(s\) team, not {formation}"
    ):
        mitigations.apply_to_episode(
            "lead_cut_line",
            formation,
            cell_for("oversub", formation),
            cast(Any, None),
            epoch=1,
        )
    argv = [
        *("--scenario", "oversub", "--formation", formation, "--epoch", "1"),
        *(
            "--model",
            "m",
            "--model-slug",
            "m",
            "--provider",
            "anthropic",
            "--key-env",
            "K",
        ),
        *("--runs-root", "r", "--agent-roots-base", "a", "--pi-cmd", "pi"),
        *("--mitigation", "priorities"),
    ]
    with pytest.raises(ValueError, match="applies to formation"):
        _drive.main(argv)


def _build(cell: Cell, flags: WorldFlags) -> Callable[[], object]:
    return lambda: build_cell(cell, 1, flags=flags)


def _charter(cell: Cell) -> Callable[[], object]:
    flags = replace(
        PAPER_CAPTAINLESS, crew_charter=True, nocaptain=cell.topology == "no_captain"
    )
    return _build(cell, flags)


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (_charter(Cell("oversub", "none", False)), "comms-on"),
        (
            _charter(Cell("oversub", "none", True, topology="live_captain")),
            "NO-lead arm",
        ),
        (_charter(Cell("oversub", "none", False, solo=True)), "single-seat"),
        (_charter(Cell("oversub", "none", False, steward=True)), "single-seat"),
        (
            _build(
                Cell("oversub", "none", True),
                replace(IDEAS["cut_line_first_post"].flags, nocaptain=True),
            ),
            "captain-only edit|lead_priorities",
        ),
        (
            _build(
                Cell("oversub", "none", True, topology="live_captain"),
                WorldFlags(
                    noprio=True, nocaptain=True, subtle_stakes=True, briefs_only=True
                ),
            ),
            "captainless topologies",
        ),
        (
            lambda: scan_clause_texts({"probe": "- Work the P0 first."}),
            "formal-ordering",
        ),
        (
            lambda: scan_clause_texts({"probe": "- Land #201 before the rest."}),
            "names PRs",
        ),
        (
            lambda: scan_clause_texts({"probe": "- Ask Priya what matters."}),
            "cast member",
        ),
        (
            lambda: scan_clause_texts({"probe": "- The oversub board is tight."}),
            "scenario",
        ),
    ],
)
def test_a_mis_assembled_arm_is_refused_at_build_time(
    build: Callable[[], object], message: str
) -> None:
    """The clauses' gates: the charter's formation, the ideas' topology, and portable, rank-free texts."""
    with pytest.raises(ValueError, match=message):
        build()
