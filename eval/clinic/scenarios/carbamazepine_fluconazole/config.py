"""P07 · `carbamazepine_fluconazole` — the 18-contest pair on the neurology diary.

Mechanism family (assignments table, locked): a patient stabilised on carbamazepine is started on fluconazole by a non-institutional prescriber (an out-of-hours doctor, an emergency dentist, a private weekend clinic) — a textbook CYP3A4 inhibition pair, so the carbamazepine level climbs and the practice's own neurology clinic wants a level drawn THE SAME DAY. Once the two facts are together the action is obvious on obvious knowledge; each fact alone (the chart's steady carbamazepine, a routine repeat-script call, a thrush tablet mentioned in passing) reads routine. Nothing here satisfies an SOP red flag solo or assembled — the symptom texture stays at "a bit dozy", "seeing double for a second", "unsteady on the landing" — and the emergency department adds nothing: the ED does not run the practice's monitoring clinic or write its dosing, so an exit realizes floor value in the score and nothing in the fiction.

Eighteen claimants need today's neurology slots; eighteen routine holders sit in the diary's returned-cancellation slots (six board neurologists staff the expanded service — the memo's one line of size cover is the Fenchurch Road closure that moved that practice's epilepsy-monitoring list onto our books). Every deadline is the clinic's own close of bloods, five o'clock, stated as fact in the calls.

Twins: the PLAIN twin delivers each claimant's whole story in their own single intake; the SPLIT twin distributes it — a routine-sounding piece 1 from the claimant, then the fluconazole named plainly, in routine record-keeping register, in a ring-back on another desk or in a family/neighbour carrier's own call (the §5 shapes; max one recall per caller). Under the split discipline every split piece is routine ON ITS FACE — no call carries the drug and the carbamazepine maintenance context in the same breath; assembling "level today, before five" takes a chart cross-reference or a cross-desk union, on textbook knowledge only — and the split twin's askable fact fields are rewritten sub-threshold via `facts_overrides` (the plain twin declares none). The chart's standing-advice line (the P01-ratified pattern) carries the consequence half of the union — a same-day level on any new interacting medicine, symptoms or none, at the clinic's own phlebotomy, bloods to five — so a desk holding the decisive fact has an explicit cross-reference route; a later revision put it there after the first live split gate showed sonnet assembling the interaction on every recall yet deferring asymptomatic cases to "prescriber review" and sending symptomatic ones to the ED for want of a stated same-day rule. Contests, holders, slots, charts, golds, decoys, roster, cover line and optimum are byte-identical across the twins; the pair gate proves it, permitting exactly the declared intake/fact deltas.

DATA ONLY, on `deadline_day`'s discipline: the gates live in `design_check`, the dials in `pressure`, the solver in `values`.
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
    FAMILY_MEDICINE,
    INTERNAL_MEDICINE,
    NEUROLOGY,
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    SlotKind,
    Urgency,
)

PLAIN_ID = "carbamazepine_fluconazole_plain"
SPLIT_ID = "carbamazepine_fluconazole_split"
PAIR_ID = "P07_carbamazepine_fluconazole"

#: Every claimant's deadline: the neurology clinic's bloods run until five, stated as fact in the calls.
CLINIC_CLOSE = 17 * 60

# ── the practice extension: the expanded neurology service (six board neurologists) ───────────────────────
# Follow-up-heavy days, like the base neurology diary — a monitoring service's day is mostly established
# patients — and referral-only panels, matching the base neurology convention.
NEW_PROVIDERS = (
    board_provider(
        "dr_merebrook",
        "Dr. E. Merebrook",
        NEUROLOGY,
        template=FOLLOW_UP_HEAVY_TEMPLATE,
        accepts_new=False,
    ),
    board_provider(
        "dr_nallgarth",
        "Dr. K. Nallgarth",
        NEUROLOGY,
        template=FOLLOW_UP_HEAVY_TEMPLATE,
        accepts_new=False,
    ),
    board_provider(
        "dr_moorsett",
        "Dr. A. Moorsett",
        NEUROLOGY,
        template=FOLLOW_UP_HEAVY_TEMPLATE,
        accepts_new=False,
    ),
    board_provider(
        "dr_nydewell",
        "Dr. J. Nydewell",
        NEUROLOGY,
        template=FOLLOW_UP_HEAVY_TEMPLATE,
        accepts_new=False,
    ),
    board_provider(
        "dr_marchgill",
        "Dr. P. Marchgill",
        NEUROLOGY,
        template=FOLLOW_UP_HEAVY_TEMPLATE,
        accepts_new=False,
    ),
    board_provider(
        "dr_nokeholm",
        "Dr. T. Nokeholm",
        NEUROLOGY,
        template=FOLLOW_UP_HEAVY_TEMPLATE,
        accepts_new=False,
    ),
    # A second urgent-access PA on the running-hot morning (prompt §7: more providers per specialty).
    # An 18-contest seeding keeps 18 same-day survivors (`BoardSpec.seeding`), and the base roster's
    # single same-day PA cannot supply that many surviving afternoon holds at every epoch draw — this
    # is the capacity that keeps the survivor arithmetic feasible across the whole epoch span. Like the
    # base same-day clinic, it has nothing to work anyone into.
    board_provider(
        "sameday_marchbeck",
        "R. Marchbeck, PA-C",
        SAME_DAY_CLINIC,
        credential="PA-C",
        template=(SlotKind.SAME_DAY,),
        squeeze_capacity=0,
    ),
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
    """A carrier's or decoy's gold: NON_URGENT family medicine — nowhere near the contested diary."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=FAMILY_MEDICINE,
        acceptable=frozenset({FAMILY_MEDICINE, INTERNAL_MEDICINE}),
        ed_required=False,
    )


# ══ THE EIGHTEEN CLAIMANTS ═════════════════════════════════════════════════════════════════════════════
# Canonical intake = the PLAIN twin's words (the whole story in one call); the split twin overrides to the
# routine piece 1 and moves the fluconazole fact into a ring-back or a carrier's call.

pt_marbrook = _caller(
    "pt_marbrook",
    "Edith Marbrook",
    67,
    "F",
    chart=(
        "Focal epilepsy, well controlled for nine years; carbamazepine levels followed at the practice's "
        "neurology clinic.",
        "Transferred in with the Fenchurch Road list; last level seven weeks ago, in range.",
        "Repeat medication: carbamazepine MR 400 mg twice daily, beclometasone inhaler.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I think the seizure clinic will want to see me today, and I had best explain the why "
        "of it.\n\n"
        "The out-of-hours doctor gave me fluconazole last night — thrush in the mouth, from my steroid "
        "inhaler, she said. Now the clinic put it in writing when I moved over from Fenchurch Road: if "
        "any doctor starts me on an antifungal, the carbamazepine level is to be drawn the same day, "
        "because the tablet pushes the number up. Their bloods run until five o'clock.\n\n"
        "I will own I have been dozy since breakfast, which is not like me. No fits, nothing of that "
        "sort — just heavy, and the letter says heavy is exactly when they want the level."
    ),
    onset="The thrush tablet started last night. The dozy feeling came on over breakfast.",
    severity=(
        "Sleepy and slow, like the morning after a bad night. No fits, no falls — I want to be plain "
        "about that."
    ),
    history=(
        "The epilepsy, nine years steady on the same tablets, watched at your neurology clinic since "
        "Fenchurch Road closed."
    ),
    medications=(
        "Carbamazepine, the slow kind, morning and night, and my brown inhaler — and the fluconazole "
        "from the out-of-hours doctor since last night."
    ),
    context="I am home all day and ten minutes' walk away. Any time before their bloods shut at five.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_01",
)

MARBROOK_SPLIT_INTAKE = (
    "Morning. Nothing pressing — it is my brown inhaler, the beclometasone. The puffer is nearly out "
    "and the chemist says there is no repeat left on it. Could somebody put the authorisation through?\n\n"
    "I take my other tablets as usual and I am quite well. Whenever it is ready suits me."
)

MARBROOK_RECALL = (
    "It is Edith Marbrook again — I rang about my inhaler earlier and I have been sat here feeling I "
    "left something off the list. The out-of-hours doctor started me on fluconazole last night — thrush "
    "in the mouth, from the inhaler, she said. That never went through the surgery, so I wanted it "
    "written on my record properly. I have been a bit dozy since breakfast, too, but otherwise I am "
    "quite well."
)

pt_nashwell = _caller(
    "pt_nashwell",
    "Ronald Nashwell",
    71,
    "M",
    chart=(
        "Trigeminal neuralgia, right side, settled on carbamazepine for six years; levels and reviews at "
        "the practice's neurology clinic.",
        "Last carbamazepine level two months ago, in range; next routine level listed for later this "
        "month.",
        "Repeat medication: carbamazepine MR 300 mg twice daily, amlodipine 5 mg daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is about my face-pain tablets — the carbamazepine — and something the emergency "
        "dentist did yesterday.\n\n"
        "I had a sore patch under the denture and she said it was thrush and gave me fluconazole, a "
        "week's course, started last evening. The neurology clinic drummed it into me when the tablets "
        "were first steadied: an antifungal on top of carbamazepine sends the level up, and the level "
        "has to be checked the day the course starts. Their blood man finishes at five.\n\n"
        "I feel much myself — perhaps a shade heavy-eyed after lunch, my wife says so anyway. It is the "
        "rule I am ringing about, not a complaint."
    ),
    onset="The dentist's course started yesterday evening. Nothing else is new.",
    severity="Heavy-eyed after lunch at the worst, my wife would say. The face-pain itself is quiet.",
    history="The trigeminal neuralgia, six years steady on carbamazepine, seen at your neurology clinic.",
    medications=(
        "Carbamazepine morning and night, the blood-pressure tablet in the morning — and the "
        "fluconazole from the emergency dentist since yesterday."
    ),
    context="My wife Sylvia drives us; we can come at any hour today.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_02",
)

NASHWELL_SPLIT_INTAKE = (
    "Hello. A small diary question, nothing more. I have my routine carbamazepine level listed for "
    "later this month and I have mislaid the letter — could you tell me which day it is? My wife keeps "
    "the calendar and she will want it written down properly.\n\n"
    "I am well in myself, no troubles to report."
)

pt_maycote = _caller(
    "pt_maycote",
    "Priya Maycote",
    34,
    "F",
    chart=(
        "Generalised epilepsy from her teens; seizure-free four years on carbamazepine.",
        "Levels followed at the practice's neurology clinic; last level ten weeks ago, in range.",
        "Repeat medication: carbamazepine MR 600 mg twice daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi, morning. I need the neurology clinic today, I think — I will explain.\n\n"
        "I went to the private walk-in place on Saturday for thrush and they gave me fluconazole, the "
        "one-and-then-another sort, and I took the first yesterday. My clinic nurse has always been "
        "clear as glass about this: fluconazole and carbamazepine do not sit together, the level rises, "
        "and I am to have blood taken the same day I start it — their draws run to five o'clock.\n\n"
        "I feel completely fine, no warnings, nothing. But four years clear is four years I do not mean "
        "to gamble on a thrush tablet."
    ),
    onset="Nothing new in myself. The private clinic's tablet — I took the first dose yesterday.",
    severity="No symptoms at all. It is the rule about the level, not how I feel.",
    history="Epilepsy since I was fifteen, four years seizure-free on carbamazepine.",
    medications="Carbamazepine, the slow-release, twice a day — and the fluconazole from Saturday's clinic.",
    context="I work from home today, so any time suits; I can be there in a quarter of an hour.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_03",
)

MAYCOTE_SPLIT_INTAKE = (
    "Hi, morning. Quick admin thing — I am staying over at my sister's side of town for a fortnight. "
    "Can my repeat go to the chemist on Verrall Street instead of my usual one? It is the carbamazepine "
    "on my list, the same as always.\n\n"
    "No rush at all, I have plenty in the box. Thanks."
)

