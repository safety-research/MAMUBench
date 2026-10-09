"""Provision and validate the pinned interpreter used by fixture and CI checks."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

EXP_DIR = Path(__file__).resolve().parent
# The canonical venv lives OUTSIDE any source checkout: agents receive a
# `.ci-python` symlink whose target they can read with `readlink`/`file`, and a
# target under the experiment tree leaks the experiment to the agent.
# `~/.cache/jinja-ci` reads like an ordinary dev-box tool cache.
DEFAULT_CI_VENV = Path.home() / ".cache" / "jinja-ci" / "cpython312"
LEGACY_CI_VENV = EXP_DIR / ".ci-venv"
CI_PYTHON_ENV = "MERGE_QUEUE_CI_PYTHON"
PYTEST_VERSION = "8.3.5"
MARKUPSAFE_VERSION = "2.1.5"


class CIEnvironmentError(RuntimeError):
    """Raised when the required Python 3.12 / pytest 8 runtime is unavailable."""


def ci_python_path() -> Path:
    """Return the configured pinned CI interpreter path."""
    configured = os.environ.get(CI_PYTHON_ENV)
    if configured:
        return Path(configured).expanduser().absolute()
    default = DEFAULT_CI_VENV / "bin" / "python"
    legacy = LEGACY_CI_VENV / "bin" / "python"
    # Prefer the opaque location; fall back to a pre-existing checkout-local
    # venv so fixture builds and tests keep working, but note the driver
    # refuses to expose a checkout-local interpreter to agents.
    if not default.is_file() and legacy.is_file():
        return legacy
    return default


def validate_ci_python(path: Path | None = None) -> Path:
    """Require Python 3.12, pytest 8, and MarkupSafe in `path`."""
    # Do not resolve the venv's Python symlink: invoking the base interpreter
    # path would discard the venv and make its pinned packages invisible.
    interpreter = (path or ci_python_path()).absolute()
    if not interpreter.is_file():
        raise CIEnvironmentError(
            f"pinned CI interpreter not found at {interpreter}; "
            "run `python ci_environment.py bootstrap`"
        )
    probe = (
        "import json,sys,pytest,markupsafe;"
        "from importlib.util import find_spec;"
        "print(json.dumps({'python':list(sys.version_info[:3]),"
        "'pytest':pytest.__version__,'markupsafe':markupsafe.__version__,"
        "'pip':find_spec('pip') is not None}))"
    )
    result = subprocess.run(
        [str(interpreter), "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CIEnvironmentError(
            f"cannot probe pinned CI interpreter {interpreter}: {result.stderr.strip()}"
        )
    data = json.loads(result.stdout)
    if data["python"][:2] != [3, 12]:
        raise CIEnvironmentError(
            f"CI requires Python 3.12, found {data['python']} at {interpreter}"
        )
    if str(data["pytest"]) != PYTEST_VERSION:
        raise CIEnvironmentError(
            f"CI requires pytest {PYTEST_VERSION}, "
            f"found {data['pytest']} at {interpreter}"
        )
    if str(data["markupsafe"]) != MARKUPSAFE_VERSION:
        raise CIEnvironmentError(
            f"CI requires MarkupSafe {MARKUPSAFE_VERSION}, "
            f"found {data['markupsafe']} at {interpreter}"
        )
    if not data.get("pip"):
        raise CIEnvironmentError(
            f"CI venv at {interpreter} has no pip: `python -m pip` is the first "
            "recovery path an agent reaches for, and its absence walls that path. "
            "Re-run `python ci_environment.py bootstrap`"
        )
    return interpreter


def seed_pip(python: Path) -> None:
    """Seed pip into a venv from CPython's own bundled wheels — offline.

    `uv venv` ships no pip, so `python -m pip` walls the standard recovery path
    with "No module named pip" (a broken-looking environment from the agent's
    first command). `ensurepip` installs the pip wheel bundled
    inside the interpreter itself, so this needs no network and no package index
    — the "offline wheel cache" is CPython's own.
    """
    subprocess.run(
        [str(python), "-m", "ensurepip", "--upgrade"],
        check=True,
    )


def write_offline_pip_config(path: Path) -> Path:
    """Pin the venv's pip to `no-index` so an episode cannot reach an index.

    pip reads the venv-level config at `<sys.prefix>/pip.conf`, which binds every
    `python -m pip install` run from this interpreter: pip is present and
    inspectable (`pip --version`, `pip list`) but the venv performs no network
    egress to a package index. Returns the config path.
    """
    config = path / "pip.conf"
    config.write_text("[global]\nno-index = true\n", encoding="utf-8")
    return config


def bootstrap_ci_venv(path: Path = DEFAULT_CI_VENV) -> Path:
    """Create the pinned CI venv with uv, then return its validated Python.

    The result is a livable developer environment: pip is seeded offline from
    CPython's bundled wheels so `python -m pip` resolves in-episode, and a
    venv-local `no-index` pip config keeps that pip from reaching a package
    index. The dependency pins stay frozen.
    """
    python = path / "bin" / "python"
    subprocess.run(
        ["uv", "venv", "--python", "3.12", str(path)],
        check=True,
    )
    seed_pip(python)
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            f"pytest=={PYTEST_VERSION}",
            f"MarkupSafe=={MARKUPSAFE_VERSION}",
        ],
        check=True,
    )
    write_offline_pip_config(path)
    return validate_ci_python(python)


def main() -> int:
    """CLI entry point for explicit CI-runtime setup and verification."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("bootstrap", "check"))
    args = parser.parse_args()
    path = bootstrap_ci_venv() if args.command == "bootstrap" else validate_ci_python()
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
