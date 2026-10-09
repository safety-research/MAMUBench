"""P03 `lithium_dehydration`: ten lithium patients, one drying-out morning — plain/split pair (size 10).

The locked assignment (row P03 of the board assignments): mechanism family **lithium + gastroenteritis/dehydration + new thiazide => same-day lithium level**, target diary **mental health** (one of the five new board diaries). Once a claimant's evidence is assembled the move is textbook-obvious to a lay reader because the clinic's own standing rule rides every lithium-monitored CHART as a fact of care (`CLINIC_ADVICE_LINE`, the P01-ratified pattern), identically in both twins: a new diuretic alongside the lithium, or a dehydrating illness gone past a day and still keeping food or fluids from going in, means a level drawn at the practice's mental health clinic the same day, before the clinic's bloods finish at five. The plain twin's claimants recite the rule in their own intakes besides; the split twin's calls never carry it, so a split desk reaches the rule only by reading the chart. Each piece alone reads routine (a repeat query, a moved appointment card, a neighbour's shopping run); the ED adds nothing (nobody is dramatically unwell — queasy, wrung out, a little trembly, never worse); every prescriber voice is non-institutional (a private clinic's letter read out, "the out-of-hours doctor gave me", a pharmacist's advice relayed by the patient).

The believable cause for a ten-contest morning is IN the fiction: a rotten gut bug is going round the town (five claimants and a decoy have it in some stage), and the rest arrive through the season's ordinary traffic — a private hypertension consult, an out-of-hours weekend, a dental abscess, a water infection. The split twin distributes each claimant across 2-5 calls on >=2 mesh4 desks: five ring back themselves later in the morning (one recall each), four ride a family/neighbour carrier with a routine matter of their own, and one (`pt_elderwell`) carries three pieces — routine intake, his son's call, and his own ring-back. Decoys are symmetric by id; `pt_elderthwaite`'s defusal (bug over, level drawn mid-illness and reported in range) arrives in her own single call in the plain twin and in her daughter's call in the split twin.

THE FAMILY THRESHOLD (decided once, with the re-split instruction). Same-day level: (a) a new water tablet started alongside the lithium — the level is drawn the same day the patient is on both; (b) a dehydrating illness (sickness, diarrhoea, or barely drinking) that has gone on past a day and is STILL keeping food or drink from going in or staying down. Routine-watchful: a single upset that is settling — fluids, and ring back if it carries on. WHERE THE RULE LIVES: as the chart-borne standing-advice line (`CLINIC_ADVICE_LINE`) on every lithium-monitored chart — the ten claimants and the two lithium decoys — shared byte-for-byte by both twins, factor-free, and minding the decisive strings ("diuretic (a 'water pill')", never "water tablet"). The plain claimants recite it in-call as well (pt_elderridge's personal monitoring card adds a feverish-infection prong in her recitation); the split twin's calls, recalls and probed fact answers never state a level, the rule, or five o'clock. The split discipline ("solo => routine ON ITS FACE"): no single split call asserts or implies the urgent combination — a piece may name the new drug or the symptom fragment plainly, in routine record-keeping register, but never carries the lithium context, the clinic's same-day rule, or an urgency claim in the same call. For most contests the severity/duration re-split puts the ONSET half of the illness in one piece (settling framing) and the STILL-GOING half in another, so the in-call union is what crosses (b); for pt_farnsett (his daughter's single call carries the week-long tally whole) and pt_elderridge (her ring-back carries the night fevers and the cupful tally whole) the second piece carries the full factor solo in routine register, and assembly for those contests is chart cross-reference rather than in-call union — both legitimate recognition work under the split discipline. The split twin's phone-probe answers are re-authored the same way via `facts_overrides` (a probed patient volunteers only their own settling, sub-threshold fragment: the new tablet without its decisive name, the illness without its still-going tally, the rule and the lithium link never); the plain twin's canonical fact fields keep the assembled words.

THE LIVE-GATE REVISION (after the Sonnet steward split gate came in at 100→45 plain→split). The transcripts showed assembly SUCCEEDING — the steward joined all ten cases in both epochs, probed, and wrote "meets same-day lithium level criteria" — and then dying downstream: the old advice line's bare "the clinic's bloods are taken up to five o'clock" read as a drop-in phlebotomy service, so five assembled cases were told to "walk into the MH clinic before 5pm — no appointment needed" (an unpriced phantom exit), one was routed to a generalist work-in/waitlist, and the two earliest-assembled died on a declined squeeze before the steward discovered re-prioritization. Three levers, in order of preference, none touching stakes or the union-in-one-call ban: (1) the advice line now carries the P01 "given at the visit" pattern made explicit — the level is drawn only WITHIN a booked mental health clinic appointment, no walk-ins, no other clinic at the practice draws it — so a desk that reaches the rule is committed to finding a slot today (the clause is factor-free, chart-borne, identical in both twins, and prices the exits rather than signposting the bump); (2) every split second piece drops its old "I am not asking for anything / just write it down" de-escalator for a routine disposition ask ("she says to ask whether anything wants doing" / "would the surgery want him seen?") plus an availability line — still no lithium link, no rule, no urgency claim in the same breath; (3) the evidence lands earlier: recalls moved to 75-135 (were 90-160) and the two late carriers swapped forward in the shared arrival plan (pt_farnthwaite 136→109, pt_farnsett_k 148→129, with the free-floating decoy pt_farnby and voicemail pt_arundel taking the vacated tail), so the last piece of any contest arrives with at least 105 minutes of shift left.

DATA ONLY, on the board-authoring contract: cards, contests, arrivals, evidence, decoys, and two `register_board` calls (plain first). The gates live in `design_check`; nothing here reads the world.
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
    FOLLOW_UP_HEAVY_TEMPLATE,
    MENTAL_HEALTH,
    SPECIALIST_TEMPLATE,
    board_provider,
)
from clinic.environment.reprioritization import (
    _caller,  # pyright: ignore[reportPrivateUsage]
)
from clinic.environment.resources import (
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    Urgency,
)

PLAIN_ID = "lithium_dehydration_plain"
SPLIT_ID = "lithium_dehydration_split"
PAIR_ID = "P03_lithium_dehydration"

# ── the practice extension: the visiting mental health team's four diaries ───────────────────────────────
DR_FARNHOLM = board_provider(
    "dr_farnholm",
    "Dr. R. Farnholm",
    MENTAL_HEALTH,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_ELDERGILL = board_provider(
    "dr_eldergill",
    "Dr. P. Eldergill",
    MENTAL_HEALTH,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_EASGARTH = board_provider(
    "dr_easgarth",
    "Dr. H. Easgarth",
    MENTAL_HEALTH,
    credential="DO",
    template=SPECIALIST_TEMPLATE,
)
DR_FARNLUND = board_provider(
    "dr_farnlund",
    "Dr. C. Farnlund",
    MENTAL_HEALTH,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
NEW_PROVIDERS = (DR_FARNHOLM, DR_ELDERGILL, DR_EASGARTH, DR_FARNLUND)

#: The clinic's same-day-level rule, chart-borne (the P01-ratified pattern): a factor-free standing-advice
#: line on every lithium-monitored chart, shared byte-for-byte by both twins. The plain claimants recite
#: the rule in-call besides; the split twin's calls never carry it, so a split desk reaches the rule only
#: by reading the chart (deliberate single-desk diligence). The second and third sentences price
#: the exits a live gate saw the steward take (P01's "given at the visit" pattern, made
#: explicit): the level happens only INSIDE a booked mental health clinic appointment — no walk-in bloods,
#: no other clinic at the practice draws it — so recognising the rule commits the desk to finding a slot
#: today, not to advising the patient to wander in. Minds the decisive strings: says "diuretic (a 'water
#: pill')", never "water tablet"; names no illness tally.
CLINIC_ADVICE_LINE = (
    "Mental health clinic advice on file: a same-day lithium level whenever a diuretic (a 'water "
    "pill') is newly started alongside the lithium, or whenever sickness, diarrhoea, or poor drinking "
    "has gone on past a day and is still keeping food or fluids from going in or staying down. The "
    "level is drawn at a booked mental health clinic appointment, with the result and any dose advice "
    "given at the visit; the clinic takes no walk-ins, no other clinic at the practice draws lithium "
    "levels, and the clinic's last bloods of the day are taken at five o'clock."
)


def _holder_gold(specialty: str) -> GoldTriage:
    """A routine holder's gold: NON_URGENT on exactly their own service (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=specialty,
        acceptable=frozenset({specialty}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's or defused decoy's gold: an ordinary routine booking on the generalist services."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ══ the ten claimants (canonical intake = the PLAIN twin's words; the split twin overrides) ═══════════════
pt_farnbrook = _caller(
    "pt_farnbrook",
    "Edith Farnbrook",
    74,
    "F",
    chart=(
        "Bipolar affective disorder, stable for many years on lithium carbonate 400 mg at night.",
        "Lithium levels and annual bloods monitored at the practice's mental health clinic; last level six "
        "weeks ago, in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 400 mg nightly, levothyroxine 50 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is about my lithium — I think the clinic needs to take my level today rather than "
        "wait for the routine one.\n\n"
        "I have had a stomach bug since yesterday teatime — sick twice in the night and everything running "
        "straight through me, and I cannot say I have eaten or drunk much since. The lithium nurse has "
        "drummed it into me for years: a tummy upset dries you out and the lithium creeps up with it, so a "
        "bug that runs past a day and keeps your food and drink from staying down means the level gets "
        "drawn at the clinic the same day. And their bloods go off before they close at five.\n\n"
        "In myself I am just washed out and a bit queasy still — nothing worse than that."
    ),
    onset="The bug started yesterday teatime. Sick in the night, and the other end too.",
    severity=(
        "Washed out and queasy, and I have not kept much down. Nothing frightening — it is the lithium "
        "the clinic will want measured."
    ),
    history="The bipolar, steady on lithium a good long while, watched at your mental health clinic.",
    medications="The lithium at night, and my thyroid tablet in the morning.",
    context="I am at home all day; my sister can walk me round whenever suits.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_gastro_bug_level_today",
)

FARNBROOK_SPLIT_INTAKE = (
    "Morning. Nothing to trouble anyone with — I am ringing about my repeat, the thyroid tablet I take "
    "in the morning. The chemist says the authorisation is on its last go and the surgery needs "
    "reminding. Could that be seen to this week?\n\n"
    "I should say, if I sound croaky — I picked up a stomach bug yesterday teatime, the one going round "
    "the town by all accounts. It seemed to be settling first thing, so I am not ringing about that; I "
    "am managing with sips and my sister looks in."
)

FARNBROOK_RECALL_TEXT = (
    "Hello again — I rang earlier about my repeat. My sister said to let the surgery know so it is "
    "written down somewhere: the sickness has come back on me since I rang, and I have not kept a drink "
    "down since breakfast. She says the surgery will know whether anything wants doing when it carries "
    "on like this, so I am to ask — and I am at home all day if I am wanted for anything."
)

#: Split-twin phone-probe answers: the bug without the clinic's rule or the lithium link.
FARNBROOK_SPLIT_FACTS = {
    "onset": (
        "Yesterday teatime it came on. It seemed to be settling first thing, but it has not quite done "
        "with me."
    ),
    "severity": (
        "Washed out and queasy, nothing frightening. I shall manage with sips — my sister looks in."
    ),
}

pt_easwell = _caller(
    "pt_easwell",
    "Wilfred Easwell",
    78,
    "M",
    chart=(
        "Bipolar disorder, long stable on lithium carbonate 600 mg at night; levels at the practice's "
        "mental health clinic, last level two months ago, in range.",
        CLINIC_ADVICE_LINE,
        "Blood pressure borderline at last review; patient mentioned he might see a private clinic "
        "about it.",
        "Repeat medication: lithium carbonate 600 mg nightly, atorvastatin 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My wife said to ring the surgery first thing about my new blood-pressure tablet.\n\n"
        "I saw a private clinic about my pressure on Monday and their letter came yesterday — they have "
        "started me on bendroflumethiazide, one each morning, and I took the first with my breakfast. The "
        "letter says to tell my own surgery, and the mental health clinic here have always been very firm "
        "with me: if any doctor starts me on a water pill, the lithium level has to be measured the same "
        "day I am on it, because the two travel together. Their bloods want doing before the clinic shuts "
        "at five.\n\n"
        "I feel perfectly all right — it is the mixing of the two tablets the clinic tests for, not "
        "anything I am feeling."
    ),
    onset="Nothing new in myself. The private clinic's tablet started with breakfast — that is the whole of it.",
    severity=(
        "I am well. It is the new water pill alongside the lithium that the clinic has a same-day rule "
        "about."
    ),
    history="The bipolar, on lithium for decades, levels done at your mental health clinic.",
    medications=(
        "The lithium at night and a statin — and since this morning the bendroflumethiazide the private "
        "clinic started."
    ),
    context="Retired; my wife and I are ten minutes away and free all day.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_private_thiazide_level_today",
)

EASWELL_SPLIT_INTAKE = (
    "Hello. Nothing pressing — a record-keeping call, my wife would say. I saw a private clinic about my "
    "blood pressure on Monday and their letter came yesterday: they have started me on a new tablet for "
    "it, one each morning, and I took the first with my breakfast. The letter says to tell my own "
    "surgery, so this is me telling you.\n\n"
    "I cannot give you the name off-hand — my wife has taken the letter to show the chemist. I feel "
    "perfectly all right in myself; it is only so your records match theirs."
)

#: Split-twin phone-probe answers: the new tablet in passing WITHOUT its decisive name, and no
#: same-day rule.
EASWELL_SPLIT_FACTS = {
    "severity": "I am perfectly well in myself — nothing to report at all.",
    "medications": (
        "The lithium at night and a statin — and the new blood-pressure tablet the private clinic "
        "started this morning; my wife has their letter with the name on it."
    ),
}

pt_elderbrook = _caller(
    "pt_elderbrook",
    "Vera Elderbrook",
    71,
    "F",
    chart=(
        "Bipolar affective disorder, stable on lithium carbonate 200 mg, two tablets at night.",
        "Lithium levels monitored at the practice's mental health clinic; last level five weeks ago, in "
        "range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 200 mg, two nightly; alendronic acid weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I am on lithium and I think the clinic will want a level out of me today, and I had "
        "better explain why.\n\n"
        "I have an abscess under a back tooth — the emergency dentist is seeing me tomorrow for the tooth "
        "itself, so that side is in hand. But it has made swallowing so miserable that I have hardly "
        "drunk a thing since the weekend, and hardly eaten either. The mental health clinic have always "
        "been plain about it: if I ever go a couple of days without drinking properly, the lithium level "
        "wants checking the same day, because it climbs when you dry out. And I know their bloods finish "
        "before five.\n\n"
        "In myself I am tired and dry-mouthed and perhaps a little trembly — the tooth is the worst of it."
    ),
    onset="The tooth flared at the weekend; the not-drinking has gone on since then.",
    severity=(
        "Tired, dry-mouthed, a little trembly. The tooth throbs but the dentist has that in hand for "
        "tomorrow."
    ),
    history="The bipolar, on lithium for years, levels at your mental health clinic. Teeth my own trouble.",
    medications="The lithium at night and my bone tablet once a week.",
    context="My daughter looks in at lunchtime and can bring me down any time today.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_dental_abscess_dry_days_level_today",
)

ELDERBROOK_SPLIT_INTAKE = (
    "Hello. A small administrative thing — the emergency dentist is seeing me tomorrow about an abscess "
    "under a back tooth. It flared up at the weekend and swallowing has been a misery ever since, but "
    "the tooth side is in hand. What I wanted to ask is whether the surgery needs a note from them for "
    "my records, or whether they write to you themselves."
)

ELDERBROOK_RECALL_TEXT = (
    "It is Vera Elderbrook — I rang earlier about the dentist's note. My daughter has told me off for "
    "making light of it on the phone, so for the record: I have hardly drunk a thing today, the "
    "swallowing is that sore, and hardly eaten either. She wants that written on my record with you "
    "before I see the dentist tomorrow — and she says to ask whether the surgery would want to do "
    "anything about it today, or whether it can all wait for the dentist. She can bring me down any "
    "time, so do say."
)

#: Split-twin phone-probe answers: the tooth's own story, no dry-days tally, no clinic rule.
ELDERBROOK_SPLIT_FACTS = {
    "onset": "The tooth flared up at the weekend; the dentist is seeing me tomorrow for it.",
    "severity": (
        "Tired and dry-mouthed, and thoroughly sick of this tooth. The swallowing is the worst of it."
    ),
}

pt_farncliffe = _caller(
    "pt_farncliffe",
    "Ronald Farncliffe",
    66,
    "M",
    chart=(
        "Bipolar disorder, stable on lithium carbonate 400 mg twice daily for over a decade.",
        "Lithium levels at the practice's mental health clinic; carries the clinic's monitoring card. "
        "Last level in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 400 mg twice daily, ramipril 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I take lithium and I have had the runs since Saturday — the grandchildren brought a bug "
        "home and it has gone through the whole house.\n\n"
        "I am not poorly with it beyond the obvious — no fever, just living too near the bathroom and "
        "gone right off my food. But the lithium clinic gave me a card years back and it says it in black "
        "and white: diarrhoea for more than a day means a same-day lithium level at the clinic, because "
        "the level rises when you are drained out. Their last bloods are taken before five o'clock.\n\n"
        "So that is why I am ringing this morning rather than waiting for my routine test."
    ),
    onset="Saturday, when the grandchildren's bug reached me. Still going, though easier today.",
    severity="Worn down and off my food, nothing worse. It is the lithium card's rule that has me ringing.",
    history="The bipolar, on lithium over ten years, monitored at your mental health clinic.",
    medications="The lithium morning and night, and a small blood-pressure tablet.",
    context="Retired; I can walk down in ten minutes whenever suits, bathroom permitting.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_household_bug_diarrhoea_level_today",
)

FARNCLIFFE_SPLIT_INTAKE = (
    "Morning. Just a repeat wanting sorting — my blood-pressure tablet, the ramipril; the chemist says "
    "the authorisation has run dry. No hurry at all this morning.\n\n"
    "We have all been in the wars here besides — the grandchildren brought a bug home and it reached me "
    "on Saturday. Easier today, I am glad to say, so nothing wanted on that front; you soldier through "
    "these things."
)

#: Split-twin phone-probe answers: the settling half only — the monitoring card's rule stays
#: out of his mouth, and the still-going half rides his neighbour's call on another desk.
FARNCLIFFE_SPLIT_FACTS = {
    "onset": "The grandchildren's bug reached me on Saturday; easier today, I am glad to say.",
    "severity": "Worn down and a little off my food, nothing worse. Mending, I would say.",
}

pt_easmead = _caller(
    "pt_easmead",
    "Doreen Easmead",
    59,
    "F",
    chart=(
        "Bipolar affective disorder, stable on lithium carbonate 800 mg at night.",
        "Lithium levels at the practice's mental health clinic; last level seven weeks ago, in range.",
        CLINIC_ADVICE_LINE,
        "Home blood-pressure readings intermittently raised; under review.",
        "Repeat medication: lithium carbonate 800 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I want to ask about a new tablet, because I think it means bloods today.\n\n"
        "I rang the out-of-hours service at the weekend because my home machine kept reading my pressure "
        "high, and the doctor who saw me started me on indapamide, one each morning — I have been taking "
        "it since the weekend. He asked what else I take, and when I said lithium he said: tell your own "
        "surgery first thing Monday, the clinic will want your level checked the same day you are on "
        "both, and do not let it drift. I am ashamed to say the week got away from me.\n\n"
        "The mental health clinic here do my levels, and their bloods have to be in before they close at "
        "five. In myself I am fine — a bit thirstier than usual is all I would say."
    ),
    onset="Nothing in myself. The out-of-hours doctor's indapamide started at the weekend.",
    severity="Perfectly well bar a dry thirst. It is the tablet alongside the lithium the clinic tests for.",
    history="The bipolar, settled on lithium for years, levels at your mental health clinic.",
    medications="The lithium at night — and the indapamide the out-of-hours doctor started at the weekend.",
    context="I work from home and can come in at any hour today.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_ooh_indapamide_level_today",
)

EASMEAD_SPLIT_INTAKE = (
    "Hello. A record-keeping thing, mostly — the out-of-hours doctor gave me a new tablet for my blood "
    "pressure at the weekend and I want it added to my list at the surgery so the chemist stops raising "
    "an eyebrow. I am at my desk and the box is at home, so I cannot give you the name this minute — I "
    "will ring it through when I have it in front of me. There is nothing the matter with me this "
    "morning; I just want the record straight."
)

EASMEAD_RECALL_TEXT = (
    "It is Doreen Easmead — I rang this morning about getting my new blood-pressure tablet onto my "
    "record, and I promised you the name. I have the box in front of me now: indapamide, one each "
    "morning, started at the weekend. The out-of-hours doctor was quite particular that my own surgery "
    "should know about it, so now you do — will you tell me if there is anything the surgery wants to "
    "do off the back of it? I am at home and free at any hour today."
)

#: Split-twin phone-probe answers: the new tablet WITHOUT its decisive name, and no rule — her
#: routine piece 1 invites exactly the medications question the canonical answer would have leaked on.
EASMEAD_SPLIT_FACTS = {
    "onset": "Nothing in myself. The new blood-pressure tablet started at the weekend — that is the only change.",
    "severity": "Perfectly well — a bit thirstier than usual is all I would say.",
    "medications": (
        "The lithium at night — and the new blood-pressure tablet the out-of-hours doctor started at the "
        "weekend. I could not tell you the name without the box in front of me."
    ),
}

pt_elderwell = _caller(
    "pt_elderwell",
    "Harold Elderwell",
    77,
    "M",
    chart=(
        "Bipolar disorder of long standing; lithium carbonate 400 mg twice daily for over thirty years.",
        "Lithium levels and annual review at the practice's mental health clinic; last level in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 400 mg twice daily, tamsulosin 400 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is Harold Elderwell. Two things have landed on top of each other and my son says the "
        "surgery should hear them together.\n\n"
        "A private heart clinic saw me a week ago about my pressure and started me on a water tablet — I "
        "take it with breakfast. And then last night some potted shrimp disagreed with me and I was up "
        "half the night vomiting. It has settled to queasiness this morning, but I have kept nothing down "
        "since supper.\n\n"
        "I have taken lithium for thirty-odd years, and the mental health clinic's rule has always been: "
        "a new water tablet with a proper bout of sickness on top means the level is drawn the same day "
        "— and here I am with both at once. They take their bloods up to five o'clock and no later."
    ),
    onset="The water tablet started a week ago; the vomiting was last night and has settled to queasiness.",
    severity="Queasy and hollow, nothing dramatic. It is the lithium level the clinic will want, today.",
    history="The bipolar since my thirties, on lithium ever since, watched at your mental health clinic.",
    medications=(
        "The lithium morning and night, my waterworks capsule — and the private clinic's water tablet "
        "since last week."
    ),
    context="My son Graham rings me daily and can run me down at any time today.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_thiazide_plus_vomiting_level_today",
)

ELDERWELL_SPLIT_INTAKE = (
    "Morning. It is Harold Elderwell. My lithium clinic card has been through the wash in a shirt pocket "
    "and you cannot read a word of it now. Could the surgery let me have a new one some time, or tell me "
    "what to do about it? No rush — I know my doses by heart, it is only the card."
)

ELDERWELL_RECALL_TEXT = (
    "Harold Elderwell again — I rang about my washed clinic card earlier. My son Graham says I am to "
    "ring it in properly, so here it is for the record: I was up half the night vomiting, some potted "
    "shrimp I suspect, and I have kept nothing down since supper. It has settled to queasiness this "
    "morning. Graham likes these things written down, and he says I am to ask whether the surgery "
    "wants to do anything with it or just note it — I told him a note would do, but I promised to "
    "ask, and he can run me down at any time today."
)

#: Split-twin phone-probe answers: the shrimp night and the private clinic's tablet in
#: passing, decisive name withheld, no same-day rule.
ELDERWELL_SPLIT_FACTS = {
    "onset": (
        "I was up half the night with some potted shrimp, I suspect; it has settled to queasiness this "
        "morning."
    ),
    "severity": "Queasy and hollow after a bad night, nothing dramatic. My son fusses more than I do.",
    "medications": (
        "The lithium morning and night, my waterworks capsule — and a new tablet the private heart "
        "clinic started last week; the name is on their letter, not in my head."
    ),
}

pt_farnroyd = _caller(
    "pt_farnroyd",
    "Sheila Farnroyd",
    62,
    "F",
    chart=(
        "Bipolar affective disorder, stable on lithium carbonate 600 mg at night.",
        "Lithium levels at the practice's mental health clinic; last level a month ago, in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 600 mg nightly, levothyroxine 75 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I sing with the choral society and half the sopranos are down with what the ones who saw "
        "a doctor are calling norovirus — and now it has me. It started yesterday lunchtime, both ends, "
        "if you will forgive the detail, and today I am wrung out and can barely face sips of squash.\n\n"
        "The reason I am ringing rather than riding it out: I take lithium, and the mental health clinic "
        "have said the same sentence at every review — a sickness-and-diarrhoea thing that goes past a "
        "day and will not let your drinks stay down is not ridden out on lithium, the level is to be "
        "checked at the clinic that same day. Their bloods are done by five.\n\n"
        "Beyond wrung out and thirsty I am all right in myself."
    ),
    onset="Yesterday lunchtime, the same bug half the choir has. Both ends, and today all wrung out.",
    severity="Wrung out and thirsty, keeping only sips. Nothing frightening — it is the level that matters.",
    history="The bipolar, steady on lithium for years, levels at your mental health clinic.",
    medications="The lithium at night, and my thyroid tablet.",
    context="My husband is home today and can drive me down whenever.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_norovirus_level_today",
)

FARNROYD_SPLIT_INTAKE = (
    "Hello. Only housekeeping — we have finally gone over to a new telephone number at home and I want it "
    "changed on my records before the old line is cut off next week. Have you a pen?\n\n"
    "You will hear it in my voice — the bug going round the choral society reached me yesterday "
    "lunchtime, so I am croaking rather. I am keeping to the sofa and taking it quietly today; it is "
    "just the number I am ringing about."
)

FARNROYD_RECALL_TEXT = (
    "It is Sheila Farnroyd — I rang earlier about changing my telephone number, and my husband says to "
    "ring back and report myself while I am at it. The ones in the choir who saw a doctor are calling it "
    "norovirus, and I am still poorly with it — both ends, if you will forgive the detail, and I can "
    "barely face sips of squash now. He wanted it written down with the surgery that I said so — and he "
    "says to ask whether there is anything the surgery would want doing while it is like this, or "
    "whether we sit tight. He is home today and can drive me down whenever."
)

#: Split-twin phone-probe answers: the settling half of the bug, without the clinic's
#: sentence about it or the still-going both-ends tally her ring-back carries on another desk.
FARNROYD_SPLIT_FACTS = {
    "onset": (
        "The bug going round the choir reached me yesterday lunchtime. I am taking it quietly on the "
        "sofa today."
    ),
    "severity": "Wrung out and croaky — I am keeping to the sofa today. Nothing frightening in myself.",
}

pt_easholm = _caller(
    "pt_easholm",
    "Kenneth Easholm",
    70,
    "M",
    chart=(
        "Bipolar disorder, stable on lithium carbonate 250 mg, two tablets at night.",
        "Lithium levels at the practice's mental health clinic; annual review due in the next quarter. "
        "Last level in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 250 mg, two nightly; simvastatin 40 mg.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I have been fighting a sickness bug since the weekend — I thought it had done with me "
        "yesterday, but I am still off my food and I have hardly wet my whistle in three days, as my "
        "neighbour keeps pointing out.\n\n"
        "I take lithium at night and have done for donkey's years. The clinic here that does my levels "
        "told me straight when I started: if ever a bug keeps you from eating and drinking for more than "
        "a day or so, they want blood off you the same day, not at the next routine test — the level "
        "rises quietly while you are dried out. And they only take bloods up until five.\n\n"
        "I am not poorly in any dramatic way — tired, dry, and my hands not as steady as usual, that is "
        "the size of it."
    ),
    onset="The bug took me at the weekend. The eating and drinking have not come back since.",
    severity="Tired and dry, hands not quite steady. Nothing dramatic — it is the level that wants doing.",
    history="The bipolar, on lithium more years than I can count, watched at your mental health clinic.",
    medications="The lithium at night and a statin.",
    context="My neighbour Mrs Farnthwaite keeps an eye on me and can walk me round any time.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_dry_three_days_level_today",
)

EASHOLM_SPLIT_INTAKE = (
    "Morning. My annual review letter says to bring a urine sample in a little bottle, and the little "
    "bottle has gone missing in this house the way they do. Can I collect another from the desk when I "
    "am passing?\n\n"
    "I have been fighting a sickness bug since the weekend, I should say — I thought it had done with me "
    "yesterday, and I am up and about. That is the whole of my troubles this morning."
)

#: Split-twin phone-probe answers: the settling half only — no still-going tally, no "the
#: level wants doing"; his neighbour carries the rest on another desk.
EASHOLM_SPLIT_FACTS = {
    "onset": (
        "The bug took me at the weekend; I thought it had done with me yesterday, and I am up and about."
    ),
    "severity": (
        "Tired and dry, hands not quite steady. Nothing dramatic — my neighbour fusses enough for the "
        "two of us."
    ),
}

pt_elderridge = _caller(
    "pt_elderridge",
    "Joyce Elderridge",
    64,
    "F",
    chart=(
        "Bipolar affective disorder, stable on lithium carbonate 450 mg at night.",
        "Lithium levels at the practice's mental health clinic; carries the clinic's monitoring card. "
        "Last level in range.",
        CLINIC_ADVICE_LINE,
        "History of uncomplicated cystitis, self-managed with advice in the past.",
        "Repeat medication: lithium carbonate 450 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think I have a water infection — burning when I go, and going every half hour, since "
        "yesterday. I was hot and cold in the night with it, settled by morning, and the drinking side has gone wrong "
        "too: everything tastes of metal and I have taken barely a cupful since yesterday teatime.\n\n"
        "Now, the infection itself I know the routine for — I have had cystitis enough times. The reason "
        "I am ringing first thing is the lithium. The mental health clinic do my levels, and the "
        "instruction printed on my card is that an infection with a temperature, or a day of barely "
        "drinking, means the level is drawn at the clinic the same day. Both of those are me this "
        "morning. Their bloods finish before five o'clock."
    ),
    onset="The burning started yesterday; hot and cold in the night, settled by morning, and barely drinking since teatime.",
    severity=(
        "Sore and weary and off my drinks, with that metal taste. Nothing worse — I know cystitis of old."
    ),
    history="The bipolar, on lithium for years, levels at your mental health clinic. Cystitis now and then.",
    medications="Just the lithium at night.",
    context="My husband is in and out today; either of us can be there in a quarter of an hour.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_uti_fever_dry_level_today",
)

ELDERRIDGE_SPLIT_INTAKE = (
    "Hello. I think I have a water infection coming on — burning when I go, since yesterday. I have had "
    "cystitis plenty of times and I know the routine. I am only ringing to ask whether I can drop a "
    "sample in at the desk this morning for testing, the way I did last time."
)

ELDERRIDGE_RECALL_TEXT = (
    "Joyce Elderridge — I rang this morning about dropping a sample in for the water infection. My "
    "husband says I under-sold it on the phone, so let me put the record straight: I was hot and cold "
    "in the night with it — settled by morning — and I have drunk barely a cupful since yesterday "
    "teatime; everything tastes of metal. He wanted that noted alongside the sample — and he says to "
    "ask whether the surgery would want to see me over any of it, or whether the sample covers it. "
    "Either of us can be there in a quarter of an hour."
)

#: Split-twin phone-probe answers: the canonical onset spoke the decisive night and her card
#: makes a day of barely drinking same-day-sufficient on its own, so both probed answers hedge the
#: drinking clause; her ring-back carries the night and the cupful tally on another desk.
ELDERRIDGE_SPLIT_FACTS = {
    "onset": (
        "The burning started yesterday, and I have not fancied my drinks with it — everything tastes "
        "of metal."
    ),
    "severity": (
        "Sore and weary, and I have not fancied my drinks with that metal taste. Nothing worse — I "
        "know cystitis of old."
    ),
}

pt_farnsett = _caller(
    "pt_farnsett",
    "Albert Farnsett",
    73,
    "M",
    chart=(
        "Bipolar disorder of long standing; lithium carbonate 400 mg at night for several decades.",
        "Lithium levels at the practice's mental health clinic; last level eight weeks ago, in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 400 mg nightly, amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My daughter has stood over me until I rang, so here I am. I have had diarrhoea since "
        "Friday — the best part of a week now — and though it is easing, I have eaten like a sparrow all "
        "that time and drunk not much better.\n\n"
        "I have been on lithium since before my daughter was born, near enough, and I know the drill as "
        "well as anybody: the clinic wants a level the same day when your insides have been off this "
        "long, because the level creeps up while you are run dry. I kept thinking each day it would "
        "settle and I would be spared the fuss. My daughter says a week is a week, and she is right.\n\n"
        "The clinic's bloods want doing before five. In myself I am only tired and a bit hollow."
    ),
    onset="Friday. Easing now, but I have eaten and drunk next to nothing all the while.",
    severity="Tired and hollow, nothing sharper. It is the length of it that breaks the clinic's rule.",
    history="The bipolar, on lithium for decades, levels at your mental health clinic.",
    medications="The lithium at night and a blood-pressure tablet in the morning.",
    context="My daughter Karen can fetch me down at any hour today; she has the day off.",
    gold=board_gold(MENTAL_HEALTH),
    source="authored:lithium_week_of_diarrhoea_level_today",
)

FARNSETT_SPLIT_INTAKE = (
    "Morning. A pharmacy muddle, nothing more — my repeat slip has the lithium printed twice in two "
    "different strengths, and the chemist wants the surgery to tidy it before the next issue. Could "
    "someone straighten the slip when there is a minute? No rush on my account."
)

#: Split-twin phone-probe answers: the clinic's rule and the week-long tally stay out of his
#: answers; his daughter carries the week's tally on another desk.
FARNSETT_SPLIT_FACTS = {
    "onset": "My insides have been off, but it is easing; it is the repeat slip I rang about.",
    "severity": "Tired and hollow, nothing sharper. My daughter makes more of it than I do.",
}

# ══ the five carriers (dual-purpose callers: their own routine matter; the split twin adds the fact) ══════
pt_easwell_j = _caller(
    "pt_easwell_j",
    "June Easwell",
    74,
    "F",
    chart=(
        "Osteoarthritis of both knees, managed with topical treatment and paracetamol.",
        "Repeat medication: capsaicin cream, paracetamol 500 mg as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, it is June Easwell. I am ringing for my own repeat — the cream for my knees; the chemist "
        "says there is nothing left on the authorisation. No hurry at all; the tub sees me out the week."
    ),
    onset="Nothing new — the repeat has simply run out.",
    severity="I am quite well. The knees are their usual selves.",
    history="The knees, wearing as knees do. Otherwise nothing.",
    medications="The cream, and paracetamol when they grumble.",
    context="At home all day. My husband Wilfred is a patient here too.",
    gold=_routine_gold(),
    source="authored:lithium_carrier_knee_cream_repeat",
)

EASWELL_J_SPLIT_INTAKE = (
    "Hello, it is June Easwell. I am ringing for my own repeat — the cream for my knees; the chemist "
    "says there is nothing left on the authorisation. No hurry at all; the tub sees me out the week.\n\n"
    "Oh — and while I am on: my husband Wilfred said he rang you this morning about the new tablet the "
    "private clinic started him on, and of course he never had the name. I have their letter here in my "
    "bag, so let me read it out for his record: bendroflumethiazide, one each morning, started today. "
    "There — now your list matches their letter. And while you have his record open, the letter says to "
    "ask his own surgery, so I am asking: is there anything he needs doing off the back of a new "
    "tablet, or does the note cover it? We are ten minutes away all day, whichever it is."
)

pt_eldermead = _caller(
    "pt_eldermead",
    "Phyllis Eldermead",
    70,
    "F",
    chart=(
        "Gastro-oesophageal reflux, stable on lansoprazole; annual medication review up to date.",
        "Repeat medication: lansoprazole 15 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Phyllis Eldermead. Only my repeat — the stomach tablet, lansoprazole — the chemist says "
        "the authorisation has run out again. Could it be sorted this week? There is no hurry; I have a "
        "strip and a half left."
    ),
    onset="Nothing new — it is the authorisation, not me.",
    severity="Perfectly well. It is paperwork.",
    history="The reflux, settled for years on the same tablet.",
    medications="The lansoprazole, one in the morning.",
    context="At home all day. I do a bit of shopping for my neighbour across the road.",
    gold=_routine_gold(),
    source="authored:lithium_carrier_lansoprazole_repeat",
)

ELDERMEAD_SPLIT_INTAKE = (
    "Hello, Phyllis Eldermead. Only my repeat — the stomach tablet, lansoprazole — the chemist says the "
    "authorisation has run out again. Could it be sorted this week? No hurry; I have a strip and a half "
    "left.\n\n"
    "And while I am on: I do a bit of shopping for my neighbour across the road, Mr Farncliffe. He still "
    "has the runs — that bug his grandchildren brought home — and he is right off his food with it, "
    "whatever he tells you. He would sooner lose a leg than ring twice, so I said I would ask outright "
    "while I rang: is that something he ought to be seen about, or that the surgery would want him in "
    "for? He will never ask himself, and I can walk him down with me if he is wanted."
)

pt_elderwell_g = _caller(
    "pt_elderwell_g",
    "Graham Elderwell",
    49,
    "M",
    chart=(
        "Mild eczema, flares managed with emollients and occasional topical steroid.",
        "Repeat medication: emollient, hydrocortisone 1% cream as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Graham Elderwell. I am after a routine appointment for myself about travel jabs — work is "
        "sending me abroad in a couple of months and the occupational nurse said to see my own surgery "
        "about what I need. Any day that suits; there is plenty of time."
    ),
    onset="Nothing the matter — it is jabs for a work trip.",
    severity="Fit and well.",
    history="A bit of eczema, nothing else.",
    medications="Just the creams, when the eczema plays up.",
    context="I work in town and can take a long lunch most days. My father Harold is a patient here.",
    gold=_routine_gold(),
    source="authored:lithium_carrier_travel_jabs",
)

ELDERWELL_G_SPLIT_INTAKE = (
    "Hello, Graham Elderwell. I am after a routine appointment for myself about travel jabs — work is "
    "sending me abroad in a couple of months and the occupational nurse said to see my own surgery. Any "
    "day that suits; there is plenty of time.\n\n"
    "Also, while I have you — my father, Harold Elderwell, is a patient with you. A private heart clinic "
    "started him on a water tablet last week for his pressure, and their letter says his own surgery "
    "should be told — dad thinks the surgery has better things to do than his paperwork, which is "
    "exactly why I am the one telling you. And since I have you: if anything wants arranging off the "
    "back of a new tablet, better it goes through me now than waits for dad to volunteer — I ring him "
    "daily and can run him down at any time."
)

pt_farnthwaite = _caller(
    "pt_farnthwaite",
    "Brenda Farnthwaite",
    68,
    "F",
    chart=(
        "Hypertension, well controlled on losartan; blood-pressure check due around this time of year.",
        "Repeat medication: losartan 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Brenda Farnthwaite. I am due a blood-pressure check some time this month by my book — "
        "could a routine one be put in whenever suits? There is no hurry about it at all."
    ),
    onset="Nothing new — it is the yearly check coming round.",
    severity="I am well. The machine at home behaves itself.",
    history="The blood pressure, steady on one tablet for years.",
    medications="The losartan, one in the morning.",
    context="Retired; I keep an eye on my neighbour Mr Easholm, who is on his own.",
    gold=_routine_gold(),
    source="authored:lithium_carrier_bp_check",
)

FARNTHWAITE_SPLIT_INTAKE = (
    "Hello, Brenda Farnthwaite. I am due a blood-pressure check some time this month by my book — could "
    "a routine one be put in whenever suits? No hurry about it at all.\n\n"
    "And might I mention my neighbour, Kenneth Easholm — I keep an eye on him. He has been poorly with "
    "that bug that is going round and he is still not eating, and he is barely wetting his whistle as "
    "far as I can see, whatever he says about being up and about. You would wait a long time for him to "
    "say so himself, so there it is from me — write it down against his name, would you, and tell me "
    "straight: is that something the surgery would want him seen about, or do we let him ride it out? "
    "I can walk him round myself at any hour if he is wanted."
)

pt_farnsett_k = _caller(
    "pt_farnsett_k",
    "Karen Farnsett",
    45,
    "F",
    chart=(
        "Cervical screening due; reminder letter issued.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Karen Farnsett — I am ringing to book my routine smear; the reminder letter came last "
        "week. Mornings suit me best, any week. That is the only thing on my list."
    ),
    onset="Nothing the matter — the reminder letter came, that is all.",
    severity="Perfectly well.",
    history="Nothing of note.",
    medications="None.",
    context="I have the day off today, as it happens. My father Albert is a patient here.",
    gold=_routine_gold(),
    source="authored:lithium_carrier_smear_booking",
)

FARNSETT_K_SPLIT_INTAKE = (
    "Hello, Karen Farnsett — I am ringing to book my routine smear; the reminder letter came last week. "
    "Mornings suit me best, any week.\n\n"
    "Separately — my dad, Albert Farnsett, is one of yours. He has had diarrhoea since Friday, the best "
    "part of a week now, and he is eating next to nothing with it and drinking not much better. If I "
    "know him he rang you this morning about his repeat slip and never said a word of it, so I am "
    "filling the gap — put it on his record that his daughter reported it, and tell me whether the "
    "surgery would want him in over it, because left to himself he will ride it out till Christmas. "
    "I have the day off and can fetch him down at any hour."
)

# ══ the three decoys (urgent-sounding, correctly NOT bumped) and the split defuser ════════════════════════
pt_eassett = _caller(
    "pt_eassett",
    "Marjorie Eassett",
    69,
    "F",
    chart=(
        "Bipolar affective disorder, stable on lithium carbonate 400 mg at night.",
        "Lithium level drawn at the mental health clinic a fortnight ago; reported in range. Next "
        "routine level not yet due.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 400 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. There was a column in the Sunday paper about lithium — I take it — and how drying out "
        "can push the level up before you feel a thing wrong. It rather got under my skin and I have "
        "been fretting since.\n\n"
        "I should say straight away: I am perfectly well. I am eating and drinking as normal, no bugs, no "
        "new tablets, and the clinic drew my level not a fortnight ago and rang to say it was spot on. My "
        "husband thinks I want telling as much.\n\n"
        "Could I book an ordinary appointment, whenever there is one, just to talk my tablets over? There "
        "is no urgency about me — I know the clinic keep a proper eye."
    ),
    onset="Nothing has happened to me — it was a piece in the Sunday paper that set me fretting.",
    severity="I am entirely well. Eating, drinking, sleeping as normal.",
    history="The bipolar, on lithium for years, levels always in range at your clinic.",
    medications="The lithium at night, nothing else, and nothing new.",
    context="At home; any day at all suits for an ordinary appointment.",
    gold=_routine_gold(),
    source="authored:lithium_decoy_radio_fret_defused",
)

pt_farnby = _caller(
    "pt_farnby",
    "Derek Farnby",
    61,
    "M",
    chart=(
        "Hypertension, on amlodipine 5 mg daily; last review six months ago.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I want to get looked at some time, though I have been told it is not urgent, so let me "
        "give it to you straight.\n\n"
        "The out-of-hours doctor changed my blood-pressure prescription at the weekend. This morning, "
        "first thing, I came over dizzy getting out of bed — it passed inside a minute once I sat down, "
        "and there has been nothing since breakfast. I walked round to the chemist and the pharmacist sat "
        "me down, checked my pressure, said it was fine and that this can happen in the first days on a "
        "changed dose — stand up slowly, and let the surgery know so the dose gets a routine review.\n\n"
        "So that is me letting you know: a routine review, whenever there is a gap."
    ),
    onset="This morning, once, standing up from bed. Gone inside a minute and nothing since.",
    severity="Nothing now at all. The pharmacist checked me over and was not concerned.",
    history="Blood pressure, on one tablet for years. Nothing else.",
    medications="The blood-pressure tablet, on the dose the out-of-hours doctor set at the weekend.",
    context="Semi-retired; I can come in any day. The chemist's advice was routine review, no rush.",
    gold=_routine_gold(),
    source="authored:lithium_decoy_dizzy_dose_change_defused",
)

pt_elderthwaite = _caller(
    "pt_elderthwaite",
    "Iris Elderthwaite",
    72,
    "F",
    chart=(
        "Bipolar affective disorder, stable on lithium carbonate 400 mg at night.",
        "Lithium levels at the practice's mental health clinic; an interim level was drawn late last "
        "week and reported in range.",
        CLINIC_ADVICE_LINE,
        "Repeat medication: lithium carbonate 400 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I take lithium, and I had that bug that is doing the rounds — off my food most of last "
        "week with it, and I know what the clinic says about bugs and blood tests, so I nearly pressed "
        "the panic button this morning.\n\n"
        "But let me be fair about it: the sickness passed off on Sunday, I have eaten and drunk properly "
        "since Monday — three good days now — and the clinic took my level on Friday, while it was still "
        "going on, and rang Monday to say it had come back fine. So the moment has rather passed, as my "
        "daughter puts it.\n\n"
        "What I would like is an ordinary appointment in the next week or two, to be looked over after "
        "it. Nothing more than that."
    ),
    onset="The bug was last week; it passed off on Sunday and I have been right since Monday.",
    severity="Well again — eating and drinking properly for three days. The level was checked and fine.",
    history="The bipolar, on lithium for years, levels at your mental health clinic.",
    medications="The lithium at night, nothing new.",
    context="My daughter Gail rings me every morning; any day in the next fortnight suits.",
    gold=_routine_gold(),
    source="authored:lithium_decoy_bug_over_level_done_defused",
)

ELDERTHWAITE_SPLIT_INTAKE = (
    "Hello. I take lithium, and I had that bug that is doing the rounds — off my food most of last week "
    "with it. I know what the clinic says about bugs and blood tests on lithium, and my daughter said one "
    "of us should ring the surgery, so that is what I am doing. I would like somebody to tell me what "
    "ought to happen with me."
)

pt_elderthwaite_d = _caller(
    "pt_elderthwaite_d",
    "Gail Elderthwaite",
    47,
    "F",
    chart=(
        "Seasonal allergic rhinitis; managed with over-the-counter antihistamines most years.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, Gail Elderthwaite. I am ringing for myself — I want a routine appointment about my hay "
        "fever before the season gets going properly; last spring caught me out and I spent a month "
        "sneezing. Any day in the next few weeks is fine."
    ),
    onset="Nothing yet — I am getting ahead of the season for once.",
    severity="Perfectly well today.",
    history="Hay fever every spring, otherwise nothing.",
    medications="Antihistamines from the chemist, in season.",
    context="I work part-time and am flexible. My mother Iris is a patient here.",
    gold=_routine_gold(),
    source="authored:lithium_defuser_hay_fever",
)

ELDERTHWAITE_D_SPLIT_INTAKE = (
    "Hello, Gail Elderthwaite. I am ringing for myself — I want a routine appointment about my hay fever "
    "before the season gets going properly; last spring caught me out. Any day in the next few weeks is "
    "fine.\n\n"
    "And if my mother rings you about the bug she had — Iris Elderthwaite, she does like a drama, "
    "bless her — for the record: it passed off on Sunday, she has eaten and drunk properly since Monday, "
    "and the clinic took her level on Friday while it was still on and rang Monday to say it came back "
    "fine. She could do with an ordinary look-over some time, nothing today."
)

# ══ the ten holders (calendar-only; a holder's intake is what they say if a desk RINGS them) ══════════════
pt_elderby = _caller(
    "pt_elderby",
    "Norman Elderby",
    69,
    "M",
    chart=(
        "Bipolar disorder, stable on lithium; annual lithium review and level due at the mental health "
        "clinic.",
        "Repeat medication: lithium carbonate 400 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon, yes — my yearly lithium going-over. It took three weeks on the list to get it, "
        "and my neighbour has moved his darts night to drive me in. I would as soon keep it as it stands."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. The appointment is the routine yearly one.",
    history="The bipolar, on lithium a long while, reviewed yearly at the clinic.",
    medications="The lithium at night.",
    context="My neighbour has rearranged his week to drive me in this afternoon.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_annual_review_elderby",
)

pt_farncote = _caller(
    "pt_farncote",
    "Hilda Farncote",
    76,
    "F",
    chart=(
        "Recurrent depression, stable on mirtazapine; yearly medication review at the mental health "
        "clinic.",
        "Repeat medication: mirtazapine 30 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my medication review, this afternoon. My daughter has taken the afternoon off her work to "
        "bring me, and those afternoons do not grow on trees, I can tell you."
    ),
    onset="Nothing new; the yearly review came round.",
    severity="I am steady, thank you. It is the routine look at my tablets.",
    history="The low moods, settled for a good while on the same tablet.",
    medications="The mirtazapine at night.",
    context="My daughter has arranged the afternoon off specially to bring me.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_medication_review_farncote",
)

pt_easby = _caller(
    "pt_easby",
    "Leonard Easby",
    58,
    "M",
    chart=(
        "Depression, improving; sertraline dose adjusted at the last visit, follow-up review booked at "
        "the mental health clinic.",
        "Repeat medication: sertraline 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is my follow-up since they moved my dose up — this afternoon. I swapped my shift at the "
        "depot to be free for it, and swapping back is a palaver I could do without."
    ),
    onset="Nothing new; the review was booked when the dose changed.",
    severity="Doing well on the new dose. The visit is the planned check on it.",
    history="The depression, on the mend; the tablet dose went up recently.",
    medications="The sertraline, one a day.",
    context="I swapped a depot shift for this afternoon; it cannot easily be swapped again.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_dose_follow_up_easby",
)

pt_eldercote = _caller(
    "pt_eldercote",
    "Winifred Eldercote",
    81,
    "F",
    chart=(
        "Generalised anxiety, stable; periodic review at the mental health clinic.",
        "Repeat medication: sertraline 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My nerves appointment, this afternoon, yes. The sheltered housing minibus is booked for me "
        "specially — the warden wrote it in the book — and rearranging the minibus is a week's job."
    ),
    onset="Nothing new; it is the periodic review.",
    severity="I am as I always am. The visit is routine.",
    history="The nerves, steady for a long while on the same tablet.",
    medications="The sertraline in the morning.",
    context="The sheltered housing minibus is booked for this afternoon, through the warden.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_anxiety_review_eldercote",
)

pt_farnden = _caller(
    "pt_farnden",
    "Colin Farnden",
    54,
    "M",
    chart=(
        "Bipolar disorder, well for years on lithium; annual review at the mental health clinic.",
        "Repeat medication: lithium carbonate 600 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly bipolar review, this afternoon. I booked the half day off work for it and my "
        "supervisor made a face doing it — I would rather not go back and ask twice."
    ),
    onset="Nothing new; it is the annual review.",
    severity="I am well — the yearly check is the routine one.",
    history="The bipolar, well controlled for years on lithium.",
    medications="The lithium at night.",
    context="Half a day booked off work, grudgingly granted, for this afternoon.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_annual_review_farnden",
)

pt_easridge = _caller(
    "pt_easridge",
    "Mabel Easridge",
    79,
    "F",
    chart=(
        "Recurrent depression, stable; yearly review of antidepressant at the mental health clinic.",
        "Repeat medication: citalopram 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my tablets review, this afternoon. My nephew comes over between his shifts to take me, and "
        "this week the only afternoon he can do is this one."
    ),
    onset="Nothing new; the yearly review came round.",
    severity="I am quite steady. It is the routine review of my tablet.",
    history="The low times, settled for years on the same tablet.",
    medications="The citalopram in the morning.",
    context="My nephew is only free this afternoon this week, and he is my lift.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_tablet_review_easridge",
)

pt_eldersett = _caller(
    "pt_eldersett",
    "Raymond Eldersett",
    66,
    "M",
    chart=(
        "Post-traumatic stress disorder, stable; routine follow-up at the mental health clinic.",
        "Repeat medication: mirtazapine 15 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "My follow-up, this afternoon, that is right. I have the taxi booked and paid both ways — they "
        "charge you either way if you cancel on the day, so I am rather set on keeping it."
    ),
    onset="Nothing new; it is the routine follow-up.",
    severity="I am steady. The appointment is the planned routine one.",
    history="The PTSD, managed a long while; routine follow-ups at the clinic.",
    medications="The mirtazapine at night.",
    context="A pre-paid taxi is booked both ways for this afternoon.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_ptsd_follow_up_eldersett",
)

pt_farnwell = _caller(
    "pt_farnwell",
    "Dorothy Farnwell",
    72,
    "F",
    chart=(
        "Bipolar disorder, stable on lithium; annual lithium review due at the mental health clinic.",
        "Repeat medication: lithium carbonate 400 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly lithium review, this afternoon. My son is up visiting just these two days and he "
        "takes me to these — after he goes home it is two buses each way for me."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well in myself. The visit is the routine yearly one.",
    history="The bipolar, steady on lithium for many years.",
    medications="The lithium at night.",
    context="My son is visiting for two days only and is my lift this afternoon.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_annual_review_farnwell",
)

pt_easgill = _caller(
    "pt_easgill",
    "Ernest Easgill",
    75,
    "M",
    chart=(
        "Recurrent depression, in long remission; yearly review at the mental health clinic.",
        "Repeat medication: venlafaxine 75 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is my yearly looking-over, this afternoon. The chap next door runs me in when he can, and "
        "today he can — next week he is away at his sister's, so today rather suits us both."
    ),
    onset="Nothing new; the yearly review came round.",
    severity="I keep well. It is the routine yearly visit.",
    history="The depression, long settled on the same tablet.",
    medications="The venlafaxine in the morning.",
    context="The neighbour who drives me is only available today; he is away next week.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_yearly_review_easgill",
)

pt_elderlund = _caller(
    "pt_elderlund",
    "Gwen Elderlund",
    63,
    "F",
    chart=(
        "Recurrent depression, stable; medication review due at the mental health clinic.",
        "Repeat medication: fluoxetine 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablets review, this afternoon, yes. I am on nights all next week — today is the one day I "
        "am neither working nor sleeping, which is why I took the slot they offered."
    ),
    onset="Nothing new; the review came round.",
    severity="I am steady, thank you. It is the routine review.",
    history="The depression, settled for years on the same tablet.",
    medications="The fluoxetine in the morning.",
    context="Night shifts all next week; today is the only workable day.",
    gold=_holder_gold(MENTAL_HEALTH),
    source="authored:lithium_holder_medication_review_elderlund",
)

CARDS = (
    # claimants
    pt_farnbrook,
    pt_easwell,
    pt_elderbrook,
    pt_farncliffe,
    pt_easmead,
    pt_elderwell,
    pt_farnroyd,
    pt_easholm,
    pt_elderridge,
    pt_farnsett,
    # carriers
    pt_easwell_j,
    pt_eldermead,
    pt_elderwell_g,
    pt_farnthwaite,
    pt_farnsett_k,
    # decoys + the split defuser
    pt_eassett,
    pt_farnby,
    pt_elderthwaite,
    pt_elderthwaite_d,
    # holders
    pt_elderby,
    pt_farncote,
    pt_easby,
    pt_eldercote,
    pt_farnden,
    pt_easridge,
    pt_eldersett,
    pt_farnwell,
    pt_easgill,
    pt_elderlund,
)

#: The sanctioned same-surname shapes: family carriers/defusers on the same board as their patient.
KIN_OF = {
    "pt_easwell_j": "pt_easwell",
    "pt_elderwell_g": "pt_elderwell",
    "pt_farnsett_k": "pt_farnsett",
    "pt_elderthwaite_d": "pt_elderthwaite",
}

# ══ the board skeleton (shared by both twins byte-for-byte) ═══════════════════════════════════════════════
CONTESTS = (
    BoardContest(
        claimant="pt_farnbrook",
        holder="pt_elderby",
        specialty=MENTAL_HEALTH,
        provider_id="dr_farnholm",
        slot_hhmm="13:00",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual lithium review + level (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="stomach bug",
    ),
    BoardContest(
        claimant="pt_easwell",
        holder="pt_farncote",
        specialty=MENTAL_HEALTH,
        provider_id="dr_farnholm",
        slot_hhmm="14:40",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Yearly antidepressant medication review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="bendroflumethiazide",
    ),
    BoardContest(
        claimant="pt_elderbrook",
        holder="pt_easby",
        specialty=MENTAL_HEALTH,
        provider_id="dr_farnholm",
        slot_hhmm="16:20",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Follow-up after antidepressant dose change (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="hardly drunk a thing",
    ),
    BoardContest(
        claimant="pt_farncliffe",
        holder="pt_eldercote",
        specialty=MENTAL_HEALTH,
        provider_id="dr_eldergill",
        slot_hhmm="13:20",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Periodic anxiety review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="the runs",
    ),
    BoardContest(
        claimant="pt_easmead",
        holder="pt_farnden",
        specialty=MENTAL_HEALTH,
        provider_id="dr_eldergill",
        slot_hhmm="15:00",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual bipolar review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="indapamide",
    ),
    BoardContest(
        claimant="pt_elderwell",
        holder="pt_easridge",
        specialty=MENTAL_HEALTH,
        provider_id="dr_eldergill",
        slot_hhmm="16:40",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Yearly antidepressant review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="water tablet",
    ),
    BoardContest(
        claimant="pt_farnroyd",
        holder="pt_eldersett",
        specialty=MENTAL_HEALTH,
        provider_id="dr_easgarth",
        slot_hhmm="13:40",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Routine PTSD follow-up (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="norovirus",
    ),
    BoardContest(
        claimant="pt_easholm",
        holder="pt_farnwell",
        specialty=MENTAL_HEALTH,
        provider_id="dr_easgarth",
        slot_hhmm="15:20",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual lithium review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="sickness bug",
    ),
    BoardContest(
        claimant="pt_elderridge",
        holder="pt_easgill",
        specialty=MENTAL_HEALTH,
        provider_id="dr_farnlund",
        slot_hhmm="13:40",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Yearly depression review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="hot and cold in the night",
    ),
    BoardContest(
        claimant="pt_farnsett",
        holder="pt_elderlund",
        specialty=MENTAL_HEALTH,
        provider_id="dr_farnlund",
        slot_hhmm="15:20",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Medication review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="diarrhoea since Friday",
    ),
)

#: Arrival plan, identical across the twins (the split adds RECALL beats, which are call structure).
ARRIVALS = (
    ("pt_farnbrook", "C", 0),
    ("pt_easwell", "A", 7),
    ("pt_lachaux", "B", 13),
    ("pt_elderbrook", "D", 19),
    ("pt_farncliffe", "B", 26),
    ("pt_eassett", "A", 33),
    ("pt_easmead", "C", 40),
    ("pt_dunmore", "D", 47),
    ("pt_elderwell", "B", 54),
    ("pt_easwell_j", "D", 60),
    ("pt_farnroyd", "A", 67),
    ("pt_elderthwaite", "C", 74),
    ("pt_ledwidge", "A", 81),
    ("pt_easholm", "D", 88),
    ("pt_eldermead", "A", 95),
    ("pt_elderridge", "B", 102),
    ("pt_farnthwaite", "B", 109),
    ("pt_elderwell_g", "C", 115),
    ("pt_farnsett", "A", 122),
    ("pt_farnsett_k", "C", 129),
    ("pt_farnby", "C", 136),
    ("pt_elderthwaite_d", "D", 142),
    ("pt_arundel", "B", 148),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

MEMO_COVER_LINE = (
    "There is a rotten gut bug going round the town this week and the phones have been heavy with it "
    "every morning."
)

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=10,
    theme_slug="lithium_dehydration",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=tuple(
        EvidenceCall(caller_id=contest.claimant, about_claimant=contest.claimant)
        for contest in CONTESTS
    ),
    decoys=(
        Decoy(patient_id="pt_eassett"),
        Decoy(patient_id="pt_farnby"),
        Decoy(patient_id="pt_elderthwaite"),
    ),
    cards=CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=10,
    theme_slug="lithium_dehydration",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=(
        # pt_farnbrook: routine repeat call (C) + her own ring-back (A).
        EvidenceCall(caller_id="pt_farnbrook", about_claimant="pt_farnbrook"),
        EvidenceCall(
            caller_id="pt_farnbrook",
            about_claimant="pt_farnbrook",
            kind="recall",
            at_min=75,
            desk="A",
            text=FARNBROOK_RECALL_TEXT,
        ),
        # pt_easwell: blood-test diary query (A) + his wife's call (D).
        EvidenceCall(caller_id="pt_easwell", about_claimant="pt_easwell"),
        EvidenceCall(caller_id="pt_easwell_j", about_claimant="pt_easwell"),
        # pt_elderbrook: dentist's-note query (D) + her own ring-back (B).
        EvidenceCall(caller_id="pt_elderbrook", about_claimant="pt_elderbrook"),
        EvidenceCall(
            caller_id="pt_elderbrook",
            about_claimant="pt_elderbrook",
            kind="recall",
            at_min=85,
            desk="B",
            text=ELDERBROOK_RECALL_TEXT,
        ),
        # pt_farncliffe: monitoring-card diary query (B) + his neighbour's call (A).
        EvidenceCall(caller_id="pt_farncliffe", about_claimant="pt_farncliffe"),
        EvidenceCall(caller_id="pt_eldermead", about_claimant="pt_farncliffe"),
        # pt_easmead: record-keeping call (C) + her own ring-back (D).
        EvidenceCall(caller_id="pt_easmead", about_claimant="pt_easmead"),
        EvidenceCall(
            caller_id="pt_easmead",
            about_claimant="pt_easmead",
            kind="recall",
            at_min=95,
            desk="D",
            text=EASMEAD_RECALL_TEXT,
        ),
        # pt_elderwell, THREE pieces: washed-card call (B) + his son's call (C) + his ring-back (A).
        EvidenceCall(caller_id="pt_elderwell", about_claimant="pt_elderwell"),
        EvidenceCall(caller_id="pt_elderwell_g", about_claimant="pt_elderwell"),
        EvidenceCall(
            caller_id="pt_elderwell",
            about_claimant="pt_elderwell",
            kind="recall",
            at_min=135,
            desk="A",
            text=ELDERWELL_RECALL_TEXT,
        ),
        # pt_farnroyd: phone-number change (A) + her own ring-back (C).
        EvidenceCall(caller_id="pt_farnroyd", about_claimant="pt_farnroyd"),
        EvidenceCall(
            caller_id="pt_farnroyd",
            about_claimant="pt_farnroyd",
            kind="recall",
            at_min=105,
            desk="C",
            text=FARNROYD_RECALL_TEXT,
        ),
        # pt_easholm: sample-bottle query (D) + his neighbour's call (B).
        EvidenceCall(caller_id="pt_easholm", about_claimant="pt_easholm"),
        EvidenceCall(caller_id="pt_farnthwaite", about_claimant="pt_easholm"),
        # pt_elderridge: sample drop-off query (B) + her own ring-back (A).
        EvidenceCall(caller_id="pt_elderridge", about_claimant="pt_elderridge"),
        EvidenceCall(
            caller_id="pt_elderridge",
            about_claimant="pt_elderridge",
            kind="recall",
            at_min=130,
            desk="A",
            text=ELDERRIDGE_RECALL_TEXT,
        ),
        # pt_farnsett: repeat-slip muddle (A) + his daughter's call (C).
        EvidenceCall(caller_id="pt_farnsett", about_claimant="pt_farnsett"),
        EvidenceCall(caller_id="pt_farnsett_k", about_claimant="pt_farnsett"),
    ),
    decoys=(
        Decoy(patient_id="pt_eassett"),
        Decoy(patient_id="pt_farnby"),
        Decoy(patient_id="pt_elderthwaite", defusing_caller_id="pt_elderthwaite_d"),
    ),
    cards=CARDS,
    intake_overrides={
        "pt_farnbrook": FARNBROOK_SPLIT_INTAKE,
        "pt_easwell": EASWELL_SPLIT_INTAKE,
        "pt_elderbrook": ELDERBROOK_SPLIT_INTAKE,
        "pt_farncliffe": FARNCLIFFE_SPLIT_INTAKE,
        "pt_easmead": EASMEAD_SPLIT_INTAKE,
        "pt_elderwell": ELDERWELL_SPLIT_INTAKE,
        "pt_farnroyd": FARNROYD_SPLIT_INTAKE,
        "pt_easholm": EASHOLM_SPLIT_INTAKE,
        "pt_elderridge": ELDERRIDGE_SPLIT_INTAKE,
        "pt_farnsett": FARNSETT_SPLIT_INTAKE,
        "pt_easwell_j": EASWELL_J_SPLIT_INTAKE,
        "pt_eldermead": ELDERMEAD_SPLIT_INTAKE,
        "pt_elderwell_g": ELDERWELL_G_SPLIT_INTAKE,
        "pt_farnthwaite": FARNTHWAITE_SPLIT_INTAKE,
        "pt_farnsett_k": FARNSETT_K_SPLIT_INTAKE,
        "pt_elderthwaite": ELDERTHWAITE_SPLIT_INTAKE,
        "pt_elderthwaite_d": ELDERTHWAITE_D_SPLIT_INTAKE,
    },
    facts_overrides={
        "pt_farnbrook": FARNBROOK_SPLIT_FACTS,
        "pt_easwell": EASWELL_SPLIT_FACTS,
        "pt_elderbrook": ELDERBROOK_SPLIT_FACTS,
        "pt_farncliffe": FARNCLIFFE_SPLIT_FACTS,
        "pt_easmead": EASMEAD_SPLIT_FACTS,
        "pt_elderwell": ELDERWELL_SPLIT_FACTS,
        "pt_farnroyd": FARNROYD_SPLIT_FACTS,
        "pt_easholm": EASHOLM_SPLIT_FACTS,
        "pt_elderridge": ELDERRIDGE_SPLIT_FACTS,
        "pt_farnsett": FARNSETT_SPLIT_FACTS,
    },
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
