"""One episode's drive, offline (no pi, no CI venv, no LLM call): what `_drive.main` and `drive_episode` do.

- resume: a run dir banked by another instrument, or with no configuration provenance, is refused;
- a failed drive keeps its `config.json` (written before any fixture or model work) and removes every seat's
  pi auth file, even after a partial startup failure;
- the requester voicer's system prompt of each topology is the paper's (the sha256 of the research code's
  `voicer._system_prompt`, the version the paper's runs imported);
- `_drive.main`, with the pi probe, the CI bootstrap and `drive_episode` stubbed, hands the driver the planned
  episode, banks `DONE.json` and resume-skips it; a signal mid-drive leaves `INCOMPLETE.json`;
- one trimmed REAL drive (`drive_episode` itself, one working round, a fake pi from `tests/fixtures`, the test
  interpreter as the CI python) per seat shape (solo, coordinator, silent team, team, the lead arms' fifth
  seat), then the Modal launcher's packing of the run dir, interrupted attempts included.
"""

from __future__ import annotations

import functools
import hashlib
import json
import sys
import tarfile
from pathlib import Path
from typing import Any, NoReturn

import anthropic
import pytest

from merge_queue import _drive
from merge_queue import run as mq_run
from merge_queue._drive import validate_existing_config
from merge_queue.runtime import driver, process, resume, voicer
from merge_queue.scenarios._cells import TOPOLOGIES, Cell
from merge_queue.scenarios._context import build_cell

FAKE_PI = Path(__file__).resolve().parent / "fixtures" / "fake_pi.py"
#: sha256 of the research code's voicer._system_prompt(topology), rendered offline
VOICER_SHA256 = {
    "no_captain": "116d01efc105fd243896e1bb2058d2790edb1529c2812b3d07e145007ba108ef",
    "live_captain": "1c71838f47715a23e8102a88886a69e9767cf532854d45eff26961884eefb6a4",
}
KEY_ENV = "MQ_TEST_TARGET_KEY"
VOICER_KEY_ENV = "MQ_TEST_VOICER_KEY"


def _argv(tmp_path: Path, scenario: str, formation: str, arm: str) -> list[str]:
    argv = [
        *("--scenario", scenario, "--formation", formation, "--epoch", "2"),
        *(
            "--model",
            "claude-opus-5",
            "--model-slug",
            "opus5",
            "--provider",
            "anthropic",
        ),
        *("--key-env", KEY_ENV, "--voicer-key-env", VOICER_KEY_ENV),
        *("--thinking", "off", "--attempts", "1"),
        *(
            "--runs-root",
            str(tmp_path / "runs"),
            "--agent-roots-base",
            str(tmp_path / "roots"),
        ),
        *("--pi-cmd", str(tmp_path / "pi")),
    ]
    return argv + (["--mitigation", arm] if arm != "none" else [])


class _FakeMessages:
    def __init__(self, systems: list[str]) -> None:
        self._systems = systems

    def create(self, **kwargs: Any) -> Any:
        self._systems.append(str(kwargs["system"]))
        block = type("Block", (), {"type": "text", "text": '{"reply": null}'})()
        return type("Response", (), {"content": [block]})()


class _FakeAnthropic:
    """`anthropic.Anthropic` for the voicer: records every system prompt sent, replies `{"reply": null}`."""

    systems: list[str] = []

    def __init__(self, **_kwargs: Any) -> None:
        self.messages = _FakeMessages(type(self).systems)


def _pi_is_fine(*, pi_bin: str = "pi") -> None:
    """`process.validate_pi_runtime` stand-in (the host's Node and pi versions are not under test)."""
    del pi_bin


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Stub the pi version probe, the CI bootstrap and the voicer's client; returns the systems sent."""
    monkeypatch.setenv(KEY_ENV, "sk-offline-target")
    monkeypatch.setenv(VOICER_KEY_ENV, "sk-offline-voicer")
    monkeypatch.setattr(process, "validate_pi_runtime", _pi_is_fine)
    monkeypatch.setattr(_drive, "ensure_ci_python", lambda: None)
    systems: list[str] = []
    monkeypatch.setattr(_FakeAnthropic, "systems", systems)
    monkeypatch.setattr(anthropic, "Anthropic", _FakeAnthropic)
    return systems


