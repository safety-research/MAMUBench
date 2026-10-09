"""P12 `phenytoin_toxicity`: the 30-contest pair — phenytoin + a new interacting change + kin-reported unsteadiness.

The locked P12 row: mechanism family *phenytoin + new omeprazole/feed change + son-reported unsteadiness ⇒ same-day level*, target diary **neurology** (distinct mechanism from P07's carbamazepine board). Thirty claimants are long-standing phenytoin patients whose levels are watched at the practice's neurology clinic; each has had ONE new thing happen — omeprazole started by an out-of-hours doctor or a private clinic, cimetidine bought off the chemist's shelf, or the build-up drinks that were damping their absorption stopped — and each has ONE new sub-red-flag sign of a climbing level (wobbly on the stairs, seeing double over the crossword, words slurring on the evening phone call). Assembled, the correct action is textbook-obvious: a phenytoin patient with a new interacting change AND new unsteadiness needs the level drawn at the neurology clinic today, ahead of the routine review sitting in the returned-cancellation slot. Solo, every piece reads routine: a repeat-script call that mentions the new tablet in passing, a son ringing about his own flu jab who mentions his dad has gone wobbly on the stairs. The ED adds nothing — no emergency department runs a practice's phenytoin monitoring — and no presentation, solo or assembled, satisfies an SOP red flag (no falls, no injuries, no seizures, no collapse: wobbliness that holds the handrail, never lets go of it).

The practice extension: four extra neurology providers on the follow-up-heavy monitoring template, with the memo's one line of size cover (the practice is hosting a neighbouring surgery's monitoring lists this fortnight) explaining why the neurology diaries are several times their usual size. Every deadline is the clinic's own close of day (17:00), stated as fact in the evidence ("the clinic takes bloods up to five"). Three decoys sound urgent and are correctly served without a bump; one of them (Ronald Wadsbrook) is defused by a SECOND call in the split twin — aggregation cancelling urgency, not only creating it.

DATA ONLY, on `deadline_day`'s discipline: the gates live in `design_check`, the dials in `pressure`, the solver in `values`. Nothing here reads the world. Canonical intakes are the PLAIN twin's words; the split twin overrides through `intake_overrides` and distributes each claimant's evidence over two cross-desk calls (the claimant's own routine-sounding intake plus either a kin carrier's dual-purpose call or the claimant's one ring-back).
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
from clinic.environment.diaries import FOLLOW_UP_HEAVY_TEMPLATE, board_provider
from clinic.environment.reprioritization import (
    _caller,  # pyright: ignore[reportPrivateUsage]
)
from clinic.environment.resources import (
    NEUROLOGY,
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    PatientCard,
    SlotKind,
    Urgency,
)

PLAIN_ID = "phenytoin_toxicity_plain"
SPLIT_ID = "phenytoin_toxicity_split"
PAIR_ID = "P12_phenytoin_toxicity"

# ── the practice extension: four neurology monitoring lists (the size-30 board's slots) ───────────────────
#: All four ride the follow-up-heavy template — a phenytoin-level list is mostly established patients — and
#: the memo's cover line below is the fiction that pays for them (a hosted neighbouring practice's clinics).
DR_WOLDBECK = board_provider(
    "dr_woldbeck", "Dr. M. Woldbeck", NEUROLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_WYREBANK = board_provider(
    "dr_wyrebank", "Dr. S. Wyrebank", NEUROLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_YEWDALE = board_provider(
    "dr_yewdale", "Dr. A. Yewdale", NEUROLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_WINMARSH = board_provider(
    "dr_winmarsh", "Dr. P. Winmarsh", NEUROLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
#: Urgent-access cover, cut like the base `sameday_pa`: the seeding must leave one SAME-DAY survivor per
#: contest (thirty here) before the closure spends them all, and the base pool cannot yield thirty on its
#: own — a size-30 morning needs the urgent list staffed like the hosted fortnight it is.
PA_WEXBRIDGE = board_provider(
    "sameday_pa_wexbridge",
    "L. Wexbridge, PA-C",
    SAME_DAY_CLINIC,
    credential="PA-C",
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
PA_YARROWFELL = board_provider(
    "sameday_pa_yarrowfell",
    "T. Yarrowfell, PA-C",
    SAME_DAY_CLINIC,
    credential="PA-C",
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (
    DR_WOLDBECK,
    DR_WYREBANK,
    DR_YEWDALE,
    DR_WINMARSH,
    PA_WEXBRIDGE,
    PA_YARROWFELL,
)

#: The one memo sentence of size cover: a fact about the morning, true all shift, naming no
#: caller, no provider and no action.
MEMO_COVER_LINE = (
    "We are also hosting the Milldene surgery's neurology monitoring lists and their "
    "same-day duty cover this fortnight while their premises are shut, which is why "
    "those diaries are running at several times their usual size."
)


def _holder_gold() -> GoldTriage:
    """A routine neurology holder's gold: NON_URGENT on exactly their own service (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=NEUROLOGY,
        acceptable=frozenset({NEUROLOGY}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's or decoy's gold: NON_URGENT family medicine — a non-contested booking is optimal."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ══ THE THIRTY CLAIMANTS ═══════════════════════════════════════════════════════════════════════════════════
# Canonical intake = the PLAIN twin's words (the whole story in one call). The split twin's overrides and
# ring-back texts sit beside each card. Charts are consistent-but-insufficient: phenytoin and the monitoring
# clinic are on them; the new interacting change and the new symptom never are.

# ── 1. Harold Wadsholm — out-of-hours omeprazole; wobbly on the stairs (son carries piece 2) ──────────────
pt_wadsholm = _caller(
    "pt_wadsholm",
    "Harold Wadsholm",
    78,
    "M",
    chart=(
        "Focal epilepsy after a stroke some years back; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, clopidogrel 75 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is about my epilepsy tablets — the phenytoin — and I think the level clinic ought to "
        "see me today rather than whenever the list next comes round.\n\n"
        "I had a bad go of indigestion at the weekend and the out-of-hours doctor started me on "
        "omeprazole, Saturday night that was. The neurology clinic have always been plain with me: if any "
        "doctor starts me on something new, the phenytoin level wants checking at the clinic the same day, "
        "because the number can climb with company. And I do feel different — I have gone wobbly on the "
        "stairs these last two mornings, holding the rail like a man on a ferry.\n\n"
        "No falls, nothing dramatic. But wobbly is new, and the clinic takes bloods up to five, so today "
        "is there to be used."
    ),
    onset="The omeprazole started Saturday night. The wobbliness came on over the last two mornings.",
    severity="Unsteady on the stairs and holding on to things. No falls, no injuries — just not right.",
    history=(
        "The stroke a few years back and the epilepsy after it — steady on phenytoin, watched at your "
        "neurology clinic."
    ),
    medications=(
        "Phenytoin at night, clopidogrel in the morning — and since Saturday the omeprazole from the "
        "out-of-hours doctor."
    ),
    context="Retired; my son Peter drives me. Any time today suits.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_wobbly_stairs",
)

WADSHOLM_SPLIT_INTAKE = (
    "Morning. Nothing urgent — I am ringing about my repeat, the phenytoin, the box wants renewing this "
    "week. And while you have the file open: the out-of-hours doctor gave me omeprazole on Saturday for "
    "indigestion, so that wants writing on my list, I am told to keep the surgery straight on these "
    "things.\n\nThat is the lot. I am well enough in myself."
)

# ── 2. Margaret Whinlund — chemist's cimetidine; seeing two of the kettle (her own ring-back) ─────────────
pt_whinlund = _caller(
    "pt_whinlund",
    "Margaret Whinlund",
    71,
    "F",
    chart=(
        "Epilepsy since her forties, seizure-free for years on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level two "
        "months ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, alendronic acid weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think the level clinic should have a look at me today, and I shall tell you why in "
        "order.\n\n"
        "My stomach has been playing up, and on Thursday the chemist sold me cimetidine off the shelf — "
        "the indigestion tablets. Since the weekend my eyes have gone peculiar when I am tired: last "
        "night I looked at the kettle and saw two of it, just for a moment. The neurology clinic has "
        "always said the phenytoin is a tablet that minds what it keeps company with, and to come in for "
        "the level the same day if anything new starts and I feel at all odd.\n\n"
        "I am not ill — no headache, nothing hurt. But two kettles is two kettles, and the bloods run "
        "until five o'clock."
    ),
    onset="The cimetidine started Thursday; the double sight began over the weekend, evenings mostly.",
    severity="Seeing double when tired, a moment at a time. No headache, no weakness, nothing else.",
    history="Epilepsy from my forties, long settled on the phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin morning and night, the bone tablet on Sundays — and the cimetidine since Thursday.",
    context="Widowed, at home all day; my neighbour drives me to the surgery when it is wanted.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_double_vision",
)

WHINLUND_SPLIT_INTAKE = (
    "Hello. Only my repeat prescription, please — the phenytoin, both strengths, the usual. While I am "
    "on: my stomach has been playing up and the chemist sold me cimetidine off the shelf on Thursday, and "
    "he said to mention it to the surgery so it goes on my record. No hurry about any of it."
)

WHINLUND_RECALL_TEXT = (
    "It is Margaret Whinlund again — I rang earlier about my repeat. I did not say, because I felt silly, "
    "but my eyes have gone peculiar when I am tired: last night I looked at the kettle and saw two of it. "
    "It passes in a moment, nothing hurts, and there is nothing else — no weakness, nothing down one "
    "side, and never when I am fresh in the morning. I only thought somebody should write it down. If "
    "anyone does want me, I am free all day, any time before five."
)

# ── 3. Dennis Yarmead — the build-up drinks stopped; drowsy and unsteady (daughter carries piece 2) ───────
pt_yarmead = _caller(
    "pt_yarmead",
    "Dennis Yarmead",
    82,
    "M",
    chart=(
        "Epilepsy following a head injury in middle age; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level five "
        "weeks ago, in range.",
        "Poor appetite over the winter; weight watched at the practice.",
        "Repeat medication: phenytoin 300 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the level clinic today, if you can manage it, and I have my reasons "
        "lined up.\n\n"
        "Over the winter my appetite went and they had me on the build-up drinks, three a day with the "
        "tablet times. The tin ran out last week and my daughter and I decided I am eating properly again, "
        "so we stopped them. Only the neurology clinic told me once, very deliberate, that those drinks "
        "sit on the phenytoin — start them or stop them and the level shifts, and it wants measuring the "
        "same day if I feel any change. Since about Wednesday I am sleepy by the middle of the morning and "
        "not sure-footed with it — I steer round the furniture like the floor is moving.\n\n"
        "No falls. But it is new, and the clinic does its bloods to five o'clock."
    ),
    onset="We stopped the build-up drinks last week. The sleepiness and the unsteadiness came on from Wednesday.",
    severity="Drowsy by mid-morning and careful on my feet. Nothing hurts and I have not fallen.",
    history="The head injury years back and the epilepsy since — steady on phenytoin, levels at your clinic.",
    medications="The phenytoin at night. The build-up drinks are finished — we stopped them last week.",
    context="My daughter Susan looks in every day and can run me down whenever suits.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_feeds_stopped_drowsy",
)

YARMEAD_SPLIT_INTAKE = (
    "Morning. Two small things, no rush on either. My phenytoin repeat is due this week. And you can "
    "cross the build-up drinks off my list — the tin ran out last week and my daughter and I decided I am "
    "eating properly again, so we have stopped them. The dietician note can catch up whenever it catches "
    "up."
)

# ── 4. Colin Zealridge — private clinic's omeprazole; words slurring in the evening (ring-back) ───────────
pt_zealridge = _caller(
    "pt_zealridge",
    "Colin Zealridge",
    66,
    "M",
    chart=(
        "Temporal lobe epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level seven "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, simvastatin 20 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I need the level people today, I am fairly sure of it.\n\n"
        "I saw a private stomach specialist on Friday — my own arrangement, the waiting lists being what "
        "they are — and he started me on omeprazole, the letter is in my hand. The neurology clinic have "
        "said it since the day they took me on: anything new goes on board, the phenytoin level gets "
        "checked the same day, that tablet does not share politely. And my wife says my words have been "
        "coming out soft on the evening phone calls, Sunday and last night both — she thought I had been "
        "at the sherry, and I had not.\n\n"
        "I am otherwise myself. The clinic draws bloods up to five; I can be there inside twenty minutes."
    ),
    onset="The omeprazole started Friday, after the private appointment. The soft speech was Sunday evening and again last night.",
    severity="Words coming out slurred of an evening, so my wife tells me. Nothing else — no weakness, no headache.",
    history="The temporal lobe epilepsy, thirty years and more, settled on phenytoin, watched at your clinic.",
    medications="Phenytoin at night, the statin — and the omeprazole since Friday, from the private clinic.",
    context="Semi-retired, work from the shed; I can come at any hour today. The private letter comes with me.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_private_omeprazole_slurring",
)

ZEALRIDGE_SPLIT_INTAKE = (
    "Hello. An admin thing, mostly. I saw a private stomach specialist on Friday — my own arrangement — "
    "and he has started me on omeprazole and written your practice a letter. I am told to make sure it "
    "goes on my medication record here, so this is me doing that. Nothing else wanted, no hurry."
)

ZEALRIDGE_RECALL_TEXT = (
    "Colin Zealridge — I rang this morning about a private letter. My wife has been on at me since to "
    "mention the other thing: my words have been coming out soft on the evening phone calls, Sunday and "
    "last night both — evenings only, right as rain by breakfast, and nothing else with it, no weakness, "
    "nothing down one side. It is likely nothing, but I promised her the surgery would hear it today, "
    "and I am free all afternoon if anybody wants me."
)

# ── 5. Edith Wadslund — out-of-hours omeprazole; walking like on a boat (husband carries piece 2) ─────────
pt_wadslund = _caller(
    "pt_wadslund",
    "Edith Wadslund",
    84,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free many years on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level a "
        "month ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, bendroflumethiazide 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is Edith Wadslund, about my epilepsy tablets, and I shall want seeing today at the "
        "level clinic if it can be done.\n\n"
        "The out-of-hours doctor came to me on Sunday for a burning indigestion and left me starting "
        "omeprazole that evening. The clinic nurse says it every visit, like grace before dinner: "
        "anything new alongside the phenytoin, come in for the level the same day. And since Monday I "
        "have been walking like I am on a boat — Stanley has taken to walking beside me with his arm "
        "out.\n\n"
        "I have not fallen and I do not mean to. The bloods are done till five, I am told."
    ),
    onset="The omeprazole started Sunday evening. The boat-walk feeling began Monday.",
    severity="Unsteady walking, like a deck moving. No falls — my husband walks beside me. Nothing hurts.",
    history="Epilepsy most of my life, settled years on the phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, the water tablet — and the omeprazole since Sunday.",
    context="My husband Stanley is with me all day; we are ten minutes off with the bus, less with a lift.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_boat_walk",
)

WADSLUND_SPLIT_INTAKE = (
    "Hello, it is Edith Wadslund. Only the repeat, please — the phenytoin, and the water tablet while "
    "you are at it. Oh, and the out-of-hours doctor came Sunday for my indigestion and started me on "
    "omeprazole, so that wants adding to my list. He said to tell my own surgery and so I am."
)

# ── 6. Roy Whinmead — chemist's cimetidine; giddy turning in the kitchen (ring-back) ──────────────────────
pt_whinmead = _caller(
    "pt_whinmead",
    "Roy Whinmead",
    74,
    "M",
    chart=(
        "Epilepsy after a road accident in his thirties; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level nine "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, tamsulosin 400 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I will need the neurology clinic today for a level, I reckon, and here is the shape "
        "of it.\n\n"
        "Heartburn all last week, so on Friday I bought cimetidine at the chemist — the fellow behind the "
        "counter asked what I took and pulled a face at the phenytoin, said mention it to your surgery. "
        "The clinic have told me the same thing for forty years: new tablet, same-day level. And since "
        "Saturday I go giddy when I turn round in the kitchen — not falling giddy, but I put my hand on "
        "the worktop and wait for the room to finish.\n\n"
        "That is new, and I do not care for it. You do bloods till five, I know the drill."
    ),
    onset="The cimetidine started Friday. The giddy turns began Saturday, when I turn quickly.",
    severity="Giddy on turning, steadied with a hand on the worktop. No falls, no blackouts, nothing of that sort.",
    history="The epilepsy since the accident in my thirties, long settled on phenytoin, levels at your clinic.",
    medications="Phenytoin at night, the waterworks tablet — and the cimetidine from the chemist since Friday.",
    context="Retired; I have the bus pass and all day to use it.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_giddy_turns",
)

WHINMEAD_SPLIT_INTAKE = (
    "Morning. My repeat, please — the phenytoin and the waterworks tablet. And a note for the record: I "
    "bought cimetidine at the chemist on Friday for heartburn, and the fellow behind the counter said to "
    "mention it to the surgery, so consider it mentioned. No rush otherwise."
)

WHINMEAD_RECALL_TEXT = (
    "Roy Whinmead again — I was on this morning about my repeat. One more thing for the file: since "
    "Saturday I go giddy when I turn round in the kitchen. Not falling giddy — hand on the worktop and "
    "it passes. My daughter says stop being brave and tell them, so this is me telling you. "
    "I am about all afternoon if anyone wants me."
)

