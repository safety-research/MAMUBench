"""The paper's world, byte for byte against the authors' research builds (`tests/fixtures/world/`).

- `paper_config_hashes.json`: the canonical-JSON sha256 of 640 `ScenarioConfig`s (every formation and shipped arm
  on 20 seeds of oversub, volunteer_p1, volunteer_p3 and baseline_tight), built with the research code's
  `variants.build_cell` at the version the paper's repair loop and mitigation ladder ran. Each is planned here as
  `_drive.py` plans the episode, whose `config.json` records the same digest (`scenario_sha256`);
- `fixture_manifests.json`: the fixture the research build made per world variant. The world's RELEASING.md is
  in the seed before history, so every commit sha of the manifest pins its text.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

import pytest

from merge_queue import _drive, mitigations
from merge_queue.environment.fixture import build_fixture
from merge_queue.environment.world import ConflictError, World
from merge_queue.scenarios import SCENARIOS, analysis_scenario, formation_of_cell
from merge_queue.scenarios._cells import Cell
from merge_queue.scenarios._context import build_cell
from merge_queue.scenarios._world import (
    PAPER_CAPTAINED,
    PAPER_CAPTAINLESS,
    WorldFlags,
    releasing_md,
)

PINS = Path(__file__).resolve().parent / "fixtures" / "world"
CONFIG_HASHES: dict[str, str] = json.loads(
    (PINS / "paper_config_hashes.json").read_text()
)["hashes"]
#: world variant -> the arm that runs it
ARM_OF_VARIANT = {PAPER_CAPTAINLESS.name: "none"} | {
    spec.variant: name for name, spec in mitigations.ARMS.items()
}


@pytest.mark.parametrize("arm", list(mitigations.MITIGATIONS))
def test_every_planned_episode_is_the_research_build(arm: str) -> None:
    keys = [k for k in CONFIG_HASHES if ARM_OF_VARIANT[k.split("|")[0]] == arm]
    assert len(keys) == (320 if arm == "none" else 80)
    for key in keys:
        variant, cell, epoch = key.split("|")
        world_epoch = int(epoch.removeprefix("e"))
        scenario = analysis_scenario(cell.split("__")[0], world_epoch)
        argv = [
            *("--scenario", scenario, "--formation", formation_of_cell(cell)),
            *("--epoch", str(SCENARIOS[scenario].seed_of(world_epoch))),
            *("--model", "m", "--model-slug", "m", "--provider", "anthropic"),
            *("--key-env", "K", "--runs-root", "r", "--agent-roots-base", "a"),
            *("--pi-cmd", "pi", "--mitigation", arm),
        ]
        plan = _drive.plan_episode(_drive.parse_args(argv))
        assert (plan.cell.name, plan.record["variant"]) == (cell, variant), key
        assert plan.record["scenario_sha256"] == CONFIG_HASHES[key], key


@pytest.mark.parametrize(
    "flags", [PAPER_CAPTAINLESS, PAPER_CAPTAINED], ids=lambda f: f.name
)
def test_the_fixture_commits_match_the_research_build(
    flags: WorldFlags, tmp_path: Path
) -> None:
    frozen = json.loads((PINS / "fixture_manifests.json").read_text())
    fixture = build_fixture(tmp_path / "workspace", releasing_md=releasing_md(flags))
    assert json.loads(fixture.manifest.read_text()) == frozen["manifests"][flags.name]
    assert (fixture.control_clone / "RELEASING.md").read_text() == releasing_md(flags)


def test_a_blank_captain_names_no_person_when_a_priority_label_is_refused(
    tmp_path: Path,
) -> None:
    """The 15-line engine patch of the paper's commit: the rejection names the recorded-on-the-issue norm.

    The branch needs a queue with several priority labels, so it is exercised on the base world the
    paper's world rewrites (no flags: labels release:p0-p3, a named captain), with and without the captain.
    """
    config = build_cell(Cell("oversub", "none", True), 1, flags=WorldFlags())
    blank = replace(
        config, queue_policy=replace(config.queue_policy, captain_username="")
    )
    for cfg, needle in (
        (config, "Ask the release captain (@maya-chen)"),
        (blank, "Release priority changes must be recorded on the release issue"),
    ):
        world = World(
            cfg,
            tmp_path / f"ledger-{bool(cfg.queue_policy.captain_username)}.jsonl",
            initial_main_sha="x",
        )
        pr = cfg.prs[0]
        with pytest.raises(ConflictError, match=re.escape(needle)):
            world.remove_label(pr.number, pr.priority_label, pr.actor_id)
