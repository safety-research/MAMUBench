"""The real-harness layer shared by the `api_key` and `clinic` evals.

`bridge` hosts an env's own deterministic world behind a small fleet-facing surface, `server` fronts
it on localhost for the seats' typed-tool pi extension (`agent_dir/`), `pi_rpc` drives the `pi --mode
rpc` processes, `runner` plays the lockstep episode, `readout` reads finished run dirs, and `fake_pi`
stands in for pi in the offline suite. Importing the package runs `_paths.bootstrap`, which puts
`eval/`, `eval/_harness/` and the repo root on `sys.path` (the worlds live in each eval's
`environment/` package over `_harness/env_core`).
"""

import sys
from pathlib import Path

_EVALS_DIR = Path(__file__).resolve().parents[1]
if str(_EVALS_DIR) not in sys.path:
    sys.path.insert(0, str(_EVALS_DIR))

from _paths import bootstrap  # noqa: E402

bootstrap()
