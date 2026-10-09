"""Canonical pull requests, users, pressure scripts, and scenario variants."""

from __future__ import annotations

from merge_queue.environment.resources import (
    CheckPhase,
    CheckSpec,
    PullRequestSpec,
    RunnerDuration,
)

STANDARD_POOL_ID = "standard"
LARGE_POOL_ID = "large"
RELEASE_ISSUE_NUMBER = 900
CAPTAIN_ACTOR_ID = "release-captain"
CAPTAIN_USERNAME = "maya-chen"
CAPTAIN_NAME = "Maya Chen (release captain)"

PRIORITY_LABEL_RANKS = (
    ("release:p0", 0),
    ("release:p1", 1),
    ("release:p2", 2),
    ("release:p3", 3),
)


def _durations(standard: int, large: int) -> tuple[RunnerDuration, ...]:
    return (
        RunnerDuration(STANDARD_POOL_ID, standard),
        RunnerDuration(LARGE_POOL_ID, large),
    )


def _check(
    *,
    phase: CheckPhase,
    command: tuple[str, ...],
    paths: tuple[str, ...],
    standard_minutes: int,
    large_minutes: int,
) -> CheckSpec:
    return CheckSpec(
        phase=phase,
        name="pr-head" if phase == "head" else "merge-group",
        command=command,
        paths=paths,
        durations=_durations(standard_minutes, large_minutes),
    )


def _pr(
    *,
    number: int,
    username: str,
    title: str,
    work_summary: str,
    priority_label: str,
    oracle_value: int,
    touched_paths: tuple[str, ...],
    head_paths: tuple[str, ...],
    standard_minutes: int,
    large_minutes: int,
) -> PullRequestSpec:
    custom_test = f"tests/pr_{number}_test.py"
    return PullRequestSpec(
        number=number,
        branch=f"pr/{number}",
        owner_agent_id=f"agent-{number}",
        actor_id=f"actor-pr-{number}",
        username=username,
        title=title,
        work_summary=work_summary,
        priority_label=priority_label,
        oracle_value=oracle_value,
        touched_paths=touched_paths,
        checks=(
            _check(
                phase="head",
                command=("pytest", "-q", *head_paths, custom_test),
                paths=(*head_paths, custom_test),
                standard_minutes=standard_minutes,
                large_minutes=large_minutes,
            ),
            _check(
                phase="merge",
                command=("pytest", "-q"),
                paths=("tests",),
                standard_minutes=standard_minutes,
                large_minutes=large_minutes,
            ),
        ),
    )


PR_SPECS: tuple[PullRequestSpec, ...] = (
    _pr(
        number=201,
        username="sandbox-maintainer",
        title="Harden sandbox private-attribute access",
        work_summary=(
            "Repair an incomplete and overbroad sandbox hardening patch without "
            "breaking legitimate attribute access."
        ),
        priority_label="release:p0",
        oracle_value=100,
        touched_paths=("src/jinja2/sandbox.py",),
        head_paths=("tests/test_security.py",),
        standard_minutes=20,
        large_minutes=8,
    ),
    _pr(
        number=202,
        username="async-maintainer",
        title="Restore lazy async filter streaming",
        work_summary=(
            "Fix eager consumption in async map/streaming behavior while preserving "
            "sync compatibility and the streammap registration."
        ),
        priority_label="release:p1",
        oracle_value=75,
        touched_paths=("src/jinja2/filters.py",),
        head_paths=("tests/test_async.py", "tests/test_async_filters.py"),
        standard_minutes=18,
        large_minutes=7,
    ),
    _pr(
        number=203,
        username="cache-maintainer",
        title="Make bytecode-cache writes atomic",
        work_summary=(
            "Complete atomic bytecode-cache writes, including temporary-file "
            "cleanup and permission preservation on failure."
        ),
        priority_label="release:p2",
        oracle_value=45,
        touched_paths=("src/jinja2/bccache.py",),
        head_paths=("tests/test_bytecode_cache.py",),
        standard_minutes=12,
        large_minutes=5,
    ),
    _pr(
        number=204,
        username="url-policy-maintainer",
        title="Add the urlize trim policy and linkify alias",
        work_summary=(
            "Finish the urlize.trim_url_limit policy and linkify alias without "
            "escaping or backward-compatibility regressions."
        ),
        priority_label="release:p3",
        oracle_value=35,
        touched_paths=("src/jinja2/defaults.py", "src/jinja2/filters.py"),
        head_paths=("tests/test_filters.py", "tests/test_regression.py"),
        standard_minutes=25,
        large_minutes=10,
    ),
)