# --- resume and teardown ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("saved", "banked", "record", "error"),
    [
        (
            {"thinking": "off"},
            None,
            {"thinking": "medium"},
            "thinking.*new --runs-root",
        ),
        # an episode recorded without a key the current record carries
        ({}, None, {"scenario_sha256": "current"}, "scenario_sha256.*new --runs-root"),
        # a Git label change alone does not alter the instrument
        (
            {"scenario_sha256": "same", "commit": "old"},
            None,
            {"scenario_sha256": "same", "commit": "new"},
            None,
        ),
        # recovery never stamps the current configuration onto an unversioned episode
        (
            None,
            "DONE.json",
            {"scenario_sha256": "current"},
            "no configuration provenance",
        ),
        (
            None,
            "episode.json",
            {"scenario_sha256": "current"},
            "no configuration provenance",
        ),
    ],
)
def test_resume_refuses_an_episode_of_another_instrument(
    tmp_path: Path,
    saved: dict[str, str] | None,
    banked: str | None,
    record: dict[str, str],
    error: str | None,
) -> None:
    if saved is not None:
        (tmp_path / "config.json").write_text(json.dumps(saved))
    if banked is not None:
        (tmp_path / banked).write_text("{}")
    if error is None:
        validate_existing_config(tmp_path, record)
        return
    with pytest.raises(SystemExit, match=error):
        validate_existing_config(tmp_path, record)
    assert saved is not None or not (tmp_path / "config.json").exists()


@pytest.mark.parametrize("deidentified", [True, False])
def test_a_failed_drive_keeps_its_record_and_drops_the_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, deidentified: bool
) -> None:
    run_dir = tmp_path / "runs" / "episode"
    agent_root = tmp_path / "work" if deidentified else None
    seats = [
        root / "agents" / "agent-201" / "home" / ".pi" / "agent"
        for root in (run_dir, agent_root)
        if root is not None
    ]

    def fail_fixture(*_args: object, **_kwargs: object) -> NoReturn:
        for seat in seats:
            seat.mkdir(parents=True)
            (seat / "auth.json").write_text("dummy-credential-for-regression-only")
            (seat / "settings.json").write_text("keep")
        raise RuntimeError("fixture failed")

    monkeypatch.setattr(driver, "build_fixture", fail_fixture)
    record = {"scenario_sha256": "current-scenario", "model": "claude-sonnet-5"}
    with pytest.raises(RuntimeError, match="fixture failed"):
        driver.drive_episode(
            run_dir=run_dir,
            agent_root=agent_root,
            config=build_cell(Cell("oversub", "none", True), 1),
            api_key="unused",
            run_record=record,
        )
    assert json.loads((run_dir / "config.json").read_text()) == record
    validate_existing_config(run_dir, record)
    assert not (run_dir / driver.LEASE_NAME).exists()
    for seat in seats:
        assert not (seat / "auth.json").exists()
        assert (seat / "settings.json").read_text() == "keep"


# --- the voicer and _drive.main ------------------------------------------------------------------------


def test_the_voicer_prompts_are_the_papers() -> None:
    for topology in TOPOLOGIES:
        text = voicer.system_prompt(topology)
        assert hashlib.sha256(text.encode()).hexdigest() == VOICER_SHA256[topology]
    with pytest.raises(ValueError, match="unknown topology 'scripted_captain'"):
        voicer.system_prompt("scripted_captain")


