"""pytest bootstrap for everything under `eval/`: the import roots every eval's tests rely on."""

from __future__ import annotations

import sys
from pathlib import Path

_EVALS_DIR = Path(__file__).resolve().parent
if str(_EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(_EVALS_DIR))

from _paths import bootstrap  # noqa: E402

bootstrap()
