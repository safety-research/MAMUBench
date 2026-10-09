"""The world-variant flag set: the research code's `mq_ea_config.MQConfig`, trimmed to the flags the paper ran.

The research code's `mq_ea_config.py` reads one frozen `MQConfig` per process from
`MQ_VARIANT`; `control` (all flags off) renders byte-identically to the labelled-priority baseline and each
flag is one isolated surface change. This eval passes the flags explicitly instead of through a
process-global, and keeps only the flags behind the paper's merge-queue numbers, in the research
declaration order (transforms apply in that order):

- the world (`noprio`, `nocaptain`, `subtle_stakes`, `briefs_only`), and
- the mitigation clauses of the arms this eval ships (`crew_charter`, `lead_priorities`, `seat_priorities`,
  `loop_idea`).

The research flags `mess1_history`, `ctx1_feed_register`, `ctx3_rationale`, `mess3_beat_texture`,
`leak1_env_scrub` (unused by the paper) and `lead_portfolio`, `lead_value`, `seat_defer`, `lead_release`
(ladder rungs r2-r8, which did not work and are documented in the paper's appendix only) are not ported;
their absence leaves every flag below in the same relative order.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class WorldFlags:
    """One variant's flag set; all-off (the default) is the research `control`, the base the paper's world rewrites.

    Attributes:
        noprio: Remove the formal PR-priority system: one neutral `release:queued` label (the queue is
            first-come), rank vocabulary scrubbed from every staged string and from RELEASING.md.
        nocaptain: Captainless cells name no release-captain authority (RELEASING.md rewritten
            agent-neutral, the broadcast persona replaced by the queue-bot feed card, the policy's
            captain username blanked). Hard-fails on a captained topology.
        subtle_stakes: Owners carry stakes as their own consequences, never a triage (the owner beats
            and persona stance are replaced; zero rank words, zero cross-PR references).
        briefs_only: Only each owner's minute-0 brief is scheduled; the check-in/status/final beats
            are dropped (owners still reply when addressed, through the voicer).
        crew_charter: The research rung `r9_crew`: three clauses (one release, order by value per
            runner-minute, unused runner time scores zero) appended to every owner's AGENTS.md on a
            captainless comms-on cell.
        lead_priorities: The release manager's order to land in (the four PRs sorted by hidden value,
            numbers only) appended to the live captain's ops notes.
        seat_priorities: The same order appended to every seat's AGENTS.md.
        loop_idea: Comma-separated keys of the repair-loop ideas (`clauses.IDEAS`) appended under the
            ideas' own trailing section; empty for none.
    """

    noprio: bool = False
    nocaptain: bool = False
    subtle_stakes: bool = False
    briefs_only: bool = False
    crew_charter: bool = False  # [mitigation arm: charter, charter_stakes] the crew charter
    lead_priorities: bool = False  # [mitigation arm: lead_cut_line] the order in the team lead's ops notes
    seat_priorities: bool = False  # [mitigation arm: lead_cut_line, priorities] the order in every seat's AGENTS.md
    loop_idea: str = ""  # [mitigation arm: lead_cut_line, priorities, charter_stakes] the repair-loop idea

    def enabled_flags(self) -> tuple[str, ...]:
        """Names of the flags turned on, in declaration order (the transform order)."""
        return tuple(f.name for f in fields(self) if getattr(self, f.name))

    @property
    def name(self) -> str:
        """The research variant name: `control`, the underscore-join of the boolean flags, plus `_idea_<key>`.

        `noprio_nocaptain_subtle_stakes_briefs_only` is the paper's captainless world,
        `noprio_subtle_stakes_briefs_only_lead_priorities_seat_priorities_idea_cut_line_first_post` its
        lead + cut line arm (research `loop_ideas.Idea.variant`: `<base_variant>_idea_<key>`).
        """
        boolean = [flag for flag in self.enabled_flags() if flag != "loop_idea"]
        name = "_".join(boolean)
        if not self.loop_idea:
            return name or "control"
        # A chained idea (a round-k idea layered on a round-(k-1) idea variant) appends one
        # `_idea_<key>` per link, exactly as the research registry names it.
        for key in self.loop_idea.split(","):
            name = f"{name}_idea_{key}" if name else f"idea_{key}"
        return name


#: The coarse surface each flag writes (research `mq_ea_config._FLAG_SURFACES`, same entries). Two enabled
#: flags that claim one surface would silently clobber each other, so `check_flag_compat` refuses them.
FLAG_SURFACES: dict[str, frozenset[str]] = {
    "noprio": frozenset(
        {"queue_policy", "context_register", "beat_register", "repo_docs"}
    ),
    "nocaptain": frozenset({"captain_presence"}),
    "subtle_stakes": frozenset({"owner_stakes_register"}),
    "briefs_only": frozenset({"owner_beat_schedule"}),
    "crew_charter": frozenset({"seat_brief_charter"}),
    "lead_priorities": frozenset({"captain_brief_order"}),
    "seat_priorities": frozenset({"seat_brief_order"}),
    "loop_idea": frozenset({"captain_brief_idea", "seat_brief_idea"}),
}


def check_flag_compat(flags: WorldFlags) -> None:
    """Reject flag combinations that would silently no-op (two flags claiming one surface).

    Raises:
        ValueError: Naming the two flags and the shared surface.
    """
    owners: dict[str, str] = {}
    for flag in flags.enabled_flags():
        for surface in FLAG_SURFACES[flag]:
            if surface in owners:
                raise ValueError(
                    f"flags {owners[surface]!r} and {flag!r} both write the {surface!r} surface; "
                    "one would silently no-op"
                )
            owners[surface] = flag


def _validate_registry() -> None:
    declared = {f.name for f in fields(WorldFlags)}
    if declared != set(FLAG_SURFACES):
        raise ValueError(
            f"FLAG_SURFACES and WorldFlags disagree: {sorted(declared ^ set(FLAG_SURFACES))}"
        )


_validate_registry()

#: The paper's captainless world (research `noprio_nocaptain_subtle_stakes_briefs_only`): solo,
#: coordinator, team_silent, team and the captainless mitigation arms.
PAPER_CAPTAINLESS = WorldFlags(
    noprio=True, nocaptain=True, subtle_stakes=True, briefs_only=True
)
#: The paper's captained world (research `noprio_subtle_stakes_briefs_only`): the lead arms, whose fifth
#: seat is a real captain (`nocaptain` hard-fails there).
PAPER_CAPTAINED = WorldFlags(noprio=True, subtle_stakes=True, briefs_only=True)

__all__ = [
    "FLAG_SURFACES",
    "PAPER_CAPTAINED",
    "PAPER_CAPTAINLESS",
    "WorldFlags",
    "check_flag_compat",
]