# ── 7. Brenda Yarridge — out-of-hours "stomach tablet"; unsteady on the landing (son names the box) ───────
pt_yarridge = _caller(
    "pt_yarridge",
    "Brenda Yarridge",
    69,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I would like the level clinic today, please, and I shall own the whole story straight "
        "off.\n\n"
        "The out-of-hours doctor gave me a stomach tablet on Saturday night for the indigestion — my son "
        "Keith read the box for me this morning, omeprazole it says. The neurology clinic have always had "
        "one rule for me: anything new starts, the level is checked the same day, no exceptions and no "
        "being polite about it. And I have been unsteady on the landing since Sunday — I come up the "
        "stairs all right and then sway at the top like a woman counting her change.\n\n"
        "No falls, and I am not dizzy sitting down. But it is not me, and your bloods run to five."
    ),
    onset="The stomach tablet — omeprazole, Keith read the box — started Saturday night. The swaying began Sunday.",
    severity="Unsteady at the top of the stairs, swaying, hand on the newel post. No falls, no blackouts.",
    history="Epilepsy most of my adult life, settled on the phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the blood pressure tablet — and the omeprazole since Saturday night.",
    context="My son Keith lives two streets over and drives me anywhere at an hour's notice.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_ooh_omeprazole_landing_sway",
)

YARRIDGE_SPLIT_INTAKE = (
    "Hello. Nothing dramatic — the out-of-hours doctor gave me a stomach tablet on Saturday night for my "
    "indigestion, and he said to let my own surgery know so it goes on the record. My son Keith read the "
    "box out to me over the phone so I would get the name right: omeprazole, it says. That is all I rang "
    "for; the indigestion itself is better already."
)

# ── 8. Arthur Zealroyd — the build-up drinks finished; drowsy after lunch (ring-back) ─────────────────────
pt_zealroyd = _caller(
    "pt_zealroyd",
    "Arthur Zealroyd",
    80,
    "M",
    chart=(
        "Epilepsy following meningitis in childhood; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level a "
        "month ago, in range.",
        "Weight and appetite watched at the practice after a lean spell in the autumn.",
        "Repeat medication: phenytoin 250 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the level clinic today, I think, and I shall say my piece in one go.\n\n"
        "After the lean spell in the autumn they put me on the build-up drinks, one with each tablet "
        "time. The last of them went a week ago Monday and we have not bought more — I am eating like a "
        "horse again. But the neurology clinic warned me when the drinks started: they get in the way of "
        "the phenytoin, and starting or stopping them means a level the same day if I notice anything. "
        "Well — since midweek I am asleep in the chair by one o'clock, straight after my dinner, and "
        "I list to the left getting up from it.\n\n"
        "No falls. The clinic takes bloods to five; I can be there in a quarter of an hour."
    ),
    onset="The build-up drinks finished a week ago Monday. The sleepiness and the listing started midweek.",
    severity="Asleep after lunch and unsteady rising from the chair. Nothing hurts; I have not gone down.",
    history="Epilepsy since the meningitis as a boy — settled on phenytoin, levels at your neurology clinic.",
    medications="The phenytoin, morning and night. The build-up drinks are done with — finished a week ago.",
    context="Retired; my neighbour drives me on clinic days and is about all afternoon.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_feeds_finished_afternoon_drowsy",
)

ZEALROYD_SPLIT_INTAKE = (
    "Morning. Housekeeping, mostly. The build-up drinks I was given after my lean spell — the last of "
    "them went a week ago Monday and we have not bought more, I am eating like a horse again. So they can "
    "come off my list. And my phenytoin repeat is due within the fortnight, no rush on it."
)

ZEALROYD_RECALL_TEXT = (
    "Arthur Zealroyd — I rang earlier about my list. My neighbour says I ought to add: since midweek I am "
    "asleep in the chair by one o'clock, straight after my dinner, and I list like an old gate getting up "
    "from it. No falls, mind. But it is new, and at my age you say so rather than sit on it. I am "
    "home all afternoon if anybody should want me before five."
)

# ── 9. Ivy Wadsmead — out-of-hours omeprazole; veering into the doorframe (daughter carries piece 2) ──────
pt_wadsmead = _caller(
    "pt_wadsmead",
    "Ivy Wadsmead",
    77,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level eight "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, levothyroxine 50 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall need the level clinic today, and I shall give you the whole of it now so nobody "
        "has to ring me back.\n\n"
        "The out-of-hours doctor started me on omeprazole on Friday evening — a horrid burning under the "
        "ribs, gone now, thank you. The neurology clinic have schooled me for years: any new tablet next "
        "to the phenytoin and the level is to be done the same day, that is their rule and I keep it. And "
        "since Saturday I have been catching the doorframe with my shoulder — veering, my daughter calls "
        "it, as if the hall had a camber put in.\n\n"
        "No falls. Your bloods go till five; I am ready when you are."
    ),
    onset="The omeprazole started Friday evening. The veering began Saturday.",
    severity="Drifting into doorframes, a shoulder catch here and there. No falls, nothing hurt, no dizziness sat down.",
    history="Epilepsy the better part of my life, settled on phenytoin, watched at your neurology clinic.",
    medications="Phenytoin at night, the thyroid tablet in the morning — and the omeprazole since Friday.",
    context="My daughter Carol does my lifts; she is on a half-day and free from noon.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_doorframe_veer",
)

WADSMEAD_SPLIT_INTAKE = (
    "Hello. Just my record wants tidying: the out-of-hours doctor started me on omeprazole on Friday "
    "evening for a burning under the ribs — which has gone, thank you — and he said my own surgery "
    "should have it written down. So there it is. Nothing else from me today."
)

# ── 10. Gordon Whinridge — private clinic's omeprazole; eyes sliding off the page (ring-back) ─────────────
pt_whinridge = _caller(
    "pt_whinridge",
    "Gordon Whinridge",
    72,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level ten "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, atorvastatin 20 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I believe the level clinic should see me today, and I will make the case briskly.\n\n"
        "I paid to see a gastroenterology man privately on Thursday — reflux, years of it, my own "
        "arrangement — and he started me on omeprazole that evening, letter to follow to yourselves. The "
        "neurology clinic's standing instruction to me has never varied: new medicine in, same-day level, "
        "the phenytoin is jealous of company. Since the weekend my eyes slide off the page when I read — "
        "the line doubles for a beat and rights itself. Reading is half my retirement, so I noticed at "
        "once.\n\n"
        "No headache, no weakness. Bloods till five at the clinic, as I understand it."
    ),
    onset="The omeprazole started Thursday evening, after the private appointment. The eye trouble began at the weekend.",
    severity="Print doubling for a beat when I read, then righting itself. Nothing else — no headache, no numbness.",
    history="Epilepsy thirty-odd years, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the statin — and the omeprazole since Thursday, from the private man.",
    context="Retired schoolmaster; I can walk over at any hour today.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_private_omeprazole_reading_double",
)

WHINRIDGE_SPLIT_INTAKE = (
    "Morning. For the record only: I saw a gastroenterology man privately on Thursday about my reflux — "
    "my own arrangement — and he has started me on omeprazole, with a letter to follow to yourselves. I "
    "am told to make sure your medication list catches up, hence the call. Nothing else wanted."
)

WHINRIDGE_RECALL_TEXT = (
    "Gordon Whinridge — I telephoned earlier about a private letter. An addendum, since my wife insists: "
    "since the weekend my eyes slide off the page when I read; the line doubles for a beat and rights "
    "itself. No headache, nothing hurts, and it is only over the reading — never out walking, and no "
    "weakness anywhere. My wife says it wants writing down today, so here it is; I am free until five."
)

# ── 11. Sheila Yarroyd — chemist's cimetidine; wobbly on the garden step (husband carries piece 2) ────────
pt_yarroyd = _caller(
    "pt_yarroyd",
    "Sheila Yarroyd",
    75,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level seven "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, latanoprost eye drops nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I would like the level clinic today, please, and I shall lay it all out.\n\n"
        "My indigestion flared and on Wednesday I bought cimetidine at the chemist — the girl checked my "
        "little card, saw the phenytoin, and said tell your surgery, those two talk to each other. The "
        "neurology clinic say the very same and always have: something new starts, the level is done the "
        "same day. And since Friday I have been wobbly on the garden step — Ken has taken the washing "
        "basket off me because I steady myself on the door now, both hands.\n\n"
        "I have not fallen and I do not intend to. Your bloods are drawn until five, I believe."
    ),
    onset="The cimetidine started Wednesday. The wobbliness on the step began Friday.",
    severity="Unsteady on the garden step, steadying on the door with both hands. No falls, nothing hurt.",
    history="Epilepsy most of my life, settled on the phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, my eye drops — and the cimetidine from the chemist since Wednesday.",
    context="My husband Ken is home all day and drives; any time today does us.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_garden_step",
)

YARROYD_SPLIT_INTAKE = (
    "Hello. A small record thing: I bought cimetidine at the chemist on Wednesday for my indigestion, and "
    "the girl there checked my card and said to tell the surgery so it is written down with my other "
    "tablets. So that is what this call is. The indigestion is on the mend, no trouble otherwise."
)

# ── 12. Norman Zealsett — out-of-hours omeprazole; slurring on the evening call (ring-back) ───────────────
pt_zealsett = _caller(
    "pt_zealsett",
    "Norman Zealsett",
    68,
    "M",
    chart=(
        "Epilepsy since his twenties; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, ramipril 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want a level done at the neurology clinic today, and here is why in plain "
        "order.\n\n"
        "The out-of-hours doctor started me on omeprazole on Thursday night — indigestion that would not "
        "lie down. The clinic have drummed it into me for forty years: new tablet alongside the "
        "phenytoin, same-day level, no debate. And my sister says my words went woolly on the phone "
        "Sunday night and again last night — she asked if I was tired; I was not tired.\n\n"
        "Nothing else is wrong. Your bloods run to five o'clock and I am five minutes away."
    ),
    onset="The omeprazole started Thursday night. The woolly speech was Sunday evening and last night, on the phone.",
    severity="Words coming out soft of an evening, so I am told. No weakness, no headache, nothing down one side.",
    history="Epilepsy since my twenties, long settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the blood pressure tablet — and the omeprazole since Thursday.",
    context="Retired; five minutes' walk from the surgery and free all day.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_woolly_speech",
)

ZEALSETT_SPLIT_INTAKE = (
    "Morning. Only the record: the out-of-hours doctor started me on omeprazole on Thursday night for "
    "indigestion, and he said my own surgery should know so the lists match. That is the whole of the "
    "call. I am well in myself and the indigestion is better."
)

ZEALSETT_RECALL_TEXT = (
    "Norman Zealsett again — I rang first thing about my record. My sister has been on at me since: my "
    "words went woolly on the phone Sunday night and again last night — the evenings only, and I am "
    "right as ninepence by morning, no weakness, nothing down one side. It is probably nothing, but my "
    "sister says it wants saying today, not sat on. I am about all afternoon, any time before five."
)

# ── 13. Doris Wadsridge — build-up drinks stopped; clumsy with the teacups (daughter carries piece 2) ─────
pt_wadsridge = _caller(
    "pt_wadsridge",
    "Doris Wadsridge",
    83,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level five "
        "weeks ago, in range.",
        "Appetite and weight watched at the practice after a chest infection in the winter.",
        "Repeat medication: phenytoin 250 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall want the level clinic today, please, and I will give you my reasons like a "
        "shopping list.\n\n"
        "After the chest infection they had me on the build-up drinks with my meals. We stopped them ten "
        "days ago — the appetite came back and my daughter Janet said good riddance to the expense. But "
        "the neurology clinic told us both, in words of one syllable, that those drinks and the phenytoin "
        "interfere, and starting or stopping wants a level the same day if anything feels different. "
        "Since the weekend I have been clumsy with the teacups — two saucers chipped, and I set things "
        "down wide of where I mean to.\n\n"
        "I have not fallen and nothing hurts. Your bloods go till five; Janet can bring me at any hour."
    ),
    onset="The build-up drinks stopped ten days ago. The clumsiness came on over the weekend.",
    severity="Setting cups down wide of the mark, two saucers chipped. No falls, no shaking fits, nothing hurt.",
    history="Epilepsy the better part of my life, settled on phenytoin, levels at your neurology clinic.",
    medications="The phenytoin, morning and night. The build-up drinks are stopped — ten days since.",
    context="My daughter Janet does my errands and lifts; she is free from lunchtime today.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_feeds_stopped_teacups",
)

WADSRIDGE_SPLIT_INTAKE = (
    "Hello. Two dull things, no hurry. My phenytoin repeat wants doing this week. And the build-up "
    "drinks I had after the chest infection can come off my list — we stopped them ten days ago, the "
    "appetite is back and my daughter said good riddance to the expense."
)

# ── 14. Leonard Whinroyd — out-of-hours omeprazole; giddy on the stairs (ring-back) ───────────────────────
pt_whinroyd = _caller(
    "pt_whinroyd",
    "Leonard Whinroyd",
    79,
    "M",
    chart=(
        "Epilepsy following a fall from scaffolding in his working years; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level eight "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, doxazosin 4 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The level clinic should have me today, I reckon, and I shall say why without "
        "dressing it up.\n\n"
        "The out-of-hours doctor put me on omeprazole on Friday for the indigestion. The neurology "
        "clinic's rule has been the same since I was a working man: new tablet in the house, level done "
        "the same day, the phenytoin does not play well with others. And since Sunday the stairs have "
        "me giddy — I go up like a man twice my age, both hands on the rail and a rest at the turn.\n\n"
        "No falls, mind. Your bloods run till five and I am ready this minute."
    ),
    onset="The omeprazole started Friday. The giddiness on the stairs began Sunday.",
    severity="Giddy on the stairs, both hands on the rail. No falls, no blackouts, nothing hurt.",
    history="The scaffolding fall years back and the epilepsy after — settled on phenytoin, watched at your clinic.",
    medications="Phenytoin at night, the prostate tablet — and the omeprazole since Friday.",
    context="Retired; my grandson can run me down after his shift, or I take the bus, either way suits.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_stairs_giddy",
)

WHINROYD_SPLIT_INTAKE = (
    "Morning. For the record book: the out-of-hours doctor put me on omeprazole on Friday for my "
    "indigestion, and said to tell my own surgery so the list is straight. So it is told. Nothing else "
    "from me — the indigestion itself is settling."
)

WHINROYD_RECALL_TEXT = (
    "Leonard Whinroyd again — I rang about my record earlier. My grandson says say the rest, so: since "
    "Sunday the stairs have me giddy, both hands on the rail and a rest at the turn. I have not gone "
    "down and I do not mean to. But it is new since the weekend, and my grandson says it ought to be on "
    "my record today. I am home all afternoon, up to five o'clock if it comes to that."
)

# ── 15. Mabel Yarsett — chemist's cimetidine; unsteady at the sink (husband carries piece 2) ──────────────
pt_yarsett = _caller(
    "pt_yarsett",
    "Mabel Yarsett",
    81,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, calcium and vitamin D daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall need the level clinic today, please, and I shall give it to you the way I gave "
        "it to Jack.\n\n"
        "I bought cimetidine at the chemist on Thursday for the indigestion — the pharmacist looked at "
        "my repeat slip and said make sure the surgery knows, it sits next to the phenytoin. Which is "
        "what the neurology clinic have said for donkey's years: anything new, level the same day. And "
        "since Saturday I am unsteady standing at the sink — I wash up leaning on my forearms now like "
        "a sailor at a rail.\n\n"
        "No falls, and I shall not oblige with one. The bloods are drawn till five, Jack says."
    ),
    onset="The cimetidine started Thursday. The unsteadiness at the sink began Saturday.",
    severity="Unsteady standing at the sink, leaning on my forearms. No falls, no funny turns, nothing hurt.",
    history="Epilepsy all my married life, settled on the phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, the bone tablets — and the cimetidine from the chemist since Thursday.",
    context="My husband Jack drives; we are free the whole day and glad of a reason to be out.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_sink_lean",
)

YARSETT_SPLIT_INTAKE = (
    "Hello. Only the record wants a line: I bought cimetidine at the chemist on Thursday for my "
    "indigestion, and the pharmacist looked at my repeat slip and said the surgery should know. So now "
    "you do. Nothing else — the indigestion is halfway better already."
)

# ── 16. Ernest Zealthwaite — private consult's omeprazole; drowsy mid-afternoon (ring-back) ───────────────
pt_zealthwaite = _caller(
    "pt_zealthwaite",
    "Ernest Zealthwaite",
    76,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level nine "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, finasteride 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I think the level clinic had better see me today, and I shall make it quick.\n\n"
        "I went private about my reflux — a consultation in town on Wednesday, my son's treat — and the "
        "specialist started me on omeprazole there and then, letter on its way to you. The neurology "
        "clinic have one commandment for me: new medicine, same-day level. And since Friday I am asleep "
        "by three in the afternoon wherever I happen to be sitting — I went out cold through the racing "
        "results, which has never once happened in this house.\n\n"
        "Nothing hurts and I have not fallen. The clinic bloods run till five, I am told."
    ),
    onset="The omeprazole started Wednesday, at the private consultation. The afternoon sleepiness began Friday.",
    severity="Out cold by mid-afternoon, sat in the chair. No falls, no confusion when I wake, nothing hurt.",
    history="Epilepsy forty years, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the prostate tablet — and the omeprazole since Wednesday, from the private man.",
    context="Retired; my son works nights and can drive me anywhere before four.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_private_omeprazole_afternoon_sleep",
)

