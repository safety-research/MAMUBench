"""Runtime teardown removes authentication before artifact copying, including failures."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from personal_assistant.environment import food_runtime, trip_runtime
from personal_assistant.harness.local_runtime import FAKE_PI, LocalHostShim, SeatLaunch
from personal_assistant.scenarios import register_trip_specs


def test_stop_scrubs_auth_before_copy_and_cleans_up_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both substrates' runtimes, a clean stop and each way it can fail (copy, close, a partial start)."""
    register_trip_specs()
    for substrate in ("food", "trip"):
        for failure in (None, "copy", "close", "partial_start"):
            run_dir = tmp_path / f"{substrate}-{failure}" / "run"
            _stop(run_dir, monkeypatch, substrate, failure)


def _stop(
    run_dir: Path, monkeypatch: pytest.MonkeyPatch, substrate: str, failure: str | None
) -> None:
    module: Any = food_runtime if substrate == "food" else trip_runtime
    api_key = "test-secret-not-for-artifacts"
    common = dict(
        model="unused",
        provider="anthropic",
        api_key=api_key,
        turn_timeout=1,
        thinking="off",
        root_host=False,
        protected_roots=(),
    )
    runtime = (
        module.FoodRuntime("conf_kestrel_quiz_booth_steward", 1, run_dir, **common)
        if substrate == "food"
        else module.TripRuntime(
            "steward", run_dir, scenario="twin_by_the_bathroom", **common
        )
    )
    container = LocalHostShim(run_dir, SeatLaunch(FAKE_PI))
    container.start()
    root = container.root
    runtime.container = container
    events: list[str] = []

    def credential_markers() -> dict[str, str]:
        return {}

    def seat_cwd(seat: str) -> str:
        return f"/home/seat-{'one' if seat == 'c1' else 'two'}/ws"

    def log(*args: object) -> None:
        pass

    runtime.server = SimpleNamespace(
        credential_markers=credential_markers, stop=lambda: events.append("server_stop")
    )
    bridge = SimpleNamespace(
        ids=("c1", "c2"),
        usernames={"c1": "seat-one", "c2": "seat-two"},
        seat_cwd=seat_cwd,
        log=log,
    )
    for username in bridge.usernames.values():
        container.write_file(
            f"/home/{username}/.pi/agent/auth.json", api_key, mode="0600"
        )
        container.write_file(f"/home/{username}/ws/AGENTS.md", "test workspace")
        container.write_file(f"/home/{username}/.pi/sessions/test.jsonl", "{}\n")
    if failure != "partial_start":
        runtime.bridge = bridge
        runtime.handles = {seat: seat for seat in bridge.ids}

    def close(seat: str) -> None:
        events.append(f"close_{seat}")
        if failure == "close" and seat == "c1":
            raise RuntimeError("close failed")

    monkeypatch.setattr(module.pi_rpc, "close_agent", close)
    original_copy = container.copy_out

    def copy(source: str, target: Path) -> bool:
        assert events[:2] == ["close_c1", "close_c2"]
        assert not list(root.rglob("auth.json"))
        events.append("copy")
        if failure == "copy":
            raise RuntimeError("copy failed")
        return original_copy(source, target)

    monkeypatch.setattr(container, "copy_out", copy)
    if failure in {"copy", "close"}:
        with pytest.raises(RuntimeError, match=f"{failure} failed"):
            runtime.stop()
    else:
        runtime.stop()
    assert not root.exists()
    assert events[-1] == "server_stop"
    assert not list(run_dir.rglob("auth.json"))
    if failure is None:
        assert "copy" in events
        assert (run_dir / "agents/c1/ws/AGENTS.md").read_text() == "test workspace"
    elif failure in {"close", "partial_start"}:
        assert "copy" not in events
    before = list(events)
    runtime.stop()
    assert events == before
