#!/usr/bin/env python3
"""exec wrapper for one unprivileged seat: resolve pi, rewrite in-fiction paths, chdir, exec.

The environment's `pi_runtime._spawn_seat` launches the bare name `pi` with the seat's in-fiction
home in its argv (`--session-dir /home/<seat>/.pi/sessions`, `--extension /home/<seat>/.pi/...`).
Inside a container or on a root host those paths are real; on an unprivileged host
`LocalHostShim` materializes them under a private root instead. This wrapper is the
`seat_exec_argv` prefix: it swaps the bare `pi` for the pinned binary the driver resolved (so no
PATH search decides which pi runs) and maps `/home/<seat>` prefixes whose home the shim created
back onto the root. Any other argument passes through untouched; the environment is inherited as
the shim composed it (already remapped). A Python pi (the offline `fake_pi.py`) runs under this
interpreter, so it needs no exec bit (an extraction that drops file modes).

    seat_exec.py <shim-root> <cwd> <pi-executable> <argv...>
"""

from __future__ import annotations

import os
import sys


def rewrite(root: str, arg: str) -> str:
    """Map `/home/<seat>/...` onto `<root>/home/<seat>/...` when that seat home exists."""
    if not arg.startswith("/home/"):
        return arg
    parts = arg.split("/", 3)
    if len(parts) < 3 or not parts[2]:
        return arg
    if not os.path.isdir(os.path.join(root, "home", parts[2])):
        return arg
    return root.rstrip("/") + arg


def main(argv: list[str]) -> int:
    """Rewrite, chdir, exec; returns only when exec itself failed."""
    if len(argv) < 4:
        sys.stderr.write(
            "usage: seat_exec.py <shim-root> <cwd> <pi-executable> <argv...>\n"
        )
        return 2
    root, cwd, pi_executable, *command = argv
    os.chdir(cwd)
    rewritten = [rewrite(root, arg) for arg in command]
    if rewritten and rewritten[0] == "pi":
        rewritten[0] = pi_executable
        if pi_executable.endswith(".py"):
            rewritten.insert(0, sys.executable)
    os.execv(rewritten[0], rewritten)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