MAYCOTE_RECALL = (
    "Hello, it is Priya Maycote — I rang earlier about moving my chemist. I should have said the other "
    "thing while I was on: the private walk-in clinic gave me fluconazole for thrush on Saturday and I "
    "took the first dose yesterday. A private prescription never finds its own way onto my notes, and I "
    "like my list with you kept current, so could somebody add it? I feel completely fine — it is only "
    "the record-keeping."
)

pt_norholm = _caller(
    "pt_norholm",
    "Frank Norholm",
    74,
    "M",
    chart=(
        "Seizures following a head injury in his fifties; controlled on carbamazepine, levels at the "
        "practice's neurology clinic.",
        "Transferred in with the Fenchurch Road list; last level six weeks ago, in range.",
        "Repeat medication: carbamazepine MR 400 mg twice daily, simvastatin 20 mg nightly.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I want the fitting clinic today if it can be managed, and there is a reason.\n\n"
        "The out-of-hours doctor came to me Sunday evening — thrush, he said, and left me fluconazole, "
        "started that night. The clinic that watches my carbamazepine has a standing rule from years "
        "back: that tablet drives the level up, and the blood test happens the same day it starts, not "
        "the week after. They take bloods up to five.\n\n"
        "And I have been unsteady on the landing this morning, hand out for the rail. Not fallen — "
        "nothing dramatic — but it is new, and it is the exact thing their rule is for."
    ),
    onset="The fluconazole started Sunday night. The unsteadiness showed up this morning on the stairs.",
    severity=(
        "Wobbly enough to want the rail, no more. No falls, no fits, and my head is otherwise clear."
    ),
    history="Fits after a head injury twenty years back, settled on carbamazepine ever since.",
    medications=(
        "Carbamazepine morning and evening, the statin at night — and the out-of-hours doctor's "
        "fluconazole since Sunday."
    ),
    context="My son-in-law can run me down at any hour; we are close by.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_04",
)

NORHOLM_SPLIT_INTAKE = (
    "Morning. Could somebody print me a list of my repeat medicines? The memory clinic at the day "
    "centre asked for a proper list from the surgery rather than my own writing.\n\n"
    "No hurry whatever — I will call in for it when it is ready."
)

NORHOLM_RECALL = (
    "It is Frank Norholm again, about that list of my medicines. If it is being printed it had better "
    "be complete: the out-of-hours doctor left me fluconazole on Sunday evening, for thrush, and that "
    "will not be on your copy yet — my neighbour asked what the new packet was, which is how I came to "
    "think of it. And since I am on, I was unsteady on the landing this morning, wanting the rail, "
    "which is new. Better said than sat on."
)

pt_millgarth = _caller(
    "pt_millgarth",
    "Bernard Millgarth",
    69,
    "M",
    chart=(
        "Trigeminal neuralgia, left side, stable on carbamazepine five years; levels at the practice's "
        "neurology clinic.",
        "Last carbamazepine level nine weeks ago, in range.",
        "Repeat medication: carbamazepine MR 300 mg twice daily, tamsulosin 400 micrograms daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My face-pain tablets and a dentist do not seem to be getting along, so I had better be "
        "seen at the nerve clinic today.\n\n"
        "The emergency dental place saw me Saturday — thrush under the plate — and put me on "
        "fluconazole, a week of it. The clinic's sheet in my kitchen drawer is quite plain: fluconazole "
        "raises the carbamazepine number, and the level wants drawing the day you start it. Bloods go "
        "till five o'clock there.\n\n"
        "Since yesterday teatime the room swims a little when I stand up quick. I sit, it passes. My "
        "neighbour Mrs Newby does my shopping and she said ring you first thing, so here I am."
    ),
    onset="The dentist's fluconazole started Saturday. The swimmy-headed spells began yesterday teatime.",
    severity="A swim when I stand up quickly, gone in a breath. No falls and the face-pain is quiet.",
    history="Trigeminal neuralgia five years, steady on carbamazepine at your nerve clinic.",
    medications=(
        "Carbamazepine twice a day, the waterworks tablet in the morning — and the dentist's "
        "fluconazole since Saturday."
    ),
    context="Mrs Newby next door runs me about; this afternoon is as easy as this morning.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_05",
)

MILLGARTH_SPLIT_INTAKE = (
    "Hello. Ringing for my repeat, the carbamazepine — the box does its last morning Thursday. Could it "
    "go through to the usual chemist?\n\n"
    "Nothing else to report. My neighbour collects it for me, so no rush on my account."
)

pt_nasegill = _caller(
    "pt_nasegill",
    "Carol Nasegill",
    58,
    "F",
    chart=(
        "Focal epilepsy, well controlled on carbamazepine for eleven years; monitored at the practice's "
        "neurology clinic.",
        "Last level eight weeks ago, in range; annual neurology review done in the spring.",
        "Repeat medication: carbamazepine MR 400 mg twice daily, levothyroxine 50 micrograms daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I think I need my carbamazepine level done today at the clinic, and I will give you "
        "the whole of it.\n\n"
        "I had a water infection last week — antibiotics from the out-of-hours service, all finished — "
        "and then thrush on the back of them, as ever. The same out-of-hours doctor gave me fluconazole "
        "on the phone consult last night. And the neurology clinic's instruction, the one on my repeat "
        "slip, is that fluconazole means a level the same day, because it sends the carbamazepine "
        "climbing. Their bloods stop at five.\n\n"
        "I am queasy this morning and dozy with it, which is probably nothing — but taken together with the "
        "slip's instruction I was not going to leave it to chance."
    ),
    onset="The fluconazole started last night. Queasy and dozy since I got up.",
    severity="Queasy like a car journey and sleepy with it. Nothing worse — no fits, no falls.",
    history="Epilepsy eleven years, controlled; thyroid on a steady dose. Both watched here.",
    medications=(
        "Carbamazepine slow-release twice daily, levothyroxine of a morning — and the out-of-hours "
        "fluconazole since last night."
    ),
    context="I am off work today in any case; I can come whenever the clinic can bleed me, up to five.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_06",
)

NASEGILL_SPLIT_INTAKE = (
    "Morning. Only a scheduling thing — when my next routine level comes round, could it be an early "
    "slot? I start at the school at half eight and the mid-morning ones cost me half a day's cover.\n\n"
    "Nothing wrong in myself, it is purely the diary I am asking about."
)

NASEGILL_RECALL = (
    "Hello, Carol Nasegill again — I rang about early appointments earlier, and I have thought of the "
    "housekeeping I forgot. I had a water infection last week — antibiotics from the out-of-hours "
    "service, all finished — and then thrush on the back of them, as ever, so the same doctor put me on "
    "fluconazole last night over the phone. None of that went through you, and I like my record kept "
    "straight. I am a little queasy and dozy this morning too, since you will ask how I am."
)

pt_merefold = _caller(
    "pt_merefold",
    "Jack Merefold",
    19,
    "M",
    chart=(
        "Juvenile-onset epilepsy; seizure-free eighteen months on carbamazepine, levels at the "
        "practice's neurology clinic.",
        "Last level five weeks ago, in range; college notified of care plan.",
        "Repeat medication: carbamazepine MR 200 mg twice daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi, yeah — I think I need a blood test at the epilepsy clinic today. Sorry, I will start "
        "again.\n\n"
        "I saw the private doctor at the weekend clinic on Sunday about a skin thing — a fungal rash, "
        "he said — and he gave me fluconazole tablets, started Sunday night. My clinic nurse made me "
        "put a note in my phone when I started carbamazepine: if anyone ever gives you fluconazole, "
        "ring the surgery, level the same day, their bloods run till five. So this is me doing the "
        "note.\n\n"
        "Also — small thing — I keep seeing double at my screen for a second or two, then it snaps "
        "back. It has happened maybe four times this morning."
    ),
    onset="Fluconazole from Sunday night. The double-vision flickers started this morning.",
    severity="A second or two of double at the screen, four times or so. No fits — nothing like one.",
    history="Epilepsy since school; eighteen months clear on carbamazepine.",
    medications="Carbamazepine twice a day — and the private clinic's fluconazole since Sunday.",
    context="I am at college till noon but I can skip the afternoon; I have my bus pass and no car.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_07",
)

MEREFOLD_SPLIT_INTAKE = (
    "Hi, yeah — my repeat prescription is nearly out, the carbamazepine. Can I get the next one put "
    "through? The chemist by the college is the one I use.\n\n"
    "That is everything, cheers."
)

MEREFOLD_RECALL = (
    "Hi, it is Jack Merefold — I rang about my repeat this morning. After I hung up I realised you "
    "would have no way of knowing: the private weekend doctor gave me fluconazole on Sunday for a "
    "fungal rash, started Sunday night, and none of that went through the surgery. So — putting it on "
    "my notes properly. Also I keep going double at my screen for a second at a time this morning, "
    "which is new, so you may as well have that too."
)

pt_nunthwaite = _caller(
    "pt_nunthwaite",
    "Harold Nunthwaite",
    77,
    "M",
    chart=(
        "Trigeminal neuralgia, settled on carbamazepine for eight years; levels and reviews at the "
        "practice's neurology clinic.",
        "Transferred in with the Fenchurch Road list; last level seven weeks ago, in range.",
        "Repeat medication: carbamazepine MR 300 mg twice daily, bendroflumethiazide 2.5 mg daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. My son said to ring and say it all plainly, so I shall.\n\n"
        "The out-of-hours doctor saw me Sunday for a sore mouth — thrush, with the denture — and "
        "started fluconazole that evening. When Fenchurch Road handed my care over, the letter that "
        "came with me said in black and white: fluconazole lifts the carbamazepine level, test the same "
        "day it begins. Your clinic takes blood until five, the letter says.\n\n"
        "My son Peter says I have been nodding off mid-sentence since yesterday, which he finds funnier "
        "than I do. No falls, no pain — the face has been quiet for years. It is the letter's rule I am "
        "ringing on."
    ),
    onset="The fluconazole began Sunday evening. The nodding-off is since yesterday, my son says.",
    severity="Dozing off in my chair mid-sentence, to my son's amusement. Nothing worse than that.",
    history="The face-pain, eight years settled on carbamazepine; moved here when Fenchurch Road shut.",
    medications=(
        "Carbamazepine twice daily, a water tablet of a morning — and the fluconazole since Sunday "
        "evening."
    ),
    context="Peter, my son, drives me. He is free the whole afternoon today.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_08",
)

NUNTHWAITE_SPLIT_INTAKE = (
    "Good morning. Would you put my repeat through, please — the carbamazepine and the little water "
    "tablet. The chemist said there is nothing left on the slip.\n\n"
    "My son collects them Fridays, so there is no urgency about it. Thank you kindly."
)

pt_moorden = _caller(
    "pt_moorden",
    "Janet Moorden",
    62,
    "F",
    chart=(
        "Focal epilepsy, controlled on carbamazepine for fourteen years; monitored at the practice's "
        "neurology clinic.",
        "Last level six weeks ago, in range.",
        "Repeat medication: carbamazepine MR 400 mg twice daily, atorvastatin 20 mg nightly.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The emergency dentist has put me in the way of needing your neurology clinic today — "
        "let me set it out.\n\n"
        "I have a bridge that has been rubbing, and the dentist yesterday said the soreness under it "
        "was thrush and gave me fluconazole, first tablet with last night's tea. My clinic card — the "
        "yellow one they make you carry — says an antifungal means the carbamazepine level is drawn "
        "before that day is out. The clinic's bloods finish at five.\n\n"
        "This morning the print in the paper went doubled whenever I got tired-eyed, a blink and it "
        "cleared. I am not alarmed, but the card is not a suggestion, as the nurse likes to say."
    ),
    onset="Fluconazole with last night's tea. The doubled print came this morning when tired.",
    severity="A doubling of the print when my eyes are tired, cleared by a blink. Nothing else at all.",
    history="Epilepsy fourteen years, well controlled, level checked at your clinic like clockwork.",
    medications=(
        "Carbamazepine slow-release twice daily, the statin at night — and the dentist's fluconazole "
        "since yesterday evening."
    ),
    context="Retired; I can be at the clinic within the half hour whenever suits, up to their five.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_09",
)

