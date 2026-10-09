"""The long-limit retry: an episode that unwinds under its instrument's first time limit is replayed once.

The API key's limits-off reruns banked their leftover nights in a second pass under a longer, identity-bearing
sample limit (28,800 s), as the clinic coordinators' re-fly did (28,800 s). The harness replays such an episode
from scratch in the same run dir; the recorded configuration names both limits, and `DONE.json` says which one
the episode banked under. `_play` is stubbed: no model, no world.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from api_key import cells as api_cells
from clinic import cells as clinic_cells

from _harness import sim
from _harness.runner import RunConfig

KEYS = sim.SimKeys("fake-not-used", "fake-not-used")


def _config(tmp_path: Path, formation: str = "team", **kw: Any) -> RunConfig:
    return RunConfig(
        eval="api_key",
        scenario="stakes_100",
        formation=formation,
        model="claude-sonnet-5",
        provider="anthropic",
        runs_root=tmp_path,
        harness="sim",
        fake_model=True,
        **kw,
    )


def _stub(
    monkeypatch: pytest.MonkeyPatch,
    outcomes: list[str],
    records: list[dict[str, Any]] | None = None,
) -> list[int]:
    """Stub `_play`: each call pops an outcome (`unwound`, `capped` or `ok`); returns the limits it saw.

    `records` collects the configuration record each attempt would write (`world/config.json`).
    """
    limits: list[int] = []

    def play(
        config: RunConfig,
        recipe: sim.SimRecipe,
        epoch: int,
        keys: sim.SimKeys,
        run_dir: Path,
        expected: dict[str, Any],
        max_turns: int,
        max_ahead: int,
        time_limit: int,
    ) -> tuple[dict[str, Any], Path, float]:
        limits.append(time_limit)
        if records is not None:
            records.append(expected)
        (run_dir / "world").mkdir(parents=True, exist_ok=True)
        outcome = outcomes.pop(0)
        if outcome == "unwound":
            raise sim.SimEpisodeIncomplete("unwound", unwound=True)
        if outcome == "capped":
            raise sim.SimEpisodeIncomplete("step-capped")
        return {"clock": 990, "driver_ended": "world horizon reached"}, run_dir, 1.0

    monkeypatch.setattr(sim, "_play", play)
    return limits


def test_an_unwound_night_is_replayed_once_under_the_long_limit_and_only_an_unwound_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # limits_off on a four-seat stakes night: 7200 s, then the 28800 s long-limit pass
    recipe = api_cells.build_sim_recipe("stakes_100", "team")
    limits = _stub(monkeypatch, ["unwound", "ok"])
    record = sim.run_episode(_config(tmp_path / "a"), recipe, 1, KEYS)
    assert limits == [7200, 28800]
    assert record["attempts"] == 2 and record["time_limit_banked_s"] == 28800
    assert record["instrument"] == "limits_off"
    # bounded: a second unwind is not replayed again
    limits = _stub(monkeypatch, ["unwound", "unwound"])
    with pytest.raises(sim.SimEpisodeIncomplete):
        sim.run_episode(_config(tmp_path / "b"), recipe, 1, KEYS)
    assert limits == [7200, 28800]
    # a step-capped night is not a time-limit problem: no replay
    limits = _stub(monkeypatch, ["capped"])
    with pytest.raises(sim.SimEpisodeIncomplete, match="step-capped"):
        sim.run_episode(_config(tmp_path / "c"), recipe, 1, KEYS)
    assert limits == [7200]


def test_a_clinic_coordinator_morning_is_replayed_at_the_coordinators_re_fly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The clinic hero re-flies at 8 h (w5top_g_opus_lo_stew): gliclazide_fluconazole_split banks only there."""
    recipe = clinic_cells.build_sim_recipe(
        "gliclazide_fluconazole_split", "coordinator"
    )
    assert recipe.instrument == "hero"
    config = RunConfig(
        eval="clinic",
        scenario="gliclazide_fluconazole_split",
        formation="coordinator",
        model="claude-opus-5",
        provider="anthropic",
        runs_root=tmp_path / "a",
        harness="sim",
        fake_model=True,
    )
    records: list[dict[str, Any]] = []
    limits = _stub(monkeypatch, ["unwound", "ok"], records)
    record = sim.run_episode(config, recipe, 1, KEYS)
    assert limits == [7200, 28800]
    assert record["attempts"] == 2 and record["time_limit_banked_s"] == 28800
    written = records[-1]
    assert (written["time_limit_s"], written["retry_time_limit_s"]) == (7200, 28800)
    assert written["on_paper_instrument"] is True and written["off_paper"] == []
    assert json.loads(
        (sim.run_dir_for(config, recipe, 1) / "DONE.json").read_text()
    ) == {**record}


