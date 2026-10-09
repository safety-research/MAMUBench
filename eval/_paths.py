"""Import paths for the four evals and their small shared runtime."""

from __future__ import annotations

import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
HARNESS_DIR = EVALS_DIR / "_harness"


def bootstrap(*paths: Path) -> None:
    """Put the evals and their shared helpers on `sys.path`.

    `paths[0]` ends up first. Idempotent: an entry already present is moved, not duplicated.
    """
    for path in reversed(paths or (EVALS_DIR, HARNESS_DIR, REPO_ROOT)):
        entry = str(path)
        if entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)
