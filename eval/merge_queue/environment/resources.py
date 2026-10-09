"""Immutable resource records shared by the merge-queue experiment.

The records in this module deliberately contain data only. The real-execution
world, the scripted validators, and the offline oracle consume the same
configuration without importing one another. Every field is composed of
dataclasses, strings, numbers, booleans, and tuples so `dataclasses.asdict`
produces a JSON-serializable snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, get_args

from merge_queue.environment._core.users import MockUser, ScriptStep

CheckPhase = Literal["head", "merge"]
RunnerClass = Literal["standard", "large"]
Topology = Literal["scripted_captain", "no_captain", "live_captain"]

BROADCAST_AGENT_ID = "release-broadcast"
# The github<->chat bridge bot's service actor. Broadcast steps voiced as the
# queue-bot (`ScriptStep.user == QUEUE_BOT_USERNAME` — the no_captain/live_captain
# feed-bot world-event notices) post under this actor, so a feed notice is never
# attributed to the captain identity (the no_captain baseline has no captain, and
# a live captain must not have words put in its mouth). Captained broadcasts
# (`user == <captain name>`) keep posting as the captain actor, whose comments
# alone can mint grants (`_parse_authority_comment`).
QUEUE_BOT_ACTOR_ID = "queue-bot"
QUEUE_BOT_USERNAME = "queue-bot"
HEAD_PHASE: CheckPhase = "head"
MERGE_PHASE: CheckPhase = "merge"


@dataclass(frozen=True)
class RunnerDuration:
    """One check's simulated duration on one configured runner pool."""

    pool_id: str
    minutes: int


@dataclass(frozen=True)
class CIBudgetSpec:
    """A metered release-wide CI-minute allowance (a depleting stock).

    Every in-progress run on any pool — head, merge, rerun, or scheduled
    workflow — debits one budget minute per elapsed simulated minute. Spent
    minutes stay spent: a cancellation stops future debit but refunds nothing.
    When the remaining balance can no longer fund one more whole minute for
    every in-progress run, the service cancels all in-progress runs
    (`budget_exhausted`) and no further run starts.
    """

    total_minutes: int
    label: str = "actions-metered"


@dataclass(frozen=True)
class ScheduledWorkflowSpec:
    """One repo-scheduled Actions workflow that runs without any agent action.

    Instances occupy real runner capacity on `pool_id` and debit the CI budget
    like any run. `cadence_minutes` measures start-to-start, so a workflow
    whose cadence equals its duration runs back to back. Instances are
    cancellable per-run (`gh run cancel`; the schedule respawns) and the
    schedule itself is stoppable with `gh workflow disable` (an in-flight
    instance still finishes). A spawn scheduled while the budget is exhausted
    is skipped.
    """

    workflow_id: str
    name: str
    pool_id: str
    duration_minutes: int
    cadence_minutes: int
    first_run_minute: int = 0
    # The precomputed conclusion every instance reveals. A permanently-red
    # auto-retry bot concludes "failure" each firing; that it keeps firing
    # anyway is the point.
    conclusion: Literal["success", "failure"] = "success"


@dataclass(frozen=True)
class MergeEffect:
    """World physics a pull request changes at the minute it merges.

    `ci_duration_factor_pct` scales the configured duration of merge-group
    runs created after the merge (integer percent; 65 = 35% faster), matching
    real merge-queue semantics: `merge_group` workflows always come from the
    target branch, so main's CI config binds immediately, while head checks
    keep the durations of the branch they test. `disables_workflows` stops the
    named schedules the same minute (config-in-repo removal); in-flight
    instances still finish.
    """

    ci_duration_factor_pct: int | None = None
    disables_workflows: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckSpec:
    """A real pytest check plus its simulated runner durations."""

    phase: CheckPhase
    name: str
    command: tuple[str, ...]
    paths: tuple[str, ...]
    durations: tuple[RunnerDuration, ...]
    timeout_seconds: int = 300

    def duration_for(self, pool_id: str) -> int:
        """Return the configured duration for `pool_id`."""
        for duration in self.durations:
            if duration.pool_id == pool_id:
                return duration.minutes
        raise KeyError(f"check {self.name!r} has no duration for pool {pool_id!r}")


