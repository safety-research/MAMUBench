"""The eval's surface is the environment's: 25 scenarios on three formations, the providers, the pinned manifests."""

from __future__ import annotations

import pytest

from personal_assistant import registry, run
from personal_assistant.outcomes import formation_of_cell

#: The food tool-surface digests every food wave of record carries in its `wave_config.json`
#: (`manifest_sha256`). A change here means the surface the reference numbers were measured on has moved.
FOOD_MANIFEST_DIGESTS = {
    "team": "9b1b23d895e61a1cd8fbf932db211f398a0ef5d9e014751b9fface93b713be5e",
    "coordinator": "d4cfb93afbb0b61ee17677646353f595623cca14e2ba466eae7c4df5615434e9",
}


def test_the_25_scenarios_of_record_run_all_three_formations() -> None:
    from personal_assistant.environment import food_run, trip_cart
    from personal_assistant.environment.ladder_report import ARMS
    from personal_assistant.environment.worlds import CELLS
    from personal_assistant.scenarios import register_trip_specs

    register_trip_specs()
    assert len(registry.SCENARIOS) == 25
    assert len(registry.HERO_SHORTS) == 16 and len(registry.SAFETY_SHORTS) == 9
    assert set(registry.HERO_SHORTS).isdisjoint(registry.SAFETY_SHORTS)
    assert registry.SAFETY_NON_COMMITTING == {
        "brunch_covers_reply",
        "itinerary_brunch",
        "second_weekend_rally",
        "tote_credit_cover",
    }
    assert all(registry.SCENARIOS[s].safety_critical for s in registry.SAFETY_SHORTS)
    assert not any(registry.SCENARIOS[s].safety_critical for s in registry.HERO_SHORTS)
    assert registry.TOPOLOGY_BY_FORMATION == {
        "coordinator": "steward",
        "team": "mesh",
        "team_silent": "mesh_nc",
    }
    # the environment's own topology -> formation map (`ladder_report.ARMS`)
    assert {
        t: ARMS[t] for t in registry.TOPOLOGY_BY_FORMATION.values()
    } == registry.FORMATION_BY_TOPOLOGY
    for short, row in registry.SCENARIOS.items():
        assert row.formations == registry.FORMATIONS, short
        cells = [row.cell(formation) for formation in registry.FORMATIONS]
        # the cell name encodes the formation (`_mesh_nc` never bins under `_mesh`)
        assert [formation_of_cell(cell) for cell in cells] == list(registry.FORMATIONS)
        if row.substrate == "food":
            assert short in food_run.RUNNABLE_SHORTS and set(cells) <= set(CELLS)
            assert food_run.scenario_deadline_s(short) == 21 * 60.0
        else:
            assert short in trip_cart.TRIP_NC_SHORTS
            assert cells == [
                f"trip_{short}_{t}" for t in ("steward", "mesh", "mesh_nc")
            ]
            assert trip_cart.resolve_trip_spec(short).deadline_minutes == 21
    assert formation_of_cell("conf_kestrel_quiz_booth_mesh__m19") == "team"
    with pytest.raises(ValueError):
        formation_of_cell("conf_x_solo")


def test_models_providers_and_pi_thinking() -> None:
    for model, provider, thinking in (
        ("claude-sonnet-5", "anthropic", "off"),
        ("claude-opus-5", "anthropic", "off"),
        ("gpt-5.6-sol", "openai", "medium"),
        ("gpt-5.6-terra", "openai", "medium"),
    ):
        assert registry.provider_for(model) == provider
        assert registry.resolve_thinking(provider, None) == thinking
    assert registry.model_id("sonnet") == "claude-sonnet-5"
    assert registry.model_id("terra") == "gpt-5.6-terra"
    assert registry.model_id("claude-x-9") == "claude-x-9"
    assert registry.resolve_thinking("openai", "HIGH") == "high"
    for refused in (
        lambda: registry.provider_for("mistral-large"),
        # the environment runtime pins anthropic seats thinking-off
        lambda: registry.resolve_thinking("anthropic", "medium"),
        lambda: registry.resolve_thinking("openai", "sometimes"),
        lambda: registry.scenario("not_a_scenario"),
    ):
        with pytest.raises(SystemExit):
            refused()


def test_food_manifests_are_the_waves_of_record() -> None:
    row = registry.SCENARIOS["kestrel_quiz_booth"]
    for formation, digest in FOOD_MANIFEST_DIGESTS.items():
        assert run.manifest_digest(run.formation_manifest(row, formation)) == digest


def test_scenario_selection_dedupes_in_registry_order() -> None:
    args = run.parse_args(
        [
            "--scenario",
            "kestrel_quiz_booth",
            "watchparty_priority_fee",
            "kestrel_quiz_booth",
        ]
    )
    assert [s.short for s in run.selected_scenarios(args)] == [
        "watchparty_priority_fee",
        "kestrel_quiz_booth",
    ]
    assert len(run.selected_scenarios(run.parse_args(["--all"]))) == 25
    assert len(run.selected_scenarios(run.parse_args(["--safety"]))) == 9
    with pytest.raises(SystemExit):
        run.selected_scenarios(run.parse_args([]))
