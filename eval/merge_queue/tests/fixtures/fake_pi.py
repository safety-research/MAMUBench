#!/usr/bin/env python3
"""An offline stand-in for `pi --mode rpc` in the merge-queue driver (tests only: no model, no network).

The driver's RPC contract (`runtime.process.run_turn`): read one `{"type": "prompt"}` line from stdin,
answer with a terminal `agent_end` event. Each turn this stand-in appends one line to a session JSONL
under `--session-dir` (the structural gate counts non-empty session files per seat) and answers with a
short question to the requester (a non-empty final text, so the driver neither retires the seat as empty
nor skips the voicer). On its first turn it writes `<session-dir>/../seat.json`: its argv, its cwd, and
which of AGENTS.md / RELEASING.md it can see there.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPLY = "Checked the queue; nothing to change this round. Anything you need from me?"


def main() -> int:
    argv = sys.argv[1:]
    sessions = Path(argv[argv.index("--session-dir") + 1])
    sessions.mkdir(parents=True, exist_ok=True)
    turn = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("type") != "prompt":
            continue
        turn += 1
        if turn == 1:
            (sessions.parent / "seat.json").write_text(
                json.dumps(
                    {
                        "argv": argv,
                        "cwd": os.getcwd(),
                        "agents_md": Path("AGENTS.md").is_file(),
                        "releasing_md": Path("RELEASING.md").is_file(),
                    },
                    indent=1,
                )
            )
        prompt = str(event.get("message", ""))
        with (sessions / "fake-session.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"turn": turn, "prompt": prompt[:200]}) + "\n")
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": [{"type": "text", "text": REPLY}]},
        ]
        sys.stdout.write(json.dumps({"type": "agent_end", "messages": messages}) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
