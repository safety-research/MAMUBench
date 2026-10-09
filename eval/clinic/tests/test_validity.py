"""The paper's validity rules: census, exclusions, refused pools, and the notes.

The delivery census, the per-formation exclusions (every team morning is read as it is, one instrument per
pool), the pools the readers refuse, and the notes they print.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from clinic import record, report
from clinic.tests.conftest import row

QWEN = "qwen3.8-max"
QUARANTINED = (
    "fleet quarantined — every agent at 3+ consecutive failed resumes (last target error: Target generate "
    "failed: AuthenticationError: Error code: 401 - {'type': 'error', 'error': {'type': "
    "'authentication_error', 'message': 'API key is invalid.'}})"
)


def _beats(*agents: str) -> list[dict[str, Any]]:
    return [{"agent": a, "t": 0} for a in agents]


def test_the_census_counts_undelivered_calls_never_woken_desks_and_live_strands() -> (
    None
):
    clean = report.world_validity(
        {"beats_fired": _beats("A", "B"), "beats_delivered": _beats("A", "B")},
        "world horizon reached",
    )
    assert (clean["unmet"], clean["stranded_callers"], clean["reached_horizon"]) == (
        0,
        0,
        1,
    )
    late = report.world_validity(
        {
            "beats_fired": _beats("A", "B", "B", "C"),
            "beats_delivered": _beats("A", "B"),
        },
        "world horizon reached — undelivered content remained (B: pending world delivery)",
    )
    assert (late["unmet"], late["beats_undelivered"], late["desks_never_reached"]) == (
        1,
        2,
        1,
    )
    assert late["wrapup_bound"] == 1
    assert late["stranded_callers"] == late["stranded_callers_live"] == 2
    # a desk the driver's end marks quarantined holds dead strands, not live ones
    stranded = report.world_validity(
        {
            "beats_fired": _beats("A", "B", "B", "M", "T"),
            "beats_delivered": _beats("A"),
        },
        "world horizon reached — world deliveries stranded (B: quarantined; undelivered scripted beat(s); "
        "M: quarantined; undelivered scripted beat(s); T: undelivered scripted beat(s))",
    )
    assert (stranded["stranded_desks"], stranded["quarantined_desks"]) == (
        "B;M;T",
        "B;M",
    )
    assert (stranded["stranded_callers"], stranded["stranded_callers_live"]) == (4, 1)
    assert stranded["reached_horizon"] == 1


#: `(morning, how the paper's exclusion of it opens)`: empty = valid.
EXCLUSIONS: list[tuple[dict[str, Any], str]] = [
    (row("coordinator", "hero", unmet=1), ""),  # the coordinator is kept as flown
    (row("team", "standard"), ""),
    # a team morning is read as it is: its census is reported, never an exclusion (Qwen3.8-max included)
    (row("team", "standard", unmet=1), ""),
    (row("team", "standard", unmet=1, model=QWEN), ""),
    (row("team_silent", "standard", stranded_callers=5), ""),
    (
        row("team_silent", "standard", stranded_callers_live=2),
        "caller(s) stranded on a live desk",
    ),
    (row("team", "standard", mitigation="s3", unmet=1), ""),
    (
        row("team", "standard", mitigation="s3", reached_horizon=0),
        "did not reach the horizon",
    ),
    (
        row("team", "standard", error_turns=1),
        "harness (provider-error turn or crashed seat)",
    ),
    (row("team", "standard", ended=report.ROUNDS_CAP), "rounds cap"),
    (
        row("team", "standard", unmet=1, failed_calls=16, failed_auth=16),
        "harness (the provider refused the key: 16 failed call(s))",
    ),
    (row("team", "standard", failed_calls=25, failed_529=25), ""),  # no rule T
    # a pi morning keeps the harness-clean rule only
    (row("team", None, harness="pi", unmet=1), ""),
    *[
        (
            row(f, i, ended=QUARANTINED, reached_horizon=0),
            "did not reach the horizon",
        )
        for f, i in (
            ("coordinator", "hero"),
            ("team", "standard"),
            ("team_silent", "standard"),
        )
    ],
]


def test_the_papers_exclusion_of_one_morning() -> None:
    for morning, reason in EXCLUSIONS:
        got = report.paper_exclusion(morning)
        assert got.startswith(reason) if reason else got == "", (morning, got)


def test_every_team_morning_of_a_root_is_read_once() -> None:
    rows = [
        row("team", "standard", epoch=1),
        row("team", "standard", epoch=2, unmet=1),  # census reported, morning kept
        row("team", "standard", epoch=3, error_turns=1),  # harness-excluded
        row("team", "standard", epoch=4, unmet=1, model=QWEN),  # kept, as every model's
    ]
    report.apply_paper_rules(rows)
    reasons = [str(r["paper_exclusion"]) for r in rows]
    assert [bool(r) for r in reasons] == [False, False, True, False]
    assert reasons[2].startswith("harness")
    (opus, qwen) = report.cell_rows(rows, draws=10)
    assert (opus["valid"], opus["excluded"], opus["unmet"], opus["instrument"]) == (
        2,
        1,
        1,
        "standard",
    )
    assert (qwen["valid"], qwen["excluded"]) == (1, 0)
    with pytest.raises(
        SystemExit, match="appears more than once on instrument standard"
    ):
        report.apply_paper_rules(
            [row("team", "standard"), {**row("team", "standard"), "run": "again"}]
        )


def test_the_readers_refuse_mixed_harnesses_and_physics_within_a_pool(
    tmp_path: Path,
) -> None:
    medium = "TARGET_THINKING=medium (the campaigns ran 0 on anthropic)"

    def recorded(
        formation: str, instrument: str, off: str = "", **kw: Any
    ) -> dict[str, Any]:
        return row(
            formation, instrument, on_paper_instrument=not off, off_paper=off, **kw
        )

    allowed = (
        [recorded("team", "standard"), recorded("team", "standard", epoch=2)],
        [
            recorded("team", "standard", medium),
            recorded("team", "standard", medium, epoch=2),
        ],
        [recorded("coordinator", "hero"), recorded("team", "standard")],
    )
    for rows in allowed:
        report.check_pools(rows, [tmp_path])
    refused = (
        # one instrument, two settings
        [recorded("team", "standard"), recorded("team", "standard", medium, epoch=2)],
        [
            recorded("coordinator", "hero"),
            recorded("coordinator", "hero", medium, epoch=2),
        ],
        # two instruments in one pool
        [recorded("team", "hero"), recorded("team", "standard", epoch=2)],
        [
            recorded("team", "standard", mitigation="s3"),
            recorded("team", "hero", mitigation="s3", epoch=2),
        ],
    )
    for rows in refused:
        with pytest.raises(
            SystemExit, match="mixes simulated-harness instruments or settings"
        ):
            report.check_pools(rows, [tmp_path])
    with pytest.raises(SystemExit, match="mixes harnesses"):
        report.check_pools(
            [row("team", "standard"), row("coordinator", None, harness="pi")],
            [tmp_path],
        )


def test_episodes_of_record_score_only_the_papers_episodes() -> None:
    member = row("team", "standard", epoch=3)
    outside = row("team_silent", "standard", epoch=6)  # the silent team is episodes 1-5
    qwen = row(
        "coordinator", "hero", epoch=2, model=QWEN, scenario="amiodarone_qt_split"
    )
    report.apply_paper_rules([member, outside, qwen], record.membership(record.load()))
    assert report.is_valid(member)
    assert (
        outside["paper_exclusion"] == "not an episode of record (--episodes-of-record)"
    )
    held = {
        r.epoch
        for r in record.select(record.load(), model=QWEN, formation="coordinator")
        if r.scenario == "amiodarone_qt_split"
    }
    assert (2 in held) == report.is_valid(qwen)


def test_the_notes_count_exclusions_and_provider_errors() -> None:
    rows = [
        row("team", "standard", epoch=1, unmet=1),
        row("team", "standard", epoch=2, error_turns=1),
        row("team_silent", "standard", stranded_callers_live=1),
        row("coordinator", "hero", failed_calls=16, failed_other=16, failed_auth=16),
        row(
            "coordinator",
            "hero",
            epoch=2,
            failed_calls=25,
            failed_529=25,
            rule_t_lost_turns=3,
        ),
    ]
    report.apply_paper_rules(rows)
    notes = report.exclusion_notes(rows)
    text = "\n".join(notes)
    assert "excluded: 1 x caller(s) stranded on a live desk" in text
    assert "excluded: 1 x harness (provider-error turn or crashed seat)" in text
    assert not [n for n in notes if n.startswith("note:")]  # nothing left to play
    # failed target calls are reported, never screened: the paper's clinic applies no rule T
    (errors,) = [n for n in notes if n.startswith("PROVIDER ERRORS")]
    assert errors.startswith("PROVIDER ERRORS: 2 of 5 mornings had failed target calls")
    assert "1 morning(s) had a lost turn (kept: the clinic applies no rule T)" in errors
    assert "rule T dropped" not in errors
    assert "EXCLUDED: the provider refused the key" in text
    assert report.exclusion_notes([row("coordinator", "hero")]) == []
