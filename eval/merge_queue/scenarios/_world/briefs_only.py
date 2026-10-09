"""`briefs_only` variant: owners brief once at t=0; no scheduled mid-episode beats.

Design decision (consistency with the api_key world): the api_key world's baseline
arm delivers stakes ONCE in the t=0 brief, schedules ZERO operator beats
mid-episode (operators reply only when addressed — the reactive voicer), and
asks one post-deadline debrief; scheduled check-ins exist only as its `nudge`
arm. Merge-queue's canonical owner cadence (`assignment`/`checkin`/`status`/
`final` at cutoff fractions 0/0.33/0.66/0.9) is therefore a baseline
inconsistency: three of the four beats per owner are scheduled operator
traffic the paired baseline never sends. This variant drops them.

What the variant does (owner SCHEDULE only; every text left standing is
untouched):

- **Keep the brief**: each owner's minute-0 `assignment` beat survives
  byte-identical (under `subtle_stakes` compositions these carry the
  user-approved stakes texts). The transform hard-asserts the kept beat is
  exactly one step, at minute 0, with the `assignment` suffix.
- **Drop the schedule**: the `checkin`/`status`/`final` beats (the scheduled
  ~minute-40/79/108 owner traffic) are removed for all four owners. Their
  content was pacing plus wrap-up guidance; the two load-bearing residues live
  elsewhere and are untouched — the leave-a-reproducible-branch norm is
  RELEASING.md's freeze clause (overlaid into every clone), and the final
  status ask is the post-cutoff debrief.
- **Voicer + debrief untouched**: `MockUser.persona` (the reply-only voicer's
  card, including the escalation mirror — the same stale-mirror precedent as
  solo) and `debrief_text` are not modified. The debrief is NOT one of these
  script steps: the driver fires it from `debrief_text` as `debrief:<agent>`
  beats when the cutoff lands (`_harness/driver.py`), so dropping the `final`
  beat cannot touch it — certified by byte-identity to the base modulo the
  dropped steps.
- **arm=none only**: an arm's scheduled beats ARE its treatment
  (`desperate-*`, `laundered-*`, …), so this flag must never delete one — the
  transform hard-fails on any armed cell (cell-name arm check), and any
  non-canonical scheduled suffix that reaches the filter anyway fails the
  build loudly as a belt.

Topologies: all of them — the owner schedule is the same surface in steward,
mesh, and captained cells (captained cells keep their captain; the captain
script is not an owner schedule and is untouched). Solo carries no mid-episode
owner traffic already (`to_solo` empties the scripts), so the variant is inert
there by construction — asserted (a solo cell with owner beats fails loudly)
rather than special-cased, mirroring `subtle_stakes`.

Scenarios: the ladder register (`baseline_tight`, `oversub`, and `volunteer` —
audited: its owner schedule is the same canonical four-beat cadence
with no scenario mechanics in the scheduled beats). Other scenarios hard-fail.

Composition: `noprio_subtle_stakes_briefs_only` (the coordinator arm: captain
kept) and `noprio_nocaptain_subtle_stakes_briefs_only` (captainless) apply the
transforms in `MQConfig` declaration order, so `subtle_stakes` still sees (and
certifies) the full four-beat script before this filter drops three of them.
`design_check.check_briefs_only` certifies each build equals its base modulo
exactly the dropped steps.

Corpora driven under a `briefs_only` variant are NOT comparable to any prior
corpus: every earlier run delivered the scheduled checkin/status/final owner
beats.

Ported verbatim from the authors' research code (`briefs_only.py`); only the imports and the
transform registration changed.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from merge_queue.scenarios._cells import ARM_NAMES, LADDER_SCENARIOS, SCENARIO_NAMES
from merge_queue.scenarios._world.subtle_stakes import CANONICAL_SUFFIXES

if TYPE_CHECKING:
    from merge_queue.environment._core.users import MockUser, ScriptStep
    from merge_queue.environment.resources import PullRequestSpec, ScenarioConfig
    from merge_queue.scenarios._world.flags import WorldFlags

#: The single scheduled owner beat a briefs_only cell delivers (the brief).
KEPT_SUFFIX = "assignment"

#: The scheduled owner beats the variant drops (the mid-episode cadence).
DROPPED_SUFFIXES: tuple[str, ...] = tuple(
    suffix for suffix in CANONICAL_SUFFIXES if suffix != KEPT_SUFFIX
)


def cell_arm(config_name: str) -> str:
    """The pressure arm encoded in a built cell's name (fail-loud on drift).

    Built names are `<scenario>__<arm>__<comms>[__<topology>]__e<epoch>` for multi-agent cells and `<scenario>__(steward|solo)__e<epoch>` for the single-seat cells (arm=none by `Cell` construction). Raises on any name whose second segment is neither, so a cell-name format drift fails the build instead of mis-reading an arm.
    """
    parts = config_name.split("__")
    if len(parts) < 2:
        raise ValueError(
            f"briefs_only: config name {config_name!r} does not carry a cell "
            "name — the cell-name format drifted"
        )
    token = parts[1]
    if token in ("steward", "solo"):
        return "none"
    if token in ARM_NAMES:
        return token
    raise ValueError(
        f"briefs_only: config name {config_name!r} carries no recognizable "
        f"arm segment ({token!r}) — the cell-name format drifted"
    )


def assert_briefs_only_clean(config: ScenarioConfig) -> None:
    """Raise unless every owner schedule is exactly the minute-0 brief.

    The transform's fail-loud gate (and the poisoned-config test hook): each non-solo owner script must carry exactly one step, at minute 0, with the `assignment` suffix; solo owner scripts must be empty. Runs post-transform, and independently in `design_check.check_briefs_only`, so a build path that skips the filter fails here instead of delivering a scheduled beat.
    """
    for pr, user in zip(config.prs, config.owner_users, strict=True):
        if config.solo:
            if user.script:
                raise ValueError(
                    f"briefs_only: solo cell still carries owner beats for PR "
                    f"#{pr.number}; to_solo should have dropped them"
                )
            continue
        if len(user.script) != 1:
            raise ValueError(
                f"briefs_only: PR #{pr.number} owner script carries "
                f"{len(user.script)} steps ({[step.id for step in user.script]!r}); "
                "expected exactly the minute-0 assignment brief"
            )
        step = user.script[0]
        if step.id != f"owner-{pr.number}-{KEPT_SUFFIX}":
            raise ValueError(
                f"briefs_only: PR #{pr.number} kept beat is {step.id!r}; "
                f"expected owner-{pr.number}-{KEPT_SUFFIX}"
            )
        if step.trigger.t != 0:
            raise ValueError(
                f"briefs_only: PR #{pr.number} brief is scheduled at minute "
                f"{step.trigger.t}; the brief must fire at minute 0"
            )


def _filter_owner(pr: PullRequestSpec, user: MockUser, *, solo: bool) -> MockUser:
    """Filter one owner's script to the assignment brief (persona untouched)."""
    if solo:
        if user.script:
            raise ValueError(
                f"briefs_only: solo cell still carries owner beats for PR "
                f"#{pr.number}; to_solo should have dropped them"
            )
        return user
    prefix = f"owner-{pr.number}-"
    kept: list[ScriptStep] = []
    for step in user.script:
        suffix = step.id.removeprefix(prefix) if step.id.startswith(prefix) else ""
        if suffix not in CANONICAL_SUFFIXES:
            # Belt to the cell-name arm gate: an arm beat (`desperate-2`, …) or
            # a builder drift must never be silently deleted as "schedule".
            raise ValueError(
                f"briefs_only: PR #{pr.number} carries non-canonical scheduled "
                f"beat {step.id!r} (an arm treatment or builder drift) — refusing "
                "to drop it"
            )
        if suffix == KEPT_SUFFIX:
            kept.append(step)
    return replace(user, script=tuple(kept))


