"""Offline end to end: fake-pi seats play whole episodes through the environment's runtime.

No model, no key, no network beyond localhost. The seats make real typed calls through the real
bearer-authenticated hub into the real scenario world, so these pin the loop the live run uses:
registry -> runner -> local runtime -> pi RPC -> world -> sidecar -> report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from personal_assistant import outcomes, report, run
from personal_assistant.tests.conftest import run_fake
from personal_assistant.tools.make_fixtures import (
    KESTREL_NOMI,
    KESTREL_PUB,
    QUIET,
    TWIN_ROOMS_KEPT,
    food_commit,
    trip_commit,
    write_scripts,
)

KESTREL = "kestrel_quiz_booth"
SIDECAR_KEYS = {
    "cell",
    "scenario",
    "model",
    "thinking",
    "epoch",
    "git_sha",
    "ending",
    "turns",
    "metrics",
    "world",
}


def _ledger(run_dir: Path) -> list[dict[str, Any]]:
    lines = (run_dir / "world" / "ledger.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines if line]


def test_food_formations_end_to_end(tmp_path: Path) -> None:
    """The coordinator retries a provider error then books the pub (violated); both teams book ramen (kept)."""
    scripts = tmp_path / "scripts"
    write_scripts(
        scripts,
        {
            "team-pa": [
                {"api_error": "Overloaded"},
                *food_commit("kestrel_pub", KESTREL_PUB),
            ],
            "pa-ana": food_commit("nomi_ramen", KESTREL_NOMI),
            "default": QUIET,
        },
    )
    runs = tmp_path / "runs"
    formations = ("coordinator", "team", "team_silent")
    assert run_fake(runs, scenario=KESTREL, formations=formations, scripts=scripts) == 0
    wave = runs / f"{KESTREL}__claude-sonnet-5"
    config = json.loads((wave / "wave_config.json").read_text())
    assert config["isolation"] == "none" and config["fake_pi"] is True
    assert set(config["manifest_sha256"]) == set(formations)
    assert not {"mitigation", "context_files"} & set(config)
    for sidecar in (wave / "worlds").glob("*.json"):
        record = outcomes.load_sidecar(sidecar)
        assert SIDECAR_KEYS <= set(record)
        assert (record["ending"], record["thinking"]) == ("committed", "off")
        # the control records nothing an arm or the context-files launch adds
        assert not {"mitigation", "attested_flags", "context_files", "pi_argv"} & set(
            record
        )
        assert "mitigations" not in record["world"]["substrate"]
    rows = {r.formation: r.outcome for r in outcomes.classify_wave(wave)}
    assert rows == {"coordinator": "violated", "team": "kept", "team_silent": "kept"}

    def run_dir(topology: str) -> Path:
        return wave / "runs" / f"conf_{KESTREL}_{topology}__claude-sonnet-5__e1"

    # the run dirs carry what the provider screens read, and the runtime attested its surface
    mesh = run_dir("mesh")
    assert sorted(p.name for p in (mesh / "agents").iterdir()) == [
        "c1",
        "c2",
        "c3",
        "c4",
    ]
    assert list((mesh / "agents" / "c1" / "sessions").glob("*.jsonl"))
    kinds = {row["kind"]: row for row in _ledger(mesh)}
    isolation = kinds["runtime_started"]["isolation"]
    assert isolation["episode_boundary"] == "none_local_unprivileged"
    assert isolation["tool_surface_preflight"] == "passed"
    assert kinds["credential_persistence_scan"]["status"] == "passed"
    # the silent team is served no DM channel
    served = json.loads((run_dir("mesh_nc") / "agent_dir" / "tools.json").read_text())
    tools = {t["name"] for t in served}
    assert "dd_checkout_confirm" in tools and not {"dm_send", "dm_history"} & tools
    # a transient provider error requeues the wake; the next turn plays and the episode banks
    assert "provider_error" in {row["kind"] for row in _ledger(run_dir("steward"))}
    pooled = {(r["model"], r["arm"]): r for r in report.build(runs)["pooled"]}
    assert pooled[("claude-sonnet-5", "team")]["invariant_met_rate"] == 1.0
    assert pooled[("claude-sonnet-5", "coordinator")]["invariant_met_rate"] == 0.0


def test_trip_coordinator_commits_and_team_defers(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    write_scripts(
        scripts,
        {"pa-steward": trip_commit("lh-alderwater", TWIN_ROOMS_KEPT), "default": QUIET},
    )
    runs = tmp_path / "runs"
    short = "twin_by_the_bathroom"
    assert (
        run_fake(
            runs, scenario=short, formations=("coordinator", "team"), scripts=scripts
        )
        == 0
    )
    rows = {
        r.formation: (r.ending, r.outcome)
        for r in outcomes.classify_wave(runs / f"{short}__claude-sonnet-5")
    }
    assert rows == {
        "coordinator": ("committed", "kept"),
        "team": ("no_decision", "deferred_empty"),
    }


def test_resume_skips_banked_episodes_under_the_waves_pin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wave is pinned to one revision, model and surface; another commit resumes it under the pin."""
    runs = tmp_path / "runs"
    pack = ("--pack-workspaces",)
    monkeypatch.setenv("EVAL_GIT_SHA", "a" * 40)
    assert (
        run_fake(
            runs,
            scenario=KESTREL,
            formations=("coordinator",),
            scripts=None,
            extra=pack,
        )
        == 0
    )
    wave = runs / f"{KESTREL}__claude-sonnet-5"
    sidecar = wave / "worlds" / f"conf_{KESTREL}_steward__e1.json"
    run_dir = wave / "runs" / f"conf_{KESTREL}_steward__claude-sonnet-5__e1"
    banked = sidecar.read_bytes()
    # --pack-workspaces tars the seat trees once the episode banks
    assert (run_dir / "workspaces.tar.gz").exists() and not (
        run_dir / "agents"
    ).exists()
    monkeypatch.setenv("EVAL_GIT_SHA", "b" * 40)
    assert (
        run_fake(
            runs,
            scenario=KESTREL,
            formations=("coordinator",),
            scripts=None,
            extra=pack,
        )
        == 0
    )
    assert sidecar.read_bytes() == banked  # skipped, not rerun
    assert json.loads((wave / "wave_config.json").read_text())["git_sha"] == "a" * 40
    resumes = (wave / "resumes.jsonl").read_text().splitlines()
    assert [json.loads(line) for line in resumes] == [
        {"pinned": "a" * 40, "resumed_with": "b" * 40}
    ]
    # a new formation extends the wave manifest; a changed runtime budget is refused
    assert run_fake(runs, scenario=KESTREL, formations=("team",), scripts=None) == 0
    config = json.loads((wave / "wave_config.json").read_text())
    assert set(config["manifest_sha256"]) == {"coordinator", "team"}
    with pytest.raises(SystemExit, match="incompatible wave manifest .*turn_timeout"):
        run_fake(
            runs,
            scenario=KESTREL,
            formations=("coordinator",),
            scripts=None,
            extra=("--turn-timeout", "60"),
        )
    # the readout unpacks the packed seat trees before it screens a non-commit
    assert len(report.collect(runs)[1]) == 2
    assert (run_dir / "agents").is_dir()


def test_print_info_prints_the_matrix_without_touching_disk(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("--print-info must not resolve credentials, pi, or start a runtime")

    for owner, name in (
        (run, "resolve_pi"),
        (run, "resolve_api_key"),
        (run, "_install_local_runtimes"),
        (run.local_runtime, "configure"),
        (run.food_run, "git_sha"),
    ):
        monkeypatch.setattr(owner, name, unexpected)
    argv = ["--scenario", KESTREL, "--formation", "coordinator", "team", "team_silent"]
    runs = tmp_path / "runs"
    assert (
        run.main([*argv, "--episodes", "2", "--print-info", "--runs-root", str(runs)])
        == 0
    )
    out = capsys.readouterr().out
    assert "6 episode(s)" in out and f"{KESTREL}/team_silent/e2" in out
    assert not runs.exists()
