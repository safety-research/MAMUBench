"""The ported scheduler knobs are inert when unset: hero-instrument worlds are byte-identical to the pre-port code.

The digests below were taken from the release as it stood before the teams' scheduler knobs were
ported into the vendored `routing.py`, `env_core/beats.py`, `driver.py` and the clinic router: one offline (`--fake-model`) epoch-1 episode per formation of `stakes_100` and
`warfarin_inr_plain` under the hero instrument (the coordinators' paper instrument; each formation's spec on
it through `cells.instrument_recipe`, played by `sim.run_episode`), the world sidecar with its per-run tool-call
ids and short uuids normalized. Every field must match except `driver_ended`, which the port extends on purpose: the
driver names world deliveries still stranded at the horizon (`— world deliveries stranded (...)`),
unconditionally, as the paper's harness does; the physics are untouched, so the pre-port text must remain its
prefix.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
from api_key import cells as api_cells
from clinic import cells as clinic_cells

from _harness import sim
from _harness.runner import RunConfig

GOLDEN: dict[str, tuple[str, str]] = {
    "token_cluster__stakes_100__none__comms__notax__e1.json": (
        "70aab773b1cfd7e4748f320a463dcc63cfd8fd1f855c954f314078bbe51377e2",
        "ABCD",
    ),
    "token_cluster__stakes_100__none__nocomms__notax__e1.json": (
        "70aab773b1cfd7e4748f320a463dcc63cfd8fd1f855c954f314078bbe51377e2",
        "ABCD",
    ),
    "token_cluster__stakes_100__steward__notax__e1.json": (
        "081b03f0b5ea6f3a982bced556fe0dd4216b4a57f9847f20dbb270b773f5b655",
        "S",
    ),
    "clinic_warfarin_inr_plain_meshfull_comms_tight_scripted__e1.json": (
        "603a3ee946723dd31a1c19b1516ed2c09d21f5addca3a813ebe8fb70a43e3b6a",
        "ABCD",
    ),
    "clinic_warfarin_inr_plain_meshfull_nocomms_tight_scripted__e1.json": (
        "229d425beea1fa8494cf4c9fa329022dd18a701f928f0d5fa73f0c564ee21ecc",
        "ABCD",
    ),
    "clinic_warfarin_inr_plain_steward_nocomms_tight_scripted__e1.json": (
        "0b152dd5cfd0b5814d46895d2572b1dc53f9d499bc53fcddd7ce540c3c85fd72",
        "A",
    ),
}


def _prefix(seats: str) -> str:
    """The pre-port `driver_ended`: every named seat holding its last staged tool result."""
    held = "; ".join(
        f"{seat}: staged tool results ['TC'] awaiting delivery" for seat in seats
    )
    return f"world horizon reached — undelivered content remained ({held})"


def _normalized(path: Path) -> tuple[str, str]:
    text = re.sub(r"for_tool_call_[0-9a-f-]{36}", "TC", path.read_text())
    text = re.sub(r'"[0-9a-zA-Z]{22}"', '"ID"', text)
    world: dict[str, Any] = json.loads(text)
    ended = str(world.pop("driver_ended"))
    digest = hashlib.sha256(json.dumps(world, sort_keys=True).encode()).hexdigest()
    return digest, ended


def test_hero_worlds_are_byte_identical_to_the_pre_port_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVAL_SIM_DISPLAY", "none")
    keys = sim.SimKeys("fake-not-used", "fake-not-used")
    for eval_name, scenario, cells in (
        ("api_key", "stakes_100", api_cells),
        ("clinic", "warfarin_inr_plain", clinic_cells),
    ):
        for formation in ("coordinator", "team", "team_silent"):
            recipe = cells.instrument_recipe(
                scenario, "hero", cells.sim_spec(scenario, formation)
            )
            config = RunConfig(
                eval=eval_name,
                scenario=scenario,
                formation=formation,
                model="claude-sonnet-5",
                provider="anthropic",
                runs_root=tmp_path,
                harness="sim",
                fake_model=True,
            )
            assert not sim.run_episode(config, recipe, 1, keys)["skipped"]
    sidecars = {p.name: p for p in tmp_path.glob("*/logs/worlds/*.json")}
    assert sorted(sidecars) == sorted(GOLDEN)
    for name, (digest, seats) in GOLDEN.items():
        got, ended = _normalized(sidecars[name])
        assert got == digest, name
        assert ended.startswith(_prefix(seats)), (name, ended)
