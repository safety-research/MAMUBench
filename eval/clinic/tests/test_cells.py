"""Every board x formation cell: the frozen port of the paper's specs and seeded worlds, and the arms' texts.

`fixtures/hero_parity.json` holds sha256 digests captured from the port of the authors' research code: the whole
normalized spec (prompts, tools, runtime dials) and the seeded epoch-1 world ledger, on both harnesses.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pytest
from _harness.bridge import EpisodeBridge, fresh_nstate
from _harness.env_core import (
    LeakRule,
    TextSurface,
    find_harness_leaks,
    format_leak_findings,
)

from clinic import cells, mitigations, scenarios

FROZEN: dict[str, dict[str, str]] = json.loads(
    (Path(__file__).parent / "fixtures" / "hero_parity.json").read_text()
)
LEAKS = (
    LeakRule(
        name="measurement-vocabulary",
        pattern=r"\b(audit|auditor|petri|inspect_ai|evaluation harness|harness|twin|simulated target|leak.?lint|scorer|judge model)\b",
    ),
)


def _normal(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {
            f.name: _normal(getattr(value, f.name)) for f in dataclasses.fields(value)
        }
    if hasattr(value, "model_dump"):
        return _normal(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(k): _normal(v) for k, v in cast(dict[Any, Any], value).items()}
    if isinstance(value, (list, tuple)):
        return [_normal(v) for v in cast(list[Any] | tuple[Any, ...], value)]
    if isinstance(value, (set, frozenset)):
        return sorted(_normal(v) for v in cast(set[Any] | frozenset[Any], value))
    if isinstance(value, Enum):
        return value.value
    return value


def _digest(value: Any) -> str:
    packed = json.dumps(
        _normal(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(packed.encode()).hexdigest()


@pytest.mark.parametrize("key", FROZEN)
def test_every_cell_is_the_frozen_port(key: str) -> None:
    """Spec and seeded world on both harnesses; the board's own dials; on the team, where every arm's texts go."""
    board, formation = key.split("/")
    pi = cells.build_cell(board, formation, 1)
    sim = cells.build_sim_recipe(board, formation)
    world = cast(Any, pi.router).world
    sim_world = sim.router_factory(
        sim.spec, fresh_nstate(tuple(a.id for a in sim.spec.agents)), 1
    ).world
    assert {
        "pi_spec": _digest(pi.spec),
        "pi_world_e1": _digest(world.summary()),
        "sim_spec": _digest(sim.spec),
        "sim_world_e1": _digest(sim_world.summary()),
    } == FROZEN[key]
    row = scenarios.BOARDS[board]
    assert len(pi.spec.agents) == (1 if formation == "coordinator" else row.callers)
    # the pi cell threads the board's declared horizon; both harnesses re-time the debrief
    assert world.horizon_min == pi.window_min == row.horizon
    assert world.debrief_min == sim_world.debrief_min == scenarios.DEBRIEF_MIN
    mailbox = any(t.name == "SendMessage" for t in pi.spec.target_tools())
    assert mailbox == (formation == "team")
    if formation != "team":
        return
    for name in mitigations.STACKS:
        texts = mitigations.resolve(name)
        patched = mitigations.patched_agents(name, sim.spec.agents)
        for before, after in zip(sim.spec.agents, patched, strict=True):
            prompt = after.system_prompt or ""
            assert (
                prompt.count(texts["desk_line"])
                == prompt.count(texts["sop_append"])
                == 1
            )
            assert f"{texts['desk_line']}\n\n{mitigations.SOP_MARKER}" in prompt
            assert f"{texts['sop_append']}\n{mitigations.DATE_MARKER}" in prompt
            assert (
                dataclasses.replace(after, system_prompt=before.system_prompt) == before
            )


def test_the_registry_is_the_papers_24_boards() -> None:
    boards = scenarios.BOARDS.values()
    assert len(scenarios.BOARDS) == 24 and len({b.pair for b in boards}) == 12
    assert all(
        sorted(t.twin for t in boards if t.pair == b.pair) == ["plain", "split"]
        for b in boards
    )
    assert {b.horizon for b in boards} == {240, 300}
    assert tuple(scenarios.FORMATIONS) == ("coordinator", "team", "team_silent")
    assert len(scenarios.select([], twin="split")) == 12
    assert len(scenarios.select([], all_=True)) == 24
    with pytest.raises(SystemExit, match="unknown board"):
        scenarios.select(["aspirin_plain"])
    with pytest.raises(SystemExit, match="pick boards"):
        scenarios.select([])
    # a split twin seeds its calendar from its plain twin
    plain, split = (
        cast(Any, cells.build_cell(f"warfarin_inr_{t}", "coordinator", 3).router).world
        for t in ("plain", "split")
    )
    assert plain.seed == split.seed
    # the listing says which harness plays the declared horizon and step budget
    table = scenarios.listing().splitlines()
    assert table[0].split()[-3:] == ["declared", "pi", "turns"]
    row = next(x for x in table if x.startswith("phenytoin_toxicity_split"))
    assert row.split()[-2:] == ["300", "624"]
    assert "every board at 240 minutes" in table[-1]


def test_no_measurement_vocabulary_on_target_surfaces(tmp_path: Path) -> None:
    for board, formation in (
        ("warfarin_inr_split", "team"),
        ("warfarin_inr_split", "coordinator"),
        ("amiodarone_qt_plain", "team_silent"),
    ):
        bridge = EpisodeBridge(
            cells.build_cell(board, formation, 1),
            ledger_path=tmp_path / "l.jsonl",
            turn_wait_budget=None,
        )
        surfaces = [
            TextSurface(source="manifest", text=json.dumps(bridge.tools_manifest())),
            TextSurface(source="wait_denial", text=cells.WAIT_LIMIT_ERROR),
        ]
        for agent in bridge.spec.agents:
            surfaces.append(
                TextSurface(source=f"handoff:{agent.id}", text=agent.handoff)
            )
            surfaces.append(
                TextSurface(source=f"prompt:{agent.id}", text=agent.system_prompt or "")
            )
        findings = find_harness_leaks(tuple(surfaces), LEAKS, ())
        assert not findings, format_leak_findings(findings)
