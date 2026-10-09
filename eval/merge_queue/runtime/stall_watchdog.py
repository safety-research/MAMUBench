"""In-runner per-episode stall watchdog: turn the stall-inflated tail into the median.

Merge-queue episodes have a long right tail (median ~23 min, p90 ~46, max ~181) that
is not work — it is waiting. The env's own defences bound *some* of it:
`_harness/process.run_turn` arms a `threading.Timer(turn_timeout)` that SIGKILLs
the pi process group, and the voicer bounds its own HTTP call. What
neither covers is a driver thread that is wedged somewhere those timers do not
reach (a pi leader that ignores its kill, an un-timed `subprocess.run`, a stuck
filesystem call). Today that is caught by hand, by the standing ops rule "no
DONE.json + no deep write for >30 min -> kick it". This module runs that rule
inside the runner.

Three things make the mechanism unusual enough to spell out:

**There is no episode process to kill.** `drive_episode` is synchronous and the
runner calls it via `anyio.to_thread.run_sync(..., abandon_on_cancel=False)`, so
an episode is a *thread* of the runner process. A thread cannot be killed. What
can be killed is the episode's pi process groups: each `spawn_pi` uses
`start_new_session=True`, so every pi leader is its own process-group leader, and
its children (tool subshells) share that group. Killing them makes the next
`run_turn` fail its RPC write, which the driver classifies as `crashed` and
retires — the episode drains through the driver's *own* recovery path within
milliseconds, ends without a DONE.json, and releases its run-dir lease normally
in `drive_episode`'s `finally`. No lease stealing is involved.

**The threshold must clear the driver's own watchdog.** A legitimate episode can
sit with no deep write for a full `turn_timeout` (1800 s) while `run_turn`'s timer
runs down, and the driver then *recovers* that seat (requeue beats, respawn,
re-wake next round). Killing at exactly 30 min would preempt that recoverable path
and convert a survivable flaky turn into a discarded episode. So the effective
threshold is `max(--stall-minutes, turn_timeout + margin)` — see
`effective_stall_seconds`. By construction, only a stall the driver's own timer
could not resolve gets here.

**Kick counts live beside the run dir, not inside it.** `prepare_run_dir`
quarantines every run-dir entry except the lock and the `.workdir` marker into
`.attempt<N>.failed/` at the start of each attempt, so a counter stored in the run
dir would be erased by the very retry it exists to count. Records live in
`<runs_dir>/.stall_kicks/<run_name>.json` instead.
"""

from __future__ import annotations

import json
import os
import signal
import threading
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

# One episode is killed at most twice: a first stall is a kick-and-requeue, a
# second stall of the same episode is terminal. `abandon` is the state after
# that — logged once, never acted on again, so a wedged episode cannot spin.
StallAction = Literal["wait", "kill", "kill_sticky", "abandon"]

DEFAULT_STALL_MINUTES = 30.0
# Poll cadence and post-kill grace. The loop is an `Event.wait`, so a watch costs
# one sleeping thread per in-flight episode (<=8 at the runner's --parallel) and
# ~20 stat calls per poll; it never spins.
DEFAULT_POLL_SECONDS = 30.0
DEFAULT_GRACE_SECONDS = 300.0
# Headroom over `turn_timeout` before a quiet episode counts as stalled, so the
# driver's own per-turn timer always gets to run down and recover first.
DEFAULT_TURN_TIMEOUT_MARGIN = 300.0

KICK_DIR_NAME = ".stall_kicks"

LogFn = Callable[[str], None]


def _print_log(message: str) -> None:
    print(message, flush=True)


def effective_stall_seconds(
    *,
    stall_minutes: float,
    turn_timeout: float,
    margin: float = DEFAULT_TURN_TIMEOUT_MARGIN,
) -> float:
    """Seconds of no-progress that count as a stall, or 0 when disabled.

    Raised to `turn_timeout + margin` when the requested window would fire inside
    the driver's own per-turn watchdog: an episode waiting out a `run_turn` timeout
    is not wedged, it is about to be recovered by the driver (missed wake, respawn,
    re-wake), and killing it there would discard a recoverable realization.
    """
    if stall_minutes <= 0:
        return 0.0
    return max(stall_minutes * 60.0, turn_timeout + margin)


def stall_action(
    *,
    now: float,
    last_progress: float,
    stall_seconds: float,
    kicks: int,
    killed_at: float | None,
    grace_seconds: float,
) -> StallAction:
    """Decide what a watch should do this poll (pure).

    `last_progress` is the newest mtime across the episode's progress artifacts (or
    the watch's start time before anything is written), `kicks` the episode's
    lifetime kick count including prior processes, and `killed_at` the time of this
    watch's last kill. A kill is given `grace_seconds` to land before the episode is
    judged again, so the drain-and-teardown window after a successful kill is not
    mistaken for a fresh stall.
    """
    if stall_seconds <= 0:
        return "wait"
    if kicks >= 2 and killed_at is not None:
        return "abandon"
    if killed_at is not None and now - killed_at < grace_seconds:
        return "wait"
    if now - last_progress < stall_seconds:
        return "wait"
    if kicks <= 0:
        return "kill"
    if kicks == 1:
        return "kill_sticky"
    return "abandon"


