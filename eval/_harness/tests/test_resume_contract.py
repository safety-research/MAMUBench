"""Completed episodes must not hide changed experimental settings."""

from __future__ import annotations

from pathlib import Path

import pytest
from api_key.run import main


def _argv(tmp_path: Path, harness: str, standin: str) -> list[str]:
    return [
        "--scenario",
        "stakes_100",
        "--formation",
        "coordinator",
        "--harness",
        harness,
        standin,
        "--runs-root",
        str(tmp_path / "runs"),
    ]


def test_changed_settings_cannot_skip_a_completed_pi_episode(tmp_path: Path) -> None:
    argv = _argv(tmp_path, "pi", "--fake-pi")
    assert main(argv) == 0
    assert main(argv) == 0
    with pytest.raises(SystemExit, match="different configuration"):
        main([*argv, "--turn-wait-budget", "30"])