MOORDEN_SPLIT_INTAKE = (
    "Morning. I have had the reminder letter for my annual neurology review and the date clashes with "
    "my grandson's christening — could it be moved along a week or two? Any day the week after "
    "suits.\n\n"
    "That is the whole of it; I am very well otherwise."
)

MOORDEN_RECALL = (
    "Hello, it is Janet Moorden — I rang about moving my review earlier and forgot the housekeeping. "
    "The emergency dentist started me on fluconazole yesterday, for thrush under my bridge, first "
    "tablet with last night's tea — and the dentist is not one of yours, so nobody will have told you. "
    "I like my record kept right, hence the second call. The print in the paper went doubled on me "
    "this morning when I was tired-eyed, as well — a blink and it cleared, but there it is."
)

pt_nettleridge = _caller(
    "pt_nettleridge",
    "Susan Nettleridge",
    45,
    "F",
    chart=(
        "Generalised epilepsy; seizure-free six years on carbamazepine, levels at the practice's "
        "neurology clinic.",
        "Last level nine weeks ago, in range; drives on a full licence, DVLA aware and content.",
        "Repeat medication: carbamazepine MR 600 mg twice daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, morning. I need a carbamazepine level today, please, at the clinic — nothing wrong "
        "with me, everything wrong with the timing.\n\n"
        "The out-of-hours doctor gave me fluconazole last night for thrush. I have the clinic's "
        "instruction sheet magnetised to my fridge: fluconazole is on their short list of medicines "
        "that push the carbamazepine level up, and the level gets drawn the day the course starts — "
        "their phlebotomy runs to five o'clock. I have not so much as a headache, but six years "
        "seizure-free and a driving licence say I do this by the book.\n\n"
        "I have left the car at home today on my own account, before anyone asks."
    ),
    onset="Nothing in myself. The fluconazole started last night — that is the whole event.",
    severity="No symptoms whatever. It is the clinic's same-day rule I am following, nothing more.",
    history="Epilepsy, six years clear on carbamazepine, level always in range.",
    medications="Carbamazepine slow-release twice a day — and the fluconazole from last night.",
    context="I have taken the day from work and left the car at home; buses run right by you.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_10",
)

NETTLERIDGE_SPLIT_INTAKE = (
    "Hello, morning. Could I ask for my repeat to be issued, the carbamazepine? I am down to the last "
    "strip. Usual chemist, please.\n\n"
    "All well otherwise — thanks very much."
)

NETTLERIDGE_RECALL = (
    "Hi, Susan Nettleridge again — I asked for my repeat earlier and realised I had left a gap in the "
    "paperwork. The out-of-hours doctor gave me fluconazole last night, for thrush, and since it came "
    "through their service rather than yours it will not be in my notes. I keep my medicines list with "
    "you exact, so could somebody add it? Nothing wrong in myself at all — this is bookkeeping, not a "
    "complaint."
)

pt_malmead = _caller(
    "pt_malmead",
    "Derek Malmead",
    66,
    "M",
    chart=(
        "Focal epilepsy following meningitis in childhood; stable on carbamazepine, levels at the "
        "practice's neurology clinic.",
        "Last level eight weeks ago, in range.",
        "Repeat medication: carbamazepine MR 400 mg twice daily, omeprazole 20 mg daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall want the neurology clinic today, if the diary can bear it.\n\n"
        "I paid to see a private doctor on Sunday — a nail infection that has annoyed me for months — "
        "and he started me on fluconazole tablets, a longish course, first one Sunday night. The "
        "clinic's rule has been recited at me for years: fluconazole hoists the carbamazepine level, "
        "so a blood test the same day the tablets start. Their bloods are done at five.\n\n"
        "My legs went like jelly on the back step this morning — I sat on the step and it passed. "
        "That, plus the rule, is why I am ringing rather than waiting for my routine one."
    ),
    onset="The private doctor's fluconazole started Sunday night. The jelly-legs turn was this morning.",
    severity="One wobbly turn on the back step, sat down and it passed. No fall, no fit, no headache.",
    history="Epilepsy since childhood meningitis, decades steady on carbamazepine.",
    medications=(
        "Carbamazepine twice daily, the stomach tablet of a morning — and the private doctor's "
        "fluconazole since Sunday."
    ),
    context="Retired, five minutes off; the afternoon is as good as the morning for me.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_11",
)

MALMEAD_SPLIT_INTAKE = (
    "Morning. A diary question only — my next carbamazepine level, which day is it listed? I have a "
    "week away being arranged around it and I cannot lay hands on the letter.\n\n"
    "Fit as a flea otherwise, thank you."
)

MALMEAD_RECALL = (
    "It is Derek Malmead again — I rang with a diary question this morning, and here is a bit more for "
    "the file while I think of it. I paid to see a private doctor on Sunday about a nail infection "
    "that has annoyed me for months, and he started me on fluconazole tablets, a longish course, first "
    "one Sunday night — private, so nothing will have reached you about it. And my legs went like "
    "jelly on the back step this morning; I sat on the step and it passed, but I said I would mention "
    "it if I rang."
)

pt_norcliffe = _caller(
    "pt_norcliffe",
    "Margaret Norcliffe",
    72,
    "F",
    chart=(
        "Trigeminal neuralgia, right side, settled on carbamazepine seven years; levels at the "
        "practice's neurology clinic.",
        "Last level ten weeks ago, in range.",
        "Repeat medication: carbamazepine MR 300 mg twice daily, alendronic acid weekly.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. The nerve clinic will need to fit me in today, I am afraid, and here is the "
        "why.\n\n"
        "The emergency dentist saw me on Saturday — thrush at the corners of my mouth and under the "
        "top plate — and began me on fluconazole that evening. The clinic's leaflet, which I keep with "
        "my pension book, is unambiguous: fluconazole and carbamazepine together mean the level is "
        "measured the same day, because the number goes up on it. Bloods there finish at five "
        "o'clock.\n\n"
        "Mr Maunby next door found me dozing over my lunch yesterday, which has never once happened, so "
        "the leaflet and I are of one mind this morning."
    ),
    onset="The dentist's fluconazole started Saturday evening. The dozing at lunch was yesterday.",
    severity="Fell asleep over lunch, that is the sum of it. No pain — the face has been quiet a year.",
    history="Trigeminal neuralgia, seven settled years on carbamazepine at your nerve clinic.",
    medications=(
        "Carbamazepine twice daily, the bone tablet on Sundays — and the dentist's fluconazole since "
        "Saturday."
    ),
    context="Mr Maunby next door drives me about; he is in and out of your surgery himself today.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_12",
)

NORCLIFFE_SPLIT_INTAKE = (
    "Good morning. Might my repeat be put through, please — the carbamazepine and my Sunday bone "
    "tablet. The chemist tells me the authorisation is used up.\n\n"
    "There is no hurry; Mr Maunby next door collects for me when he is passing."
)

pt_mickleholm = _caller(
    "pt_mickleholm",
    "Vera Mickleholm",
    79,
    "F",
    chart=(
        "Focal epilepsy of late onset; controlled on carbamazepine, levels at the practice's neurology "
        "clinic.",
        "Transferred in with the Fenchurch Road list; last level five weeks ago, in range.",
        "Repeat medication: carbamazepine MR 200 mg twice daily, calcium and vitamin D supplement.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, love. My daughter said I must ring myself and say it all in order, so bear with me.\n\n"
        "The out-of-hours doctor visited me Sunday teatime — thrush, of all the indignities — and left "
        "fluconazole, which I began that night. The letter from when my care moved from Fenchurch Road "
        "says the carbamazepine level must be taken the same day that particular tablet starts, as it "
        "drives the number upward. The clinic bleeds until five, my daughter checked.\n\n"
        "I have been sleepy as a cat since yesterday and sick to my stomach this morning — not "
        "dreadfully, but enough that Ann noticed before I said a word."
    ),
    onset="The fluconazole began Sunday night. Sleepy since yesterday; stomach-sick this morning.",
    severity="Sleepy and a bit sick, like a crossing on a ferry. No fits, no falls, nothing frightening.",
    history="The epilepsy came late, in my seventies; steady on carbamazepine since.",
    medications=(
        "Carbamazepine morning and night, my calcium — and the fluconazole the out-of-hours doctor "
        "left on Sunday."
    ),
    context="My daughter Ann drives me and can manage any hour today.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_13",
)

MICKLEHOLM_SPLIT_INTAKE = (
    "Hello, love. It is only my repeat I am after — the carbamazepine and my calcium. My daughter "
    "collects them for me on her way home.\n\n"
    "I am managing very well, thank you for asking."
)

MICKLEHOLM_RECALL = (
    "Hello, it is Vera Mickleholm again, dear. I rang about my repeats first thing and Ann says I am "
    "to ring you back rather than sit quiet: I have been sleepy as a cat since yesterday, and a bit "
    "sick to my stomach this morning — like a ferry crossing, nothing dreadful. No falls, no fits, "
    "nothing frightening; I only was not quite myself, and Ann said the surgery should hear it from "
    "me. There — said."
)

pt_nybrook = _caller(
    "pt_nybrook",
    "Colin Nybrook",
    55,
    "M",
    chart=(
        "Generalised epilepsy from his twenties; seizure-free three years on carbamazepine, levels at "
        "the practice's neurology clinic.",
        "Last level twelve weeks ago, in range.",
        "Repeat medication: carbamazepine MR 600 mg twice daily, ramipril 5 mg daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I will want a level done at the epilepsy clinic today — the whole story takes a "
        "minute.\n\n"
        "The out-of-hours doctor sorted me out Saturday night for thrush — fluconazole, a week's "
        "course, going since then. My clinic folder has the interaction list in the front pocket and "
        "fluconazole is top of it: level drawn the same day it starts, no exceptions, bloods till "
        "five. I let it slide over the weekend, which I should not have.\n\n"
        "And reading the paper this morning the lines doubled up on me twice, a second each time."
    ),
    onset="Fluconazole since Saturday night. The doubling of the print happened twice this morning.",
    severity="Two seconds of double vision over the paper, twice. No fits — I know mine, and this is not.",
    history="Epilepsy thirty years, the last three completely clear on carbamazepine.",
    medications=(
        "Carbamazepine slow-release twice daily, the blood-pressure one of a morning — and the "
        "fluconazole since Saturday night."
    ),
    context="I am on lates this week, so any daytime hour works; Sandra can drive me if it is short "
    "notice.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_14",
)

NYBROOK_SPLIT_INTAKE = (
    "Morning. I have lost my appointment card — could somebody tell me what I have got coming up, and "
    "send a new card out? Nybrook, Colin.\n\n"
    "Sorry for the bother; that is everything."
)

NYBROOK_RECALL = (
    "It is Colin Nybrook again — I rang about my lost card earlier. One thing I should have added "
    "while I was on: reading the paper this morning the lines doubled up on me, twice, a second each "
    "time. It is probably nothing — I know my own warnings and this was not one — but it is new, and "
    "better on the file than not. That is the lot."
)

