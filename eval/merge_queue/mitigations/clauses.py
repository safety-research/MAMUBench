"""The mitigation arms' AGENTS.md clauses: the crew charter, the release manager's order, the repair-loop ideas.

Every working merge-queue mitigation in the paper is prompt-only: a trailing section appended to the
AGENTS.md pi auto-loads into a seat's `<project_context>` (the four owners', or the live team lead's
ops notes). Nothing gates a tool and no server check exists; owners keep their merge rights. Ported
verbatim from the authors' research code:

- `crew_charter` (`SEAT_HEADING`, `CREW_CHARTER_CLAUSE`, `scan_clause_texts`, `append_clause`, the
  applicability gates). The lead clause stack beside it (`lead_portfolio`, `lead_value`, `seat_defer`,
  `lead_release`: ladder rungs r2-r8) did not work and is not ported.
- `lead_priorities` / `seat_priorities` (the order to land in, rendered per world from the hidden PR values,
  numbers only).
- `loop_idea`, reading the committed selections `selected_round1.json` and
  `selected_round2.json` (vendored beside this module, byte-identical to the research repair loop's
  selection files), restricted to the three ideas this eval ships.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from merge_queue.scenarios._cells import (
    CAPTAINED_TOPOLOGIES,
    LADDER_SCENARIOS,
    SCENARIO_NAMES,
)
from merge_queue.scenarios._world import nocaptain, noprio
from merge_queue.scenarios._world.briefs_only import cell_arm
from merge_queue.scenarios._world.flags import (
    PAPER_CAPTAINED,
    PAPER_CAPTAINLESS,
    WorldFlags,
)

if TYPE_CHECKING:
    from merge_queue.environment.resources import ScenarioConfig

Transform = Callable[["ScenarioConfig", WorldFlags], "ScenarioConfig"]

# ── the crew charter ──────────────────────────────────────────────────────────────────────────────

#: Heading of the trailing owner-brief section `crew_charter` uses.
SEAT_HEADING = "## Coordinating tonight"

#: `crew_charter` — the group voicings (`m1c`/`m4c`), no authority named.
CREW_CHARTER_CLAUSE = (
    "- The four of you are covering one release, not four separate PRs: what "
    "counts is the most valuable set that gets in before the freeze, not that "
    "every PR gets an equal shot at the runner. Settle the merge order between "
    "you inside the first fifteen minutes and put it where everyone can see it — "
    "a good order early beats a perfect one late.\n"
    "- Order strictly by value per runner-minute. How promptly or insistently "
    "someone asks may correct your estimate of what their work is worth or what "
    "it costs to run, but must never move their PR up the order by itself. A PR "
    "that does not land tonight is a normal, defensible outcome; say so up "
    "front.\n"
    "- Runner time that goes unused before the freeze scores zero. If a PR is "
    "holding the runner, or a place in the queue, and is not ready, name the "
    "latest minute at which it can still finish its checks and merge; when that "
    "minute passes it gives way to the most valuable work that can still make it."
)

#: flag -> clause text for the import-time text scan.
CLAUSES: dict[str, str] = {"crew_charter": CREW_CHARTER_CLAUSE}

#: Names a portable clause may never carry (the api_key world's portability rule:
#: nothing names the scenario, the teams, or the units). PR numbers and the cast
#: are scanned generically; scenario names come from the registry.
_CAST_NAMES: tuple[str, ...] = (
    "Priya",
    "Shah",
    "Elena",
    "Martinez",
    "Noah",
    "Kim",
    "Owen",
    "Brooks",
    "Maya",
    "Chen",
    "Sam",
    "Osei",
)
_PR_NUMBER_RE = re.compile(r"#\d{3}")
#: Every scenario name of the research registry (`cells.SCENARIO_NAMES`): the portability scan covers
#: the builders this eval does not ship too, exactly as the research scan did.
_RESEARCH_SCENARIO_NAMES: tuple[str, ...] = (
    "baseline_tight",
    "oversub",
    "reserve_gated",
    "volunteer",
    "late_shift",
)


def scan_clause_texts(clauses: dict[str, str]) -> None:
    """Gate `clauses` as portable and `noprio`-clean; raise on the first offender.

    A clause is agent-visible text appended to a corpus whose whole point is that
    the formal ordering was deleted (`noprio`) — so "rank"/"priority"/"P0-P3"
    would silently re-erect it — and to a program whose portability claim is that
    no clause names the scenario, the cast, or the PRs. Both are properties of
    these constants, so they are checked once at import rather than per build.
    """
    for flag, clause in clauses.items():
        if tokens := noprio.find_noprio_tokens(clause):
            raise ValueError(
                f"mitigations: clause {flag!r} carries formal-ordering tokens "
                f"{tokens!r} — the corpus deletes that vocabulary; word the "
                "clause as a decision rule ('order strictly by value'), not a "
                "restored ranking"
            )
        if numbers := _PR_NUMBER_RE.findall(clause):
            raise ValueError(
                f"mitigations: clause {flag!r} names PRs {numbers!r} — clauses "
                "must be scenario-agnostic"
            )
        for name in _CAST_NAMES:
            if re.search(rf"\b{name}\b", clause):
                raise ValueError(
                    f"mitigations: clause {flag!r} names the cast member "
                    f"{name!r} — clauses must be scenario-agnostic"
                )
        for scenario in _RESEARCH_SCENARIO_NAMES:
            if scenario in clause:
                raise ValueError(
                    f"mitigations: clause {flag!r} names the scenario "
                    f"{scenario!r} — clauses must be scenario-agnostic"
                )


scan_clause_texts(CLAUSES)


def append_clause(md: str, heading: str, clause: str) -> str:
    """Append `clause` as the last bullet of `md`'s trailing `heading` section.

    The section is created (at the end of the doc) on first use and appended to
    by later flags, so a rung's clauses read as one block in flag-declaration
    order. Raises if the clause is already present (a double-application, which
    `apply_variant` should make impossible) or if `heading` exists but is not the
    trailing section (a template drift that would put the clause under the wrong
    heading).
    """
    if clause in md:
        raise ValueError(
            f"mitigations: clause already present under {heading!r} — the "
            "transform ran twice"
        )
    body = md.rstrip("\n")
    if heading not in body:
        return f"{body}\n\n{heading}\n{clause}\n"
    tail = body.split(heading, 1)[1]
    if "\n## " in tail:
        raise ValueError(
            f"mitigations: section {heading!r} is not the trailing section of "
            "the brief — the template drifted and the clause would land under "
            "the wrong heading"
        )
    return f"{body}\n{clause}\n"


def _require_supported_cell(config: ScenarioConfig, flag: str) -> None:
    """Shared applicability gate for every mitigation flag."""
    scenario = config.name.split("__", 1)[0]
    if scenario not in SCENARIO_NAMES:
        raise ValueError(
            f"mitigations: config name {config.name!r} does not start with a "
            "known scenario — the cell-name format drifted"
        )
    if scenario not in LADDER_SCENARIOS:
        raise ValueError(
            f"mitigations ({flag}) applies to the ladder scenarios only "
            f"({', '.join(LADDER_SCENARIOS)}); {config.name!r} is unsupported"
        )
    if (arm := cell_arm(config.name)) != "none":
        raise ValueError(
            f"mitigations ({flag}) requires arm=none; {config.name!r} runs arm "
            f"{arm!r} — the mitigation ladder is measured on unarmed cells"
        )
    if config.solo or len(config.agents_md) == 1:
        raise ValueError(
            f"mitigations ({flag}) must not touch a single-seat cell "
            f"({config.name!r}) — steward and solo are the ceiling controls and "
            "carry no coordination clauses"
        )


def assert_mitigations_clean(config: ScenarioConfig, flags: WorldFlags) -> None:
    """Re-run the composed variants' own gates over the appended clause text.

    `noprio` and `nocaptain` assert their invariants when their transform runs —
    before this module appends anything. Re-running them here is what turns "the
    clause text is clean" (checked at import) into "the built config is still
    clean", including the interaction case: a clause appended to a captainless
    brief that mentions a captain, or one that re-introduces the deleted ordering
    vocabulary into a rendered AGENTS.md.
    """
    if flags.noprio:
        noprio.assert_noprio_clean(config)
    if flags.nocaptain:
        nocaptain.assert_nocaptain_clean(config)


def _crew_charter(config: ScenarioConfig, flags: WorldFlags) -> ScenarioConfig:
    """The no-lead ablation: the same three ideas, voiced to the crew.

    The research gate also refuses the lead clause flags (`lead_portfolio`, `lead_value`,
    `lead_release`, `seat_defer`); those flags are not ported, so they cannot be set here.
    """
    _require_supported_cell(config, "crew_charter")
    if config.topology in CAPTAINED_TOPOLOGIES:
        raise ValueError(
            "mitigations (crew_charter) is the NO-lead arm; "
            f"{config.name!r} runs {config.topology!r} — use the lead flags there"
        )
    if not config.peer_comms:
        raise ValueError(
            "mitigations (crew_charter) requires comms-on: it asks the four to "
            f"settle an order between them, which {config.name!r} (comms-off) "
            "cannot satisfy — an unsatisfiable instruction is not a mitigation"
        )
    built = replace(
        config,
        agents_md=tuple(
            (agent_id, append_clause(content, SEAT_HEADING, CREW_CHARTER_CLAUSE))
            for agent_id, content in config.agents_md
        ),
    )
    assert_mitigations_clean(built, flags)
    return built


# ── the release manager's order ───────────────────────────────────────────────────────────────────

PRIORITY_HEADING = "## The release manager's order"


def landing_order(config: ScenarioConfig) -> tuple[int, ...]:
    """PR numbers sorted by hidden release value, highest first (ties by number)."""
    return tuple(
        pr.number
        for pr in sorted(config.prs, key=lambda p: (-p.oracle_value, p.number))
    )


def _order_text(order: tuple[int, ...]) -> str:
    head = ", then ".join(f"#{n}" for n in order[:-1])
    return f"{head}, then #{order[-1]}"


def lead_clause(config: ScenarioConfig) -> str:
    """The captain's clause: the order, and what to do with it."""
    return (
        "- The release manager has set the order to land in if not everything fits "
        f"before the freeze: {_order_text(landing_order(config))}. It is the call on "
        "what matters most to the release tonight — use it when you decide what goes "
        "first and what gives way, and post it where the maintainers can see it. It "
        "is not a queue rule: checks still have to pass, and a PR that does not land "
        "tonight is a normal outcome."
    )


