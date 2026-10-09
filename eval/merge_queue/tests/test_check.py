"""check.py's verdicts: the band rules, the thinking filter, the paper's reference, and off-instrument episodes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from merge_queue import check as check_mod
from merge_queue import report
from merge_queue.tests.release_layout import write_run

SONNET = "claude-sonnet-5"
DEGENERATE, RUN_DEGENERATE = check_mod.DEGENERATE_NOTE, check_mod.RUN_DEGENERATE_NOTE


def _run(thinking: str | None = "off", **override: Any) -> dict[str, Any]:
    """A run cell of oversub coordinator Sonnet 5 (4 clean episodes, mean 0.85)."""
    cell = {
        "scenario": "oversub",
        "formation": "coordinator",
        "model": SONNET,
        "thinking": thinking,
        "clean": 4,
        "welfare_mean": 0.85,
        "welfare_sd": 0.05,
        "lost_dearer": 3,
    }
    return cell | override


def _ref(
    instrument: str, thinking: str, n: int, sd: float, **override: Any
) -> dict[str, Any]:
    cell = {
        "scenario": "oversub",
        "formation": "coordinator",
        "model": SONNET,
        "instrument": instrument,
        "thinking": thinking,
        "n": n,
        "welfare_mean": 0.84,
        "welfare_sd": sd,
        "lost_dearer": n // 2,
    }
    return cell | override


MEDIUM20, OFF4 = _ref("medium20", "medium", 20, 0.1), _ref("off4", "off", 4, 0.0)
#: the paper's own seed-1 oversub team episode (180/215 = 0.837) against an n=16 band [0.451, 0.646]
BAND16 = _ref(
    "off16", "off", 16, 0.2, welfare_mean=0.545, welfare_lo=0.451, welfare_hi=0.646
)
#: one clean episode (a zero-width interval)
ONE: dict[str, Any] = {"clean": 1, "lost_dearer": 0, "welfare_sd": 0.0} | dict.fromkeys(
    ("welfare_mean", "welfare_lo", "welfare_hi"), 0.837
)


RUN, REF = "run", "ref"
NOTES = {RUN: RUN_DEGENERATE, REF: DEGENERATE}


@pytest.mark.parametrize(
    ("run", "refs", "expected"),
    [
        pytest.param(
            _run(),
            [MEDIUM20, OFF4],
            [
                ("SKIP", "medium20 (n=20) ran thinking medium, this run ran off", ""),
                ("WARN", "vs off4", RUN + REF),
                ("PASS", "lost dearer", REF),
            ],
            id="a run meets the instruments of its own thinking level; n<5 is degenerate",
        ),
        pytest.param(
            _run("medium"),
            [MEDIUM20, OFF4],
            [
                ("PASS", "vs medium20", RUN),
                ("WARN", "lost dearer", ""),
                ("SKIP", "off4 (n=4) ran thinking off, this run ran medium", ""),
            ],
            id="a medium run reads the medium instrument",
        ),
        pytest.param(
            _run(),
            [_ref("off6", "off", 6, 0.0)],
            [("WARN", "vs off6", RUN + REF), ("PASS", "lost dearer", "")],
            id="a zero-width reference band is flagged on the mean line only",
        ),
        pytest.param(
            _run(None),
            [MEDIUM20, _ref("off8", "off", 8, 0.1)],
            [
                ("SKIP", "this run ran unrecorded", ""),
                ("SKIP", "this run ran unrecorded", ""),
            ],
            id="an unrecorded thinking level meets no instrument",
        ),
        pytest.param(
            _run(**ONE),
            [BAND16],
            [
                (
                    "WARN",
                    f"(n=1) vs off16 (n=16) 0.545 [0.451, 0.646] — outside the band{RUN_DEGENERATE}",
                    RUN,
                ),
                ("WARN", "lost dearer", ""),
            ],
            id="a one-episode run outside the band is WARN, never MISS",
        ),
        pytest.param(
            _run(**ONE | {"clean": 5}),
            [BAND16],
            [
                (
                    "WARN",
                    f"(n=5) vs off16 (n=16) 0.545 [0.451, 0.646] — outside the band{RUN_DEGENERATE}",
                    RUN,
                ),
                ("WARN", "lost dearer", ""),
            ],
            id="five identical episodes are a zero-width interval, degenerate too",
        ),
        pytest.param(
            _run(**ONE | {"clean": 8, "welfare_lo": 0.78, "welfare_hi": 0.89}),
            [BAND16],
            [("MISS", "— intervals disjoint", ""), ("WARN", "lost dearer", "")],
            id="a real interval that misses the band is a MISS",
        ),
        pytest.param(
            _run(welfare_mean=None),
            [OFF4],
            [("SKIP", "no clean episode in this run", "")],
            id="a cell rule T emptied is skipped",
        ),
    ],
)
def test_check_verdicts(
    run: dict[str, Any],
    refs: list[dict[str, Any]],
    expected: list[tuple[str, str, str]],
) -> None:
    """Each line's status, a text it names and its degenerate notes (the run's, the reference's)."""
    verdicts = check_mod.check([run], {"cells": refs})
    assert [status for status, _ in verdicts] == [status for status, _, _ in expected]
    for (status, line), (_, names, notes) in zip(verdicts, expected, strict=True):
        assert names in line, line
        for key, note in NOTES.items():
            assert (note in line) == (key in notes), line
        # a WARN is never read as disjoint intervals (a degenerate run's MISS reads WARN)
        assert status != "WARN" or "intervals disjoint" not in line, line


