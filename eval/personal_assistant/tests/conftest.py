"""Test bootstrap: `eval/` on `sys.path`, the fixture waves, and the helpers several test files share."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

TESTS_DIR = Path(__file__).resolve().parent
EVAL_ROOT = TESTS_DIR.parent
EVALS_DIR = EVAL_ROOT.parent
if str(EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(EVALS_DIR))

from personal_assistant._paths import bootstrap  # noqa: E402

bootstrap()

if TYPE_CHECKING:
    from personal_assistant.environment.trip_cart import TripCartWorld, TripSpec
    from personal_assistant.outcomes import EpisodeOutcome

FIXTURE_WAVES = TESTS_DIR / "fixtures" / "waves"
EXPECTED = EVAL_ROOT / "expected"
REFERENCE = EXPECTED / "reference.json"


@pytest.fixture(scope="session")
def fixture_waves() -> Path:
    """The committed fixture waves (see `tools/make_fixtures.py`)."""
    assert FIXTURE_WAVES.is_dir(), "run tools/make_fixtures.py"
    return FIXTURE_WAVES


def run_fake(
    runs_root: Path,
    *,
    scenario: str,
    formations: tuple[str, ...],
    scripts: Path | None,
    epochs: int = 1,
    epoch0: int = 1,
    extra: tuple[str, ...] = (),
) -> int:
    """Invoke `run.main` in fake-pi mode (no model, no key, localhost only)."""
    from personal_assistant import run

    argv = [
        "--scenario",
        scenario,
        "--formation",
        *formations,
        "--episodes",
        str(epochs),
        "--epoch0",
        str(epoch0),
        "--fake-pi",
        "--runs-root",
        str(runs_root),
        "--parallel",
        str(len(formations)),
        *extra,
    ]
    if scripts is not None:
        argv += ["--fake-scripts", str(scripts)]
    return run.main(argv)


def episode(**fields: Any) -> EpisodeOutcome:
    """A classified episode: a committed, kept Claude Sonnet 5 team episode unless `fields` say otherwise."""
    from personal_assistant.outcomes import EpisodeOutcome

    base: dict[str, Any] = {
        "wave": "w",
        "sidecar": f"s{fields.get('epoch', 1)}.json",
        "scenario": "kestrel_quiz_booth",
        "formation": "team",
        "cell": "c",
        "model": "claude-sonnet-5",
        "thinking": "off",
        "epoch": 1,
        "git_sha": "g",
        "ending": "committed",
        "outcome": "kept",
        "gate_instrument": "g",
        "gate_errors": 0,
        "canaries": (),
        "turns": 1,
    }
    return EpisodeOutcome(**{**base, **fields})


def book_trip(world: TripCartWorld, spec: TripSpec) -> None:
    """Book the spec's first listing for the whole cast (distinct rooms, shares summing to the price)."""
    listing = next(iter(spec.listings.values()))
    creator = world.ids[0]
    assert world.dispatch(
        creator, "trip_draft_create", {"listing_id": listing.id}
    ).startswith("PeakStay: shared draft")
    base, extra = divmod(listing.price, len(spec.travellers))
    for i, (traveller, room) in enumerate(
        zip(spec.travellers, listing.rooms, strict=False)
    ):
        share = base + (1 if i < extra else 0)
        assert share <= traveller.platform_share_cap
        seat = traveller.seat if traveller.seat in world.ids else creator
        result = world.dispatch(
            seat,
            "trip_draft_set",
            {"person": traveller.id, "room": room, "share": share},
        )
        assert "staged" in result, result
    result = world.dispatch(creator, "trip_checkout_confirm", {})
    assert world.booking is not None, result
