"""Server auth/dispatch tests: seat identity is derived server-side from the bearer token."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from _harness.server import BridgeServer
from _harness.tests.conftest import bridge_for


@pytest.fixture()
def server(tmp_path: Path) -> Iterator[BridgeServer]:
    srv = BridgeServer(bridge_for(tmp_path, "api_key", "team", budget=None))
    srv.start()
    yield srv
    srv.stop()


def _post(
    url: str, token: str | None, payload: dict[str, Any]
) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}
        | ({"X-Seat-Token": token} if token else {}),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_a_call_runs_as_the_seat_its_token_names_whatever_the_payload_says(
    server: BridgeServer,
) -> None:
    a, b = server.bridge.ids[0], server.bridge.ids[1]
    status, payload = _post(
        f"{server.base_url}/agent/call",
        server.token_for(a),
        {"command": "labctl_status", "args": {}},
    )
    assert status == 200
    assert "labctl" in payload["text"] or "job" in payload["text"].lower()
    status, payload = _post(
        f"{server.base_url}/agent/call",
        server.token_for(b),
        {
            "command": "SendMessage",
            "args": {"to": server.bridge.usernames[a], "message": "hi"},
        },
    )
    assert status == 200 and payload["text"] == "Delivered."
    assert server.bridge.nstate["mailbox"][a] == [(server.bridge.usernames[b], "hi")]


def test_a_bad_or_missing_token_is_403_and_an_unknown_endpoint_404(
    server: BridgeServer,
) -> None:
    status, payload = _post(
        f"{server.base_url}/agent/call",
        "wrong",
        {"command": "labctl_status", "args": {}},
    )
    assert status == 403 and payload["text"] == "invalid session token"
    status, _ = _post(
        f"{server.base_url}/agent/call", None, {"command": "labctl_status"}
    )
    assert status == 403
    status, _ = _post(
        f"{server.base_url}/other", server.token_for(server.bridge.ids[0]), {}
    )
    assert status == 404
