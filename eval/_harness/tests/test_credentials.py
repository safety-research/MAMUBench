"""Live credentials exist only while seats are running, never in saved pi artifacts."""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import Any

import pytest
from api_key.cells import build_cell

from _harness import pi_rpc, runner

SENTINEL = "dummy-credential-for-regression-only"


@pytest.mark.parametrize("startup_error", [False, True])
def test_shared_pi_runner_cleans_auth_after_close_on_success_or_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, startup_error: bool
) -> None:
    config = runner.RunConfig(
        eval="api_key",
        scenario="stakes_100",
        formation="coordinator",
        model="offline",
        provider="anthropic",
        runs_root=tmp_path / "runs",
        fake_pi=True,
        rounds_max=1,
        pack_workspaces=True,
    )
    cell = build_cell("stakes_100", "coordinator", 1)
    original_spawn = pi_rpc.spawn_agent
    original_close = pi_rpc.close_agents
    authored: list[Path] = []
    stopped = False

    def spawn(*args: Any, **kwargs: Any) -> Any:
        agent_dir = Path(kwargs["env"]["HOME"]) / ".pi" / "agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "auth.json").write_text(SENTINEL)
        (agent_dir / "settings.json").write_text("keep")
        authored.append(agent_dir / "auth.json")
        if startup_error:
            raise RuntimeError("injected startup failure")
        return original_spawn(*args, **kwargs)

    def close(handles: list[Any]) -> None:
        nonlocal stopped
        assert authored and all(path.is_file() for path in authored)
        original_close(handles)
        stopped = True

    monkeypatch.setattr(pi_rpc, "spawn_agent", spawn)
    monkeypatch.setattr(pi_rpc, "close_agents", close)
    if startup_error:
        with pytest.raises(RuntimeError, match="injected startup failure"):
            runner.run_episode(config, cell, 1, "unused")
    else:
        runner.run_episode(config, cell, 1, "unused")
    assert stopped
    assert all(not path.exists() for path in authored)
    run_dir = runner.run_dir_for(config, cell, 1)
    if not startup_error:
        with tarfile.open(run_dir / "workspaces.tar.gz") as archive:
            assert not any(
                name.endswith("/.pi/agent/auth.json") for name in archive.getnames()
            )
            assert any(
                name.endswith("/.pi/agent/settings.json") for name in archive.getnames()
            )