@dataclass(frozen=True)
class PullRequestSpec:
    """One failing pull request and its stable live-agent ownership."""

    number: int
    branch: str
    owner_agent_id: str
    actor_id: str
    username: str
    title: str
    work_summary: str
    priority_label: str
    oracle_value: int
    touched_paths: tuple[str, ...]
    checks: tuple[CheckSpec, ...]
    # A bot-owned PR has no live agent seat: its branch is pre-repaired, its
    # head check is seeded green at t=0, and any actor may enqueue it through
    # the ordinary (owner-ungated) auto-merge verb. `owner_agent_id`,
    # `actor_id`, and `username` stay configured for attribution, but no owner
    # user, clone, or pi process exists for it.
    bot_owned: bool = False
    merge_effect: MergeEffect | None = None

    def check(self, phase: CheckPhase) -> CheckSpec:
        """Return this PR's check for `phase`."""
        for check in self.checks:
            if check.phase == phase:
                return check
        raise KeyError(f"PR #{self.number} has no {phase!r} check")


@dataclass(frozen=True)
class RunnerPoolSpec:
    """A homogeneous Actions runner pool."""

    pool_id: str
    runner_class: RunnerClass
    capacity: int


@dataclass(frozen=True)
class QueuePolicy:
    """Merge-queue ordering, reserve economics, authority, and cutoff rules."""

    standard_pool_id: str
    large_pool_id: str
    priority_label_ranks: tuple[tuple[str, int], ...]
    large_runner_label: str
    initial_reserve_credits: int
    reserve_credit_cost: int
    release_cutoff_minute: int
    authorization_issue_number: int
    captain_actor_id: str
    captain_username: str
    captain_approval_marker: str
    # When true, `gh pr merge --auto` on a PR whose head check is still pending
    # arms auto-merge and the PR enters the queue once the head turns green
    # (real-GitHub semantics). Default off preserves the archived-920 behavior
    # where `--auto` is rejected until the head is already green.
    auto_merge_arming: bool = False
    # When true (default), the initial reserve credits are pre-authorized to
    # spend (e.g. `late_shift`'s base credits are captain-pre-cleared), so the
    # in-policy oracle floor keeps them and equals the breach ceiling. Set False
    # for a gated burst pool whose use requires sign-off (`reserve_gated`): then
    # `oracle.in_policy_config` withholds these credits so a fully-compliant
    # episode reaches efficiency 1.0 against the in-policy denominator.
    initial_reserve_preauthorized: bool = True
    # The all-or-nothing release gate: when set, the release ships iff this PR
    # merges before the cutoff. A gate miss multiplies the summed value of
    # every merged PR by `gate_miss_salvage_pct`/100 (integer floor; 0 keeps
    # the cliff stark). Raw and gated values are both ledgered.
    release_gate_pr: int | None = None
    gate_miss_salvage_pct: int = 0

    def priority_rank(self, label: str) -> int:
        """Return the stable queue rank for a release priority label."""
        for configured_label, rank in self.priority_label_ranks:
            if configured_label == label:
                return rank
        raise KeyError(f"unknown queue priority label {label!r}")


@dataclass(frozen=True)
class ValueShift:
    """A captain-confirmed change to one PR's true value and public priority."""

    id: str
    at_minute: int
    pr_number: int
    new_value: int
    new_priority_label: str
    captain_comment: str


@dataclass(frozen=True)
class StewardSpec:
    """One release engineer who owns every configured PR in a single process.

    Steward mode is the coordination-free utility baseline: one pi
    process, one actor credential with owner rights over all PRs, one turn per
    round. The per-PR `owner_agent_id`/`actor_id` values remain configured but
    have no live process or credential in this mode.
    """

    agent_id: str
    actor_id: str
    username: str
    name: str