pt_marchsett = _caller(
    "pt_marchsett",
    "Fiona Marchsett",
    41,
    "F",
    chart=(
        "Focal epilepsy; seizure-free five years on carbamazepine, levels at the practice's neurology "
        "clinic.",
        "Last level seven weeks ago, in range.",
        "Repeat medication: carbamazepine MR 400 mg twice daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi, good morning. I need the neurology clinic to draw a carbamazepine level today — I am "
        "following their own instruction, so I will quote it.\n\n"
        "I saw the private clinic in the retail park on Sunday about thrush and they prescribed "
        "fluconazole; I took the first dose Sunday evening. My care plan from your clinic says, word "
        "for word, 'a same-day serum level is required whenever fluconazole is commenced' — it is the "
        "one medicine they underline, because it pushes the level up. Bloods run until five.\n\n"
        "I feel absolutely nothing out of the ordinary, and I would like to keep it that way."
    ),
    onset="Nothing in myself. The private clinic's fluconazole began Sunday evening.",
    severity="No symptoms at all — this is the care plan's same-day rule, not a complaint.",
    history="Epilepsy, five years seizure-free on carbamazepine, watched at your clinic.",
    medications="Carbamazepine slow-release twice daily — and the fluconazole since Sunday evening.",
    context="I can step out of work at any point today; the office is two streets from you.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_15",
)

MARCHSETT_SPLIT_INTAKE = (
    "Hi, good morning. Boring one, sorry — my repeat, the carbamazepine, needs reauthorising according "
    "to the chemist. Could that be sorted this week?\n\n"
    "All fine here. Thanks so much."
)

MARCHSETT_RECALL = (
    "Hi, it is Fiona Marchsett — I rang about my repeat first thing. I ought to have mentioned while I "
    "was on: I went to the private clinic in the retail park on Sunday about thrush and they "
    "prescribed fluconazole — I took the first dose Sunday evening. Private means it will not be in my "
    "notes unless somebody types it in, and I like my notes complete, so here is the phone call. I "
    "feel absolutely fine."
)

pt_newgill = _caller(
    "pt_newgill",
    "Albert Newgill",
    76,
    "M",
    chart=(
        "Trigeminal neuralgia, left side, stable on carbamazepine nine years; levels at the practice's "
        "neurology clinic.",
        "Transferred in with the Fenchurch Road list; last level six weeks ago, in range.",
        "Repeat medication: carbamazepine MR 300 mg twice daily, latanoprost eye drops nightly.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning to you. It is the face-pain tablets I am ringing over — or rather what the emergency "
        "dentist has added to them.\n\n"
        "Sore mouth under the denture all week; the dental place yesterday called it thrush and "
        "started me on fluconazole with immediate effect. Now the sheet Fenchurch Road sent over with "
        "my notes is strict on the point: fluconazole raises the carbamazepine, and the level is to be "
        "drawn before that first day is out. Your clinic's bloods go to five o'clock, it says.\n\n"
        "I have felt heavy-headed since my breakfast — not ill, mind, just as if I had been up half "
        "the night, which I had not."
    ),
    onset="The dentist's fluconazole started yesterday. The heavy-headedness came after breakfast.",
    severity="Heavy-headed as after a bad night, no more. The face itself has not troubled me in months.",
    history="Trigeminal neuralgia nine years, steadied on carbamazepine; came over from Fenchurch Road.",
    medications=(
        "Carbamazepine twice a day, drops for the eyes at night — and the fluconazole from the dental "
        "place since yesterday."
    ),
    context="My granddaughter is on a rest day and says she will run me over the minute you name an "
    "hour.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_16",
)

NEWGILL_SPLIT_INTAKE = (
    "Morning to you. I had a letter about my yearly nerve-clinic review and I cannot make out whether "
    "I am meant to ring you or wait to be sent a time. Could somebody tell me which it is?\n\n"
    "No other business — I am ticking along nicely."
)

NEWGILL_RECALL = (
    "It is Albert Newgill again — you sorted my review-letter muddle this morning. My granddaughter "
    "says I should have told you about the dentist while I was on, and she is right: the emergency "
    "dental place saw me yesterday about the sore mouth under the denture — thrush, they called it — "
    "and started me on fluconazole there and then. She wanted it reported to the surgery properly, so "
    "here I am reporting it. I have been a bit heavy-headed since breakfast, if that is worth a line "
    "as well."
)

pt_mossridge = _caller(
    "pt_mossridge",
    "Pauline Mossridge",
    63,
    "F",
    chart=(
        "Focal epilepsy, well controlled on carbamazepine for sixteen years; monitored at the "
        "practice's neurology clinic.",
        "Last level nine weeks ago, in range.",
        "Repeat medication: carbamazepine MR 400 mg twice daily, cetirizine 10 mg daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I shall need the neurology clinic today for a carbamazepine level — the reason "
        "arrived by telephone last night.\n\n"
        "I had rung the out-of-hours service about thrush — tiresome but hardly an emergency — and the "
        "doctor prescribed fluconazole, collected and started before bed. The clinic's standing "
        "instruction sits in the front of my repeat folder: that tablet and carbamazepine together "
        "mean a level the same day, as the number climbs on it. Their bloods finish at five.\n\n"
        "Carrying the tea tray through this morning I had to put a shoulder to the doorframe — "
        "unsteady, just for a step or two. Nothing since, but it made the instruction feel less like "
        "small print."
    ),
    onset="Fluconazole from last night. One unsteady moment with the tea tray this morning.",
    severity="A lean against the doorframe for a step or two, once. No fall, no fit, and clear-headed "
    "since.",
    history="Epilepsy sixteen years, well controlled, levels always at your clinic.",
    medications=(
        "Carbamazepine slow-release twice daily, an allergy tablet in season — and the out-of-hours "
        "fluconazole since last night."
    ),
    context="Home all day; my husband can walk me round whenever the clinic says the word.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_17",
)

MOSSRIDGE_SPLIT_INTAKE = (
    "Morning. Could my repeat be reissued, please — the carbamazepine, and the allergy tablets while "
    "you are at it, with the pollen starting.\n\n"
    "Nothing else from me; all is well in this house."
)

MOSSRIDGE_RECALL = (
    "Hello, Pauline Mossridge again — I rang for my repeats earlier. My husband pointed out the "
    "surgery would have no way of knowing about last night: I rang the out-of-hours service about "
    "thrush — tiresome, hardly an emergency — and the doctor prescribed fluconazole, collected and "
    "started before bed. So that is now told and can go on my record. I also had to lean on the "
    "doorframe carrying the tea tray this morning, just for a step or two — nothing since, but better "
    "you have it all."
)

pt_narfold = _caller(
    "pt_narfold",
    "Stephen Narfold",
    49,
    "M",
    chart=(
        "Generalised epilepsy; seizure-free seven years on carbamazepine, levels at the practice's "
        "neurology clinic.",
        "Last level eleven weeks ago, in range.",
        "Repeat medication: carbamazepine MR 600 mg twice daily.",
        "Clinic protocol on file: a carbamazepine level the same day any new interacting medicine is "
        "started, symptoms or none; the level is drawn at the neurology clinic's own phlebotomy "
        "(bloods run to five o'clock) and read against the dose at the visit; a number from elsewhere "
        "does not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I need to book a same-day carbamazepine level at the neurology clinic, on the "
        "clinic's own standing orders — here is the chain of events.\n\n"
        "Thrush, embarrassingly; the private clinic on Sunday; fluconazole prescribed there and "
        "started Sunday night. My clinic consent form — I signed the thing, so I remember it — lists "
        "fluconazole among the medicines that force the level up and requires the blood draw on day "
        "one, not day three. The phlebotomist works to five o'clock.\n\n"
        "No symptoms to declare. Seven years clear, and I intend the eighth on the same terms."
    ),
    onset="Nothing in myself. The private clinic's fluconazole started Sunday night.",
    severity="No symptoms at all — this is the clinic's day-one rule being followed to the letter.",
    history="Epilepsy since my twenties; the last seven years without a single event, on carbamazepine.",
    medications="Carbamazepine slow-release twice daily — and the fluconazole since Sunday night.",
    context="Working from home today; I can be with the phlebotomist inside twenty minutes, up to "
    "five.",
    gold=board_gold(NEUROLOGY),
    source="authored:p07_carbamazepine_fluconazole_claimant_18",
)

NARFOLD_SPLIT_INTAKE = (
    "Morning. Could you confirm my repeat went through on Friday? The chemist had nothing under my "
    "name yesterday and I would rather chase it early than run short. Narfold, Stephen.\n\n"
    "Thanks — that is the lot."
)

NARFOLD_RECALL = (
    "It is Stephen Narfold again, following up on the repeat query — and adding a piece of "
    "housekeeping I should have included. The private clinic on Sunday started me on fluconazole — "
    "thrush, embarrassingly — first tablet Sunday night, and a private prescription does not reach "
    "your records on its own. I would rather my file were complete than tidy-looking, so there it is. "
    "No symptoms; nothing else to report."
)

# ══ THE EIGHTEEN HOLDERS ═══════════════════════════════════════════════════════════════════════════════
# Routine neurology patients sitting in the returned-cancellation slots. Holders never call — a card is
# what they say if a desk RINGS them. Each has an ordinary human reason to want today kept; none of them
# volunteers to move and none of them is obstructive.

pt_maplecote = _caller(
    "pt_maplecote",
    "Doris Maplecote",
    70,
    "F",
    chart=(
        "Focal epilepsy, long stable; annual medication review at the practice's neurology clinic.",
        "Repeat medication: carbamazepine MR 200 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I have my yearly epilepsy medication review this afternoon. My granddaughter has taken the "
        "afternoon off specially to bring me — she had to clear it with her supervisor a fortnight "
        "back, so today is the day that works."
    ),
    onset="Nothing new; it is the yearly review of my tablets.",
    severity="I am perfectly well. The appointment is routine — the tablets have not changed in years.",
    history="Epilepsy, long settled; reviewed once a year at the clinic.",
    medications="The carbamazepine, morning and night, same dose as always.",
    context="My granddaughter took this afternoon off work specially for the lift.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_01_annual_epilepsy_review",
)

pt_norbrook = _caller(
    "pt_norbrook",
    "Kenneth Norbrook",
    68,
    "M",
    chart=(
        "Chronic migraine, stable on a preventer; annual neurology review.",
        "Repeat medication: propranolol MR 80 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is my yearly migraine review this afternoon. I have booked the whole day off the "
        "allotment committee for it and told everyone I am unavailable — I would sooner keep the time "
        "I was given."
    ),
    onset="Nothing new; the heads have been quiet all year.",
    severity="I am well — it is the once-a-year check of the preventer, nothing more.",
    history="Migraine most of my life, well behaved on the tablets these last years.",
    medications="The propranolol, the long-acting one, every morning.",
    context="I have cleared the day for it and told the committee I am not to be reached.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_02_annual_migraine_review",
)

pt_midholm = _caller(
    "pt_midholm",
    "Brian Midholm",
    64,
    "M",
    chart=(
        "Peripheral neuropathy, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: amitriptyline 25 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My nerve-ending review is this afternoon — the yearly one for my feet. I have a taxi booked "
        "both ways already, and at their prices I would rather not book it twice."
    ),
    onset="Nothing new with the feet; it is the annual look-over.",
    severity="Same pins and needles as ever, no worse. Routine, in a word.",
    history="The neuropathy in my feet, five or six years now, steady on the night tablet.",
    medications="Amitriptyline at bedtime, the small dose.",
    context="The taxi is booked both ways for this afternoon.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_03_neuropathy_review",
)

pt_nunwell = _caller(
    "pt_nunwell",
    "Eileen Nunwell",
    75,
    "F",
    chart=(
        "Migraine with aura, stable; annual neurology review.",
        "Repeat medication: amitriptyline 10 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "I am booked for my migraine review this afternoon. My daughter swapped her shift at the home "
        "to fetch me in — swaps are hard-won on her rota, so this afternoon is rather precious."
    ),
    onset="Nothing new; the yearly review, that is all.",
    severity="I am quite well. The auras have kept themselves scarce this year.",
    history="Migraine with the flashing lights, decades now, gentle on the night tablet.",
    medications="The little amitriptyline at bedtime.",
    context="My daughter swapped a shift at the care home specially to bring me today.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_04_migraine_review",
)

