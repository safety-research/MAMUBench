"""The `--harness sim` recipes ARE the paper drivers' recipes, checked spec-for-spec.

These pin the HERO instrument (the drivers as flown: burst 6, the derived balance gate, every scheduler
knob unset; each formation's spec on it through `cells.instrument_recipe`, the builder under every paper
cell); the teams' knob sets (the API key's `limits_off`, the clinic's `standard`), and which one each paper cell
plays, are pinned against the paper's launch records in `test_sim_instruments.py`. The spec itself is instrument-independent.

`eval/api_key/cells.py` and `eval/clinic/cells.py` restate how the paper's drivers (the api_key single-user and
16-user drivers, the clinic driver) built their cells. `fixtures/pinned_recipes.json` holds what those drivers
built under the paper's env (the spec digest per cell, `api_key.tests.test_hero_parity._digest`,
and their house-role and scheduler dials); these tests compare the release's recipes with it, so the two can
never drift apart silently.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from _multiagent_pi.audit import (
    _max_ahead,  # pyright: ignore[reportPrivateUsage]
)
from api_key import cells as api_cells
from api_key.environment.resources import SCENARIOS as TC_KNOBS
from api_key.environment.resources import recommended_max_turns
from api_key.scenarios.prompts import TokenClusterScenarioSpec, build_topology_spec
from api_key.scenarios.roster import stakes_n16_roster
from api_key.tests.test_hero_parity import (
    _digest,  # pyright: ignore[reportPrivateUsage]
)
from clinic import cells as clinic_cells
from clinic.scenarios.prompts import ClinicScenarioSpec

from _harness.sim import max_ahead_of_record

PINNED: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "pinned_recipes.json").read_text()
)


def test_max_ahead_formula_is_the_drivers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAX_AHEAD", raising=False)
    for max_turns, n in (
        (300, 1),
        (300, 4),
        (300, 17),
        (300, 52),
        (800, 4),
        (1000, 8),
        (1400, 16),
        (900, 17),
    ):
        assert max_ahead_of_record(max_turns, n) == _max_ahead(max_turns, n)
    # The paper's values: single seats and the clusters sit at the cap, the clinic floors at the floor.
    assert max_ahead_of_record(800, 4) == 20
    assert max_ahead_of_record(300, 1) == 20
    assert max_ahead_of_record(300, 17) == 8
    assert max_ahead_of_record(300, 52) == 8


@pytest.mark.parametrize(
    "scenario_id", ["stakes_100", "stakes_n8_240", "peq_brb_n4_105", "peq_pyr_n8_211"]
)
def test_api_key_recipe_matches_tc_single_user_driver(scenario_id: str) -> None:
    driver = PINNED["api_key_driver"]
    for formation in ("coordinator", "team", "team_silent"):
        recipe = api_cells.instrument_recipe(
            scenario_id, "hero", api_cells.sim_spec(scenario_id, formation)
        )
        assert _digest(recipe.spec) == PINNED["api_key"][f"{scenario_id}/{formation}"]
        assert recipe.spec == api_cells.build_sim_recipe(scenario_id, formation).spec
        assert recipe.spec.name.endswith("__notax")
        assert recipe.max_turns == recommended_max_turns(
            cast(TokenClusterScenarioSpec, recipe.spec).runtime_n_seats,
            clock=api_cells.CLOCK_DIAL,
        )
        assert recipe.auditor == driver["AUDITOR_KIND"] == "escalation"
        assert recipe.auditor_model == driver["AUDITOR"]
        assert recipe.judge_model == driver["JUDGE"]
        assert recipe.burst == 6 and recipe.world_tool_label == "labctl"
        assert recipe.framing == "live" and recipe.spec.interaction == "interactive"


def test_api_key_n16_recipe_matches_tc_stakes_n16_driver() -> None:
    """The n16 driver builds its cells with the explicit n16 roster and no clock stamp on the name."""
    roster = stakes_n16_roster()
    for topology, comms, formation in (
        ("steward", True, "coordinator"),
        ("mesh", True, "team"),
        ("mesh", False, "team_silent"),
    ):
        recipe = api_cells.instrument_recipe(
            "stakes_n16_480", "hero", api_cells.sim_spec("stakes_n16_480", formation)
        )
        expected = build_topology_spec(
            knobs=TC_KNOBS["stakes_n16_480"],
            topology=topology,  # type: ignore[arg-type]
            arm="none",
            roster=roster,
            comms=comms,
        ).spec
        assert recipe.spec == expected
        assert "__notax" not in recipe.spec.name
        assert recipe.max_turns == 1400 and recipe.time_limit_s == 14400


@pytest.mark.parametrize(
    "board_id", ["warfarin_inr_plain", "warfarin_inr_split", "amiodarone_qt_split"]
)
def test_clinic_recipe_matches_the_papers_driver(board_id: str) -> None:
    driver = PINNED["clinic_driver"]
    for formation in ("coordinator", "team", "team_silent"):
        recipe = clinic_cells.instrument_recipe(
            board_id, "hero", clinic_cells.sim_spec(board_id, formation)
        )
        assert _digest(recipe.spec) == PINNED["clinic"][f"{board_id}/{formation}"]
        assert recipe.spec == clinic_cells.build_sim_recipe(board_id, formation).spec
        assert recipe.spec.interaction == "scripted" and recipe.framing == "console"
        assert recipe.max_turns == driver["MAX_TURNS"] == 300
        assert recipe.burst == driver["BURST"] == 6
        assert recipe.auditor == "none" and recipe.world_tool_label == "clinic"
        assert recipe.dials == {"DEBRIEF_MIN": driver["DEBRIEF_MIN"]}
        assert recipe.knobs == {} and recipe.max_ahead is None  # hero: every knob unset
        assert recipe.auditor_model == driver["AUDITOR"]
        assert recipe.judge_model == driver["JUDGE"]
        # The driver's own knob builder leaves the horizon at the dataclass default: the four
        # 300-minute pairs flew (and are referenced at) a 240-minute shift on this instrument.
        assert isinstance(recipe.spec, ClinicScenarioSpec)
        assert recipe.spec.runtime_knobs.horizon == "240"


def test_clinic_sim_horizon_differs_from_the_pi_cell_on_300_minute_boards() -> None:
    """Documented instrument divergence: the pi cell threads the declared 300, the sim recipe flies 240."""
    sim = clinic_cells.build_sim_recipe("amiodarone_qt_split", "coordinator")
    pi = clinic_cells.build_cell("amiodarone_qt_split", "coordinator", 1)
    assert isinstance(sim.spec, ClinicScenarioSpec)
    assert sim.spec.runtime_knobs.horizon == "240"
    assert pi.window_min == 300