def test_no_retry_on_the_api_key_hero_the_lead_ladder_or_the_clinic_teams(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # the API key hero instrument (the paper's original runs) never re-flew
    hero = api_cells.build_sim_recipe("stakes_100", "coordinator")
    limits = _stub(monkeypatch, ["unwound"])
    with pytest.raises(sim.SimEpisodeIncomplete):
        sim.run_episode(_config(tmp_path / "a", formation="coordinator"), hero, 1, KEYS)
    assert limits == [7200]
    # the lead ladder banked every night under its 4 / 6 / 8 h limit
    lead = api_cells.build_sim_recipe("stakes_100", "team", mitigation="lead_value")
    limits = _stub(monkeypatch, ["unwound"])
    with pytest.raises(sim.SimEpisodeIncomplete):
        sim.run_episode(_config(tmp_path / "b", mitigation="lead_value"), lead, 1, KEYS)
    assert limits == [14_400]
    # the clinic's standard instrument (the peer-to-peer and silent teams, s1-s3) is one 16 h pass
    team = clinic_cells.build_sim_recipe("warfarin_inr_plain", "team")
    limits = _stub(monkeypatch, ["unwound"])
    with pytest.raises(sim.SimEpisodeIncomplete):
        sim.run_episode(
            replace(
                _config(tmp_path / "c"), eval="clinic", scenario="warfarin_inr_plain"
            ),
            team,
            1,
            KEYS,
        )
    assert limits == [57_600]


QUARANTINED = (
    "fleet quarantined — every agent at 3+ consecutive failed resumes (last target error: Target generate "
    "failed: AuthenticationError: Error code: 401 - {'type': 'error', 'error': {'type': "
    "'authentication_error', 'message': 'API key is invalid.'}})"
)


def test_a_fleet_quarantined_night_is_not_banked_even_at_the_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A quarantine at clock >= the deadline (a key rejected mid-night) is no finished night: no DONE.json.

    The paper scores only worlds whose driver ended at the horizon; the run dir stays unbanked, so rerunning
    the command redoes it.
    """
    recipe = api_cells.build_sim_recipe("stakes_100", "team")

    def play(
        config: RunConfig,
        recipe: sim.SimRecipe,
        epoch: int,
        keys: sim.SimKeys,
        run_dir: Path,
        expected: dict[str, Any],
        max_turns: int,
        max_ahead: int,
        time_limit: int,
    ) -> tuple[dict[str, Any], Path, float]:
        (run_dir / "world").mkdir(parents=True, exist_ok=True)
        world = {"clock": 930, "deadline_min": 900, "driver_ended": QUARANTINED}
        return world, run_dir, 1.0

    monkeypatch.setattr(sim, "_play", play)
    config = _config(tmp_path)
    with pytest.raises(
        sim.SimEpisodeIncomplete, match="without reaching the world's horizon"
    ):
        sim.run_episode(config, recipe, 2, KEYS)
    assert not (sim.run_dir_for(config, recipe, 2) / "DONE.json").exists()
    # a horizon end with an annotated remainder banks
    sim.require_bankable(
        {
            "driver_ended": "world horizon reached — undelivered content remained (S: staged)"
        },
        tmp_path,
        800,
        7200,
    )
    with pytest.raises(sim.SimEpisodeIncomplete, match="step cap"):
        sim.require_bankable(
            {"driver_ended": "step cap reached", "driver_step_capped": True},
            tmp_path,
            800,
            7200,
        )
