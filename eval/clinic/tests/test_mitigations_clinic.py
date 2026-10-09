"""The clinic mitigation arms s1, s2, s3: texts, stack resolution and injection pinned to the paper's runs.

`fixtures/pinned_mitigations.json` holds sha256 digests (no texts) of three records of the paper's runs:

- `rules` / `stacks`: the research-code registry's entries for the five rules and three stacks (registry md5
  `registry_md5`); every shipped text must hash to its registry component.
- `roots`: the resolved `components` the three paper roots (Claude Opus 5, `warfarin_inr_split`, episodes 1-10)
  recorded, and their scheduler knobs; `resolve` must reproduce the components and the knobs must be the
  `standard` instrument.
- `desk_prompts_warfarin_inr_split`: every desk system prompt of epoch 1 of those three transcripts; the release's
  team spec with the arm injected must reproduce all 17, byte for byte.

Where every board's desks take the texts is checked cell by cell in `test_cells.py`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from _harness.readout import load_run
from _mitigations import NONE

from clinic import cells, mitigations, report
from clinic.tests.conftest import run_sim

PINNED: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "pinned_mitigations.json").read_text()
)
REGISTRY_ID = {"s1": "r2_stack_s3", "s2": "r2_stack_s5", "s3": "r2_stack_s11"}
BOARD = "warfarin_inr_split"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_texts_and_stacks_are_the_registrys_and_resolve_as_the_paper_roots_recorded() -> (
    None
):
    assert PINNED["registry_md5"] == "fa8f3fcdf1c2b7b794171900d36eb367"
    assert set(mitigations.RULES) == set(PINNED["rules"]) == set("ABCDE")
    for letter, rule in mitigations.RULES.items():
        want = PINNED["rules"][letter]
        assert (rule.research_id, rule.component, sha(rule.text)) == (
            want["research_id"],
            want["component"],
            want["sha256"],
        )
    standard = cells.SIM_INSTRUMENTS[cells.MITIGATION_INSTRUMENT]
    for name, stack in mitigations.STACKS.items():
        want = PINNED["stacks"][name]
        assert stack.research_id == want["research_id"] == REGISTRY_ID[name]
        assert [mitigations.RULES[x].research_id for x in stack.rules] == want[
            "parents"
        ]
        assert want["components"] == {}  # a stack's texts are its parents'
        root = PINNED["roots"][stack.research_id]
        assert root["cell"] == f"clinic_{BOARD}_meshfull_comms_tight_scripted"
        packed = json.dumps(
            mitigations.resolve(name),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        assert sha(packed) == root["components_sha256"]
        # the roots ran the standard knobs at the paper's reasoning setting
        knobs = root["knobs"]
        assert {
            k: int(knobs[k])
            for k in (
                "MAX_TURNS",
                "BURST",
                "MAX_AHEAD",
                "PETRI_GENERATE_TIMEOUT",
                "PETRI_SAMPLE_TIME_LIMIT",
            )
        } == {
            "MAX_TURNS": standard.max_turns,
            "BURST": standard.burst,
            "MAX_AHEAD": standard.max_ahead,
            "PETRI_GENERATE_TIMEOUT": standard.generate_timeout_s,
            "PETRI_SAMPLE_TIME_LIMIT": standard.time_limit_s,
        }
        assert {k: knobs[k] for k in standard.knobs} == standard.knobs
        assert knobs["TARGET_THINKING"] == cells.THINKING_OF_RECORD["anthropic"]
    # two texts under one component join with a blank line, in the registry's parent order
    s2 = mitigations.resolve("s2")
    assert s2 == {
        "sop_append": f"{mitigations.RULES['A'].text}\n\n{mitigations.RULES['E'].text}",
        "desk_line": mitigations.RULES["B"].text,
    }


@pytest.mark.parametrize("name", sorted(REGISTRY_ID))
def test_the_arms_recipe_is_the_paper_transcripts_on_the_standard_scheduler(
    name: str,
) -> None:
    control = cells.build_sim_recipe(BOARD, "team")
    recipe = cells.build_sim_recipe(BOARD, "team", mitigation=name)
    paper = PINNED["desk_prompts_warfarin_inr_split"][REGISTRY_ID[name]]
    ours = sorted(sha(a.system_prompt or "") for a in recipe.spec.agents)
    assert len(ours) == 17 and ours == paper
    # prompt text only: the rest of the spec is the control's, on the control's instrument, the arm recorded
    assert replace(recipe.spec, agents=control.spec.agents) == control.spec
    assert (recipe.mitigation, control.mitigation) == (name, None)
    assert recipe.instrument == control.instrument == cells.MITIGATION_INSTRUMENT
    assert cells.MITIGATION_INSTRUMENT == "standard"
    assert recipe.knobs == control.knobs == cells.SIM_INSTRUMENTS["standard"].knobs
    assert recipe.max_turns == 5000
    assert recipe.effort_of_record == control.effort_of_record


def test_the_arms_apply_to_the_simulated_team_only() -> None:
    assert list(mitigations.MITIGATIONS) == [NONE, "s1", "s2", "s3"]
    for name in mitigations.STACKS:
        arm = mitigations.MITIGATIONS[name]
        assert (arm.formations, arm.harnesses) == (("team",), ("sim",))
        assert arm.research_id == REGISTRY_ID[name]
        for formation in ("coordinator", "team_silent"):
            with pytest.raises(ValueError, match=f"not {formation}"):
                cells.build_sim_recipe(BOARD, formation, mitigation=name)
        with pytest.raises(ValueError, match="not pi"):
            cells.build_cell(BOARD, "team", 1, name)
    listing = mitigations.listing()
    assert "act on what you hear" in listing and "r2_stack_s11" not in listing
    desk = cells.sim_spec(BOARD, "team").agents[0]
    with pytest.raises(ValueError, match="desk console prompt missing"):
        mitigations.patched_agents("s3", (replace(desk, system_prompt="no marker"),))


def test_an_arm_morning_banks_stamped_and_reads_as_its_own_cell(tmp_path: Path) -> None:
    runs = tmp_path / "runs"
    run_sim(runs, "team", "--mitigation", "s3")
    (run_dir,) = runs.iterdir()
    assert run_dir.name == (
        f"clinic_{BOARD}_meshfull_comms_tight_scripted__mit-s3__claude-sonnet-5__e1__sim__fakemodel"
    )
    loaded = load_run(run_dir)
    assert loaded is not None
    config = loaded[1]
    assert (config["mitigation"], config["instrument"]) == ("s3", "standard")
    assert config["on_paper_instrument"] is True
    episodes, _ = report.collect(runs)
    assert [(e["mitigation"], e["instrument"]) for e in episodes] == [
        ("s3", "standard")
    ]
    assert report.is_valid(episodes[0])
    (cell,) = report.cell_rows(episodes, draws=20)
    assert (cell["mitigation"], cell["valid"]) == ("s3", 1)
