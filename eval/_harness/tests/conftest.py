"""Shared wiring for the harness tests: one bridge over a default cell of either eval."""

from __future__ import annotations

from pathlib import Path

from _harness.bridge import EpisodeBridge

DEFAULT_SCENARIO = {"api_key": "stakes_100", "clinic": "warfarin_inr_split"}


def bridge_for(
    tmp_path: Path,
    eval_name: str,
    formation: str,
    *,
    scenario: str | None = None,
    budget: int | None = 60,
) -> EpisodeBridge:
    """One episode bridge over epoch 1 of a cell — the shared test wiring."""
    if eval_name == "api_key":
        from api_key.cells import build_cell
    else:
        from clinic.cells import build_cell
    cell = build_cell(scenario or DEFAULT_SCENARIO[eval_name], formation, 1)
    return EpisodeBridge(
        cell, ledger_path=tmp_path / "ledger.jsonl", turn_wait_budget=budget
    )
