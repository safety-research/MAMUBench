"""All hero specs and seeded initial worlds stay unchanged by the standalone port.

Hashes were captured from the port of the authors' research code before refactoring. They
cover the complete dataclass spec (including prompts, tools and runtime dials),
and the deterministic epoch-1 world ledger for both harnesses and every formation.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pytest
from _harness.bridge import fresh_nstate

from api_key import cells
from api_key.environment.router import TokenClusterRouter

FROZEN = json.loads(
    (Path(__file__).parent / "fixtures" / "hero_parity.json").read_text()
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
def test_frozen_hero_spec_and_seeded_world(key: str) -> None:
    name, formation = key.split("/")
    expected = FROZEN[key]
    pi = cells.build_cell(name, formation, 1)
    sim = cells.build_sim_recipe(name, formation)
    nstate = fresh_nstate(tuple(a.id for a in sim.spec.agents))
    router = sim.router_factory(sim.spec, nstate, 1)
    assert _digest(pi.spec) == expected["pi_spec"]
    assert (
        _digest(cast(TokenClusterRouter, pi.router).world.summary())
        == expected["pi_world_e1"]
    )
    assert _digest(sim.spec) == expected["sim_spec"]
    assert _digest(router.world.summary()) == expected["sim_world_e1"]
