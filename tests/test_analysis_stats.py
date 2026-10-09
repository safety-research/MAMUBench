"""analysis/stats.py on offline roots: an api_key stand-in run (`run.py --fake-model`) and merge_queue's paper fixtures.

Each root goes through its environment's report.py; the combined tables carry the reports' rows unchanged, with a
`root` column after `env`, a missing root is skipped with a note, and stats.md holds the pooled headline.
"""

from __future__ import annotations

import csv
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "analysis" / "stats.py"
MQ_FIXTURES = ROOT / "eval" / "merge_queue" / "tests" / "fixtures" / "paper_runs"


def offline_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.endswith("API_KEY")}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def stats(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(STATS), *args]
    return subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, env=offline_env(), timeout=600
    )


def test_stats_combines_each_environments_report(tmp_path: Path) -> None:
    (tmp_path / "empty.env").write_text("")
    runs = tmp_path / "api_key_runs"
    plan = "api_key --backend local --fake-model --model claude-opus-5 --scenario stakes_80"
    plan += " --formation coordinator team --episodes 2"
    launch = [
        sys.executable,
        str(ROOT / "run.py"),
        *plan.split(),
        "--runs-root",
        str(runs),
    ]
    launch += ["--env-file", str(tmp_path / "empty.env")]
    proc = subprocess.run(
        launch, cwd=ROOT, capture_output=True, text=True, env=offline_env(), timeout=900
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]

    out = tmp_path / "out"
    plot = importlib.util.find_spec("matplotlib") is not None
    args = [
        f"--roots=api_key={runs}",
        f"--roots=merge_queue={MQ_FIXTURES}",
        "--out-dir",
        str(out),
    ]
    args += [
        f"--roots=clinic={tmp_path / 'missing'}",
        f"--roots=personal_assistant={tmp_path / 'missing'}",
    ]
    proc = stats(*args, *(["--plot"] if plot else []))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (
        "clinic: no runs at" in proc.stdout
        and "personal_assistant: no runs at" in proc.stdout
    )

    combined = rows(out / "stats.csv")
    assert list(combined[0])[:3] == ["env", "root", "scenario"]
    for env, root in (("api_key", runs.name), ("merge_queue", MQ_FIXTURES.name)):
        own = rows(out / env / root / "scores.csv")
        assert own and [r for r in combined if r["env"] == env] == [
            {"env": env, "root": root, **r} for r in own
        ]
        own = rows(out / env / root / "contrasts.csv")
        assert [r for r in rows(out / "contrasts.csv") if r["env"] == env] == [
            {"env": env, "root": root, **r} for r in own
        ]
    md = (out / "stats.md").read_text()
    assert (
        "| api_key | api_key_runs | POOLED (1 scenarios) | claude-opus-5 | coordinator | none | 2 |"
        in md
    )
    assert (
        "| merge_queue | paper_runs | volunteer_p1 | claude-opus-5 | team |" in md
    )  # it pools none here
    assert (out / "stats.png").is_file() == plot


def test_stats_with_no_runs_writes_nothing(tmp_path: Path) -> None:
    missing = [
        f"--roots={env}={tmp_path / 'none'}"
        for env in ("api_key", "clinic", "personal_assistant")
    ]
    proc = stats(
        *missing,
        f"--roots=merge_queue={tmp_path / 'none'}",
        "--out-dir",
        str(tmp_path / "out"),
    )
    assert proc.returncode == 1 and "no runs found" in proc.stdout
    assert not (tmp_path / "out").exists()


def test_stats_solo_only_roots_with_one_basename(tmp_path: Path) -> None:
    """Two roots named `results` keep their own rows and dirs; a table no report fills keeps its header."""
    (tmp_path / "empty.env").write_text("")
    first = tmp_path / "a" / "results"
    plan = "api_key --backend local --fake-model --model claude-opus-5 --scenario stakes_80"
    plan += " --formation solo --episodes 1"
    launch = [
        sys.executable,
        str(ROOT / "run.py"),
        *plan.split(),
        "--runs-root",
        str(first),
    ]
    launch += ["--env-file", str(tmp_path / "empty.env")]
    proc = subprocess.run(
        launch, cwd=ROOT, capture_output=True, text=True, env=offline_env(), timeout=900
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    second = tmp_path / "b" / "results"
    shutil.copytree(first, second)

    out = tmp_path / "out"
    proc = stats(
        f"--roots=api_key={first}",
        f"--roots=api_key={second}",
        f"--roots=api_key={first}",  # read once
        *(
            f"--roots={env}={tmp_path / 'none'}"
            for env in ("clinic", "personal_assistant")
        ),
        f"--roots=merge_queue={tmp_path / 'none'}",
        "--out-dir",
        str(out),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "labelled results-2" in proc.stdout
    combined = rows(out / "stats.csv")
    for label in ("results", "results-2"):
        own = rows(out / "api_key" / label / "scores.csv")
        assert own and [r for r in combined if r["root"] == label] == [
            {"env": "api_key", "root": label, **r} for r in own
        ]
    assert {r["root"] for r in combined} == {"results", "results-2"}

    own_header = (
        (out / "api_key" / "results" / "contrasts.csv").read_text().splitlines()
    )
    assert own_header and len(own_header) == 1  # solo only: no contrast, header alone
    header = (out / "contrasts.csv").read_text().splitlines()
    assert len(header) == 1
    assert header[0].split(",")[:2] == ["env", "root"] and header[0].endswith(
        own_header[0].removeprefix("env,")
    )


def test_missing_default_root_names_its_siblings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = importlib.util.spec_from_file_location("stats", STATS)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "REPO", tmp_path)
    runs = tmp_path / "eval" / "api_key" / "runs"
    (runs / "results_fake").mkdir(parents=True)
    note: str = mod.missing_note("api_key", runs / "results")
    assert note == (
        "api_key: no runs at eval/api_key/runs/results; skipped"
        " (eval/api_key/runs holds results_fake: --roots api_key=DIR reads one)"
    )
    assert mod.missing_note("api_key", tmp_path / "x") == (
        "api_key: no runs at x; skipped"  # not a default root: no list
    )
