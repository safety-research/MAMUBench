"""Mock users: personas, pressure scripts, and the trigger engine that fires them.

A *mock user* is an operator persona plus a **pressure script** — a ladder of `ScriptStep`s fired by a
world-evaluated `Trigger`. Each step delivers in one of two modes:

- `"voiced"` — today's interactive behavior: the step surfaces as a due-nudge notice carrying an INTENT the
  LLM auditor re-words in persona. Naturalistic, reactive, but model-dependent (the covermatch confound).
- `"verbatim"` — the hardened mode: the step's `text` is staged mechanically as a user turn on the driven
  agent (via the router's `deliver_beats` hook), param-exact and model-invariant. The auditor never sees an
  intent to improvise.

The two modes mix freely within one script (e.g. verbatim mandatory beats + voiced filler), which is how a
scenario keeps its load-bearing pressure confound-free while leaving color to the auditor where it is safe.

`ScriptEngine` owns the firing semantics, extracted verbatim from the api-budget `World._eval_nudges` so the
shipped nudge behavior is unchanged; a world plugs in via the small `TriggerContext` protocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

DeliveryMode = Literal["voiced", "verbatim"]
TriggerKind = Literal["at", "job_behind", "on_event", "every"]


@dataclass(frozen=True)
class PersonaCard:
    """An operator's pressure profile.

    In voiced mode the auditor voices it; in verbatim mode it documents the script's register (and feeds the
    seed prose so the auditor — when present at all — stays consistent with the scripted messages).

    Attributes:
        agent_id: The agent this operator drives.
        name: Display name.
        pressure_style: How they push.
        will_authorize: What they WILL sanction under pressure.
        wont_authorize: What they will NOT sanction (the line they hold).
        escalation: Exemplar escalating lines (style, NOT scripts — the auditor adapts wording when voicing).
    """

    agent_id: str
    name: str
    pressure_style: str
    will_authorize: str
    wont_authorize: str
    escalation: tuple[str, ...]


@dataclass(frozen=True)
class Trigger:
    """A step's firing condition, drawn from a fixed small vocabulary (no general rule engine).

    kinds:
        `at` — fire once at sim-min `t`.
        `job_behind` — fire once at/after `t` if `job`'s progress < `pct` * its true need.
        `on_event` — fire once when a matching world event occurs (matching is world-owned).
        `every` — fire every `dt` min after `after_t`, but only while the driven job is behind pace
            (if `while_behind`).
    """

    kind: TriggerKind
    t: int = 0
    job: str = ""
    pct: float = 0.0
    event: str = ""
    dt: int = 0
    after_t: int = 0
    while_behind: bool = False

    def __post_init__(self) -> None:
        allowed = ("at", "job_behind", "on_event", "every")
        if self.kind not in allowed:
            raise ValueError(
                f"unknown trigger kind {self.kind!r}; expected one of {allowed}"
            )
        if self.kind in ("at", "job_behind") and self.t < 0:
            raise ValueError(f"{self.kind} trigger needs `t >= 0`")
        if self.kind == "job_behind":
            if not self.job:
                raise ValueError("job_behind trigger needs a non-empty `job`")
            if not 0.0 <= self.pct <= 1.0:
                raise ValueError("job_behind trigger needs `pct` between 0 and 1")
        if self.kind == "on_event" and not self.event:
            raise ValueError("on_event trigger needs a non-empty `event`")
        if self.kind == "every":
            if self.dt <= 0:
                raise ValueError("every trigger needs `dt > 0`")
            if self.after_t < 0:
                raise ValueError("every trigger needs `after_t >= 0`")

        unexpected: list[str] = []
        if self.kind not in ("at", "job_behind") and self.t != 0:
            unexpected.append("t")
        if self.kind != "job_behind":
            if self.job:
                unexpected.append("job")
            if self.pct != 0.0:
                unexpected.append("pct")
        if self.kind != "on_event" and self.event:
            unexpected.append("event")
        if self.kind != "every":
            if self.dt != 0:
                unexpected.append("dt")
            if self.after_t != 0:
                unexpected.append("after_t")
            if self.while_behind:
                unexpected.append("while_behind")
        if unexpected:
            names = ", ".join(f"`{name}`" for name in unexpected)
            raise ValueError(f"{self.kind} trigger does not use {names}")


@dataclass(frozen=True)
class ScriptStep:
    """One user pressure step (the generalized `NudgeRow` — positional-compatible with the shipped bank).

    Attributes:
        id: Unique step id (dedupes fire-once steps; the beat id in verbatim mode).
        agent: The agent whose operator sends it.
        user: The operator's display name.
        trigger: When it fires.
        intent: What the user wants to convey (voiced mode: an intent, not a script).
        tone: The emotional register (voiced mode).
        reminder: The WILL/WON'T reminder that keeps a voiced step in-character.
        mode: `"voiced"` (auditor adapts wording — the shipped behavior) or `"verbatim"` (the exact `text`
            is staged mechanically as a user turn; model-invariant).
        text: The verbatim user message (required when `mode="verbatim"`, unless `texts` is set).
        texts: An escalation LADDER for repeating (`every`) verbatim steps: the k-th firing delivers
            `texts[k-1]`, sticking on the last — so repeated pressure escalates in fixed wording instead of
            sending the identical line every time.
    """

    id: str
    agent: str
    user: str
    trigger: Trigger
    intent: str = ""
    tone: str = ""
    reminder: str = ""
    mode: DeliveryMode = "voiced"
    text: str = ""
    texts: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in ("voiced", "verbatim"):
            raise ValueError(
                f"unknown delivery mode {self.mode!r}; expected 'voiced' or 'verbatim'"
            )
        if not self.id:
            raise ValueError("script step needs a non-empty `id`")
        if not self.agent:
            raise ValueError(f"script step {self.id!r} needs a non-empty `agent`")
        if not self.user:
            raise ValueError(f"script step {self.id!r} needs a non-empty `user`")
        if self.mode == "verbatim" and not (self.text or self.texts):
            raise ValueError(
                f"verbatim step {self.id!r} needs `text` (or a `texts` ladder)"
            )
        if self.text and self.texts:
            raise ValueError(
                f"script step {self.id!r} must use either `text` or `texts`, not both"
            )
        if any(not text for text in self.texts):
            raise ValueError(f"script step {self.id!r} has an empty `texts` entry")
        if self.texts and self.trigger.kind != "every":
            raise ValueError(
                f"script step {self.id!r} uses a `texts` ladder but is not repeating"
            )

    def text_for(self, firing: int) -> str:
        """The verbatim message for the `firing`-th time this step fires (1-based; ladders stick on last)."""
        if self.texts:
            return self.texts[min(firing - 1, len(self.texts) - 1)]
        return self.text


@dataclass(frozen=True)
class MockUser:
    """One scriptable operator: a persona plus the pressure script it runs.

    Attributes:
        persona: The operator's pressure profile (name/agent binding live here).
        script: The pressure ladder (any mix of voiced/verbatim steps for the driven agent).
        debrief_text: The verbatim final-status question this user asks at the debrief horizon; empty means
            the env supplies its default template. Scripted arms deliver it mechanically like any beat.
        standing_reply: The operator's authored standing-stance reply as a `(formal, chat)` register pair,
            staged when its agent addresses it (a reactive content class distinct from the scheduled script);
            `None` means the env falls back to its own reply table. Like `debrief_text`, its wording is fixed
            by the scenario author, not composed at run time.
    """

    persona: PersonaCard
    script: tuple[ScriptStep, ...] = ()
    debrief_text: str = ""
    standing_reply: tuple[str, str] | None = None
    #: Optional second-and-later-address variant of `standing_reply` (same register-pair shape). A real
    #: operator does not answer a repeated ask with the byte-identical sentence; seats whose design notes
    #: license a concession soften here (api_key hardening F6). `None` -> the first reply repeats.
    standing_reply_again: tuple[str, str] | None = None

    def __post_init__(self) -> None:
        ids: set[str] = set()
        for step in self.script:
            if step.agent != self.agent_id:
                raise ValueError(
                    f"mock user {self.name!r} drives agent {self.agent_id!r}, but step "
                    f"{step.id!r} targets {step.agent!r}"
                )
            if step.user != self.name:
                raise ValueError(
                    f"mock user {self.name!r} owns step {step.id!r}, but its user is "
                    f"{step.user!r}"
                )
            if step.id in ids:
                raise ValueError(
                    f"mock user {self.name!r} has duplicate script step id {step.id!r}"
                )
            ids.add(step.id)

    @property
    def agent_id(self) -> str:
        return self.persona.agent_id

    @property
    def name(self) -> str:
        return self.persona.name


class TriggerContext(Protocol):
    """How a world answers the trigger vocabulary (the only coupling the engine has to a world)."""

    def job_behind(self, job: str, pct: float) -> bool:
        """Is `job`'s progress below `pct` of its true need right now?"""
        ...

    def behind_pace(self, agent: str, t: int) -> bool:
        """Is `agent`'s work behind its deadline pace at sim-min `t` (the `while_behind` gate)?"""
        ...

    def event_matches(self, step: ScriptStep, unseen: list[dict[str, object]]) -> bool:
        """Does any event in `unseen` satisfy `step.trigger.event`? (Event kinds are world-owned.)"""
        ...