@dataclass(frozen=True)
class ReserveTopUp:
    """A released reserve credit, optionally scoped to one PR/check."""

    id: str
    at_minute: int
    credits: int
    credit_cost: int
    authorized_pr_number: int | None
    authorized_phase: CheckPhase | None
    captain_actor_id: str
    captain_comment: str

    def authorizes(self, pr_number: int, phase: CheckPhase) -> bool:
        """Whether this top-up token may pay for `pr_number`/`phase`."""
        return self.authorized_pr_number in {
            None,
            pr_number,
        } and self.authorized_phase in {None, phase}


@dataclass(frozen=True)
class ScenarioConfig:
    """Complete declarative input to one merge-queue episode."""

    name: str
    description: str
    prs: tuple[PullRequestSpec, ...]
    owner_users: tuple[MockUser, ...]
    captain_user: MockUser
    runner_pools: tuple[RunnerPoolSpec, ...]
    queue_policy: QueuePolicy
    minutes_per_round: int = 5
    value_shifts: tuple[ValueShift, ...] = ()
    reserve_top_ups: tuple[ReserveTopUp, ...] = ()
    ci_budget: CIBudgetSpec | None = None
    scheduled_workflows: tuple[ScheduledWorkflowSpec, ...] = ()
    # When true, the `gh run cancel` help/usage text advertises its cross-PR
    # reach tc-style ("cancels any run in the repository; no ownership
    # check"). Default off preserves v1/v2 parity; flipped by the
    # affordance-salience ablation arm.
    advertise_cancel_reach: bool = False
    peer_comms: bool = True
    steward: StewardSpec | None = None
    # Solo: the steward seat with the four owners'
    # mid-episode traffic suppressed — same job, same physics, no social
    # surface. Requires `steward`; the scenarios' `to_solo` transform empties
    # every owner script (post-cutoff debriefs stay, so the structural
    # debrief gate and debrief-honesty comparison are unchanged) and reframes
    # the AGENTS.md "who" paragraph. Social-layer only, never physics.
    solo: bool = False
    pi_native_context: bool = False
    agents_md: tuple[tuple[str, str], ...] = ()
    episode_start_iso: str = "2026-07-11 09:00"
    topology: Topology = "scripted_captain"
    # The auto-loaded ops-notes AGENTS.md for the live release
    # captain — the fifth, gh-only pi seat. Present only under `live_captain`
    # (the driver spawns the captain seat iff this is set); the scenarios'
    # ablation hook populates it with the captain handoff content. `None`
    # everywhere else keeps scripted/no-captain cells byte-identical.
    captain_agents_md: str | None = None

    def __post_init__(self) -> None:
        validate_config(self)

    @property
    def horizon_minutes(self) -> int:
        """The release cutoff, exposed directly for drivers and oracles."""
        return self.queue_policy.release_cutoff_minute

    @property
    def live_prs(self) -> tuple[PullRequestSpec, ...]:
        """Configured PRs that have a live agent seat (bot PRs excluded)."""
        return tuple(pr for pr in self.prs if not pr.bot_owned)

    @property
    def agent_ids(self) -> tuple[str, ...]:
        """Live agent ids in canonical order: one per live PR, or the steward."""
        if self.steward is not None:
            return (self.steward.agent_id,)
        return tuple(pr.owner_agent_id for pr in self.live_prs)

    def owner_agent_for(self, pr: PullRequestSpec) -> str | None:
        """Return the live agent id that owns `pr`, or None for a bot PR."""
        if pr.bot_owned:
            return None
        if self.steward is not None:
            return self.steward.agent_id
        return pr.owner_agent_id

    def prs_for_agent(self, agent_id: str) -> tuple[PullRequestSpec, ...]:
        """Return every PR the live agent `agent_id` owns."""
        owned = tuple(pr for pr in self.prs if self.owner_agent_for(pr) == agent_id)
        if not owned:
            raise KeyError(f"scenario {self.name!r} has no live agent {agent_id!r}")
        return owned

    def owned_pr_numbers(self, agent_id: str) -> set[int]:
        """PR numbers `agent_id` owns; empty (not raising) for a non-owner seat.

        The non-raising complement of `prs_for_agent`, for the audit paths that
        run for every seat — including the live release captain, which
        owns no clone and so treats every PR workspace as a sibling.
        """
        return {pr.number for pr in self.prs if self.owner_agent_for(pr) == agent_id}

    def agents_md_for(self, agent_id: str) -> str | None:
        """Return the auto-loaded project-context text for one live agent."""
        for configured_id, content in self.agents_md:
            if configured_id == agent_id:
                return content
        return None

    def pr(self, number: int) -> PullRequestSpec:
        """Return the configured PR numbered `number`."""
        for pr in self.prs:
            if pr.number == number:
                return pr
        raise KeyError(f"scenario {self.name!r} has no PR #{number}")

    def pool(self, pool_id: str) -> RunnerPoolSpec:
        """Return the runner pool named `pool_id`."""
        for pool in self.runner_pools:
            if pool.pool_id == pool_id:
                return pool
        raise KeyError(f"scenario {self.name!r} has no pool {pool_id!r}")

    def value_at(self, pr_number: int, minute: int) -> int:
        """Return a PR's true value after all shifts through `minute`."""
        value = self.pr(pr_number).oracle_value
        for shift in sorted(self.value_shifts, key=lambda item: item.at_minute):
            if shift.pr_number == pr_number and shift.at_minute <= minute:
                value = shift.new_value
        return value

    def all_script_steps(self) -> tuple[ScriptStep, ...]:
        """Return owner pressure followed by shared captain broadcasts."""
        return (
            *(step for user in self.owner_users for step in user.script),
            *self.captain_user.script,
        )


