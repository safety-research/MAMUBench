#!/usr/bin/env python3
"""A deterministic stand-in for `pi --mode rpc` + the environment's hub extension, for offline tests.

Speaks exactly what the environment runtime needs from a seat: the pi 0.77 RPC protocol
(`pi_rpc.run_turn`: one `{"type": "prompt"}` line in, events out ending in `agent_end` with
pi-shaped `messages`), the hub extension's start-up attestation (`POST /runtime/attest` with the
active tool list, thinking level and project-context blocks — `_preflight_tool_surfaces` fails
closed without it; without `--no-context-files` the cwd AGENTS.md is attested as loaded), typed
tool calls over the bearer-authenticated hub (`POST /agent/call`), and a pi-shaped session
transcript under `--session-dir` (the provider screens in `ladder_report.py` read those).

Scripts (`FAKE_PI_SCRIPT_DIR/<FAKE_PI_SEAT>.json`, else `default.json`, else empty): a list of
turns, each an object with any of

    "steps":     [{"tool": name, "args": {...}} | {"sleep": seconds}, ...]
    "reply":     assistant text after the steps (omit it to end the turn on a tool result — the
                 provider screens' DEAD-TURN signature)
    "api_error": a provider-failure turn (assistant message with stopReason "error", no content)
    "storm":     N extra `overloaded` error records written to the session transcript before the
                 turn (the UNRECOVERED-STORM screen counts them in the session tail)

Turns past the end of the script are quiet (an assistant message with empty content).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

PI_VERSION = "0.77.0"


def _flag(argv: list[str], name: str, default: str = "") -> str:
    if name in argv:
        index = argv.index(name)
        if index + 1 < len(argv):
            return argv[index + 1]
    return default


def _post(path: str, payload: dict[str, Any]) -> str:
    base = os.environ.get("PA_HUB_SERVER", "").rstrip("/")
    token = os.environ.get("PA_HUB_TOKEN", "")
    request = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Seat-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body: object = json.loads(response.read().decode())
    except (OSError, urllib.error.URLError) as exc:
        return f"error: the assistant hub is not responding ({exc})."
    if isinstance(body, dict):
        return str(cast(dict[str, Any], body).get("text", ""))
    return ""


def _load_script() -> list[dict[str, Any]]:
    directory = os.environ.get("FAKE_PI_SCRIPT_DIR")
    if not directory:
        return []
    for name in (os.environ.get("FAKE_PI_SEAT", ""), "default"):
        candidate = Path(directory) / f"{name}.json"
        if name and candidate.exists():
            loaded: object = json.loads(candidate.read_text())
            if isinstance(loaded, list):
                return [dict(turn) for turn in cast(list[dict[str, Any]], loaded)]
    return []


class Session:
    """A pi-shaped session transcript (the subset the environment's readers consume)."""

    def __init__(
        self, session_dir: Path, *, cwd: str, model: str, thinking: str
    ) -> None:
        session_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"
        self.path = session_dir / f"{stamp}_{uuid.uuid4()}.jsonl"
        self._write(
            {"type": "session", "version": 3, "id": str(uuid.uuid4()), "cwd": cwd}
        )
        self._write({"type": "model_change", "provider": "fake", "modelId": model})
        self._write({"type": "thinking_level_change", "thinkingLevel": thinking})

    def _write(self, record: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def message(self, message: dict[str, Any]) -> None:
        """Append one message record."""
        self._write({"type": "message", "message": message})


def _turn_messages(
    prompt: str, entry: dict[str, Any], session: Session
) -> list[dict[str, Any]]:
    user = {"role": "user", "content": [{"type": "text", "text": prompt}]}
    session.message(user)
    messages: list[dict[str, Any]] = [user]
    storm = int(entry.get("storm", 0) or 0)
    for _ in range(storm):
        session.message(
            {
                "role": "assistant",
                "content": [],
                "stopReason": "error",
                "errorMessage": "overloaded",
            }
        )
    if entry.get("api_error"):
        failure: dict[str, Any] = {
            "role": "assistant",
            "content": [],
            "stopReason": "error",
            "errorMessage": str(entry["api_error"]),
        }
        session.message(failure)
        messages.append(failure)
        return messages
    steps: list[dict[str, Any]] = [
        dict(step) for step in cast(list[dict[str, Any]], entry.get("steps") or [])
    ]
    for index, step in enumerate(steps):
        if "sleep" in step:
            time.sleep(float(step["sleep"]))
            continue
        tool = str(step["tool"])
        args: dict[str, Any] = dict(cast(dict[str, Any], step.get("args") or {}))
        call_id = f"fake-{uuid.uuid4().hex[:8]}-{index}"
        call = {
            "role": "assistant",
            "content": [
                {"type": "toolCall", "id": call_id, "name": tool, "arguments": args}
            ],
        }
        result = {
            "role": "toolResult",
            "toolCallId": call_id,
            "toolName": tool,
            "content": [
                {
                    "type": "text",
                    "text": _post("/agent/call", {"command": tool, "args": args}),
                }
            ],
            "isError": False,
        }
        session.message(call)
        session.message(result)
        messages.extend((call, result))
    reply = str(entry.get("reply") or "")
    if reply or not steps:
        text = {
            "role": "assistant",
            "content": [{"type": "text", "text": reply}] if reply else [],
        }
        session.message(text)
        messages.append(text)
    return messages


def _project_context(argv: list[str]) -> list[dict[str, str]]:
    """The `<project_instructions>` blocks pi 0.77 would build, as the hub extension attests them.

    Launched with `--no-context-files` (the run-of-record launch) pi loads none; without it, pi
    loads the AGENTS.md in its working directory verbatim, attested as that file's absolute path
    plus the sha256 of its text (`hub.ts` `projectContextBlocks`).
    """
    if "--no-context-files" in argv:
        return []
    agents = Path.cwd() / "AGENTS.md"
    if not agents.is_file():
        return []
    return [
        {
            "path": str(agents),
            "sha256": hashlib.sha256(agents.read_text().encode()).hexdigest(),
        }
    ]


def main(argv: list[str]) -> int:
    """Attest, then answer prompts from stdin until it closes."""
    if "--version" in argv:
        print(PI_VERSION)
        return 0
    thinking = _flag(argv, "--thinking", "off")
    tools = [name for name in _flag(argv, "--tools").split(",") if name]
    session_dir = Path(_flag(argv, "--session-dir", str(Path.cwd() / "sessions")))
    session = Session(
        session_dir,
        cwd=os.getcwd(),
        model=_flag(argv, "--model", "fake"),
        thinking=thinking,
    )
    attested = _post(
        "/runtime/attest",
        {
            "active_tools": tools,
            "all_tools": tools,
            "thinking": thinking,
            "project_context": _project_context(argv),
        },
    )
    if attested != "attested":
        sys.stderr.write(f"fake_pi: attestation failed: {attested}\n")
    script = _load_script()
    turn = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        raw: object = json.loads(line)
        if not isinstance(raw, dict):
            continue
        event = cast(dict[str, Any], raw)
        if event.get("type") != "prompt":
            continue
        prompt = str(event.get("message", ""))
        entry = script[turn] if turn < len(script) else {}
        turn += 1
        messages = _turn_messages(prompt, entry, session)
        sys.stdout.write(json.dumps({"type": "agent_end", "messages": messages}) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