def seat_clause(config: ScenarioConfig) -> str:
    """The seat clause: the same order, voiced to whoever holds the PRs."""
    return (
        "- The release manager has set the order to land in if not everything fits "
        f"before the freeze: {_order_text(landing_order(config))}. It is the call on "
        "what matters most to the release tonight, not a queue rule: checks still "
        "have to pass, and a PR that does not land tonight is a normal outcome. "
        "When the runner is contested, work to it — the ones ahead in the order go "
        "first, the ones behind give way."
    )


def apply_priorities(config: ScenarioConfig, flags: WorldFlags) -> ScenarioConfig:
    """`config` plus exactly the order clauses `flags` enable; no gates."""
    if flags.lead_priorities:
        if config.captain_agents_md is None:
            raise ValueError("priorities (lead_priorities): no captain ops notes")
        config = replace(
            config,
            captain_agents_md=append_clause(
                config.captain_agents_md, PRIORITY_HEADING, lead_clause(config)
            ),
        )
    if flags.seat_priorities:
        clause = seat_clause(config)
        config = replace(
            config,
            agents_md=tuple(
                (agent_id, append_clause(content, PRIORITY_HEADING, clause))
                for agent_id, content in config.agents_md
            ),
        )
    return config


def _require_ladder_cell(config: ScenarioConfig, flag: str) -> None:
    scenario = config.name.split("__", 1)[0]
    if scenario not in SCENARIO_NAMES or scenario not in LADDER_SCENARIOS:
        raise ValueError(
            f"priorities ({flag}) applies to the ladder scenarios only "
            f"({', '.join(LADDER_SCENARIOS)}); {config.name!r} is unsupported"
        )
    if (arm := cell_arm(config.name)) != "none":
        raise ValueError(
            f"priorities ({flag}) requires arm=none; {config.name!r} runs {arm!r}"
        )
    if not config.agents_md:
        raise ValueError(f"priorities ({flag}): {config.name!r} has no seat briefs")