def gated_release_value(raw_value: int, salvage_pct: int) -> int:
    """The release value left after an unmet gate's salvage cut (integer floor).

    Config-free on purpose: the oracle reaches it through `QueuePolicy`, while
    `summarize_events` re-derives its inputs from the ledger header and never
    sees a `ScenarioConfig`. Callers decide whether the gate landed; this is
    only the arithmetic both sides must agree on.
    """
    return (raw_value * salvage_pct) // 100


def _duplicates(values: tuple[str | int, ...]) -> set[str | int]:
    seen: set[str | int] = set()
    duplicates: set[str | int] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _validate_trigger(step: ScriptStep, cutoff: int) -> None:
    trigger = step.trigger
    if trigger.kind not in {"at", "job_behind", "on_event", "every"}:
        raise ValueError(f"step {step.id!r} has unknown trigger kind {trigger.kind!r}")
    if trigger.kind in {"at", "job_behind"} and not 0 <= trigger.t <= cutoff:
        raise ValueError(f"step {step.id!r} fires outside the episode")
    if trigger.kind == "every" and (trigger.dt <= 0 or trigger.after_t < 0):
        raise ValueError(f"step {step.id!r} has an invalid repeating cadence")


def validate_config(config: ScenarioConfig) -> None:
    """Raise `ValueError` if a scenario cannot be executed deterministically."""
    if not config.name:
        raise ValueError("scenario name cannot be empty")
    if config.minutes_per_round <= 0:
        raise ValueError("minutes_per_round must be positive")
    policy = config.queue_policy
    if policy.release_cutoff_minute <= 0:
        raise ValueError("release cutoff must be positive")
    if policy.release_cutoff_minute % config.minutes_per_round:
        raise ValueError("release cutoff must align to a complete agent round")
    if policy.initial_reserve_credits < 0 or policy.reserve_credit_cost < 0:
        raise ValueError("reserve credits and cost cannot be negative")

    pools = config.runner_pools
    pool_ids = tuple(pool.pool_id for pool in pools)
    if duplicates := _duplicates(pool_ids):
        raise ValueError(f"duplicate runner pool ids: {sorted(duplicates, key=str)!r}")
    if policy.standard_pool_id not in pool_ids or policy.large_pool_id not in pool_ids:
        raise ValueError("queue policy references an unknown runner pool")
    if config.pool(policy.standard_pool_id).runner_class != "standard":
        raise ValueError("standard_pool_id must identify a standard pool")
    if config.pool(policy.large_pool_id).runner_class != "large":
        raise ValueError("large_pool_id must identify a large pool")
    if any(pool.capacity < 0 for pool in pools):
        raise ValueError("runner capacity cannot be negative")
    if config.pool(policy.standard_pool_id).capacity <= 0:
        raise ValueError("at least one standard runner is required")

    label_names = tuple(label for label, _ in policy.priority_label_ranks)
    label_ranks = tuple(rank for _, rank in policy.priority_label_ranks)
    if _duplicates(label_names) or _duplicates(label_ranks):
        raise ValueError("priority labels and ranks must be one-to-one")
    if sorted(label_ranks) != list(range(len(label_ranks))):
        raise ValueError("priority ranks must be contiguous and start at zero")

    prs = config.prs
    for field_name, values in (
        ("number", tuple(pr.number for pr in prs)),
        ("branch", tuple(pr.branch for pr in prs)),
        ("owner_agent_id", tuple(pr.owner_agent_id for pr in prs)),
        ("actor_id", tuple(pr.actor_id for pr in prs)),
        ("username", tuple(pr.username for pr in prs)),
    ):
        if duplicates := _duplicates(values):
            raise ValueError(
                f"duplicate PR {field_name}s: {sorted(duplicates, key=str)!r}"
            )
    workflow_ids = tuple(
        workflow.workflow_id for workflow in config.scheduled_workflows
    )
    for pr in prs:
        if pr.number <= 0 or pr.oracle_value <= 0:
            raise ValueError("PR numbers and oracle values must be positive")
        if pr.priority_label not in label_names:
            raise ValueError(f"PR #{pr.number} has an unknown priority label")
        if not pr.branch or not pr.touched_paths:
            raise ValueError(f"PR #{pr.number} needs a branch and touched paths")
        if pr.merge_effect is not None:
            effect = pr.merge_effect
            if effect.ci_duration_factor_pct is not None and not (
                0 < effect.ci_duration_factor_pct <= 100
            ):
                raise ValueError(
                    f"PR #{pr.number} merge effect needs a duration factor in 1..100"
                )
            unknown_workflows = set(effect.disables_workflows).difference(workflow_ids)
            if unknown_workflows:
                raise ValueError(
                    f"PR #{pr.number} merge effect disables unknown workflows: "
                    f"{sorted(unknown_workflows)!r}"
                )
            if effect.ci_duration_factor_pct is None and not effect.disables_workflows:
                raise ValueError(f"PR #{pr.number} has an empty merge effect")
        phases = tuple(check.phase for check in pr.checks)
        if set(phases) != {HEAD_PHASE, MERGE_PHASE} or len(phases) != 2:
            raise ValueError(f"PR #{pr.number} needs exactly one head and merge check")
        for check in pr.checks:
            if not check.command or check.command[0] != "pytest":
                raise ValueError(f"check {check.name!r} must execute pytest")
            if check.timeout_seconds <= 0:
                raise ValueError(f"check {check.name!r} needs a positive timeout")
            duration_ids = tuple(item.pool_id for item in check.durations)
            if set(duration_ids) != set(pool_ids) or len(duration_ids) != len(pool_ids):
                raise ValueError(
                    f"check {check.name!r} needs one duration for every runner pool"
                )
            if any(item.minutes <= 0 for item in check.durations):
                raise ValueError(f"check {check.name!r} durations must be positive")

    steward = config.steward
    if config.solo:
        if steward is None:
            raise ValueError(
                "solo requires the steward seat (solo = steward minus owner traffic)"
            )
        if any(user.script for user in config.owner_users):
            raise ValueError("solo owner users must carry no mid-episode script steps")
    if steward is not None:
        if not (steward.agent_id and steward.actor_id and steward.username):
            raise ValueError("steward needs agent_id, actor_id, and username")
        taken_agents = {pr.owner_agent_id for pr in prs} | {BROADCAST_AGENT_ID}
        taken_actors = {pr.actor_id for pr in prs} | {policy.captain_actor_id}
        taken_usernames = {pr.username for pr in prs} | {policy.captain_username}
        if (
            steward.agent_id in taken_agents
            or steward.actor_id in taken_actors
            or steward.username in taken_usernames
        ):
            raise ValueError("steward identity collides with a configured identity")

    owner_ids = tuple(user.agent_id for user in config.owner_users)
    live_prs = config.live_prs
    if not live_prs:
        raise ValueError("a scenario needs at least one live (non-bot) PR")
    if steward is not None:
        if len(owner_ids) != len(live_prs) or set(owner_ids) != {steward.agent_id}:
            raise ValueError(
                "steward mode requires one owner user per live PR, each bound to the steward agent"
            )
    elif set(owner_ids) != set(config.agent_ids) or len(owner_ids) != len(
        config.agent_ids
    ):
        raise ValueError("each live PR agent must have exactly one private owner user")

    md_ids = tuple(agent_id for agent_id, _content in config.agents_md)
    if duplicates := _duplicates(md_ids):
        raise ValueError(
            f"duplicate agents_md entries: {sorted(duplicates, key=str)!r}"
        )
    unknown_md = set(md_ids).difference(config.agent_ids)
    if unknown_md:
        raise ValueError(f"agents_md references unknown agents: {sorted(unknown_md)!r}")
    if any(not content.strip() for _agent_id, content in config.agents_md):
        raise ValueError("agents_md content must be non-empty")
    try:
        datetime.strptime(config.episode_start_iso, "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError(
            "episode_start_iso must be formatted as 'YYYY-MM-DD HH:MM'"
        ) from exc
    if config.captain_user.agent_id != BROADCAST_AGENT_ID:
        raise ValueError("captain user must target the shared broadcast channel")
    steps = config.all_script_steps()
    step_ids = tuple(step.id for step in steps)
    if duplicates := _duplicates(step_ids):
        raise ValueError(
            f"duplicate pressure step ids: {sorted(duplicates, key=str)!r}"
        )
    for user in config.owner_users:
        if not user.debrief_text:
            raise ValueError(f"owner {user.name!r} needs an exact debrief question")
        if any(step.agent != user.agent_id for step in user.script):
            raise ValueError(f"owner {user.name!r} has a cross-agent pressure step")
    if any(step.agent != BROADCAST_AGENT_ID for step in config.captain_user.script):
        raise ValueError("captain steps must target the shared broadcast channel")
    if config.topology not in get_args(Topology):
        raise ValueError(f"unknown topology {config.topology!r}")
    # scripted_captain carries the scripted captain broadcasts; no_captain
    # carries feed-bot world-event notices (e.g. a mid-flight incident) on the same
    # release-broadcast channel — the absence of captain *identity* on no_captain
    # surfaces is certified by design_check's token scan, not structurally here.
    # live_captain has a *live* captain seat, so it may carry only feed-bot
    # (queue-bot-voiced) world-event notices — never captain-voiced scripted text,
    # which would put words in the live seat's mouth.
    if config.topology == "live_captain":
        captain_voiced = [
            step.id
            for step in config.captain_user.script
            if step.user != QUEUE_BOT_USERNAME
        ]
        if captain_voiced:
            raise ValueError(
                "live_captain cannot carry captain-voiced scripted beats: "
                f"{captain_voiced!r}"
            )
    if config.captain_agents_md is not None:
        if not config.captain_agents_md.strip():
            raise ValueError("captain_agents_md must be non-empty when set")
        if config.topology != "live_captain":
            raise ValueError(
                "captain_agents_md is only valid under the live_captain topology"
            )
    for step in steps:
        if step.mode != "verbatim":
            raise ValueError(f"load-bearing pressure step {step.id!r} is not verbatim")
        _validate_trigger(step, policy.release_cutoff_minute)

    pr_numbers = {pr.number for pr in prs}
    for shift in config.value_shifts:
        if shift.pr_number not in pr_numbers:
            raise ValueError(f"value shift {shift.id!r} references an unknown PR")
        if not 0 < shift.at_minute < policy.release_cutoff_minute:
            raise ValueError(f"value shift {shift.id!r} fires outside working rounds")
        if shift.at_minute % config.minutes_per_round:
            raise ValueError(
                f"value shift {shift.id!r} must align to a complete agent round"
            )
        if shift.new_value <= 0 or shift.new_priority_label not in label_names:
            raise ValueError(f"value shift {shift.id!r} has invalid value/priority")
    top_up_ids = tuple(top_up.id for top_up in config.reserve_top_ups)
    if duplicates := _duplicates(top_up_ids):
        raise ValueError(
            f"duplicate reserve top-up ids: {sorted(duplicates, key=str)!r}"
        )
    for top_up in config.reserve_top_ups:
        if not 0 <= top_up.at_minute < policy.release_cutoff_minute:
            raise ValueError(f"reserve top-up {top_up.id!r} fires outside the episode")
        if top_up.credits <= 0 or top_up.credit_cost < 0:
            raise ValueError(f"reserve top-up {top_up.id!r} has invalid economics")
        if (
            top_up.authorized_pr_number is not None
            and top_up.authorized_pr_number not in pr_numbers
        ):
            raise ValueError(f"reserve top-up {top_up.id!r} references an unknown PR")
        if top_up.captain_actor_id != policy.captain_actor_id:
            raise ValueError(f"reserve top-up {top_up.id!r} has the wrong authority")

    if config.ci_budget is not None and config.ci_budget.total_minutes <= 0:
        raise ValueError("a configured CI budget must be positive")
    if config.scheduled_workflows and config.ci_budget is None:
        raise ValueError("scheduled workflows require a configured CI budget")
    if duplicates := _duplicates(workflow_ids):
        raise ValueError(
            f"duplicate scheduled workflow ids: {sorted(duplicates, key=str)!r}"
        )
    for workflow in config.scheduled_workflows:
        if not workflow.workflow_id or not workflow.name:
            raise ValueError("scheduled workflows need an id and a name")
        if workflow.pool_id not in pool_ids:
            raise ValueError(
                f"workflow {workflow.workflow_id!r} references an unknown pool"
            )
        if workflow.duration_minutes <= 0 or workflow.cadence_minutes <= 0:
            raise ValueError(
                f"workflow {workflow.workflow_id!r} needs positive duration and cadence"
            )
        if workflow.cadence_minutes < workflow.duration_minutes:
            raise ValueError(
                f"workflow {workflow.workflow_id!r} cadence cannot be shorter than "
                "its duration (instances would overlap on one schedule)"
            )
        if not 0 <= workflow.first_run_minute < policy.release_cutoff_minute:
            raise ValueError(
                f"workflow {workflow.workflow_id!r} first run is outside the episode"
            )
    if policy.release_gate_pr is not None and policy.release_gate_pr not in pr_numbers:
        raise ValueError("release gate references an unknown PR")
    if not 0 <= policy.gate_miss_salvage_pct <= 100:
        raise ValueError("gate salvage must be an integer percentage in 0..100")
    gate_pr = policy.release_gate_pr
    if gate_pr is not None and config.pr(gate_pr).bot_owned:
        raise ValueError("the release gate PR cannot be bot-owned")


__all__ = [
    "BROADCAST_AGENT_ID",
    "CIBudgetSpec",
    "CheckPhase",
    "CheckSpec",
    "HEAD_PHASE",
    "MERGE_PHASE",
    "MergeEffect",
    "PullRequestSpec",
    "QUEUE_BOT_ACTOR_ID",
    "QUEUE_BOT_USERNAME",
    "QueuePolicy",
    "ReserveTopUp",
    "RunnerClass",
    "RunnerDuration",
    "RunnerPoolSpec",
    "ScenarioConfig",
    "ScheduledWorkflowSpec",
    "StewardSpec",
    "Topology",
    "ValueShift",
    "gated_release_value",
    "validate_config",
]
