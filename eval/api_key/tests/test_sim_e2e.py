"""Offline end-to-end on the simulated harness (the paper's instrument), with inspect's mock model.

Every paper cell banks a night in the pi harness's run-dir shape with its settings of record, report and check
read it, a banked night resumes (or refuses to), and the readers refuse a root whose pools mix instruments.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from _harness.readout import load_run
from _mitigations import NONE
from _mitigations import of as mitigation_of

from api_key import check, report
from api_key.tests.conftest import run_sim

LIMITS_OFF = 1_000_000
#: `stakes_100`, epoch 1, per (formation, arm): the cell, then instrument, burst, max_ahead, step budget,
#: first-pass limit, long-limit retry and generate timeout as recorded in `world/config.json`.
CELLS = {
    ("solo", NONE): (
        "token_cluster__stakes_100__solo__notax",
        ("hero", 6, 20, 800, 7200, None, 900),
    ),
    ("coordinator", NONE): (
        "token_cluster__stakes_100__steward__notax",
        ("hero", 6, 20, 800, 7200, None, 900),
    ),
    ("team", NONE): (
        "token_cluster__stakes_100__none__comms__notax",
        ("limits_off", LIMITS_OFF, LIMITS_OFF, 800, 7200, 28800, 900),
    ),
    ("team_silent", NONE): (
        "token_cluster__stakes_100__none__nocomms__notax",
        ("limits_off", LIMITS_OFF, LIMITS_OFF, 800, 7200, 28800, 900),
    ),
    ("team", "lead_value"): (
        "token_cluster__stakes_100__lead__mesh__portfolio__lead_only__g_m1__notax",
        ("limits_off", LIMITS_OFF, LIMITS_OFF, 850, 14400, None, 3600),
    ),
}
RECORDED = (
    "instrument",
    "burst",
    "max_ahead",
    "max_turns",
    "time_limit_s",
    "retry_time_limit_s",
    "generate_timeout_s",
)


@pytest.fixture(autouse=True)
def no_display(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EVAL_SIM_DISPLAY", "none")


def test_every_paper_cell_banks_its_settings_of_record_and_reads_clean(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs = tmp_path / "runs"
    assert (
        run_sim(runs, "--formation", "solo", "coordinator", "team", "team_silent") == 0
    )
    assert run_sim(runs, "--formation", "team", "--mitigation", "lead_value") == 0
    assert len(list(runs.iterdir())) == len(CELLS)
    for (formation, arm), (cell, settings) in CELLS.items():
        stamp = "" if arm == NONE else f"__mit-{arm}"
        run_dir = runs / f"{cell}{stamp}__claude-sonnet-5__e1__sim__fakemodel"
        loaded = load_run(run_dir)
        assert loaded is not None, run_dir.name
        summary, config, done = loaded
        assert (config["cell"], config["formation"], mitigation_of(config)) == (
            cell,
            formation,
            arm,
        )
        assert tuple(config[key] for key in RECORDED) == settings
        assert config["paper_instrument"] == config["instrument"] == done["instrument"]
        assert config["on_paper_instrument"] is True and config["off_paper"] == []
        assert config["auditor"] == "escalation" and config["knobs"] == {}
        assert config["dials"] == {
            "TOKEN_CLUSTER_EXEC": "mechanical",
            "TOKEN_CLUSTER_CLOCK": "no_time_tax",
        }
        assert (config["harness"], config["fake_model"], config["target_effort"]) == (
            "sim",
            True,
            "none",
        )
        assert config["harness_env"]["BURST"] == str(settings[1])
        assert config["harness_env"]["TARGET_REASONING"] == "none"
        assert float(summary["clock"]) >= float(summary["deadline_min"])
        assert not summary.get("unwound") and not summary.get("driver_step_capped")
        # the provider-error scan ran over the banked log and found the stand-in's clean calls
        assert done["rule_t_scanned"] is True and done["ok_calls"] > 0
        assert done["rule_t_lost_turns"] == 0 and done["failed_calls"] == 0
        assert done["attempts"] == 1
        # the world sidecar the paper's readers read sits beside the eval log
        assert (run_dir / "logs" / "worlds" / f"{cell}__e1.json").exists()
    rows = {(r["formation"], mitigation_of(r)): r for r in report.collect(runs)}
    assert set(rows) == set(CELLS)
    assert all(r["roster_ok"] and report.is_clean(r) for r in rows.values())
    # participation is a team readout; the lead's own actions never count as a user's
    assert rows[("solo", NONE)]["participation"] is None
    assert rows[("team", "lead_value")]["participation"] == 0.0
    # check.py compares every cell and its pooled row; one episode is WARN, never MISS
    capsys.readouterr()
    assert check.main([str(runs)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("reference: reference.json (paper")
    assert "WARN stakes_100 team claude-sonnet-5 [mitigation lead_value]: run" in out
    assert "(10 compared; 0 skipped)" in out and "HARNESS" not in out


def test_a_non_anthropic_target_records_its_provider_and_reasoning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    runs = tmp_path / "runs"
    assert run_sim(runs, "--formation", "team", "--model", "qwen/qwen3.8-max") == 0
    (run_dir,) = runs.iterdir()
    loaded = load_run(run_dir)
    assert loaded is not None
    config = loaded[1]
    assert (config["provider"], config["target_effort"]) == ("openrouter", "minimal")
    # target_model sends no serving option
    assert config["target_serving"] == "standard"
    (row,) = report.collect(runs)
    assert row["model"] == "qwen3.8-max"


def test_a_banked_night_is_skipped_on_resume_unless_recorded_otherwise(
    tmp_path: Path,
) -> None:
    runs = tmp_path / "runs"
    assert run_sim(runs, "--formation", "team") == 0
    (run_dir,) = runs.iterdir()
    stamp = (run_dir / "DONE.json").read_text()
    assert run_sim(runs, "--formation", "team") == 0
    assert (run_dir / "DONE.json").read_text() == stamp
    # a run dir recorded under another scheduler never DONE-skips
    path = run_dir / "world" / "config.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "instrument": "hero"}))
    with pytest.raises(SystemExit, match="different configuration"):
        run_sim(runs, "--formation", "team")


@pytest.fixture(scope="module")
def two_nights(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("two_nights") / "runs"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("EVAL_SIM_DISPLAY", "none")
        assert run_sim(root, "--formation", "coordinator", "--episodes", "2") == 0
    return root


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"harness": "pi"}, "mixes harnesses"),
        ({"instrument": "limits_off"}, "mixes simulated-harness instruments"),
        (  # a record from other code (an `off_paper` reason) never pools with the paper's
            {"on_paper_instrument": False, "off_paper": ["TARGET_REASONING=high"]},
            "instruments or settings within a pool .*TARGET_REASONING=high",
        ),
    ],
)
def test_the_readers_refuse_a_pool_that_mixes_harnesses_or_settings(
    two_nights: Path, tmp_path: Path, change: dict[str, object], message: str
) -> None:
    root = shutil.copytree(two_nights, tmp_path / "runs")
    path = next(root.glob("*__e2__sim__fakemodel")) / "world" / "config.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), **change}))
    with pytest.raises(SystemExit, match=message):
        report.collect(root)
    with pytest.raises(SystemExit, match=message):
        check.main([str(root)])