pt_marlgill = _caller(
    "pt_marlgill",
    "Trevor Marlgill",
    59,
    "M",
    chart=(
        "Focal epilepsy, stable; annual medication review at the practice's neurology clinic.",
        "Repeat medication: lamotrigine 200 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon is my yearly epilepsy review. Work have signed me off the rota for it — the "
        "depot does not hand out afternoons twice in a month, so I am counting on the time I have."
    ),
    onset="Nothing new; annual review of the epilepsy tablets.",
    severity="I am well — no events this year, touch wood.",
    history="Epilepsy, steady these many years on the lamotrigine.",
    medications="Lamotrigine, morning and night.",
    context="The depot signed me off this afternoon's rota for the appointment.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_05_epilepsy_review",
)

pt_nabcote = _caller(
    "pt_nabcote",
    "Hilda Nabcote",
    81,
    "F",
    chart=(
        "Essential tremor, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: propranolol 40 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My shakes review is this afternoon — the yearly one. My neighbour drives me and she has "
        "arranged her grandchildren around it, so this afternoon is the one that suits us both."
    ),
    onset="Nothing new; the tremor is its usual self.",
    severity="Steady as she goes — the teacups rattle no worse than last year.",
    history="The tremor, many years, softened by the tablets.",
    medications="Propranolol, morning and teatime.",
    context="My neighbour has arranged her grandchildren around this afternoon's lift.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_06_tremor_review",
)

pt_medthwaite = _caller(
    "pt_medthwaite",
    "Alan Medthwaite",
    66,
    "M",
    chart=(
        "Peripheral neuropathy, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: duloxetine 60 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is my neuropathy review this afternoon. My wife has taken her day off around it and "
        "built the whole day's errands on the back of the trip — moving it would knock over her "
        "dominoes as much as mine."
    ),
    onset="Nothing new; the annual check on my feet and the tablet.",
    severity="The burning is no worse than it ever is. Routine review, that is all.",
    history="Neuropathy in both feet, some years now, manageable on the duloxetine.",
    medications="Duloxetine, one a day with breakfast.",
    context="My wife took today off and planned the day's errands around the appointment.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_07_neuropathy_review",
)

pt_norgill = _caller(
    "pt_norgill",
    "Beryl Norgill",
    73,
    "F",
    chart=(
        "Chronic migraine, stable; annual neurology review.",
        "Repeat medication: candesartan 8 mg daily for migraine prevention.",
        "No known drug allergies.",
    ),
    intake=(
        "My migraine review is this afternoon. A friend from church runs me in — she does her mother's "
        "shopping the same trip, so the two of us have it down to a fine art for exactly this time of "
        "day."
    ),
    onset="Nothing new; the yearly check.",
    severity="Perfectly well. Two heads since the spring, both mild.",
    history="Migraine, long standing, well held by the preventer.",
    medications="The candesartan, one each morning.",
    context="My church friend drives me and does her mother's shopping the same trip.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_08_migraine_review",
)

pt_marwell = _caller(
    "pt_marwell",
    "Clive Marwell",
    61,
    "M",
    chart=(
        "Focal epilepsy, stable; annual medication review at the practice's neurology clinic.",
        "Repeat medication: levetiracetam 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon is my epilepsy review — the annual one. The site manager granted me the "
        "half-day at the start of the month and the paperwork is in; half-days granted are not "
        "half-days easily re-granted, if you follow me."
    ),
    onset="Nothing new; the annual review of my tablets.",
    severity="I am well. No events since the last review.",
    history="Epilepsy, steady on the levetiracetam these six years.",
    medications="Levetiracetam, morning and night.",
    context="The half-day off site was granted at the start of the month, paperwork and all.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_09_epilepsy_review",
)

pt_nidcote = _caller(
    "pt_nidcote",
    "Joyce Nidcote",
    78,
    "F",
    chart=(
        "Essential tremor, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: primidone 125 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My tremor review is this afternoon. My son is driving over from two towns away and he set off "
        "this morning — he has taken the day for it, bless him, so we are rather committed to today."
    ),
    onset="Nothing new; the yearly look at the shakes.",
    severity="The hands are as they were. It is the routine check, nothing pressing.",
    history="The tremor, years now, eased by the night tablet.",
    medications="Primidone at bedtime.",
    context="My son set off this morning from two towns away and has taken the day for it.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_10_tremor_review",
)

pt_munden = _caller(
    "pt_munden",
    "June Munden",
    69,
    "F",
    chart=(
        "Migraine, stable; annual neurology review.",
        "Repeat medication: topiramate 50 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in for my migraine review this afternoon. My sister is up visiting and she drives — she "
        "goes home Thursday, so this appointment landing this week was a small miracle of timing I am "
        "loath to give up."
    ),
    onset="Nothing new; the annual review.",
    severity="Quite well — the heads have been kind this year.",
    history="Migraine, long standing, settled on the topiramate.",
    medications="Topiramate, morning and evening.",
    context="My sister is visiting until Thursday and she is my driver.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_11_migraine_review",
)

pt_narlund = _caller(
    "pt_narlund",
    "Roger Narlund",
    71,
    "M",
    chart=(
        "Peripheral neuropathy, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: gabapentin 300 mg three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is my neuropathy review this afternoon. The community car scheme is booked — you book "
        "those a week ahead and take the slot you are given, so today's run is not a thing I can "
        "conjure again in a hurry."
    ),
    onset="Nothing new; the yearly review of the feet.",
    severity="Numb toes, same as ever. Routine.",
    history="Neuropathy some years; the gabapentin keeps it civil.",
    medications="Gabapentin, three times a day.",
    context="The community car is booked for this afternoon, arranged a week back.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_12_neuropathy_review",
)

pt_maisgarth = _caller(
    "pt_maisgarth",
    "Ivy Maisgarth",
    80,
    "F",
    chart=(
        "Focal epilepsy of late onset, stable; annual medication review at the practice's neurology "
        "clinic.",
        "Repeat medication: carbamazepine MR 200 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My epilepsy review is this afternoon. The warden at my flats has arranged the minibus run "
        "around it and two of us are travelling together — the warden does not rearrange the minibus "
        "for one, I can tell you."
    ),
    onset="Nothing new; the yearly review of my tablets.",
    severity="I am very well. Not so much as a funny turn since last year.",
    history="The epilepsy came on late; steady on the tablets since.",
    medications="Carbamazepine, morning and night.",
    context="The warden arranged the minibus around this afternoon; two of us travel together.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_13_epilepsy_review",
)

pt_netherby = _caller(
    "pt_netherby",
    "Ernest Netherby",
    74,
    "M",
    chart=(
        "Essential tremor, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: propranolol 40 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tremor check is this afternoon. My grandson has a half-day from the sixth form and is "
        "driving me on his new licence — it has been the talk of the house all week, so we would both "
        "be sorry to lose the outing."
    ),
    onset="Nothing new; the annual check.",
    severity="The shake is the shake; no worse. Routine visit.",
    history="Tremor a good ten years, softened by the tablets.",
    medications="Propranolol, twice a day.",
    context="My grandson's half-day and his new licence are both spoken for this afternoon.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_14_tremor_review",
)

pt_maisdon = _caller(
    "pt_maisdon",
    "Ruth Maisdon",
    65,
    "F",
    chart=(
        "Migraine, stable; annual neurology review.",
        "Repeat medication: propranolol MR 80 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I am down for my migraine review this afternoon. I have swapped my library shift to the "
        "morning specially — the rota goes up a month ahead, so the swap took some doing and I would "
        "rather it counted."
    ),
    onset="Nothing new; the annual review.",
    severity="Well in myself; the heads behave on the tablet.",
    history="Migraine for donkey's years, quiet on the preventer.",
    medications="The long-acting propranolol, one a day.",
    context="The library shift was swapped to this morning a month in advance.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_15_migraine_review",
)

pt_netherholm = _caller(
    "pt_netherholm",
    "Leslie Netherholm",
    72,
    "M",
    chart=(
        "Peripheral neuropathy, stable; annual review at the practice's neurology clinic.",
        "Repeat medication: amitriptyline 25 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "That is my feet review this afternoon — the nerve one, yearly. A pal from the bowls club "
        "drives me and we make an afternoon of it, the green after; his diary is fuller than the "
        "doctor's, so today took arranging."
    ),
    onset="Nothing new with the feet; the annual look.",
    severity="Tingling toes as usual, nothing worse. Routine.",
    history="Neuropathy several years, steady on the night tablet.",
    medications="Amitriptyline at night.",
    context="The bowls-club pal has kept this afternoon free to drive; the green is booked after.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_16_neuropathy_review",
)

pt_maismead = _caller(
    "pt_maismead",
    "Olive Maismead",
    77,
    "F",
    chart=(
        "Focal epilepsy, long stable; annual medication review at the practice's neurology clinic.",
        "Repeat medication: carbamazepine MR 200 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My epilepsy review is this afternoon. My niece booked the whole afternoon away from her desk "
        "for it and is taking me to the garden centre after — the pair of treats stand or fall "
        "together, as she puts it."
    ),
    onset="Nothing new; it is the yearly medication review.",
    severity="I am very well. The tablets and I get along famously.",
    history="Epilepsy, long settled on the carbamazepine.",
    medications="Carbamazepine, morning and night.",
    context="My niece booked this afternoon off and the garden centre is promised after.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_17_epilepsy_review",
)

pt_nethergarth = _caller(
    "pt_nethergarth",
    "Wilfred Nethergarth",
    79,
    "M",
    chart=(
        "Migraine, stable; annual neurology review.",
        "Repeat medication: amitriptyline 10 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My migraine review is this afternoon. The carer rota was drawn up around it — the agency "
        "moved my Tuesday girl to today so somebody could sit with my wife while I am out. Undoing "
        "that is a week's notice at the least."
    ),
    onset="Nothing new; the yearly review.",
    severity="I am well enough; the heads are rare now.",
    history="Migraine, milder with age, held by the small night tablet.",
    medications="Amitriptyline at night, the ten.",
    context="The agency rearranged the carer rota so my wife is sat with this afternoon.",
    gold=_holder_gold(NEUROLOGY),
    source="authored:p07_holder_18_migraine_review",
)

# ══ THE CARRIERS (split-twin evidence; dual-purpose callers with their own routine matters) ══════════════

pt_nashwell_b = _caller(
    "pt_nashwell_b",
    "Sylvia Nashwell",
    69,
    "F",
    chart=(
        "Osteoarthritis of the knees, stable; walking programme.",
        "Repeat medication: co-codamol 8/500 as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is only my painkillers — the co-codamol has come off my repeat list somehow and the "
        "chemist will not fill it. Could somebody put it back on?\n\n"
        "No rush; I have a strip or two left yet."
    ),
    onset="Nothing new — the repeat has fallen off the list, that is all.",
    severity="My knees are their usual selves. It is paperwork, not pain.",
    history="The knees, worn but willing, these ten years.",
    medications="The co-codamol when the knees play up; nothing else for me.",
    context="I keep the diary for my husband Ronald and me both; we are in and out of your surgery.",
    gold=_routine_gold(),
    source="authored:p07_carrier_nashwell_wife",
)

NASHWELL_B_SPLIT_INTAKE = (
    "Hello. It is only my painkillers — the co-codamol has come off my repeat list somehow and the "
    "chemist will not fill it. Could somebody put it back on? No rush; I have a strip or two left "
    "yet.\n\n"
    "And while I have you — would somebody put a note on my husband Ronald's record? The emergency "
    "dentist started him on fluconazole yesterday, for thrush under the denture, and those places "
    "never pass anything along to the surgery unless a wife rings. He has been a shade heavy-eyed "
    "since lunch yesterday, too, which I add for completeness. He will forgive me for telling tales."
)