@dataclass(frozen=True)
class KickRecord:
    """One episode's lifetime stall history, persisted across invocations."""

    kicks: int = 0
    sticky: bool = False
    last_kick: str | None = None


class KickStore:
    """Per-episode kick counts under `<runs_dir>/.stall_kicks/`.

    Kept outside the run dir because `prepare_run_dir` quarantines run-dir content
    at the start of every attempt; a counter inside would not survive the retry it
    is counting. Records are operator-clearable: delete the json to give a
    failed-sticky episode a fresh budget.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir

    def path_for(self, run_name: str) -> Path:
        """The record path for `run_name` (not guaranteed to exist)."""
        return self._base / f"{run_name}.json"

    def read(self, run_name: str) -> KickRecord:
        """This episode's record, or an empty one when absent/corrupt."""
        try:
            raw = cast(
                dict[str, object],
                json.loads(self.path_for(run_name).read_text(encoding="utf-8")),
            )
        except (OSError, ValueError):
            return KickRecord()
        kicks = raw.get("kicks")
        last_kick = raw.get("last_kick")
        return KickRecord(
            kicks=kicks if isinstance(kicks, int) else 0,
            sticky=raw.get("sticky") is True,
            last_kick=last_kick if isinstance(last_kick, str) else None,
        )

    def record_kick(self, run_name: str, *, sticky: bool) -> KickRecord:
        """Add one kick to `run_name`'s record and return the new state."""
        current = self.read(run_name)
        updated = KickRecord(
            kicks=current.kicks + 1,
            sticky=current.sticky or sticky,
            last_kick=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self._base.mkdir(parents=True, exist_ok=True)
        path = self.path_for(run_name)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(
                {
                    "kicks": updated.kicks,
                    "sticky": updated.sticky,
                    "last_kick": updated.last_kick,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
        return updated

    def clear(self, run_name: str) -> None:
        """Forget `run_name`'s stall history (an episode that ran without stalling)."""
        self.path_for(run_name).unlink(missing_ok=True)


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _newest(paths: Iterable[Path]) -> float | None:
    stamps = [stamp for stamp in (_mtime(path) for path in paths) if stamp is not None]
    return max(stamps) if stamps else None


def progress_mtime(run_dir: Path, agent_root: Path | None = None) -> float | None:
    """Newest mtime across an episode's progress artifacts, or None if none exist.

    Three depths, cheapest first, because each catches a different stall:

    - the run dir's own entries (`turns.jsonl` per completed turn, `voicer.jsonl`
      per voiced reply, and the terminal `episode.json` / `git_archaeology.json`
      that a draining episode writes) — a non-recursive scan, ~8 entries;
    - `service/events.jsonl`, appended and flushed per world event, so it advances
      *within* a turn as the agent drives the service through its `gh` shim;
    - each seat's pi session jsonl and stderr, the deepest write there is: pi
      appends to its session file as the model streams, so this is the signal that
      goes quiet the moment a provider call hangs.

    Both the de-identified live root (where the agent trees live during the
    episode) and the run dir (where the driver moves them at teardown) are probed,
    so the signal does not blink out at the handover.
    """
    roots = [root for root in (agent_root, run_dir) if root is not None]
    candidates: list[Path] = [run_dir / "service" / "events.jsonl"]
    try:
        candidates.extend(Path(entry.path) for entry in os.scandir(run_dir))
    except OSError:
        pass
    for root in roots:
        agents = root / "agents"
        try:
            seats = [Path(entry.path) for entry in os.scandir(agents) if entry.is_dir()]
        except OSError:
            continue
        for seat in seats:
            candidates.append(seat / "stderr.log")
            try:
                candidates.extend((seat / "sessions").glob("*.jsonl"))
            except OSError:
                continue
    return _newest(candidates)


def _proc_cwd(pid: int) -> Path | None:
    """Resolve `pid`'s working directory, or None when it is not readable."""
    try:
        target = os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None
    # A cwd whose directory has been unlinked reads back as "<path> (deleted)".
    return Path(target.removesuffix(" (deleted)"))


def _under_any(path: Path, roots: Sequence[Path]) -> bool:
    return any(path == root or root in path.parents for root in roots)


def episode_process_groups(roots: Sequence[Path]) -> tuple[int, ...]:
    """Process-group ids of live processes working inside one of `roots`.

    Attribution is by working directory: an episode's pi leaders are spawned with
    `cwd` set to a workspace under the episode's own live root, so a cwd under
    `roots` is proof the process belongs to this episode. Only groups are returned
    — a pi leader is its own group leader (`start_new_session=True`), so its tool
    subshells are reached through it even if they have since cd'd elsewhere.

    Never reports this process or its own group, so a caller can never signal
    itself, and silently skips processes owned by other users (their `/proc`
    entries are unreadable, which is exactly the isolation we want).
    """
    resolved = [root.resolve() for root in roots]
    own_pid = os.getpid()
    own_pgid = os.getpgid(0)
    groups: set[int] = set()
    try:
        entries = list(os.scandir("/proc"))
    except OSError:
        return ()
    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == own_pid:
            continue
        cwd = _proc_cwd(pid)
        if cwd is None or not _under_any(cwd, resolved):
            continue
        try:
            pgid = os.getpgid(pid)
        except OSError:
            continue
        if pgid <= 1 or pgid == own_pgid:
            continue
        groups.add(pgid)
    return tuple(sorted(groups))


def kill_episode_processes(
    roots: Sequence[Path], *, sig: int = signal.SIGKILL
) -> tuple[int, ...]:
    """SIGKILL every process group working inside `roots`; return the ids killed."""
    killed: list[int] = []
    for pgid in episode_process_groups(roots):
        try:
            os.killpg(pgid, sig)
        except OSError:
            continue
        killed.append(pgid)
    return tuple(killed)


class StallWatch:
    """Watch one in-flight episode and kick it when it stops making progress.

    Used as a context manager around the `drive_episode` call; the watch thread is
    a daemon and stops on exit, so it can never outlive the runner. A watch with
    `stall_seconds <= 0` starts no thread at all — that is how `--stall-minutes 0`
    opts out with zero overhead.
    """

    def __init__(
        self,
        *,
        run_name: str,
        run_dir: Path,
        agent_root: Path | None,
        store: KickStore,
        stall_seconds: float,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        grace_seconds: float = DEFAULT_GRACE_SECONDS,
        log: LogFn = _print_log,
    ) -> None:
        self._run_name = run_name
        self._run_dir = run_dir
        self._agent_root = agent_root
        self._store = store
        self._stall_seconds = stall_seconds
        self._poll_seconds = poll_seconds
        self._grace_seconds = grace_seconds
        self._log = log
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._killed_at: float | None = None
        self.kicks = 0

    @property
    def kicked(self) -> bool:
        """Whether this watch had to kick its episode."""
        return self.kicks > 0

    def __enter__(self) -> StallWatch:
        if self._stall_seconds > 0:
            self._thread = threading.Thread(
                target=self._loop,
                name=f"stall-watch:{self._run_name}",
                daemon=True,
            )
            self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stop.set()
        if self._thread is not None:
            # `_stop.set()` wakes the loop's `Event.wait` immediately, so this
            # returns at once; the bounded join only guards against a poll caught
            # mid-probe, and the thread re-checks `_stop` before it can act again.
            self._thread.join(timeout=5.0)
            self._thread = None

    def _roots(self) -> tuple[Path, ...]:
        roots = [self._run_dir]
        if self._agent_root is not None:
            roots.append(self._agent_root)
        return tuple(roots)

    def _loop(self) -> None:
        started = time.time()
        abandoned = False
        while not self._stop.wait(self._poll_seconds):
            if (self._run_dir / "DONE.json").is_file():
                return
            last = progress_mtime(self._run_dir, self._agent_root)
            action = stall_action(
                now=time.time(),
                last_progress=started if last is None else last,
                stall_seconds=self._stall_seconds,
                kicks=self._store.read(self._run_name).kicks,
                killed_at=self._killed_at,
                grace_seconds=self._grace_seconds,
            )
            if action == "wait" or self._stop.is_set():
                continue
            if action == "abandon":
                if not abandoned:
                    abandoned = True
                    self._log(
                        f"[stall] {self._run_name}: still no progress after the "
                        "kill; the driver thread is wedged outside pi and cannot "
                        "be reclaimed in-process. Leaving it and moving on."
                    )
                continue
            self._kick(sticky=action == "kill_sticky")

    def _kick(self, *, sticky: bool) -> None:
        quiet_minutes = self._stall_seconds / 60.0
        killed = kill_episode_processes(self._roots())
        self._killed_at = time.time()
        self.kicks += 1
        record = self._store.record_kick(self._run_name, sticky=sticky)
        groups = ", ".join(str(pgid) for pgid in killed) or "none found"
        if sticky:
            self._log(
                f"[stall] {self._run_name}: stalled again after a prior kick "
                f"(no progress for >{quiet_minutes:.0f} min); killed process "
                f"groups [{groups}] and marked it FAILED-STICKY — it will not be "
                f"retried. Clear {self._store.path_for(self._run_name)} to retry."
            )
        else:
            self._log(
                f"[stall] {self._run_name}: no progress for >{quiet_minutes:.0f} "
                f"min and no DONE.json; killed process groups [{groups}]. The "
                f"episode will finish incomplete and is retryable "
                f"(kick {record.kicks})."
            )
