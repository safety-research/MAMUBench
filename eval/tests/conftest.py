"""Shared stand-ins for the launcher, runner, mitigation and Modal tests (offline: nothing runs on Modal or a model)."""

from __future__ import annotations

import importlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from _mitigations import Mitigation

import run

ENVS = ("api_key", "clinic", "merge_queue", "personal_assistant")
#: A registered stand-in arm: it drives the per-arm plumbing (its hooks are the real arms' or stubbed per test).
FAKE = "fake_arm"


def fake_arm_record(
    formations: tuple[str, ...] = ("team",), **fields: Any
) -> Mitigation:
    return Mitigation(
        name=FAKE,
        paper_label="fake arm (tests)",
        description="Registered, not implemented.",
        formations=formations,
        research_id="test_only",
        **fields,
    )


@pytest.fixture
def fake_arm(monkeypatch: pytest.MonkeyPatch) -> None:
    """`fake_arm` (team only, both harnesses) in all four registries for one test.

    Its runs are the formation matrix's models and episodes on the team.
    """
    for env in ENVS:
        package = importlib.import_module(f"{env}.mitigations")
        monkeypatch.setitem(package.MITIGATIONS, FAKE, fake_arm_record())
        paper = importlib.import_module(f"{env}.matrix").PAPER
        monkeypatch.setitem(package.RUNS, FAKE, replace(paper, formations=("team",)))


@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> list[tuple[list[str], dict[str, str]]]:
    """Every `(command, env)` the root launcher `run.main` executes (its subprocess is stubbed)."""
    calls: list[tuple[list[str], dict[str, str]]] = []

    def execute(command: list[str], **kwargs: Any) -> object:
        calls.append((command, dict(kwargs.get("env") or {})))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(run.subprocess, "run", execute)
    return calls


def write(path: Path, text: str) -> Path:
    path.write_text(text)
    return path