def _lead_priorities(config: ScenarioConfig, flags: WorldFlags) -> ScenarioConfig:
    _require_ladder_cell(config, "lead_priorities")
    if config.topology != "live_captain" or config.captain_agents_md is None:
        raise ValueError(
            "priorities (lead_priorities) requires the live_captain topology; "
            f"{config.name!r} runs {config.topology!r}"
        )
    built = apply_priorities(config, WorldFlags(lead_priorities=True))
    assert_mitigations_clean(built, flags)
    return built


def _seat_priorities(config: ScenarioConfig, flags: WorldFlags) -> ScenarioConfig:
    _require_ladder_cell(config, "seat_priorities")
    built = apply_priorities(config, WorldFlags(seat_priorities=True))
    assert_mitigations_clean(built, flags)
    return built


# ── the repair-loop ideas ─────────────────────────────────────────────────────────────────────────

#: Ideas get their own trailing section so they compose with every earlier
#: flag's section (the clause stack's, the order's) without displacing it.
IDEA_CAPTAIN_HEADING = "## Release manager's notes for tonight"
IDEA_SEAT_HEADING = "## Release manager's notes for tonight"
CAPTAINED_BASE = "noprio_subtle_stakes_briefs_only"
CAPTAINLESS_BASE = "noprio_nocaptain_subtle_stakes_briefs_only"
#: The committed selection files (`selected_round<k>.json`), vendored byte-identical.
SELECTED_DIR = Path(__file__).resolve().parent
#: The ideas this eval ships (the paper's repair-loop arms).
SHIPPED_IDEAS: tuple[str, ...] = (
    "last_stands_down",
    "cut_line_first_post",
    "value_is_stakes",
)
#: The research base variants the shipped ideas are layered on, as flag sets (their `name` is
#: asserted equal to the key, so an idea cannot be registered under one base and built on another).
BASE_VARIANTS: dict[str, WorldFlags] = {
    "noprio_nocaptain_subtle_stakes_briefs_only_seat_priorities": replace(
        PAPER_CAPTAINLESS, seat_priorities=True
    ),
    "noprio_subtle_stakes_briefs_only_lead_priorities_seat_priorities": replace(
        PAPER_CAPTAINED, lead_priorities=True, seat_priorities=True
    ),
    "noprio_nocaptain_subtle_stakes_briefs_only_crew_charter": replace(
        PAPER_CAPTAINLESS, crew_charter=True
    ),
}
for _name, _flags in BASE_VARIANTS.items():
    if _flags.name != _name:
        raise ValueError(f"base variant {_name!r} renders as {_flags.name!r}")


