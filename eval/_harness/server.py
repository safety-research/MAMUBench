"""Localhost HTTP front for `EpisodeBridge` — what the pi extension talks to.

One endpoint: `POST /agent/call {"command": <tool name>, "args": {...}}`, authenticated by the per-seat
`X-Seat-Token` header (an unguessable token minted per seat per episode; the seat identity is derived from
the token server-side, so one seat cannot impersonate another by editing its own env). Serialization lives
in the bridge itself (its `RLock` covers dispatch AND the runner's turn calls) — in lockstep mode calls
only ever arrive from the one seat currently taking its turn, so the lock is a correctness backstop, not a
throughput concern.

The server binds 127.0.0.1 on an ephemeral port; the runner threads it up per episode and hands each pi
process `LABCTL_SERVER`/`LABCTL_TOKEN` via its (minimal) environment.
"""

from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

from _harness.bridge import EpisodeBridge


class BridgeServer:
    """Serve one episode's bridge on `host`:<ephemeral>; `base_url` after `start()`.

    `host` stays 127.0.0.1 except the Linux docker tier, where container→host traffic arrives on the
    docker bridge interface, not the loopback (auth is the per-seat token either way).
    """

    def __init__(self, bridge: EpisodeBridge, *, host: str = "127.0.0.1") -> None:
        self.bridge = bridge
        self.host = host
        self._seat_tokens: dict[str, str] = {
            seat: secrets.token_urlsafe(24) for seat in bridge.ids
        }
        self.tokens: dict[str, str] = {t: s for s, t in self._seat_tokens.items()}
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def token_for(self, seat: str) -> str:
        """The seat's bearer token (goes into that pi process's env as `LABCTL_TOKEN`)."""
        return self._seat_tokens[seat]

    @property
    def port(self) -> int:
        assert self._httpd is not None, "server not started"
        return int(self._httpd.server_address[1])

    @property
    def base_url(self) -> str:
        host = "127.0.0.1" if self.host == "0.0.0.0" else self.host  # noqa: S104 — bind-all serves loopback too
        return f"http://{host}:{self.port}"

    def start(self) -> None:
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass  # keep pi's stdio clean; the bridge ledger is the record

            def _reply(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/agent/call":
                    self._reply(404, {"text": "unknown endpoint"})
                    return
                seat = server.tokens.get(self.headers.get("X-Seat-Token", ""))
                if seat is None:
                    self._reply(403, {"text": "invalid session token"})
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    parsed: Any = json.loads(self.rfile.read(length) or b"{}")
                    if not isinstance(parsed, dict):
                        raise TypeError("request body must be a JSON object")
                    payload = cast("dict[str, Any]", parsed)
                    command = str(payload.get("command", ""))
                    raw_args: Any = payload.get("args")
                    args: dict[str, Any] = (
                        cast("dict[str, Any]", raw_args)
                        if isinstance(raw_args, dict)
                        else {}
                    )
                except (ValueError, TypeError):
                    self._reply(400, {"text": "malformed request"})
                    return
                try:
                    text = server.bridge.dispatch(seat, command, args)
                except Exception as e:  # noqa: BLE001 — surface, never hang the tool call
                    self._reply(500, {"text": f"internal error: {type(e).__name__}"})
                    raise
                self._reply(200, {"text": text})

        self._httpd = ThreadingHTTPServer((self.host, 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