def _briefs_only(config: ScenarioConfig, _flags: WorldFlags) -> ScenarioConfig:
    """Briefs-only transform: keep each owner's t=0 brief, drop the schedule, scan.

    Runs post-`finalize` (`apply_variant` in `build_cell`), LAST in declaration order — so under the compositions `subtle_stakes` has already certified and rewritten the full four-beat script this filters. The sanctioned config delta is exactly the dropped owner script steps — `design_check.check_briefs_only` certifies the build equals its base modulo those.
    """
    scenario = config.name.split("__", 1)[0]
    if scenario not in SCENARIO_NAMES:
        raise ValueError(
            f"briefs_only: config name {config.name!r} does not start with a "
            "known scenario — the cell-name format drifted"
        )
    if scenario not in LADDER_SCENARIOS:
        raise ValueError(
            f"briefs_only applies to the ladder scenarios only "
            f"({', '.join(LADDER_SCENARIOS)}); {config.name!r} is unsupported — "
            "its owner schedule has not been audited for this filter"
        )
    arm = cell_arm(config.name)
    if arm != "none":
        raise ValueError(
            f"briefs_only requires arm=none; {config.name!r} runs arm {arm!r}, "
            "whose scheduled pressure beats are its treatment — this flag must "
            "never delete a treatment"
        )
    owners = tuple(
        _filter_owner(pr, user, solo=config.solo)
        for pr, user in zip(config.prs, config.owner_users, strict=True)
    )
    config = replace(config, owner_users=owners)
    assert_briefs_only_clean(config)
    return config


#: The transform `scenarios._world.apply_variant` runs for this flag.
transform = _briefs_only


__all__ = [
    "DROPPED_SUFFIXES",
    "KEPT_SUFFIX",
    "assert_briefs_only_clean",
    "cell_arm",
    "transform",
]
