"""Every simulated-harness instrument IS the paper runs' knob set, pinned against their launch records.

`fixtures/knobs_of_record.json` copies the paper launchers' identity-bearing env verbatim (the clinic teams'
`KNOBS_OF_RECORD`, the hero coordinator block, the api_key rerun's `cell_env` and time limits). These tests
render each recipe under the launchers' knob names (`sim.harness_env`) and compare knob for knob, so an
instrument can never drift from the record silently. They also pin which instrument each paper cell plays (its
formation's, the lead arms' ladder, the clinic arms') and the Modal timeout each needs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from api_key import cells as api_cells
from api_key import mitigations as api_mitigations
from api_key import scenarios as api_scenarios
from clinic import cells as clinic_cells
from clinic.scenarios import FRAMING

from _harness import sim

RECORD: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "knobs_of_record.json").read_text()
)
#: Launcher knobs the release expresses structurally rather than as env: the no-LLM scripted driver
#: (`auditor="none"`, no live judge) and the one framing every board declares.
STRUCTURAL = ("AUDITOR", "JUDGE", "DRIVER", "FRAMINGS")


def _clinic_env(formation: str, board: str = "warfarin_inr_split") -> dict[str, str]:
    recipe = clinic_cells.build_sim_recipe(board, formation)
    assert recipe.instrument == "standard"
    max_ahead = (
        recipe.max_ahead
        if recipe.max_ahead is not None
        else sim.max_ahead_of_record(recipe.max_turns, len(recipe.spec.agents))
    )
    return sim.harness_env(
        recipe, recipe.max_turns, max_ahead, recipe.time_limit_s, "0"
    )


def _structural_ok(recipe: sim.SimRecipe, record: dict[str, str]) -> None:
    assert record.get("DRIVER") == "mechanical" and recipe.auditor == "none"
    assert record.get("FRAMINGS") == FRAMING == "f_all_closed"
    assert record.get("AUDITOR", "") == "" and record.get("JUDGE", "") == ""


@pytest.mark.parametrize("formation", ["team", "team_silent"])
def test_clinic_standard_instrument_equals_the_knobs_of_record(
    formation: str,
) -> None:
    record: dict[str, str] = RECORD["clinic"]["standard"]
    env = _clinic_env(formation)
    expected = {k: v for k, v in record.items() if k not in STRUCTURAL}
    assert env == expected
    _structural_ok(
        clinic_cells.build_sim_recipe("warfarin_inr_split", formation), record
    )


def test_clinic_hero_is_the_coordinator_block_with_no_team_scheduler_knob() -> None:
    record: dict[str, str] = RECORD["clinic"]["hero"]
    recipe = clinic_cells.build_sim_recipe("amiodarone_qt_plain", "coordinator")
    assert recipe.instrument == "hero"
    env = sim.harness_env(
        recipe,
        recipe.max_turns,
        sim.max_ahead_of_record(recipe.max_turns, len(recipe.spec.agents)),
        recipe.time_limit_s,
        "0",
    )
    for key, value in record.items():
        if key not in STRUCTURAL:
            assert env[key] == value, key
    _structural_ok(recipe, record)
    # No MAX_AHEAD override (the derived value applies, exactly as the hero lanes ran), and none of the
    # knobs the paper's launchers refused in a coordinator container is set.
    assert recipe.max_ahead is None and recipe.knobs == {}
    forbidden = set(RECORD["clinic"]["coord_forbidden_env"]) - {"MAX_AHEAD"}
    assert not forbidden & set(env)
    assert (
        env["MAX_AHEAD"] == "20"
    )  # one desk at 300 steps: the derived value, pinned explicitly
    # the first pass is the paper's 7,200 s; a morning that did not finish is replayed once at the
    # coordinators' re-fly limit (the paper's 8 h second pass)
    assert recipe.time_limit_s == int(record["PETRI_SAMPLE_TIME_LIMIT"]) == 7200
    assert (
        recipe.retry_time_limit_s
        == clinic_cells.HERO_LONG_LIMIT_S
        == RECORD["clinic"]["hero_long_limit"]
    )


def test_clinic_hero_long_limit_changes_no_other_instrument_or_eval() -> None:
    """Only the clinic's hero re-flies at 8 h: the clinic's standard instrument and the API key hero are as flown."""
    assert set(clinic_cells.SIM_INSTRUMENTS) == {"hero", "standard"}
    assert clinic_cells.SIM_INSTRUMENTS["standard"].retry_time_limit_s is None
    for scenario_id in ("stakes_100", "stakes_n16_480", "peq_cls_n8_143"):
        for formation in ("coordinator", "solo"):
            recipe = api_cells.build_sim_recipe(scenario_id, formation)
            assert recipe.instrument == "hero" and recipe.retry_time_limit_s is None
    for arm in ("s1", "s2", "s3"):
        recipe = clinic_cells.build_sim_recipe(
            "warfarin_inr_split", "team", mitigation=arm
        )
        assert recipe.instrument == "standard" and recipe.retry_time_limit_s is None


def test_clinic_thinking_of_record_per_provider() -> None:
    by_provider = {
        model.split("/", 1)[0]: thinking
        for model, thinking in RECORD["clinic"]["target_thinking"].items()
    }
    assert clinic_cells.THINKING_OF_RECORD == by_provider


def _group(scenario_id: str) -> str:
    if scenario_id in ("stakes_80", "stakes_100", "stakes_130"):
        return "doses"
    if scenario_id == "stakes_n8_240":
        return "n8"
    if scenario_id == "stakes_n16_480":
        return "n16"
    return "peq"


@pytest.mark.parametrize("scenario_id", sorted(api_scenarios.SCENARIOS))
def test_api_key_limits_off_is_the_rerun_cell_env(scenario_id: str) -> None:
    record: dict[str, str] = RECORD["api_key"]["limits_off"]
    recipe = api_cells.build_sim_recipe(scenario_id, "team")
    assert recipe.instrument == "limits_off"
    assert str(recipe.burst) == record["BURST"]
    assert str(recipe.max_ahead) == record["MAX_AHEAD"]
    assert str(recipe.generate_timeout_s) == record["PETRI_GENERATE_TIMEOUT"]
    assert recipe.dials["TOKEN_CLUSTER_EXEC"] == record["TOKEN_CLUSTER_EXEC"]
    assert recipe.auditor == record["AUDITOR_MODE"]
    assert recipe.auditor_model == record["AUDITOR"]
    assert recipe.judge_model == record["JUDGE"]
    assert recipe.knobs == {}  # the api_key rerun set no other knob
    assert (
        recipe.time_limit_s
        == RECORD["api_key"]["time_limit_by_group"][_group(scenario_id)]
    )
    assert recipe.retry_time_limit_s == RECORD["api_key"]["long_limit"]


@pytest.mark.parametrize(
    "scenario_id", ["stakes_100", "stakes_n16_480", "peq_cls_n8_143"]
)
def test_api_key_hero_keeps_the_capped_scheduler(scenario_id: str) -> None:
    recipe = api_cells.build_sim_recipe(scenario_id, "coordinator")
    assert recipe.instrument == "hero"
    assert str(recipe.burst) == RECORD["api_key"]["hero"]["BURST"]
    assert recipe.max_ahead is None and recipe.retry_time_limit_s is None
    assert sim.max_ahead_of_record(recipe.max_turns, len(recipe.spec.agents)) == 20
    assert (
        recipe.time_limit_s
        == RECORD["api_key"]["time_limit_by_group"][_group(scenario_id)]
    )


def test_api_key_reasoning_of_record_is_the_lanes_table() -> None:
    by_provider = {
        provider: effort for _, provider, effort in RECORD["api_key"]["lanes"].values()
    }
    assert api_cells.REASONING_OF_RECORD == by_provider


def test_api_key_ladder_parameters_are_the_ladders() -> None:
    ladder = RECORD["api_key"]["ladder"]
    assert api_mitigations.LADDER_INSTRUMENT == "limits_off"
    assert {
        str(k): v for k, v in api_mitigations.LADDER_TIME_LIMIT_S.items()
    } == ladder["TIME_LIMIT_S"]
    assert (
        str(api_mitigations.LADDER_GENERATE_TIMEOUT_S)
        == ladder["PETRI_GENERATE_TIMEOUT"]
    )
    recipe = api_cells.instrument_recipe(
        "stakes_n8_240",
        api_mitigations.LADDER_INSTRUMENT,
        api_cells.sim_spec("stakes_n8_240", "team"),
        time_limit_s=api_mitigations.LADDER_TIME_LIMIT_S[8],
        generate_timeout_s=api_mitigations.LADDER_GENERATE_TIMEOUT_S,
        max_turns=1234,
    )
    assert (recipe.burst, recipe.max_ahead) == (1_000_000, 1_000_000)
    assert (recipe.time_limit_s, recipe.generate_timeout_s, recipe.max_turns) == (
        21_600,
        3600,
        1234,
    )
    # the lead arms play exactly that ladder: limits off, the cast's limit, the 1 h generate timeout, n + 1 steps
    for arm in ("lead_value", "lead_full_stack"):
        lead = api_cells.build_sim_recipe("stakes_n8_240", "team", mitigation=arm)
        assert (lead.instrument, lead.burst, lead.max_ahead) == (
            "limits_off",
            1_000_000,
            1_000_000,
        )
        assert (lead.time_limit_s, lead.generate_timeout_s) == (21_600, 3600)
        assert lead.max_turns == 1050 and lead.retry_time_limit_s is None


def test_paper_instrument_per_formation() -> None:
    assert api_cells.PAPER_INSTRUMENT == {
        "coordinator": "hero",
        "team": "limits_off",
        "team_silent": "limits_off",
        "solo": "hero",
    }
    assert clinic_cells.PAPER_INSTRUMENT == {
        "coordinator": "hero",
        "team": "standard",
        "team_silent": "standard",
    }
    assert clinic_cells.MITIGATION_INSTRUMENT == "standard"
    for formation, instrument in (("coordinator", "hero"), ("team", "limits_off")):
        assert (
            api_cells.build_sim_recipe("stakes_100", formation).instrument == instrument
        )
    for formation, instrument in clinic_cells.PAPER_INSTRUMENT.items():
        recipe = clinic_cells.build_sim_recipe("warfarin_inr_plain", formation)
        assert recipe.instrument == instrument
    # the peer-to-peer and the silent team share one scheduler: one 16 h pass at 5,000 steps
    team = clinic_cells.build_sim_recipe("warfarin_inr_plain", "team")
    silent = clinic_cells.build_sim_recipe("warfarin_inr_plain", "team_silent")
    assert team.mitigation is None
    assert team.knobs == silent.knobs and team.max_turns == silent.max_turns == 5000
    assert (team.time_limit_s, team.retry_time_limit_s) == (57600, None)


def test_unknown_instruments_are_refused() -> None:
    with pytest.raises(ValueError, match="standard"):
        api_cells.instrument_recipe(
            "stakes_100", "standard", api_cells.sim_spec("stakes_100", "team")
        )
    with pytest.raises(ValueError, match="limits_off"):
        clinic_cells.instrument_recipe(
            "warfarin_inr_plain",
            "limits_off",
            clinic_cells.sim_spec("warfarin_inr_plain", "team"),
        )
    with pytest.raises(ValueError, match="nope"):
        clinic_cells.instrument_recipe(
            "warfarin_inr_plain",
            "nope",
            clinic_cells.sim_spec("warfarin_inr_plain", "team"),
        )


def test_episode_budgets_and_modal_timeouts_fit_each_instrument() -> None:
    margin = sim.EPISODE_MARGIN_S
    hero = api_cells.build_sim_recipe("stakes_100", "coordinator")
    assert sim.episode_wall_budget_s(hero) == 7200 + margin
    team = api_cells.build_sim_recipe("stakes_100", "team")
    assert sim.episode_wall_budget_s(team) == 7200 + 28800 + margin
    assert (
        sim.modal_timeout_needed_s(
            "api_key", [("stakes_n16_480", "team"), ("stakes_100", "coordinator")]
        )
        == 14400 + 28800 + margin
    )
    assert (
        sim.modal_timeout_needed_s("clinic", [("warfarin_inr_plain", "team_silent")])
        == 57600 + margin
    )
    # the clinic hero: 2 h, then the coordinators' 8 h re-fly
    assert (
        sim.modal_timeout_needed_s(
            "clinic", [("gliclazide_fluconazole_split", "coordinator")]
        )
        == 7200 + 28800 + margin
    )
    # the clinic team: one 16 h pass, no retry
    assert (
        sim.modal_timeout_needed_s("clinic", [("warfarin_inr_plain", "team")])
        == 57600 + margin
    )
    # every instrument's worst case fits Modal's 24 h function ceiling
    spec = clinic_cells.sim_spec("phenytoin_toxicity_split", "team")
    assert all(
        sim.episode_wall_budget_s(
            clinic_cells.instrument_recipe("phenytoin_toxicity_split", i, spec)
        )
        <= 24 * 3600
        for i in clinic_cells.SIM_INSTRUMENTS
    )