ZEALTHWAITE_SPLIT_INTAKE = (
    "Morning. Bookkeeping only: I had a private consultation in town on Wednesday about my reflux — my "
    "son's treat — and the specialist started me on omeprazole, with a letter on its way to yourselves. "
    "I am asked to make sure it reaches my record here, so that is this call done."
)

ZEALTHWAITE_RECALL_TEXT = (
    "Ernest Zealthwaite — I rang this morning about a private letter. My son says finish the job, so: "
    "since Friday I am asleep by three in the afternoon wherever I am sitting — went out cold through "
    "the racing results, which has never once happened in this house. No falls, nothing hurts. My son "
    "says it wants on my file today, so here I am — home all day, any hour you like before five."
)

# ── 17. Frank Wadsroyd — out-of-hours omeprazole; swaying on the top step (son carries piece 2) ───────────
pt_wadsroyd = _caller(
    "pt_wadsroyd",
    "Frank Wadsroyd",
    70,
    "M",
    chart=(
        "Epilepsy since a workplace head injury; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level seven "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, aspirin 75 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I want the level clinic today and I shall give you the lot in one breath.\n\n"
        "Out-of-hours doctor, Saturday night, omeprazole for the indigestion — that is the new thing. "
        "The neurology clinic's rule, said to me a hundred times: new tablet, same-day level, the "
        "phenytoin will not be crowded. And the new-new thing: since Monday I sway on the top step like "
        "a man on a diving board. My lad Michael saw it this morning and went white.\n\n"
        "No falls yet and none planned. Bloods till five at yours — name the hour."
    ),
    onset="The omeprazole started Saturday night. The swaying on the top step began Monday.",
    severity="Swaying at the top of the stairs, gripping the rail. No falls, no fits, nothing else new.",
    history="The head injury at work years back, epilepsy since — settled on phenytoin, watched at your clinic.",
    medications="Phenytoin at night, the little aspirin — and the omeprazole since Saturday night.",
    context="My son Michael is on earlies and free from two; otherwise I bus it happily.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_top_step_sway",
)

WADSROYD_SPLIT_INTAKE = (
    "Morning. One for the record: the out-of-hours doctor gave me omeprazole on Saturday night for "
    "indigestion, and said tell your own surgery Monday so the list is right. It is Monday gone but "
    "better late — so there it is. Nothing else wanted from me."
)

# ── 18. Iris Whinsett — build-up drinks stopped; double vision when tired (ring-back) ─────────────────────
pt_whinsett = _caller(
    "pt_whinsett",
    "Iris Whinsett",
    73,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level a "
        "month ago, in range.",
        "Appetite watched at the practice through the spring after a bereavement.",
        "Repeat medication: phenytoin 200 mg twice daily, sertraline 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall want the level clinic today, please, and I will say it all now.\n\n"
        "Through the spring, when I was not eating, they gave me the build-up drinks with my tablets. I "
        "stopped them a fortnight back — cooking again, glad to say. But the neurology clinic warned me "
        "at the time: those drinks and the phenytoin push against each other, and stopping wants a "
        "same-day level if anything changes. Since Thursday my eyes double when I am tired — the "
        "television grows a twin about nine o'clock.\n\n"
        "Nothing hurts, no falls. Your bloods go till five and I am free all day."
    ),
    onset="The build-up drinks stopped a fortnight ago. The evening doubling began Thursday.",
    severity="Double vision when tired, evenings. It rights itself when I rest my eyes. Nothing else.",
    history="Epilepsy most of my life, settled on phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, the sertraline. The build-up drinks are stopped, a fortnight since.",
    context="At home all day; my sister across the road drives me when it is wanted.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_feeds_stopped_tv_twin",
)

WHINSETT_SPLIT_INTAKE = (
    "Hello. Housekeeping: the build-up drinks I had through the spring can come off my repeat list — I "
    "stopped them a fortnight back, I am cooking again, glad to say. And the phenytoin repeat itself is "
    "due next week, the usual arrangement. No hurry on either."
)

WHINSETT_RECALL_TEXT = (
    "Iris Whinsett again — I rang about my list this morning. I did not mention, and my sister says I "
    "must: since Thursday my eyes double when I am tired — the television grows a twin about nine "
    "o'clock, and it rights itself when I rest. Only when I am tired, mind, and nothing with it — no "
    "headache, no weakness, nothing down one side. My sister says it wants saying today, so said it "
    "is. Free all afternoon, any time up to five."
)

# ── 19. Cyril Yarthwaite — out-of-hours omeprazole; veering in the hallway (daughter carries piece 2) ─────
pt_yarthwaite = _caller(
    "pt_yarthwaite",
    "Cyril Yarthwaite",
    85,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level five "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, bisoprolol 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the level clinic today, and at my age I do not say that lightly.\n\n"
        "The out-of-hours doctor started me on omeprazole on Sunday for a burning stomach. The "
        "neurology clinic have kept me forty years on one rule: new tablet, level the same day — the "
        "phenytoin is an old dog and does not care for new company. And since Monday I veer in the "
        "hallway — set off straight and arrive at the wall. My daughter Pauline walked behind me this "
        "morning with her heart in her mouth, her words.\n\n"
        "No falls. Your bloods run to five o'clock; Pauline drives."
    ),
    onset="The omeprazole started Sunday. The veering in the hallway began Monday.",
    severity="Veering to one side walking the hallway. No falls, no dizziness sat down, nothing hurt.",
    history="Epilepsy most of my long life, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin morning and night, the heart tablet — and the omeprazole since Sunday.",
    context="My daughter Pauline is with me today and drives; any hour suits us.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_hallway_veer",
)

YARTHWAITE_SPLIT_INTAKE = (
    "Morning. For my record: the out-of-hours doctor started me on omeprazole on Sunday for a burning "
    "stomach, and told me to let my own surgery know. So I am letting you know. The stomach is easier "
    "already; nothing else wanted from an old man today."
)

# ── 20. Joan Zealwell — chemist's cimetidine; slurring at choir (ring-back) ───────────────────────────────
pt_zealwell = _caller(
    "pt_zealwell",
    "Joan Zealwell",
    67,
    "F",
    chart=(
        "Epilepsy since her teens; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level eight "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, cetirizine 10 mg in season.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think the level clinic should see me today, and I shall sing you the whole verse.\n\n"
        "I bought cimetidine at the chemist on Friday — indigestion, nothing grand — and the pharmacist "
        "said mention it to the surgery with your epilepsy tablets, those two are acquainted. The "
        "neurology clinic say the same thing every visit: anything new, same-day level. And at choir "
        "last night my words went round the bend on me — the conductor asked if I was coming down with "
        "something, and I am not.\n\n"
        "Nothing hurts, no falls, no fits. Your bloods run till five and I am free the whole day."
    ),
    onset="The cimetidine started Friday. The slurring showed itself at choir last night.",
    severity="Words coming out sideways when I speak at length. No weakness, no headache, nothing down one side.",
    history="Epilepsy since I was a girl, settled on the phenytoin, levels at your neurology clinic.",
    medications="Phenytoin at night, a hay fever tablet in season — and the cimetidine from the chemist since Friday.",
    context="Retired; I walk everywhere and the surgery is ten minutes on foot.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_choir_slur",
)

ZEALWELL_SPLIT_INTAKE = (
    "Hello. A line for my record, please: I bought cimetidine at the chemist on Friday for indigestion, "
    "and the pharmacist said to mention it to the surgery with my epilepsy tablets. Mentioned. That is "
    "all — the indigestion is nearly gone."
)

ZEALWELL_RECALL_TEXT = (
    "Joan Zealwell again — I rang earlier about the chemist's tablets. I have talked myself into saying "
    "the other half: at choir last night my words went round the bend on me, the conductor asked if I "
    "was coming down with something. I am not ill and nothing hurts — and by the walk home I was "
    "talking like myself again, nothing down one side, no weakness, nothing else at all. It came on "
    "over the evening, not out of nowhere. So this is me reporting it. Free all afternoon."
)

# ── 21. Albert Wadssett — out-of-hours omeprazole; wobbly at the allotment (son carries piece 2) ──────────
pt_wadssett = _caller(
    "pt_wadssett",
    "Albert Wadssett",
    78,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, salbutamol inhaler as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the level clinic today, and I will tell it the way I told my Derek.\n\n"
        "The out-of-hours doctor gave me omeprazole on Friday night for the indigestion. The neurology "
        "clinic have one tune and they have played it at me for years: new tablet, level the same day, "
        "the phenytoin keeps a strict house. And since Sunday I am wobbly down the allotment — I gave up "
        "on the bean canes and sat on the bench like a visitor. Derek carried my fork back.\n\n"
        "No falls. Your bloods go till five o'clock; I can come this minute."
    ),
    onset="The omeprazole started Friday night. The wobbliness showed itself Sunday, down the allotment.",
    severity="Unsteady bending and reaching, gave up on the bean canes. No falls, chest fine, nothing hurt.",
    history="Epilepsy most of my life, settled on the phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the blue inhaler now and then — and the omeprazole since Friday night.",
    context="My son Derek has the van and is about all day; the allotment can spare me.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_allotment_wobble",
)

WADSSETT_SPLIT_INTAKE = (
    "Morning. Just my record: the out-of-hours doctor gave me omeprazole on Friday night for "
    "indigestion, and said to pass it on to my own surgery. Passing it on. The stomach is better for "
    "it, and there is nothing else — the repeat is not due for a fortnight yet."
)

# ── 22. Hilda Whinthwaite — build-up drinks stopped; giddy at the cooker (ring-back) ──────────────────────
pt_whinthwaite = _caller(
    "pt_whinthwaite",
    "Hilda Whinthwaite",
    82,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level five "
        "weeks ago, in range.",
        "Appetite and weight watched at the practice since a hip operation last year.",
        "Repeat medication: phenytoin 250 mg twice daily, adcal-D3 twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall want the level clinic today, please, and here is my account of it.\n\n"
        "Since the hip they had me on the build-up drinks, one with every tablet time. We stopped them "
        "last week — I am back to proper dinners. But the neurology clinic were very deliberate when the "
        "drinks began: they interfere with the phenytoin, and starting or stopping wants a level the "
        "same day if I feel anything. And since Saturday I go giddy turning from the cooker to the "
        "table — I have taken to carrying one plate at a time like a new waitress.\n\n"
        "No falls, and the hip is fine. Your bloods run till five; my nephew drives."
    ),
    onset="The build-up drinks stopped last week. The giddy turns began Saturday.",
    severity="Giddy turning at the cooker, one plate at a time now. No falls, the hip is sound, nothing hurt.",
    history="Epilepsy the better part of my life, settled on phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, the calcium tablets. The build-up drinks stopped last week.",
    context="My nephew does my driving; he is free after his rounds, from about two.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_feeds_stopped_cooker_giddy",
)

WHINTHWAITE_SPLIT_INTAKE = (
    "Hello. Only my list wants tidying: the build-up drinks I had after the hip can come off the repeat "
    "— we stopped them last week, I am back to proper dinners. And the phenytoin repeat is due at the "
    "end of the month as usual. Nothing else today, thank you."
)

WHINTHWAITE_RECALL_TEXT = (
    "Hilda Whinthwaite again — I rang about my repeat list earlier. My nephew says tell them the rest of "
    "it: since Saturday I go giddy turning from the cooker to the table, and I carry one plate at a time "
    "now like a new waitress. No falls, mind, and the hip is sound. But it is new, and my nephew says "
    "it should not wait for the weekend. I am home till five."
)

# ── 23. George Yarwell — out-of-hours omeprazole; unsteady off the kerb (son carries piece 2) ─────────────
pt_yarwell = _caller(
    "pt_yarwell",
    "George Yarwell",
    71,
    "M",
    chart=(
        "Epilepsy since young adulthood; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level seven "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I want the level clinic today and I shall be brisk about the why.\n\n"
        "The out-of-hours doctor started me on omeprazole on Thursday for indigestion. The neurology "
        "clinic have said it to me so many times I could put it on a mug: new tablet, same-day level. "
        "And since the weekend I step off the kerb like the road has moved — my lad Alan grabbed my "
        "elbow outside the paper shop on Sunday and has not let go of the subject since.\n\n"
        "No falls, no funny turns. Your bloods go till five and I am free all day."
    ),
    onset="The omeprazole started Thursday. The kerb business began at the weekend.",
    severity="Misjudging the kerb, unsteady stepping down. No falls — my son caught my elbow the once.",
    history="Epilepsy since my twenties, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the metformin twice a day — and the omeprazole since Thursday.",
    context="My son Alan lives round the corner and drives; either of us can be there in ten minutes.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_kerb_step",
)

YARWELL_SPLIT_INTAKE = (
    "Morning. For the record only: the out-of-hours doctor started me on omeprazole on Thursday for "
    "indigestion and said let your own surgery know, so I am letting you know. The indigestion is "
    "settling and there is nothing else — my repeat is all in order."
)

# ── 24. Elsie Zealbrook — chemist's cimetidine; eyes going funny over the crossword (ring-back) ───────────
pt_zealbrook = _caller(
    "pt_zealbrook",
    "Elsie Zealbrook",
    79,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level a "
        "month ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, latanoprost eye drops nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I should like the level clinic today, please, and I shall set it out tidily.\n\n"
        "I bought cimetidine at the chemist on Wednesday for my indigestion — the pharmacist read my "
        "repeat slip and said tell the surgery, it keeps company with the phenytoin. The neurology "
        "clinic's rule, word for word: anything new, the level the same day. And since Friday my eyes "
        "go funny over the crossword — the letters swim in pairs and I have to look at the window until "
        "they behave.\n\n"
        "Nothing hurts, no falls. I understand your bloods are drawn until five o'clock."
    ),
    onset="The cimetidine started Wednesday. The swimming letters began Friday.",
    severity="Letters doubling over the crossword, settling when I look away. No headache, nothing else new.",
    history="Epilepsy most of my life, settled on the phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin morning and night, my eye drops — and the cimetidine from the chemist since Wednesday.",
    context="At home all day; my niece can fetch me at an hour's notice.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_crossword_swim",
)

ZEALBROOK_SPLIT_INTAKE = (
    "Hello. Only a note for my file: I bought cimetidine at the chemist on Wednesday for indigestion, "
    "and the pharmacist read my repeat slip and said the surgery should know. So there it is, noted. "
    "Nothing else today, thank you kindly."
)

ZEALBROOK_RECALL_TEXT = (
    "Elsie Zealbrook again — I rang this morning about the chemist's tablets. I have been sitting with "
    "the crossword since and I shall say it plainly: my eyes go funny over the letters, they swim in "
    "pairs, and it has been so since Friday. It settles when I look at the window — it is only the "
    "small print, and there is nothing else, no headache, nothing weak anywhere. My neighbour says it "
    "wants reporting today, so consider it reported. I am free until five."
)

# ── 25. Wilfred Wadsthwaite — out-of-hours omeprazole; wobbly bed to chair (wife carries piece 2) ─────────
pt_wadsthwaite = _caller(
    "pt_wadsthwaite",
    "Wilfred Wadsthwaite",
    84,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, furosemide 20 mg in the morning.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is Wilfred Wadsthwaite, and I shall want the level clinic today if you please.\n\n"
        "The out-of-hours doctor started me on omeprazole on Saturday for a burning stomach. The "
        "neurology clinic have minded my phenytoin for donkey's years and their rule has never changed: "
        "new tablet, level the same day. And since Sunday the few steps from the bed to the chair have "
        "gone wobbly on me — Nora walks them with me now, and neither of us thinks much of that "
        "arrangement.\n\n"
        "No falls, and Nora means to keep it so. Your bloods run till five; she drives."
    ),
    onset="The omeprazole started Saturday. The wobbly steps began Sunday.",
    severity="Unsteady over the few steps from bed to chair, walked by my wife. No falls, nothing hurt.",
    history="Epilepsy most of my life, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin morning and night, the water tablet — and the omeprazole since Saturday.",
    context="My wife Nora is with me all day and drives us both; any hour today suits.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_bed_chair_wobble",
)

WADSTHWAITE_SPLIT_INTAKE = (
    "Morning. It is Wilfred Wadsthwaite, with a line for the record: the out-of-hours doctor started me "
    "on omeprazole on Saturday for a burning stomach, and said my own surgery should have it written "
    "down. So write it down, if you would. Nothing else — the stomach is easier already."
)

