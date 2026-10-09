"""Remove provider credentials from stopped pi seats before preserving artifacts."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def remove_pi_auth_files(agent_dirs: Iterable[Path]) -> None:
    """Delete only each known pi agent directory's auth.json; keep session/config artifacts."""
    for agent_dir in agent_dirs:
        (agent_dir / "auth.json").unlink(missing_ok=True)