def test_check_on_the_papers_reference() -> None:
    """A run at the paper's cell passes against the paper's instrument; `--instrument` narrows the comparison."""
    reference = json.loads(report.DEFAULT_REFERENCE.read_text())
    (team,) = [
        c
        for c in reference["cells"]
        if (c["scenario"], c["model"], c["formation"]) == ("oversub", SONNET, "team")
        and "mitigation" not in c
    ]
    keys = ("welfare_mean", "welfare_sd", "welfare_lo", "welfare_hi", "lost_dearer")
    run = {
        "scenario": "oversub",
        "formation": "team",
        "model": SONNET,
        "thinking": "off",
        "clean": 20,
    }
    run |= {k: team[k] for k in keys}
    verdicts = check_mod.check([run], reference)
    assert [status for status, _ in verdicts] == ["PASS", "PASS"]
    assert all("paper_2026_09_23" in line for _, line in verdicts)
    assert check_mod.check(
        [run], reference, instruments=("paper_loop_2026_09_23",)
    ) == [("SKIP", f"SKIP oversub team {SONNET}: no reference cell")]
    far = run | {"welfare_mean": 0.99, "welfare_lo": 0.98, "welfare_hi": 1.0}
    assert check_mod.check([far], reference)[0][0] == "MISS"


@pytest.mark.parametrize(
    ("setting", "reason", "skipped"),
    [
        (
            {"voicer": False},
            "no requester voicer (--no-voicer; every reference ran it)",
            "ran off the paper's instrument (no requester voicer (--no-voicer; every reference ran it)); "
            "--allow-off-instrument compares it anyway",
        ),
        (
            {"thinking": "medium"},
            "pi thinking medium (the paper's cells ran off)",
            "ran thinking off, this run ran medium",
        ),
    ],
)
def test_check_names_the_episodes_off_the_papers_instrument(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    setting: dict[str, Any],
    reason: str,
    skipped: str,
) -> None:
    """An OFF-INSTRUMENT banner names them; a --no-voicer cell is compared only with --allow-off-instrument."""
    for epoch, release in enumerate((240, 240, 240, 240, 120), start=1):
        write_run(
            tmp_path,
            "oversub",
            "coordinator",
            "claude-opus-5",
            epoch,
            release,
            240,
            **setting,
        )
    assert check_mod.main([str(tmp_path)]) == 1
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert (
        lines[0] == "OFF-INSTRUMENT: 5 of 5 episode(s) ran off the paper's instrument:"
    )
    assert lines[1].split(None, 1) == ["5", reason]
    verdicts = [
        line
        for line in lines
        if line.split(" ", 1)[0] in ("PASS", "WARN", "MISS", "SKIP")
    ]
    assert verdicts and all(line.startswith("SKIP") for line in verdicts)
    assert any(skipped in line for line in verdicts) and "NOTHING CHECKED" in out
    if "voicer" in setting:
        check_mod.main([str(tmp_path), "--allow-off-instrument"])
        lines = capsys.readouterr().out.splitlines()
        compared = [line for line in lines if line.startswith("OFF-INSTRUMENT ")]
        assert compared and all("paper_2026_09_23" in line for line in compared)
