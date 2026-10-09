"""Repository and runtime asset locations for the standalone eval."""

import sys
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parent
EVALS_DIR = EVAL_ROOT.parent
REPO_ROOT = EVALS_DIR.parent
PA_HARNESS_DIR = EVAL_ROOT / "harness"


def bootstrap() -> None:
    """Allow direct script execution alongside normal package imports."""
    for path in (EVALS_DIR, EVALS_DIR / "_harness", REPO_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def run_dir_model(model: str) -> str:
    """A model id as it names an episode's run dir (`_providers.path_safe_model`): an OpenRouter id's `/` -> `__`.

    Every paper model id has no `/`, so its run dirs keep their names.
    """
    return model.replace("/", "__")
