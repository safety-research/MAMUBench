"""The mitigation packages, the env hooks and run-dir naming stability.

Every registry starts with the control arm `none`, and every other arm has its paper runs (`RUNS`). These tests pin
the contract the arms plug into: listing, validation, the hook dispatch in `cells` / the runners, and that the
control arm changes no run-dir name or record (the reports' per-arm keying is `test_mitigation_reports.py`).
"""

from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from _harness import runner, sim
from _mitigations import ALL, NONE, control, listing, validate

from tests.conftest import ENVS, FAKE
from tests.conftest import fake_arm_record as fake_arm


def registry(env: str) -> ModuleType:
    return importlib.import_module(f"{env}.mitigations")


def env_formations(env: str) -> tuple[str, ...]:
    if env == "personal_assistant":
        from personal_assistant import registry as pa_registry

        return tuple(pa_registry.FORMATIONS)
    return tuple(importlib.import_module(f"{env}.scenarios").FORMATIONS)


# ── the registries ────────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("env", ENVS)
def test_every_registry_starts_with_the_control_arm_and_every_arm_has_its_paper_runs(
    env: str,
) -> None:
    package = registry(env)
    arms = package.MITIGATIONS
    assert next(iter(arms)) == NONE
    control_arm = arms[NONE]
    assert control_arm.research_id is None
    assert control_arm.formations == env_formations(env)
    expected_harnesses = ("pi", "sim") if env in ("api_key", "clinic") else ("pi",)
    assert control_arm.harnesses == expected_harnesses
    assert all(arm.name == name for name, arm in arms.items())
    assert set(package.RUNS) == set(arms) - {NONE}
    for name, cells in package.RUNS.items():
        assert set(cells.formations) <= set(arms[name].formations)


@pytest.mark.parametrize("env", ENVS)
def test_runner_lists_mitigations_without_a_scenario(
    env: str, capsys: pytest.CaptureFixture[str]
) -> None:
    run_mod = importlib.import_module(f"{env}.run")
    assert run_mod.main(["--list-mitigations"]) == 0
    out = capsys.readouterr().out
    assert out.startswith(f"{env} mitigations (") and "control (no mitigation)" in out
    for name in registry(env).MITIGATIONS:
        assert f"  {name} " in out


def test_mitigation_record_validates_its_fields() -> None:
    for bad in ("Bad-Name", ALL):
        with pytest.raises(ValueError, match="lowercase"):
            replace(fake_arm(), name=bad)
    with pytest.raises(ValueError, match="no formation"):
        replace(fake_arm(), formations=())


def test_validate_names_the_registry_the_formation_and_the_harness() -> None:
    arms = {NONE: control(("coordinator", "team"), ("pi", "sim")), FAKE: fake_arm()}
    assert validate(arms, NONE, "env", formations=["coordinator", "team"]).name == NONE
    with pytest.raises(
        ValueError, match=r"unknown env mitigation 'x'; available: none, fake_arm"
    ):
        validate(arms, "x", "env")
    with pytest.raises(ValueError, match="applies to formation.*team, not coordinator"):
        validate(arms, FAKE, "env", formations=["coordinator"])
    sim_only = {FAKE: fake_arm(harnesses=("sim",))}
    with pytest.raises(ValueError, match="implemented for the sim harness, not pi"):
        validate(sim_only, FAKE, "env", harness="pi")
    assert "fake arm (tests)" in listing(arms, "env")
    assert "research_id" not in listing(
        arms, "env"
    )  # a registry id, not a label to list


# ── the hooks: an arm reaches its env's builder ───────────────────────────────────────────────────


def test_api_key_and_clinic_cells_dispatch_an_arm_to_their_hooks() -> None:
    from api_key import cells as api_cells
    from clinic import cells as clinic_cells

    assert (
        api_cells.build_sim_recipe(
            "stakes_100", "team", mitigation="lead_value"
        ).mitigation
        == "lead_value"
    )
    assert (
        clinic_cells.build_sim_recipe(
            "warfarin_inr_split", "team", mitigation="s3"
        ).mitigation
        == "s3"
    )
    # the arms ran on the simulated harness only; the formation rule is enforced before the hook
    with pytest.raises(ValueError, match="sim harness, not pi"):
        api_cells.build_cell("stakes_100", "team", 1, "lead_value")
    with pytest.raises(ValueError, match="sim harness, not pi"):
        clinic_cells.build_cell("warfarin_inr_split", "team", 1, "s3")
    with pytest.raises(ValueError, match="not coordinator"):
        api_cells.build_sim_recipe("stakes_100", "coordinator", mitigation="lead_value")
    # an unknown arm never reaches a hook
    with pytest.raises(ValueError, match="unknown api_key mitigation"):
        api_cells.build_sim_recipe("stakes_100", "team", mitigation="missing")
    # the control arm is the recipe of record, unchanged
    control_recipe = api_cells.build_sim_recipe("stakes_100", "team", mitigation=NONE)
    assert control_recipe == api_cells.build_sim_recipe("stakes_100", "team")
    assert control_recipe.mitigation is None


