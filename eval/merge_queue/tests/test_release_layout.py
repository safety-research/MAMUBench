"""Release-layout run dirs end to end, and the paper's briefs and seeds from the launcher's `--print-info`.

The merge queue has no offline stand-in, so the readers are proven on real episodes of the paper's corpus
re-laid as this runner banks them (`tests/release_layout.py`, which asserts that the release plans the world
each research episode ran): each as a Modal-packed run dir (`workspaces.tar.gz`) and as a local one. They check
that `report.py` reads each release run dir exactly as the research dir it came from, rule T included, and
that `check.py` compares every clean cell with the paper instrument of its arm.

`--print-info --render-to DIR` plans the paper's seeds (the run names of the paper's episodes, pinned by digest)
and renders every arm's AGENTS.md byte for byte equal to the briefs of the paper's own oversub e1 run dirs
(pinned by sha256); the charter has no brief of its own in the paper and is pinned against the one it derives
from. The formation matrix plans exactly the paper's 480 episodes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from merge_queue import check as check_mod
from merge_queue import mitigations, report
from merge_queue import run as mq_run
from merge_queue._drive import main as drive_main
from merge_queue.mitigations.clauses import (
    IDEA_SEAT_HEADING,
    IDEAS,
    PRIORITY_HEADING,
    SEAT_HEADING,
)
from merge_queue.scenarios._cells import Cell
from merge_queue.scenarios._context import build_cell
from merge_queue.tests import release_layout as rl

REPO_ROOT = Path(__file__).resolve().parents[3]
#: the paper's repair-loop seeds (world epochs) per scenario = `--episodes 5` of each scenario
LOOP_SEEDS = {
    "oversub": [1, 2, 3, 4, 5],
    "volunteer_p1": [1, 4, 7, 10, 13],
    "volunteer_p3": [3, 6, 9, 12, 15],
}
MODELS = {"opus5": "claude-opus-5", "sonnet5": "claude-sonnet-5"}
#: seeds of the launcher's plan that the paper's record does not hold (arm, model slug) -> run names: Opus 5
#: explicit prioritization's three undrained seeds.
UNFROZEN = {
    ("priorities", "opus5"): {
        "oversub__none__comms__opus5__e5",
        "volunteer__none__comms__opus5__e13",
        "volunteer__none__comms__opus5__e12",
    },
}
#: (arm, model slug) -> (count, sha256 of the sorted research run names) of the paper's episodes of the arm on
#: the three reported scenarios (the research run-dir grammar: `<cell>__<slug>__e<world epoch>`).
PAPER_ARM_EPISODES: dict[tuple[str, str], tuple[int, str]] = {
    ("lead_cut_line", "opus5"): (
        15,
        "2608406cdad04b50c662ce885b3cc4e6a5cf302b1c8f3cee1340a09c8efc018f",
    ),
    ("lead_cut_line", "sonnet5"): (
        15,
        "e7e795fb98b32bb0d9c2591f58c7f3b87995e5666790b19a3e418608d65983ef",
    ),
    ("priorities", "opus5"): (
        12,
        "f21220f3311b1e74ccf53a550912167e1187b77cfe6076405004bf6974ab82d9",
    ),
    ("priorities", "sonnet5"): (
        15,
        "4e4b7d2261430cc23ab950295737b7ab4a92991a156f2a7628a21c940cba5bf7",
    ),
    ("charter_stakes", "opus5"): (
        15,
        "0aeaff930f87fe55b76664e113d1b272bafa472064be426f1bc8c0e7c5afd25e",
    ),
    ("charter_stakes", "sonnet5"): (
        15,
        "4e4b7d2261430cc23ab950295737b7ab4a92991a156f2a7628a21c940cba5bf7",
    ),
    ("charter", "opus5"): (
        60,
        "328fe19430c7ef83b854a6705f35939790699f56207d118237feed7d430a7c25",
    ),
    ("charter", "sonnet5"): (
        60,
        "573ac9d99a3b49b078ba1651ae33f16774a9a30722cbed2d26d2fcda39da5be6",
    ),
}
#: model slug -> sha256 of the sorted run names of the paper's 240 formation episodes (solo, coordinator,
#: silent team, team on the three reported scenarios, 20 seeds each).
PAPER_FORMATION_EPISODES = {
    "opus5": "69f141d1192d8e61d9e242cbda8c8f70ce46b64f5cf862a39b0f1694e5244d7d",
    "sonnet5": "0c39d1eae8ef89d3c3a9e044e4902671a20531a7d881becc92317f5b94a4af8e",
}
#: the sha256 of the briefs in the paper's oversub e1 run dirs, per (research rung, seat)
PAPER_BRIEFS = {
    ("i1_cut_line_first_post", "release-captain"): (
        "e29c1b6201a4d9b0241ea229c5de25b92a132d6e27c55d2f3006dd9b9e48634a"
    ),
    ("i1_cut_line_first_post", "agent-201"): (
        "c5eb7e08477e3931f7e62b9f69ddeec70137f34d264440d58fe8ef0e2551ad4d"
    ),
    ("i1_last_stands_down", "agent-201"): (
        "9f23650eb0bf2da75b3e66af6dea15c206d83914f9479085498f9bfb240dcc6c"
    ),
    ("i1_value_is_stakes", "agent-201"): (
        "421794cda5575a3aca04966779b65d5643467a76f8d929cb0e398302ad988c32"
    ),
}
#: the two fixture episodes the paper dropped under rule T: (rung, model slug, scenario, world epoch) -> turns
RULE_T = {
    ("mesh-comms", "sonnet5", "volunteer_p3", 45): 7,
    ("r9_crew", "opus5", "volunteer_p3", 24): 1,
}
OWNERS = {"agent-201", "agent-202", "agent-203", "agent-204"}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _names_digest(names: set[str]) -> str:
    return _sha256("\n".join(sorted(names)))


def _oversub_e1_brief(key: str, seat: str) -> str:
    """A repair-loop idea's oversub e1 brief (`clauses.IDEAS[key]`), built as the arm builds it."""
    idea = IDEAS[key]
    topology = "live_captain" if idea.captained else "no_captain"
    config = build_cell(
        Cell("oversub", "none", True, topology=topology), 1, flags=idea.flags
    )
    text = (
        config.captain_agents_md
        if seat == "release-captain"
        else dict(config.agents_md)[seat]
    )
    assert text is not None
    return text


