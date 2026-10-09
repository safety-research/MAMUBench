"""Authenticated localhost HTTP transport for the merge-queue world."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import cast

from .engine import NotFoundError, World
from .gh import GhCommandRouter

_MAX_REQUEST_BYTES = 1_000_000


class _BoundServer(ThreadingHTTPServer):
    """HTTP server carrying the world and command router for request handlers."""

    daemon_threads = True

    def __init__(
        self,
        world: World,
        before_command: Callable[[str], None] | None,
    ) -> None:
        self.world = world
        self.router = GhCommandRouter(world)
        self.before_command = before_command
        self._revoked_tokens: set[str] = set()
        self._revoked_tokens_lock = threading.Lock()
        super().__init__(("127.0.0.1", 0), _RequestHandler)

    def revoke_token(self, token: str) -> None:
        """Prevent a previously issued credential from authenticating again."""
        with self._revoked_tokens_lock:
            self._revoked_tokens.add(token)

    def token_is_revoked(self, token: str) -> bool:
        """Return whether `token` has been revoked at the HTTP boundary."""
        with self._revoked_tokens_lock:
            return token in self._revoked_tokens


class _RequestHandler(BaseHTTPRequestHandler):
    """Private request handler; all agent actions use one authenticated endpoint."""

    @property
    def _bound_server(self) -> _BoundServer:
        return cast(_BoundServer, self.server)

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        """Serve a non-mutating readiness probe."""
        if self.path != "/healthz":
            self._json(HTTPStatus.NOT_FOUND, {"error": "endpoint not found"})
            return
        self._json(HTTPStatus.OK, {"ok": True})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        """Execute a CLI command without accepting an actor field from the body."""
        if self.path != "/v1/command":
            self._json(HTTPStatus.NOT_FOUND, {"error": "endpoint not found"})
            return
        actor = self._authenticate()
        if actor is None:
            return
        if self._bound_server.before_command is not None:
            try:
                self._bound_server.before_command(actor)
            except RuntimeError as exc:
                self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
                return
        length_raw = self.headers.get("Content-Length")
        try:
            length = int(length_raw or "0")
        except ValueError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid Content-Length"})
            return
        if not 0 < length <= _MAX_REQUEST_BYTES:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid request size"})
            return
        try:
            decoded = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON request"})
            return
        if not isinstance(decoded, dict):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "request must be an object"})
            return
        body = cast(dict[str, object], decoded)
        raw_argv = body.get("argv")
        if not isinstance(raw_argv, list):
            self._json(
                HTTPStatus.BAD_REQUEST, {"error": "argv must be a list of strings"}
            )
            return
        raw_items = cast(list[object], raw_argv)
        if not all(isinstance(item, str) for item in raw_items):
            self._json(
                HTTPStatus.BAD_REQUEST, {"error": "argv must be a list of strings"}
            )
            return
        stdin_raw = body.get("stdin", "")
        if not isinstance(stdin_raw, str):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "stdin must be a string"})
            return
        argv = [cast(str, item) for item in raw_items]
        result = self._bound_server.router.execute(actor, argv, stdin=stdin_raw)
        self._json(
            HTTPStatus.OK,
            {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        """Suppress wall-clock-bearing default request logs."""
        del format, args

    def _authenticate(self) -> str | None:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "missing credential"})
            return None
        token = header[len(prefix) :]
        if self._bound_server.token_is_revoked(token):
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "revoked credential"})
            return None
        try:
            return self._bound_server.world.actor_for_token(token)
        except NotFoundError:
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "invalid credential"})
            return None

    def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        raw = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class WorldHTTPServer:
    """Lifecycle wrapper for a loopback-only threaded world service."""

    def __init__(
        self,
        world: World,
        *,
        before_command: Callable[[str], None] | None = None,
    ) -> None:
        self.world = world
        self._server = _BoundServer(world, before_command)
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        """Return the loopback URL chosen by the operating system."""
        address = cast(tuple[str, int], self._server.server_address)
        host, port = address
        return f"http://{host}:{port}"

    def start(self) -> "WorldHTTPServer":
        """Start serving in a daemon thread."""
        if self._thread is not None:
            return self
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="merge-queue-world",
            daemon=True,
        )
        self._thread.start()
        return self

    def revoke_token(self, token: str) -> None:
        """Revoke one agent credential for all subsequent service requests."""
        if not token:
            raise ValueError("token must be non-empty")
        self._server.revoke_token(token)

    def close(self) -> None:
        """Stop the server and join its thread."""
        if self._thread is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
        self._thread = None

    def __enter__(self) -> "WorldHTTPServer":
        return self.start()

    def __exit__(self, *_exc: object) -> None:
        self.close()