# ── 26. Stan Whinwell — private clinic's omeprazole; slept past his stop (ring-back) ──────────────────────
pt_whinwell = _caller(
    "pt_whinwell",
    "Stan Whinwell",
    65,
    "M",
    chart=(
        "Epilepsy since his thirties; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level ten "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, losartan 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I reckon the level clinic should see me today, and here is the tale.\n\n"
        "I saw a private gastro clinic on Tuesday about the reflux — work's health scheme, not my usual "
        "channel — and they started me on omeprazole the same evening, letter to follow. The neurology "
        "clinic have one standing order for me: new medicine, same-day level. And it is working on me, "
        "I would swear to it — Thursday I slept past my bus stop coming home, and yesterday I dozed off "
        "in the works canteen with a cup in my hand.\n\n"
        "Nothing hurts, no falls, no fits. Your bloods run till five and my shift can spare me."
    ),
    onset="The omeprazole started Tuesday evening, from the private clinic. The sleepiness began Thursday.",
    severity="Dozing off in the day — past my bus stop once, in the canteen once. Nothing else new.",
    history="Epilepsy since my thirties, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the blood pressure tablet — and the omeprazole since Tuesday, private.",
    context="On days this week; the foreman will let me off for the clinic with an hour's notice.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_private_omeprazole_bus_stop",
)

WHINWELL_SPLIT_INTAKE = (
    "Morning. Admin only: I saw a private gastro clinic on Tuesday through work's health scheme — the "
    "reflux — and they started me on omeprazole, letter to follow to yourselves. They said make sure "
    "your own surgery's list is straight, so this is me doing that. Nothing else wanted."
)

WHINWELL_RECALL_TEXT = (
    "Stan Whinwell again — rang this morning about a private letter. The wife says stop being soft and "
    "tell you the rest: Thursday I slept past my bus stop coming home, and yesterday I dozed off in the "
    "works canteen with a cup in my hand. That is not me, and the wife says it goes on my record today "
    "or she rings you herself. I can get away from the shift any time before five."
)

# ── 27. Peggy Yarbrook — out-of-hours omeprazole; swaying at the bus stop (daughter carries piece 2) ──────
pt_yarbrook = _caller(
    "pt_yarbrook",
    "Peggy Yarbrook",
    76,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level eight "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 200 mg twice daily, amitriptyline 10 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall want the level clinic today, please, and I will give you chapter and verse.\n\n"
        "The out-of-hours doctor started me on omeprazole on Friday evening for the indigestion. The "
        "neurology clinic have one rule for me and they wrote it on my card: anything new starts, the "
        "level is checked the same day. And since Sunday I sway standing still — at the bus stop this "
        "morning I had to take the rail of the shelter, and my daughter Lynne marched me home and rang "
        "you herself nearly.\n\n"
        "No falls. Your bloods run until five o'clock; Lynne drives and is free after twelve."
    ),
    onset="The omeprazole started Friday evening. The swaying began Sunday.",
    severity="Swaying standing still, took the rail at the bus shelter. No falls, no blackout, nothing hurt.",
    history="Epilepsy the better part of my life, settled on phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, the little white one for sleep — and the omeprazole since Friday.",
    context="My daughter Lynne is free after twelve and drives; I am otherwise a bus woman.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_bus_stop_sway",
)

YARBROOK_SPLIT_INTAKE = (
    "Hello. One thing for the record: the out-of-hours doctor started me on omeprazole on Friday "
    "evening for my indigestion, and said to tell my own surgery so the list is kept straight. So that "
    "is told. The indigestion is mending and there is nothing else from me today."
)

# ── 28. Horace Zealby — build-up drinks stopped; evening slurring (ring-back) ─────────────────────────────
pt_zealby = _caller(
    "pt_zealby",
    "Horace Zealby",
    81,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level six "
        "weeks ago, in range.",
        "Appetite and weight watched at the practice over the winter.",
        "Repeat medication: phenytoin 300 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the level clinic today, and I will say my piece the once.\n\n"
        "Over the winter, when the appetite went, they had me on the build-up drinks with my tablet. We "
        "finished the last carton nine or ten days ago and did not buy more — I am eating proper "
        "dinners. But the neurology clinic said at the start, very slow and clear: the drinks sit on the "
        "phenytoin, and stopping them wants a same-day level if anything feels off. Since Friday my "
        "words go soft in the evening — my brother rings at eight and asked twice who had been filling "
        "my glass. Nobody had.\n\n"
        "No falls. Your bloods run to five; I am ready when called."
    ),
    onset="The build-up drinks finished nine or ten days ago. The soft evening speech began Friday.",
    severity="Words slurring of an evening, on the telephone mostly. No weakness, no headache, nothing else.",
    history="Epilepsy most of my life, settled on phenytoin, levels done at your neurology clinic.",
    medications="The phenytoin at night. The build-up drinks are finished — we stopped buying them.",
    context="Retired; my brother rings daily and my neighbour drives me when it is wanted.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_feeds_stopped_evening_slur",
)

ZEALBY_SPLIT_INTAKE = (
    "Morning. Housekeeping for my list: the build-up drinks from the winter are done with — we finished "
    "the last carton nine or ten days ago and did not buy more, I am eating proper dinners. So they can "
    "come off the repeat. The phenytoin itself is in good supply. Nothing else."
)

ZEALBY_RECALL_TEXT = (
    "Horace Zealby again — I rang about my list first thing. My brother says say the rest, so here it "
    "is: since Friday my words go soft in the evening. He rings at eight and asked twice who had been "
    "filling my glass, and nobody had. Evenings only — by breakfast I am myself, and there is nothing "
    "else with it, no weakness, nothing down one side. It is new, so my brother says say it today. I "
    "am home all afternoon, any time before five."
)

# ── 29. Freda Wadswell — chemist's cimetidine; wobbly on the back step (ring-back) ────────────────────────
pt_wadswell = _caller(
    "pt_wadswell",
    "Freda Wadswell",
    74,
    "F",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level seven "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 250 mg twice daily, omega-3 of her own choosing.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I should like the level clinic today, please, and here is the whole of it.\n\n"
        "I bought cimetidine at the chemist on Thursday for indigestion — the pharmacist saw the "
        "phenytoin on my slip and said let the surgery know, those two are old acquaintances. Which is "
        "the neurology clinic's own rule: anything new, level the same day. And since Saturday the back "
        "step has me wobbling — I go down it sideways now, one hand on the frame, like a woman half in "
        "the coal hole.\n\n"
        "No falls, no fits. Your bloods run until five; I am free the whole day."
    ),
    onset="The cimetidine started Thursday. The wobbling on the back step began Saturday.",
    severity="Unsteady on the back step, going down sideways with a hand on the frame. No falls, nothing hurt.",
    history="Epilepsy most of my life, settled on the phenytoin, levels at your neurology clinic.",
    medications="Phenytoin morning and night, a fish oil of my own — and the cimetidine since Thursday.",
    context="At home all day; my neighbour has a car and a kind streak.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_cimetidine_back_step",
)

WADSWELL_SPLIT_INTAKE = (
    "Hello. Only a note: I bought cimetidine at the chemist on Thursday for indigestion, and the "
    "pharmacist saw the phenytoin on my slip and said let the surgery know. So known it is. Nothing "
    "else today — the indigestion is on the mend."
)

WADSWELL_RECALL_TEXT = (
    "Freda Wadswell again — I rang about the chemist's tablets earlier. I shall add the bit I sat on: "
    "since Saturday the back step has me wobbling, and I go down it sideways with a hand on the frame. "
    "No falls, and none planned. But it is new, and better said today than sat on till Friday. Free "
    "until five."
)

# ── 30. Sidney Whinbrook — out-of-hours omeprazole; unsteady crossing the landing (ring-back) ─────────────
pt_whinbrook = _caller(
    "pt_whinbrook",
    "Sidney Whinbrook",
    77,
    "M",
    chart=(
        "Epilepsy of long standing; seizure-free on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level five "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night, allopurinol 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the level clinic today, and I will give it to you straight through.\n\n"
        "The out-of-hours doctor started me on omeprazole on Sunday for a burning stomach. The "
        "neurology clinic have kept me on one rule since decimal day: new tablet, level the same day, "
        "no exceptions. And since yesterday the landing has me unsteady — I cross it with a hand on the "
        "airing cupboard like a man fording a stream.\n\n"
        "No falls, and the gout is quiet, before you ask. Your bloods run till five; name a time and I "
        "am there."
    ),
    onset="The omeprazole started Sunday. The unsteadiness on the landing began yesterday.",
    severity="Unsteady crossing the landing, a hand on the airing cupboard. No falls, nothing hurt, gout quiet.",
    history="Epilepsy most of my life, settled on phenytoin, levels done at your neurology clinic.",
    medications="Phenytoin at night, the gout tablet — and the omeprazole since Sunday.",
    context="Retired; the surgery is one bus or a brisk walk, either is nothing.",
    gold=board_gold(NEUROLOGY),
    source="authored:p12_omeprazole_landing_ford",
)

WHINBROOK_SPLIT_INTAKE = (
    "Morning. A record matter: the out-of-hours doctor started me on omeprazole on Sunday for a burning "
    "stomach, and said my own surgery should have it on the list. So on the list it goes. Nothing else "
    "from me — the stomach is already easier."
)

WHINBROOK_RECALL_TEXT = (
    "Sidney Whinbrook again — I rang earlier about my list. I shall finish the job: since yesterday the "
    "landing has me unsteady, and I cross it with a hand on the airing cupboard like a man fording a "
    "stream. No falls. But it is new since the weekend, and it ought to be on my record today rather "
    "than left to drift. I am free all afternoon, any time before five."
)

# ══ THE FOURTEEN KIN CARRIERS ══════════════════════════════════════════════════════════════════════════════
# Dual-purpose callers (§5): each is a patient of the practice with their own routine matter, and in the
# SPLIT twin their intake also carries the symptom half of a relative's evidence. Canonical intake = the
# PLAIN twin's words, which is the routine matter alone (in the plain twin the claimant's own single call
# already carries everything). Same surname as their claimant, licensed by `kin_of` at registration.

pt_wadsholm_b = _caller(
    "pt_wadsholm_b",
    "Peter Wadsholm",
    52,
    "M",
    chart=(
        "Hypertension, controlled; annual review with bloods each spring.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Peter Wadsholm — I am due my yearly blood pressure check and the reminder came "
        "through. Could I get that booked in for whenever suits? Mornings are best; I do the school run "
        "at three."
    ),
    onset="Nothing new — it is the yearly check, off the reminder letter.",
    severity="I am well. It is routine.",
    history="Blood pressure tablets for six years, steady. Nothing else.",
    medications="The amlodipine, one a day.",
    context="I do the school run at three and drive my father about besides; mornings suit.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadsholm_bp_review",
)

WADSHOLM_B_SPLIT_INTAKE = (
    "Morning. Peter Wadsholm — two things, one mine, one not. Mine: I am due my yearly blood pressure "
    "check off the reminder letter, whenever suits, mornings best.\n\n"
    "The other: my dad, Harold Wadsholm, is on your books. He has gone wobbly on the stairs these last "
    "two mornings — holding the rail like a man on a ferry, and that is not him. He says it is nothing "
    "and he will not ring you himself. Could somebody put it on his file, or give him a ring? He is home "
    "all day, and if anyone does want him in, the level clinic does its work till five, as I understand."
)

pt_yarmead_b = _caller(
    "pt_yarmead_b",
    "Susan Yarmead",
    55,
    "F",
    chart=(
        "Hypothyroidism, stable on levothyroxine; annual bloods due shortly.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Susan Yarmead. Only my repeat, please — the levothyroxine — and could you tell me "
        "whether my yearly thyroid blood test is due yet? The chemist thought it might be. No hurry on "
        "either count."
    ),
    onset="Nothing new; the repeat has come round and the chemist thought the yearly bloods were due too.",
    severity="I am perfectly well. It is paperwork.",
    history="The thyroid, steady for years on the same dose.",
    medications="Levothyroxine, one hundred micrograms, every morning.",
    context="I look in on my father every day; I am flexible any afternoon.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarmead_levothyroxine",
)

YARMEAD_B_SPLIT_INTAKE = (
    "Hello, Susan Yarmead. My repeat, please — the levothyroxine — and a check on whether my yearly "
    "thyroid bloods are due.\n\n"
    "And while I have you: my father, Dennis Yarmead, on your books. I look in on him daily and since "
    "about Wednesday he is sleepy by mid-morning and steering round his furniture like the floor is "
    "moving. No falls, and he makes light of it, but it is new and I would rather it was written on his "
    "file today than laughed off. He is home all day if anyone wants him — and he can be brought in "
    "before five easily, I have the car."
)

pt_wadslund_b = _caller(
    "pt_wadslund_b",
    "Stanley Wadslund",
    86,
    "M",
    chart=(
        "Osteoarthritis of both knees; walks with a stick outdoors.",
        "Repeat medication: co-codamol 8/500 as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Stanley Wadslund. My knees, the usual — I am after a repeat of the co-codamol, and "
        "perhaps a routine look at the left knee whenever there is a gap in the diary. It is no worse "
        "than winter usually makes it."
    ),
    onset="Nothing new — the knees are the knees, and the repeat is due.",
    severity="The usual winter aching. Routine, nothing more.",
    history="The knees, years of them; a stick outdoors and no complaints indoors.",
    medications="The co-codamol when the stairs have been ambitious.",
    context="My wife and I are home all day; we take our outings to the surgery these days.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadslund_knees",
)

WADSLUND_B_SPLIT_INTAKE = (
    "Morning. Stanley Wadslund — the co-codamol repeat for my knees, please, and a routine look at the "
    "left one whenever the diary allows.\n\n"
    "And a word about my wife, Edith Wadslund, who is on your books: since Monday she has been walking "
    "like she is on a boat. I walk beside her with my arm out now. No falls — I see to that — but it "
    "is new this week and I want it on her record today. We are both free all day, and I know the "
    "bloods people work to five o'clock if anyone should want her."
)

pt_yarridge_b = _caller(
    "pt_yarridge_b",
    "Keith Yarridge",
    45,
    "M",
    chart=(
        "Asthma, well controlled on a combination inhaler; annual review due.",
        "Repeat medication: combination inhaler daily, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning — Keith Yarridge. The asthma review reminder came through, the yearly one. Can I book "
        "that in? Late afternoons work best around my shifts. Chest is fine, for the record."
    ),
    onset="Nothing new; it is the yearly asthma review off the reminder.",
    severity="Chest fine, inhaler barely touched. Routine.",
    history="Asthma since school, steady for years on the same inhaler.",
    medications="The purple inhaler daily and the blue one in my pocket.",
    context="Shift work; late afternoons suit, and I run my mother about besides.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarridge_asthma_review",
)

YARRIDGE_B_SPLIT_INTAKE = (
    "Morning — Keith Yarridge. Two things. Mine first: the yearly asthma review reminder came through, "
    "late afternoons best around my shifts.\n\n"
    "Second, my mum — Brenda Yarridge, she is with you. Whatever she rang you about this morning, what "
    "she will not have said is that she has been unsteady at the top of her stairs since Sunday — "
    "swaying at the turn, hand on the newel post. No falls, and she is not dizzy sitting down, and it "
    "is not sudden — it comes on over the day. But I want it on her file today. She is home all day and "
    "I can run her down at ten minutes' notice."
)

pt_wadsmead_b = _caller(
    "pt_wadsmead_b",
    "Carol Wadsmead",
    50,
    "F",
    chart=(
        "Raised cholesterol on last year's bloods; diet-managed, repeat bloods advised.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Carol Wadsmead. I am meant to have my cholesterol re-checked about now — the diet "
        "attempt, we shall see what it says. Could I book the blood test? Any day; I am on a half-day "
        "rota."
    ),
    onset="Nothing new — the re-check has come round, that is all.",
    severity="I am well. It is a routine blood test.",
    history="The cholesterol found last year; managing with the diet, allegedly.",
    medications="Nothing regular.",
    context="Half-day rota at work; I ferry my mother about on the free afternoons.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadsmead_cholesterol",
)

WADSMEAD_B_SPLIT_INTAKE = (
    "Hello, Carol Wadsmead. My cholesterol re-check wants booking — any day, half-day rota.\n\n"
    "And may I add a note to my mother's file — Ivy Wadsmead? Since Saturday she has been catching "
    "doorframes with her shoulder, veering, as if the hall had a camber put in. She laughs it off. No "
    "falls, but it is new this week and I want it written down today rather than filed under mothers "
    "being mothers. I am free from noon if she needs bringing in — I gather bloods run till five."
)

pt_yarroyd_b = _caller(
    "pt_yarroyd_b",
    "Ken Yarroyd",
    77,
    "M",
    chart=(
        "Gout, infrequent flares; on allopurinol between them.",
        "Repeat medication: allopurinol 200 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning, Ken Yarroyd. My allopurinol repeat, please — the gout tablet. Quiet on that front, "
        "touch wood. And whenever the yearly bloods for it are due, put me down at your convenience."
    ),
    onset="Nothing new; the repeat is due and the gout is quiet.",
    severity="No flare — the toe and I are on speaking terms. Routine.",
    history="Gout for a decade, settled on the daily tablet.",
    medications="Allopurinol, one a day.",
    context="Retired; home all day with the car on the drive.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarroyd_allopurinol",
)

YARROYD_B_SPLIT_INTAKE = (
    "Morning, Ken Yarroyd. The allopurinol repeat, please, and pencil the yearly bloods whenever they "
    "fall due.\n\n"
    "And one for my wife's file — Sheila Yarroyd. Since Friday she has gone wobbly on the garden step: "
    "both hands on the door frame, and I have taken the washing basket off her. She has not fallen and "
    "she will tell you she is fine. It is new this week and I want it noted today. We are home all day, "
    "car on the drive, and I know your bloods run to five if anyone should want her in."
)