class _StubDrive:
    """`driver.drive_episode` stand-in: records its kwargs, makes the run dir, returns a complete episode."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> driver.EpisodeResult:
        self.calls.append(kwargs)
        run_dir: Path = kwargs["run_dir"]
        run_dir.mkdir(parents=True, exist_ok=True)
        seats = tuple(driver.seat_agents_md(kwargs["config"]))
        return driver.EpisodeResult(
            scenario=kwargs["config"].name,
            model=kwargs["model"],
            run_dir=run_dir,
            rounds=1,
            sim_minute=0,
            wall_clock_seconds=0.0,
            crashed_agents=(),
            turn_counts=dict.fromkeys(seats, 1),
            session_counts=dict.fromkeys(seats, 1),
            oracle={},
            world={
                "cutoff_reached": True,
                "terminal_status": dict.fromkeys(seats, "debriefed"),
                "release_value": 0,
                "oracle_value": 0,
                "merged_prs": [],
            },
            events_sha256="0" * 64,
            missed_wakes=dict.fromkeys(seats, 0),
            wake_orders=(),
        )


@pytest.mark.parametrize("arm", ["none", "lead_cut_line"])
def test_drive_main_hands_the_driver_the_planned_episode(
    arm: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, offline: list[str]
) -> None:
    """The plan's config, RELEASING.md, record and wake seed, the paper's launch settings, the cell's voicer."""
    argv = _argv(tmp_path, "volunteer_p3", "team", arm)
    argv += ["--no-voicer"] if arm != "none" else []
    plan = _drive.plan_episode(_drive.parse_args(argv))
    stub = _StubDrive()
    monkeypatch.setattr(driver, "drive_episode", stub)
    assert _drive.main(argv) == 0
    (call,) = stub.calls
    assert (call["config"], call["run_dir"], call["run_record"]) == (
        plan.config,
        plan.run_dir,
        plan.record,
    )
    assert plan.releasing is not None and call["releasing_md"] == plan.releasing
    assert call["wake_seed"] == resume.wake_seed(plan.cell.scenario, plan.world_epoch)
    assert (call["thinking"], call["pi_bin"], call["api_key"], call["api_key_var"]) == (
        "off",
        str(tmp_path / "pi"),
        "sk-offline-target",
        "ANTHROPIC_API_KEY",
    )
    assert call["defer_voicer"] and call["steal_stale_lease"]
    if arm == "none":
        assert call["voicer"].system == voicer.system_prompt("no_captain")
    else:
        assert call["voicer"] is None
    done = json.loads((plan.run_dir / "DONE.json").read_text())
    assert done["infrastructure_pass"] and done["run_dir"] == str(plan.run_dir)
    assert json.loads((plan.run_dir / "config.json").read_text()) == plan.record
    assert offline == []  # nothing was voiced: the stub drove no turn
    # the rerun resume-skips the banked episode
    assert _drive.main(argv) == 2 and len(stub.calls) == 1


def test_an_interrupted_attempt_leaves_a_failure_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, offline: list[str]
) -> None:
    """A signal mid-drive (Modal's preemption) writes INCOMPLETE.json before it propagates; the rerun counts it."""
    argv = _argv(tmp_path, "oversub", "team", "none")
    plan = _drive.plan_episode(_drive.parse_args(argv))

    def preempted(**kwargs: Any) -> driver.EpisodeResult:
        kwargs["run_dir"].mkdir(parents=True, exist_ok=True)
        raise KeyboardInterrupt

    monkeypatch.setattr(driver, "drive_episode", preempted)
    with pytest.raises(KeyboardInterrupt):
        _drive.main(argv)
    incomplete = json.loads((plan.run_dir / "INCOMPLETE.json").read_text())
    assert incomplete["interrupted"] and not incomplete["infrastructure_pass"]
    assert incomplete["failures"] == [f"attempt 1: {_drive.INTERRUPTED}"]
    assert json.loads((plan.run_dir / "config.json").read_text()) == plan.record
    # the restarted container's drive quarantines the lost attempt (as `driver.prepare_run_dir` does) and banks
    stub = _StubDrive()

    def restarted(**kwargs: Any) -> driver.EpisodeResult:
        quarantine = plan.run_dir / ".attempt1.failed"
        quarantine.mkdir()
        (plan.run_dir / "INCOMPLETE.json").rename(quarantine / "INCOMPLETE.json")
        return stub(**kwargs)

    monkeypatch.setattr(driver, "drive_episode", restarted)
    assert _drive.main(argv) == 0
    done = json.loads((plan.run_dir / "DONE.json").read_text())
    assert done["infrastructure_pass"] and done["quarantined_attempts"] == 1
    assert not (plan.run_dir / "INCOMPLETE.json").exists()


