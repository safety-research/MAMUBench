"""The solo formation and the two team-lead arms are the paper's, spec for spec, prompt for prompt, setting for setting.

`fixtures/pinned_surfaces.json` holds sha256 digests (no texts) of three independent anchors:

- `builder`: the builders in the authors' research code, at the version the paper ran: for all 25
  scenarios x {solo, lead_value, lead_full_stack} the cell name, the complete spec digest
  (`test_hero_parity._digest`), the seeded world at epochs 1 and 7, the step budget and the agent count; `texts`:
  the auditor seed prompt of four cells.
- `audited_full_stack`: the paper's audited render of the full stack on `stakes_100` (byte-identical to the
  paper's episode): the system prompt and opening brief of all five agents, in agent order.
- `transcripts`: two paper transcripts (Claude Opus 5, `stakes_100`, episode 1): the `lead_value` ladder episode
  and the formation corpus's solo episode (system prompt, opening brief and offered tools per agent).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import pytest
from _harness.sim import SimRecipe
from _multiagent_pi.scenario import build_seed

from api_key import cells
from api_key.scenarios import FORMATIONS, SCENARIOS
from api_key.scenarios.prompts import TokenClusterScenarioSpec, router_for_spec
from api_key.tests.test_hero_parity import (
    _digest,  # pyright: ignore[reportPrivateUsage]
)

PINNED: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "pinned_surfaces.json").read_text()
)
LABELS = ("solo", "lead_value", "lead_full_stack")


def sha(text: str | None) -> str:
    return hashlib.sha256((text or "").encode()).hexdigest()


def recipe(scenario: str, label: str) -> SimRecipe:
    """What the release plays for one research render: `solo`, or an arm of the `team` formation."""
    if label == "solo":
        return cells.build_sim_recipe(scenario, "solo")
    return cells.build_sim_recipe(scenario, "team", mitigation=label)


def release_spec(scenario: str, label: str) -> TokenClusterScenarioSpec:
    return cast(TokenClusterScenarioSpec, recipe(scenario, label).spec)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("scenario", list(SCENARIOS))
def test_spec_and_seeded_worlds_equal_the_research_builder(
    scenario: str, label: str
) -> None:
    want = PINNED["builder"][f"{scenario}/{label}"]
    played = recipe(scenario, label)
    spec = played.spec
    assert spec.name == want["cell"] and len(spec.agents) == want["n_agents"]
    assert played.max_turns == want["max_turns"]
    assert _digest(spec) == want["spec"]
    assert _digest(router_for_spec(spec, {}, 1).world.summary()) == want["world_e1"]
    assert _digest(router_for_spec(spec, {}, 7).world.summary()) == want["world_e7"]


@pytest.mark.parametrize("key", sorted(PINNED["texts"]))
def test_auditor_seed_prompts_equal_the_research_render(key: str) -> None:
    scenario, label = key.split("/")
    assert (
        sha(build_seed(release_spec(scenario, label)))
        == (PINNED["texts"][key]["seed_prompt"])
    )


@pytest.mark.parametrize(
    ("anchor", "label"),
    [
        ("audited_full_stack", "lead_full_stack"),
        ("transcripts/lead_value/stakes_100/claude-opus-5/e1", "lead_value"),
        ("transcripts/solo/stakes_100/claude-opus-5/e1", "solo"),
    ],
)
def test_prompts_and_tools_equal_the_papers_renders(anchor: str, label: str) -> None:
    """System prompt and opening brief per agent (and, in a transcript, the offered tools), keyed by cwd.

    The agent order itself is pinned by the spec digests; the audited render lists the lead first, then A-D.
    """
    pinned: dict[str, Any] = PINNED
    for part in anchor.split("/", 1):
        pinned = pinned[part]
    spec = release_spec("stakes_100", label)
    assert pinned["sample"] == spec.name and pinned["epoch"] == 1
    seen = pinned["agents"]
    if isinstance(seen, list):  # the audited render: agents in order, no tools
        seen = {a["cwd"]: a for a in cast(list[dict[str, Any]], seen)}
    assert sorted(a.cwd for a in spec.agents) == sorted(seen)
    for agent in spec.agents:
        want = seen[agent.cwd]
        assert sha(agent.handoff) == want["brief"]
        assert sha(agent.system_message(spec.date)) == want["system"]
        if "tools" in want:
            assert [t.name for t in spec.target_tools(agent.id)] == want["tools"]


@pytest.mark.parametrize("scenario", ["stakes_100", "peq_cls_n8_143", "stakes_n16_480"])
def test_every_formation_and_arm_plays_the_same_night(scenario: str) -> None:
    """Worlds key on `(scenario, epoch)`: every formation (both harnesses) and arm plays the same seeded night."""
    specs = [cells.sim_spec(scenario, f) for f in FORMATIONS] + [
        release_spec(scenario, arm) for arm in LABELS[1:]
    ]
    for epoch in (1, 4):
        team = router_for_spec(cells.sim_spec(scenario, "team"), {}, epoch).world
        worlds = [router_for_spec(spec, {}, epoch).world for spec in specs] + [
            cast(Any, cells.build_cell(scenario, f, epoch).router).world
            for f in FORMATIONS
            if f != "solo"
        ]
        for world in worlds:
            assert world.seed == team.seed
            assert set(world.summary()["jobs"]) == set(team.summary()["jobs"])
        # the lead arms run the team's world itself (same seats, same launch stagger)
        lead_world = router_for_spec(specs[-1], {}, epoch).world
        assert (
            lead_world.summary()["launch_offsets"] == team.summary()["launch_offsets"]
        )


#: The settings of record the solo and lead cells play: (scenario, label) -> cell, instrument, burst, max_ahead,
#: step budget, first-pass limit, long-limit retry, generate timeout.
# fmt: off
SETTINGS = {
    ("stakes_100", "solo"): (
        "token_cluster__stakes_100__solo__notax",
        "hero", 6, None, 800, 7200, None, 900,
    ),
    ("stakes_n8_240", "solo"): (
        "token_cluster__stakes_n8_240__solo__n8_fixed_total__notax",
        "hero", 6, None, 1000, 10800, None, 900,
    ),
    ("peq_lin_n4_77", "solo"): (
        "token_cluster__peq_lin_n4_77__solo__notax",
        "hero", 6, None, 800, 14400, None, 900,
    ),
    ("stakes_n16_480", "solo"): (  # the 16-user driver stamps no clock
        "token_cluster__stakes_n16_480__solo__n16_fixed_total",
        "hero", 6, None, 1400, 14400, None, 900,
    ),
    **{
        (scenario, arm): (
            None, "limits_off", 1_000_000, 1_000_000, turns, limit, None, 3600,
        )
        for arm in LABELS[1:]
        for scenario, turns, limit in (
            ("stakes_100", 850, 14_400),
            ("peq_pyr_n8_116", 1050, 21_600),
            ("peq_skl_n16_350", 1450, 28_800),
        )
    },
}
# fmt: on


@pytest.mark.parametrize(("scenario", "label"), sorted(SETTINGS))
def test_solo_and_lead_recipes_are_the_settings_of_record(
    scenario: str, label: str
) -> None:
    cell, instrument, burst, max_ahead, turns, limit, retry, timeout = SETTINGS[
        (scenario, label)
    ]
    played = recipe(scenario, label)
    if cell is not None:
        assert played.spec.name == cell
    assert (played.instrument, played.burst, played.max_ahead) == (
        instrument,
        burst,
        max_ahead,
    )
    assert (played.max_turns, played.time_limit_s, played.retry_time_limit_s) == (
        turns,
        limit,
        retry,
    )
    assert played.generate_timeout_s == timeout and played.auditor == "escalation"
    assert played.mitigation == (None if label == "solo" else label)
    assert played.effort_of_record["anthropic"] == "none"