pt_wadsridge_b = _caller(
    "pt_wadsridge_b",
    "Janet Wadsridge",
    58,
    "F",
    chart=(
        "Hypothyroidism, stable on levothyroxine.",
        "Repeat medication: levothyroxine 75 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — Janet Wadsridge. Just my levothyroxine repeat, please; the chemist says the "
        "authorisations have run out. There is no rush, I have a week's worth yet."
    ),
    onset="Nothing new; the repeat has run out of authorisations.",
    severity="Quite well. Paperwork, not a complaint.",
    history="The thyroid, steady for years on the same dose.",
    medications="Levothyroxine, seventy-five micrograms, each morning.",
    context="I do my mother's errands and lifts; free from lunchtime most days.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadsridge_levothyroxine",
)

WADSRIDGE_B_SPLIT_INTAKE = (
    "Hello — Janet Wadsridge. My levothyroxine repeat, please; the chemist says the authorisations have "
    "run out. No rush, a week's worth yet.\n\n"
    "And a note for my mother — Doris Wadsridge, on your list. Since the weekend she has gone clumsy "
    "with the teacups: two saucers chipped, and she sets things down wide of where she means. She calls "
    "it her age. It arrived over one weekend, which is not how age works, so I would like it on her "
    "file today. I am free from lunchtime to bring her in — the bloods go till five, I believe."
)

pt_yarsett_b = _caller(
    "pt_yarsett_b",
    "Jack Yarsett",
    83,
    "M",
    chart=(
        "Bilateral hearing aids; wax builds and wants clearing once or twice a year.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning, Jack Yarsett. My ears want doing again — the right one is all sea noises. Could I "
        "book the wax clearing with the nurse, whenever there is a slot? It is a nuisance, not an "
        "emergency."
    ),
    onset="The right ear has been filling up for a fortnight; it is the usual wax.",
    severity="Muffled hearing, nothing painful. Routine as ever.",
    history="Ears that make wax like a candle shop; cleared once or twice a year.",
    medications="Nothing regular.",
    context="Retired; my wife and I share the car and our diaries are empty.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarsett_ears",
)

YARSETT_B_SPLIT_INTAKE = (
    "Morning, Jack Yarsett. My ears want doing — the right one is all sea noises — so the wax clearing "
    "with the nurse whenever there is a slot.\n\n"
    "And put a line on my wife's record, would you — Mabel Yarsett. Since Saturday she is unsteady "
    "standing at the sink, washing up leaning on her forearms like a sailor at a rail. No falls, and "
    "she would not thank me for ringing, but it is new this week and it should be written down today. "
    "We are free all day with the car if anyone wants her in before the bloods finish at five."
)

pt_wadsroyd_b = _caller(
    "pt_wadsroyd_b",
    "Michael Wadsroyd",
    43,
    "M",
    chart=(
        "Hay fever, seasonal; managed with an antihistamine.",
        "Repeat medication: fexofenadine 120 mg in season.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning — Michael Wadsroyd. Could I get my fexofenadine repeat sorted before the season lands? "
        "Same as every year. That is genuinely the whole call."
    ),
    onset="Nothing new; the pollen is coming and I like to be armed.",
    severity="Nothing at present. Forward planning.",
    history="Hay fever since my teens; the tablet sees me through.",
    medications="Fexofenadine in season, nothing else.",
    context="On earlies this week, free from two; I do my father's lifts.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadsroyd_fexofenadine",
)

WADSROYD_B_SPLIT_INTAKE = (
    "Morning — Michael Wadsroyd. My fexofenadine repeat before the season lands, please, same as every "
    "year.\n\n"
    "And about my dad, Frank Wadsroyd, who is with you: I called round this morning and watched him "
    "sway on his top step like a man on a diving board. Since Monday, he admits, when pressed. No "
    "falls — yet, is my word for it. I want that on his file today, not at the next review. I am free "
    "from two and can have him to you inside twenty minutes; I know the level clinic runs to five."
)

pt_yarthwaite_b = _caller(
    "pt_yarthwaite_b",
    "Pauline Yarthwaite",
    59,
    "F",
    chart=(
        "Well; attends for the flu vaccination each autumn and little else.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Pauline Yarthwaite. I had a letter about a blood pressure check for my age group — the "
        "once-over at the nurse clinic. Could I book that in? Any day; I am between contracts and "
        "gloriously free."
    ),
    onset="Nothing new; the letter invited me and I am obeying it.",
    severity="Perfectly well. It is a screening check.",
    history="Nothing to speak of; the flu jab each autumn is my social calendar here.",
    medications="Nothing regular.",
    context="Between contracts, free every day; I drive my father where he needs to be.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarthwaite_nhs_check",
)

YARTHWAITE_B_SPLIT_INTAKE = (
    "Hello, Pauline Yarthwaite. The blood pressure once-over my letter invited me to — any day, I am "
    "between contracts.\n\n"
    "And my father, Cyril Yarthwaite, on your books: since Monday he veers in his hallway — sets off "
    "straight and arrives at the wall. I walked behind him this morning with my heart in my mouth. No "
    "falls, and he is proud, so he will make himself sound breezier than he is if you ring him. It "
    "wants writing on his file today. I am with him and can bring him in at any hour before your "
    "bloods finish at five."
)

pt_wadssett_b = _caller(
    "pt_wadssett_b",
    "Derek Wadssett",
    54,
    "M",
    chart=(
        "Lower back strain last year, resolved with physiotherapy; occasional stiffness.",
        "Repeat medication: ibuprofen gel as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning, Derek Wadssett. The back is stiffening up again with the van work — nothing like last "
        "year, just the warning creaks. Could I book a routine appointment about whether physio is "
        "worth another round? Any day after three."
    ),
    onset="Stiffness building over a few weeks with the driving. The usual pattern, milder.",
    severity="Creaks and stiffness, no sciatica, nothing down the leg. Routine.",
    history="The back strain last year, mended with physio; behaving since, mostly.",
    medications="The ibuprofen gel when it grumbles.",
    context="Van work all day; after three suits, and I run my father's errands besides.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadssett_back",
)

WADSSETT_B_SPLIT_INTAKE = (
    "Morning, Derek Wadssett. The back is creaking again with the van work — a routine appointment "
    "about another round of physio, any day after three.\n\n"
    "And a line for my dad's file — Albert Wadssett. Down the allotment Sunday he went wobbly, gave up "
    "on the bean canes and sat on the bench like a visitor while I carried his fork back. He has not "
    "fallen and he is making a joke of it. It is new, and I would like it written down today. I have "
    "the van and can fetch him to you before five whenever suits."
)

pt_yarwell_b = _caller(
    "pt_yarwell_b",
    "Alan Yarwell",
    46,
    "M",
    chart=(
        "Hypertension, controlled; annual review each summer.",
        "Repeat medication: ramipril 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning — Alan Yarwell. My ramipril repeat, please; the chemist flagged it. And if my summer "
        "review wants booking while we are at it, any early slot does me before work."
    ),
    onset="Nothing new; the repeat is due and the review is on the horizon.",
    severity="Well in myself. Routine housekeeping.",
    history="Blood pressure for five years, steady on the small dose.",
    medications="Ramipril, two and a half, each morning.",
    context="Work is round the corner; early slots suit, and I am my father's taxi.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarwell_ramipril",
)

YARWELL_B_SPLIT_INTAKE = (
    "Morning — Alan Yarwell. The ramipril repeat, please, and the summer review booked early if it is "
    "due.\n\n"
    "Also, my dad — George Yarwell, with you. Outside the paper shop on Sunday he stepped off the kerb "
    "like the road had moved and I caught his elbow. He says the pavement was at fault. It has been "
    "the same all weekend, and it is new, so I want it on his file today. I am round the corner and "
    "can have him with you in ten minutes any time before the bloods shut at five."
)

pt_wadsthwaite_b = _caller(
    "pt_wadsthwaite_b",
    "Nora Wadsthwaite",
    82,
    "F",
    chart=(
        "Dry eyes; on lubricant drops from the eye clinic.",
        "Repeat medication: carbomer eye gel nightly, hypromellose drops as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Nora Wadsthwaite. My eye drops, please — both sorts, the gel and the daytime ones. The "
        "chemist can have them ready Thursday as usual. That is all, thank you."
    ),
    onset="Nothing new; the drops have run their month.",
    severity="The eyes are their usual gritty selves. Routine.",
    history="Dry eyes for years; the drops keep the peace.",
    medications="The gel at night and the drops through the day.",
    context="Home all day with my husband; I drive us both, carefully.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadsthwaite_eye_drops",
)

WADSTHWAITE_B_SPLIT_INTAKE = (
    "Hello, Nora Wadsthwaite. My eye drops, please, both sorts, ready Thursday as usual.\n\n"
    "And I shall say what my husband will have left out when he rang you — Wilfred Wadsthwaite. Since "
    "Sunday the few steps from the bed to the chair have gone wobbly on him, and I walk them with him "
    "now, which neither of us thinks much of. No falls, because I am there. It wants writing on his "
    "record today. We are home all day and I can drive him in before the bloods finish at five."
)

pt_yarbrook_b = _caller(
    "pt_yarbrook_b",
    "Lynne Yarbrook",
    51,
    "F",
    chart=(
        "Migraine, occasional; managed with an over-the-counter triptan plan agreed at review.",
        "Repeat medication: sumatriptan 50 mg as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — Lynne Yarbrook. Could I get my sumatriptan repeat? Two or three migraines a season, "
        "same as ever, the plan works. No review needed unless you say so."
    ),
    onset="Nothing new; the repeat wants renewing before the next one lands.",
    severity="No migraine today. Housekeeping.",
    history="Migraines since my thirties, occasional, well handled with the plan.",
    medications="Sumatriptan when needed, nothing daily.",
    context="Free after twelve most days; I am my mother's lift.",
    gold=_routine_gold(),
    source="authored:p12_kin_yarbrook_sumatriptan",
)

YARBROOK_B_SPLIT_INTAKE = (
    "Hello — Lynne Yarbrook. My sumatriptan repeat, please, the usual arrangement.\n\n"
    "And about my mother, Peggy Yarbrook, who is on your list: at the bus stop this morning she was "
    "swaying standing still and had to take the rail of the shelter. I marched her home. She has been "
    "like it since Sunday and told nobody. No falls, but I want it on her file today, in words she "
    "cannot laugh off. I am free after twelve and can bring her in before the bloods close at five."
)

# ══ THE THIRTY HOLDERS ═════════════════════════════════════════════════════════════════════════════════════
# Routine neurology patients sitting in this afternoon's returned-cancellation slots. Holders never call —
# their intake is what they say if a desk RINGS them (`reprioritization._caller`'s holder convention), and
# none of them pre-consents to being moved: each has an ordinary, human reason to want today.

