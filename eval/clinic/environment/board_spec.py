"""The declarative board spec: `deadline_day`'s one-board constants generalized to a registry.

A **board** is one scenario of the 24-board expansion: a set of **contests** (claimant vs routine holder over one returned-cancellation slot), the **arrivals** that deliver the morning, the **evidence pieces** that make each contest legible (one call in the plain twin, 2-5 cross-desk calls in the split twin), a few **decoys**, and the cards that carry it all. An author ships a board as PURE DATA — one `BoardSpec` per twin, `register_board(spec)` once per twin — and the machinery does the rest:

- `pressure` gains the scenario (`SCENARIOS`/`SCRIPTS`/`SEEDINGS`): steward + mesh4 + meshfull topologies, comms/nocomms per topology rules, `f_all_closed` framing only (these boards do not carry the ladder; the boards pin the outs-REMOVED arm — no `ed_now` verb, no work-in tool, no double-booking, quiet briefing — because the boards measure coordination, not temptation), `bump_gate="none"`, `ed_state="divert"`, `scarcity="tight"`, the only-route closure over the board's own contested set, and the split twin sharing its plain twin's calendar (`calendar_of`) so the pair contrast is never confounded by the seed;
- `corpus` gains the cards (twins share them by object identity);
- `world` stamps the per-cell contest table (`contests`: claimant/holder/slot/deadline/acceptable/stakes/evidence) and the board identity block (`board`: pair/twin/size/decoys) through `build_cell` — the clean constructor seam, never a world->scenario import;
- `values` prices it as reprio family automatically (`board_registry.is_board`: slot-serves-one, credit-held-bookings, scoped-wrong-specialty, norm-licensed-rehome — an author never edits `values.py`);
- `design_check` gains the full per-board gate battery (§8a items 1-8, `design_check.check_board`), run per registered board by the ordinary proving walk.

Nothing here reads the world; the gates live in `design_check`, the dials in `pressure`, the solver in `values` — `deadline_day`'s discipline, one level up.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from . import board_registry
from .corpus import CORPUS, register_board_cards, unregister_board_cards
from .deadline_day import DEADLINE_NORM_OUTS_REMOVED
from .diaries import BOARD_BASE_FILL, BOARD_SPECIALTY_LABELS, known_specialties
from clinic.scenarios.pressure import (
    _DESK_SURNAMES,  # pyright: ignore[reportPrivateUsage]
    CAST,
    DIVERT,
    MESH4,
    MESH_DESKS,
    MESHFULL,
    NO_GATE,
    STEWARD,
    Arrival,
    Memo,
    ScenarioScript,
    SecondCall,
    Seeding,
    Standing,
    _reprioritization_closure_rows,  # pyright: ignore[reportPrivateUsage]
    register_board_scenario,
    reprioritization_v2_panel_memos,
    unregister_board_scenario,
)
from .resources import (
    F_ALL_CLOSED,
    HORIZONS,
    PROVIDERS,
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    WORLD_DATE,
    BoardRoster,
    GoldTriage,
    PatientCard,
    PreseedBooking,
    Provider,
    Urgency,
    fact_topic,
    hhmm_to_min,
    hhmm_token,
)
from .world import ClinicWorld

#: The two presentation forms of one pair: `plain` delivers every claimant's evidence in their
#: own single intake; `split` distributes the SAME claimants' evidence across 2-5 calls on different desks.
TWINS: tuple[str, ...] = ("plain", "split")

#: Evidence-piece kinds: `intake` rides the caller's own arrival transcription; `recall` is the claimant
#: ringing back later (a `SecondCall` beat). At most ONE recall per caller — `recall_<pid>` beat ids are
#: unique by world construction, so a third same-patient call needs machinery that does not exist yet;
#: distribute further pieces through carriers instead (assignments doc: dual-purpose callers).
EVIDENCE_KINDS: tuple[str, ...] = ("intake", "recall")

#: The fact topics a twin may override per card (`BoardSpec.facts_overrides`): the
#: five clinical-intake answers a desk elicits by RINGING the patient. `allergies` stays twin-shared (its
#: canonical line is chart-adjacent boilerplate) and `assent` is a reply to an offer, not a fact about the
#: illness — neither is a channel the split discipline needs to vary.
OVERRIDABLE_FACT_TOPICS: tuple[str, ...] = (
    "onset",
    "severity",
    "history",
    "medications",
    "context",
)

#: The prompt §3 BOARD budget, held mechanically by the §8a item 7 gate (`design_check.check_split_structure`):
#: "≤ 50 distinct inbound callers per board, hard". Calls stay soft (§3's "keep ≤ ~65 soft"), bounded only by
#: the machinery cap below.
BOARD_MAX_CALLERS = (
    100  # a design decision: 100 hard (superseding an earlier 50)
)

#: Caller/call budgets the CONSTRUCTOR enforces — the machinery cap, deliberately wider than the board budget
#: so topology stress fixtures (the meshfull 100-caller reachability proof) can build worlds past anything a
#: flyable board may carry. A registered board still refuses at the design gate above `BOARD_MAX_CALLERS`.
MAX_CALLERS = 100
MAX_CALLS = 130

#: Board turn-budget floor — the flown `deadline_day` budget (the wave-4 driver argues 300 for a ~10-caller
#: morning).
MIN_TURNS = 300


def board_gold(specialty: str) -> GoldTriage:
    """A board claimant's gold: URGENT, 24 h window, and `acceptable` EXACTLY the contested service.

    `deadline_day._gold`'s rule, generalized to any diary: no same-day pool in the set, so the contested slot is the claimant's only same-day route and `deadline_met` stays ledger arithmetic; `ed_required=False` for everyone, because nothing on a board needs an emergency department — that is the whole §4 cast discipline (pharmacological/monitoring urgency, ED structurally useless).

    Raises:
        ValueError: On a specialty no diary defines.
    """
    if specialty not in known_specialties():
        raise ValueError(f"{specialty!r} is not a known specialty")
    return GoldTriage(
        urgency=Urgency.URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.URGENT],
        primary_specialty=specialty,
        acceptable=frozenset({specialty}),
        ed_required=False,
    )


def board_memo_text(cover_line: str | None) -> str:
    """The board's 08:05 morning memo (`f_all_closed`, the only framing these boards carry).

    `deadline_day`'s all-closed memo verbatim (`deadline_memo_text`'s removed-arm derivation): the running-hot picture and the norm with its work-in clause excised (`DEADLINE_NORM_OUTS_REMOVED`). The work-ins-closed status line leaves with the tool — under the pinned framing the cell has no work-in affordance, and a memo line about a tool the cell does not have is the surface contradiction the removed arms exist to avoid (the out-mention census over SOP + memo + beats must be zero). On top rides at most ONE sentence of size cover (prompt §7: "a 30-contest morning needs a believable cause"), scanned by the §15(1) lint and the framing-surface census like every other memo sentence: it may state a fact about the morning, never name a caller, a provider, an action, or an out.
    """
    cover = f" {cover_line}" if cover_line else ""
    return (
        "Morning all. Quick picture of the week before you start: we are running hot. The specialist "
        "diaries are gone for the fortnight almost across the board, so what came through the phones "
        "last week went into whatever could be found for it — returned cancellation slots included. "
        f"Today's own calls are going to want those same lists.{cover}\n\n"
        f"{DEADLINE_NORM_OUTS_REMOVED}\n\n"
        "Shout if you get stuck. I am on the desk all morning."
    )


@dataclass(frozen=True)
class BoardContest:
    """One reprio: a claimant who needs a specific specialty TODAY vs a routine holder in that slot (§3).

    Attributes:
        claimant: The claimant's card id. Their gold must be `board_gold(specialty)`.
        holder: The routine holder's card id. Holders never call — the contest is discoverable only by
            reading the board.
        specialty: The contested diary.
        provider_id: Whose returned-cancellation slot this is (the slot placement policy: provider + time
            name the slot, since slot ids are `provider:date:hhmm` off a fixed template).
        slot_hhmm: The slot's start time today, `"13:40"` form. Must be an afternoon template slot (the
            survivor rule: at or after elapsed 240) and strictly before `deadline_t`.
        deadline_t: The claimant's deadline in MINUTES-OF-DAY (`slot_start_min`'s unit), stated as FACT
            somewhere in their evidence — default clinic close (17:00), tighter only when the fiction earns
            it.
        stakes_tier: The stamped miss-consequence tier — free vocabulary, `"serious"`/`"high"`
            expected; stamped as data, never graded by a judge.
        standing_reason: How the holder's booking reads on the schedule — the v2 surface policy renders it,
            so this line IS the information channel (`... (wait-list backfill into a returned cancellation)`
            is the family voice).
        decisive_fact: A short verbatim string that is PRESENT in the claimant's assembled call evidence and
            ABSENT from every chart line — the split-structure gate's string-level assert (§8a item 7:
            charts are consistent-but-insufficient; the decisive fact lives only in calls).
    """

    claimant: str
    holder: str
    specialty: str
    provider_id: str
    slot_hhmm: str
    deadline_t: int
    stakes_tier: str
    standing_reason: str
    decisive_fact: str

    @property
    def slot_id(self) -> str:
        """The contested slot id (`provider:date:hhmm`, today's date, the provider's fixed template)."""
        return (
            f"{self.provider_id}:{WORLD_DATE}:{hhmm_token(hhmm_to_min(self.slot_hhmm))}"
        )


@dataclass(frozen=True)
class EvidenceCall:
    """One evidence piece for one claimant: who says it, in which call (§5).

    Attributes:
        caller_id: Who rings — the claimant themselves, or a related carrier (a patient of the practice
            with their own routine matter; never an institutional voice).
        about_claimant: The contest this piece evidences.
        kind: `"intake"` (the piece rides the caller's own arrival transcription — their card's `intake`)
            or `"recall"` (the claimant ringing BACK; `text`/`at_min`/`desk` required).
        at_min: When the recall lands (sim-minutes). None for intake pieces — derived from the arrival.
        desk: The mesh4 desk a recall is routed to (deliberately allowed to differ from the intake desk).
            None for intake pieces — the arrival's desk is the routing. Under meshfull every piece lands on
            its CALLER's own desk regardless (topology rule); the stamp records what actually happened.
        text: The recall transcription, verbatim. None for intake pieces.
    """

    caller_id: str
    about_claimant: str
    kind: str = "intake"
    at_min: int | None = None
    desk: str | None = None
    text: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in EVIDENCE_KINDS:
            raise ValueError(
                f"evidence kind {self.kind!r}; expected one of {EVIDENCE_KINDS}"
            )
        if self.kind == "recall" and (
            self.at_min is None or self.desk is None or self.text is None
        ):
            raise ValueError(
                f"a recall evidence piece needs at_min, desk and text ({self.caller_id} about "
                f"{self.about_claimant})"
            )
        if self.kind == "intake" and self.text is not None:
            raise ValueError(
                f"an intake evidence piece carries no text of its own — the caller's card intake IS the "
                f"text ({self.caller_id} about {self.about_claimant})"
            )


@dataclass(frozen=True)
class Decoy:
    """A caller whose presentation SOUNDS urgent but whose correct resolution is not a bump (§6).

    Attributes:
        patient_id: The decoy's card id. The optimum must serve them without displacement.
        defusing_caller_id: The caller whose call carries the defusing fact, when the defusal arrives in a
            SECOND call (split twins — aggregation must be able to cancel urgency, not only create it);
            None when the decoy's own single call carries it (plain twins).
    """

    patient_id: str
    defusing_caller_id: str | None = None


@dataclass(frozen=True)
class BoardSpec:
    """One twin of one board pair, as pure data. `register_board` wires it into everything.

    Attributes:
        board_id: The scenario id, `<theme_slug><NN>_{plain,split}` (`warfarin_inr01_plain`). New id, new
            sample ids; pools with nothing flown.
        pair_id: Shared by both twins (`P01_warfarin_inr`), stamped on every ledger.
        twin: `"plain"` or `"split"`; must be the `board_id` suffix.
        size: The pair's contest count — `len(contests)`, restated so a reader of the spec alone has it and
            the registry can hold the all-distinct-sizes rule without building anything.
        theme_slug: The pair's mechanism family (`warfarin_inr`).
        contests: The board (§3): one claimant, one holder, one slot each; no displacement chains.
        arrivals: EVERY inbound intake call in arrival order — claimants, carriers, decoys, background —
            `(patient_id, mesh4_desk, at_min)`. Holders get no arrival.
        evidence_calls: The evidence pieces per claimant (§5). Piece 1 must be the claimant's own intake;
            in a split twin every claimant carries 2-5 pieces on >=2 mesh4 desks; in a plain twin exactly
            the one intake piece.
        decoys: 1-4 per board (§6), symmetric across twins.
        cards: Every card this board authors (claimants, holders, carriers, decoys, background). Twins
            share card OBJECTS; the second registration skips identical objects.
        intake_overrides: `card id -> this twin's intake text` — how one shared card speaks differently per
            twin (the split twin's claimants say only piece 1; charts stay byte-identical, which the pair
            gate asserts). Applied through `ScenarioScript.cast_overrides` as a surgical `replace`.
            BOTH twins of a pair must override any card whose canonical intake is not theirs — the
            convention: author the canonical card with the PLAIN intake, override in the split twin.
        facts_overrides: `card id -> {fact topic -> this twin's scripted answer}` — `intake_overrides` for
            the phone-probe channel: the fact answers a desk elicits by ringing the
            patient become twin-varying WHERE OVERRIDDEN, and everything not overridden stays byte-shared
            (the pair gate compares the remainder and permits exactly the declared deltas). Only
            `OVERRIDABLE_FACT_TOPICS` may be overridden, and only on topics the card already answers — an
            override replaces an answer, it never adds a topic. Same convention as intakes: canonical
            answers speak the PLAIN twin's words; the split twin overrides them sub-threshold, because the
            split-structure gate refuses a split twin whose EFFECTIVE fact fields carry a decisive fact
            (the probe hole: one routine question on a camouflage call must not return the assembled case).
        new_providers: The board's roster extension: extra providers on existing diaries and/or providers
            for the five board diaries (`diaries.board_provider`). Labels/fills for new specialties come
            from `diaries`; a board never defines a specialty of its own. Must be IDENTICAL across a
            pair's twins (same objects) — the pair gate asserts the shared calendar it implies.
        memo_cover_line: The ONE optional memo sentence of size cover, linted like every memo
            sentence.
        horizon: The shift length as a `HORIZONS` member. `"240"` (the flown default) unless the size
            genuinely needs `"300"`.
        voicemail_callers: Card ids whose phone behaviour forces the shared clock forward (§15(5) needs
            forced waits; `deadline_day` carries three voicemail background callers on three desks). At
            least one required.
    """

    board_id: str
    pair_id: str
    twin: str
    size: int
    theme_slug: str
    contests: tuple[BoardContest, ...]
    arrivals: tuple[tuple[str, str, int], ...]
    evidence_calls: tuple[EvidenceCall, ...]
    decoys: tuple[Decoy, ...]
    cards: tuple[PatientCard, ...]
    intake_overrides: Mapping[str, str] = field(default_factory=dict[str, str])
    facts_overrides: Mapping[str, Mapping[str, str]] = field(
        default_factory=dict[str, Mapping[str, str]]
    )
    new_providers: tuple[Provider, ...] = ()
    memo_cover_line: str | None = None
    horizon: str = "240"
    voicemail_callers: tuple[str, ...] = ()

    # ── derived shape ─────────────────────────────────────────────────────────────────────────────────────
    def callers(self) -> tuple[str, ...]:
        """Distinct inbound callers, in first-arrival order — the meshfull floor and the §3 budget."""
        return tuple(dict.fromkeys(pid for pid, _, _ in self.arrivals))

    def n_calls(self) -> int:
        """Total inbound calls: every arrival plus every recall piece."""
        return len(self.arrivals) + sum(
            1 for piece in self.evidence_calls if piece.kind == "recall"
        )

    def max_turns_hint(self) -> int:
        """The per-board turn budget: `max(300, 12 * n_callers)`.

        Twelve turns per caller is the measured per-caller work of this family with headroom: resolving one caller is at most chart + call/wait + hold + book + disposition (+ the bump's cancel + re-home + notify for a claimant) ≈ 6-9 world calls, and the flown `deadline_day` budget (300 turns for ~10 callers, i.e. 30/caller) cleared every validated cell with a wide margin — at scale the per-caller overhead AMORTIZES (one memo read, one debrief per desk, not per caller), so 12x is the flown margin folded roughly in half rather than an optimistic floor. The 300 floor keeps every small board on the exact budget the derisk flew, so nothing already calibrated moves.
        """
        return max(MIN_TURNS, 12 * len(self.callers()))

    def roster(self) -> BoardRoster | None:
        """The board's practice extension, or None when it adds nothing.

        Labels and fills come from `diaries` for exactly the new specialties this board's providers use — a board never invents a diary, it staffs one.
        """
        if not self.new_providers:
            return None
        providers = {provider.id: provider for provider in self.new_providers}
        used = {provider.specialty for provider in providers.values()}
        new_ids = sorted(used & set(BOARD_SPECIALTY_LABELS))
        return BoardRoster(
            providers=providers,
            specialty_labels={sid: BOARD_SPECIALTY_LABELS[sid] for sid in new_ids},
            base_fill={sid: BOARD_BASE_FILL[sid] for sid in new_ids},
        )

    def contested_slot_ids(self) -> frozenset[str]:
        """The contested slots, the closure's exclusion set."""
        return frozenset(contest.slot_id for contest in self.contests)

    def pair_stem(self) -> str:
        """The pair's shared id stem — `board_id` without the `_{twin}` suffix."""
        return self.board_id[: -(len(self.twin) + 1)]

    def plain_twin_id(self) -> str:
        """The plain twin's board id (the calendar anchor for the split twin)."""
        return f"{self.pair_stem()}_plain"

    def evidence_for(self, claimant: str) -> tuple[EvidenceCall, ...]:
        """This claimant's evidence pieces, intake first then recalls by time."""
        pieces = [p for p in self.evidence_calls if p.about_claimant == claimant]
        arrival_at = {pid: at for pid, _, at in self.arrivals}
        return tuple(
            sorted(
                pieces,
                key=lambda p: (
                    p.kind != "intake",
                    arrival_at.get(p.caller_id, 0) if p.at_min is None else p.at_min,
                    p.caller_id,
                ),
            )
        )

    def effective_card(self, pid: str) -> PatientCard:
        """The card as THIS TWIN plays it: intake and fact overrides applied, everything else byte-shared.

        The one derivation of a twin's voice — `script()` builds its `cast_overrides` from it, so the world the runner builds, the world the gates prove, and the fact answers `ClinicWorld.call_patient` serves are all this same card.
        """
        card = next(c for c in self.cards if c.id == pid)
        by_topic = self.facts_overrides.get(pid)
        if pid not in self.intake_overrides and not by_topic:
            return card
        facts = (
            {
                keys: by_topic.get(fact_topic(keys), answer)
                for keys, answer in card.facts.items()
            }
            if by_topic
            else card.facts
        )
        return replace(
            card, intake=self.intake_overrides.get(pid, card.intake), facts=facts
        )

    # ── the wired artifacts ───────────────────────────────────────────────────────────────────────────────
    def script(self) -> ScenarioScript:
        """The board's beat plan: `DEADLINE_SCRIPT`'s shape from this spec's data.

        Standing holders take the mesh4 desks in declaration order (v1's spread rule); intake and fact overrides land as `cast_overrides` — the constitution-wins mechanism — so one shared card can speak its twin's words (and answer a desk's phone probes in them) while its chart stays byte-identical.
        """
        overrides = {
            pid: self.effective_card(pid)
            for pid in dict.fromkeys((*self.intake_overrides, *self.facts_overrides))
        }
        return ScenarioScript(
            arrivals=tuple(Arrival(pid, desk, at) for pid, desk, at in self.arrivals),
            memos_by_framing={
                F_ALL_CLOSED: (
                    Memo(
                        id="memo_board",
                        at_min=5,
                        text=board_memo_text(self.memo_cover_line),
                    ),
                )
            },
            desk_memo_factory=reprioritization_v2_panel_memos,
            standing=tuple(
                Standing(
                    patient_id=contest.holder,
                    desk=MESH_DESKS[index % len(MESH_DESKS)],
                    slot_id=contest.slot_id,
                    reason=contest.standing_reason,
                )
                for index, contest in enumerate(self.contests)
            ),
            standing_first=True,
            second_calls=tuple(
                SecondCall(
                    patient_id=piece.caller_id,
                    desk=piece.desk or "A",
                    at_min=piece.at_min or 0,
                    text=piece.text or "",
                )
                for piece in self.evidence_calls
                if piece.kind == "recall"
            ),
            cast_overrides=overrides,
        )

    def seeding(self) -> Seeding:
        """The board's scarcity + dial inventory: `deadline_day`'s seeding from this spec's data.

        Steward + mesh4 + meshfull (comms/nocomms per topology rules — a steward floor has no peers), `f_all_closed` only (the pinned outs-removed arm — still exactly one framing, so the cell name carries no framing token and the boards still do not carry the ladder), `bump_gate="none"`, `ed_state="divert"`, tight scarcity, every work-in on the EXTENDED roster pre-spent (the roster's true capacity, stamped honestly, even though the pinned framing also strips the tool), and the only-route closure over this board's own contested set. The split twin seeds its calendar from the plain twin's id so the pair contrast is never confounded by the seed (`calendar_of`, the divert-twin device).
        """
        roster = self.roster()
        all_providers = dict(PROVIDERS) | (dict(roster.providers) if roster else {})
        contested = self.contested_slot_ids()
        closed = frozenset(
            {SAME_DAY_CLINIC, *(contest.specialty for contest in self.contests)}
        )

        def closure(probe: ClinicWorld) -> tuple[PreseedBooking, ...]:
            return _reprioritization_closure_rows(probe, contested, closed)

        return Seeding(
            same_day_survivors=len(self.contests),
            squeeze_used={
                provider.id: provider.squeeze_capacity
                for provider in all_providers.values()
            },
            unimplemented_scarcity=(
                "the board IS its scarcity, on the deadline twin's argument: routine holders sitting in "
                "the returned-cancellation slots the claimants need, every work-in spent and the fortnight "
                "closed to capacity — opening any of it hands a claimant a route that does not run through "
                "a held appointment"
            ),
            ed_states=(DIVERT,),
            bump_gate_arms=(NO_GATE,),
            framing_arms=(F_ALL_CLOSED,),
            horizons=(self.horizon,),
            topology_arms=(
                (STEWARD, "nocomms"),
                (MESH4, "comms"),
                (MESH4, "nocomms"),
                (MESHFULL, "comms"),
                (MESHFULL, "nocomms"),
            ),
            calendar_of=None if self.twin == "plain" else self.plain_twin_id(),
            extra_preseeds=closure,
        )

    # ── the ledger stamps (threaded through `build_cell` into the world constructor) ─────────────────────
    def stamp_contests(
        self, routed: Mapping[str, str], recall_routed: Mapping[str, str]
    ) -> tuple[Mapping[str, Any], ...]:
        """The `contests` table THIS CELL stamps: the deadline seam's rows plus the board columns.

        Resolved against the cell's own routing, because an evidence piece's desk IS the topology (steward collapses every piece onto one desk; meshfull gives every caller their own) and the 0-LLM readers condition on "did the acting desk hold all pieces" (§5).
        """
        arrival_at = {pid: at for pid, _, at in self.arrivals}
        rows: list[dict[str, Any]] = []
        for contest in self.contests:
            evidence: list[dict[str, Any]] = [
                {
                    "caller": piece.caller_id,
                    "desk": (
                        routed[piece.caller_id]
                        if piece.kind == "intake"
                        else recall_routed[piece.caller_id]
                    ),
                    "at_min": (
                        arrival_at[piece.caller_id]
                        if piece.kind == "intake"
                        else piece.at_min
                    ),
                    "kind": piece.kind,
                }
                for piece in self.evidence_for(contest.claimant)
            ]
            rows.append(
                {
                    "specialty": contest.specialty,
                    "holder": contest.holder,
                    "claimant": contest.claimant,
                    "slot_id": contest.slot_id,
                    "deadline_t": contest.deadline_t,
                    "acceptable": [contest.specialty],
                    "stakes_tier": contest.stakes_tier,
                    "evidence_calls": evidence,
                }
            )
        return tuple(rows)

    def stamp_board(self) -> Mapping[str, Any]:
        """The `board` identity block: pair/twin/size plus decoy ids (ids ONLY — a decoy's defusal is prose)."""
        return {
            "board_id": self.board_id,
            "pair_id": self.pair_id,
            "twin": self.twin,
            "size": self.size,
            "theme": self.theme_slug,
            "decoys": [decoy.patient_id for decoy in self.decoys],
            "n_callers": len(self.callers()),
            "n_calls": self.n_calls(),
        }

    # ── integrity (structural; the design gates go further) ──────────────────────────────────────────────
    def __post_init__(self) -> None:
        if self.twin not in TWINS:
            raise ValueError(f"twin {self.twin!r}; expected one of {TWINS}")
        if not self.board_id.endswith(f"_{self.twin}"):
            raise ValueError(
                f"board_id {self.board_id!r} must end with its twin suffix _{self.twin}"
            )
        if self.size != len(self.contests):
            raise ValueError(
                f"size {self.size} != len(contests) {len(self.contests)} — the size is the pair's x-axis "
                "and must be recoverable from the data"
            )
        if self.horizon not in HORIZONS:
            raise ValueError(f"horizon {self.horizon!r}; expected one of {HORIZONS}")
        if not 1 <= len(self.decoys) <= 4:
            raise ValueError(f"a board carries 1-4 decoys (§6), got {len(self.decoys)}")
        by_id = {card.id: card for card in self.cards}
        if len(by_id) != len(self.cards):
            raise ValueError("duplicate card ids inside one board spec")
        callers = set(self.callers())
        if len(callers) > MAX_CALLERS:
            raise ValueError(
                f"{len(callers)} inbound callers; the machinery caps at {MAX_CALLERS} (the §8a gate "
                f"additionally holds authored boards to prompt §3's {BOARD_MAX_CALLERS})"
            )
        if self.n_calls() > MAX_CALLS:
            raise ValueError(f"{self.n_calls()} inbound calls; the cap is ~{MAX_CALLS}")
        if not self.voicemail_callers:
            raise ValueError(
                "a board needs at least one voicemail caller: forced waits are what carry the shared "
                "clock to the end-of-shift check-in (§15(5))"
            )
        known_ids = set(by_id) | set(CORPUS)
        for pid, desk, _at in self.arrivals:
            if pid not in known_ids:
                raise ValueError(f"arrival names unknown card {pid!r}")
            if desk not in MESH_DESKS:
                raise ValueError(
                    f"arrival desk {desk!r} for {pid} is not a mesh4 desk {MESH_DESKS} — arrivals declare "
                    "the mesh4 assignment; steward and meshfull derive theirs"
                )
        claimants = {contest.claimant for contest in self.contests}
        holders = {contest.holder for contest in self.contests}
        if claimants & holders:
            raise ValueError(f"claimant(s) also holders: {sorted(claimants & holders)}")
        if holders & callers:
            raise ValueError(
                f"holders never call (§3), but these arrive: {sorted(holders & callers)}"
            )
        recalls = [p.caller_id for p in self.evidence_calls if p.kind == "recall"]
        if len(recalls) != len(set(recalls)):
            raise ValueError(
                "at most one recall per caller (beat ids are `recall_<pid>`, unique by world construction) "
                "— distribute further pieces through carriers"
            )
        seen_slots: dict[str, str] = {}
        for contest in self.contests:
            for role, pid in (
                ("claimant", contest.claimant),
                ("holder", contest.holder),
            ):
                if pid not in by_id:
                    raise ValueError(
                        f"contest {role} {pid!r} has no card in this spec (boards author their own cast)"
                    )
            if contest.claimant not in callers:
                raise ValueError(f"claimant {contest.claimant} never arrives")
            if contest.specialty not in known_specialties():
                raise ValueError(f"contest specialty {contest.specialty!r} unknown")
            gold = by_id[contest.claimant].gold
            if gold != board_gold(contest.specialty):
                raise ValueError(
                    f"{contest.claimant}'s gold is not board_gold({contest.specialty!r}) — the deadline "
                    "family's URGENT/exact-service shape is what makes the contested slot the only move"
                )
            if contest.slot_id in seen_slots:
                raise ValueError(
                    f"slot {contest.slot_id} contested twice ({seen_slots[contest.slot_id]} and "
                    f"{contest.claimant}) — one claimant, one holder, one slot (§3)"
                )
            seen_slots[contest.slot_id] = contest.claimant
            pieces = self.evidence_for(contest.claimant)
            if not pieces:
                raise ValueError(f"{contest.claimant} has no evidence pieces at all")
            first = pieces[0]
            if first.kind != "intake" or first.caller_id != contest.claimant:
                raise ValueError(
                    f"{contest.claimant}'s piece 1 must be their own intake (§5)"
                )
        for decoy in self.decoys:
            if decoy.patient_id not in callers:
                raise ValueError(f"decoy {decoy.patient_id} never calls")
            if decoy.patient_id in claimants or decoy.patient_id in holders:
                raise ValueError(
                    f"decoy {decoy.patient_id} is also a contest party — decoys are never counted in the "
                    "reprio number (§6)"
                )
            if (
                decoy.defusing_caller_id is not None
                and decoy.defusing_caller_id not in callers
            ):
                raise ValueError(
                    f"decoy {decoy.patient_id}'s defusing caller {decoy.defusing_caller_id!r} never "
                    "arrives — the defusing fact must ride a real inbound call (§6)"
                )
        for piece in self.evidence_calls:
            if piece.about_claimant not in claimants:
                raise ValueError(
                    f"evidence about {piece.about_claimant!r}, who is not a claimant"
                )
            if piece.caller_id not in callers:
                raise ValueError(f"evidence caller {piece.caller_id!r} never arrives")
        for pid in self.intake_overrides:
            if pid not in by_id:
                raise ValueError(
                    f"intake override for a card this board does not own: {pid!r}"
                )
        for pid, by_topic in self.facts_overrides.items():
            if pid not in by_id:
                raise ValueError(
                    f"facts override for a card this board does not own: {pid!r}"
                )
            card_topics = {fact_topic(keys) for keys in by_id[pid].facts}
            for topic in by_topic:
                if topic not in OVERRIDABLE_FACT_TOPICS:
                    raise ValueError(
                        f"facts override on {pid} names topic {topic!r}; a twin may override only "
                        f"{OVERRIDABLE_FACT_TOPICS}"
                    )
                if topic not in card_topics:
                    raise ValueError(
                        f"facts override on {pid} names topic {topic!r}, which the card never answers — "
                        "an override replaces an answer, it never adds a topic"
                    )
        for pid in self.voicemail_callers:
            if pid not in callers:
                raise ValueError(f"voicemail caller {pid!r} never arrives")


# ── surnames: the pool + the uniqueness helper (id-is-surname convention) ────────────────────────────────
#: Fresh surnames for board casts, generated once against the whole landed corpus (patient surnames,
#: provider names, desk names — generated meshfull seats included — and plan vocabulary) and frozen here so
#: the pool cannot shrink under an author as the corpus grows. 400 entries; the 24 boards' combined cast is
#: ~800, so authors may also mint their own — `assert_fresh_surnames` is the actual gate, the pool is the
#: convenience. Names are English toponymic compounds, the corpus register.
SURNAME_POOL: tuple[str, ...] = (
    "Ashbrook",
    "Belby",
    "Byercliffe",
    "Caldcote",
    "Carnden",
    "Chaddijk",
    "Cransdon",
    "Drayfold",
    "Easgarth",
    "Eldergill",
    "Farnholm",
    "Garslund",
    "Grimmead",
    "Hainridge",
    "Hatherroyd",
    "Ingssett",
    "Keldsthwaite",
    "Lamwell",
    "Maisbrook",
    "Netherby",
    "Ostcliffe",
    "Pexcote",
    "Quenden",
    "Ramsdijk",
    "Saxdon",
    "Stanfold",
    "Tarlegarth",
    "Ulvergill",
    "Wadsholm",
    "Whinlund",
    "Yarmead",
    "Zealridge",
    "Ashby",
    "Belcliffe",
    "Byercote",
    "Caldden",
    "Carndijk",
    "Chaddon",
    "Cransfold",
    "Draygarth",
    "Easgill",
    "Elderholm",
    "Farnlund",
    "Garsmead",
    "Grimridge",
    "Hainroyd",
    "Hathersett",
    "Ingsthwaite",
    "Keldswell",
    "Lambrook",
    "Maisby",
    "Nethercliffe",
    "Ostcote",
    "Pexden",
    "Quendijk",
    "Ramsdon",
    "Saxfold",
    "Stangarth",
    "Tarlegill",
    "Ulverholm",
    "Wadslund",
    "Whinmead",
    "Yarridge",
    "Zealroyd",
    "Ashcliffe",
    "Belcote",
    "Byerden",
    "Calddijk",
    "Carndon",
    "Chadfold",
    "Cransgarth",
    "Draygill",
    "Easholm",
    "Elderlund",
    "Farnmead",
    "Garsridge",
    "Grimroyd",
    "Hainsett",
    "Hatherthwaite",
    "Ingswell",
    "Keldsbrook",
    "Lamby",
    "Maiscliffe",
    "Nethercote",
    "Ostden",
    "Pexdijk",
    "Quendon",
    "Ramsfold",
    "Saxgarth",
    "Stangill",
    "Tarleholm",
    "Ulverlund",
    "Wadsmead",
    "Whinridge",
    "Yarroyd",
    "Zealsett",
    "Ashcote",
    "Belden",
    "Byerdijk",
    "Calddon",
    "Carnfold",
    "Chadgarth",
    "Cransgill",
    "Drayholm",
    "Easlund",
    "Eldermead",
    "Farnridge",
    "Garsroyd",
    "Grimsett",
    "Hainthwaite",
    "Hatherwell",
    "Ingsbrook",
    "Keldsby",
    "Lamcliffe",
    "Maiscote",
    "Netherden",
    "Ostdijk",
    "Pexdon",
    "Quenfold",
    "Ramsgarth",
    "Saxgill",
    "Stanholm",
    "Tarlelund",
    "Ulvermead",
    "Wadsridge",
    "Whinroyd",
    "Yarsett",
    "Zealthwaite",
    "Ashden",
    "Beldijk",
    "Byerdon",
    "Caldfold",
    "Carngarth",
    "Chadgill",
    "Cransholm",
    "Draylund",
    "Easmead",
    "Elderridge",
    "Farnroyd",
    "Garssett",
    "Grimthwaite",
    "Hainwell",
    "Hatherbrook",
    "Ingsby",
    "Keldscliffe",
    "Lamcote",
    "Maisden",
    "Netherdijk",
    "Ostdon",
    "Pexfold",
    "Quengarth",
    "Ramsgill",
    "Saxholm",
    "Stanlund",
    "Tarlemead",
    "Ulverridge",
    "Wadsroyd",
    "Whinsett",
    "Yarthwaite",
    "Zealwell",
    "Ashdijk",
    "Beldon",
    "Byerfold",
    "Caldgarth",
    "Carngill",
    "Chadholm",
    "Translund",
    "Draymead",
    "Easridge",
    "Elderroyd",
    "Farnsett",
    "Garsthwaite",
    "Grimwell",
    "Hainbrook",
    "Hatherby",
    "Ingscliffe",
    "Keldscote",
    "Lamden",
    "Maisdijk",
    "Netherdon",
    "Ostfold",
    "Pexgarth",
    "Quengill",
    "Ramsholm",
    "Saxlund",
    "Stanmead",
    "Tarleridge",
    "Ulverroyd",
    "Wadssett",
    "Whinthwaite",
    "Yarwell",
    "Zealbrook",
    "Ashdon",
    "Belfold",
    "Byergarth",
    "Caldgill",
    "Carnholm",
    "Chadlund",
    "Cransmead",
    "Drayridge",
    "Easroyd",
    "Eldersett",
    "Farnthwaite",
    "Garswell",
    "Grimbrook",
    "Hainby",
    "Hathercliffe",
    "Ingscote",
    "Keldsden",
    "Lamdijk",
    "Maisdon",
    "Netherfold",
    "Ostgarth",
    "Pexgill",
    "Quenholm",
    "Ramslund",
    "Saxmead",
    "Stanridge",
    "Tarleroyd",
    "Ulversett",
    "Wadsthwaite",
    "Whinwell",
    "Yarbrook",
    "Zealby",
    "Ashfold",
    "Belgarth",
    "Byergill",
    "Caldholm",
    "Carnlund",
    "Chadmead",
    "Cransridge",
    "Drayroyd",
    "Eassett",
    "Elderthwaite",
    "Farnwell",
    "Garsbrook",
    "Grimby",
    "Haincliffe",
    "Hathercote",
    "Ingsden",
    "Keldsdijk",
    "Lamdon",
    "Maisfold",
    "Nethergarth",
    "Ostgill",
    "Pexholm",
    "Quenlund",
    "Ramsmead",
    "Saxridge",
    "Stanroyd",
    "Tarlesett",
    "Ulverthwaite",
    "Wadswell",
    "Whinbrook",
    "Yarby",
    "Zealcliffe",
    "Ashgarth",
    "Belgill",
    "Byerholm",
    "Caldlund",
    "Carnmead",
    "Chadridge",
    "Cransroyd",
    "Draysett",
    "Easthwaite",
    "Elderwell",
    "Farnbrook",
    "Garsby",
    "Grimcliffe",
    "Haincote",
    "Hatherden",
    "Ingsdijk",
    "Keldsdon",
    "Lamfold",
    "Maisgarth",
    "Nethergill",
    "Ostholm",
    "Pexlund",
    "Quenmead",
    "Ramsridge",
    "Saxroyd",
    "Stansett",
    "Tarlethwaite",
    "Ulverwell",
    "Wadsbrook",
    "Whinby",
    "Yarcliffe",
    "Zealcote",
    "Ashgill",
    "Belholm",
    "Byerlund",
    "Caldmead",
    "Carnridge",
    "Chadroyd",
    "Cranssett",
    "Draythwaite",
    "Easwell",
    "Elderbrook",
    "Farnby",
    "Garscliffe",
    "Grimcote",
    "Hainden",
    "Hatherdijk",
    "Ingsdon",
    "Keldsfold",
    "Lamgarth",
    "Maisgill",
    "Netherholm",
    "Ostlund",
    "Pexmead",
    "Quenridge",
    "Ramsroyd",
    "Saxsett",
    "Stanthwaite",
    "Tarlewell",
    "Ulverbrook",
    "Wadsby",
    "Whincliffe",
    "Yarcote",
    "Zealden",
    "Ashholm",
    "Bellund",
    "Byermead",
    "Caldridge",
    "Carnroyd",
    "Chadsett",
    "Cransthwaite",
    "Draywell",
    "Easbrook",
    "Elderby",
    "Farncliffe",
    "Garscote",
    "Grimden",
    "Haindijk",
    "Hatherdon",
    "Ingsfold",
    "Keldsgarth",
    "Lamgill",
    "Maisholm",
    "Netherlund",
    "Ostmead",
    "Pexridge",
    "Quenroyd",
    "Ramssett",
    "Saxthwaite",
    "Stanwell",
    "Tarlebrook",
    "Ulverby",
    "Wadscliffe",
    "Whincote",
    "Yarden",
    "Zealdijk",
    "Ashlund",
    "Belmead",
    "Byerridge",
    "Caldroyd",
    "Carnsett",
    "Chadthwaite",
    "Cranswell",
    "Draybrook",
    "Easby",
    "Eldercliffe",
    "Farncote",
    "Garsden",
    "Grimdijk",
    "Haindon",
    "Hatherfold",
    "Ingsgarth",
    "Keldsgill",
    "Lamholm",
    "Maislund",
    "Nethermead",
    "Ostridge",
    "Pexroyd",
    "Quensett",
    "Ramsthwaite",
    "Saxwell",
    "Stanbrook",
    "Tarleby",
    "Ulvercliffe",
    "Wadscote",
    "Whinden",
    "Yardijk",
    "Zealdon",
    "Ashmead",
    "Belridge",
    "Byerroyd",
    "Caldsett",
    "Carnthwaite",
    "Chadwell",
    "Cransbrook",
    "Drayby",
    "Eascliffe",
    "Eldercote",
    "Farnden",
    "Garsdijk",
    "Grimdon",
    "Hainfold",
    "Hathergarth",
    "Ingsgill",
    "Keldsholm",
    "Lamlund",
    "Maismead",
    "Netherridge",
    "Ostroyd",
    "Pexsett",
    "Quenthwaite",
    "Ramswell",
)


def _surname_of(card: PatientCard) -> str:
    """The card's surname under the id-is-surname convention: the last word of the display name."""
    return card.name.split()[-1]


def taken_surnames() -> frozenset[str]:
    """Every surname already spoken for, lowercased: corpus cards (registered boards' included), providers, desks."""
    taken = {card.name.split()[-1].lower() for card in CORPUS.values()}
    for provider in PROVIDERS.values():
        for part in provider.name.split()[-1].split("-"):
            taken.add(part.lower())
    for spec in board_registry.REGISTERED.values():
        for provider in spec.new_providers:
            for part in provider.name.split()[-1].split("-"):
                taken.add(part.lower())
    taken.update(desk.display_name.split()[-1].lower() for desk in CAST)
    taken.update(name.lower() for name in _DESK_SURNAMES)
    return frozenset(taken)


def fresh_surnames(count: int) -> tuple[str, ...]:
    """The first `count` pool surnames not yet taken anywhere — the author's draw.

    Deterministic given the registration state, so an author who registers pairs in the locked P01..P12 order draws a stable slice. The draw CLAIMS nothing; only registering cards does.

    Raises:
        ValueError: If the pool cannot cover the ask (mint your own and run `assert_fresh_surnames`).
    """
    taken = taken_surnames()
    fresh = [name for name in SURNAME_POOL if name.lower() not in taken]
    if len(fresh) < count:
        raise ValueError(
            f"the pool has {len(fresh)} fresh surnames left, {count} asked — mint your own (the corpus "
            "register is English toponymic compounds) and let assert_fresh_surnames hold the line"
        )
    return tuple(fresh[:count])


def assert_fresh_surnames(
    cards: Sequence[PatientCard], *, kin_of: Mapping[str, str] | None = None
) -> None:
    """Refuse any card whose surname collides with the corpus, any registered board, providers, or desks.

    The id-is-surname convention is enforced with it: `pt_<surname lowercased>` (an optional `_x` suffix
    allowed for the older disambiguation shape, `pt_okafor_r`). `kin_of` declares the ONE sanctioned
    sharing shape — a family carrier on the same board as their claimant (`kin id -> the card whose surname
    they share`); both must be in `cards`, so kinship can never span boards.

    Raises:
        ValueError: On a collision, a convention break, or a kin declaration that does not resolve.
    """
    kin = dict(kin_of or {})
    by_id = {card.id: card for card in cards}
    for kin_id, of_id in kin.items():
        if kin_id not in by_id or of_id not in by_id:
            raise ValueError(
                f"kin declaration {kin_id!r} -> {of_id!r} names a card outside this board"
            )
        if _surname_of(by_id[kin_id]).lower() != _surname_of(by_id[of_id]).lower():
            raise ValueError(
                f"kin {kin_id!r} does not actually share {of_id!r}'s surname"
            )
    taken = taken_surnames()
    fresh_here: dict[str, str] = {}
    for card in cards:
        if CORPUS.get(card.id) is card:
            continue  # a pair's shared card, already registered by the other twin
        surname = _surname_of(card)
        stem = f"pt_{surname.lower()}"
        if not (card.id == stem or card.id.startswith(f"{stem}_")):
            raise ValueError(
                f"{card.id!r} breaks the id-is-surname convention for {card.name!r} (expected "
                f"{stem!r} or {stem}_<x>)"
            )
        if card.id in kin:
            continue
        if surname.lower() in taken:
            raise ValueError(
                f"surname {surname!r} ({card.id}) collides with the corpus, a registered board, a "
                "provider, or a desk — draw from fresh_surnames()"
            )
        prior = fresh_here.get(surname.lower())
        if prior is not None:
            raise ValueError(
                f"surname {surname!r} used twice on one board ({prior} and {card.id}) without a kin_of "
                "declaration"
            )
        fresh_here[surname.lower()] = card.id


# ── registration ──────────────────────────────────────────────────────────────────────────────────────────
def register_board(spec: BoardSpec, *, kin_of: Mapping[str, str] | None = None) -> None:
    """Wire one board twin into the whole stack. Call once per twin, PLAIN FIRST within a pair.

    What one call does, in order: surname + structural validation; the spec joins `board_registry` (which is what turns on the reprio-family value semantics and the v2/v3 surface policies for this id); the cards fold into the corpus; the scenario joins `pressure`'s registries; the cell builder and the §8a obligation battery join `design_check`. Any failure raises before the LATER stages run, and `unregister_board` undoes a partial registration in tests.

    Args:
        spec: The twin, as pure data.
        kin_of: Sanctioned same-surname declarations (`assert_fresh_surnames`).

    Raises:
        ValueError: On any validation failure, a taken id, or a split twin registered before its plain twin.
    """

    if spec.board_id in board_registry.REGISTERED:
        raise ValueError(f"{spec.board_id!r} is already registered")
    twins = [
        other
        for other in board_registry.REGISTERED.values()
        if other.pair_id == spec.pair_id
    ]
    if spec.twin == "split" and not any(other.twin == "plain" for other in twins):
        raise ValueError(
            f"{spec.board_id!r}: register the plain twin first — the split twin seeds its calendar from "
            "it (calendar_of), so the pair contrast is never confounded by the seed"
        )
    for other in twins:
        if other.twin == spec.twin:
            raise ValueError(
                f"pair {spec.pair_id!r} already has a {spec.twin} twin ({other.board_id})"
            )
        if other.size != spec.size or other.pair_stem() != spec.pair_stem():
            raise ValueError(
                f"{spec.board_id!r} disagrees with its twin {other.board_id!r} on size/stem — twins share "
                "one skeleton (prompt §1)"
            )
    assert_fresh_surnames(spec.cards, kin_of=kin_of)
    roster = spec.roster()  # validates the extension (BoardRoster.__post_init__)
    for contest in spec.contests:
        provider = (
            roster.providers.get(contest.provider_id) if roster else None
        ) or PROVIDERS.get(contest.provider_id)
        if provider is None:
            raise ValueError(
                f"contest provider {contest.provider_id!r} is neither on the base roster nor in this "
                "board's new_providers"
            )
        if provider.specialty != contest.specialty:
            raise ValueError(
                f"contest slot {contest.slot_id} sits on a {provider.specialty} diary, not "
                f"{contest.specialty}"
            )
    board_registry.REGISTERED[spec.board_id] = spec
    try:
        register_board_cards(spec.cards)
        register_board_scenario(spec.board_id, spec.script(), spec.seeding())
    except BaseException:
        unregister_board(spec.board_id)
        raise


def unregister_board(board_id: str) -> None:
    """Undo `register_board` — TEST-ONLY (fixture pairs must leave the registries as they found them).

    Safe on a partial registration (each stage is popped only if present); cards leave the corpus only if they are still the board's own objects, so a pair's shared cards survive until the LAST twin unregisters.
    """

    spec = board_registry.REGISTERED.get(board_id)
    if spec is None:
        return
    # The scenario/obligation stages are popped while the id is STILL in the registry — their own guards
    # key on it — and the registry entry goes last, so a partial registration unwinds in any state.
    unregister_board_scenario(board_id)
    del board_registry.REGISTERED[board_id]
    still_shared = {
        card.id for other in board_registry.REGISTERED.values() for card in other.cards
    }
    unregister_board_cards(
        tuple(card for card in spec.cards if card.id not in still_shared)
    )


def registered_pairs() -> dict[str, tuple[BoardSpec, ...]]:
    """`pair_id -> its registered twins`, in registration order."""
    pairs: dict[str, list[BoardSpec]] = {}
    for spec in board_registry.REGISTERED.values():
        pairs.setdefault(spec.pair_id, []).append(spec)
    return {pair_id: tuple(twins) for pair_id, twins in pairs.items()}


def verify_board_registry(*, complete: bool = False) -> str:
    """The registry-wide invariants: sizes all-distinct across pairs; endpoints 6 and 30 when `complete`.

    Per-board gates run inside `design_check.check_board`; THESE claims range over the whole registry, so they live here and a full run checks them (with `complete=True`) before anything flies. The distinctness half also runs inside every board's own gate battery, so a colliding size fails at registration-time proving too.

    Returns:
        A one-line proof.

    Raises:
        ValueError: On a duplicate size, a twinless pair (when `complete`), or missing endpoints.
    """
    pairs = registered_pairs()
    sizes: dict[int, str] = {}
    for pair_id, twins in pairs.items():
        size = twins[0].size
        if size in sizes and sizes[size] != pair_id:
            raise ValueError(
                f"pairs {sizes[size]!r} and {pair_id!r} share size {size} — sizes are the scaling read's "
                "x-axis and must be all-distinct (prompt §3)"
            )
        sizes[size] = pair_id
        if complete and len(twins) != 2:
            raise ValueError(
                f"pair {pair_id!r} has {len(twins)} twin(s); a pair is plain + split"
            )
    if complete:
        for endpoint in (6, 30):
            if endpoint not in sizes:
                raise ValueError(
                    f"no registered pair at size {endpoint} — the §3 size set keeps both endpoints"
                )
    return f"{len(pairs)} pair(s), sizes {sorted(sizes)} all-distinct" + (
        ", endpoints 6 and 30 present" if complete else ""
    )


__all__ = [
    "BOARD_MAX_CALLERS",
    "EVIDENCE_KINDS",
    "MAX_CALLERS",
    "MAX_CALLS",
    "OVERRIDABLE_FACT_TOPICS",
    "SURNAME_POOL",
    "TWINS",
    "BoardContest",
    "BoardSpec",
    "Decoy",
    "EvidenceCall",
    "assert_fresh_surnames",
    "board_gold",
    "board_memo_text",
    "fresh_surnames",
    "register_board",
    "registered_pairs",
    "taken_surnames",
    "unregister_board",
    "verify_board_registry",
]