# --- one trimmed real drive per seat shape, and the Modal launcher's packing -----------------------------


def _pack(runs_root: Path, scenario: str, formation: str, arm: str = "none") -> None:
    import modal_app  # noqa: PLC0415 - the launcher (and `modal`) only where a test packs

    modal_app._pack_merge_queue_workspaces(  # pyright: ignore[reportPrivateUsage]
        runs_root, scenario, formation, 2, "claude-opus-5", arm
    )


@pytest.mark.parametrize(
    ("scenario", "formation", "arm"),
    [
        ("volunteer_p3", "solo", "none"),
        ("volunteer_p1", "coordinator", "none"),
        ("oversub", "team_silent", "none"),
        ("baseline_tight", "team", "charter"),
        ("oversub", "team", "lead_cut_line"),
    ],
)
def test_a_real_drive_builds_every_seat(
    scenario: str,
    formation: str,
    arm: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    offline: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`drive_episode` itself, one working round: fixture + RELEASING.md, shims, every seat, voicer, packing."""
    pi = tmp_path / "pi"
    pi.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_PI}" "$@"\n')
    pi.chmod(0o755)
    # the test interpreter stands in for the pinned CI venv (it has pytest, not the Jinja deps: the seeded
    # head-check logs capture an import error, which only changes their display text)
    monkeypatch.setenv("MERGE_QUEUE_ALLOW_CHECKOUT_CI_PYTHON", "1")
    monkeypatch.setattr(driver, "validate_ci_python", lambda: Path(sys.executable))
    monkeypatch.setattr(
        driver,
        "drive_episode",
        functools.partial(driver.drive_episode, max_working_rounds=1),
    )
    argv = _argv(tmp_path, scenario, formation, arm)
    plan = _drive.plan_episode(_drive.parse_args(argv))
    # one round never reaches the freeze, so the structural gate fails only on the cutoff and its debrief
    assert _drive.main(argv) == 1
    assert "driver error" not in capsys.readouterr().out
    run_dir = plan.run_dir
    incomplete = json.loads((run_dir / "INCOMPLETE.json").read_text())
    assert incomplete["failures"] == [
        "cutoff not reached",
        "post-cutoff debrief did not render for every agent",
    ]
    briefs = driver.seat_agents_md(plan.config)
    assert len(briefs) == plan.seats
    episode = json.loads((run_dir / "episode.json").read_text())
    assert episode["crashed_agents"] == []
    assert (
        episode["session_counts"] == episode["turn_counts"] == dict.fromkeys(briefs, 1)
    )
    lead = plan.config.queue_policy.captain_actor_id
    live_root = resume.agent_root(
        (tmp_path / "roots").resolve(), plan.run_name
    ).resolve()
    # every seat ran in its own workspace with its brief (the lead in node/ops-notes, context files on)
    for seat, brief in briefs.items():
        seen = json.loads((run_dir / "agents" / seat / "seat.json").read_text())
        workspace = Path(seen["cwd"]).resolve().relative_to(live_root)
        assert seen["agents_md"] and seen["argv"][-2:] == ["--thinking", "off"], seat
        if seat == lead:
            assert workspace == Path("node/ops-notes")
            assert "--no-context-files" not in seen["argv"]
        elif formation in ("solo", "coordinator"):
            assert workspace == Path("node/workspaces")
        else:
            assert workspace.parent == Path("node/workspaces") and seen["releasing_md"]
        assert (run_dir / workspace / "AGENTS.md").read_text() == brief
    # every clone carries the paper world's RELEASING.md (the arm's variant)
    clones = sorted((run_dir / "node" / "workspaces").glob("jinja-pr*/RELEASING.md"))
    assert len(clones) == 4 and plan.releasing is not None
    assert {path.read_text(encoding="utf-8") for path in clones} == {plan.releasing}
    # the voicer answered every owner turn with the cell topology's prompt (the lead is never voiced)
    owners = sorted(seat for seat in briefs if seat != lead)
    assert offline == [voicer.system_prompt(plan.cell.topology)] * len(owners)
    rows = [
        json.loads(line) for line in (run_dir / "voicer.jsonl").read_text().splitlines()
    ]
    assert sorted(r["agent_id"] for r in rows if r["decision"] == "decline") == owners
    # no seat's key survives the episode
    assert not [*run_dir.rglob("auth.json"), *(tmp_path / "roots").rglob("auth.json")]
    # the Modal launcher packs the seat trees of the run dir it names
    _pack(run_dir.parent, scenario, formation, arm)
    assert (run_dir / "workspaces.tar.gz").is_file()
    assert not (run_dir / "agents").exists() and not (run_dir / "node").exists()


def test_packing_keeps_every_interrupted_attempt(tmp_path: Path) -> None:
    """An interrupted container's own workspaces.tar.gz is unpacked into the new archive, one level deep.

    A truncated one (a killed container) is kept as a file and never fails the teardown (which would retain
    the claim).
    """
    runs_root = tmp_path / "runs"
    run_dir = runs_root / mq_run.run_dir_name("oversub", "team", "claude-opus-5", 2)
    whole, truncated = run_dir / ".attempt1.failed", run_dir / ".attempt2.failed"
    old = tmp_path / "old"
    (old / "agents" / "owner1" / "sessions").mkdir(parents=True)
    (old / "agents" / "owner1" / "sessions" / "s.jsonl").write_text('{"usage": 1}\n')
    (old / "node").mkdir()
    (old / "node" / "big.bin").write_bytes(bytes(range(256)) * 4096)
    for quarantine in (whole, truncated):
        quarantine.mkdir(parents=True)
        (quarantine / "INCOMPLETE.json").write_text("{}\n")
        with tarfile.open(quarantine / "workspaces.tar.gz", "w:gz") as tar:
            for name in ("agents", "node"):
                tar.add(old / name, arcname=name)
    data = (truncated / "workspaces.tar.gz").read_bytes()
    (truncated / "workspaces.tar.gz").write_bytes(data[: len(data) // 2])
    (run_dir / "agents" / "owner1" / "sessions").mkdir(parents=True)
    (run_dir / "agents" / "owner1" / "sessions" / "t.jsonl").write_text(
        '{"usage": 2}\n'
    )
    _pack(runs_root, "oversub", "team")
    with tarfile.open(run_dir / "workspaces.tar.gz", "r:gz") as tar:
        members = {m.name: m for m in tar.getmembers()}
        inner = tar.extractfile(
            members[".attempt1.failed/agents/owner1/sessions/s.jsonl"]
        )
        assert inner is not None and inner.read() == b'{"usage": 1}\n'
    assert {
        "agents/owner1/sessions/t.jsonl",
        ".attempt1.failed/INCOMPLETE.json",
        ".attempt1.failed/node/big.bin",
        ".attempt2.failed/INCOMPLETE.json",
        ".attempt2.failed/workspaces.tar.gz",
    } <= set(members)
    assert ".attempt1.failed/workspaces.tar.gz" not in members
    assert ".attempt2.failed/node/big.bin" not in members
    assert not whole.exists() and not (run_dir / "agents").exists()
