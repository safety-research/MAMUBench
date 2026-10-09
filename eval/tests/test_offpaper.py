"""The off-instrument guard every reader shares: the pool key (`physics`) and the check banner / cell gating."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import _offpaper
import pytest
from _harness.readout import base_row, single_harness, single_instrument

HERO = "instrument hero (the paper's is limits_off)"
HIGH = "TARGET_REASONING=high (the campaigns ran none on anthropic)"


def _row(
    formation: str = "coordinator",
    instrument: str | None = "hero",
    off_paper: str = "",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "formation": formation,
        "model": "claude-sonnet-5",
        "mitigation": "none",
        "harness": "sim",
        "instrument": instrument,
        "off_paper": off_paper,
        "on_paper_instrument": None if instrument is None else not off_paper,
        **extra,
    }


def test_base_row_carries_the_recorded_reasons(tmp_path: Path) -> None:
    config = {
        "scenario": "stakes_100",
        "formation": "team",
        "instrument": "hero",
        "on_paper_instrument": False,
        "off_paper": [HERO, HIGH],
    }
    row = base_row(tmp_path / "run", {}, config, {})
    assert row["off_paper"] == f"{HERO}; {HIGH}"
    assert _offpaper.sim_reasons(row) == (HERO, HIGH)
    # a run banked before instruments were recorded (or a pi run) carries none and is never flagged
    old = base_row(tmp_path / "run", {}, {"scenario": "stakes_100"}, {})
    assert old["off_paper"] == "" and _offpaper.sim_reasons(old) == ()


def test_recorded_reasons_reads_a_config_list_or_a_row_string() -> None:
    assert _offpaper.recorded_reasons([HERO, HIGH]) == (HERO, HIGH)
    assert _offpaper.recorded_reasons(f"{HERO}; {HIGH}") == (HERO, HIGH)
    assert _offpaper.recorded_reasons("") == ()
    assert _offpaper.recorded_reasons(None) == ()
    # recorded off without a reason (never written by sim.py, but never read as on the instrument either)
    assert _offpaper.sim_reasons({"on_paper_instrument": False}) == (
        "recorded off the paper's instrument",
    )


def test_physics_is_the_instrument_plus_every_off_paper_reason() -> None:
    assert _offpaper.physics(_row()) == "hero"
    assert _offpaper.physics(_row(off_paper=HIGH)) == f"hero [off paper: {HIGH}]"
    assert _offpaper.physics(_row(instrument=None)) == "None"


def test_a_pool_that_mixes_reasoning_settings_is_refused(tmp_path: Path) -> None:
    # an on-paper coordinator night and one recorded at another reasoning setting (another epoch) never pool
    with pytest.raises(
        SystemExit, match="mixes simulated-harness instruments or settings"
    ):
        single_instrument([_row(), _row(off_paper=HIGH, epoch=2)], tmp_path)
    # ... and so do two different off-paper settings on the same instrument
    with pytest.raises(SystemExit, match=r"max_turns 50"):
        single_harness(
            [_row(off_paper=HIGH), _row(off_paper="max_turns 50 (recipe 800)")],
            tmp_path,
        )
    # one setting per pool, whatever it is, and different formations on different instruments, pool fine
    single_instrument([_row(off_paper=HIGH), _row(off_paper=HIGH, epoch=2)], tmp_path)
    single_instrument(
        [_row(), _row("team", "limits_off"), _row("team_silent", "hero", HERO)],
        tmp_path,
    )


def test_split_and_banner() -> None:
    rows = [_row(), _row(off_paper=HERO), _row(off_paper=f"{HERO}; {HIGH}")]
    on, off, reasons = _offpaper.split(rows, _offpaper.sim_reasons)
    assert on == rows[:1] and off == rows[1:]
    assert reasons == {HERO: 2, HIGH: 1}
    skip = _offpaper.banner(reasons, len(off), len(rows), "skip")
    assert (
        skip[0] == "OFF-INSTRUMENT: 2 of 3 episode(s) ran off the paper's instrument:"
    )
    assert skip[1] == f"       2  {HERO}" and skip[2] == f"       1  {HIGH}"
    assert "SKIPped" in skip[3] and "--allow-off-instrument" in skip[3]
    assert "marked OFF-INSTRUMENT" in _offpaper.banner(reasons, 2, 3, "marked")[3]
    assert "not the paper's" in _offpaper.banner(reasons, 2, 3, "info")[3]
    assert _offpaper.banner(reasons, 2, 3, None, "a note")[3:] == ["  a note"]
    assert _offpaper.banner({}, 0, 3, "skip") == []


def _compare(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """A stand-in check: one MISS line per cell (formation) of the rows it is given."""
    return [
        ("MISS", f"MISS {f}: compared") for f in sorted({r["formation"] for r in rows})
    ]


def test_gated_verdicts_skip_mark_or_compare() -> None:
    rows = [_row("coordinator"), _row("team", off_paper=HERO)]

    def label(r: dict[str, Any]) -> str:
        return str(r["formation"])

    banner, verdicts = _offpaper.gated_verdicts(
        rows, _offpaper.sim_reasons, _compare, label, paper=True, allow=False
    )
    assert banner[0].startswith("OFF-INSTRUMENT: 1 of 2")
    assert verdicts == [
        ("MISS", "MISS coordinator: compared"),
        (
            "SKIP",
            f"SKIP team: ran off the paper's instrument ({HERO}); --allow-off-instrument compares it anyway",
        ),
    ]
    banner, verdicts = _offpaper.gated_verdicts(
        rows, _offpaper.sim_reasons, _compare, label, paper=True, allow=True
    )
    assert verdicts == [
        ("MISS", "MISS coordinator: compared"),
        ("MISS", "OFF-INSTRUMENT MISS team: compared"),
    ]
    # another reference (an older instrument): everything is compared as it is, the banner still names the reasons
    banner, verdicts = _offpaper.gated_verdicts(
        rows, _offpaper.sim_reasons, _compare, label, paper=False, allow=False
    )
    assert "not the paper's" in banner[-1] and verdicts == _compare(rows)
    # every episode on the instrument: no banner, the check unchanged
    banner, verdicts = _offpaper.gated_verdicts(
        rows[:1], _offpaper.sim_reasons, _compare, label, paper=True, allow=False
    )
    assert banner == [] and verdicts == _compare(rows[:1])


def test_harness_banner_names_pi_episodes_against_the_simulated_reference() -> None:
    assert _offpaper.harness_banner([{"harness": "sim"}, {"harness": "sim"}]) == []
    lines = _offpaper.harness_banner([{"harness": "pi"}, {}])
    assert lines[0].startswith("HARNESS: 2 of 2 episode(s) ran the real-pi harness")
    assert "not a reproduction" in lines[1]
