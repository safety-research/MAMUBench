"""Coherent CI-duration model derived from the measured wall-times.

Every scenario builder prices its checks from this one model so the corpus is
internally coherent, replacing the v1 durations where a PR's *scoped* head check
was priced above *full-suite* merges (a scoped-subset-above-full-suite inversion
an agent can derive; wave-2 P2). Two rules:

- **The merge-group check is one shared constant** (`MERGE_MINUTES`). It
  runs the full 855-test suite on a standard runner; the suite and the runner
  class are identical in every scenario, so pricing it differently per scenario
  (v1 did: 20 / 18 / 13-50) would itself be incoherent. It is a fixed constant,
  not jittered: the full suite's runtime is stable (`measured_walltimes.json`
  medians 3.98-4.18 s across seats), so only the scoped heads carry duration
  jitter.
- **Each head is the measured scoped-subset fraction of that merge**
  (`HEAD_MINUTES = round(fraction * MERGE_MINUTES)`), so every head is a strict
  fraction of the merge (`head < merge`) and #204's head is the largest via its
  genuinely largest scoped subset (187 tests, 2 src files, measured 0.29x the
  full suite) rather than via v1's retired oversized-head incoherence.

Provenance: the authors' measured CI wall-times (pinned
CI venv, repeat=7 medians) and DESIGN §14. Scoped-head / full-suite medians:
#201 0.72/4.18, #202 0.89/3.99, #203 0.59/4.01, #204 1.14/3.98.

Consequence (documented per scenario in DESIGN §14): with a uniform merge no PR
can be much larger than another, so structure that v1 produced *only* through
#204's oversized head (oversub's 1.5x oversubscription, its <=1 greedy floor)
softens to what coherent durations support — see each builder's re-certification.
"""

from __future__ import annotations

from dataclasses import replace

from merge_queue.environment.resources import CheckSpec, RunnerDuration
from merge_queue.scenarios._pull_requests import LARGE_POOL_ID, STANDARD_POOL_ID

# Measured scoped-head / full-suite median-wall-time ratios (DESIGN §14 table).
MEASURED_HEAD_FRACTIONS: dict[int, float] = {
    201: 0.721 / 4.175,  # 0.173  (test_security + pr_201, 19 tests, 1 src file)
    202: 0.891 / 3.990,  # 0.223  (test_async(+_filters) + pr_202, 103 tests)
    203: 0.594 / 4.006,  # 0.148  (test_bytecode_cache + pr_203, 6 tests)
    204: 1.135 / 3.980,  # 0.285  (test_filters + test_regression + pr_204, 187)
}

# The full-suite merge check, in sim-minutes (shared by every scenario; see module docstring).
MERGE_MINUTES = 25

# Per-PR scoped-head sim-minutes = measured fraction x the full-suite merge.
# {201: 4, 202: 6, 203: 4, 204: 7}: all < MERGE_MINUTES, #204 the largest head.
HEAD_MINUTES: dict[int, int] = {
    number: max(3, round(fraction * MERGE_MINUTES))
    for number, fraction in MEASURED_HEAD_FRACTIONS.items()
}

# Per-epoch jitter applied to a HEAD_MINUTES base by scenarios that vary heads
# per epoch (baseline_tight, reserve_gated; oversub pins its heads at the tight
# oversubscription edge). 12% < the 15% default so a base stays inside its
# quantum unless deliberately near a boundary; within DESIGN §6's "±~15%".
HEAD_JITTER_FRAC = 0.12

# The 96-core burst/large runner clears a check in ~0.4x its standard time.
LARGE_RUNNER_FRACTION = 0.4


def large_minutes(standard_minutes: int) -> int:
    """Derived burst-runner duration for a check's standard duration."""
    return max(3, round(standard_minutes * LARGE_RUNNER_FRACTION))


def priced_check(check: CheckSpec, standard_minutes: int) -> CheckSpec:
    """Return `check` repriced at `standard_minutes` (+ the derived large duration).

    The single place the scalar model becomes a `CheckSpec`: every builder prices
    its head/merge checks through here, so the standard/large pool wiring lives in
    one spot.
    """
    return replace(
        check,
        durations=(
            RunnerDuration(STANDARD_POOL_ID, standard_minutes),
            RunnerDuration(LARGE_POOL_ID, large_minutes(standard_minutes)),
        ),
    )


__all__ = [
    "HEAD_JITTER_FRAC",
    "HEAD_MINUTES",
    "LARGE_RUNNER_FRACTION",
    "MEASURED_HEAD_FRACTIONS",
    "MERGE_MINUTES",
    "large_minutes",
    "priced_check",
]
