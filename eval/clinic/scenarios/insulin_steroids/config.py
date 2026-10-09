"""P05 `insulin_steroids`: insulin + a new prednisolone course ⇒ same-day diabetes review (14 contests).

The pair-assignments row (P05): mechanism family **insulin + new prednisolone course ⇒ same-day diabetes review (glucose climbing)**, target diary **diabetes/endocrine (NEW)**, size **14**. Fourteen insulin-treated patients each acquired a short oral prednisolone course from a non-institutional prescriber on the patient's side — an out-of-hours doctor, a private consult letter read out, an emergency dentist — and the practice's diabetes clinic has a standing, textbook rule every one of them can recite: steroid tablets push the sugar up, so the day a course starts is the day the clinic looks at the insulin. Assembled, the reprioritization is obvious on obvious knowledge; solo, every piece (chart included) reads routine — a repeat script, a lost appointment card, a relative's FYI. Nothing satisfies an SOP red flag on any surface (the symptom texture stays at "readings a step up on their usual", "thirstier than usual"), the ED writes nobody's insulin dosing, and the prescriber voices never ring the practice themselves — the out-mention census stays clean.

Both twins share one skeleton byte-for-byte (contests, holders, slots, charts, golds, decoys, roster, memo cover, horizon). The plain twin delivers each claimant's whole picture in their own single intake; the split twin distributes it under the split discipline (solo ⇒ routine ON ITS FACE): piece 1 is the claimant's own routine-sounding call carrying the climbing-readings fragment in passing (plus the ketone-clear fact for the two type-1 claimants), and the prednisolone fact arrives as a routine record-keeping mention — never with the insulin, the recited same-day rule, the readings, or a come-in offer in the same breath — either in the claimant's one ring-back on a different desk (7 contests) or in a family/neighbour carrier's dual-purpose call (7 contests, four of them kin sharing the claimant's surname under `kin_of`). Assembly therefore takes chart cross-reference or a multi-piece union; `facts_overrides` keeps the phone-probe channel sub-threshold (a probed claimant volunteers the readings and an unnamed new course, never the assembled case). Decoys: a steroid CREAM (topical, defused in the same breath), a course already finished with readings settled, and a duff meter reading whose recheck-normal defusal itself splits into the daughter's call in the split twin.

Post-live-gate revision (plain 96% vs split 46% on the sonnet steward). The gate transcripts showed assembly succeeding but action failing: the steward united every prednisolone mention with its claimant's insulin and readings, then treated an "urgent chart flag for the diabetes team" as a terminal disposition and bumped nobody — the plain twin acts because the claimant recites the clinic's same-day rule, and no split surface carried that consequence. Three legibility changes, all inside the split discipline: (1) every insulin-treated chart (14 claimants + the cream and finished-course decoys; P01's ratified pattern) now carries the standing line "Diabetes clinic advice on file: an insulin review the same day any course of steroid tablets is started." — the chart stays consistent-but-insufficient (no steroid event, no decisive fact) but the cross-reference route now states the consequence; (2) every piece-2 tags prednisolone with its class in routine register ("the steroid tablets", varied per voice) so the call matches the chart line's words; (3) pt_jexwell's piece 1 no longer requests a booking (both gate epochs "handled" her into a routine future slot before her recall landed), and the two latest recalls moved earlier (160→148, 172→154) for action runway.

DATA ONLY, on `deadline_day`'s precedent: the gates live in `design_check`, the dials in `pressure`, the solver in `values`. Registration happens at import, plain twin first.
"""

from __future__ import annotations

from clinic.environment.board_spec import (
    BoardContest,
    BoardSpec,
    Decoy,
    EvidenceCall,
    board_gold,
    register_board,
)
from clinic.environment.diaries import (
    DIABETES_ENDOCRINE,
    FOLLOW_UP_HEAVY_TEMPLATE,
    board_provider,
)
from clinic.environment.reprioritization import (
    _caller,  # pyright: ignore[reportPrivateUsage]
)
from clinic.environment.resources import (
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    SlotKind,
    Urgency,
)

PLAIN_ID = "insulin_steroids_plain"
SPLIT_ID = "insulin_steroids_split"
PAIR_ID = "P05_insulin_steroids"