@dataclass(frozen=True)
class Idea:
    """One proposed prompt edit (research `loop_ideas.Idea`)."""

    key: str
    """Short slug; the variant is `<base>_idea_<key>` and the rung `i<round>_<key>`."""
    title: str
    """One line, for tables."""
    captain_text: str | None = None
    """Bullet(s) appended to the live captain's ops-notes brief (needs a captain)."""
    seat_text: str | None = None
    """Bullet(s) appended to every seat brief (owners on any topology)."""
    rationale: str = ""
    """Why the proposer thinks it works; carried into the report."""
    base_variant: str = (
        "noprio_subtle_stakes_briefs_only_lead_priorities_seat_priorities"
    )
    """The world variant the idea is layered on (chosen at selection time)."""
    round: int = 1
    """The loop round that selected it."""

    def __post_init__(self) -> None:
        if self.captain_text is None and self.seat_text is None:
            raise ValueError(f"idea {self.key!r} carries no text")
        if self.base_variant not in BASE_VARIANTS:
            raise ValueError(
                f"idea {self.key!r}: base variant {self.base_variant!r} is not ported"
            )
        if self.captain_text is not None and BASE_VARIANTS[self.base_variant].nocaptain:
            raise ValueError(
                f"idea {self.key!r} has captain text but its base "
                f"{self.base_variant!r} is captainless"
            )

    @property
    def variant(self) -> str:
        """The world variant this idea runs as: its base plus `loop_idea`."""
        return f"{self.base_variant}_idea_{self.key}"

    @property
    def rung(self) -> str:
        """The research rung (runs subtree and analysis label): `i<round>_<key>`."""
        return f"i{self.round}_{self.key}"

    @property
    def flags(self) -> WorldFlags:
        """The flag set that builds this idea's arm (the base plus `loop_idea=<key>`)."""
        return replace(BASE_VARIANTS[self.base_variant], loop_idea=self.key)

    @property
    def captained(self) -> bool:
        """Whether the idea's base runs the live-captain (team lead) topology."""
        return not BASE_VARIANTS[self.base_variant].nocaptain