def test_personal_assistant_and_merge_queue_hooks() -> None:
    from merge_queue import mitigations as mq_mitigations
    from personal_assistant import registry as pa_registry
    from personal_assistant import run as pa_run

    scenario = pa_registry.scenario("kestrel_quiz_booth")
    control_manifest = pa_run.formation_manifest(scenario, "team")
    assert control_manifest == pa_run.formation_manifest(scenario, "team", NONE)
    # the guard changes no tool; the full stack adds the row-ack tool
    assert pa_run.formation_manifest(scenario, "team", "guard") == control_manifest
    assert "dd_row_ack" in {
        str(t["name"])
        for t in pa_run.formation_manifest(scenario, "team", "full_stack")
    }
    with pytest.raises(ValueError, match="not coordinator"):
        mq_mitigations.apply_to_episode("charter", "coordinator", None, None, epoch=1)  # type: ignore[arg-type]


# ── run-dir naming: stable for the control arm, stamped for an arm ────────────────────────────────


def _config(**fields: Any) -> runner.RunConfig:
    base: dict[str, Any] = {
        "eval": "api_key",
        "scenario": "stakes_100",
        "formation": "team",
        "model": "claude-sonnet-5",
        "provider": "anthropic",
        "runs_root": Path("/runs"),
    }
    return runner.RunConfig(**{**base, **fields})


def test_pi_and_sim_run_dirs_are_unchanged_for_the_control_arm() -> None:
    from api_key import cells as api_cells

    cell = api_cells.build_cell("stakes_100", "team", 3)
    recipe = api_cells.build_sim_recipe("stakes_100", "team")
    assert _config().mitigation == NONE
    # the legacy formulas, verbatim
    assert runner.run_dir_for(_config(), cell, 3) == Path(
        f"/runs/{cell.spec.name}__claude-sonnet-5__e3"
    )
    assert runner.run_dir_for(_config(fake_pi=True), cell, 3).name.endswith(
        "__e3__fakepi"
    )
    assert sim.run_dir_for(_config(harness="sim"), recipe, 3) == Path(
        f"/runs/{recipe.spec.name}__claude-sonnet-5__e3__sim"
    )
    # an arm is stamped after the cell, so `<cell>__<model>__e<N>` parsers keep working
    armed = _config(mitigation=FAKE)
    assert runner.run_dir_for(armed, cell, 3).name == (
        f"{cell.spec.name}__mit-{FAKE}__claude-sonnet-5__e3"
    )
    assert sim.run_dir_for(replace(armed, fake_model=True), recipe, 3).name == (
        f"{recipe.spec.name}__mit-{FAKE}__claude-sonnet-5__e3__sim__fakemodel"
    )


def test_sim_refuses_a_recipe_of_another_arm() -> None:
    from api_key import cells as api_cells

    recipe = api_cells.build_sim_recipe("stakes_100", "team")
    sim.check_mitigation(_config(harness="sim"), recipe)
    sim.check_mitigation(
        _config(harness="sim", mitigation=FAKE), replace(recipe, mitigation=FAKE)
    )
    with pytest.raises(ValueError, match="plays mitigation 'none'"):
        sim.check_mitigation(_config(harness="sim", mitigation=FAKE), recipe)
    with pytest.raises(ValueError, match=f"plays mitigation '{FAKE}'"):
        sim.check_mitigation(_config(harness="sim"), replace(recipe, mitigation=FAKE))


def test_modal_timeout_follows_each_cells_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    from api_key import cells as api_cells
    from api_key import mitigations as api_mitigations

    monkeypatch.setitem(api_mitigations.MITIGATIONS, FAKE, fake_arm())

    def long_arm(scenario: str, formation: str, mitigation: str) -> sim.SimRecipe:
        recipe = api_cells.instrument_recipe(
            scenario,
            api_mitigations.LADDER_INSTRUMENT,
            api_cells.sim_spec(scenario, formation),
            time_limit_s=99_000,
        )
        return replace(recipe, mitigation=mitigation, retry_time_limit_s=None)

    monkeypatch.setattr(api_mitigations, "build_sim_recipe", long_arm)
    control_needed = sim.modal_timeout_needed_s("api_key", [("stakes_100", "team")])
    assert control_needed == sim.modal_timeout_needed_s(
        "api_key", [("stakes_100", "team", NONE)]
    )
    assert (
        sim.modal_timeout_needed_s(
            "api_key", [("stakes_100", "team"), ("stakes_100", "team", FAKE)]
        )
        == 99_000 + sim.EPISODE_MARGIN_S
    )


def test_personal_assistant_wave_names_and_manifests() -> None:
    from personal_assistant import registry as pa_registry
    from personal_assistant import run as pa_run

    assert pa_run.wave_name("kestrel_quiz_booth", "claude-sonnet-5") == (
        "kestrel_quiz_booth__claude-sonnet-5"
    )
    assert pa_run.wave_name("kestrel_quiz_booth", "claude-sonnet-5", FAKE) == (
        f"kestrel_quiz_booth__claude-sonnet-5__mit-{FAKE}"
    )
    scenario = pa_registry.scenario("kestrel_quiz_booth")
    config = pa_run.RunConfig(
        model="claude-sonnet-5",
        provider="anthropic",
        thinking="off",
        isolation="none",
        fake_pi=True,
        turn_timeout=1800.0,
        hard_cap=2700.0,
        revision="test",
        pi_version="fake",
    )
    record = pa_run.wave_config(scenario, ("coordinator", "team"), config)
    assert "mitigation" not in record
    assert record == pa_run.wave_config(scenario, ("coordinator", "team"), config, NONE)