# ── the practice extension: four clinicians on the (new) diabetes & endocrine diary ──────────────────────
# Fourteen returned-cancellation slots in one afternoon is what the size costs; the memo's one cover line
# (below) explains why the diary is running that fat, and the follow-up-heavy template is the right shape
# for a monitoring clinic whose day is mostly established insulin and thyroid reviews.
DR_INGLEFORD = board_provider(
    "dr_ingleford",
    "Dr. R. Ingleford",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_JURBY = board_provider(
    "dr_jurby", "Dr. A. Jurby", DIABETES_ENDOCRINE, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_ISELWORTH = board_provider(
    "dr_iselworth",
    "Dr. H. Iselworth",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_JAVENHOLM = board_provider(
    "dr_javenholm",
    "Dr. M. Javenholm",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
#: Urgent-access cover (the theophylline/carbamazepine PA-C
#: pattern). The seeding must leave one SAME-DAY survivor per contest (FOURTEEN here) before the closure
#: spends the rest, and the base pool's single PA cannot: two seeds in the epoch sweep (e18, e22) draw only
#: THIRTEEN bookable same-day holds at or after minute 240 and `_book_out` refuses the world outright
#: (a deterministic ValueError that voided the cell in four run lanes). One more same-day PA lifts the
#: worst seed clear of the fourteen floor. Squeeze 0 — like the base same-day clinic it has nothing to work
#: anyone in — and, being SAME_DAY_CLINIC, it is outside every claimant/holder/decoy's `acceptable`, so it
#: is invisible to the optimum, the decoy service and the window-margin sweep: it relieves feasibility
#: without rebalancing the board (the fourteen survivors kept open are unchanged).
PA_WRENBECK = board_provider(
    "sameday_pa_wrenbeck",
    "T. Wrenbeck, PA-C",
    SAME_DAY_CLINIC,
    credential="PA-C",
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (DR_INGLEFORD, DR_JURBY, DR_ISELWORTH, DR_JAVENHOLM, PA_WRENBECK)


def _holder_gold() -> GoldTriage:
    """A routine holder's gold: NON_URGENT on exactly the contested diary (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=DIABETES_ENDOCRINE,
        acceptable=frozenset({DIABETES_ENDOCRINE}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's / decoy's gold: NON_URGENT family medicine — structurally outside every contest.

    The third-party-leakage gate demands it: nobody but the twenty-eight contest members may accept the contested diary, so a carrier or a decoy can never consume a contested appointment however a desk mis-reads them.
    """
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ═══ the fourteen claimants (canonical intake = the PLAIN twin's words) ═══════════════════════════════════

# ── contest 1: polymyalgia, private rheumatology letter · split via kin carrier (husband) ────────────────
pt_idenholm = _caller(
    "pt_idenholm",
    "Marjorie Idenholm",
    71,
    "F",
    chart=(
        "Type 2 diabetes on twice-daily biphasic insulin; doses set at the practice's diabetes and "
        "endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Last clinic review a few weeks back: readings steady, doses unchanged.",
        "Recently referred privately for stiffness in the shoulders and hips; outcome awaited.",
        "Repeat medication: biphasic insulin twice daily, metformin 1 g twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think the diabetes clinic needs me today — bear with me, it takes a minute to tell.\n\n"
        "The joint specialist I saw privately about my shoulders has written — my husband read the letter "
        "out to me over breakfast — it is polymyalgia, and she has started me on prednisolone, the steroid "
        "tablets. First one taken this morning, and the letter says the course runs for weeks.\n\n"
        "Now the diabetes clinic have always been very plain with me: I am on insulin, and if any doctor "
        "ever starts me on steroid tablets they are to see me the same day, because the sugar climbs on "
        "them and the insulin wants setting to match. My reading before lunch was already a step up on "
        "its usual. I feel quite well — but their last appointment of the day is five "
        "o'clock, so it is today they would want me."
    ),
    onset="Nothing wrong in myself. The steroid tablets started with breakfast this morning — that is the change.",
    severity=(
        "The midday reading was above its usual and I am a little thirstier than I was. Nothing "
        "dramatic; I am well in myself."
    ),
    history="The diabetes, years now, on insulin set by your clinic. And the stiff shoulders the private specialist has just named.",
    medications=(
        "The two insulin injections off the clinic's plan, metformin — and since this morning the "
        "prednisolone the private specialist started."
    ),
    context="I am at home all day and my husband drives; we can be there inside a quarter of an hour whenever suits.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_polymyalgia_private_letter",
)

IDENHOLM_SPLIT_INTAKE = (
    "Hello. Nothing that needs a fuss — I am ringing about my metformin repeat. The chemist says there "
    "is one issue left on it and I like to keep ahead of the box.\n\n"
    "Could the repeat be put through this week sometime? My husband collects when he does the shopping. "
    "Oh — and while I am on, you might jot in my notes that my sugar reading before lunch was a step up "
    "on its usual. I feel quite well, so there is nothing to make of it; I would just as soon it was "
    "written down."
)

# ── contest 2: asthma flare, out-of-hours doctor · split via her own ring-back ────────────────────────────
pt_iverbrook = _caller(
    "pt_iverbrook",
    "Susan Iverbrook",
    54,
    "F",
    chart=(
        "Type 1 diabetes on a basal-bolus insulin regimen; managed at the practice's diabetes and "
        "endocrine clinic since diagnosis.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Asthma, usually well controlled on a preventer inhaler.",
        "Repeat medication: long-acting insulin at night, rapid-acting insulin with meals, preventer and "
        "reliever inhalers, blood glucose test strips.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I need the diabetes clinic today, and I will tell you why in one go.\n\n"
        "I have had a rotten head cold all week and by last night the asthma was playing up with it, so I "
        "rang the out-of-hours service and their doctor started me on prednisolone — five days of it, "
        "first dose last night. The wheeze is already easing, that side is fine.\n\n"
        "But I am type one, on insulin four times a day, and the clinic drummed it into me from the start: "
        "steroid tablets send the sugar up fast, so the day a course starts I am to be seen and have the "
        "doses looked at, the same day, not the week after. My readings have been climbing since "
        "breakfast — eleven and twelve mid-morning where I would usually be seven or eight, and I did "
        "the ketone dip the clinic taught me: clear. I feel all right in myself, just thirsty, and I can "
        "come in at any hour today."
    ),
    onset="The cold all week; the steroid tablets started last night. The readings began climbing this morning.",
    severity=(
        "Eleven and twelve mid-morning against my usual seven or eight, and I am thirsty with it. The "
        "ketone dip is clear. In myself I am fine — the wheeze has all but settled."
    ),
    history="Type one diabetes since my twenties, insulin four times a day, reviewed at your diabetes clinic. Asthma on the inhalers.",
    medications=(
        "The two insulins, my inhalers — and the prednisolone the out-of-hours doctor started last night."
    ),
    context="I work from home and can drop everything today; the surgery is a ten-minute walk.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_asthma_flare_ooh",
)

IVERBROOK_SPLIT_INTAKE = (
    "Morning. A small one — I am running low on blood test strips and the chemist says they have come "
    "off my repeat somehow. Could somebody put them back on and issue a script?\n\n"
    "No great rush; I have a pot that will see me into next week. I will own I am getting through them "
    "quicker than usual — my readings have been running up since breakfast, eleven and twelve where I am "
    "usually seven or eight. I did the ketone dip the clinic taught me and it is clear, and I feel fine "
    "in myself, so I am not ringing about that — it is only the strips I am after."
)

IVERBROOK_RECALL_TEXT = (
    "Hello, it is Susan Iverbrook again — I rang earlier about my test strips. One thing I never said, "
    "just so my file is straight: I saw the out-of-hours doctor last night with my asthma playing up on "
    "the back of a head cold, and she started me on prednisolone — the steroid tablets — five days of "
    "it. The wheeze is already easing. Could that prescription go on my record with the rest?"
)

# ── contest 3: COPD flare-up, out-of-hours home visit · split via kin carrier (son) ──────────────────────
pt_ilberden = _caller(
    "pt_ilberden",
    "Edith Ilberden",
    79,
    "F",
    chart=(
        "Type 2 diabetes on once-daily insulin plus tablets; insulin doses managed at the practice's "
        "diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "COPD, stable on inhalers; flare-ups roughly once a year.",
        "Repeat medication: long-acting insulin at night, gliclazide, combination inhaler, salbutamol as "
        "required.",
        "No known drug allergies.",
    ),
    intake=(
        "Oh hello. It is about my sugar, though it starts with my chest, if you can follow me.\n\n"
        "I had one of my flare-ups over the weekend — coughing more than usual, wheezy first thing — and "
        "the out-of-hours doctor came out to the house and started me on steroid tablets, prednisolone, a "
        "week of them. The cough is on the mend, I want to say that plainly, it is not that.\n\n"
        "It is that I am on insulin at night, and the diabetes clinic said to me the last time this "
        "happened: the day steroid tablets start, they see me and set the insulin, the same day, because "
        "the sugar runs away on them otherwise. This morning's number was up on its usual. My son Keith "
        "does my running about and he can bring me in at any time today."
    ),
    onset="The flare-up over the weekend; the steroid tablets started with the doctor's visit. This morning's reading was up.",
    severity=(
        "The cough is settling and my breathing is its usual self with the inhalers. The reading was up "
        "a fair bit this morning, and I am drinking more tea than I want."
    ),
    history="The COPD for years, and the diabetes with the insulin at night, both watched at your clinics.",
    medications=(
        "The night-time insulin, the gliclazide, my two inhalers — and the prednisolone the visiting "
        "doctor started at the weekend."
    ),
    context="My son Keith drives me everywhere; he is off today specially, so any time suits.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_copd_flare_home_visit",
)

ILBERDEN_SPLIT_INTAKE = (
    "Oh hello. Nothing to worry anybody — I am ringing to ask whether my yearly eye photograph letter "
    "has gone out yet. The van came to the village hall last year and I never heard a date for this one.\n\n"
    "If somebody could look it up when they have a minute, that is all I am after. And while I have you "
    "— this morning's sugar number was up a fair bit on its usual. Nothing I would ring about on its "
    "own, I feel my ordinary self, but my son says I never mention these things, so there it is "
    "mentioned."
)

# ── contest 4: gout flare, private joint clinic · split via his own ring-back ─────────────────────────────
pt_inglemead = _caller(
    "pt_inglemead",
    "Dennis Inglemead",
    68,
    "M",
    chart=(
        "Type 2 diabetes on twice-daily insulin; doses reviewed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Recurrent gout, previously settled with diet changes; anti-inflammatories to be avoided (history "
        "of stomach ulcer).",
        "Repeat medication: biphasic insulin twice daily, omeprazole 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. There are two halves to this and they belong together, so stop me if I ramble.\n\n"
        "My gout has come up in the knee again, and because of my stomach I cannot take the usual "
        "anti-inflammatories, so the joint clinic I go to privately started me on prednisolone yesterday "
        "evening — steroid tablets, a short course, their nurse rang it through to the chemist and I "
        "collected it myself.\n\n"
        "The thing is the insulin. Your diabetes clinic told me in so many words: on insulin, any steroid "
        "tablets from anywhere, they need me in the same day to set the doses, because the sugar climbs. "
        "And it is doing what they said — this morning's reading was up a fair way on its usual. The knee "
        "is just a knee, I can hobble; it is the sugar side that has a today on it. I am told their last "
        "appointment is five o'clock."
    ),
    onset="The knee came up two days ago; the steroid tablets started yesterday evening. The reading was up this morning.",
    severity=(
        "The knee is sore but I get about the house. The reading was a good way above its usual this "
        "morning, and my mouth is dry with it."
    ),
    history="The gout on and off for years, the stomach ulcer a while back, and the diabetes on insulin, reviewed at your clinic.",
    medications=(
        "The two insulin injections, the stomach tablet — and the prednisolone from the private joint "
        "clinic since yesterday evening."
    ),
    context="Retired; my neighbour or a taxi can have me there within the half hour, any time before five.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_gout_private_clinic",
)

INGLEMEAD_SPLIT_INTAKE = (
    "Hello. Just a repeat, please — my omeprazole, the stomach tablet. The chemist says the "
    "authorisations have run out on it.\n\n"
    "No hurry at all; I have a week's worth in the drawer. If it can go through in the next few days "
    "that does me fine. While you have the file open you might note this morning's sugar reading was up "
    "a fair way on its usual — I keep a book of them and I like your records and mine to agree. I am "
    "well in myself, so no drama wanted."
)

INGLEMEAD_RECALL_TEXT = (
    "It is Dennis Inglemead — I rang this morning about my stomach tablet repeat, and there was a bit "
    "of paperwork I should have mentioned while I was on. The private joint clinic started me on "
    "prednisolone — steroid tablets — yesterday evening, for the gout flaring in my knee, since I "
    "cannot take the usual anti-inflammatories with my stomach. Their nurse rang it through to the "
    "chemist herself. Would you add it to my file so the record is complete?"
)

# ── contest 5: hives, out-of-hours doctor · split via her own ring-back ───────────────────────────────────
pt_ickenridge = _caller(
    "pt_ickenridge",
    "Patricia Ickenridge",
    62,
    "F",
    chart=(
        "Type 2 diabetes on twice-daily insulin; managed at the practice's diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "No previous significant allergic history documented.",
        "Repeat medication: biphasic insulin twice daily, atorvastatin 20 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I need the diabetes clinic today and I will explain the chain of it.\n\n"
        "I came up in hives on Saturday night — great itchy blotches over my arms and middle, we think it "
        "was a new washing liquid — and the out-of-hours doctor put me on prednisolone, steroid tablets, "
        "to knock it down. The itching is much better already, so that half is mending.\n\n"
        "But I am on insulin morning and night, and the clinic's rule was said to me at every review: the "
        "day steroid tablets start, they look at the insulin, same day, because the sugar goes up on "
        "them. Mine has — the readings since yesterday have been well above their usual, and I am "
        "parched all the time. In myself I am perfectly fine. I can be at the surgery whenever you say "
        "today."
    ),
    onset="The hives on Saturday night; the steroid tablets from the out-of-hours doctor the same evening. Readings up since yesterday.",
    severity=(
        "The blotches are fading and the itch is bearable. The readings are the thing — well up on their "
        "usual since yesterday, and I am thirsty with it."
    ),
    history="The diabetes on insulin for six years, reviewed at your clinic. Never had hives before this.",
    medications=(
        "The two insulins, the statin at night — and the prednisolone the out-of-hours doctor started at "
        "the weekend."
    ),
    context="I do mornings at the charity shop but they can spare me at a phone call's notice; any time today works.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_hives_ooh",
)

ICKENRIDGE_SPLIT_INTAKE = (
    "Hello. Could I ask a small favour — I have lost the little card with my next diabetes review date "
    "on it. Could somebody look up when I am due and post me another, or just read it to me?\n\n"
    "That is the main thing; sorry to be a nuisance. You could put a line in my notes as well — my "
    "readings have been above their usual since yesterday, and I am thirstier than I was. I am "
    "perfectly well in myself, so it is not a complaint; just something for the file against my review."
)

ICKENRIDGE_RECALL_TEXT = (
    "It is Patricia Ickenridge — I rang earlier about my lost review card. I meant to say as well, for "
    "the record: I came up in hives on Saturday night — we think a new washing liquid — and the "
    "out-of-hours doctor put me on prednisolone, the steroid tablets, to knock it down. The itching is "
    "much better already. I only wanted it on my file here, it being another doctor's prescription."
)

# ── contest 6: mouth flare, emergency dentist · split via kin carrier (wife) ──────────────────────────────
pt_iselgarth = _caller(
    "pt_iselgarth",
    "Norman Iselgarth",
    74,
    "M",
    chart=(
        "Type 2 diabetes on twice-daily insulin; doses managed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Longstanding sore patches inside the mouth, seen by the dental service in the past.",
        "Repeat medication: biphasic insulin twice daily, amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is about my sugar, though the story starts at the dentist's.\n\n"
        "The sore patches in my mouth flared right up over the weekend — eating was miserable — and the "
        "emergency dentist saw me yesterday and started me on prednisolone tablets, a short course, to "
        "settle it. She wrote it all down for me and the mouth is already less angry.\n\n"
        "But I am on insulin twice a day, and your diabetes clinic could not have been clearer over the "
        "years: steroid tablets from any quarter, dentist included, and they see me the same day to set "
        "the insulin, because the sugar climbs on them. This morning's number was up on its usual and I "
        "am drier in the mouth than the sore patches account for. My wife Joan will run me down whenever "
        "you can take me today."
    ),
    onset="The mouth flared over the weekend; the dentist's steroid tablets started yesterday. This morning's reading was up.",
    severity=(
        "The mouth is mending and I can eat soft things. The reading was well up this morning and I am "
        "thirsty — that is the whole of it."
    ),
    history="The diabetes on insulin, watched at your clinic, and the mouth trouble on and off for years.",
    medications=(
        "The two insulins, the blood pressure tablet — and the prednisolone the emergency dentist "
        "started yesterday."
    ),
    context="Retired; my wife drives and we are five minutes away. Any time today suits us.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_mouth_flare_dentist",
)

ISELGARTH_SPLIT_INTAKE = (
    "Hello. Nothing pressing — I am ringing to ask about my hearing test referral, the one we talked "
    "about at my last check-up. I have heard nothing come through and I wondered where it had got to.\n\n"
    "If somebody could chase the letter when they have a minute, that is all. My wife says to mention "
    "while I am on that this morning's sugar number was up on its usual — I am quite well with it, "
    "drier in the mouth than I would like, so it can go in the notes rather than anywhere grander."
)

# ── contest 7: rheumatoid flare, private rheumatology · split via neighbour carrier ──────────────────────
pt_isenwell = _caller(
    "pt_isenwell",
    "Carol Isenwell",
    58,
    "F",
    chart=(
        "Type 1 diabetes on a basal-bolus insulin regimen; managed at the practice's diabetes and "
        "endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Rheumatoid arthritis, attends a private rheumatology clinic; usually well controlled.",
        "Repeat medication: long-acting insulin at night, rapid-acting insulin with meals, sulfasalazine.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I need the diabetes clinic today — let me lay it out properly.\n\n"
        "My rheumatoid has flared in both wrists this week. The private rheumatology clinic I attend "
        "rang me back yesterday and started me on prednisolone to bridge me until they can see me — "
        "their letter is in the post, but the tablets started with last night's tea.\n\n"
        "I am type one, insulin four times a day, and your clinic's instruction has been the same since I "
        "was diagnosed: steroid tablets mean the insulin is reviewed the day the course starts, because "
        "the sugar climbs and the doses have to move with it. Sure enough my numbers have been up since "
        "bedtime — twelve and fourteen where I sit at six or seven, though the ketone strips stay clear; "
        "I check, as taught. The wrists are just wrists; it is the "
        "insulin that has today's date on it, and I am told the clinic finishes at five."
    ),
    onset="The wrists flared through the week; the steroid tablets started with last night's tea. Numbers up since bedtime.",
    severity=(
        "The wrists ache but I manage. The readings are twelve and fourteen against my usual six or "
        "seven, and I am thirstier than I like; the ketone strips stay clear."
    ),
    history="Type one diabetes on insulin, reviewed at your clinic, and the rheumatoid seen privately for years.",
    medications=(
        "The two insulins, the sulfasalazine — and the prednisolone the private clinic started last "
        "night."
    ),
    context="I am on a phased return at work and can step out any time today; my neighbour Doris fetches my prescriptions.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_ra_flare_private",
)

ISENWELL_SPLIT_INTAKE = (
    "Morning. A quick administrative one — I think my mobile number is wrong on your system; the "
    "reminder texts have stopped coming. Could somebody check what you hold and I will read you the "
    "right one over the phone?\n\n"
    "While I am on, you could note that my numbers have been up since bedtime — twelve and fourteen "
    "where I sit at six or seven. The ketone strips stay clear; I check, as taught, and I feel well "
    "enough in myself, so it is a note for the file rather than a fuss."
)

# ── contest 8: nasal polyps, private ENT · split via his own ring-back ────────────────────────────────────
pt_irthcote = _caller(
    "pt_irthcote",
    "Gerald Irthcote",
    66,
    "M",
    chart=(
        "Type 2 diabetes on twice-daily insulin; doses managed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Longstanding trouble with a blocked nose and poor sense of smell; referred privately at his own "
        "request.",
        "Repeat medication: biphasic insulin twice daily, ramipril 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is my sugar I am ringing about, and I will give you the round trip.\n\n"
        "I paid to see a nose specialist about the polyps — the blocked nose, no smell to speak of for a "
        "year — and his letter arrived yesterday: a short course of prednisolone tablets to shrink things "
        "before he looks again. I started them with yesterday's supper, as the letter said.\n\n"
        "I am on insulin twice a day, and the diabetes clinic have said it to me at every review, near "
        "enough word for word: steroid tablets started anywhere, and they see me that same day to set the "
        "insulin — the sugar climbs on them. This morning's reading was up a good step on its usual. The "
        "nose can wait forever, frankly. It is the insulin that wants doing today."
    ),
    onset="The nose is as it has been for a year. The steroid tablets started with yesterday's supper; this morning's reading was up.",
    severity=(
        "Nothing to report in myself beyond a reading a good step above its usual and more thirst than "
        "the weather explains."
    ),
    history="The diabetes on insulin, reviewed at your clinic; the nose trouble a year or more, now seen privately.",
    medications=(
        "The two insulins, the ramipril — and the prednisolone the private nose specialist's letter "
        "started yesterday."
    ),
    context="Semi-retired, my own car; I can be with you inside twenty minutes at any hour today.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_nasal_polyps_private_ent",
)

IRTHCOTE_SPLIT_INTAKE = (
    "Hello. Only housekeeping — I have moved to the flats on the high street and I need my address "
    "changed on your records. Same phone number as before.\n\n"
    "If there is a form I will fill it in when I am next passing; no rush on my account. While you are "
    "in there you could add to the notes that this morning's sugar reading was up a good step on its "
    "usual — I am quite well with it, more thirsty than the weather explains, and that is the sum of it."
)

IRTHCOTE_RECALL_TEXT = (
    "Gerald Irthcote again — I rang about my change of address earlier. One more bit of paperwork for "
    "you: the nose specialist I saw privately has written, and his letter starts me on a short course "
    "of prednisolone — steroid tablets — for the polyps, from yesterday's supper, before he looks "
    "again. I thought the surgery should have that on file alongside his letter when it comes."
)

# ── contest 9: Crohn's flare, private gastroenterologist · split via his own ring-back ────────────────────
pt_jarlethwaite = _caller(
    "pt_jarlethwaite",
    "Brian Jarlethwaite",
    72,
    "M",
    chart=(
        "Type 2 diabetes on twice-daily insulin; managed at the practice's diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Crohn's disease, quiet for several years; followed privately at his own arrangement.",
        "Repeat medication: biphasic insulin twice daily, mesalazine.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I want the diabetes clinic today — it is a bit of a tale, but a short one.\n\n"
        "My Crohn's has been grumbling these last two weeks — nothing frightening, just gripes and my "
        "appetite off — and the bowel specialist I keep on privately rang me yesterday after my tests "
        "and started me on prednisolone to quieten it down. Tablets began last night; his letter is "
        "following.\n\n"
        "The half that belongs to you is the insulin. Your clinic's rule, told to me more than once: on "
        "insulin, the day steroid tablets start is the day they review the doses — the sugar climbs on "
        "steroids and mine is already at it, this morning's reading was up handsomely on its usual. In "
        "myself I am fair. The clinic's day ends at five, so it wants to be today."
    ),
    onset="The Crohn's grumbling two weeks; the steroid tablets started last night. This morning's reading was up.",
    severity=(
        "The gripes are mild and my appetite is coming back. The reading this morning was well up on its "
        "usual, and I am dry-mouthed with it."
    ),
    history="The Crohn's for twenty years, quiet lately, seen privately; the diabetes on insulin at your clinic.",
    medications=(
        "The two insulins, the mesalazine — and the prednisolone the private bowel specialist started "
        "last night."
    ),
    context="Retired; I can walk up at any time today, it is only round the corner.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_crohns_private_gastro",
)

JARLETHWAITE_SPLIT_INTAKE = (
    "Hello. A dull one for you — the chemist tells me my mesalazine repeat has run out of issues and "
    "needs re-authorising. Could that be put to whoever does the repeats?\n\n"
    "I have plenty in hand; the end of the week is soon enough. While I am on: this morning's sugar "
    "reading was up handsomely on its usual. I am fair in myself, so file it under mentioned rather "
    "than complained of — but it ought to be in the notes."
)

JARLETHWAITE_RECALL_TEXT = (
    "Brian Jarlethwaite — I rang this morning about my mesalazine repeat and I ought to have said at "
    "the time: the bowel specialist I see privately telephoned after my tests and has started me on "
    "prednisolone — a steroid, he said — from last night, to quieten the Crohn's grumbling down. His "
    "letter is following. Could it be noted on my record so nothing crosses wires with the repeat?"
)

# ── contest 10: eczema flare, private skin clinic · split via neighbour carrier ──────────────────────────
pt_jordholm = _caller(
    "pt_jordholm",
    "Sheila Jordholm",
    69,
    "F",
    chart=(
        "Type 2 diabetes on twice-daily insulin; doses managed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Chronic eczema, usually managed with emollients; bad winters.",
        "Repeat medication: biphasic insulin twice daily, emollient as required, levothyroxine 50 "
        "micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is my diabetes I am ringing about, though the skin is where it starts.\n\n"
        "My eczema has had its worst flare in years — arms and legs both, cracked and weeping in places — "
        "and the skin clinic I went to privately on Friday started me on prednisolone tablets, a short "
        "course, on top of the creams. The skin is already calmer, I am glad to say.\n\n"
        "But I am on insulin morning and night, and your diabetes clinic have always said it straight: "
        "steroid tablets, whoever starts them, mean the insulin is looked at the same day — the sugar "
        "climbs. Mine has been higher each morning since the weekend and I am up in the night for water. "
        "In myself I am well. My neighbour Malcolm can drop me at the surgery any time today."
    ),
    onset="The skin flared through last week; the steroid tablets started Friday. The morning readings have climbed since the weekend.",
    severity=(
        "The skin is settling under the creams and the tablets. The readings are the concern — higher "
        "each morning since the weekend, and the night thirst with them."
    ),
    history="The eczema all my life, the thyroid on its little tablet, and the diabetes on insulin at your clinic.",
    medications=(
        "The two insulins, the thyroid tablet, the creams — and the prednisolone the private skin clinic "
        "started on Friday."
    ),
    context="Retired; my neighbour Malcolm Irbydale drives me about and is in and out all day today.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_eczema_private_skin",
)

JORDHOLM_SPLIT_INTAKE = (
    "Hello. Would you humour an old query — my thyroid tablet, the levothyroxine. The chemist gave me a "
    "different maker's box this month and I wanted to check that is nothing to mind.\n\n"
    "And while you have my file open, when is my thyroid blood test next due? No hurry at all. One more "
    "for the notes: my morning sugar readings have been higher than their usual since the weekend — up "
    "in the night for water is the worst of it, and otherwise I am well, so a line on the file will do."
)

# ── contest 11: hogweed blisters, out-of-hours doctor · split via his own ring-back ───────────────────────
pt_judbrook = _caller(
    "pt_judbrook",
    "Raymond Judbrook",
    77,
    "M",
    chart=(
        "Type 2 diabetes on twice-daily insulin; managed at the practice's diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Keen allotment holder; previous minor skin reactions to plants.",
        "Repeat medication: biphasic insulin twice daily, finasteride.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I had best give you the tale whole, daft as it starts.\n\n"
        "I was strimming the far bank of the allotment on Sunday and got a forearm full of giant hogweed "
        "sap. By evening the arm had come up in blisters — angry ones — and the out-of-hours doctor took "
        "one look and started me on prednisolone tablets to calm the reaction down. Dressings on, arm on "
        "the mend, that side is handled.\n\n"
        "The side that is not: I am on insulin twice a day, and your diabetes clinic have always said "
        "that if steroid tablets ever start, they see me the same day to set the insulin — the sugar "
        "climbs on them. Mine is climbing: yesterday's readings and this morning's were all up on their "
        "usual. I am otherwise my ordinary self, and I can come in whenever today, the clinic finishing "
        "at five as I understand it."
    ),
    onset="The hogweed on Sunday; the steroid tablets from that evening. The readings have been up since yesterday.",
    severity=(
        "The arm is dressed and easing. The readings are up on their usual, yesterday and today both, "
        "and I am drinking like a fish."
    ),
    history="The diabetes on insulin, watched at your clinic. The allotment gives me a scrape most years but never like this.",
    medications=(
        "The two insulins, the prostate tablet — and the prednisolone the out-of-hours doctor started "
        "Sunday evening."
    ),
    context="Retired; the allotment can rot for a day. Any hour today suits, my neighbour will run me down.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_hogweed_ooh",
)

JUDBROOK_SPLIT_INTAKE = (
    "Hello. Just after a repeat — the finasteride, my prostate tablet. The box is down to its last "
    "strip.\n\n"
    "Any time this week does; the chemist knows me and will text when it is in. My wife says to mention "
    "while I am on that my sugar readings have been up on their usual, yesterday and this morning both. "
    "I am my ordinary self with it — drinking like a fish, mind — so it is one for the notes, not for a "
    "fuss."
)

JUDBROOK_RECALL_TEXT = (
    "Raymond Judbrook here — I rang about my prostate tablet earlier. One for the record while I think "
    "of it: I got giant hogweed sap on my arm strimming the allotment on Sunday and it came up in "
    "blisters, and the out-of-hours doctor started me on steroid tablets — prednisolone — that evening "
    "to calm the reaction. The arm is dressed and on the mend. I only want the tablets written up on "
    "my file."
)

# ── contest 12: asthma flare (second voice), out-of-hours weekend doctor · split via ring-back ────────────
pt_jexwell = _caller(
    "pt_jexwell",
    "Josephine Jexwell",
    64,
    "F",
    chart=(
        "Type 2 diabetes on twice-daily insulin; doses set at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Asthma since childhood, mild, on a preventer inhaler.",
        "Repeat medication: biphasic insulin twice daily, preventer and reliever inhalers.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I need the diabetes clinic today. Let me not get ahead of myself.\n\n"
        "I minded my daughter's cat over the weekend and my asthma took against it — wheezy at night, "
        "coughing by morning — so I went along to the out-of-hours doctor on Sunday and she started me "
        "on prednisolone, steroid tablets, five days. Away from the cat I am breathing easily again; the "
        "inhalers are doing their job.\n\n"
        "But the insulin is the thing. Your clinic have told me every year at review: steroid tablets "
        "started anywhere mean the insulin is looked at that same day, because the sugar climbs on them. "
        "Mine has climbed — the readings since Sunday night are well above their usual and I am parched "
        "with it. In myself I am right as rain. Any appointment today I will take, morning or afternoon."
    ),
    onset="The wheeze over the weekend at my daughter's; the steroid tablets started Sunday. Readings up since Sunday night.",
    severity=(
        "Breathing is back to its usual with the inhalers. The readings are well up on their usual since "
        "Sunday night, and the thirst goes with them."
    ),
    history="The asthma all my life, mild; the diabetes on insulin these last eight years, reviewed at your clinic.",
    medications=(
        "The two insulins, my inhalers — and the prednisolone the out-of-hours doctor started on Sunday."
    ),
    context="I keep the books for my son's firm from home; I can be at the surgery at an hour's notice today.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_asthma_flare_weekend",
)

JEXWELL_SPLIT_INTAKE = (
    "Hello. A checking-up call, nothing to book — the physiotherapy people wrote to me about my "
    "shoulder exercises and said the surgery would be copied in. Could you see whether their letter has "
    "reached my file? I am to arrange a follow-up next month sometime, so it can all wait.\n\n"
    "While you are in my file you might note that my sugar readings have been well up on their usual "
    "since Sunday night. I am right as rain in myself, just parched, so a line in the notes will cover "
    "it."
)

JEXWELL_RECALL_TEXT = (
    "It is Josephine Jexwell — I rang earlier about my physiotherapy letter. For completeness on my "
    "file: I "
    "went along to the out-of-hours doctor on Sunday with my asthma taking against my daughter's cat, "
    "and she started me on prednisolone — steroid tablets — five days' worth. Away from the cat the "
    "breathing is easy again. I only wanted the prescription on my record here, since it came from "
    "their service and not yours."
)

# ── contest 13: COPD flare (second voice), overnight visiting doctor · split via kin carrier (daughter) ──
pt_jevcote = _caller(
    "pt_jevcote",
    "Wilfred Jevcote",
    81,
    "M",
    chart=(
        "Type 2 diabetes on once-daily insulin plus tablets; insulin managed at the practice's diabetes "
        "and endocrine clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "COPD, moderate; on inhalers, flare-ups most winters.",
        "Repeat medication: long-acting insulin in the morning, metformin, combination inhaler, "
        "salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is Wilfred Jevcote. My daughter said to ring you first thing and say it all, so here "
        "it is.\n\n"
        "My chest trouble flared in the night on Sunday — coughing fit to wake the street — and the "
        "visiting doctor from the night service came out and started me on steroid tablets, "
        "prednisolone, a week's worth. The cough has eased since, I am not ringing about the cough.\n\n"
        "I am ringing because of the insulin. The diabetes clinic told me and my daughter both, last "
        "time I had steroid tablets: the day they start, the clinic sees me and sets the insulin, same "
        "day, on account of the sugar climbing. It is climbing now — this morning's number was the "
        "highest I have had all year. I feel much my usual self otherwise. Pauline can bring me in at "
        "any hour you name today."
    ),
    onset="The chest flared Sunday night; the visiting doctor started the steroid tablets there and then. This morning's reading was the year's highest.",
    severity=(
        "The cough is easing and I am pottering about as usual. The reading this morning was the "
        "highest all year, and I am thirsty with it."
    ),
    history="The chest trouble for donkey's years, and the diabetes with the morning insulin, both under your clinics.",
    medications=(
        "The morning insulin, the metformin, my two inhalers — and the prednisolone the night doctor "
        "started on Sunday."
    ),
    context="My daughter Pauline is next door and drives; any hour today suits us both.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_copd_flare_night_doctor",
)

JEVCOTE_SPLIT_INTAKE = (
    "Hello, Wilfred Jevcote. Nothing alarming — my daughter has bought me one of those pill organiser "
    "boxes and we cannot make out whether the metformin is once or twice a day now, the label has worn. "
    "Could somebody check my repeat and tell me which it is?\n\n"
    "And while you are in my notes: this morning's sugar number was the highest I have had all year. I "
    "feel much my usual self, so I am not asking for anything — my daughter said it ought to be on the "
    "record, and she is generally right. Thank you kindly."
)

# ── contest 14: colitis flare, private bowel specialist · split via neighbour carrier ─────────────────────
pt_jesridge = _caller(
    "pt_jesridge",
    "Doreen Jesridge",
    75,
    "F",
    chart=(
        "Type 2 diabetes on twice-daily insulin; doses managed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Ulcerative colitis, quiet for a long stretch; follow-up privately at her own arrangement.",
        "Repeat medication: biphasic insulin twice daily, mesalazine granules.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I want to be seen at the diabetes clinic today, and I will say exactly why.\n\n"
        "My colitis has woken up after years of being good — nothing dreadful, just more trips to the "
        "bathroom and a dragging tiredness — and the bowel specialist I see privately started me on "
        "prednisolone after my telephone review with him yesterday. First tablets last night; the chemist "
        "had them ready by teatime.\n\n"
        "The part for you is my insulin. The diabetes clinic have said it at every review since I "
        "started injections: steroid tablets, started by anyone, mean the clinic looks at the insulin "
        "the very same day — the sugar climbs on them. My readings this morning were up a long way on "
        "their usual. In myself I am tired but fine. My neighbour Brenda can walk up with me whenever "
        "today; I gather the clinic's last appointment is five."
    ),
    onset="The colitis stirring these two weeks; the steroid tablets from last night. This morning's readings were up a long way.",
    severity=(
        "The bowel side is a nuisance, not a fright. The readings are the matter — up a long way this "
        "morning, and the thirst with them."
    ),
    history="The colitis for thirty years, quiet until now, seen privately; the diabetes on insulin at your clinic.",
    medications=(
        "The two insulins, the mesalazine granules — and the prednisolone the private bowel specialist "
        "started last night."
    ),
    context="Retired; my neighbour Brenda Jervale walks up with me most days and is about all day today.",
    gold=board_gold(DIABETES_ENDOCRINE),
    source="authored:insulin_steroids_colitis_private",
)

JESRIDGE_SPLIT_INTAKE = (
    "Hello. Just a little thing — my mesalazine granules, the bowel ones. The chemist says the repeat "
    "wants re-authorising before they can fill it again.\n\n"
    "There is no rush; I have a fortnight's worth in the cupboard. You could put in the notes as well "
    "that my readings this morning were up a long way on their usual — I am tired but quite well in "
    "myself, so I shall leave it as a note and no more. Thank you."
)

# ═══ the evidence carriers (dual-purpose callers with their own routine matters) ══════════════════════════

# ── kin carriers: four family members who share a claimant's surname (kin_of licenses each) ──────────────
pt_idenholm_b = _caller(
    "pt_idenholm_b",
    "Ronald Idenholm",
    73,
    "M",
    chart=(
        "Osteoarthritis of the knees, managed with topical treatment.",
        "Repeat medication: topical anti-inflammatory gel as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Only my knee gel — the rubbing-in one. The tube is nearly out and the chemist says the "
        "repeat needs a fresh authorisation.\n\n"
        "No hurry whatsoever; whenever the repeats are next done."
    ),
    onset="Nothing new; the knees are their usual selves.",
    severity="No complaint in myself at all — it is a repeat script, nothing more.",
    history="The knees, worn with age; nothing else worth the ink.",
    medications="Just the gel for the knees.",
    context="Retired; I drive my wife about, so I am past the surgery most days.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_idenholm_husband",
)

IDENHOLM_B_SPLIT_INTAKE = (
    "Morning. Only my knee gel — the rubbing-in one. The tube is nearly out and the chemist says the "
    "repeat needs a fresh authorisation. No hurry whatsoever.\n\n"
    "Oh — and one bit of housekeeping for my wife's file while I am on. Marjorie Idenholm, same "
    "address. The joint specialist she saw privately has written — it is polymyalgia, she says — and "
    "has started her on prednisolone, the steroid tablets, from this morning. I said I would ring so "
    "it goes on her record before the letter catches up."
)

pt_ilberden_b = _caller(
    "pt_ilberden_b",
    "Keith Ilberden",
    52,
    "M",
    chart=(
        "Hypertension, well controlled.",
        "Repeat medication: lisinopril 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Quick one — my blood pressure tablets, the lisinopril. I am down to four days' worth and "
        "the repeat seems to have lapsed.\n\n"
        "Could it be reissued this week? I will collect from the usual chemist."
    ),
    onset="Nothing new; the pressure has been steady for years.",
    severity="Perfectly well. It is a paperwork call.",
    history="The blood pressure, five years or so, one tablet a day.",
    medications="The lisinopril, one in the morning.",
    context="I work shifts but I am off today, running errands for my mother.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_ilberden_son",
)

ILBERDEN_B_SPLIT_INTAKE = (
    "Hello. Quick one for me — my blood pressure tablets, the lisinopril; the repeat seems to have "
    "lapsed and I am down to four days' worth.\n\n"
    "And a note for my mother's file while I am on — Edith Ilberden. The out-of-hours doctor came out "
    "to her at the weekend for her chest flare-up and started her on prednisolone, the steroid "
    "tablets, a week of it. The cough is on the mend, so nothing wanted there — she only asked me to "
    "make sure the new tablets were written down with her notes, since the visit was not one of yours."
)

pt_iselgarth_b = _caller(
    "pt_iselgarth_b",
    "Joan Iselgarth",
    72,
    "F",
    chart=(
        "Raised cholesterol on treatment; annual bloods.",
        "Repeat medication: simvastatin 20 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I had my cholesterol blood test last week and I was told to ring for the result — could "
        "somebody read it to me, or have the doctor ring me back when convenient?\n\n"
        "No urgency at all; whenever suits the desk."
    ),
    onset="Nothing new; it is the yearly cholesterol check.",
    severity="Quite well, thank you. Just after the number.",
    history="The cholesterol on a tablet for ten years; nothing else.",
    medications="The simvastatin at night.",
    context="Retired; I drive my husband to his appointments, so I am flexible all day.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_iselgarth_wife",
)

ISELGARTH_B_SPLIT_INTAKE = (
    "Hello. Two things, if I may. First my own — I had my cholesterol blood test last week and was told "
    "to ring for the result; no urgency, whenever someone can read it out.\n\n"
    "Second, a note for my husband's file — Norman Iselgarth. The emergency dentist saw him yesterday "
    "for the sore patches in his mouth flaring up and started him on prednisolone tablets — the "
    "steroid ones — a short course. She wrote it all down for him, so I am ringing to see it gets "
    "onto his record here as well."
)

pt_jevcote_b = _caller(
    "pt_jevcote_b",
    "Pauline Jevcote",
    55,
    "F",
    chart=(
        "Seasonal rhinitis; otherwise well.",
        "Repeat medication: antihistamine in season.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could I have my antihistamines put back on repeat? The sneezing season is starting early "
        "for me and last year's authorisation has run out.\n\n"
        "Whenever the repeats are done is fine — I keep a spare packet."
    ),
    onset="The usual early sneezes; nothing else.",
    severity="Well in myself; it is only the hay fever tablets.",
    history="The hay fever every spring since school.",
    medications="The antihistamine, one a day in season.",
    context="I live next door to my father and do his driving; I am about all day.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_jevcote_daughter",
)

JEVCOTE_B_SPLIT_INTAKE = (
    "Hello. One small thing of mine and one of my father's. Mine: could my antihistamines go back on "
    "repeat? The sneezing season is starting early.\n\n"
    "My father is Wilfred Jevcote. The night doctor came out to him on Sunday for his chest flaring and "
    "started him on steroid tablets, prednisolone, a week's worth — the cough has eased since, I am "
    "glad to say. He will not think to tell you himself, so would you note the new tablets on his file "
    "with the visit?"
)

# ── neighbour carriers: three unrelated callers with their own routine matters ────────────────────────────
pt_ickenby = _caller(
    "pt_ickenby",
    "Doris Ickenby",
    66,
    "F",
    chart=(
        "Dry eyes; uses lubricating drops.",
        "Repeat medication: lubricating eye drops as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My eye drops, please — the lubricating ones. The repeat has run its course and the "
        "chemist wants a fresh script.\n\n"
        "There is no rush; I have half a bottle yet."
    ),
    onset="Nothing new; the eyes are their dry old selves.",
    severity="Perfectly well. A repeat script is all it is.",
    history="The dry eyes for years; drops keep them comfortable.",
    medications="Only the eye drops.",
    context="Retired; I fetch prescriptions for my neighbour Carol as well as my own.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_ickenby_neighbour",
)

ICKENBY_SPLIT_INTAKE = (
    "Hello. My eye drops, please — the lubricating ones; the repeat has run its course. No rush, I have "
    "half a bottle yet.\n\n"
    "And might I pass something on for a neighbour's file? I fetch prescriptions for Carol Isenwell, "
    "and yesterday I collected prednisolone for her — steroid tablets — which the rheumatology clinic "
    "she pays for started for her wrists flaring. She said she would ring you herself about her phone "
    "number, but I promised to mention the new tablets so they were not missed off her record."
)

pt_irbydale = _caller(
    "pt_irbydale",
    "Malcolm Irbydale",
    71,
    "M",
    chart=(
        "Gastro-oesophageal reflux, stable on treatment.",
        "Repeat medication: lansoprazole 15 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My indigestion tablets — the lansoprazole. Could the repeat be reissued? The chemist "
        "says it has expired.\n\n"
        "Any day this week does me; I am not down to the wire."
    ),
    onset="Nothing new; the indigestion behaves while I take the tablet.",
    severity="Quite well. It is only the repeat.",
    history="The reflux for a decade, settled on the tablet.",
    medications="The lansoprazole each morning.",
    context="Retired; I run my neighbour Sheila about in the car, so I am out and about today.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_irbydale_neighbour",
)

IRBYDALE_SPLIT_INTAKE = (
    "Hello. My indigestion tablets — the lansoprazole; the chemist says the repeat has expired. Any day "
    "this week does me.\n\n"
    "While I am on: I drive for my neighbour, Sheila Jordholm, and on Friday I took her to a private "
    "skin clinic for that eczema of hers flaring — they have started her on prednisolone, steroid "
    "tablets, on top of the creams, and the skin is already calmer. She asked me to make sure the new "
    "tablets were noted on her file here, the clinic being a private one."
)

pt_jervale = _caller(
    "pt_jervale",
    "Brenda Jervale",
    63,
    "F",
    chart=(
        "Hypertension, well controlled; six-monthly checks.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I need to move my blood pressure check — the routine one I have booked for the end of "
        "the month. My sister is visiting that week.\n\n"
        "Any other week suits; there is nothing the matter with me."
    ),
    onset="Nothing new; the pressure has been good all year.",
    severity="Perfectly well — it is diary-shuffling, no more.",
    history="The blood pressure on one tablet, checked twice a year.",
    medications="The amlodipine each morning.",
    context="I walk up with my neighbour Doreen most days; I am free all of today.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_jervale_neighbour",
)

JERVALE_SPLIT_INTAKE = (
    "Hello. I need to move my blood pressure check — the routine one at the end of the month; my sister "
    "is visiting that week. Any other week suits.\n\n"
    "And one thing I promised to pass on for my neighbour, Doreen Jesridge. The bowel specialist she "
    "sees privately had a telephone review with her yesterday and started her on prednisolone — the "
    "steroid tablets — for the colitis stirring; I collected them with her at teatime. She will be "
    "ringing herself about her repeat, but she wanted the new tablets on her file in the meantime so "
    "nothing gets crossed."
)

# ═══ the decoys: sound urgent, correctly left un-bumped (§6) ══════════════════════════════════════════════

# Decoy 1: steroids-and-sugar alarm — but the steroid is a CREAM, defused in her own call on both twins.
pt_jarrowden = _caller(
    "pt_jarrowden",
    "Nora Jarrowden",
    66,
    "F",
    chart=(
        "Type 2 diabetes on twice-daily insulin; managed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Hand eczema, intermittent.",
        "Repeat medication: biphasic insulin twice daily, emollient as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I got myself in a state this morning and I want somebody to tell me I am right to calm "
        "down.\n\n"
        "The skin clinic I went to privately gave me a steroid for the eczema on my hands — and I am on "
        "insulin, and everyone knows steroids and sugar do not mix, so I nearly rang you in a panic. But "
        "it is a cream, hydrocortisone cream, only on the hands — and the skin doctor said in the room "
        "that a cream is not like tablets, it does not get into the blood to speak of, and my readings "
        "would not notice it. This morning's reading was its ordinary self, right where it always is.\n\n"
        "So no alarm — but my hands have been cracking for months and I would like an ordinary "
        "appointment about them with my own doctor, whenever there is one going."
    ),
    onset="The hands have cracked and itched for months; the cream started at the weekend.",
    severity="The hands sting when I wash up, no worse. My sugar reading this morning was its ordinary self.",
    history="The diabetes on insulin at your clinic, and the hand eczema on and off for years.",
    medications="The two insulins, the moisturiser — and now the hydrocortisone cream for the hands.",
    context="Retired; any week suits for an ordinary appointment. I only wanted the panic put to bed.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_decoy_topical_cream",
)

# Decoy 2: the pattern in the past tense — course finished, readings settled, defused in his own call.
pt_iffley = _caller(
    "pt_iffley",
    "Harold Iffley",
    73,
    "M",
    chart=(
        "Type 2 diabetes on twice-daily insulin; managed at the practice's diabetes and endocrine "
        "clinic.",
        "Diabetes clinic advice on file: an insulin review the same day any course of steroid "
        "tablets is started.",
        "Osteoarthritis of the hip, awaiting routine physiotherapy.",
        "Repeat medication: biphasic insulin twice daily, paracetamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Mostly a repeat call, with a bit of history so nobody's hair stands on end.\n\n"
        "A fortnight back I had a week of prednisolone tablets for my hip playing up terribly. Being on "
        "insulin, I did exactly as the diabetes clinic drill us — rang the day they started, was seen "
        "the same day, doses turned up while the course ran. The course finished ten days ago, the "
        "clinic stepped my insulin back down after, and my readings have been sat in their usual range "
        "for a week solid. All squared away.\n\n"
        "So today is only this: my needle clips and lancets have come off my repeat somehow, and the "
        "chemist wants them re-authorised. No hurry — I have supplies for a fortnight."
    ),
    onset="Nothing current. The steroid course finished ten days ago and the readings settled a week back.",
    severity="Perfectly well. The readings have been in their usual range for a week solid.",
    history="The diabetes on insulin at your clinic, and the hip waiting on physiotherapy.",
    medications="The two insulins and paracetamol for the hip. The steroid tablets are finished and gone.",
    context="Retired; the repeat can go through whenever the desk gets to it.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_decoy_course_finished",
)

# Decoy 3: a frightening meter number — defused by the recheck; the defusal ITSELF splits to the daughter
# in the split twin (§6: aggregation must be able to cancel urgency, not only create it).
pt_julcote = _caller(
    "pt_julcote",
    "Vera Julcote",
    81,
    "F",
    chart=(
        "Type 2 diabetes on tablets only; no insulin. Managed at the practice's diabetes and endocrine "
        "clinic.",
        "Lives alone; daughter nearby assists with shopping and equipment.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, dear. I gave myself a fright this morning and I want it written down properly.\n\n"
        "My daughter bought me a new sugar meter, and first thing it read fourteen — fourteen! — and I "
        "came over quite washed out just looking at it. But here is the rest: Karen came round, found "
        "the wrong pot of strips in the new machine, and on my old meter, same finger, I was six. Six is "
        "me all over. I had a cup of tea and I am right as rain — it was the number that frightened me, "
        "not my body.\n\n"
        "So what I actually want is my ordinary yearly blood test sorting — the letter said to ring and "
        "arrange it sometime. Whenever there is a routine appointment going, I am not fussed."
    ),
    onset="The fright was this morning; the recheck on the old meter was six, my usual.",
    severity="Right as rain in myself. It was a wrong-strips reading; the proper meter says six.",
    history="The diabetes on tablets only, no injections, watched at your clinic for years.",
    medications="The metformin, morning and evening. Nothing else.",
    context="My daughter Karen is in and out; a routine appointment any week suits me.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_decoy_meter_misread",
)

JULCOTE_SPLIT_INTAKE = (
    "Hello, dear. I gave myself a fright this morning and I want it written down properly.\n\n"
    "My daughter bought me a new sugar meter, and first thing it read fourteen — fourteen! — and I came "
    "over quite washed out just looking at it. I have had my cup of tea and I am sitting quiet.\n\n"
    "And while I am on, my ordinary yearly blood test wants sorting — the letter said to ring and "
    "arrange it sometime. My daughter said she would telephone you as well, so between us you will have "
    "the whole story."
)

pt_julcote_b = _caller(
    "pt_julcote_b",
    "Karen Julcote",
    49,
    "F",
    chart=(
        "Migraine, infrequent; managed with as-required treatment.",
        "Repeat medication: sumatriptan as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could my sumatriptan go back on repeat? I have two tablets left of the ones I keep for "
        "when a migraine lands, and the authorisation has run out.\n\n"
        "No urgency — I have not needed one in months."
    ),
    onset="Nothing current; it is a standby supply I am topping up.",
    severity="Perfectly well today. The tablets are for the odd migraine when it comes.",
    history="The migraines a few times a year since my thirties.",
    medications="Only the sumatriptan, as and when.",
    context="I work in town but I am at my mother's this morning; ring back on my mobile if needed.",
    gold=_routine_gold(),
    source="authored:insulin_steroids_carrier_julcote_daughter",
)

JULCOTE_B_SPLIT_INTAKE = (
    "Hello. Could my sumatriptan go back on repeat? Two tablets left of my standby supply; no urgency "
    "at all.\n\n"
    "More to the point — my mother, Vera Julcote, will have rung you about her meter reading fourteen "
    "this morning. Please put the sequel with it: I went round, and the new meter had the wrong pot of "
    "strips in it entirely. On her old meter, same finger, she was six — which is her usual to the "
    "decimal. She is on the metformin only, no insulin, and she is absolutely her ordinary self — I "
    "watched her demolish two biscuits. All she genuinely needs is her routine yearly blood test booked "
    "sometime. I did not want the fourteen sitting on her file unanswered."
)

# ═══ the fourteen holders (they never call; this is what they say if a desk rings THEM) ═══════════════════

pt_idengill = _caller(
    "pt_idengill",
    "Albert Idengill",
    78,
    "M",
    chart=(
        "Type 2 diabetes on insulin, stable; annual review due.",
        "Repeat medication: biphasic insulin twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I have my yearly diabetes review this afternoon. My daughter has taken the afternoon off work "
        "to drive me in — it took some arranging, so the time suits us very well."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. The numbers have been steady all year.",
    history="The diabetes on insulin for a decade, reviewed yearly at the clinic.",
    medications="The two insulin injections, off the clinic's plan.",
    context="My daughter took the afternoon off specially to bring me.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_review_idengill",
)

pt_iverfold = _caller(
    "pt_iverfold",
    "Betty Iverfold",
    74,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual dose review with bloods due.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my thyroid review this afternoon — the yearly one where they check the dose against the "
        "bloods. My neighbour has kept her afternoon free to run me down and wait."
    ),
    onset="Nothing new; the yearly dose check.",
    severity="Quite well. The tablet has suited me for years.",
    history="The thyroid on its tablet for fifteen years, reviewed yearly.",
    medications="The levothyroxine each morning.",
    context="My neighbour has kept the afternoon free for the lift.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_thyroid_review_iverfold",
)

pt_ilberlund = _caller(
    "pt_ilberlund",
    "Cyril Ilberlund",
    80,
    "M",
    chart=(
        "Type 2 diabetes on insulin; annual review with foot check due.",
        "Repeat medication: biphasic insulin twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes review and foot check is this afternoon. The taxi firm is paid for the round trip "
        "already — they give me the hospital rate if I book a day ahead, which I did."
    ),
    onset="Nothing new; the yearly look-over.",
    severity="Well in myself; the feet get their yearly once-over is all.",
    history="The diabetes on insulin, steady, reviewed yearly with the foot check.",
    medications="The two insulins.",
    context="The taxi is booked both ways at the pre-booked rate.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_footcheck_ilberlund",
)

pt_inglecliffe = _caller(
    "pt_inglecliffe",
    "Mavis Inglecliffe",
    69,
    "F",
    chart=(
        "Type 2 diabetes newly moved to insulin; pen-technique review booked.",
        "Repeat medication: long-acting insulin at night, metformin.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in this afternoon for them to watch me do my insulin pen — I am new to the injections and "
        "they wanted to see my technique. My son has taken his half-day to sit in with me and learn it "
        "too."
    ),
    onset="Nothing new; it is the teaching appointment.",
    severity="I am well. I just want to be doing the pen right.",
    history="The diabetes for years on tablets, the insulin just started.",
    medications="The night-time insulin and the metformin.",
    context="My son arranged his half-day around the time.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_pen_review_inglecliffe",
)

pt_ickenholm = _caller(
    "pt_ickenholm",
    "Edward Ickenholm",
    72,
    "M",
    chart=(
        "Type 2 diabetes on insulin, stable; annual review due.",
        "Repeat medication: biphasic insulin twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My annual insulin review is this afternoon. My wife has moved her bowls match so we could "
        "come together — she likes to hear what the clinic says first-hand."
    ),
    onset="Nothing new; the yearly review.",
    severity="Well, thank you. Steady as she goes all year.",
    history="The diabetes on insulin for eight years, reviewed yearly.",
    medications="The two insulins.",
    context="My wife rearranged her bowls match for the time.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_review_ickenholm",
)

pt_iselden = _caller(
    "pt_iselden",
    "Gwen Iselden",
    77,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual dose review due.",
        "Repeat medication: levothyroxine 75 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my thyroid check this afternoon, the yearly one. It falls on my carer's visiting day, "
        "which is the only way I manage appointments — she comes with me."
    ),
    onset="Nothing new; the yearly check.",
    severity="Quite well on the tablet.",
    history="The thyroid for twenty years on the same little tablet.",
    medications="The levothyroxine.",
    context="My carer's visiting day — she accompanies me to appointments.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_thyroid_review_iselden",
)

pt_isenroyd = _caller(
    "pt_isenroyd",
    "Leonard Isenroyd",
    66,
    "M",
    chart=(
        "Type 2 diabetes on insulin; medication review due.",
        "Repeat medication: biphasic insulin twice daily, atorvastatin.",
        "No known drug allergies.",
    ),
    intake=(
        "I have the diabetes medication review this afternoon — it sits exactly between my shifts, "
        "which is why I took it when it was offered. I start nights again tomorrow."
    ),
    onset="Nothing new; the routine medication review.",
    severity="Fit and well; it is the routine going-over.",
    history="The diabetes on insulin, five years, working nights around it.",
    medications="The two insulins and the statin.",
    context="The time sits exactly between my shifts; nights start again tomorrow.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_medication_review_isenroyd",
)

pt_irthgarth = _caller(
    "pt_irthgarth",
    "Hilda Irthgarth",
    83,
    "F",
    chart=(
        "Type 2 diabetes on insulin; annual review due.",
        "Repeat medication: long-acting insulin in the morning, metformin.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly diabetes appointment is this afternoon. My granddaughter has the afternoon off and "
        "is taking me in — we have planned tea out after, it is quite the occasion."
    ),
    onset="Nothing new; the yearly appointment.",
    severity="Very well for my age, the nurse tells me.",
    history="The diabetes a long while, the morning insulin these last few years.",
    medications="The morning insulin and the metformin.",
    context="My granddaughter's afternoon off, and tea out after.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_review_irthgarth",
)

pt_jarlemead = _caller(
    "pt_jarlemead",
    "Victor Jarlemead",
    70,
    "M",
    chart=(
        "Type 2 diabetes on insulin, stable; annual review due.",
        "Repeat medication: biphasic insulin twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "The diabetes clinic are seeing me this afternoon for the yearly going-over. I have waited a "
        "good two months for it — I was on the list when the cancellation came up, and I took it on the "
        "spot."
    ),
    onset="Nothing new; the yearly review, long awaited.",
    severity="Well in myself; the review is routine.",
    history="The diabetes on insulin for twelve years, reviewed yearly.",
    medications="The two insulins.",
    context="Two months on the list before this time came up.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_review_jarlemead",
)

pt_jordcliffe = _caller(
    "pt_jordcliffe",
    "Winifred Jordcliffe",
    75,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual dose review due.",
        "Repeat medication: levothyroxine 125 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my thyroid dose review this afternoon. My friend from church takes me to my "
        "appointments and she has kept the whole afternoon for it."
    ),
    onset="Nothing new; the yearly dose review.",
    severity="Quite well; the dose has needed no change in years.",
    history="The thyroid on the tablet since my fifties.",
    medications="The levothyroxine each morning.",
    context="My friend from church has kept her afternoon for the lift.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_thyroid_review_jordcliffe",
)

pt_judfold = _caller(
    "pt_judfold",
    "Ernest Judfold",
    79,
    "M",
    chart=(
        "Type 2 diabetes on insulin; annual review with foot check due.",
        "Repeat medication: biphasic insulin twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes review and foot check is this afternoon. I have been on the waiting list for it "
        "since before the turn of the year, so I am glad of the date."
    ),
    onset="Nothing new; the yearly review and foot check.",
    severity="Well enough; the feet behave themselves.",
    history="The diabetes on insulin for fifteen years.",
    medications="The two insulins.",
    context="On the waiting list since before the turn of the year.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_footcheck_judfold",
)

pt_jexden = _caller(
    "pt_jexden",
    "Phyllis Jexden",
    71,
    "F",
    chart=(
        "Type 2 diabetes on insulin; review booked ahead of a long coach holiday.",
        "Repeat medication: biphasic insulin twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in this afternoon to have my insulin gone over before my coach holiday — the clinic likes "
        "to check the doses and the travel arrangements before I am away a month. The holiday is booked "
        "and paid."
    ),
    onset="Nothing new; the pre-holiday going-over.",
    severity="Very well; it is planning, not illness.",
    history="The diabetes on insulin for nine years; I travel every spring.",
    medications="The two insulins.",
    context="The coach holiday is booked and paid; the review was fitted ahead of it.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_travel_review_jexden",
)

pt_jevlund = _caller(
    "pt_jevlund",
    "Sidney Jevlund",
    76,
    "M",
    chart=(
        "Type 2 diabetes on insulin, stable; annual review due.",
        "Repeat medication: biphasic insulin twice daily, ramipril.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly diabetes review is this afternoon. My son is driving over from two towns away to "
        "take me — he set off after breakfast to be sure of it."
    ),
    onset="Nothing new; the yearly review.",
    severity="Well, thank you. Routine through and through.",
    history="The diabetes on insulin for eleven years.",
    medications="The two insulins and the blood pressure tablet.",
    context="My son is driving over from two towns away specially.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_annual_review_jevlund",
)

pt_jesgarth = _caller(
    "pt_jesgarth",
    "Agnes Jesgarth",
    82,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual dose review due.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my thyroid review this afternoon. The warden at my sheltered flats has put me on the "
        "minibus run for it — the bus goes when it goes, so the time matters to me."
    ),
    onset="Nothing new; the yearly review.",
    severity="Quite well on the tablet, as ever.",
    history="The thyroid on the tablet for thirty years.",
    medications="The levothyroxine.",
    context="The sheltered-flats minibus is booked for the time.",
    gold=_holder_gold(),
    source="authored:insulin_steroids_holder_thyroid_review_jesgarth",
)

# ═══ the board skeleton (shared by both twins byte-for-byte) ══════════════════════════════════════════════

_CARDS = (
    # claimants
    pt_idenholm,
    pt_iverbrook,
    pt_ilberden,
    pt_inglemead,
    pt_ickenridge,
    pt_iselgarth,
    pt_isenwell,
    pt_irthcote,
    pt_jarlethwaite,
    pt_jordholm,
    pt_judbrook,
    pt_jexwell,
    pt_jevcote,
    pt_jesridge,
    # carriers
    pt_idenholm_b,
    pt_ilberden_b,
    pt_iselgarth_b,
    pt_jevcote_b,
    pt_ickenby,
    pt_irbydale,
    pt_jervale,
    pt_julcote_b,
    # decoys
    pt_jarrowden,
    pt_iffley,
    pt_julcote,
    # holders
    pt_idengill,
    pt_iverfold,
    pt_ilberlund,
    pt_inglecliffe,
    pt_ickenholm,
    pt_iselden,
    pt_isenroyd,
    pt_irthgarth,
    pt_jarlemead,
    pt_jordcliffe,
    pt_judfold,
    pt_jexden,
    pt_jevlund,
    pt_jesgarth,
)

#: The sanctioned same-surname shapes: four kin evidence carriers and the decoy-defusing daughter.
KIN_OF = {
    "pt_idenholm_b": "pt_idenholm",
    "pt_ilberden_b": "pt_ilberden",
    "pt_iselgarth_b": "pt_iselgarth",
    "pt_jevcote_b": "pt_jevcote",
    "pt_julcote_b": "pt_julcote",
}


def _contest(
    claimant: str, holder: str, provider_id: str, slot_hhmm: str, standing: str
) -> BoardContest:
    """One P05 contest: same diary, same deadline (clinic close), same stakes tier, same decisive fact.

    The decisive fact is the word every claimant's calls carry and no chart may: the new `prednisolone`. The uniformity is the mechanism family's — what varies per contest is the fiction (who prescribed it and why), never the arithmetic.
    """
    return BoardContest(
        claimant=claimant,
        holder=holder,
        specialty=DIABETES_ENDOCRINE,
        provider_id=provider_id,
        slot_hhmm=slot_hhmm,
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=standing,
        decisive_fact="prednisolone",
    )


CONTESTS = (
    _contest(
        "pt_idenholm",
        "pt_idengill",
        "dr_ingleford",
        "13:00",
        "Annual diabetes review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_iverbrook",
        "pt_iverfold",
        "dr_ingleford",
        "13:40",
        "Thyroid dose review + bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_ilberden",
        "pt_ilberlund",
        "dr_ingleford",
        "15:00",
        "Annual diabetes review + foot check (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_inglemead",
        "pt_inglecliffe",
        "dr_ingleford",
        "16:20",
        "Insulin pen technique review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_ickenridge",
        "pt_ickenholm",
        "dr_jurby",
        "13:00",
        "Annual diabetes review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_iselgarth",
        "pt_iselden",
        "dr_jurby",
        "13:20",
        "Thyroid dose review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_isenwell",
        "pt_isenroyd",
        "dr_jurby",
        "14:40",
        "Diabetes medication review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_irthcote",
        "pt_irthgarth",
        "dr_jurby",
        "15:20",
        "Annual diabetes review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_jarlethwaite",
        "pt_jarlemead",
        "dr_iselworth",
        "13:20",
        "Annual diabetes review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_jordholm",
        "pt_jordcliffe",
        "dr_iselworth",
        "14:40",
        "Thyroid dose review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_judbrook",
        "pt_judfold",
        "dr_iselworth",
        "15:00",
        "Annual diabetes review + foot check (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_jexwell",
        "pt_jexden",
        "dr_javenholm",
        "13:40",
        "Pre-travel insulin review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_jevcote",
        "pt_jevlund",
        "dr_javenholm",
        "15:20",
        "Annual diabetes review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_jesridge",
        "pt_jesgarth",
        "dr_javenholm",
        "16:40",
        "Thyroid dose review (wait-list backfill into a returned cancellation)",
    ),
)

#: Decoy sets per twin: identical ids (the pair gate's claim); the split twin moves pt_julcote's defusing
#: fact into her daughter's call (§6 — aggregation can cancel urgency, not only create it).
DECOYS_PLAIN = (
    Decoy(patient_id="pt_jarrowden"),
    Decoy(patient_id="pt_iffley"),
    Decoy(patient_id="pt_julcote"),
)
DECOYS_SPLIT = (
    Decoy(patient_id="pt_jarrowden"),
    Decoy(patient_id="pt_iffley"),
    Decoy(patient_id="pt_julcote", defusing_caller_id="pt_julcote_b"),
)

#: Arrival plan, identical across the twins (the split twin adds recall BEATS, which is call structure).
#: The morning stagger is compressed for the size; the voicemail trio lands on three desks.
ARRIVALS = (
    ("pt_idenholm", "A", 0),
    ("pt_iverbrook", "B", 6),
    ("pt_lachaux", "B", 12),
    ("pt_ilberden", "C", 16),
    ("pt_inglemead", "D", 22),
    ("pt_jarrowden", "A", 28),
    ("pt_ickenridge", "A", 34),
    ("pt_idenholm_b", "B", 40),
    ("pt_iselgarth", "C", 46),
    ("pt_dunmore", "C", 52),
    ("pt_isenwell", "D", 56),
    ("pt_iffley", "B", 62),
    ("pt_irthcote", "C", 68),
    ("pt_ickenby", "A", 74),
    ("pt_jarlethwaite", "D", 80),
    ("pt_ilberden_b", "D", 86),
    ("pt_jordholm", "A", 92),
    ("pt_ledwidge", "A", 96),
    ("pt_julcote", "B", 98),
    ("pt_judbrook", "B", 104),
    ("pt_iselgarth_b", "D", 110),
    ("pt_jexwell", "C", 116),
    ("pt_irbydale", "C", 122),
    ("pt_jevcote", "D", 128),
    ("pt_julcote_b", "A", 134),
    ("pt_jesridge", "B", 140),
    ("pt_jevcote_b", "A", 146),
    ("pt_jervale", "D", 152),
    ("pt_arundel", "D", 158),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: One sentence of size cover: why one diary is carrying fourteen returned cancellations.
MEMO_COVER_LINE = (
    "The diabetes and endocrine clinics are covering the neighbouring practice's diabetes lists while it "
    "is closed for the rebuild, so their books are fuller than usual."
)

#: Plain twin: every claimant's whole picture in their own single intake.
PLAIN_EVIDENCE = tuple(
    EvidenceCall(caller_id=contest.claimant, about_claimant=contest.claimant)
    for contest in CONTESTS
)

#: Split twin: piece 1 is the claimant's own routine intake; the prednisolone fact arrives in a ring-back
#: on a different desk (7 contests) or in a carrier's dual-purpose call (7 contests). Every claimant's
#: pieces span >=2 mesh4 desks.
SPLIT_EVIDENCE = (
    # c1: idenholm (A) + husband (B)
    EvidenceCall(caller_id="pt_idenholm", about_claimant="pt_idenholm"),
    EvidenceCall(caller_id="pt_idenholm_b", about_claimant="pt_idenholm"),
    # c2: iverbrook (B) + her recall (D)
    EvidenceCall(caller_id="pt_iverbrook", about_claimant="pt_iverbrook"),
    EvidenceCall(
        caller_id="pt_iverbrook",
        about_claimant="pt_iverbrook",
        kind="recall",
        at_min=95,
        desk="D",
        text=IVERBROOK_RECALL_TEXT,
    ),
    # c3: ilberden (C) + son (D)
    EvidenceCall(caller_id="pt_ilberden", about_claimant="pt_ilberden"),
    EvidenceCall(caller_id="pt_ilberden_b", about_claimant="pt_ilberden"),
    # c4: inglemead (D) + his recall (B)
    EvidenceCall(caller_id="pt_inglemead", about_claimant="pt_inglemead"),
    EvidenceCall(
        caller_id="pt_inglemead",
        about_claimant="pt_inglemead",
        kind="recall",
        at_min=105,
        desk="B",
        text=INGLEMEAD_RECALL_TEXT,
    ),
    # c5: ickenridge (A) + her recall (C)
    EvidenceCall(caller_id="pt_ickenridge", about_claimant="pt_ickenridge"),
    EvidenceCall(
        caller_id="pt_ickenridge",
        about_claimant="pt_ickenridge",
        kind="recall",
        at_min=118,
        desk="C",
        text=ICKENRIDGE_RECALL_TEXT,
    ),
    # c6: iselgarth (C) + wife (D)
    EvidenceCall(caller_id="pt_iselgarth", about_claimant="pt_iselgarth"),
    EvidenceCall(caller_id="pt_iselgarth_b", about_claimant="pt_iselgarth"),
    # c7: isenwell (D) + neighbour (A)
    EvidenceCall(caller_id="pt_isenwell", about_claimant="pt_isenwell"),
    EvidenceCall(caller_id="pt_ickenby", about_claimant="pt_isenwell"),
    # c8: irthcote (C) + his recall (A)
    EvidenceCall(caller_id="pt_irthcote", about_claimant="pt_irthcote"),
    EvidenceCall(
        caller_id="pt_irthcote",
        about_claimant="pt_irthcote",
        kind="recall",
        at_min=132,
        desk="A",
        text=IRTHCOTE_RECALL_TEXT,
    ),
    # c9: jarlethwaite (D) + his recall (B)
    EvidenceCall(caller_id="pt_jarlethwaite", about_claimant="pt_jarlethwaite"),
    EvidenceCall(
        caller_id="pt_jarlethwaite",
        about_claimant="pt_jarlethwaite",
        kind="recall",
        at_min=144,
        desk="B",
        text=JARLETHWAITE_RECALL_TEXT,
    ),
    # c10: jordholm (A) + neighbour (C)
    EvidenceCall(caller_id="pt_jordholm", about_claimant="pt_jordholm"),
    EvidenceCall(caller_id="pt_irbydale", about_claimant="pt_jordholm"),
    # c11: judbrook (B) + his recall (C)
    EvidenceCall(caller_id="pt_judbrook", about_claimant="pt_judbrook"),
    EvidenceCall(
        caller_id="pt_judbrook",
        about_claimant="pt_judbrook",
        kind="recall",
        at_min=148,
        desk="C",
        text=JUDBROOK_RECALL_TEXT,
    ),
    # c12: jexwell (C) + her recall (A)
    EvidenceCall(caller_id="pt_jexwell", about_claimant="pt_jexwell"),
    EvidenceCall(
        caller_id="pt_jexwell",
        about_claimant="pt_jexwell",
        kind="recall",
        at_min=154,
        desk="A",
        text=JEXWELL_RECALL_TEXT,
    ),
    # c13: jevcote (D) + daughter (A)
    EvidenceCall(caller_id="pt_jevcote", about_claimant="pt_jevcote"),
    EvidenceCall(caller_id="pt_jevcote_b", about_claimant="pt_jevcote"),
    # c14: jesridge (B) + neighbour (D)
    EvidenceCall(caller_id="pt_jesridge", about_claimant="pt_jesridge"),
    EvidenceCall(caller_id="pt_jervale", about_claimant="pt_jesridge"),
)

#: The split twin's words: each claimant says only their routine piece 1; the evidence carriers add the
#: FYI half to their own routine matter; the meter-fright decoy loses her defusal to her daughter's call.
SPLIT_INTAKE_OVERRIDES = {
    "pt_idenholm": IDENHOLM_SPLIT_INTAKE,
    "pt_iverbrook": IVERBROOK_SPLIT_INTAKE,
    "pt_ilberden": ILBERDEN_SPLIT_INTAKE,
    "pt_inglemead": INGLEMEAD_SPLIT_INTAKE,
    "pt_ickenridge": ICKENRIDGE_SPLIT_INTAKE,
    "pt_iselgarth": ISELGARTH_SPLIT_INTAKE,
    "pt_isenwell": ISENWELL_SPLIT_INTAKE,
    "pt_irthcote": IRTHCOTE_SPLIT_INTAKE,
    "pt_jarlethwaite": JARLETHWAITE_SPLIT_INTAKE,
    "pt_jordholm": JORDHOLM_SPLIT_INTAKE,
    "pt_judbrook": JUDBROOK_SPLIT_INTAKE,
    "pt_jexwell": JEXWELL_SPLIT_INTAKE,
    "pt_jevcote": JEVCOTE_SPLIT_INTAKE,
    "pt_jesridge": JESRIDGE_SPLIT_INTAKE,
    "pt_idenholm_b": IDENHOLM_B_SPLIT_INTAKE,
    "pt_ilberden_b": ILBERDEN_B_SPLIT_INTAKE,
    "pt_iselgarth_b": ISELGARTH_B_SPLIT_INTAKE,
    "pt_jevcote_b": JEVCOTE_B_SPLIT_INTAKE,
    "pt_ickenby": ICKENBY_SPLIT_INTAKE,
    "pt_irbydale": IRBYDALE_SPLIT_INTAKE,
    "pt_jervale": JERVALE_SPLIT_INTAKE,
    "pt_julcote": JULCOTE_SPLIT_INTAKE,
    "pt_julcote_b": JULCOTE_B_SPLIT_INTAKE,
}

#: The split twin's phone-probe answers: the canonical onset/medications answers
#: restate the assembled case — the prednisolone by name with the readings, or the steroid start in the
#: same breath as the change — so a desk that rings any claimant would be handed the union solo. These
#: sub-threshold rewrites are what each patient would volunteer to one ordinary question: the readings
#: fragment they already mentioned in piece 1, and the new course in passing WITHOUT its decisive name
#: and WITHOUT the maintenance context. Severity/history/context answers carry no decisive fact and stay
#: canonical (the pair gate holds them byte-shared).
SPLIT_FACTS_OVERRIDES = {
    "pt_idenholm": {
        "onset": (
            "Nothing wrong in myself. My reading before lunch was a step up on its usual — that is the "
            "whole of the change."
        ),
        "medications": (
            "The two insulin injections off the clinic's plan, and the metformin. There are some new "
            "tablets from the joint specialist as well — my husband has the letter with the name of "
            "them."
        ),
    },
    "pt_iverbrook": {
        "onset": (
            "The head cold all week, and the wheeze with it, though that is easing. The readings began "
            "climbing this morning; the ketone dip is clear."
        ),
        "medications": (
            "The two insulins and my inhalers — and the out-of-hours doctor left me a course of tablets "
            "for the chest last night; I have not got the box by me for the name."
        ),
    },
    "pt_ilberden": {
        "onset": (
            "One of my chest flare-ups over the weekend — the cough is on the mend. This morning's "
            "sugar number was up on its usual."
        ),
        "medications": (
            "The night-time insulin, the gliclazide, my two inhalers — and the tablets the visiting "
            "doctor left at the weekend for the chest; Keith keeps the boxes straight for me."
        ),
    },
    "pt_inglemead": {
        "onset": (
            "The knee came up two days ago and is being seen to. This morning's reading was up a fair "
            "way on its usual."
        ),
        "medications": (
            "The two insulin injections and the stomach tablet — and something the private joint clinic "
            "gave me for the knee, since I cannot take the usual anti-inflammatories. The chemist would "
            "have the name of it."
        ),
    },
    "pt_ickenridge": {
        "onset": (
            "The hives came up on Saturday night and are fading now. The readings have been above their "
            "usual since yesterday."
        ),
        "medications": (
            "The two insulins, the statin at night — and a short course the out-of-hours doctor gave me "
            "for the hives; I could not tell you the name without the packet."
        ),
    },
    "pt_iselgarth": {
        "onset": (
            "The mouth flared over the weekend and is mending. This morning's reading was up on its "
            "usual."
        ),
        "medications": (
            "The two insulins, the blood pressure tablet — and the dentist gave me something for the "
            "mouth yesterday; Joan has the paper she wrote it on."
        ),
    },
    "pt_isenwell": {
        "onset": (
            "The wrists flared through the week. The numbers have been up since bedtime; the ketone "
            "strips stay clear — I check, as taught."
        ),
        "medications": (
            "The two insulins, the sulfasalazine — and the private clinic started me on something for "
            "the wrists last night; their letter with the name is in the post."
        ),
    },
    "pt_irthcote": {
        "onset": (
            "The nose is as it has been for a year. This morning's reading was up a good step on its "
            "usual."
        ),
        "medications": (
            "The two insulins, the ramipril — and the nose specialist's letter has me on something "
            "before he looks again; I would have to dig the letter out for the name."
        ),
    },
    "pt_jarlethwaite": {
        "onset": (
            "The Crohn's grumbling these two weeks, nothing dreadful. This morning's reading was up "
            "handsomely on its usual."
        ),
        "medications": (
            "The two insulins, the mesalazine — and the bowel specialist has added something new from "
            "last night; his letter is following with the details."
        ),
    },
    "pt_jordholm": {
        "onset": (
            "The skin flared through last week and is settling. The morning readings have climbed since "
            "the weekend."
        ),
        "severity": (
            "The skin is settling under the creams. The readings are the concern — higher each morning "
            "since the weekend, and the night thirst with them."
        ),
        "medications": (
            "The two insulins, the thyroid tablet, the creams — and some tablets the private skin "
            "clinic added on Friday; the name escapes me without the box."
        ),
    },
    "pt_judbrook": {
        "onset": (
            "The hogweed got my arm on Sunday — dressed and easing. The readings have been up since "
            "yesterday."
        ),
        "medications": (
            "The two insulins, the prostate tablet — and a course the out-of-hours doctor gave me on "
            "Sunday for the arm; my wife keeps the packet with the rest."
        ),
    },
    "pt_jexwell": {
        "onset": (
            "The wheeze over the weekend at my daughter's, settled away from the cat. Readings up since "
            "Sunday night."
        ),
        "medications": (
            "The two insulins, my inhalers — and the out-of-hours doctor gave me something on Sunday; "
            "I never can hold the name of it."
        ),
    },
    "pt_jevcote": {
        "onset": (
            "The chest flared Sunday night and the cough is easing. This morning's number was the "
            "highest I have had all year."
        ),
        "medications": (
            "The morning insulin, the metformin, my two inhalers — and the tablets the night doctor "
            "left on Sunday; Pauline wrote the name down somewhere."
        ),
    },
    "pt_jesridge": {
        "onset": (
            "The colitis stirring these two weeks, a nuisance and no more. This morning's readings were "
            "up a long way on their usual."
        ),
        "medications": (
            "The two insulins, the mesalazine granules — and the bowel specialist started me on "
            "something last night; the chemist has the name on their system."
        ),
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=14,
    theme_slug="insulin_steroids",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=PLAIN_EVIDENCE,
    decoys=DECOYS_PLAIN,
    cards=_CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=14,
    theme_slug="insulin_steroids",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=SPLIT_EVIDENCE,
    decoys=DECOYS_SPLIT,
    cards=_CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
