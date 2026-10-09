#!/usr/bin/env python3
"""A deterministic stand-in for `pi --mode rpc`, for the offline test suite.

Speaks just enough of the pi RPC protocol for `pi_rpc.run_turn`: reads one JSON `{"type": "prompt"}`
line from stdin, runs the next scripted turn, and emits a terminal `agent_end` event with pi-shaped
`messages`. Two scripted step kinds exercise the twin's two real surfaces with no model and no network
beyond localhost:

- `{"tool": "labctl_status", "args": {...}}` — a TYPED tool call: POSTs to the bridge server exactly the
  way the labctl extension does (same endpoint, same `X-Seat-Token` header from this process's env), and
  embeds the result as a `toolCall`/`toolResult` message pair.
- `{"command": "ls"}` — a real bash step run in the workspace cwd (pi's native bash analog).

Script format (`FAKE_PI_SCRIPT` env var — path to a JSON file): a list of turns, each
`{"steps": [...], "reply": "..."}`. Turns past the end of the script are quiet monitoring turns with no
steps and no reply text (pure text turns — which the runner's idle-skip rule then parks, like the sim).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from typing import Any


def _bash(command: str) -> str:
    out = subprocess.run(
        ["bash", "-lc", command], capture_output=True, text=True, timeout=60
    )
    return (out.stdout + out.stderr).strip()


def _typed_call(tool: str, args: dict[str, Any]) -> str:
    base = os.environ.get("LABCTL_SERVER", "").rstrip("/")
    token = os.environ.get("LABCTL_TOKEN", "")
    req = urllib.request.Request(
        f"{base}/agent/call",
        data=json.dumps({"command": tool, "args": args}).encode(),
        headers={"Content-Type": "application/json", "X-Seat-Token": token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return str(json.loads(resp.read().decode()).get("text", ""))
    except OSError as e:
        return f"error: controller unreachable ({e})"


def _turn_messages(
    prompt: str, steps: list[dict[str, Any]], reply: str, api_error: str = ""
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    if api_error:
        # A provider-failure turn, exactly as pi records one: an assistant message with
        # stopReason "error" and no content (see pi_rpc.turn_error).
        messages.append(
            {
                "role": "assistant",
                "content": [],
                "stopReason": "error",
                "errorMessage": api_error,
            }
        )
        return messages
    for i, step in enumerate(steps):
        if "tool" in step:
            tool = str(step["tool"])
            args = dict(step.get("args", {}))
            result = _typed_call(tool, args)
        else:
            tool = "bash"
            args = {"command": str(step.get("command", "true"))}
            result = _bash(args["command"])
        messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "toolCall",
                        "id": f"fake-{i}",
                        "toolName": tool,
                        "input": args,
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "toolResult",
                "toolCallId": f"fake-{i}",
                "content": [{"type": "text", "text": result}],
            }
        )
    if reply:
        messages.append(
            {"role": "assistant", "content": [{"type": "text", "text": reply}]}
        )
    return messages


def main() -> int:
    # Argv is ignored on purpose (the runner passes real pi flags); only the protocol matters.
    script_path = os.environ.get("FAKE_PI_SCRIPT")
    script: list[dict[str, Any]] = []
    if script_path and os.path.exists(script_path):
        with open(script_path) as f:
            script = json.load(f)
    turn = 0
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        event = json.loads(line)
        if event.get("type") != "prompt":
            continue
        prompt = str(event.get("message", ""))
        entry: dict[str, Any] = script[turn] if turn < len(script) else {}
        turn += 1
        messages = _turn_messages(
            prompt,
            list(entry.get("steps", [])),
            str(entry.get("reply", "")),
            api_error=str(entry.get("api_error", "")),
        )
        sys.stdout.write(json.dumps({"type": "agent_end", "messages": messages}) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
