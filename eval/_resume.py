"""The resume guard: a completed episode is reused only under the configuration that recorded it."""

from __future__ import annotations

from typing import Any


def configuration_drift(
    prior: dict[str, Any], expected: dict[str, Any]
) -> dict[str, tuple[Any, Any]]:
    """Reject changed behavior or unversioned output; Git labels may change for identical settings."""
    return {
        key: (prior.get(key), value)
        for key, value in expected.items()
        if key not in {"commit", "formation"} and prior.get(key) != value
    }
