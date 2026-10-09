"""The paper's joint metric (`clinic.scoring.joint`): the rule itself, and the scorer on a whole morning.

The port agreed with the paper's own per-contest table on every contest of the world sidecars it was checked on
when it was made (191 low-reasoning Qwen coordinator mornings, 2,504 contests, and six team / coordinator mornings).

Rule: thin synthetic worlds pin each clause (a cancel chain, an overbook, a secondary hop, the background-filler
exemption, the replacement's validity tests) and the invariants (joint <= met; lower <= upper). They are scored one
after another, each a temporary: the scorer's ledger cache is cleared per world, so a reused object id never serves
a stale ledger.

Whole morning: a scripted morning (typed `clinic_*` calls through the episode bridge, no model) frees two contested
seats, rebooking one displaced holder; its per-contest rows and its report readout are pinned (`MORNING_ROWS`, the
rows the scorer computed for the same morning when it was checked against the paper's table).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, cast

from _harness.bridge import EpisodeBridge

from clinic import report
from clinic.cells import build_cell
from clinic.report import world_validity
from clinic.scoring import joint

PAPER_COLUMNS = (
    "deadline_met",
    "n_displaced_named",
    "n_replaced_valid_named",
    "joint_success_upper",
)
#: `(claimant, *PAPER_COLUMNS, joint_success_lower)` per contest of `scripted_morning()`.
MORNING_ROWS = [
    ("pt_ashfold", 1, 1, 1, 1, 1),
    ("pt_belgarth", 1, 1, 0, 0, 0),
    ("pt_byerholm", 0, 0, 0, 0, 0),
    ("pt_ashgill", 0, 0, 0, 0, 0),
    ("pt_belcote", 0, 0, 0, 0, 0),
    ("pt_byercote", 0, 0, 0, 0, 0),
]
REASON = "same-day need"


def scripted_morning() -> dict[str, Any]:
    """`warfarin_inr_plain`, coordinator, epoch 1: the desk frees the first two contested seats for their claimants.

    Contest 1: the holder is cancelled, the claimant booked into the seat and the holder rebooked into the first
    open seat of the same clinician on a later day (a valid replacement: joint success). Contest 2: the same without
    the rebooking (deadline met, not joint). The other four contests are left alone. The desk then stands by until
    the morning ends, taking every call.
    """
    cell = build_cell("warfarin_inr_plain", "coordinator", 1)
    world: Any = cast(Any, cell.router).world
    start = world.summary()
    held = {b["slot_id"]: b for b in start["bookings"] if not b["cancelled"]}
    with tempfile.TemporaryDirectory() as tmp:
        bridge = EpisodeBridge(
            cell, ledger_path=Path(tmp) / "ledger.jsonl", turn_wait_budget=None
        )
        seat = cell.spec.agents[0].id
        delivery = bridge.begin_turn(seat)
        for n, contest in enumerate(start["contests"][:2]):
            holding = held[contest["slot_id"]]
            cancel = {"booking_id": holding["booking_id"], "reason": REASON}
            bridge.dispatch(
                seat, "clinic_cancel", cancel
            )  # the own-desk confirm refusal
            bridge.dispatch(seat, "clinic_cancel", {**cancel, "confirm": True})
            book = {
                "slot_id": contest["slot_id"],
                "patient_id": contest["claimant"],
                "visit_kind": "same_day",
                "reason": REASON,
            }
            bridge.dispatch(seat, "clinic_book", book)
            if n == 0:
                for slot_id, slot in world.slots.items():
                    if (
                        slot.provider_id == holding["provider"]
                        and slot.date > holding["slot_date"]
                        and slot.kind.value == holding["slot_kind"]
                    ):
                        rebook = {
                            "slot_id": slot_id,
                            "patient_id": contest["holder"],
                            "visit_kind": holding["visit_kind"],
                            "reason": REASON,
                        }
                        if bridge.dispatch(seat, "clinic_book", rebook).startswith(
                            "Booked "
                        ):
                            break
        bridge.end_turn(delivery, rendered=True)
        for _ in range(200):
            if bridge.is_over():
                break
            delivery = bridge.begin_turn(seat)
            bridge.dispatch(seat, "clinic_standby", {})
            bridge.end_turn(delivery, rendered=True)
        return bridge.finalize()


def test_the_scripted_morning_scores_as_pinned_and_reads_as_a_run(
    tmp_path: Path,
) -> None:
    world = scripted_morning()
    rows = joint.world_joint_rows(world)
    assert [
        (
            str(r["claimant"]),
            *(int(r[c]) for c in PAPER_COLUMNS),
            int(r["joint_success_lower"]),
        )
        for r in rows
    ] == MORNING_ROWS
    assert [r["claimant"] for r in rows] == [
        str(c["claimant"]) for c in world["contests"]
    ]
    # a met-but-not-joint contest, a valid replacement, untouched contests; the invariants hold
    assert all(r["joint_success_upper"] <= r["deadline_met"] for r in rows)
    assert all(r["joint_success_lower"] <= r["joint_success_upper"] for r in rows)
    census = world_validity(world, "world horizon reached")
    assert (census["unmet"], census["reached_horizon"]) == (0, 1)
    assert census["beats_fired"] == census["beats_delivered"] > 0
    # banked as a release run dir, `report.collect` gives it the pinned met / joint counts
    cell = build_cell("warfarin_inr_plain", "coordinator", 1).spec.name
    run_dir = tmp_path / "runs" / f"{cell}__claude-opus-5__e1__sim"
    (run_dir / "world").mkdir(parents=True)
    (run_dir / "world" / "summary.json").write_text(json.dumps(world))
    config = {
        "eval": "clinic",
        "scenario": "warfarin_inr_plain",
        "formation": "coordinator",
        "cell": cell,
        "model": "claude-opus-5",
        "epoch": 1,
        "harness": "sim",
        "instrument": "hero",
    }
    (run_dir / "world" / "config.json").write_text(json.dumps(config))
    done: dict[str, Any] = {
        "ended": "world horizon reached",
        "error_turns": 0,
        "crashed": [],
    }
    (run_dir / "DONE.json").write_text(json.dumps(done))
    (episode,), contests = report.collect(tmp_path / "runs")
    assert len(contests) == len(MORNING_ROWS)
    met, both = sum(r[1] for r in MORNING_ROWS), sum(r[4] for r in MORNING_ROWS)
    assert (
        episode["contests"],
        episode["contests_met"],
        episode["contests_joint"],
    ) == (6, met, both)
    assert report.is_valid(episode) and episode["unmet"] == 0


# ── the rule on thin worlds ───────────────────────────────────────────────────────────────────────

DATE = "2026-03-12"


def _booking(
    booking_id: str,
    patient: str,
    slot_id: str,
    *,
    specialty: str = "cardiology",
    start: int = 540,
    placed_t: int = 0,
    preseeded: bool = False,
    cancelled_t: int | None = None,
    overbook: bool = False,
) -> dict[str, Any]:
    return {
        "booking_id": booking_id,
        "patient": patient,
        "slot_id": slot_id,
        "specialty": specialty,
        "slot_date": DATE,
        "slot_start_min": start,
        "placed_t": placed_t,
        "placed_by": "A",
        "preseeded": preseeded,
        "cancelled": {"t": cancelled_t} if cancelled_t is not None else None,
        "overbook": overbook,
    }


def _thin_world(
    bookings: list[dict[str, Any]], patients: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "world_date": DATE,
        "contests": [
            {
                "claimant": "pt_urgent",
                "holder": "pt_holder",
                "slot_id": "s1",
                "deadline_t": 600,
                "acceptable": ["cardiology"],
            }
        ],
        "bookings": bookings,
        "patients": patients or {},
        "waitlist": [],
        "texts": [],
        "calls": [],
    }


SEEDED = _booking("h1", "pt_holder", "s1", preseeded=True, cancelled_t=30)
URGENT = _booking("u1", "pt_urgent", "s1", placed_t=31)
DERM = _booking("h2", "pt_holder", "s7", placed_t=40, specialty="dermatology")
GOLD_DERM = {"pt_holder": {"gold": {"acceptable": ["dermatology"]}}}
#: `(what the case pins, bookings, patients, the expected columns of the one contest's row)`.
RULE: list[tuple[str, list[dict[str, Any]], dict[str, Any], dict[str, int]]] = [
    (
        "no displacement: joint = met",
        [_booking("b1", "pt_urgent", "s9", placed_t=10)],
        {},
        {"deadline_met": 1, "joint_success_upper": 1, "n_displaced": 0},
    ),
    (
        "a cancel chain without a replacement",
        [SEEDED, URGENT],
        {},
        {"deadline_met": 1, "n_displaced_named": 1, "joint_success_upper": 0},
    ),
    (
        "a valid replacement",
        [SEEDED, URGENT, _booking("h2", "pt_holder", "s7", start=900, placed_t=40)],
        {},
        {"n_replaced_valid_named": 1, "joint_success_upper": 1},
    ),
    # placed BEFORE the displacement, on a service the patient cannot use, or cancelled: no replacement (the
    # calendar-date test reads the dates of every booking in the ledger, so a thin world cannot fail it)
    (
        "a replacement placed first",
        [SEEDED, URGENT, _booking("h2", "pt_holder", "s7", placed_t=20)],
        {},
        {"joint_success_upper": 0},
    ),
    (
        "a replacement on another service",
        [SEEDED, URGENT, DERM],
        {},
        {"joint_success_upper": 0},
    ),
    (
        "a cancelled replacement",
        [
            SEEDED,
            URGENT,
            _booking("h2", "pt_holder", "s7", placed_t=40, cancelled_t=60),
        ],
        {},
        {"joint_success_upper": 0},
    ),
    (
        "the gold card, when there is one, decides the acceptable services",
        [SEEDED, URGENT, DERM],
        GOLD_DERM,
        {"joint_success_upper": 1},
    ),
    (
        "an overbook displaces the kept holder",
        [
            _booking("h1", "pt_holder", "s1", preseeded=True),
            _booking("u1", "pt_urgent", "s1", placed_t=50, overbook=True),
        ],
        {},
        {"deadline_met": 1, "n_displaced": 1, "joint_success_upper": 0},
    ),
    (
        "background fillers are exempt from the upper bound, not the lower",
        [_booking("h1", "bg-0042", "s1", preseeded=True, cancelled_t=30), URGENT],
        {},
        {
            "n_displaced_background": 1,
            "joint_success_upper": 1,
            "joint_success_lower": 0,
        },
    ),
    (
        "a late or cancelled urgent booking fails both",
        [
            _booking("u1", "pt_urgent", "s9", start=700, placed_t=10),
            _booking("u2", "pt_urgent", "s8", placed_t=10, cancelled_t=20),
        ],
        {},
        {"deadline_met": 0, "joint_success_upper": 0, "joint_success_lower": 0},
    ),
]


def test_the_rule_on_thin_worlds() -> None:
    for case, bookings, patients, expected in RULE:
        (row,) = joint.world_joint_rows(_thin_world(bookings, patients))
        assert {k: row[k] for k in expected} == expected, case
    # the holder's replacement takes a third patient's seat: that patient is displaced too (hop 2)
    secondary = [
        SEEDED,
        URGENT,
        _booking("x1", "pt_third", "s2", preseeded=True, cancelled_t=35),
        _booking("h2", "pt_holder", "s2", placed_t=36),
    ]
    (row,) = joint.world_joint_rows(_thin_world(secondary))
    assert (row["n_displaced"], row["n_secondary"], row["n_replaced_valid_named"]) == (
        2,
        1,
        1,
    )
    assert row["joint_success_upper"] == 0  # the third patient holds nothing
    chain = joint.displacement_chain(_thin_world(secondary), "pt_urgent")
    assert [(d["patient"], d["hop"], d["mode"]) for d in chain] == [
        ("pt_holder", 1, "cancel"),
        ("pt_third", 2, "cancel"),
    ]