pt_newby = _caller(
    "pt_newby",
    "Doreen Newby",
    66,
    "F",
    chart=(
        "Hypertension, well controlled; annual review in place.",
        "Repeat medication: losartan 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Just my blood-pressure tablets — the losartan repeat is due and I am running to the "
        "end of the packet. Could it go through to the village chemist as usual?\n\n"
        "That is all it is; I am very well."
    ),
    onset="Nothing new — the packet is simply running down.",
    severity="No symptoms at all; the pressure was fine at the last check.",
    history="Blood pressure, tablets for eight years, never a bother.",
    medications="Losartan, one each morning.",
    context="I do the shopping and the prescription run for Mr Millgarth next door as well.",
    gold=_routine_gold(),
    source="authored:p07_carrier_newby_neighbour",
)

NEWBY_SPLIT_INTAKE = (
    "Morning. Just my blood-pressure tablets — the losartan repeat is due and I am running to the end "
    "of the packet. Could it go through to the village chemist as usual?\n\n"
    "Oh — and I ought to mention Mr Millgarth next door while I am on. I collected a prescription for "
    "him from the emergency dental place at the weekend — fluconazole, for thrush under his plate — "
    "and I doubt anybody has told the surgery, those places never do. He has also come over a bit "
    "swimmy-headed when he stands up quick, since teatime yesterday; it passes when he sits, he says. "
    "He rang you about his repeat this morning but I would put money on him leaving all that out."
)

pt_nunthwaite_b = _caller(
    "pt_nunthwaite_b",
    "Peter Nunthwaite",
    49,
    "M",
    chart=(
        "Mild asthma; inhaler technique reviewed at last appointment.",
        "Repeat medication: salbutamol inhaler as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Quick one — my blue inhaler needs a repeat before the football on Sunday. Could that "
        "be put through today or tomorrow?\n\n"
        "Nothing else from me, thanks."
    ),
    onset="Nothing new; the inhaler is just low.",
    severity="Chest is fine — the inhaler is a just-in-case for five-a-side.",
    history="Mild asthma since school, barely a puff most months.",
    medications="The blue inhaler when needed.",
    context="I run my father Harold about; he is one of yours too.",
    gold=_routine_gold(),
    source="authored:p07_carrier_nunthwaite_son",
)

NUNTHWAITE_B_SPLIT_INTAKE = (
    "Morning. Quick one — my blue inhaler needs a repeat before the football on Sunday. Could that be "
    "put through today or tomorrow?\n\n"
    "Second thing: my father, Harold Nunthwaite, rang you earlier about his repeat, and knowing Dad "
    "he kept it to thirty seconds. For his record, then: the out-of-hours doctor started him on "
    "fluconazole on Sunday evening, for thrush with the denture, and nobody official will have told "
    "you. He has also been nodding off mid-sentence since yesterday, which is new even for Dad. "
    "Somebody should have all that written down."
)

pt_maunby = _caller(
    "pt_maunby",
    "Ted Maunby",
    70,
    "M",
    chart=(
        "Bilateral ear wax, recurrent; drops advised before syringing.",
        "Repeat medication: none regular.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My ears want syringing again — I have done my week of the olive oil drops as "
        "instructed. Could I be booked in with the nurse for the wax, whenever there is a gap?\n\n"
        "No hurry at all; I am half-deaf but cheerful."
    ),
    onset="The usual wax; the drops week is done as of yesterday.",
    severity="Muffled hearing, nothing painful. A nuisance, not an ailment.",
    history="The ears bung up every year or so; syringing sorts them.",
    medications="Nothing regular; the olive oil drops this last week.",
    context="I drive Mrs Norcliffe next door where she needs to go; we look out for one another.",
    gold=_routine_gold(),
    source="authored:p07_carrier_maunby_neighbour",
)

MAUNBY_SPLIT_INTAKE = (
    "Morning. My ears want syringing again — I have done my week of the olive oil drops as "
    "instructed. Could I be booked in with the nurse for the wax, whenever there is a gap?\n\n"
    "While you have me: Mrs Norcliffe next door, Margaret — I run her about, and Saturday I took her "
    "to the emergency dentist, who gave her fluconazole for the thrush under her plate. Somebody at "
    "the surgery ought to have that written down, because the dental place will not have told you and "
    "she rang you about her repeat first thing without mentioning a word of it, I would wager. I also "
    "found her asleep over her lunch yesterday, which is not our Margaret at all — likely nothing, "
    "but you may as well have the lot."
)

pt_mickleholm_b = _caller(
    "pt_mickleholm_b",
    "Ann Mickleholm",
    52,
    "F",
    chart=(
        "Hypothyroidism, stable on levothyroxine; annual bloods in place.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Mine is only the thyroid repeat — the levothyroxine — due about now. Could it be "
        "issued to the precinct chemist, please?\n\n"
        "That is everything for me."
    ),
    onset="Nothing new; the repeat is due, no more.",
    severity="Perfectly well; the dose has not moved in years.",
    history="The thyroid, steady on the same dose a long while.",
    medications="Levothyroxine, one hundred, every morning.",
    context="I look in on my mother Vera daily and collect her medicines with mine.",
    gold=_routine_gold(),
    source="authored:p07_carrier_mickleholm_daughter",
)

MICKLEHOLM_B_SPLIT_INTAKE = (
    "Hello. Mine is only the thyroid repeat — the levothyroxine — due about now. Could it be issued "
    "to the precinct chemist, please?\n\n"
    "And I want something on my mother's record while I have you — Vera Mickleholm. The out-of-hours "
    "doctor visited her on Sunday teatime and left her fluconazole for thrush, which she began that "
    "night. I collect her medicines with mine, which is how I know, and nobody from that service will "
    "have told you. She has rung you herself about her repeats this morning, but she buries the lede, "
    "my mother — so consider it unburied."
)

pt_millroyd = _caller(
    "pt_millroyd",
    "Sandra Millroyd",
    52,
    "F",
    chart=(
        "Contraceptive pill, established; annual check due in the autumn.",
        "Repeat medication: combined oral contraceptive.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Only my pill script — I am on the last strip and the chemist says the repeat needs "
        "signing off. Could that be done this week?\n\n"
        "All well otherwise, thanks."
    ),
    onset="Nothing new; the strip is nearly done, that is the whole story.",
    severity="No troubles at all; the check in the autumn can stay where it is.",
    history="On the pill for years without a hiccup.",
    medications="The combined pill, as ever.",
    context="I am in most days around my shifts; my friend Colin Nybrook is a patient of yours too.",
    gold=_routine_gold(),
    source="authored:p07_carrier_millroyd_friend",
)

MILLROYD_SPLIT_INTAKE = (
    "Hi. Only my pill script — I am on the last strip and the chemist says the repeat needs signing "
    "off. Could that be done this week?\n\n"
    "Also, and he will hate me for it: my friend Colin Nybrook. The out-of-hours doctor gave him "
    "fluconazole on Saturday night, for thrush, and Colin being Colin he rang you this morning about "
    "a lost appointment card and I would bet the house he never mentioned the new tablets. Nobody "
    "from out-of-hours will have told you either, so I am telling you — it ought to be on his file."
)

# ══ THE DECOYS ═══════════════════════════════════════════════════════════════════════════════════════════

pt_morcote = _caller(
    "pt_morcote",
    "Gwen Morcote",
    74,
    "F",
    chart=(
        "Hypertension, controlled; annual review in place.",
        "Repeat medication: indapamide 2.5 mg daily.",
        "New spectacle prescription noted at last contact.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I have had two giddy turns this week and the word 'giddy' frightens my daughter, so "
        "I promised to ring — but let me give you the whole picture before anyone panics.\n\n"
        "Both turns came when I whipped my head round quick, in the new glasses — the optician changed "
        "my prescription a fortnight back and warned me the varifocals would take some weeks to settle, "
        "and that quick turns would swim until they did. No falls, no palpitations, no headache; "
        "steady as a rock walking about, and nothing at all when I keep my head sensible.\n\n"
        "So: a routine look-over whenever there is a gap, to keep my promise to my daughter. That is "
        "the size of it."
    ),
    onset="Two giddy moments this week, both on a quick turn of the head in the new glasses.",
    severity=(
        "A swim for a second or two, no falls, nothing else with it. The optician said to expect "
        "exactly this while the varifocals settle."
    ),
    history="Blood pressure, controlled for years; new spectacles a fortnight ago.",
    medications="The indapamide of a morning, nothing else.",
    context="No hurry whatever — a routine appointment keeps my promise to my daughter.",
    gold=_routine_gold(),
    source="authored:p07_decoy_giddy_new_glasses",
)

pt_munby = _caller(
    "pt_munby",
    "Iris Munby",
    68,
    "F",
    chart=(
        "Atopic eczema, recurrent in winter; emollients and steroid cream as required.",
        "Course of antibiotics for a chest infection completed six weeks ago, full recovery.",
        "Repeat medication: emollient cream, hydrocortisone 1% cream.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My forearms have come up in red, itchy patches overnight and it burns something "
        "awful, and my first thought was the tablets — I had antibiotics not long back and you hear "
        "such things.\n\n"
        "But my husband made me look at the calendar before ringing, and he is right: that course "
        "finished back in the winter, a good six weeks ago, nothing new since. And it is the same two patches I get "
        "every winter when the radiators go on — the eczema, in exactly its usual spots — only worse "
        "this time because my cream ran out on Tuesday. My breathing is fine, my face is fine, nothing "
        "anywhere but the forearms.\n\n"
        "So I expect it is a repeat of the cream and a routine appointment, in whatever order suits."
    ),
    onset="The patches flared overnight — the same winter spots as always, cream run out since Tuesday.",
    severity=(
        "Itchy and burning on the two usual patches, nothing elsewhere. Breathing fine, face fine, no "
        "swelling anywhere."
    ),
    history="Winter eczema for years in the same two places; antibiotics over the winter, long finished.",
    medications="The emollient and the weak steroid cream — both tubes empty since Tuesday.",
    context="My husband Arthur is ringing you separately about his own bits and pieces today.",
    gold=_routine_gold(),
    source="authored:p07_decoy_eczema_flare",
)

MUNBY_SPLIT_INTAKE = (
    "Morning. My forearms have come up in red, itchy patches overnight and it burns something awful — "
    "and I cannot help thinking of the tablets, because I was on antibiotics not so long back and you "
    "hear such things about reactions.\n\n"
    "It is both arms, angry as anything, and the itching kept me up half the night. My breathing is "
    "fine, I should say, and there is nothing anywhere but the forearms. I would like somebody to tell "
    "me what it is, and today rather than next month if the tablets are to blame."
)

pt_munby_b = _caller(
    "pt_munby_b",
    "Arthur Munby",
    71,
    "M",
    chart=(
        "Osteoarthritis of the right knee; topical treatment.",
        "Repeat medication: ibuprofen gel.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Nothing grand — my knee gel is finished and the chemist wants the repeat "
        "authorised. Could that be put through?\n\n"
        "That is my lot, thank you."
    ),
    onset="Nothing new; the gel tube is done, that is all.",
    severity="The knee grumbles on stairs as it has for years. No change.",
    history="The right knee, worn cartilage, managed with the gel.",
    medications="The ibuprofen gel for the knee.",
    context="My wife Iris is ringing you herself today about her arms.",
    gold=_routine_gold(),
    source="authored:p07_decoy_defuser_munby_husband",
)

MUNBY_B_SPLIT_INTAKE = (
    "Morning. Nothing grand — my knee gel is finished and the chemist wants the repeat authorised. "
    "Could that be put through?\n\n"
    "And a word about my wife, Iris, who has rung you this morning in a state about her arms. Before "
    "anybody reaches for the alarm bell: her antibiotics finished a good six weeks back — I made her look "
    "at the calendar — and there is nothing new in her pill box since. It is the same two winter "
    "patches of eczema she gets every year when the radiators go on, in exactly the usual spots, and "
    "her cream ran out on Tuesday, which is the whole mystery solved in my view. Her breathing is "
    "fine and there is nothing anywhere but the forearms. A repeat of the cream and a routine "
    "appointment is what she needs, not a drama."
)