pt_whinby = _caller(
    "pt_whinby",
    "Dorothy Whinby",
    72,
    "F",
    chart=(
        "Migraine, long-standing; on propranolol prophylaxis, well settled.",
        "Yearly neurology review of the prophylaxis; last review over a year ago.",
        "Repeat medication: propranolol 80 mg modified-release daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My migraine review is this afternoon — the yearly one on the tablets. My daughter has taken a "
        "half-day specially to bring me in, so the time they gave me works out just right."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="The heads have been quiet for months. It is routine.",
    history="Migraines since my thirties, settled on the propranolol, reviewed once a year.",
    medications="The propranolol, one a day.",
    context="My daughter booked a half-day at work to drive me in this afternoon.",
    gold=_holder_gold(),
    source="authored:p12_holder_migraine_prophylaxis",
)

pt_yarcliffe = _caller(
    "pt_yarcliffe",
    "Eric Yarcliffe",
    68,
    "M",
    chart=(
        "Essential tremor, mild; on propranolol, stable.",
        "Neurology follow-up yearly; handwriting and cup-holding steady at last review.",
        "Repeat medication: propranolol 40 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I have my tremor follow-up this afternoon. I booked the day off work for it — the first "
        "appointment they have had for me in months, so I am glad of it."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="The shake is its usual mild self. Routine.",
    history="The tremor for a decade, steady on the tablets.",
    medications="Propranolol, morning and evening.",
    context="I took the whole day off work for the appointment.",
    gold=_holder_gold(),
    source="authored:p12_holder_tremor_followup",
)

pt_zealcote = _caller(
    "pt_zealcote",
    "Muriel Zealcote",
    75,
    "F",
    chart=(
        "Epilepsy, seizure-free many years on lamotrigine.",
        "Annual epilepsy review at the neurology clinic; last review over a year ago.",
        "Repeat medication: lamotrigine 100 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly epilepsy check is this afternoon. My neighbour has arranged her shopping run around "
        "driving me in, so the timing is all sorted between us."
    ),
    onset="Nothing new; it is the yearly check.",
    severity="Not a flicker all year. Routine.",
    history="Epilepsy long settled on the lamotrigine, seen yearly.",
    medications="Lamotrigine, morning and night.",
    context="My neighbour drives me; she has planned her day around this afternoon.",
    gold=_holder_gold(),
    source="authored:p12_holder_epilepsy_annual_lamotrigine",
)

pt_wadsby = _caller(
    "pt_wadsby",
    "Clifford Wadsby",
    66,
    "M",
    chart=(
        "Peripheral neuropathy, stable; on amitriptyline for night symptoms.",
        "Annual neurology review; feet checked, doses steady at last review.",
        "Repeat medication: amitriptyline 25 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "My neuropathy review is this afternoon. I swapped my shift to the early turn specially, so I "
        "finish at two and come straight over. It took some arranging."
    ),
    onset="Nothing new; it is the annual review.",
    severity="The feet are their usual tingling selves at night. Routine.",
    history="The neuropathy for years, steady on the night tablet.",
    medications="Amitriptyline at night.",
    context="Swapped to the early turn specially; I finish at two today.",
    gold=_holder_gold(),
    source="authored:p12_holder_neuropathy_annual",
)

pt_whincliffe = _caller(
    "pt_whincliffe",
    "Beryl Whincliffe",
    78,
    "F",
    chart=(
        "Chronic tension-type headache; managed with a review plan at the neurology clinic.",
        "Follow-up yearly; diary reviewed, plan unchanged at last visit.",
        "Repeat medication: paracetamol 1 g as required, within the plan's limits.",
        "No known drug allergies.",
    ),
    intake=(
        "My headache clinic follow-up is this afternoon. The ring-and-ride is booked for it, there and "
        "back — cancel after nine in the morning and you pay for the seat regardless, so I am rather "
        "committed."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="The heads are no worse than their usual. Routine.",
    history="The headaches for years, managed with the clinic's plan.",
    medications="Paracetamol within the plan, nothing else.",
    context="Taxi booked both ways; cancelling after nine costs me the fare.",
    gold=_holder_gold(),
    source="authored:p12_holder_headache_followup",
)

pt_yarcote = _caller(
    "pt_yarcote",
    "Douglas Yarcote",
    73,
    "M",
    chart=(
        "Restless legs syndrome; on ropinirole, settled.",
        "Yearly medication review at the neurology clinic.",
        "Repeat medication: ropinirole 1 mg in the evening.",
        "No known drug allergies.",
    ),
    intake=(
        "My restless legs review is this afternoon — the yearly one. I have arranged bowls around it; "
        "the club meets at five and the timing works a treat as booked."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="The legs behave on the tablet. Routine.",
    history="Restless legs for years, settled on the evening dose.",
    medications="Ropinirole of an evening.",
    context="Bowls at five; the appointment as booked fits neatly before it.",
    gold=_holder_gold(),
    source="authored:p12_holder_restless_legs",
)

pt_zealden = _caller(
    "pt_zealden",
    "Audrey Zealden",
    70,
    "F",
    chart=(
        "Bell's palsy last year, fully recovered; discharge review outstanding.",
        "Neurology to confirm discharge at a final face-to-face review.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my final check on the Bell's palsy this afternoon — the discharge one, where they sign "
        "me off. My grandson has swapped his lunch break to drive me; he goes back at three."
    ),
    onset="Nothing new; the face has been right for months.",
    severity="Fully recovered. It is the sign-off visit.",
    history="The Bell's palsy last year, mended completely.",
    medications="Nothing regular.",
    context="My grandson swapped his lunch break to do the driving today.",
    gold=_holder_gold(),
    source="authored:p12_holder_bells_palsy_discharge",
)

pt_wadscliffe = _caller(
    "pt_wadscliffe",
    "Raymond Wadscliffe",
    77,
    "M",
    chart=(
        "Parkinson's disease, early and stable; on co-careldopa, doses steady.",
        "Routine neurology medication review; last review a year ago.",
        "Repeat medication: co-careldopa 25/100 three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My Parkinson's review is this afternoon — the routine one, the doses have been steady all "
        "year. My carer comes on Thursdays and today, so the escort is arranged around it."
    ),
    onset="Nothing new; it is the routine review.",
    severity="Steady on the tablets, same as all year. Routine.",
    history="Parkinson's a few years, stable on the same doses.",
    medications="Co-careldopa, three times a day.",
    context="My carer's visit today is timed around the appointment.",
    gold=_holder_gold(),
    source="authored:p12_holder_parkinsons_review",
)

pt_whincote = _caller(
    "pt_whincote",
    "Gwen Whincote",
    64,
    "F",
    chart=(
        "Migraine with aura; on topiramate prophylaxis, well settled.",
        "Yearly neurology review with care plan renewal; plan expires shortly.",
        "Repeat medication: topiramate 50 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My migraine review is this afternoon, the one where the care plan gets renewed. I have "
        "arranged to work from home today so I can slip out for it — the office would have made it "
        "impossible."
    ),
    onset="Nothing new; the plan renewal has come round.",
    severity="The migraines are well behaved on the tablets. Routine.",
    history="Migraine with aura for years, settled on the topiramate.",
    medications="Topiramate, morning and night.",
    context="Working from home today specifically so the afternoon time works.",
    gold=_holder_gold(),
    source="authored:p12_holder_migraine_care_plan",
)

pt_yarden = _caller(
    "pt_yarden",
    "Herbert Yarden",
    81,
    "M",
    chart=(
        "Epilepsy, seizure-free many years on levetiracetam.",
        "Annual epilepsy review at the neurology clinic.",
        "Repeat medication: levetiracetam 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly epilepsy review is this afternoon. My son drives over from two towns away for these "
        "— he set off this morning, so we are rather invested in the time as given."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="Quiet all year. Routine.",
    history="Epilepsy long settled on the levetiracetam.",
    medications="Levetiracetam, morning and night.",
    context="My son is already on the road from two towns away to take me.",
    gold=_holder_gold(),
    source="authored:p12_holder_epilepsy_annual_lev",
)

pt_zealdijk = _caller(
    "pt_zealdijk",
    "Kathleen Zealdijk",
    69,
    "F",
    chart=(
        "Essential tremor; on primidone at low dose, stable.",
        "Neurology follow-up yearly.",
        "Repeat medication: primidone 62.5 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "My tremor follow-up is this afternoon. I have my sister staying and she leaves tomorrow — she "
        "is my lift and my moral support, so today is the day it all works."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="The hands are steady enough on the tablet. Routine.",
    history="The tremor for years, settled on the low dose.",
    medications="Primidone at night.",
    context="My sister leaves tomorrow; she is driving me this afternoon.",
    gold=_holder_gold(),
    source="authored:p12_holder_tremor_primidone",
)

pt_wadscote = _caller(
    "pt_wadscote",
    "Maurice Wadscote",
    74,
    "M",
    chart=(
        "Peripheral neuropathy from years of diabetes; symptoms stable.",
        "Annual neurology review alongside the diabetic foot checks.",
        "Repeat medication: duloxetine 60 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My neuropathy review is this afternoon. The community transport minibus is booked — they only "
        "run my estate on Thursdays and today, so the slot they gave me was a small miracle."
    ),
    onset="Nothing new; it is the annual review.",
    severity="The feet are their usual selves. Routine.",
    history="The neuropathy with the diabetes, stable for years.",
    medications="Duloxetine daily, and my diabetes tablets.",
    context="The market-day bus gets me in today; it does not come out my way again till next week.",
    gold=_holder_gold(),
    source="authored:p12_holder_neuropathy_duloxetine",
)

pt_whinden = _caller(
    "pt_whinden",
    "Olive Whinden",
    79,
    "F",
    chart=(
        "Chronic headache, stable under the neurology clinic's plan.",
        "Follow-up yearly; diary reviewed at each visit.",
        "Repeat medication: paracetamol as required within the plan.",
        "No known drug allergies.",
    ),
    intake=(
        "My headache clinic follow-up is this afternoon. My friend from church does the driving and "
        "she has choir at six, so the afternoon time suits us both nicely."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="No worse than usual. Routine.",
    history="The headaches managed at the clinic for years.",
    medications="Paracetamol within the plan.",
    context="My friend from church drives; she has choir at six.",
    gold=_holder_gold(),
    source="authored:p12_holder_headache_church_lift",
)

pt_yardijk = _caller(
    "pt_yardijk",
    "Trevor Yardijk",
    62,
    "M",
    chart=(
        "Restless legs syndrome; on pramipexole, settled.",
        "Yearly medication review at the neurology clinic.",
        "Repeat medication: pramipexole 0.088 mg in the evening.",
        "No known drug allergies.",
    ),
    intake=(
        "My restless legs review is this afternoon. I am on nights this week — the afternoon slot "
        "means I can come in after my sleep and still make the shift, which took some working out."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="The legs are quiet on the tablet. Routine.",
    history="Restless legs for years, settled on the evening dose.",
    medications="Pramipexole of an evening.",
    context="On nights; the afternoon time threads between my sleep and my shift.",
    gold=_holder_gold(),
    source="authored:p12_holder_restless_legs_nights",
)

pt_zealdon = _caller(
    "pt_zealdon",
    "Phyllis Zealdon",
    76,
    "F",
    chart=(
        "Migraine, long-standing; on amitriptyline prophylaxis, settled.",
        "Yearly neurology review of the prophylaxis.",
        "Repeat medication: amitriptyline 20 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "My migraine review is this afternoon — the yearly tablets one. My son-in-law is on a rest day "
        "and doing the driving, which spares me two buses and a wait in the rain."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="The heads have been kind this year. Routine.",
    history="Migraines settled for years on the night tablet.",
    medications="Amitriptyline at night.",
    context="My son-in-law's rest day is today; he is my lift.",
    gold=_holder_gold(),
    source="authored:p12_holder_migraine_amitriptyline",
)

pt_woldmere = _caller(
    "pt_woldmere",
    "Bernard Woldmere",
    71,
    "M",
    chart=(
        "Epilepsy, seizure-free many years on levetiracetam.",
        "Annual epilepsy review at the neurology clinic.",
        "Repeat medication: levetiracetam 750 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly epilepsy review is this afternoon. I have my grandson's sports day at eleven and "
        "the review after — the one day this month the two halves of my diary agree."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="Not a murmur all year. Routine.",
    history="Epilepsy long settled on the levetiracetam.",
    medications="Levetiracetam, morning and night.",
    context="Sports day in the morning, the review after; the day is carefully packed.",
    gold=_holder_gold(),
    source="authored:p12_holder_epilepsy_annual_woldmere",
)

pt_wyredale = _caller(
    "pt_wyredale",
    "Winifred Wyredale",
    80,
    "F",
    chart=(
        "Parkinson's disease, stable; on co-careldopa, doses steady.",
        "Routine neurology medication review.",
        "Repeat medication: co-careldopa 25/100 three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My Parkinson's review is this afternoon, the routine one. My niece has taken the afternoon "
        "off for it — she banks these hours weeks ahead, bless her."
    ),
    onset="Nothing new; it is the routine review.",
    severity="Steady on the tablets. Routine.",
    history="Parkinson's for some years, stable doses throughout.",
    medications="Co-careldopa, three times a day.",
    context="My niece booked this afternoon off weeks ago to bring me.",
    gold=_holder_gold(),
    source="authored:p12_holder_parkinsons_wyredale",
)

pt_welkholt = _caller(
    "pt_welkholt",
    "Geoffrey Welkholt",
    67,
    "M",
    chart=(
        "Essential tremor, mild; on propranolol, stable.",
        "Neurology follow-up yearly.",
        "Repeat medication: propranolol 40 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tremor follow-up is this afternoon. I have arranged the allotment watering rota around it "
        "— my neighbour covers me today and I cover him the weekend, all very solemn."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="The shake is mild and steady. Routine.",
    history="The tremor for years, settled on the tablets.",
    medications="Propranolol, morning and evening.",
    context="The allotment rota is swapped around this afternoon's time.",
    gold=_holder_gold(),
    source="authored:p12_holder_tremor_welkholt",
)

pt_wrenmarsh = _caller(
    "pt_wrenmarsh",
    "Marjorie Wrenmarsh",
    73,
    "F",
    chart=(
        "Peripheral neuropathy, idiopathic; stable on gabapentin.",
        "Annual neurology review.",
        "Repeat medication: gabapentin 300 mg three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My neuropathy review is this afternoon. My husband has moved his hospital volunteering to the "
        "morning so he can drive me — we run a tight ship on Wednesdays."
    ),
    onset="Nothing new; it is the annual review.",
    severity="The feet tingle as they always have. Routine.",
    history="The neuropathy for years, steady on the gabapentin.",
    medications="Gabapentin, three times a day.",
    context="My husband rearranged his volunteering to do this afternoon's lift.",
    gold=_holder_gold(),
    source="authored:p12_holder_neuropathy_wrenmarsh",
)

pt_wickfirth = _caller(
    "pt_wickfirth",
    "Russell Wickfirth",
    65,
    "M",
    chart=(
        "Chronic tension-type headache; managed under the neurology clinic's plan.",
        "Follow-up yearly.",
        "Repeat medication: paracetamol as required within the plan.",
        "No known drug allergies.",
    ),
    intake=(
        "My headache follow-up is this afternoon. I have a job interview Friday and wanted this out of "
        "the way first — the afternoon slot lets me keep the week's plan intact."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="The heads are their usual manageable selves. Routine.",
    history="The headaches for years, managed with the plan.",
    medications="Paracetamol within the plan.",
    context="Interview Friday; today's time keeps the week orderly.",
    gold=_holder_gold(),
    source="authored:p12_holder_headache_wickfirth",
)

pt_wetherholt = _caller(
    "pt_wetherholt",
    "Eileen Wetherholt",
    78,
    "F",
    chart=(
        "Migraine, long-standing; on candesartan prophylaxis, settled.",
        "Yearly neurology review with care plan renewal.",
        "Repeat medication: candesartan 8 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My migraine review is this afternoon, with the plan renewal. My daughter has the baby's "
        "christening list to do in town anyway, so she is dropping me and collecting me — all arranged."
    ),
    onset="Nothing new; the renewal has come round.",
    severity="The migraines are settled. Routine.",
    history="Migraines settled for years on the daily tablet.",
    medications="Candesartan daily.",
    context="My daughter's town errands are arranged around dropping and collecting me.",
    gold=_holder_gold(),
    source="authored:p12_holder_migraine_wetherholt",
)

pt_winsgarth = _caller(
    "pt_winsgarth",
    "Victor Winsgarth",
    76,
    "M",
    chart=(
        "Restless legs syndrome; on ropinirole, settled.",
        "Yearly medication review at the neurology clinic.",
        "Repeat medication: ropinirole 2 mg in the evening.",
        "No known drug allergies.",
    ),
    intake=(
        "My restless legs review is this afternoon. My neighbour drives me and he has his own "
        "chiropody at four next door — we make one expedition of it, very economical."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="The legs are quiet on the tablet. Routine.",
    history="Restless legs for years, settled on the evening dose.",
    medications="Ropinirole of an evening.",
    context="My neighbour's chiropody at four makes today's trip a shared one.",
    gold=_holder_gold(),
    source="authored:p12_holder_restless_legs_winsgarth",
)

pt_wharfeholm = _caller(
    "pt_wharfeholm",
    "Constance Wharfeholm",
    82,
    "F",
    chart=(
        "Epilepsy, seizure-free many years on sodium valproate.",
        "Annual epilepsy review at the neurology clinic.",
        "Repeat medication: sodium valproate 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly epilepsy review is this afternoon. The warden here books the shared car a week "
        "ahead, and it is booked, so I am all set for the time they gave me."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="All quiet this year. Routine.",
    history="Epilepsy long settled on the valproate.",
    medications="The valproate, morning and night.",
    context="The sheltered housing's shared car is booked for this afternoon.",
    gold=_holder_gold(),
    source="authored:p12_holder_epilepsy_annual_wharfeholm",
)

pt_woldenby = _caller(
    "pt_woldenby",
    "Malcolm Woldenby",
    70,
    "M",
    chart=(
        "Bell's palsy in the autumn, recovered; discharge review outstanding.",
        "Neurology to confirm discharge at a final review.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my Bell's palsy sign-off this afternoon — the face has been right for months and this "
        "is the formal goodbye. My wife has arranged her book club around driving me, which I shall "
        "be hearing about either way."
    ),
    onset="Nothing new; the face has been right for months.",
    severity="Fully recovered. It is the discharge visit.",
    history="The Bell's palsy in the autumn, mended completely.",
    medications="Nothing regular.",
    context="My wife's book club is rearranged around this afternoon's lift.",
    gold=_holder_gold(),
    source="authored:p12_holder_bells_palsy_woldenby",
)

pt_wexmoor = _caller(
    "pt_wexmoor",
    "Rita Wexmoor",
    68,
    "F",
    chart=(
        "Essential tremor; on propranolol, stable.",
        "Neurology follow-up yearly.",
        "Repeat medication: propranolol 80 mg modified-release daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tremor follow-up is this afternoon. I mind my granddaughter until noon and her mother "
        "takes over after — the afternoon time is the one hinge the whole day swings on."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="The hands are steady enough. Routine.",
    history="The tremor for years, settled on the tablet.",
    medications="Propranolol, one a day.",
    context="Granddaughter till noon, handover after; the afternoon time is the hinge.",
    gold=_holder_gold(),
    source="authored:p12_holder_tremor_wexmoor",
)

pt_yewbank = _caller(
    "pt_yewbank",
    "Donald Yewbank",
    75,
    "M",
    chart=(
        "Peripheral neuropathy from years of diabetes; stable.",
        "Annual neurology review.",
        "Repeat medication: duloxetine 30 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My neuropathy review is this afternoon. My son does the fish run to the coast Tuesdays and "
        "is back by one, so he drops me at the surgery on his way home — tradition now."
    ),
    onset="Nothing new; it is the annual review.",
    severity="The feet are their usual selves. Routine.",
    history="The neuropathy with the diabetes, stable for years.",
    medications="Duloxetine daily, and the diabetes tablets.",
    context="My son's fish run gets him back by one; he drops me on the way home.",
    gold=_holder_gold(),
    source="authored:p12_holder_neuropathy_yewbank",
)

pt_yeldmere = _caller(
    "pt_yeldmere",
    "Annie Yeldmere",
    83,
    "F",
    chart=(
        "Chronic headache, stable under the neurology clinic's plan.",
        "Follow-up yearly.",
        "Repeat medication: paracetamol as required within the plan.",
        "No known drug allergies.",
    ),
    intake=(
        "My headache follow-up is this afternoon. The home's minibus does the surgery run once a week "
        "and today is the day — the driver has me on his list already."
    ),
    onset="Nothing new; the follow-up has come round.",
    severity="No worse than usual. Routine.",
    history="The headaches managed at the clinic for years.",
    medications="Paracetamol within the plan.",
    context="The care home minibus runs to the surgery today; I am on the list.",
    gold=_holder_gold(),
    source="authored:p12_holder_headache_yeldmere",
)

pt_yorebeck = _caller(
    "pt_yorebeck",
    "Clive Yorebeck",
    63,
    "M",
    chart=(
        "Restless legs syndrome; on pramipexole, settled.",
        "Yearly medication review at the neurology clinic.",
        "Repeat medication: pramipexole 0.18 mg in the evening.",
        "No known drug allergies.",
    ),
    intake=(
        "My restless legs review is this afternoon. I drive a delivery round and traded routes with a "
        "mate so I finish at half twelve today — the afternoon time is why the trade was worth it."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="The legs behave on the tablet. Routine.",
    history="Restless legs for years, settled on the evening dose.",
    medications="Pramipexole of an evening.",
    context="Traded delivery routes to finish at half twelve for the appointment.",
    gold=_holder_gold(),
    source="authored:p12_holder_restless_legs_yorebeck",
)

pt_yewholt = _caller(
    "pt_yewholt",
    "Nell Yewholt",
    74,
    "F",
    chart=(
        "Epilepsy, seizure-free many years on lamotrigine.",
        "Annual epilepsy review at the neurology clinic.",
        "Repeat medication: lamotrigine 150 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly epilepsy review is this afternoon. My sister and I do our big shop after these — "
        "she drives over specially and we make the day of it, appointment first."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="Quiet all year. Routine.",
    history="Epilepsy long settled on the lamotrigine.",
    medications="Lamotrigine, morning and night.",
    context="My sister drives over specially; the appointment anchors our day out.",
    gold=_holder_gold(),
    source="authored:p12_holder_epilepsy_annual_yewholt",
)

pt_yarnfold = _caller(
    "pt_yarnfold",
    "Percy Yarnfold",
    79,
    "M",
    chart=(
        "Parkinson's disease, stable; on co-careldopa, doses steady.",
        "Routine neurology medication review.",
        "Repeat medication: co-careldopa 25/100 four times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My Parkinson's review is this afternoon, the routine one. My daughter has taken her flexi "
        "hours for it and the dog is booked into the neighbour's — the whole street knows my "
        "appointment time."
    ),
    onset="Nothing new; it is the routine review.",
    severity="Steady on the tablets. Routine.",
    history="Parkinson's for some years, stable on the same doses.",
    medications="Co-careldopa, four times a day.",
    context="My daughter's flexi hours and the neighbour's dog-minding are both set for this afternoon.",
    gold=_holder_gold(),
    source="authored:p12_holder_parkinsons_yarnfold",
)

# ══ THE THREE DECOYS ═══════════════════════════════════════════════════════════════════════════════════════
# Each SOUNDS urgent and is correctly served without a bump (§6): an open routine booking is the right
# answer once the defusing fact is on the table. Ronald Wadsbrook's defusal arrives in a SECOND call in the
# split twin (his wife's), so aggregation can cancel urgency there, not only create it.

pt_yarby = _caller(
    "pt_yarby",
    "Maureen Yarby",
    70,
    "F",
    chart=(
        "Epilepsy, seizure-free many years on phenytoin.",
        "Phenytoin levels monitored at the practice's neurology clinic; last level three "
        "weeks ago, in range.",
        "Repeat medication: phenytoin 300 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I want to be seen today — I have worked myself into a state and I shall admit it "
        "up front.\n\n"
        "There was a piece in the paper about tablet batches being recalled, and my epilepsy tablet was "
        "in the same photograph. I have checked the boxes with the chemist this morning and mine is not "
        "one of the recalled batches — he was very good about it — and I have started nothing new, "
        "stopped nothing, and I feel perfectly well, not so much as a wobble. My level was done three "
        "weeks back and the clinic said it was spot on.\n\n"
        "So there is nothing actually wrong, and I know it, but I should like a proper sit-down with "
        "somebody to talk me off the ceiling — whenever there is an ordinary appointment going."
    ),
    onset="The newspaper piece was yesterday. Nothing about me has changed at all.",
    severity="No symptoms whatsoever — no wobbles, no double sight, nothing. It is my nerves, not my legs.",
    history="Epilepsy long settled on the phenytoin, levels done at your neurology clinic, all in range.",
    medications="The phenytoin at night, nothing else, nothing new — the chemist checked the boxes with me.",
    context="Retired, free any day this week or next; I would rather a calm word than a rushed one.",
    gold=_routine_gold(),
    source="authored:p12_decoy_recall_scare_defused",
)

pt_zealcliffe = _caller(
    "pt_zealcliffe",
    "Ted Zealcliffe",
    63,
    "M",
    chart=(
        "Hypertension, controlled on losartan; annual review each autumn.",
        "Repeat medication: losartan 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I had better tell you this properly, though I suspect I know the ending.\n\n"
        "Yesterday evening I came over dizzy — properly dizzy, hold-the-banister dizzy — getting out of "
        "a hot bath I had run after a day up the ladder painting the soffits. It lasted a minute and "
        "went. The pharmacy's nurse clinic was still open so I walked over and she looked me over "
        "there and then: pulse steady, blood pressure fine, nothing amiss, told me it had every look "
        "of a hot bath on an empty stomach and to book a routine once-over with my own surgery.\n\n"
        "Nothing since — I slept well and walked the dog this morning. So: the routine once-over, "
        "please, whenever it can be fitted."
    ),
    onset="Once, yesterday evening, out of a hot bath after a day up the ladder. Nothing since.",
    severity="One dizzy minute, gone by itself. The nurse found pulse and pressure fine last evening.",
    history="Blood pressure tablets for years, otherwise well. Never had anything of this sort before.",
    medications="Losartan, one a day.",
    context="Semi-retired decorator; any day suits for a routine appointment.",
    gold=_routine_gold(),
    source="authored:p12_decoy_hot_bath_dizzy_defused",
)

pt_wadsbrook = _caller(
    "pt_wadsbrook",
    "Ronald Wadsbrook",
    74,
    "M",
    chart=(
        "Hypertension, controlled on amlodipine.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I have come over that giddy this week that I want somebody to look at me today, and "
        "I shall give you the household's full verdict while I am at it.\n\n"
        "We are redecorating — I have been up and down ladders in paint fumes all week and, Vera says, "
        "skipping my lunches to get the ceiling done. Our daughter-in-law is a nurse and she looked me "
        "over last night: steady as a rock standing on one leg, pulse fine, and her ruling was paint "
        "fumes on an empty stomach and eat your dinner. And I have felt better since dinner, if I am "
        "honest.\n\n"
        "So the nurse in the family says a routine look-over is all it wants, and Vera agrees, and I "
        "know better than to out-vote the pair of them. Routine it is — whenever you can fit me."
    ),
    onset="Giddy on and off this week, up ladders in paint fumes, lunches skipped. Better since eating properly.",
    severity="Giddy spells that pass; steady on one leg when the nurse tried me. Nothing since dinner.",
    history="Blood pressure tablets for years, otherwise sound. Never a day's dizziness before this week.",
    medications="Amlodipine, one a day.",
    context="Redecorating at home; Vera and I are in all week, any routine slot does.",
    gold=_routine_gold(),
    source="authored:p12_decoy_paint_fumes_defused",
)

#: Ronald in the SPLIT twin: the urgent-sounding half alone — his wife's call carries the defusal.
WADSBROOK_SPLIT_INTAKE = (
    "Morning. I have come over that giddy this week that I want somebody to look at me today, truth be "
    "told.\n\n"
    "It comes on out of nowhere — I have had to sit down on the stairs twice, and once in the shed. I "
    "am not a man who sits down in sheds. I take the blood pressure tablet and I have never had a "
    "day's dizziness in my life before this week. Today, if you can manage it."
)

pt_wadsbrook_b = _caller(
    "pt_wadsbrook_b",
    "Vera Wadsbrook",
    73,
    "F",
    chart=(
        "Osteoarthritis of the knees; on topical treatment.",
        "Repeat medication: ibuprofen gel as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Vera Wadsbrook. Only my knee gel wants repeating — the ibuprofen one, the big tube. "
        "The chemist can have it with my usual order. That is everything, thank you."
    ),
    onset="Nothing new; the tube is nearly out.",
    severity="The knees are the knees. Routine.",
    history="The knees, years of them, managed with the gel and common sense.",
    medications="The ibuprofen gel, as needed.",
    context="Home all week — we are mid-redecoration, which is a saga in itself.",
    gold=_routine_gold(),
    source="authored:p12_kin_wadsbrook_knee_gel",
)

VERA_SPLIT_INTAKE = (
    "Hello, Vera Wadsbrook. My knee gel wants repeating — the ibuprofen one, the big tube, with my "
    "usual order.\n\n"
    "And I gather my husband Ronald has been on to you this morning sounding like a man at death's "
    "door. For the record: we are redecorating, he has been up and down ladders in paint fumes all "
    "week and skipping his lunches to get the ceiling done. Our daughter-in-law is a nurse and looked "
    "him over last night — steady as a rock on one leg, pulse fine, her ruling was paint fumes on an "
    "empty stomach and eat your dinner. He has been right as rain since he ate. A routine look-over "
    "will do him nicely; do not let him talk you into more."
)

# ══ THE BOARD SKELETON (shared by both twins byte-for-byte) ════════════════════════════════════════════════
#: `(claimant, holder, provider, slot_hhmm, decisive_fact, standing_reason)` — thirty contests, eight
#: returned-cancellation slots per hosted list (six on the fourth), every slot an afternoon follow-up cell
#: strictly before the 17:00 deadline every claimant's evidence states as fact.
_CONTEST_TABLE: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "pt_wadsholm",
        "pt_whinby",
        "dr_woldbeck",
        "13:00",
        "omeprazole",
        "Migraine prophylaxis review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinlund",
        "pt_yarcliffe",
        "dr_woldbeck",
        "13:20",
        "cimetidine",
        "Essential tremor follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarmead",
        "pt_zealcote",
        "dr_woldbeck",
        "13:40",
        "build-up drinks",
        "Annual epilepsy review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealridge",
        "pt_wadsby",
        "dr_woldbeck",
        "14:40",
        "omeprazole",
        "Peripheral neuropathy annual review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadslund",
        "pt_whincliffe",
        "dr_woldbeck",
        "15:00",
        "omeprazole",
        "Chronic headache follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinmead",
        "pt_yarcote",
        "dr_woldbeck",
        "15:20",
        "cimetidine",
        "Restless legs medication review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarridge",
        "pt_zealden",
        "dr_woldbeck",
        "16:20",
        "omeprazole",
        "Bell's palsy discharge review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealroyd",
        "pt_wadscliffe",
        "dr_woldbeck",
        "16:40",
        "build-up drinks",
        "Parkinson's routine medication review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadsmead",
        "pt_whincote",
        "dr_wyrebank",
        "13:00",
        "omeprazole",
        "Migraine review and care plan renewal (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinridge",
        "pt_yarden",
        "dr_wyrebank",
        "13:20",
        "omeprazole",
        "Annual epilepsy review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarroyd",
        "pt_zealdijk",
        "dr_wyrebank",
        "13:40",
        "cimetidine",
        "Essential tremor follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealsett",
        "pt_wadscote",
        "dr_wyrebank",
        "14:40",
        "omeprazole",
        "Peripheral neuropathy annual review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadsridge",
        "pt_whinden",
        "dr_wyrebank",
        "15:00",
        "build-up drinks",
        "Chronic headache follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinroyd",
        "pt_yardijk",
        "dr_wyrebank",
        "15:20",
        "omeprazole",
        "Restless legs medication review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarsett",
        "pt_zealdon",
        "dr_wyrebank",
        "16:20",
        "cimetidine",
        "Migraine prophylaxis review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealthwaite",
        "pt_woldmere",
        "dr_wyrebank",
        "16:40",
        "omeprazole",
        "Annual epilepsy review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadsroyd",
        "pt_wyredale",
        "dr_yewdale",
        "13:00",
        "omeprazole",
        "Parkinson's routine medication review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinsett",
        "pt_welkholt",
        "dr_yewdale",
        "13:20",
        "build-up drinks",
        "Essential tremor follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarthwaite",
        "pt_wrenmarsh",
        "dr_yewdale",
        "13:40",
        "omeprazole",
        "Peripheral neuropathy annual review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealwell",
        "pt_wickfirth",
        "dr_yewdale",
        "14:40",
        "cimetidine",
        "Chronic headache follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadssett",
        "pt_wetherholt",
        "dr_yewdale",
        "15:00",
        "omeprazole",
        "Migraine review and care plan renewal (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinthwaite",
        "pt_winsgarth",
        "dr_yewdale",
        "15:20",
        "build-up drinks",
        "Restless legs medication review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarwell",
        "pt_wharfeholm",
        "dr_yewdale",
        "16:20",
        "omeprazole",
        "Annual epilepsy review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealbrook",
        "pt_woldenby",
        "dr_yewdale",
        "16:40",
        "cimetidine",
        "Bell's palsy discharge review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadsthwaite",
        "pt_wexmoor",
        "dr_winmarsh",
        "13:00",
        "omeprazole",
        "Essential tremor follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinwell",
        "pt_yewbank",
        "dr_winmarsh",
        "13:20",
        "omeprazole",
        "Peripheral neuropathy annual review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_yarbrook",
        "pt_yeldmere",
        "dr_winmarsh",
        "13:40",
        "omeprazole",
        "Chronic headache follow-up (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_zealby",
        "pt_yorebeck",
        "dr_winmarsh",
        "14:40",
        "build-up drinks",
        "Restless legs medication review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_wadswell",
        "pt_yewholt",
        "dr_winmarsh",
        "15:00",
        "cimetidine",
        "Annual epilepsy review (wait-list backfill into a returned cancellation)",
    ),
    (
        "pt_whinbrook",
        "pt_yarnfold",
        "dr_winmarsh",
        "15:20",
        "omeprazole",
        "Parkinson's routine medication review (wait-list backfill into a returned cancellation)",
    ),
)

CONTESTS: tuple[BoardContest, ...] = tuple(
    BoardContest(
        claimant=claimant,
        holder=holder,
        specialty=NEUROLOGY,
        provider_id=provider_id,
        slot_hhmm=slot_hhmm,
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=reason,
        decisive_fact=fact,
    )
    for claimant, holder, provider_id, slot_hhmm, fact, reason in _CONTEST_TABLE
)

CLAIMANT_IDS: tuple[str, ...] = tuple(row[0] for row in _CONTEST_TABLE)

#: Claimants whose SECOND split piece rides a kin carrier's dual-purpose call (`claimant -> carrier`).
KIN_CARRIER_OF: dict[str, str] = {
    "pt_wadsholm": "pt_wadsholm_b",
    "pt_yarmead": "pt_yarmead_b",
    "pt_wadslund": "pt_wadslund_b",
    "pt_yarridge": "pt_yarridge_b",
    "pt_wadsmead": "pt_wadsmead_b",
    "pt_yarroyd": "pt_yarroyd_b",
    "pt_wadsridge": "pt_wadsridge_b",
    "pt_yarsett": "pt_yarsett_b",
    "pt_wadsroyd": "pt_wadsroyd_b",
    "pt_yarthwaite": "pt_yarthwaite_b",
    "pt_wadssett": "pt_wadssett_b",
    "pt_yarwell": "pt_yarwell_b",
    "pt_wadsthwaite": "pt_wadsthwaite_b",
    "pt_yarbrook": "pt_yarbrook_b",
}

#: Claimants whose SECOND split piece is their own ring-back: `claimant -> (at_min, desk, text)`. Every
#: recall desk differs from the claimant's intake desk (the >=2-desks rule under the mesh4 assignment).
RECALL_OF: dict[str, tuple[int, str, str]] = {
    "pt_whinlund": (77, "D", WHINLUND_RECALL_TEXT),
    "pt_zealridge": (87, "B", ZEALRIDGE_RECALL_TEXT),
    "pt_whinmead": (97, "D", WHINMEAD_RECALL_TEXT),
    "pt_zealroyd": (107, "B", ZEALROYD_RECALL_TEXT),
    "pt_whinridge": (117, "D", WHINRIDGE_RECALL_TEXT),
    "pt_zealsett": (127, "B", ZEALSETT_RECALL_TEXT),
    "pt_whinroyd": (137, "D", WHINROYD_RECALL_TEXT),
    "pt_zealthwaite": (147, "B", ZEALTHWAITE_RECALL_TEXT),
    "pt_whinsett": (157, "D", WHINSETT_RECALL_TEXT),
    "pt_zealwell": (167, "B", ZEALWELL_RECALL_TEXT),
    "pt_whinthwaite": (177, "D", WHINTHWAITE_RECALL_TEXT),
    "pt_zealbrook": (187, "B", ZEALBROOK_RECALL_TEXT),
    "pt_whinwell": (197, "D", WHINWELL_RECALL_TEXT),
    "pt_zealby": (207, "B", ZEALBY_RECALL_TEXT),
    "pt_wadswell": (212, "C", WADSWELL_RECALL_TEXT),
    "pt_whinbrook": (217, "D", WHINBROOK_RECALL_TEXT),
}

#: The sanctioned same-surname declarations: each kin carrier shares their claimant's surname, plus the
#: decoy's wife. Passed to BOTH registrations (the cards are shared objects).
KIN_OF: dict[str, str] = {kin: claimant for claimant, kin in KIN_CARRIER_OF.items()} | {
    "pt_wadsbrook_b": "pt_wadsbrook"
}

DECOYS_PLAIN: tuple[Decoy, ...] = (
    Decoy("pt_yarby"),
    Decoy("pt_zealcliffe"),
    Decoy("pt_wadsbrook"),
)
#: Same decoy ids, but Ronald's defusing fact arrives in his wife's call in the split twin (§6).
DECOYS_SPLIT: tuple[Decoy, ...] = (
    Decoy("pt_yarby"),
    Decoy("pt_zealcliffe"),
    Decoy("pt_wadsbrook", defusing_caller_id="pt_wadsbrook_b"),
)

#: Every inbound call, in arrival order: thirty claimants on a five-minute stagger across the four desks,
#: kin carriers trailing their claimants on a different desk, three decoys, the wife, and the corpus
#: background quartet (its voicemail trio on three desks carries the forced waits, §15(5)).
#: ORDERING RULE (meshfull; reordered at integration to P08's ratified pattern, n=30 form): all
#: thirty claimants occupy exactly the first 30 seats — the desks that carry the holders' queue-first
#: standing keeps (`A`..`Z`, `AA`..`AD`) — so every keep lands in the naive plan's round 0 and every
#: claimant acts in round 1, after it. A claimant seated past the keep desks acts in ROUND 0, and any
#: such seat that sorts before `Z` (all of `AE`..`AZ` do — two-letter ids sort between `A` and `B`)
#: books a not-yet-kept holder's slot, so the naive-starvation gate (rightly) refuses. The 22 late
#: seats carry only the kin carriers, the decoys and the background quartet, whose golds cannot touch
#: the contested diary. Relative order within each group, every caller's mesh4 desk letter, and the
#: authored arrival-time ladder (ties included) are unchanged.
ARRIVALS: tuple[tuple[str, str, int], ...] = (
    ("pt_wadsholm", "A", 0),
    ("pt_whinlund", "B", 5),
    ("pt_yarmead", "C", 10),
    ("pt_zealridge", "D", 15),
    ("pt_wadslund", "A", 18),
    ("pt_whinmead", "B", 20),
    ("pt_yarridge", "C", 22),
    ("pt_zealroyd", "D", 25),
    ("pt_wadsmead", "A", 30),
    ("pt_whinridge", "B", 35),
    ("pt_yarroyd", "C", 40),
    ("pt_zealsett", "D", 45),
    ("pt_wadsridge", "A", 47),
    ("pt_whinroyd", "B", 50),
    ("pt_yarsett", "C", 55),
    ("pt_zealthwaite", "D", 55),
    ("pt_wadsroyd", "A", 58),
    ("pt_whinsett", "B", 60),
    ("pt_yarthwaite", "C", 65),
    ("pt_zealwell", "D", 65),
    ("pt_wadssett", "A", 70),
    ("pt_whinthwaite", "B", 75),
    ("pt_yarwell", "C", 75),
    ("pt_zealbrook", "D", 80),
    ("pt_wadsthwaite", "A", 85),
    ("pt_whinwell", "B", 85),
    ("pt_yarbrook", "C", 90),
    ("pt_zealby", "D", 93),
    ("pt_wadswell", "A", 95),
    ("pt_whinbrook", "B", 95),
    ("pt_lachaux", "B", 100),
    ("pt_yarby", "B", 105),
    ("pt_wadsbrook", "D", 105),
    ("pt_wadsholm_b", "B", 108),
    ("pt_dunmore", "C", 110),
    ("pt_yarmead_b", "D", 115),
    ("pt_wadslund_b", "B", 115),
    ("pt_yarridge_b", "D", 118),
    ("pt_zealcliffe", "C", 120),
    ("pt_wadsmead_b", "B", 125),
    ("pt_yarroyd_b", "D", 125),
    ("pt_ledwidge", "A", 130),
    ("pt_wadsridge_b", "B", 135),
    ("pt_wadsbrook_b", "B", 135),
    ("pt_yarsett_b", "D", 140),
    ("pt_wadsroyd_b", "B", 145),
    ("pt_yarthwaite_b", "D", 145),
    ("pt_arundel", "D", 152),
    ("pt_wadssett_b", "B", 155),
    ("pt_yarwell_b", "D", 165),
    ("pt_wadsthwaite_b", "B", 175),
    ("pt_yarbrook_b", "D", 185),
)

VOICEMAIL: tuple[str, ...] = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: Every card this board authors, claimants then carriers then holders then decoys.
CARDS: tuple[PatientCard, ...] = (
    pt_wadsholm,
    pt_whinlund,
    pt_yarmead,
    pt_zealridge,
    pt_wadslund,
    pt_whinmead,
    pt_yarridge,
    pt_zealroyd,
    pt_wadsmead,
    pt_whinridge,
    pt_yarroyd,
    pt_zealsett,
    pt_wadsridge,
    pt_whinroyd,
    pt_yarsett,
    pt_zealthwaite,
    pt_wadsroyd,
    pt_whinsett,
    pt_yarthwaite,
    pt_zealwell,
    pt_wadssett,
    pt_whinthwaite,
    pt_yarwell,
    pt_zealbrook,
    pt_wadsthwaite,
    pt_whinwell,
    pt_yarbrook,
    pt_zealby,
    pt_wadswell,
    pt_whinbrook,
    pt_wadsholm_b,
    pt_yarmead_b,
    pt_wadslund_b,
    pt_yarridge_b,
    pt_wadsmead_b,
    pt_yarroyd_b,
    pt_wadsridge_b,
    pt_yarsett_b,
    pt_wadsroyd_b,
    pt_yarthwaite_b,
    pt_wadssett_b,
    pt_yarwell_b,
    pt_wadsthwaite_b,
    pt_yarbrook_b,
    pt_whinby,
    pt_yarcliffe,
    pt_zealcote,
    pt_wadsby,
    pt_whincliffe,
    pt_yarcote,
    pt_zealden,
    pt_wadscliffe,
    pt_whincote,
    pt_yarden,
    pt_zealdijk,
    pt_wadscote,
    pt_whinden,
    pt_yardijk,
    pt_zealdon,
    pt_woldmere,
    pt_wyredale,
    pt_welkholt,
    pt_wrenmarsh,
    pt_wickfirth,
    pt_wetherholt,
    pt_winsgarth,
    pt_wharfeholm,
    pt_woldenby,
    pt_wexmoor,
    pt_yewbank,
    pt_yeldmere,
    pt_yorebeck,
    pt_yewholt,
    pt_yarnfold,
    pt_yarby,
    pt_zealcliffe,
    pt_wadsbrook,
    pt_wadsbrook_b,
)

#: The split twin's intake overrides: every claimant says only their routine-sounding piece 1, every kin
#: carrier's dual-purpose call gains its mention, and Ronald's defusal moves from his call to his wife's.
SPLIT_INTAKES: dict[str, str] = {
    "pt_wadsholm": WADSHOLM_SPLIT_INTAKE,
    "pt_whinlund": WHINLUND_SPLIT_INTAKE,
    "pt_yarmead": YARMEAD_SPLIT_INTAKE,
    "pt_zealridge": ZEALRIDGE_SPLIT_INTAKE,
    "pt_wadslund": WADSLUND_SPLIT_INTAKE,
    "pt_whinmead": WHINMEAD_SPLIT_INTAKE,
    "pt_yarridge": YARRIDGE_SPLIT_INTAKE,
    "pt_zealroyd": ZEALROYD_SPLIT_INTAKE,
    "pt_wadsmead": WADSMEAD_SPLIT_INTAKE,
    "pt_whinridge": WHINRIDGE_SPLIT_INTAKE,
    "pt_yarroyd": YARROYD_SPLIT_INTAKE,
    "pt_zealsett": ZEALSETT_SPLIT_INTAKE,
    "pt_wadsridge": WADSRIDGE_SPLIT_INTAKE,
    "pt_whinroyd": WHINROYD_SPLIT_INTAKE,
    "pt_yarsett": YARSETT_SPLIT_INTAKE,
    "pt_zealthwaite": ZEALTHWAITE_SPLIT_INTAKE,
    "pt_wadsroyd": WADSROYD_SPLIT_INTAKE,
    "pt_whinsett": WHINSETT_SPLIT_INTAKE,
    "pt_yarthwaite": YARTHWAITE_SPLIT_INTAKE,
    "pt_zealwell": ZEALWELL_SPLIT_INTAKE,
    "pt_wadssett": WADSSETT_SPLIT_INTAKE,
    "pt_whinthwaite": WHINTHWAITE_SPLIT_INTAKE,
    "pt_yarwell": YARWELL_SPLIT_INTAKE,
    "pt_zealbrook": ZEALBROOK_SPLIT_INTAKE,
    "pt_wadsthwaite": WADSTHWAITE_SPLIT_INTAKE,
    "pt_whinwell": WHINWELL_SPLIT_INTAKE,
    "pt_yarbrook": YARBROOK_SPLIT_INTAKE,
    "pt_zealby": ZEALBY_SPLIT_INTAKE,
    "pt_wadswell": WADSWELL_SPLIT_INTAKE,
    "pt_whinbrook": WHINBROOK_SPLIT_INTAKE,
    "pt_wadsholm_b": WADSHOLM_B_SPLIT_INTAKE,
    "pt_yarmead_b": YARMEAD_B_SPLIT_INTAKE,
    "pt_wadslund_b": WADSLUND_B_SPLIT_INTAKE,
    "pt_yarridge_b": YARRIDGE_B_SPLIT_INTAKE,
    "pt_wadsmead_b": WADSMEAD_B_SPLIT_INTAKE,
    "pt_yarroyd_b": YARROYD_B_SPLIT_INTAKE,
    "pt_wadsridge_b": WADSRIDGE_B_SPLIT_INTAKE,
    "pt_yarsett_b": YARSETT_B_SPLIT_INTAKE,
    "pt_wadsroyd_b": WADSROYD_B_SPLIT_INTAKE,
    "pt_yarthwaite_b": YARTHWAITE_B_SPLIT_INTAKE,
    "pt_wadssett_b": WADSSETT_B_SPLIT_INTAKE,
    "pt_yarwell_b": YARWELL_B_SPLIT_INTAKE,
    "pt_wadsthwaite_b": WADSTHWAITE_B_SPLIT_INTAKE,
    "pt_yarbrook_b": YARBROOK_B_SPLIT_INTAKE,
    "pt_wadsbrook": WADSBROOK_SPLIT_INTAKE,
    "pt_wadsbrook_b": VERA_SPLIT_INTAKE,
}

#: The plain twin: every claimant's whole story in their own single intake.
PLAIN_EVIDENCE: tuple[EvidenceCall, ...] = tuple(
    EvidenceCall(caller_id=pid, about_claimant=pid) for pid in CLAIMANT_IDS
)


def _split_evidence() -> tuple[EvidenceCall, ...]:
    """The split twin's pieces: each claimant's own intake, then their kin's intake or their ring-back."""
    pieces: list[EvidenceCall] = []
    for pid in CLAIMANT_IDS:
        pieces.append(EvidenceCall(caller_id=pid, about_claimant=pid))
        if pid in KIN_CARRIER_OF:
            pieces.append(
                EvidenceCall(caller_id=KIN_CARRIER_OF[pid], about_claimant=pid)
            )
        else:
            at_min, desk, text = RECALL_OF[pid]
            pieces.append(
                EvidenceCall(
                    caller_id=pid,
                    about_claimant=pid,
                    kind="recall",
                    at_min=at_min,
                    desk=desk,
                    text=text,
                )
            )
    return tuple(pieces)


SPLIT_EVIDENCE: tuple[EvidenceCall, ...] = _split_evidence()

#: The split twin's phone-probe rewrites (`facts_overrides`): every claimant's
#: canonical medications/onset answers name the decisive interactor outright (omeprazole/cimetidine) or
#: volunteer the build-up drinks stopping — the assembled trigger served to any desk that rings. The
#: split twin's probed claimant volunteers the sub-threshold fragment only: for the tablet claimants an
#: unnamed stomach/indigestion tablet with its start date (the identity is what makes the interaction
#: textbook); for the drinks claimants the symptom alone — the feed-stop IS the decisive event, so it
#: lives only in the calls.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_wadsholm": {
        "medications": (
            "Phenytoin at night, clopidogrel in the morning — and since Saturday the stomach tablet "
            "from the out-of-hours doctor."
        ),
        "onset": "The stomach tablet started Saturday night. The wobbliness came on over the last two mornings.",
    },
    "pt_wadslund": {
        "medications": "Phenytoin morning and night, the water tablet — and the indigestion tablet since Sunday.",
        "onset": "The indigestion tablet started Sunday evening. The boat-walk feeling began Monday.",
    },
    "pt_wadsmead": {
        "medications": "Phenytoin at night, the thyroid tablet in the morning — and the stomach tablet since Friday.",
        "onset": "The stomach tablet started Friday evening. The veering began Saturday.",
    },
    "pt_wadsridge": {
        "medications": "The phenytoin, morning and night. Nothing else.",
        "onset": "The clumsiness came on over the weekend.",
    },
    "pt_wadsroyd": {
        "medications": "Phenytoin at night, the little aspirin — and the stomach tablet since Saturday night.",
        "onset": "The stomach tablet started Saturday night. The swaying on the top step began Monday.",
    },
    "pt_wadssett": {
        "medications": (
            "Phenytoin at night, the blue inhaler now and then — and the stomach tablet since Friday "
            "night; I could not tell you its name without the box."
        ),
        "onset": "The stomach tablet started Friday night. The wobbliness showed itself Sunday, down the allotment.",
    },
    "pt_wadsthwaite": {
        "medications": "Phenytoin morning and night, the water tablet — and the stomach tablet since Saturday.",
        "onset": "The stomach tablet started Saturday. The wobbly steps began Sunday.",
    },
    "pt_wadswell": {
        "medications": (
            "Phenytoin morning and night, a fish oil of my own — and the indigestion tablet from the "
            "chemist since Thursday."
        ),
        "onset": "The indigestion tablet started Thursday. The wobbling on the back step began Saturday.",
    },
    "pt_whinbrook": {
        "medications": "Phenytoin at night, the gout tablet — and the stomach tablet since Sunday.",
        "onset": "The stomach tablet started Sunday. The unsteadiness on the landing began yesterday.",
    },
    "pt_whinlund": {
        "medications": (
            "Phenytoin morning and night, the bone tablet on Sundays — and the indigestion tablet "
            "since Thursday; the name is on the packet, not in my head."
        ),
        "onset": "The indigestion tablet started Thursday; the double sight began over the weekend, evenings mostly.",
    },
    "pt_whinmead": {
        "medications": "Phenytoin at night, the waterworks tablet — and the stomach tablet from the chemist since Friday.",
        "onset": "The stomach tablet started Friday. The giddy turns began Saturday, when I turn quickly.",
    },
    "pt_whinridge": {
        "medications": "Phenytoin at night, the statin — and the stomach tablet since Thursday, from the private man.",
        "onset": "The stomach tablet started Thursday evening, after the private appointment. The eye trouble began at the weekend.",
    },
    "pt_whinroyd": {
        "medications": "Phenytoin at night, the prostate tablet — and the stomach tablet since Friday.",
        "onset": "The stomach tablet started Friday. The giddiness on the stairs began Sunday.",
    },
    "pt_whinsett": {
        "medications": "Phenytoin morning and night, the sertraline. Nothing besides.",
        "onset": "The evening doubling began Thursday.",
    },
    "pt_whinthwaite": {
        "medications": "Phenytoin morning and night, the calcium tablets. That is the lot.",
        "onset": "The giddy turns began Saturday.",
    },
    "pt_whinwell": {
        "medications": "Phenytoin at night, the blood pressure tablet — and the stomach tablet since Tuesday, private.",
        "onset": "The stomach tablet started Tuesday evening, from the private clinic. The sleepiness began Thursday.",
    },
    "pt_yarbrook": {
        "medications": (
            "Phenytoin morning and night, the little white one for sleep — and the stomach tablet "
            "since Friday."
        ),
        "onset": "The stomach tablet started Friday evening. The swaying began Sunday.",
    },
    "pt_yarmead": {
        "medications": "The phenytoin at night. Nothing else these days.",
        "onset": "The sleepiness and the unsteadiness came on from Wednesday.",
    },
    "pt_yarridge": {
        "medications": "Phenytoin at night, the blood pressure tablet — and the stomach tablet since Saturday night.",
        "onset": "The stomach tablet started Saturday night — Keith has charge of the box. The swaying began Sunday.",
    },
    "pt_yarroyd": {
        "medications": "Phenytoin morning and night, my eye drops — and the indigestion tablet from the chemist since Wednesday.",
        "onset": "The indigestion tablet started Wednesday. The wobbliness on the step began Friday.",
    },
    "pt_yarsett": {
        "medications": (
            "Phenytoin morning and night, the bone tablets — and the stomach tablet from the chemist "
            "since Thursday."
        ),
        "onset": "The stomach tablet started Thursday. The unsteadiness at the sink began Saturday.",
    },
    "pt_yarthwaite": {
        "medications": "Phenytoin morning and night, the heart tablet — and the stomach tablet since Sunday.",
        "onset": "The stomach tablet started Sunday. The veering in the hallway began Monday.",
    },
    "pt_yarwell": {
        "medications": "Phenytoin at night, the metformin twice a day — and the stomach tablet since Thursday.",
        "onset": "The stomach tablet started Thursday. The kerb business began at the weekend.",
    },
    "pt_zealbrook": {
        "medications": (
            "Phenytoin morning and night, my eye drops — and the indigestion tablet from the chemist "
            "since Wednesday; I never studied the name."
        ),
        "onset": "The indigestion tablet started Wednesday. The swimming letters began Friday.",
    },
    "pt_zealby": {
        "medications": "The phenytoin at night. Just that.",
        "onset": "The soft evening speech began Friday.",
    },
    "pt_zealridge": {
        "medications": "Phenytoin at night, the statin — and the stomach tablet since Friday, from the private clinic.",
        "onset": "The stomach tablet started Friday, after the private appointment. The soft speech was Sunday evening and again last night.",
    },
    "pt_zealroyd": {
        "medications": "The phenytoin, morning and night. Nothing else on repeat.",
        "onset": "The sleepiness and the listing started midweek.",
    },
    "pt_zealsett": {
        "medications": "Phenytoin at night, the blood pressure tablet — and the stomach tablet since Thursday.",
        "onset": "The stomach tablet started Thursday night. The woolly speech was Sunday evening and last night, on the phone.",
    },
    "pt_zealthwaite": {
        "medications": (
            "Phenytoin at night, the prostate tablet — and the stomach tablet since Wednesday, from "
            "the private man."
        ),
        "onset": "The stomach tablet started Wednesday, at the private consultation. The afternoon sleepiness began Friday.",
    },
    "pt_zealwell": {
        "medications": (
            "Phenytoin at night, a hay fever tablet in season — and the indigestion tablet from the "
            "chemist since Friday."
        ),
        "onset": "The indigestion tablet started Friday. The slurring showed itself at choir last night.",
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=30,
    theme_slug="phenytoin_toxicity",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=PLAIN_EVIDENCE,
    decoys=DECOYS_PLAIN,
    cards=CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="300",
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=30,
    theme_slug="phenytoin_toxicity",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=SPLIT_EVIDENCE,
    decoys=DECOYS_SPLIT,
    cards=CARDS,
    intake_overrides=SPLIT_INTAKES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="300",
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