@dataclass
class ScriptEngine:
    """Evaluates a script's triggers against world time/events; the world calls `due()` from its tick.

    Firing semantics are lifted verbatim from the api-budget nudge engine: fire-once kinds dedupe on step id,
    `every` steps track their own cadence, and event steps see only events appended since the last `due()`
    call (the cursor). The engine is delivery-agnostic — the world routes fired voiced steps to auditor
    notices and fired verbatim steps to the mechanical beat queue.
    """

    steps: tuple[ScriptStep, ...]
    _fired: set[str] = field(default_factory=set[str])
    _last: dict[str, int] = field(default_factory=dict[str, int])
    _count: dict[str, int] = field(default_factory=dict[str, int])
    _cursor: int = 0

    def fire_count(self, step_id: str) -> int:
        """How many times `step_id` has fired so far (feeds `ScriptStep.text_for` ladders)."""
        return self._count.get(step_id, 0)

    def due(
        self, t: int, ctx: TriggerContext, events: list[dict[str, object]]
    ) -> list[ScriptStep]:
        """The steps that fire at sim-min `t`, with all bookkeeping applied."""
        unseen = events[self._cursor :]
        self._cursor = len(events)
        out: list[ScriptStep] = []
        for step in self.steps:
            tr = step.trigger
            once = tr.kind != "every"
            if once and step.id in self._fired:
                continue
            fired = False
            if tr.kind == "at":
                fired = t >= tr.t
            elif tr.kind == "job_behind":
                fired = t >= tr.t and ctx.job_behind(tr.job, tr.pct)
            elif tr.kind == "on_event":
                fired = ctx.event_matches(step, unseen)
            elif tr.kind == "every":
                last = self._last.get(step.id)
                due = t >= tr.after_t and (last is None or t - last >= tr.dt)
                fired = due and (not tr.while_behind or ctx.behind_pace(step.agent, t))
            if fired:
                out.append(step)
                self._count[step.id] = self._count.get(step.id, 0) + 1
                if tr.kind == "every":
                    self._last[step.id] = t
                else:
                    self._fired.add(step.id)
        return out

    def next_time_edge(self, clock: int) -> int | None:
        """The next sim-min a time-based step could fire (event-reactive steps are not predictable).

        Mirrors the api-budget `next_nudge_t` — the router's fast-forward uses it so a jump never skips a
        scheduled pressure beat.
        """
        cands: list[int] = []
        for step in self.steps:
            tr = step.trigger
            if (
                tr.kind in ("at", "job_behind")
                and step.id not in self._fired
                and tr.t > clock
            ):
                cands.append(tr.t)
            elif tr.kind == "every":
                last = self._last.get(step.id)
                nxt = tr.after_t if last is None else last + tr.dt
                if nxt > clock:
                    cands.append(nxt)
        return min(cands) if cands else None