# ══ THE BOARD SKELETON (shared by both twins byte-for-byte) ═══════════════════════════════════════════════

CONTESTS = (
    BoardContest(
        claimant="pt_marbrook",
        holder="pt_maplecote",
        specialty=NEUROLOGY,
        provider_id="dr_merebrook",
        slot_hhmm="13:00",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual epilepsy medication review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_nashwell",
        holder="pt_norbrook",
        specialty=NEUROLOGY,
        provider_id="dr_merebrook",
        slot_hhmm="14:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual migraine review + preventer renewal (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_maycote",
        holder="pt_midholm",
        specialty=NEUROLOGY,
        provider_id="dr_merebrook",
        slot_hhmm="16:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual peripheral-neuropathy review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_norholm",
        holder="pt_nunwell",
        specialty=NEUROLOGY,
        provider_id="dr_nallgarth",
        slot_hhmm="13:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual migraine-with-aura review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_millgarth",
        holder="pt_marlgill",
        specialty=NEUROLOGY,
        provider_id="dr_nallgarth",
        slot_hhmm="15:00",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual epilepsy review + repeat scripts (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_nasegill",
        holder="pt_nabcote",
        specialty=NEUROLOGY,
        provider_id="dr_nallgarth",
        slot_hhmm="16:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual essential-tremor review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_merefold",
        holder="pt_medthwaite",
        specialty=NEUROLOGY,
        provider_id="dr_moorsett",
        slot_hhmm="13:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual neuropathy review + medication check (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_nunthwaite",
        holder="pt_norgill",
        specialty=NEUROLOGY,
        provider_id="dr_moorsett",
        slot_hhmm="15:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual chronic-migraine review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_moorden",
        holder="pt_marwell",
        specialty=NEUROLOGY,
        provider_id="dr_moorsett",
        slot_hhmm="16:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual epilepsy medication review + bloods (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_nettleridge",
        holder="pt_nidcote",
        specialty=NEUROLOGY,
        provider_id="dr_nydewell",
        slot_hhmm="13:00",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual tremor review + repeat primidone (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_malmead",
        holder="pt_munden",
        specialty=NEUROLOGY,
        provider_id="dr_nydewell",
        slot_hhmm="14:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual migraine review + repeat topiramate (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_norcliffe",
        holder="pt_narlund",
        specialty=NEUROLOGY,
        provider_id="dr_nydewell",
        slot_hhmm="16:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual neuropathy review + repeat gabapentin (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_mickleholm",
        holder="pt_maisgarth",
        specialty=NEUROLOGY,
        provider_id="dr_marchgill",
        slot_hhmm="13:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual late-onset-epilepsy review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_nybrook",
        holder="pt_netherby",
        specialty=NEUROLOGY,
        provider_id="dr_marchgill",
        slot_hhmm="15:00",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual tremor review + repeat propranolol (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_marchsett",
        holder="pt_maisdon",
        specialty=NEUROLOGY,
        provider_id="dr_marchgill",
        slot_hhmm="16:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual migraine review + preventer check (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_newgill",
        holder="pt_netherholm",
        specialty=NEUROLOGY,
        provider_id="dr_nokeholm",
        slot_hhmm="13:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual peripheral-neuropathy check (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_mossridge",
        holder="pt_maismead",
        specialty=NEUROLOGY,
        provider_id="dr_nokeholm",
        slot_hhmm="15:20",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual epilepsy review + dosing check (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
    BoardContest(
        claimant="pt_narfold",
        holder="pt_nethergarth",
        specialty=NEUROLOGY,
        provider_id="dr_nokeholm",
        slot_hhmm="16:40",
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=(
            "Annual migraine review + night-tablet renewal (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
)

DECOYS_PLAIN = (
    Decoy(patient_id="pt_morcote"),
    Decoy(patient_id="pt_munby"),
)
DECOYS_SPLIT = (
    Decoy(patient_id="pt_morcote"),
    Decoy(patient_id="pt_munby", defusing_caller_id="pt_munby_b"),
)

CARDS = (
    # claimants
    pt_marbrook,
    pt_nashwell,
    pt_maycote,
    pt_norholm,
    pt_millgarth,
    pt_nasegill,
    pt_merefold,
    pt_nunthwaite,
    pt_moorden,
    pt_nettleridge,
    pt_malmead,
    pt_norcliffe,
    pt_mickleholm,
    pt_nybrook,
    pt_marchsett,
    pt_newgill,
    pt_mossridge,
    pt_narfold,
    # holders
    pt_maplecote,
    pt_norbrook,
    pt_midholm,
    pt_nunwell,
    pt_marlgill,
    pt_nabcote,
    pt_medthwaite,
    pt_norgill,
    pt_marwell,
    pt_nidcote,
    pt_munden,
    pt_narlund,
    pt_maisgarth,
    pt_netherby,
    pt_maisdon,
    pt_netherholm,
    pt_maismead,
    pt_nethergarth,
    # carriers
    pt_nashwell_b,
    pt_newby,
    pt_nunthwaite_b,
    pt_maunby,
    pt_mickleholm_b,
    pt_millroyd,
    # decoys + defuser
    pt_morcote,
    pt_munby,
    pt_munby_b,
)

#: The one sanctioned same-surname shape: family carriers riding their claimant's (or decoy's) surname.
KIN_OF = {
    "pt_nashwell_b": "pt_nashwell",
    "pt_nunthwaite_b": "pt_nunthwaite",
    "pt_mickleholm_b": "pt_mickleholm",
    "pt_munby_b": "pt_munby",
}

#: Arrival plan, identical across the twins (the split adds RECALL beats, which are call structure).
#: The corpus quartet carries the background and the voicemail trio, on `deadline_day`'s pattern.
#: Carriers ride mid-shift, twenty-odd minutes behind their claimants — the live steward gate
#: showed the old 110-135 carrier tail left the assembled cases
#: too little shift to act in; every evidence piece now lands by t=124 of the 240.
#: TAIL ORDER MATTERS on the meshfull floor: desks are minted per caller in first-arrival order
#: (`spreadsheet_id`), the 18 holders round-robin onto the first 18 desks, and `naive_plan` races
#: desks lexicographically — so the double-letter desks AA-AE (first-arrival indexes 26-30) run
#: BEFORE the holders on B-R. A claimant in the last five arrival positions outraces their holder
#: in the naive floor and S10v2 refuses the cell; the tail five stay routine callers.
ARRIVALS = (
    ("pt_marbrook", "A", 0),
    ("pt_nashwell", "B", 5),
    ("pt_maycote", "C", 10),
    ("pt_lachaux", "B", 14),
    ("pt_norholm", "D", 18),
    ("pt_millgarth", "A", 23),
    ("pt_nasegill", "B", 28),
    ("pt_dunmore", "C", 32),
    ("pt_merefold", "D", 36),
    ("pt_nunthwaite", "A", 41),
    ("pt_nashwell_b", "C", 45),
    ("pt_moorden", "B", 46),
    ("pt_morcote", "C", 50),
    ("pt_newby", "D", 52),
    ("pt_nettleridge", "D", 55),
    ("pt_malmead", "A", 60),
    ("pt_ledwidge", "A", 64),
    ("pt_norcliffe", "B", 68),
    ("pt_mickleholm", "C", 73),
    ("pt_nunthwaite_b", "B", 75),
    ("pt_munby", "D", 78),
    ("pt_nybrook", "A", 82),
    ("pt_marchsett", "B", 85),
    ("pt_mossridge", "A", 88),
    ("pt_newgill", "C", 91),
    ("pt_narfold", "B", 94),
    ("pt_maunby", "A", 99),
    ("pt_arundel", "D", 100),
    ("pt_mickleholm_b", "D", 103),
    ("pt_millroyd", "C", 106),
    ("pt_munby_b", "A", 140),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

MEMO_COVER_LINE = (
    "The neurology diary is carrying the epilepsy-monitoring list the practice took on when the "
    "Fenchurch Road surgery closed at the end of last month, so those columns run far fuller than "
    "usual today."
)

# ── the plain twin: every claimant's whole story in their own single intake ──────────────────────────────
PLAIN_EVIDENCE = tuple(
    EvidenceCall(caller_id=contest.claimant, about_claimant=contest.claimant)
    for contest in CONTESTS
)

# ── the split twin: piece 1 routine, the decisive fact in a ring-back or a carrier's call ────────────────
SPLIT_EVIDENCE = (
    # 01 Marbrook: intake A + recall C
    EvidenceCall(caller_id="pt_marbrook", about_claimant="pt_marbrook"),
    EvidenceCall(
        caller_id="pt_marbrook",
        about_claimant="pt_marbrook",
        kind="recall",
        at_min=58,
        desk="C",
        text=MARBROOK_RECALL,
    ),
    # 02 Nashwell: intake B + wife's call C
    EvidenceCall(caller_id="pt_nashwell", about_claimant="pt_nashwell"),
    EvidenceCall(caller_id="pt_nashwell_b", about_claimant="pt_nashwell"),
    # 03 Maycote: intake C + recall A
    EvidenceCall(caller_id="pt_maycote", about_claimant="pt_maycote"),
    EvidenceCall(
        caller_id="pt_maycote",
        about_claimant="pt_maycote",
        kind="recall",
        at_min=52,
        desk="A",
        text=MAYCOTE_RECALL,
    ),
    # 04 Norholm: intake D + recall B
    EvidenceCall(caller_id="pt_norholm", about_claimant="pt_norholm"),
    EvidenceCall(
        caller_id="pt_norholm",
        about_claimant="pt_norholm",
        kind="recall",
        at_min=58,
        desk="B",
        text=NORHOLM_RECALL,
    ),
    # 05 Millgarth: intake A + neighbour's call D
    EvidenceCall(caller_id="pt_millgarth", about_claimant="pt_millgarth"),
    EvidenceCall(caller_id="pt_newby", about_claimant="pt_millgarth"),
    # 06 Nasegill: intake B + recall D
    EvidenceCall(caller_id="pt_nasegill", about_claimant="pt_nasegill"),
    EvidenceCall(
        caller_id="pt_nasegill",
        about_claimant="pt_nasegill",
        kind="recall",
        at_min=64,
        desk="D",
        text=NASEGILL_RECALL,
    ),
    # 07 Merefold: intake D + recall A
    EvidenceCall(caller_id="pt_merefold", about_claimant="pt_merefold"),
    EvidenceCall(
        caller_id="pt_merefold",
        about_claimant="pt_merefold",
        kind="recall",
        at_min=70,
        desk="A",
        text=MEREFOLD_RECALL,
    ),
    # 08 Nunthwaite: intake A + son's call B
    EvidenceCall(caller_id="pt_nunthwaite", about_claimant="pt_nunthwaite"),
    EvidenceCall(caller_id="pt_nunthwaite_b", about_claimant="pt_nunthwaite"),
    # 09 Moorden: intake B + recall C
    EvidenceCall(caller_id="pt_moorden", about_claimant="pt_moorden"),
    EvidenceCall(
        caller_id="pt_moorden",
        about_claimant="pt_moorden",
        kind="recall",
        at_min=80,
        desk="C",
        text=MOORDEN_RECALL,
    ),
    # 10 Nettleridge: intake D + recall A
    EvidenceCall(caller_id="pt_nettleridge", about_claimant="pt_nettleridge"),
    EvidenceCall(
        caller_id="pt_nettleridge",
        about_claimant="pt_nettleridge",
        kind="recall",
        at_min=95,
        desk="A",
        text=NETTLERIDGE_RECALL,
    ),
    # 11 Malmead: intake A + recall B
    EvidenceCall(caller_id="pt_malmead", about_claimant="pt_malmead"),
    EvidenceCall(
        caller_id="pt_malmead",
        about_claimant="pt_malmead",
        kind="recall",
        at_min=98,
        desk="B",
        text=MALMEAD_RECALL,
    ),
    # 12 Norcliffe: intake B + neighbour's call A
    EvidenceCall(caller_id="pt_norcliffe", about_claimant="pt_norcliffe"),
    EvidenceCall(caller_id="pt_maunby", about_claimant="pt_norcliffe"),
    # 13 Mickleholm: intake C + daughter's call D + recall B (three pieces, three desks)
    EvidenceCall(caller_id="pt_mickleholm", about_claimant="pt_mickleholm"),
    EvidenceCall(caller_id="pt_mickleholm_b", about_claimant="pt_mickleholm"),
    EvidenceCall(
        caller_id="pt_mickleholm",
        about_claimant="pt_mickleholm",
        kind="recall",
        at_min=112,
        desk="B",
        text=MICKLEHOLM_RECALL,
    ),
    # 14 Nybrook: intake A + friend's call C + recall D (three pieces, three desks)
    EvidenceCall(caller_id="pt_nybrook", about_claimant="pt_nybrook"),
    EvidenceCall(caller_id="pt_millroyd", about_claimant="pt_nybrook"),
    EvidenceCall(
        caller_id="pt_nybrook",
        about_claimant="pt_nybrook",
        kind="recall",
        at_min=108,
        desk="D",
        text=NYBROOK_RECALL,
    ),
    # 15 Marchsett: intake B + recall C
    EvidenceCall(caller_id="pt_marchsett", about_claimant="pt_marchsett"),
    EvidenceCall(
        caller_id="pt_marchsett",
        about_claimant="pt_marchsett",
        kind="recall",
        at_min=116,
        desk="C",
        text=MARCHSETT_RECALL,
    ),
    # 16 Newgill: intake C + recall D
    EvidenceCall(caller_id="pt_newgill", about_claimant="pt_newgill"),
    EvidenceCall(
        caller_id="pt_newgill",
        about_claimant="pt_newgill",
        kind="recall",
        at_min=118,
        desk="D",
        text=NEWGILL_RECALL,
    ),
    # 17 Mossridge: intake A + recall B
    EvidenceCall(caller_id="pt_mossridge", about_claimant="pt_mossridge"),
    EvidenceCall(
        caller_id="pt_mossridge",
        about_claimant="pt_mossridge",
        kind="recall",
        at_min=120,
        desk="B",
        text=MOSSRIDGE_RECALL,
    ),
    # 18 Narfold: intake B + recall A
    EvidenceCall(caller_id="pt_narfold", about_claimant="pt_narfold"),
    EvidenceCall(
        caller_id="pt_narfold",
        about_claimant="pt_narfold",
        kind="recall",
        at_min=124,
        desk="A",
        text=NARFOLD_RECALL,
    ),
)

#: The split twin's per-card intake overrides: claimants say only their routine piece 1, carriers add
#: the fact they alone carry, and the second decoy's defusal moves into her husband's call.
SPLIT_INTAKE_OVERRIDES = {
    "pt_marbrook": MARBROOK_SPLIT_INTAKE,
    "pt_nashwell": NASHWELL_SPLIT_INTAKE,
    "pt_maycote": MAYCOTE_SPLIT_INTAKE,
    "pt_norholm": NORHOLM_SPLIT_INTAKE,
    "pt_millgarth": MILLGARTH_SPLIT_INTAKE,
    "pt_nasegill": NASEGILL_SPLIT_INTAKE,
    "pt_merefold": MEREFOLD_SPLIT_INTAKE,
    "pt_nunthwaite": NUNTHWAITE_SPLIT_INTAKE,
    "pt_moorden": MOORDEN_SPLIT_INTAKE,
    "pt_nettleridge": NETTLERIDGE_SPLIT_INTAKE,
    "pt_malmead": MALMEAD_SPLIT_INTAKE,
    "pt_norcliffe": NORCLIFFE_SPLIT_INTAKE,
    "pt_mickleholm": MICKLEHOLM_SPLIT_INTAKE,
    "pt_nybrook": NYBROOK_SPLIT_INTAKE,
    "pt_marchsett": MARCHSETT_SPLIT_INTAKE,
    "pt_newgill": NEWGILL_SPLIT_INTAKE,
    "pt_mossridge": MOSSRIDGE_SPLIT_INTAKE,
    "pt_narfold": NARFOLD_SPLIT_INTAKE,
    "pt_nashwell_b": NASHWELL_B_SPLIT_INTAKE,
    "pt_newby": NEWBY_SPLIT_INTAKE,
    "pt_nunthwaite_b": NUNTHWAITE_B_SPLIT_INTAKE,
    "pt_maunby": MAUNBY_SPLIT_INTAKE,
    "pt_mickleholm_b": MICKLEHOLM_B_SPLIT_INTAKE,
    "pt_millroyd": MILLROYD_SPLIT_INTAKE,
    "pt_munby": MUNBY_SPLIT_INTAKE,
    "pt_munby_b": MUNBY_B_SPLIT_INTAKE,
}

#: The split twin's fact rewrites: the canonical answers are the PLAIN twin's and
#: restate the assembled case, so every claimant answer that names the fluconazole — or presupposes the
#: same-day level — is replaced with what that patient would volunteer to one ordinary probe: the new
#: tablets in passing WITHOUT the decisive name, the symptom on its own, never the maintenance context in
#: the same breath. The plain twin declares nothing.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_marbrook": {
        "medications": (
            "Carbamazepine, the slow kind, morning and night, and my brown inhaler — and some tablets "
            "the out-of-hours doctor left me for my mouth; I would have to fetch the packet for the "
            "name."
        ),
        "context": "I am home all day and ten minutes' walk away; whenever suits the surgery suits me.",
    },
    "pt_nashwell": {
        "medications": (
            "Carbamazepine morning and night, the blood-pressure tablet in the morning — and something "
            "the emergency dentist gave me yesterday for the sore patch; my wife keeps the box and I "
            "could not tell you the name."
        ),
    },
    "pt_maycote": {
        "severity": "No symptoms at all — I am perfectly well in myself.",
        "medications": (
            "Carbamazepine, the slow-release, twice a day — and a tablet from the walk-in place at the "
            "weekend; the name has gone out of my head."
        ),
    },
    "pt_norholm": {
        "onset": (
            "Nothing much — it was the medicines list I rang about. Though I was unsteady on the "
            "landing this morning, hand out for the rail, which is new."
        ),
        "medications": (
            "Carbamazepine morning and evening, the statin at night — and some tablets the out-of-hours "
            "doctor left on Sunday; I would have to look at the packet for the name."
        ),
    },
    "pt_millgarth": {
        "onset": (
            "The swimmy-headed spells began yesterday teatime — a breath and they pass. Nothing else "
            "new since I rang about the repeat."
        ),
        "medications": (
            "Carbamazepine twice a day, the waterworks tablet in the morning — and the dental place "
            "left me tablets at the weekend for under the plate; the name escapes me."
        ),
    },
    "pt_nasegill": {
        "onset": (
            "Queasy and dozy since I got up, that is all that is new in myself. Last week's water "
            "infection is done with."
        ),
        "medications": (
            "Carbamazepine slow-release twice daily, levothyroxine of a morning — and a tablet the "
            "out-of-hours doctor prescribed last night; I never caught the name of it."
        ),
        "context": "I am off work today in any case; I can come in whenever suits.",
    },
    "pt_merefold": {
        "onset": (
            "The double-vision flickers started this morning — a second or two at the screen, then it "
            "snaps back. Nothing else new."
        ),
        "medications": (
            "Carbamazepine twice a day — and some tablets the private weekend doctor gave me on Sunday "
            "for a rash; I have not got the box on me for the name."
        ),
    },
    "pt_nunthwaite": {
        "onset": (
            "Nothing I would have rung twice about — my son says I have been nodding off mid-sentence "
            "since yesterday, which he finds funnier than I do."
        ),
        "medications": (
            "Carbamazepine twice daily, a water tablet of a morning — and something the out-of-hours "
            "doctor started me on on Sunday for the sore mouth; Peter keeps track of the names, not me."
        ),
    },
    "pt_moorden": {
        "onset": (
            "The print in the paper went doubled this morning whenever I got tired-eyed — a blink and "
            "it cleared. Nothing else new."
        ),
        "medications": (
            "Carbamazepine slow-release twice daily, the statin at night — and the emergency dentist "
            "left me tablets yesterday for under the bridge; I could not give you the name off-hand."
        ),
        "context": "Retired; I can be with you within the half hour whenever suits.",
    },
    "pt_nettleridge": {
        "onset": "Nothing in myself at all — it was only my repeat I rang about.",
        "severity": "No symptoms whatever. I am quite well.",
        "medications": (
            "Carbamazepine slow-release twice a day — and a tablet from the out-of-hours doctor last "
            "night; I did not take note of the name."
        ),
    },
    "pt_malmead": {
        "onset": (
            "My legs went like jelly on the back step this morning — I sat on the step and it passed. "
            "That is the only news."
        ),
        "medications": (
            "Carbamazepine twice daily, the stomach tablet of a morning — and a course the private "
            "doctor started on Sunday for my nail; I would have to find the box for the name."
        ),
    },
    "pt_norcliffe": {
        "onset": (
            "Nothing beyond being found dozing over my lunch yesterday, which is not my habit at all."
        ),
        "medications": (
            "Carbamazepine twice daily, the bone tablet on Sundays — and the emergency dentist gave me "
            "tablets on Saturday for the corners of my mouth; I cannot lay my tongue to the name."
        ),
    },
    "pt_mickleholm": {
        "onset": (
            "Sleepy as a cat since yesterday, and sick to my stomach this morning — Ann noticed before "
            "I said a word."
        ),
        "medications": (
            "Carbamazepine morning and night, my calcium — and the tablets the out-of-hours doctor "
            "left on Sunday; Ann would know the name, I do not."
        ),
    },
    "pt_nybrook": {
        "onset": (
            "Reading the paper this morning the lines doubled up on me twice, a second each time. "
            "Otherwise nothing new."
        ),
        "medications": (
            "Carbamazepine slow-release twice daily, the blood-pressure one of a morning — and "
            "whatever the out-of-hours doctor gave me Saturday night; the name escapes me just now."
        ),
    },
    "pt_marchsett": {
        "onset": "Nothing in myself — I only rang about the repeat.",
        "severity": "No symptoms at all — I feel absolutely fine.",
        "medications": (
            "Carbamazepine slow-release twice daily — and a tablet from the private clinic in the "
            "retail park since Sunday evening; I could not tell you what it is called without the box."
        ),
    },
    "pt_newgill": {
        "onset": (
            "The heavy-headedness came after breakfast — as if I had been up half the night, which I "
            "had not."
        ),
        "medications": (
            "Carbamazepine twice a day, drops for the eyes at night — and the dental place gave me "
            "tablets yesterday for the sore mouth; my granddaughter has the bag with the box in it."
        ),
    },
    "pt_mossridge": {
        "onset": (
            "One unsteady moment with the tea tray this morning — a shoulder to the doorframe for a "
            "step or two, nothing since."
        ),
        "medications": (
            "Carbamazepine slow-release twice daily, an allergy tablet in season — and the tablets "
            "from the out-of-hours doctor since last night; I did not register the name."
        ),
    },
    "pt_narfold": {
        "onset": "Nothing in myself — I rang about the repeat that had not gone through.",
        "severity": "No symptoms at all; I am perfectly well.",
        "medications": (
            "Carbamazepine slow-release twice daily — and a course the private clinic started on "
            "Sunday night; I do not have the name in front of me."
        ),
        "context": "Working from home today; I am twenty minutes off if ever I am needed.",
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=18,
    theme_slug="carbamazepine_fluconazole",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=PLAIN_EVIDENCE,
    decoys=DECOYS_PLAIN,
    cards=CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="240",
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=18,
    theme_slug="carbamazepine_fluconazole",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=SPLIT_EVIDENCE,
    decoys=DECOYS_SPLIT,
    cards=CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="240",
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
