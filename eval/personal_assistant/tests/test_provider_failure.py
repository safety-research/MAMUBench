"""An episode whose provider refuses every call is a provider failure, never a behavioural result.

The provider screen reads a seat whose every assistant message is an error with no content as a seat that never
answered (`ladder_report._seat_dead_turn`); a refusal no retry can clear (401 / 402 / 403 / 404) stops the seat,
and a relay with every seat down ends at once instead of waiting out its window.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from personal_assistant.environment import relay as relay_module
from personal_assistant.environment.ladder_report import (
    _seat_dead_turn,  # pyright: ignore[reportPrivateUsage]
)
from personal_assistant.environment.pi_runtime import provider_refused
from personal_assistant.environment.relay import DecisionFreeRelay, RelayPrompt


def _session(seat_dir: Path, messages: list[dict[str, Any]]) -> None:
    sessions = seat_dir / "sessions"
    sessions.mkdir(parents=True)
    lines = [{"type": "session"}] + [
        {"type": "message", "message": m} for m in messages
    ]
    (sessions / "s.jsonl").write_text("\n".join(json.dumps(line) for line in lines))


ERROR: dict[str, Any] = {
    "role": "assistant",
    "content": [],
    "stopReason": "error",
    "errorMessage": "401 User not found.",
}
USER = {"role": "user", "content": [{"type": "text", "text": "hi"}]}
ANSWER = {
    "role": "assistant",
    "content": [{"type": "text", "text": "ok"}],
    "stopReason": "stop",
}


@pytest.mark.parametrize("ending", ["deadline_expired", "no_decision"])
def test_a_seat_whose_every_call_failed_is_a_dead_seat(
    tmp_path: Path, ending: str
) -> None:
    _session(tmp_path / "S", [USER, ERROR, USER, ERROR])
    assert _seat_dead_turn(tmp_path / "S", ending)
    # one completion is output: the seat answered, whatever failed around it
    _session(tmp_path / "T", [USER, ERROR, USER, ANSWER, USER, ERROR])
    assert not _seat_dead_turn(tmp_path / "T", "deadline_expired")


def test_only_errors_no_retry_clears_stop_the_seat() -> None:
    for error in (
        "401 User not found.",
        '401 {"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}}',
        "402 Insufficient credits",
        "403 Key limit exceeded",
        "404 No endpoints found that support tool use.",
    ):
        assert provider_refused(error), error
    for error in (
        "429 Rate limit exceeded",
        '529 {"type":"error","error":{"type":"overloaded_error"}}',
        "502 <html>Bad Gateway</html>",
        "Connection error.",
        "Request timed out.",
    ):
        assert not provider_refused(error), error


class _Scenario:
    def opening(self, seat: str) -> RelayPrompt:
        return RelayPrompt(seat, "brief")

    def debrief(self, seat: str) -> RelayPrompt:
        return RelayPrompt(seat, "receipt")


class _RefusedEpisode:
    """Every turn is refused: the runtime marks the seat crashed and raises, as `food_runtime.turn` does."""

    ids: tuple[str, ...] = ("A", "B")
    turn_timeout = 1.0
    record_turn_text = False

    def __init__(self) -> None:
        self.crashed: dict[str, str] = {}
        self.turns = 0
        self._lock = threading.Lock()

    def ensure_started(self) -> None:
        pass

    def turn(self, seat: str, prompt: str) -> object:
        with self._lock:
            self.turns += 1
        self.crashed[seat] = "provider refused: 401 User not found."
        raise RuntimeError(self.crashed[seat])

    def status(self) -> dict[str, Any]:
        # a DM still queued for a downed seat must not keep the relay waiting
        return {"orders_placed": 0, "dm_pending": {"A": 1, "B": 0}}

    def dm_drain(self, seat: str) -> list[str]:
        return []

    def dm_requeue(self, seat: str, rows: list[str]) -> None:
        pass

    def record_diner_msg(self, seat: str, principal: str, beat: str, text: str) -> None:
        pass

    def post_event(self, body: dict[str, Any]) -> None:
        pass


def test_a_relay_with_every_seat_refused_ends_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(relay_module, "_POLL_SECONDS", 0.01)
    episode = _RefusedEpisode()
    relay = DecisionFreeRelay(episode, _Scenario(), hard_cap_s=5.0, deadline_s=4.0)
    assert relay.run() == "transport_failure"
    assert episode.turns == 2 and set(episode.crashed) == {"A", "B"}


def test_the_screen_finds_an_openrouter_episodes_run_dir(tmp_path: Path) -> None:
    """An OpenRouter id's `/` never nests a run dir: the screen reads `<cell>__<vendor>__<model>__e<N>`."""
    from personal_assistant.environment.ladder_report import provider_killed

    record = {
        "cell": "conf_x_steward",
        "model": "deepseek/deepseek-v4-flash",
        "epoch": 1,
        "ending": "deadline_expired",
    }
    sidecar = tmp_path / "worlds" / "conf_x_steward__e1.json"
    run_dir = tmp_path / "runs" / "conf_x_steward__deepseek__deepseek-v4-flash__e1"
    _session(run_dir / "agents" / "S", [USER, ERROR])
    assert provider_killed(record, sidecar)
