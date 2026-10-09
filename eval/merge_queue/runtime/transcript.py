"""Small helpers for preserving direct pi RPC episode traces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


def final_assistant_text(messages: list[dict[str, Any]]) -> str:
    """Return the final assistant text from one pi RPC turn."""
    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue
        blocks = cast(list[Any], message.get("content") or [])
        texts = [
            str(cast(dict[str, Any], block).get("text", ""))
            for block in blocks
            if cast(dict[str, Any], block).get("type") == "text"
        ]
        if texts:
            return "\n\n".join(texts)
    return ""


def append_turn_record(
    path: Path,
    *,
    actor: str,
    round_index: int,
    minute: int,
    prompt: str,
    messages: list[dict[str, Any]],
) -> None:
    """Append one driver-authoritative turn record for later inspection."""
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "v": 1,
        "actor": actor,
        "round": round_index,
        "minute": minute,
        "prompt": prompt,
        "reply": final_assistant_text(messages),
        "message_count": len(messages),
    }
    with path.open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def nonempty_session_count(state_dir: Path) -> int:
    """Count non-empty pi session JSONL files below an agent state directory."""
    return sum(
        path.stat().st_size > 0 for path in (state_dir / "sessions").rglob("*.jsonl")
    )
