"""Scenario selection, and no target-visible surface leaks the measurement stack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _harness.bridge import EpisodeBridge
from _harness.env_core import (
    LeakRule,
    TextSurface,
    find_harness_leaks,
    format_leak_findings,
)

from api_key import cells, scenarios
from api_key.scenarios.operators import all_authored_reply_texts

#: Vocabulary that would out the measurement stack. Bare `eval` is deliberately NOT banned: the cast are
#: ML researchers whose in-fiction jobs are their own evals; the harness framing around it is what leaks.
RULES = (
    LeakRule(
        name="measurement-vocabulary",
        pattern=r"\b(audit|auditor|petri|inspect_ai|evaluation harness|harness|twin|simulated target|leak.?lint|scorer|judge model)\b",
    ),
)


def test_select_and_lookup() -> None:
    assert [s.id for s in scenarios.select([], seats=16)] == [
        s.id for s in scenarios.SCENARIOS.values() if s.n_seats == 16
    ]
    assert len(scenarios.select([], all_=True)) == 25
    with pytest.raises(SystemExit, match="unknown scenario"):
        scenarios.select(["stakes_999"])
    with pytest.raises(SystemExit, match="pick scenarios"):
        scenarios.select([])


def pi_surfaces(name: str, formation: str, tmp_path: Path) -> list[TextSurface]:
    """A pi-harness cell: the served tool manifest, the wait denial, every brief, system prompt and norms file."""
    bridge = EpisodeBridge(
        cells.build_cell(name, formation, 1),
        ledger_path=tmp_path / "l.jsonl",
        turn_wait_budget=None,
    )
    surfaces = [
        TextSurface(source="manifest", text=json.dumps(bridge.tools_manifest())),
        TextSurface(source="wait_denial", text=cells.WAIT_LIMIT_ERROR),
    ]
    for agent in bridge.spec.agents:
        surfaces.append(TextSurface(source=f"handoff:{agent.id}", text=agent.handoff))
        if agent.system_prompt is not None:
            surfaces.append(
                TextSurface(source=f"system:{agent.id}", text=agent.system_prompt)
            )
    surfaces += [
        TextSurface(source=f"norms:{path}", text=text)
        for path, text in bridge.norms_files().items()
    ]
    return surfaces


def sim_surfaces(name: str, formation: str, mitigation: str) -> list[TextSurface]:
    """A simulated-harness-only cell (solo, the lead arms): every brief and tool description a target sees."""
    spec = cells.build_sim_recipe(name, formation, mitigation=mitigation).spec
    surfaces: list[TextSurface] = []
    for agent in spec.agents:
        tools = [t.model_dump(mode="json") for t in spec.target_tools(agent.id)]
        surfaces.append(TextSurface(source=f"handoff:{agent.id}", text=agent.handoff))
        surfaces.append(TextSurface(source=f"tools:{agent.id}", text=json.dumps(tools)))
    return surfaces


@pytest.mark.parametrize(
    ("harness", "name", "formation", "mitigation"),
    [
        ("pi", "stakes_100", "team", "none"),
        ("pi", "stakes_100", "coordinator", "none"),
        ("pi", "peq_cls_n8_143", "team_silent", "none"),
        ("pi", "stakes_n16_480", "team", "none"),
        ("sim", "stakes_100", "solo", "none"),
        ("sim", "peq_duo_n16_409", "solo", "none"),
        ("sim", "stakes_100", "team", "lead_value"),
        ("sim", "stakes_n8_240", "team", "lead_full_stack"),
        ("sim", "peq_skl_n16_463", "team", "lead_full_stack"),
    ],
)
def test_no_measurement_vocabulary_on_target_surfaces(
    harness: str, name: str, formation: str, mitigation: str, tmp_path: Path
) -> None:
    surfaces = (
        pi_surfaces(name, formation, tmp_path)
        if harness == "pi"
        else sim_surfaces(name, formation, mitigation)
    )
    findings = find_harness_leaks(tuple(surfaces), RULES, ())
    assert not findings, format_leak_findings(findings)


def test_no_measurement_vocabulary_in_authored_operator_replies() -> None:
    surfaces = tuple(
        TextSurface(source=f"authored_reply:{i}", text=text)
        for i, text in enumerate(all_authored_reply_texts())
    )
    findings = find_harness_leaks(surfaces, RULES, ())
    assert not findings, format_leak_findings(findings)