@pytest.fixture(scope="module")
def laid_out(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """This eval's paper run dirs laid out packed and local, each in its own runs root."""
    root = tmp_path_factory.mktemp("release_runs")
    for layout in ("packed", "local"):
        rl.lay_out_all(root / layout, pack=layout == "packed")
    return {layout: root / layout for layout in ("packed", "local")}


def _by_episode(rows: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    return {(r["rung"], r["model"], r["scenario"], r["world_epoch"]): r for r in rows}


@pytest.mark.parametrize("layout", ["packed", "local"])
def test_report_reads_a_release_run_dir_as_the_research_dir(
    laid_out: dict[str, Path], layout: str
) -> None:
    release = _by_episode(report.collect(laid_out[layout]))
    source = _by_episode(report.collect(rl.FIXTURES))
    assert release.keys() == source.keys() and len(release) == 8
    skip = {"run", "commit", "provider"}
    for key, row in release.items():
        assert {k: v for k, v in row.items() if k not in skip} == {
            k: v for k, v in source[key].items() if k not in skip
        }, key
        assert row["provider"] == "anthropic" and row["commit"] == mq_run.git_commit()
        turns = RULE_T.get(
            (row["rung"], row["model_slug"], row["scenario"], row["world_epoch"])
        )
        assert (row["excluded"] == "rule_t") == (turns is not None), key
        assert turns is None or row["turns_ended_by_error"] == turns


def test_report_and_check_run_on_release_run_dirs(
    laid_out: dict[str, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs_root = laid_out["packed"]
    assert (
        report.main([str(runs_root), "--out-dir", str(tmp_path), "--draws", "20"]) == 0
    )
    written = {p.name for p in tmp_path.iterdir()}
    assert written == {
        "episodes.csv",
        "scenarios.csv",
        "summary.txt",
        "summary.json",
        "paper_cells.csv",
        "paper_deltas.csv",
        "paper_means.csv",
        "scores.csv",
        "contrasts.csv",
        "results.md",
    }
    with (tmp_path / "paper_cells.csv").open(newline="") as handle:
        cells = list(csv.DictReader(handle))
    assert tuple(cells[0]) == report.RESEARCH_CELL_COLUMNS
    # six clean episodes (the two rule-T episodes are dropped), one per cell
    clean = [r for r in report.collect(runs_root) if report.is_clean(r)]
    assert len(clean) == 6
    assert sorted(
        (c["rung"], c["model"], c["scenario"], c["n"]) for c in cells
    ) == sorted((r["rung"], r["model_slug"], r["scenario"], "1") for r in clean)
    text = (tmp_path / "summary.txt").read_text()
    assert "[paper]" in text and "rule-T dropped 1" in text
    capsys.readouterr()
    assert check_mod.main([str(runs_root)]) in (0, 1)
    verdicts = re.findall(
        r"^(PASS|WARN|MISS) (\S+) (\S+) (\S+)( \[mitigation (\S+)\])?: .* vs (\S+) \(n=",
        capsys.readouterr().out,
        re.M,
    )
    compared = {
        (s, f, m, arm or "none"): inst for _v, s, f, m, _a, arm, inst in verdicts
    }
    for row in clean:
        arm = row["mitigation"]
        instrument = compared[(row["scenario"], row["formation"], row["model"], arm)]
        assert instrument == (
            "paper_loop_2026_09_23"
            if arm in ("lead_cut_line", "priorities", "charter_stakes")
            else "paper_2026_09_23"
        ), row["run"]


# --- --print-info ----------------------------------------------------------------------------------------


def _rendered(render_to: Path) -> dict[str, dict[str, Any]]:
    """A `--render-to DIR`: run dir name -> {"config": record, "<seat>": AGENTS.md text, ...}."""
    out: dict[str, dict[str, Any]] = {}
    for run in sorted(p for p in render_to.iterdir() if p.is_dir()):
        out[run.name] = {"config": json.loads((run / "config.json").read_text())}
        for brief in sorted(run.glob("*/AGENTS.md")):
            out[run.name][brief.parent.name] = brief.read_text(encoding="utf-8")
    return out


def _render(render_to: Path, *args: str) -> dict[str, dict[str, Any]]:
    """`eval/merge_queue/run.py --print-info ... --render-to DIR`, read back; `--print-info` touches no runs root."""
    runs = render_to.parent / "runs"
    argv = [
        "--print-info",
        *args,
        "--runs-root",
        str(runs),
        "--render-to",
        str(render_to),
    ]
    assert mq_run.main(argv) == 0 and not runs.exists()
    return _rendered(render_to)


def _research_name(entry: dict[str, Any], run: str) -> str:
    """The research run-dir name of a rendered episode: the cell it runs + model slug + world epoch."""
    return "__".join([entry["config"]["cell"], *run.split("__")[-2:]])


def test_the_drive_scripts_print_info_prints_its_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`_drive.py --print-info --render-to DIR`, in process and as the launcher runs it (its own interpreter)."""
    job = rl.ReleaseJob("oversub", "team", 1, "lead_cut_line", "claude-opus-5")
    args = mq_run.parse_args(rl.launcher_argv(job, tmp_path / "runs"))
    (planned,) = mq_run.plan(args)
    argv = mq_run.drive_argv(
        args, planned, provider="anthropic", key_env="ANTHROPIC_API_KEY", pi_cmd="pi"
    )
    assert drive_main([*argv[2:], "--render-to", str(tmp_path / "one")]) == 0
    printed = json.loads(capsys.readouterr().out)
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert json.loads(proc.stdout) == printed
    record = json.loads((tmp_path / "one" / "config.json").read_text())
    assert printed.pop("seats") == 5 and printed.pop("run_dir") == str(
        (tmp_path / "runs").resolve()
        / "oversub__none__comms__mit-lead_cut_line__opus5__e1"
    )
    assert printed == record and record["cell"] == "oversub__none__comms__live_captain"
    assert record["turn_timeout"] == 1800.0  # the setting of record
    lead = (tmp_path / "one" / "release-captain" / "AGENTS.md").read_text()
    assert _sha256(lead) == PAPER_BRIEFS[("i1_cut_line_first_post", "release-captain")]
    assert not (tmp_path / "runs").exists()
    with pytest.raises(SystemExit, match="add --print-info"):
        drive_main(
            [a for a in argv[2:] if a != "--print-info"]
            + ["--render-to", str(tmp_path)]
        )
    # building the episode without driving it is --print-info: a leftover --dry-run is refused
    capsys.readouterr()
    with pytest.raises(SystemExit) as refused:
        drive_main([a for a in argv[2:] if a != "--print-info"] + ["--dry-run"])
    assert refused.value.code == 2
    assert (
        "unknown option --dry-run (building the episode without driving it is --print-info)"
        in capsys.readouterr().err
    )


@pytest.mark.parametrize("slug", sorted(MODELS))
@pytest.mark.parametrize("arm", [n for n in mitigations.MITIGATIONS if n != "none"])
def test_the_launchers_print_info_renders_the_papers_briefs_and_seeds(
    arm: str, slug: str, tmp_path: Path
) -> None:
    epochs = 20 if arm == "charter" else 5
    rendered = _render(
        tmp_path / "render",
        *("--all", "--formation", "team", "--mitigation", arm),
        *("--episodes", str(epochs), "--model", MODELS[slug]),
    )
    assert len(rendered) == 3 * epochs
    spec = mitigations.ARMS[arm]
    lead = spec.topology == "live_captain"
    for run, entry in rendered.items():
        config = entry["config"]
        assert re.fullmatch(rf"[a-z_]+__none__comms__mit-{arm}__{slug}__e\d+", run), run
        assert (config["mitigation"], config["world"], config["variant"]) == (
            arm,
            "paper",
            spec.variant,
        )
        assert config["cell"].endswith("__live_captain") == lead
        assert set(entry) - {"config"} == OWNERS | (
            {"release-captain"} if lead else set()
        )
    # seeds: `--episodes 5` (20 for the charter) of the paper's three scenarios are the paper's seeds
    planned = {_research_name(e, run) for run, e in rendered.items()}
    held = planned - UNFROZEN.get((arm, slug), set())
    assert (len(held), _names_digest(held)) == PAPER_ARM_EPISODES[(arm, slug)]
    if epochs == 5:
        by_scenario: dict[str, list[int]] = {}
        for run, entry in rendered.items():
            by_scenario.setdefault(entry["config"]["scenario"], []).append(
                int(run.rsplit("__e", 1)[1])
            )
        assert {s: sorted(e) for s, e in by_scenario.items()} == LOOP_SEEDS
    # the briefs: byte for byte the paper's own oversub e1 briefs (model-independent texts)
    e1 = rendered[f"oversub__none__comms__mit-{arm}__{slug}__e1"]
    pinned = {seat: d for (rung, seat), d in PAPER_BRIEFS.items() if rung == spec.rung}
    for seat, digest in pinned.items():
        assert _sha256(e1[seat]) == digest, (arm, seat)
    assert bool(pinned) == (arm in ("lead_cut_line", "priorities", "charter_stakes"))
    if arm == "charter":
        # the charter is charter + stakes without the stakes note (the loop's base variant)
        stakes = _oversub_e1_brief("value_is_stakes", "agent-201")
        assert _sha256(stakes) == PAPER_BRIEFS[("i1_value_is_stakes", "agent-201")]
        assert e1["agent-201"] == stakes[: stakes.index(f"\n{IDEA_SEAT_HEADING}")]
        assert SEAT_HEADING in e1["agent-201"]


@pytest.mark.parametrize("slug", sorted(MODELS))
def test_the_launchers_print_info_plans_the_papers_formation_matrix(
    slug: str, tmp_path: Path
) -> None:
    formations = ("--formation", "solo", "coordinator", "team_silent", "team")
    matrix = ("--all", *formations, "--episodes", "20", "--model", MODELS[slug])
    if slug == "opus5":
        # the root launcher's default is this matrix; it forwards `--render-to` to a local `--print-info` (default
        # backend: prints the Modal command)
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "run.py"),
                "merge_queue",
                "--print-info",
                "--model",
                MODELS[slug],
                "--runs-name",
                "release_layout_probe",
                "--render-to",
                str(tmp_path / "render"),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert (
            "Modal command: " in proc.stdout
            and "merge_queue: 240 episode(s), 3 scenario(s)" in proc.stdout
        )
        rendered = _rendered(tmp_path / "render")
    else:
        rendered = _render(tmp_path / "render", *matrix)
    assert len(rendered) == 240
    assert _names_digest(set(rendered)) == PAPER_FORMATION_EPISODES[slug]
    for run, entry in rendered.items():
        config = entry["config"]
        assert "mitigation" not in config and config["cell"] == run.rsplit("__", 2)[0]
        assert (config["world"], config["variant"]) == (
            "paper",
            "noprio_nocaptain_subtle_stakes_briefs_only",
        )
        # the coordinator and solo cells run one seat (the steward's), the teams one per PR owner
        seats = set(entry) - {"config"}
        assert seats == (
            {"steward"} if config["formation"] in ("coordinator", "solo") else OWNERS
        ), run
        for seat in seats:
            # the control arm carries no mitigation text
            text = entry[seat]
            assert PRIORITY_HEADING not in text and IDEA_SEAT_HEADING not in text
            assert SEAT_HEADING not in text
    # every leaderless arm only appends to the team formation's owner brief of the same seed
    team = rendered[f"oversub__none__comms__{slug}__e1"]["agent-201"]
    for key in ("last_stands_down", "value_is_stakes"):
        assert _oversub_e1_brief(key, "agent-201").startswith(team), key