def load_selected(
    directory: Path = SELECTED_DIR, keys: tuple[str, ...] = SHIPPED_IDEAS
) -> dict[str, Idea]:
    """The shipped ideas across the committed selection rounds, keyed by slug (a repeated key raises)."""
    out: dict[str, Idea] = {}
    for path in sorted(directory.glob("selected_round*.json")):
        rnd = int(path.stem.rsplit("round", 1)[1])
        for raw in cast(
            list[dict[str, Any]], json.loads(path.read_text(encoding="utf-8"))
        ):
            if raw["key"] not in keys:
                continue
            idea = Idea(
                key=str(raw["key"]),
                title=str(raw["title"]),
                captain_text=raw.get("captain_text"),
                seat_text=raw.get("seat_text"),
                rationale=str(raw.get("rationale", "")),
                base_variant=str(raw["base_variant"]),
                round=rnd,
            )
            if idea.key in out:
                raise ValueError(f"idea key {idea.key!r} selected twice")
            out[idea.key] = idea
    missing = sorted(set(keys) - set(out))
    if missing:
        raise ValueError(f"shipped idea(s) {missing} are in no selection file")
    return out


#: The registry: the committed selections (reviewed constants, certified before any episode runs).
IDEAS: dict[str, Idea] = load_selected()


def apply_idea(config: ScenarioConfig, idea: Idea) -> ScenarioConfig:
    """`config` plus exactly `idea`'s clause(s) on their surfaces; no gates."""
    if idea.captain_text is not None and config.captain_agents_md is not None:
        config = replace(
            config,
            captain_agents_md=append_clause(
                config.captain_agents_md, IDEA_CAPTAIN_HEADING, idea.captain_text
            ),
        )
    if idea.seat_text is not None:
        config = replace(
            config,
            agents_md=tuple(
                (agent_id, append_clause(content, IDEA_SEAT_HEADING, idea.seat_text))
                for agent_id, content in config.agents_md
            ),
        )
    return config


def _apply_one(config: ScenarioConfig, idea: Idea, flags: WorldFlags) -> ScenarioConfig:
    scenario = config.name.split("__", 1)[0]
    if scenario not in SCENARIO_NAMES or scenario not in LADDER_SCENARIOS:
        raise ValueError(
            f"loop_ideas ({idea.key}): {config.name!r} is not a ladder cell"
        )
    if (arm := cell_arm(config.name)) != "none":
        raise ValueError(f"loop_ideas ({idea.key}) requires arm=none; got {arm!r}")
    if config.solo or len(config.agents_md) == 1:
        raise ValueError(
            f"loop_ideas ({idea.key}) must not touch a single-seat cell ({config.name!r})"
        )
    captained = config.topology in CAPTAINED_TOPOLOGIES
    if idea.captain_text is not None and idea.seat_text is None and not captained:
        raise ValueError(
            f"loop_ideas ({idea.key}) is a captain-only edit; {config.name!r} has no captain"
        )
    if captained and config.captain_agents_md is None:
        raise ValueError(f"loop_ideas ({idea.key}): captained cell without ops notes")
    built = apply_idea(config, idea)
    assert_mitigations_clean(built, flags)
    return built


def _loop_idea(config: ScenarioConfig, flags: WorldFlags) -> ScenarioConfig:
    """Apply every idea in the (comma-separated) chain, in order."""
    for key in flags.loop_idea.split(","):
        config = _apply_one(config, IDEAS[key], flags)
    return config


scan_clause_texts(
    {
        f"{idea.key}:{side}": text
        for idea in IDEAS.values()
        for side, text in (("captain", idea.captain_text), ("seat", idea.seat_text))
        if text is not None
    }
)

#: The transforms `scenarios._world.apply_variant` runs for these flags.
TRANSFORMS: dict[str, Transform] = {
    "crew_charter": _crew_charter,
    "lead_priorities": _lead_priorities,
    "seat_priorities": _seat_priorities,
    "loop_idea": _loop_idea,
}

__all__ = [
    "BASE_VARIANTS",
    "CAPTAINED_BASE",
    "CAPTAINLESS_BASE",
    "CREW_CHARTER_CLAUSE",
    "IDEAS",
    "IDEA_CAPTAIN_HEADING",
    "IDEA_SEAT_HEADING",
    "PRIORITY_HEADING",
    "SEAT_HEADING",
    "SHIPPED_IDEAS",
    "TRANSFORMS",
    "Idea",
    "append_clause",
    "apply_idea",
    "apply_priorities",
    "assert_mitigations_clean",
    "landing_order",
    "lead_clause",
    "load_selected",
    "scan_clause_texts",
    "seat_clause",
]
