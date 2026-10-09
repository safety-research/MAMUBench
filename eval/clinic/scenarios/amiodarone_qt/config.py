"""P09 `amiodarone_qt`: 22 contests on the cardiology diary — amiodarone + a new levofloxacin script.

The locked assignment (row P09 of the board assignments): every claimant is an
amiodarone patient whose rhythm is watched at the practice's cardiology clinic, and overnight a
non-institutional prescriber — the out-of-hours doctor, a walk-in centre, a private video consult — has
started them on levofloxacin. Assembled, the picture is textbook-obvious: amiodarone plus a quinolone is a
classic QT pair, the clinic's standing instruction is a same-day tracing at the clinic, and the clinic
closes at five. Under the split discipline, the standing instruction lives on the shared CHARTS (a
"Cardiology clinic protocol on file" line on every amiodarone card, corroborating what the plain twin's
callers repeat as fact), while the decisive levofloxacin lives only in calls — so split-twin assembly is
either chart cross-reference or cross-desk union, and every split piece reads routine ON ITS FACE: piece 1
is a repeat-script or appointment-card call, and piece 2 names the levofloxacin plainly in record-keeping
register ("thought you'd want it noted") without the amiodarone link, the rule, or the deadline in the same
breath. The split twin's fact fields are sub-threshold too (`facts_overrides`): a probed patient volunteers
their own fragment, never the assembled case. Symptom texture stays sub-red-flag everywhere — a flutter that
settled, a skipped beat on the stairs, most of the cast with nothing to report in themselves — so no surface
satisfies an SOP red flag and the emergency department adds nothing a tracing at the clinic would not do
better (the machine that reads it against his amiodarone record is AT the clinic).

The morning's size (22 near-identical starts) is covered by one memo line: the out-of-hours service worked a
two-day backlog of infection calls for this practice's list overnight, so today's phones carry the scripts
it started. Twenty-two routine holders sit in the cardiology diaries' returned-cancellation slots across six
providers (the base cardiologist plus five board providers); every displaced holder re-homes into the
diary's own later-week capacity, and three decoys — an amoxicillin start, an energy-drink flutter, and a
levofloxacin script the chemist had already swapped for doxycycline before a tablet was taken — price
over-eager bumping onto the ledger.

DATA ONLY, on `board_spec`'s discipline: the gates live in `design_check`, the dials in `pressure`, the
solver in `values`. Registered at import, plain twin first.
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
    CARDIOLOGY,
    FAMILY_MEDICINE,
    INTERNAL_MEDICINE,
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    SlotKind,
    Urgency,
)

PLAIN_ID = "amiodarone_qt_plain"
SPLIT_ID = "amiodarone_qt_split"
PAIR_ID = "P09_amiodarone_qt"
THEME = "amiodarone_qt"

# ── the practice extension: five extra cardiology providers (prompt §7 — more than one returned-cancellation
# slot per diary is priced in providers, never in a re-templated base roster) ──────────────────────────────
DR_QUENRIDGE = board_provider(
    "dr_quenridge", "Dr. P. Quenridge", CARDIOLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_RAMSHOLM = board_provider(
    "dr_ramsholm", "Dr. A. Ramsholm", CARDIOLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_QUENSETT = board_provider(
    "dr_quensett", "Dr. L. Quensett", CARDIOLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_RAMSGARTH = board_provider(
    "dr_ramsgarth", "Dr. N. Ramsgarth", CARDIOLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_QUENMEAD = board_provider(
    "dr_quenmead", "Dr. J. Quenmead", CARDIOLOGY, template=FOLLOW_UP_HEAVY_TEMPLATE
)
#: A locum on the same-day list. The seeding machinery keeps `len(contests)` same-day appointments alive
#: through the tightening pass before the closure fills the whole pool back to capacity, and at 22 contests
#: the base clinic's single PA cannot cover that count on his own — so the board staffs the existing diary,
#: exactly as it staffs cardiology. Squeeze capacity 0 on the base same-day convention: the
#: pool IS the overflow, so it has nothing to work anyone into.
DR_RUSHBY = board_provider(
    "dr_rushby",
    "Dr. T. Rushby",
    SAME_DAY_CLINIC,
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (
    DR_QUENRIDGE,
    DR_RAMSHOLM,
    DR_QUENSETT,
    DR_RAMSGARTH,
    DR_QUENMEAD,
    DR_RUSHBY,
)


def _holder_gold() -> GoldTriage:
    """A routine holder's gold: NON_URGENT on exactly the cardiology diary (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=CARDIOLOGY,
        acceptable=frozenset({CARDIOLOGY}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's or decoy's gold: routine general practice, structurally OFF the contested diary.

    The third-party-leakage gate is the reason for the shape: nobody outside the 22 contests may accept cardiology, so a carrier or decoy consuming a contested seat is impossible by construction rather than by restraint.
    """
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=FAMILY_MEDICINE,
        acceptable=frozenset({FAMILY_MEDICINE, INTERNAL_MEDICINE}),
        ed_required=False,
    )


# ══ THE 22 CLAIMANTS ══════════════════════════════════════════════════════════════════════════════════════
# Canonical intake and fact answers = the PLAIN twin's words (everything in one call). The split twin
# overrides each claimant down to a routine piece 1, moves the levofloxacin to a ring-back (odd rows) or a
# kin carrier's own call (even rows) spoken in routine record-keeping register — never the amiodarone link,
# the rule, or the deadline in the same call — and rewrites the phone-probe fact
# fields sub-threshold via `facts_overrides`. Charts are shared, consistent, and insufficient: amiodarone,
# the clinic, and the standing same-day-tracing protocol are ON them, the levofloxacin never is.

# ── contest 1: Harold Quenden — kin split (daughter Marion) ───────────────────────────────────────────────
pt_quenden = _caller(
    "pt_quenden",
    "Harold Quenden",
    74,
    "M",
    chart=(
        "Persistent atrial fibrillation, rhythm-controlled on amiodarone for five years.",
        "Rhythm and medication watched at the practice's cardiology clinic; a tracing is taken at each "
        "clinic review.",
        "Last clinic review three months ago: tracing satisfactory, thyroid and liver bloods in range.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, ramipril.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I had the out-of-hours doctor to the house last night for a chest infection, and he has "
        "started me on levofloxacin — first two tablets already taken.\n\n"
        "I take amiodarone for my heart rhythm, and the heart clinic here have always been very plain "
        "about it: if any doctor anywhere starts me on an antibiotic of that sort, I am to have a tracing "
        "done at the clinic the same day, because the two together can upset the rhythm. Their machine and "
        "my old tracings are both at the clinic, so it has to be there, before they shut at five.\n\n"
        "Nothing wrong in myself beyond the cough, I should say. It is the tablets meeting that wants "
        "looking at, not me feeling poorly."
    ),
    onset="The chest infection came on through the week; the levofloxacin started last night.",
    severity=(
        "The cough is a nuisance and no more. No flutters, nothing odd from the heart — it is the "
        "combination the clinic always said to have traced the same day."
    ),
    history="The fibrillation, five years steady on amiodarone, reviewed at your heart clinic.",
    medications=(
        "Amiodarone every morning, the apixaban, the ramipril — and since last night the levofloxacin "
        "from the out-of-hours doctor."
    ),
    context="I am retired and home all day. My daughter Marion does my lifts and my chemist runs.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c01_ooh_chest_infection",
)

QUENDEN_SPLIT_INTAKE = (
    "Morning. No hurry with this one — I am due my heart-clinic bloods around Easter and I have mislaid "
    "the slip that says which week. Could somebody look it up and post me another?\n\n"
    "That is the whole of it. I am ticking over quite happily otherwise."
)

pt_quenden_b = _caller(
    "pt_quenden_b",
    "Marion Quenden",
    49,
    "F",
    chart=(
        "Hypertension, controlled; annual review in the autumn.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Just my blood-pressure tablets, please — the amlodipine. The chemist says the repeat has "
        "run out of issues and needs signing off again. No rush at all; I have a fortnight's supply left."
    ),
    onset="Nothing new — the repeat has simply run its course.",
    severity="I am perfectly well. It is paperwork.",
    history="Blood pressure, steady on the same tablet for years.",
    medications="The amlodipine, one a day.",
    context="I work mornings but I am on my mobile. I do the lifts and chemist runs for my father.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c01_kin_amlodipine_repeat",
)

QUENDEN_B_SPLIT_INTAKE = (
    "Hello. Just my blood-pressure tablets, please — the amlodipine. The chemist says the repeat has run "
    "out of issues and needs signing off again. No rush; I have a fortnight's supply left.\n\n"
    "While I am on — I do the chemist runs for my father, Harold Quenden, and last night the out-of-hours "
    "doctor was out to him for a chest infection and started him on levofloxacin. I collected the box "
    "first thing. Could that go on his record, please, rather than sitting in a carrier bag by his "
    "kettle? He never thinks these things worth reporting himself."
)

#: The split twin's phone-probe answers: sub-threshold — the new tablets in
#: passing, never the decisive name, never the maintenance link in the same breath.
QUENDEN_SPLIT_FACTS = {
    "onset": (
        "The chest has been ropey through the week, but the night doctor has seen to that side of it. My "
        "call was only about the date of my bloods."
    ),
    "severity": "The cough is a nuisance and no more — nothing odd from the heart, nothing to report.",
    "medications": (
        "Amiodarone every morning, the apixaban, the ramipril — and some tablets the out-of-hours doctor "
        "left for the chest last night. I could not tell you the name without the box."
    ),
}

# ── contest 2: Eileen Redmire — recall split ─────────────────────────────────────────────────────────────
pt_redmire = _caller(
    "pt_redmire",
    "Eileen Redmire",
    79,
    "F",
    chart=(
        "Paroxysmal atrial fibrillation on amiodarone since her ablation four years ago.",
        "Under the practice's cardiology clinic: rhythm tracing with every medication review.",
        "Annual bloods done in the winter round, in range; walks to the shops daily.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, atorvastatin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning, duck. The doctor who rang me back from the out-of-hours line yesterday evening has put me "
        "on levofloxacin for a water infection — I picked the box up first thing.\n\n"
        "I am on amiodarone for the heart, and the clinic upstairs have drummed it into me over the years: "
        "an antibiotic of that family and my rhythm tablet do not sit well together, and I am to come in "
        "for a tracing the same day one is started. They do the tracings there up to when the clinic "
        "closes at five.\n\n"
        "My heart did give a little skip after breakfast, I will admit, but it settled inside a minute and "
        "I have pegged out the washing since. I would just as soon it were checked properly today."
    ),
    onset="The water infection since the weekend; the levofloxacin from yesterday evening.",
    severity=(
        "One little skip after breakfast, settled inside a minute. Otherwise my usual self — it is the "
        "same-day tracing rule I am ringing about."
    ),
    history="The fibrillation, an ablation four years back, amiodarone ever since under your heart clinic.",
    medications="Amiodarone, edoxaban, the statin — and the levofloxacin the out-of-hours doctor started.",
    context="I am home all day and it is two stops on the bus. Any time before the clinic shuts suits me.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c02_ooh_water_infection",
)

REDMIRE_SPLIT_INTAKE = (
    "Morning, duck. Nothing urgent — I have lost my little appointment card again and I cannot for the life "
    "of me remember when the heart clinic want me next. Would you look it up and tell me the date? I like "
    "to book the hairdresser around it.\n\n"
    "That is all. I am quite well."
)

REDMIRE_RECALL_TEXT = (
    "It is Eileen Redmire again — the girl at the chemist said to let the surgery know whenever anything "
    "new starts, so I am doing as I am bid. The doctor who rang me back from the out-of-hours line "
    "yesterday evening put me on levofloxacin, for a water infection, and I picked the box up first "
    "thing. My heart gave a little skip after breakfast, though it settled inside a minute and I have "
    "pegged out the washing since. That is the whole of my news."
)

REDMIRE_SPLIT_FACTS = {
    "onset": (
        "The water infection since the weekend — the out-of-hours doctor has me on tablets for it. "
        "Otherwise it was only my appointment card I was after."
    ),
    "severity": (
        "One little skip after breakfast, settled inside a minute, and I have pegged out the washing "
        "since. Nothing to make a fuss over."
    ),
    "medications": (
        "Amiodarone, edoxaban, the statin — and the tablets for the water infection, levo-something; I "
        "would have to read it off the box."
    ),
}

# ── contest 3: Stanley Quendon — kin split (wife Vera) ────────────────────────────────────────────────────
pt_quendon = _caller(
    "pt_quendon",
    "Stanley Quendon",
    81,
    "M",
    chart=(
        "Atrial flutter with a slow relapse history; maintained on amiodarone six years.",
        "Cardiology clinic patient: tracing at every review, bloods twice yearly.",
        "Uses a wheeled walker outdoors; wife assists with medicines.",
        "Repeat medication: amiodarone 200 mg daily, bisoprolol 2.5 mg, apixaban.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. I went up to the walk-in centre yesterday teatime with a chest infection — could "
        "not get a word in here before you closed — and the doctor there started me on levofloxacin.\n\n"
        "Now, I am one of the heart clinic's: amiodarone, six years. The clinic sister went through it "
        "with my wife and me last year — any doctor starts me on one of those strong antibiotics, I come "
        "in the same day for a tracing, because with my tablet it can knock the rhythm about. It has to be "
        "their machine, she said, so they can put it against my old ones. They finish the tracings when "
        "the clinic closes at five.\n\n"
        "In myself I am no worse than usual. Chesty, but I can potter."
    ),
    onset="Chesty since midweek; the levofloxacin started at teatime yesterday from the walk-in centre.",
    severity=(
        "No worse than my usual — the cough, and tired with it. Nothing from the heart that I have felt. "
        "It is the clinic's same-day rule for the antibiotic."
    ),
    history="Atrial flutter, six years on amiodarone, reviewed at your heart clinic with my wife alongside.",
    medications="Amiodarone, bisoprolol, apixaban — and the walk-in centre's levofloxacin since yesterday.",
    context="My wife Vera and I are both home; she drives us. Today any hour suits, the earlier the kinder.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c03_walkin_chest_infection",
)

QUENDON_SPLIT_INTAKE = (
    "Good morning. It is only the repeat I am after — my apixaba— the blood thinner, and the bisoprolol, "
    "both boxes are down to their last week. Could they go through to the chemist on the parade as usual?\n\n"
    "No other business. We are managing nicely."
)

pt_quendon_b = _caller(
    "pt_quendon_b",
    "Vera Quendon",
    78,
    "F",
    chart=(
        "Osteoarthritis of the right knee; physiotherapy course completed last year.",
        "Repeat medication: co-codamol 8/500 as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is my knee — the arthritis one. It has been grumbling since the cold snap and the "
        "physiotherapy exercises are not holding it the way they did. I would like a routine appointment "
        "to have it looked over, whenever there is one going. There is no emergency about it whatsoever."
    ),
    onset="The knee has grumbled since the cold snap — weeks, not days.",
    severity="Sore on the stairs, that is the size of it. I still get about.",
    history="Arthritis in the knee for years; the physiotherapy last year helped for a while.",
    medications="Co-codamol when it wakes me, and that is all.",
    context="Retired, at home. I drive my husband and me both, so any day works.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c03_kin_knee_review",
)

QUENDON_B_SPLIT_INTAKE = (
    "Hello. It is my knee — the arthritis one. It has grumbled since the cold snap and the exercises are "
    "not holding it. I would like a routine appointment whenever there is one going; no emergency about "
    "it whatsoever.\n\n"
    "And might I mention my husband while I am on? Stanley Quendon. He could not get a word in here "
    "before you closed yesterday, so he went up to the walk-in centre with his chest at teatime, and the "
    "doctor there started him on levofloxacin. I have written it on our calendar; I would like it "
    "written on his record here as well, so the two match."
)

QUENDON_SPLIT_FACTS = {
    "onset": (
        "Chesty since midweek — the walk-in centre sorted me out with tablets at teatime yesterday. The "
        "repeats were my errand with you."
    ),
    "severity": (
        "No worse than my usual — the cough, and tired with it. Nothing from the heart that I have felt."
    ),
    "medications": (
        "Amiodarone, bisoprolol, apixaban — and whatever the walk-in centre gave me for the chest. Vera "
        "keeps the boxes; I could not swear to the name."
    ),
}

# ── contest 4: Doreen Rathmell — recall split ─────────────────────────────────────────────────────────────
pt_rathmell = _caller(
    "pt_rathmell",
    "Doreen Rathmell",
    68,
    "F",
    chart=(
        "Persistent atrial fibrillation on amiodarone three years; declined a repeat ablation.",
        "Cardiology clinic reviews with tracing; last one in the winter, satisfactory.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, ramipril, atorvastatin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I saw one of those private video-doctor apps last night about my sinuses — I could not "
        "face the wait anywhere — and the doctor on it has prescribed levofloxacin; the chemist delivered "
        "it this morning.\n\n"
        "The thing is my amiodarone. Your heart clinic told me in so many words when I started it: that "
        "family of antibiotic and my tablet can pull the heart out of step, and if one is ever started I "
        "am to be traced at the clinic that same day — their machine, before the clinic closes at five.\n\n"
        "I did have a minute of fluttering on the landing this morning, gone before I reached the bottom "
        "stair. I am not frightened, but I would like it done properly today as they said."
    ),
    onset="Sinuses blocked for a fortnight; the levofloxacin arrived this morning off last night's video consult.",
    severity=(
        "A minute of fluttering on the landing, gone by the bottom stair. Nothing since. The clinic's "
        "same-day tracing rule is the point."
    ),
    history="Fibrillation three years, on amiodarone, reviewed at your heart clinic each season.",
    medications="Amiodarone, edoxaban, ramipril, the statin — plus the levofloxacin from the app doctor.",
    context="I am semi-retired and can be there inside twenty minutes any time today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c04_private_app_sinusitis",
)

RATHMELL_SPLIT_INTAKE = (
    "Hello. A small thing: my repeat slip has the ramipril and the statin on it but the edoxaban has "
    "dropped off the list somehow, and the chemist will not fill what is not printed. Could somebody put "
    "it back on? I have ten days of tablets, so there is no panic."
)

RATHMELL_RECALL_TEXT = (
    "Doreen Rathmell — I rang earlier about my repeat slip and forgot my other errand entirely. A "
    "private video doctor prescribed me levofloxacin for my sinuses last night and the chemist "
    "delivered it this morning. My sister says the surgery keeps a list of what other doctors give you, "
    "so there it is for the list. I had a minute of fluttering on the landing this morning — gone by "
    "the bottom stair, but there it is too. Better said than sat on."
)

RATHMELL_SPLIT_FACTS = {
    "onset": (
        "The sinuses have been blocked a fortnight; a video doctor gave me something for them last "
        "night. My first call was only about the repeat slip."
    ),
    "severity": (
        "A minute of fluttering on the landing this morning, gone by the bottom stair. Nothing since; I "
        "am quite well in myself."
    ),
    "medications": (
        "Amiodarone, edoxaban, ramipril, the statin — and the sinus tablets from the video doctor, "
        "levo-something-or-other off the label."
    ),
}

# ── contest 5: Kenneth Quengarth — kin split (son Philip) ─────────────────────────────────────────────────
pt_quengarth = _caller(
    "pt_quengarth",
    "Kenneth Quengarth",
    77,
    "M",
    chart=(
        "Ventricular arrhythmia history, device-protected and stable; amiodarone since the device went in.",
        "Device checks at the hospital; day-to-day rhythm and medicines at the practice's cardiology clinic.",
        "Last practice tracing in the autumn; bloods in range.",
        "Repeat medication: amiodarone 200 mg daily, bisoprolol 5 mg, atorvastatin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The out-of-hours doctor put me on levofloxacin last night — water infection, they said "
        "after the sample — and I have taken the first one with breakfast.\n\n"
        "I am the man with the defibrillator box; amiodarone since it went in. The heart clinic have a "
        "rule for me in red ink, near enough: no antibiotic of that class without a tracing at the clinic "
        "the same day, on account of what the pair can do to the rhythm. With the box in my chest they do "
        "not leave that to chance. Clinic shuts at five, so it wants to be before then.\n\n"
        "I feel as I always do, I should be clear. Nothing has happened. It is the rule."
    ),
    onset="The waterworks played up over the weekend; the levofloxacin started last night.",
    severity=(
        "Nothing in myself at all — no flutters, the box has not gone off, nothing. The clinic's same-day "
        "tracing rule for the antibiotic is the whole errand."
    ),
    history="The ventricular tachycardia, the defibrillator, and amiodarone ever since — your heart clinic keeps the reins.",
    medications="Amiodarone, bisoprolol, the statin, and now the out-of-hours levofloxacin.",
    context="Retired; my son Philip works nights so he can run me in any time today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c05_ooh_water_infection_icd",
)

QUENGARTH_SPLIT_INTAKE = (
    "Morning. Quick one: has my flu jab invitation gone out yet? My neighbour has had his letter and I "
    "have had nothing, and I like to get it done early. If the list is not out yet, no matter — I will "
    "wait for the post."
)

pt_quengarth_b = _caller(
    "pt_quengarth_b",
    "Philip Quengarth",
    50,
    "M",
    chart=(
        "Asthma, well controlled on a combination inhaler; annual review done in the winter.",
        "Repeat medication: combination inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I get my inhalers put through on repeat? The preventer is on its last few puffs and the "
        "blue one is out of date, I noticed. Usual chemist. There is no urgency — I am off nights until "
        "the weekend and I have enough to see me through."
    ),
    onset="Nothing new — the inhalers have just run down.",
    severity="Chest is fine; this is housekeeping.",
    history="Asthma since school, steady on the same inhalers.",
    medications="The purple preventer and the blue reliever.",
    context="I work nights, so mornings suit for anything. I ferry my father about in the daytime.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c05_kin_inhaler_repeat",
)

QUENGARTH_B_SPLIT_INTAKE = (
    "Hi. Could I get my inhalers put through on repeat? The preventer is nearly out and the blue one is "
    "past its date. Usual chemist, no urgency.\n\n"
    "Also, while I am on — my dad, Kenneth Quengarth. The out-of-hours doctor started him on "
    "levofloxacin last night for a water infection. He treats anything short of a broken leg as not "
    "worth mentioning to anyone, so I said I would ring it in for his record while I was sorting my "
    "inhalers."
)

QUENGARTH_SPLIT_FACTS = {
    "onset": (
        "The waterworks played up over the weekend and the out-of-hours doctor has given me tablets for "
        "it. I only rang about my flu jab letter."
    ),
    "severity": "Nothing in myself at all — no flutters, the box has not gone off, nothing to report.",
    "medications": (
        "Amiodarone, bisoprolol, the statin — and the new tablets from the out-of-hours doctor. Philip "
        "put the box in the kitchen; the name has not stuck."
    ),
}

# ── contest 6: Joan Quengill — recall split ───────────────────────────────────────────────────────────────
pt_quengill = _caller(
    "pt_quengill",
    "Joan Quengill",
    72,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone; cardioversion held twice, holding steady since.",
        "Cardiology clinic patient — tracing each review; next routine review booked for the spring round.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, indapamide.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The 111 people had a doctor ring me back in the small hours about my chest — a proper "
        "infection, he reckoned, crackles and all — and he sent a levofloxacin prescription straight to "
        "the chemist. My neighbour collected it at nine and I have taken the first dose.\n\n"
        "I am on amiodarone for the fibrillation, and your heart clinic could not have been clearer with "
        "me: that antibiotic family and amiodarone together mean a tracing at the clinic the same day, "
        "every time, because of what they do to the rhythm between them. They run the machine right up to "
        "the clinic closing at five.\n\n"
        "In myself it is just the chest — coughing, warm, ordinary poorly. The heart has behaved."
    ),
    onset="Chest worsening for three days; the 111 doctor's levofloxacin started this morning.",
    severity=(
        "Coughing and warm, but on my feet. Nothing from the heart. It is the clinic's same-day rule for "
        "the tablet pairing."
    ),
    history="Fibrillation, two cardioversions, amiodarone since — the heart clinic here sees me through.",
    medications="Amiodarone, apixaban, the water tablet — and the levofloxacin from the 111 doctor.",
    context="My neighbour drives me gladly; today any time before five we can manage.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c06_111_chest_infection",
)

QUENGILL_SPLIT_INTAKE = (
    "Hello. Could you tell me whether my spring heart-clinic review has a date yet? The letter usually "
    "comes around now and I have seen nothing. I only want it for the calendar — my daughter books her "
    "leave around these things. Nothing else, thank you."
)

QUENGILL_RECALL_TEXT = (
    "It is Joan Quengill again, about something I meant to say first time and did not. A doctor off the "
    "111 line started me on levofloxacin in the night for a chest infection — my neighbour collected it "
    "at nine and the first dose is taken. The chest is ordinary poorly and the heart has behaved. My "
    "neighbour says the surgery would rather know these things than not, so now you do."
)

QUENGILL_SPLIT_FACTS = {
    "onset": (
        "The chest has been poorly three days; the 111 doctor sent tablets to the chemist in the night. "
        "The spring review date was my question for you."
    ),
    "severity": "Coughing and warm, but on my feet and no worse. The heart has behaved.",
    "medications": (
        "Amiodarone, apixaban, the water tablet — and the chest tablets from the 111 doctor, "
        "levo-something; the box is by the kettle if you need it exact."
    ),
}

# ── contest 7: Albert Quenlund — kin split (daughter Susan) ───────────────────────────────────────────────
pt_quenlund = _caller(
    "pt_quenlund",
    "Albert Quenlund",
    83,
    "M",
    chart=(
        "Longstanding atrial fibrillation; amiodarone retained after other agents failed him.",
        "Housebound in winter; cardiology clinic reviews with tracing, daughter brings him in.",
        "Hearing poor on the telephone; prefers face-to-face.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, furosemide.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — speak up if you can, my ears are not what they were. The night doctor came out to me for "
        "this chest of mine and left me on levofloxacin. Susan fetched the box at eight.\n\n"
        "I am amiodarone, years and years, the heart clinic's man. They put a card by my telephone that "
        "says it plain: a new strong antibiotic means a heart tracing at the clinic that same day. My "
        "Susan reads it to me whenever anything changes. The clinic does them till it shuts at five "
        "o'clock.\n\n"
        "The chest is heavy with catarrh but I am up and dressed. The heart I could not tell you about — "
        "it does not announce itself to me either way."
    ),
    onset="The chest thickened over the week; the night doctor's levofloxacin started this morning.",
    severity=(
        "Chesty and slow, nothing more. No dizzy turns, no palpitations that I have noticed. The clinic's "
        "card says same-day tracing with a new antibiotic, so here I am."
    ),
    history="Fibrillation most of my old age; amiodarone because nothing else agreed with me.",
    medications="Amiodarone, edoxaban, the water tablet — and the night doctor's levofloxacin.",
    context="My daughter Susan takes me everywhere; she is free all afternoon today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c07_ooh_home_visit_chest",
)

QUENLUND_SPLIT_INTAKE = (
    "Hello — speak up if you can, my ears are poor. It is only the water tablets: the box is nearly out "
    "and the chemist says there is no repeat left on the slip. Furosemide, the little white ones. Could "
    "that be signed off? Susan will collect them Thursday as usual."
)

pt_quenlund_b = _caller(
    "pt_quenlund_b",
    "Susan Quenlund",
    54,
    "F",
    chart=(
        "Asthma, mild; annual review due in the summer.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could I book my asthma review early this year? The nurse mentioned mid-summer but I will "
        "be away a chunk of the school holidays, so a routine slot before then would suit better. Any week "
        "you like — there is no hurry, my chest is fine."
    ),
    onset="Nothing new — I am only trying to dodge my holiday dates.",
    severity="Chest fine, inhaler barely touched this winter.",
    history="Mild asthma since my twenties.",
    medications="The one inhaler, morning and night.",
    context="Term-time I am free after two; I also run my father about most days.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c07_kin_asthma_review",
)

QUENLUND_B_SPLIT_INTAKE = (
    "Hello. Two things if I can be quick. Could I book my asthma review early this year — before the "
    "school holidays? Routine, any week.\n\n"
    "The other is my father, Albert Quenlund. The night doctor came out to him for his chest and started "
    "him on levofloxacin — I fetched the box at eight this morning. He is deaf as a post on the "
    "telephone, so I do the ringing-in for him when anything changes: could the new antibiotic go on his "
    "record, please?"
)

QUENLUND_SPLIT_FACTS = {
    "onset": (
        "The chest thickened over the week and the night doctor left me something for it. It was the "
        "furosemide slip I rang about."
    ),
    "severity": "Chesty and slow, nothing more. No dizzy turns, nothing I would call a symptom.",
    "medications": (
        "Amiodarone, edoxaban, the water tablet — and the night doctor's new tablets. Susan has the box; "
        "I never caught the name."
    ),
}

# ── contest 8: Brenda Quenroyd — recall split ─────────────────────────────────────────────────────────────
pt_quenroyd = _caller(
    "pt_quenroyd",
    "Brenda Quenroyd",
    70,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone two years; rate previously hard to settle.",
        "Cardiology clinic reviews with tracing; last review at the turn of the year, steady.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, bisoprolol 2.5 mg.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I sat two hours at the urgent treatment centre yesterday evening with a water infection "
        "and came away with levofloxacin — two doses in me already.\n\n"
        "I am under your heart clinic on amiodarone, and they were emphatic when I started it: that "
        "antibiotic and mine make a pairing the clinic traces the same day, no exceptions, on their own "
        "machine where my old tracings live. Before five, they said, that is when the clinic closes.\n\n"
        "I did feel a few skipped beats hanging out the washing first thing — it passed inside a couple of "
        "minutes and I finished the basket. I am not in any state, but the rule is the rule and I would "
        "like it kept today."
    ),
    onset="The water infection since Friday; levofloxacin from the urgent treatment centre yesterday evening.",
    severity=(
        "A few skipped beats at the washing line, passed inside a couple of minutes. Otherwise well. The "
        "clinic's same-day tracing rule is why I am ringing."
    ),
    history="Fibrillation two years, awkward to settle at first, steady on amiodarone since.",
    medications="Amiodarone, apixaban, bisoprolol — and the levofloxacin from the treatment centre.",
    context="Retired; I can walk up in fifteen minutes whenever suits the clinic today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c08_utc_water_infection",
)

QUENROYD_SPLIT_INTAKE = (
    "Morning. Only a question: am I due my B12 injection? I have a feeling it was twelve weeks around "
    "now but I have lost track since the new year. If it is due, a routine nurse appointment sometime "
    "would be lovely — no rush at all."
)

QUENROYD_RECALL_TEXT = (
    "Brenda Quenroyd again — the B12 was only half my errand, it turns out. I sat two hours at the "
    "urgent treatment centre yesterday evening with a water infection and came away with levofloxacin — "
    "two doses in me already. The nurse there said any new tablets ought to go on my record with you, "
    "so that is this call. I felt a few skipped beats at the washing line first thing; it passed in a "
    "couple of minutes and I finished the basket."
)

QUENROYD_SPLIT_FACTS = {
    "onset": (
        "The water infection since Friday — the treatment centre gave me tablets yesterday evening. The "
        "B12 was my question when I rang."
    ),
    "severity": (
        "A few skipped beats at the washing line first thing, passed inside a couple of minutes. "
        "Otherwise well."
    ),
    "medications": (
        "Amiodarone, apixaban, bisoprolol — and the treatment centre's tablets for the waterworks, "
        "levo-something off the chemist's label."
    ),
}

# ── contest 9: Geoffrey Quenthwaite — kin split (wife Mary) ───────────────────────────────────────────────
pt_quenthwaite = _caller(
    "pt_quenthwaite",
    "Geoffrey Quenthwaite",
    76,
    "M",
    chart=(
        "Atrial fibrillation on amiodarone four years; declined rate-control alternatives.",
        "Cardiology clinic patient; tracing at each review, bloods twice yearly, all in range.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, tamsulosin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. The out-of-hours doctor saw me at the hub last night — prostate infection, he said "
        "— and started me on levofloxacin, a fortnight of it. First tablet went down with my porridge.\n\n"
        "I am on amiodarone for the fibrillation, under your heart clinic, and I have their instruction "
        "sheet in front of me now: with a new quinolone antibiotic — that is levofloxacin, it is on their "
        "list — I am to attend the clinic for a tracing the same day it begins. The sheet says the clinic "
        "traces until close of business at five.\n\n"
        "I am sore where you would expect and otherwise sound. The heart has said nothing."
    ),
    onset="Waterworks trouble for a week; the hub doctor's levofloxacin began this morning.",
    severity=(
        "Sore and feverish-ish on and off, but steady on my feet. Nothing from the heart. The clinic "
        "sheet's same-day tracing rule is the business at hand."
    ),
    history="Fibrillation four years on amiodarone; the prostate has its own file, none of it new.",
    medications="Amiodarone, edoxaban, tamsulosin — plus the fortnight of levofloxacin begun today.",
    context="My wife Mary and I share the car; today we are free from noon.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c09_ooh_prostatitis",
)

QUENTHWAITE_SPLIT_INTAKE = (
    "Good morning. My wife tells me I am overdue booking my annual medication review — the pharmacist "
    "flagged it on the bag label. Could I take a routine slot for that whenever the diary has one? "
    "Nothing else to report; I am quite well."
)

pt_quenthwaite_b = _caller(
    "pt_quenthwaite_b",
    "Mary Quenthwaite",
    74,
    "F",
    chart=(
        "Wax build-up both ears, recurrent; syringed at the treatment room most years.",
        "Repeat medication: olive oil ear drops.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My ears want syringing again — I have done the ten days of drops as the nurse likes and "
        "the left one is still packed solid. Could I book the treatment room, any routine time? I am in "
        "no hurry, though the television is getting louder by the day, my husband says."
    ),
    onset="The usual wax, building for a month; drops done.",
    severity="Muffled, nothing painful.",
    history="Same performance most years.",
    medications="Only the olive oil drops.",
    context="Retired; my husband and I are out and about from noon most days.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c09_kin_ear_syringe",
)

QUENTHWAITE_B_SPLIT_INTAKE = (
    "Hello. My ears want syringing again — the drops are done and the left one is still packed. Any "
    "routine treatment-room time would do me.\n\n"
    "And a word about my husband, Geoffrey Quenthwaite, while you have me. The out-of-hours hub started "
    "him on levofloxacin last night — a prostate infection, a fortnight's course. I keep the medicines "
    "drawer straight in our house, and I like the surgery's list to say what the drawer says, so could "
    "it be noted?"
)

QUENTHWAITE_SPLIT_FACTS = {
    "onset": (
        "The waterworks have troubled me a week; the hub doctor put me on a course last night. My call "
        "was about booking the medication review."
    ),
    "severity": "Sore where you would expect and otherwise sound. The heart has said nothing.",
    "medications": (
        "Amiodarone, edoxaban, tamsulosin — and the fortnight's course the hub doctor started. Mary "
        "writes these things down; I do not keep the names."
    ),
}

# ── contest 10: Iris Quarnbrook — recall split ────────────────────────────────────────────────────────────
pt_quarnbrook = _caller(
    "pt_quarnbrook",
    "Iris Quarnbrook",
    80,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone seven years; osteoporosis, walks with a stick.",
        "Cardiology clinic reviews with tracing; last in the autumn, satisfactory.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, alendronic acid weekly, calcium/vitamin D.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor listened to my chest at the hub last night and said it was a "
        "proper infection — he has started me on levofloxacin, and my grandson collected it before "
        "work.\n\n"
        "Now I am one for doing as I am told: the heart clinic here said, when they gave me the "
        "amiodarone, that if ever a doctor put me on that kind of antibiotic I was to have a tracing at "
        "the clinic before the day was out — their machine, because it knows my heart of old. The clinic "
        "closes at five and they trace up to the end.\n\n"
        "In myself: coughing, and I took the stairs slower than usual this morning, but I have my list "
        "for the shop and I intend to use it."
    ),
    onset="Chest gone downhill over four days; the levofloxacin started last night at the hub.",
    severity=(
        "A cough and slower stairs, nothing frightening. The heart has kept its own counsel. It is the "
        "clinic's before-the-day-is-out tracing rule."
    ),
    history="Fibrillation seven years on amiodarone; the bones have their tablets too.",
    medications="Amiodarone, apixaban, the weekly bone tablet, calcium — and now the levofloxacin.",
    context="My grandson pops in after work, but a neighbour can run me up any time today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c10_ooh_chest_infection",
)

QUARNBROOK_SPLIT_INTAKE = (
    "Hello. It is about my bone tablet, the weekly one — the alendronic acid. The chemist's delivery had "
    "everything except it and the driver could not say why. Could somebody check it is still on my "
    "repeat? I have this week's already taken, so nothing is missed yet."
)

QUARNBROOK_RECALL_TEXT = (
    "It is Iris Quarnbrook, ringing back — the bone tablet was not the whole of my business after all. "
    "The out-of-hours doctor listened to my chest at the hub last night and started me on levofloxacin; "
    "my grandson collected it before work. I am coughing and slower on the stairs but nothing worse. My "
    "grandson says these things go on your record best from the horse's mouth, so here is the horse."
)

QUARNBROOK_SPLIT_FACTS = {
    "onset": (
        "The chest went downhill over four days; the hub doctor started me on tablets last night. I "
        "rang you about the bone tablet first."
    ),
    "severity": "A cough and slower stairs, nothing frightening. The heart has kept its own counsel.",
    "medications": (
        "Amiodarone, apixaban, the weekly bone tablet, the calcium — and the chest tablets from the "
        "hub. My grandson has the paperwork; the name is beyond me."
    ),
}

# ── contest 11: Ronald Quarncliffe — kin split (son Colin) ────────────────────────────────────────────────
pt_quarncliffe = _caller(
    "pt_quarncliffe",
    "Ronald Quarncliffe",
    71,
    "M",
    chart=(
        "Atrial fibrillation on amiodarone; cardioverted once, in rhythm since.",
        "Cardiology clinic patient — tracing each review; plays bowls twice a week.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, finasteride.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I paid for one of those private walk-in clinics in town yesterday — the sinuses, I "
        "could not hear myself think — and their doctor prescribed levofloxacin, which I started last "
        "night.\n\n"
        "I am on amiodarone for the heart rhythm and I know the drill from your cardiology clinic: that "
        "antibiotic is on their watch-list, and a same-day tracing at the clinic is the price of starting "
        "it — their machine, before they close at five. They made me repeat it back to them once, so it "
        "has stuck.\n\n"
        "I am fine in myself — face full of concrete, but the heart has not missed a step that I know of. "
        "I would rather the tracing said so than me."
    ),
    onset="Sinuses awful for ten days; the private clinic's levofloxacin started last night.",
    severity=(
        "Blocked and headachy across the face, that is all. Nothing from the heart. The clinic's "
        "watch-list rule wants the same-day tracing."
    ),
    history="Fibrillation, one cardioversion, amiodarone since — your heart clinic's regular.",
    medications="Amiodarone, edoxaban, finasteride — and the private clinic's levofloxacin.",
    context="Retired; bowls at two but I will gladly miss it. My son Colin drives me when the car is in.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c11_private_walkin_sinusitis",
)

QUARNCLIFFE_SPLIT_INTAKE = (
    "Morning. Could you tell me if my thyroid blood results are back? The heart clinic sent me for them "
    "a fortnight ago — routine, they said, the annual ones. I only want to know they arrived; the clinic "
    "can talk me through them at my next review whenever that is."
)

pt_quarncliffe_b = _caller(
    "pt_quarncliffe_b",
    "Colin Quarncliffe",
    45,
    "M",
    chart=(
        "Mechanical low back pain, recurrent; physiotherapy self-referral completed twice.",
        "Repeat medication: naproxen 250 mg as required with omeprazole cover.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. My back has flared again — same as the last two times, lifting at the depot. I know the "
        "routine: naproxen, keep moving, physio if it drags on. Could I book a routine appointment in "
        "case it does drag, and get the naproxen repeat authorised while we are at it? No rush on either."
    ),
    onset="Flared three days ago lifting at the depot.",
    severity="Stiff and sore, moving carefully, been here before.",
    history="Same back, every couple of years since my thirties.",
    medications="Naproxen with the stomach cover, when it flares.",
    context="On light duties this week; afternoons are easiest. I look in on my father most evenings.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c11_kin_back_flare",
)

QUARNCLIFFE_B_SPLIT_INTAKE = (
    "Hi. My back has flared again — the usual, lifting at the depot. Could I book a routine appointment "
    "and get the naproxen repeat authorised? No rush on either.\n\n"
    "Separate thing: my father, Ronald Quarncliffe. He paid for a private walk-in clinic yesterday "
    "about his sinuses and they have put him on levofloxacin — he started it last night. Those private "
    "places never seem to send the paperwork on to anyone, so could it be noted on his record here?"
)

QUARNCLIFFE_SPLIT_FACTS = {
    "onset": (
        "The sinuses have been awful ten days; a private clinic gave me tablets for them yesterday. My "
        "call here was after my thyroid results."
    ),
    "severity": (
        "Blocked and headachy across the face, that is all. The heart has not missed a step that I know "
        "of."
    ),
    "medications": (
        "Amiodarone, edoxaban, finasteride — and the private clinic's tablets for the sinuses. The name "
        "is on the box at home, not in my head."
    ),
}

# ── contest 12: Joyce Quarndon — recall split ─────────────────────────────────────────────────────────────
pt_quarndon = _caller(
    "pt_quarndon",
    "Joyce Quarndon",
    78,
    "F",
    chart=(
        "Persistent atrial fibrillation on amiodarone; hypertension.",
        "Cardiology clinic reviews with tracing; blood pressure checked alongside.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, losartan.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor rang me back at ten last night about the burning waterworks and "
        "has put me on levofloxacin — the chemist by the precinct had it ready at half eight this "
        "morning.\n\n"
        "I take amiodarone for the heart, and the clinic upstairs have a standing instruction for the "
        "likes of me: a new antibiotic from that family means a tracing at the clinic the same day it "
        "starts. They were kind about it but firm — same day, their machine, and they close at five.\n\n"
        "I am well enough in myself, just the stinging and a bit washed out. The heart has given me no "
        "bother that I have felt."
    ),
    onset="The waterworks burning since midweek; levofloxacin started this morning.",
    severity=(
        "Stinging and washed out, nothing worse. No flutters felt. The clinic's standing same-day tracing "
        "instruction is the reason for the call."
    ),
    history="Fibrillation on amiodarone these last years; blood pressure behaving on the losartan.",
    medications="Amiodarone, apixaban, losartan — and the out-of-hours levofloxacin from this morning.",
    context="I am home all day; my friend over the road drives and has offered already.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c12_ooh_water_infection",
)

QUARNDON_SPLIT_INTAKE = (
    "Hello. I wonder — could the surgery change my nominated chemist? The one by the precinct has taken "
    "over my old one and the repeats need pointing there now, I am told. It is only the losartan and my "
    "usual bits on the slip. No hurry whatsoever."
)

QUARNDON_RECALL_TEXT = (
    "It is Joyce Quarndon again — the chemist business reminded me of my other errand. The out-of-hours "
    "doctor rang me back at ten last night about the burning waterworks and put me on levofloxacin; the "
    "chemist by the precinct had it ready at half eight and the first dose is down. I feel washed out "
    "but ordinary. Since the prescription came from the out-of-hours people and not from you, I did not "
    "want it falling between two stools."
)

QUARNDON_SPLIT_FACTS = {
    "onset": (
        "The waterworks have burned since midweek; the out-of-hours doctor put me on tablets this "
        "morning. The chemist change was my errand when I rang."
    ),
    "severity": "Stinging and a bit washed out, nothing worse. No flutters felt.",
    "medications": (
        "Amiodarone, apixaban, losartan — and the water-infection tablets from this morning, "
        "levo-something; the new chemist will have it on their screen."
    ),
}

# ── contest 13: Dennis Quarngarth — kin split (wife Pauline) ──────────────────────────────────────────────
pt_quarngarth = _caller(
    "pt_quarngarth",
    "Dennis Quarngarth",
    69,
    "M",
    chart=(
        "Atrial flutter, amiodarone-maintained after two failed rate-control trials.",
        "Cardiology clinic patient; tracing each review. Still drives the community minibus Tuesdays.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, atorvastatin, lansoprazole.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Walk-in centre job, this one: I went up yesterday afternoon with a chest infection — "
        "green as you like, sorry to be vivid — and their doctor started me on levofloxacin.\n\n"
        "I am on amiodarone for the flutter, and your heart clinic's line has always been: that class of "
        "antibiotic and my tablet get a same-day tracing at the clinic, no debate, because together they "
        "can stretch the heart's timing. Their machine has all my old traces to set it against. Same day "
        "means before the clinic shuts at five, they said.\n\n"
        "I am chesty but solid — drove the minibus only Tuesday. Nothing felt from the heart at all."
    ),
    onset="The chest turned nasty over the weekend; levofloxacin from the walk-in centre yesterday.",
    severity=(
        "A ripe cough and tired shoulders, that is my lot. Nothing from the heart. The clinic's no-debate "
        "same-day tracing rule applies, so I am applying it."
    ),
    history="Atrial flutter, two failed tries at other tablets, amiodarone since — the heart clinic's doing.",
    medications="Amiodarone, edoxaban, the statin, the stomach one — plus the walk-in centre's levofloxacin.",
    context="My wife Pauline and I are both in today; the car is outside. Any hour before five.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c13_walkin_chest_infection",
)

QUARNGARTH_SPLIT_INTAKE = (
    "Morning. Small housekeeping: the chemist says my lansoprazole has dropped off the repeat slip and "
    "wants re-authorising. Could that be sorted when somebody has a minute? I have a good week's worth "
    "in the cupboard, so it is not urgent."
)

pt_quarngarth_b = _caller(
    "pt_quarngarth_b",
    "Pauline Quarngarth",
    67,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual bloods due around now.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think my annual thyroid bloods are due — the reminder usually lands about now and I "
        "would rather book the nurse before the diary fills. Any routine morning suits me. That is the "
        "lot; I am very well."
    ),
    onset="Nothing new — the annual bloods are simply due.",
    severity="Perfectly well; this is calendar-keeping.",
    history="The thyroid, steady on the same dose for a decade.",
    medications="Levothyroxine, first thing, one hundred micrograms.",
    context="Retired; mornings free. My husband and I share the one car.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c13_kin_thyroid_bloods",
)

QUARNGARTH_B_SPLIT_INTAKE = (
    "Hello. Could I book my annual thyroid bloods with the nurse — any routine morning?\n\n"
    "And while you have me: my husband Dennis Quarngarth went up to the walk-in centre yesterday "
    "afternoon with a chest infection and they started him on levofloxacin. He rang you this morning "
    "about his stomach tablet's repeat slip, which tells you everything about his priorities — so I am "
    "ringing about the antibiotic, for his record."
)

QUARNGARTH_SPLIT_FACTS = {
    "onset": (
        "The chest turned nasty over the weekend; the walk-in centre started me on tablets yesterday. I "
        "rang about the lansoprazole slip, nothing else."
    ),
    "severity": "A ripe cough and tired shoulders, that is my lot. Nothing from the heart.",
    "medications": (
        "Amiodarone, edoxaban, the statin, the stomach one — and the walk-in centre's chest tablets. "
        "Pauline could tell you the name; I cannot."
    ),
}

# ── contest 14: Pamela Quillcote — recall split ───────────────────────────────────────────────────────────
pt_quillcote = _caller(
    "pt_quillcote",
    "Pamela Quillcote",
    75,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone; mild heart failure, stable on treatment.",
        "Cardiology clinic reviews with tracing; weighs herself weekly as advised, steady.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, furosemide, ramipril.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor at the hub gave me levofloxacin last night for a chest infection "
        "— I have taken the first dose with breakfast and the second is due at teatime.\n\n"
        "I am one of the heart clinic's fibrillation patients, on amiodarone, and their rule was "
        "explained to me with a diagram, no less: that antibiotic can stretch the heart's electrics, and "
        "with my tablet on board they trace me at the clinic the same day it starts. Before five — the "
        "machine goes off with the lights, the nurse jokes.\n\n"
        "In myself: coughing, and I have kept off the stairs more than usual, but my weight is steady and "
        "my ankles are their normal size. Nothing felt from the heart."
    ),
    onset="Chest infection building all week; the hub's levofloxacin started this morning.",
    severity=(
        "A cough and a lazy day of it, nothing more. Weight steady, ankles normal. The clinic's same-day "
        "tracing rule with the new antibiotic is the errand."
    ),
    history="Fibrillation and the mild heart failure, both steady under your heart clinic.",
    medications="Amiodarone, apixaban, furosemide, ramipril — and the hub's levofloxacin since breakfast.",
    context="My niece can run me up between school runs, so late morning or mid-afternoon suits best.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c14_ooh_chest_infection_hf",
)

QUILLCOTE_SPLIT_INTAKE = (
    "Hello. I am after a routine nurse appointment for my blood-pressure check — the clinic likes it done "
    "between my reviews and it has crept past the interval. Whenever there is a gap in the book; there is "
    "nothing the matter with me today."
)

QUILLCOTE_RECALL_TEXT = (
    "Pamela Quillcote here, ringing back after my blood-pressure booking. The out-of-hours hub gave me "
    "levofloxacin last night for a chest infection — first dose with breakfast, the second due at "
    "teatime. I am coughing but steady, weight and ankles ordinary. My sister keeps a copy of my "
    "medicine list in her handbag and says the surgery's copy should say the same as hers, so please "
    "add it."
)

QUILLCOTE_SPLIT_FACTS = {
    "onset": (
        "The chest infection built all week; the hub gave me tablets last night. I rang first about my "
        "blood-pressure check."
    ),
    "severity": (
        "A cough and a lazy day of it. Weight steady, ankles their normal size — nothing else to report."
    ),
    "medications": (
        "Amiodarone, apixaban, furosemide, ramipril — and the hub's chest tablets since breakfast, "
        "levo-something on the label."
    ),
}

# ── contest 15: Maurice Quillgarth — kin split (daughter Janet) ───────────────────────────────────────────
pt_quillgarth = _caller(
    "pt_quillgarth",
    "Maurice Quillgarth",
    82,
    "M",
    chart=(
        "Atrial fibrillation of long standing, on amiodarone; previous stroke, fully recovered.",
        "Cardiology clinic patient; tracing each review. Daughter holds power of attorney for finances only.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, atorvastatin, folic acid.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The night doctor came to the house — the water infection has me up five times a night — "
        "and left a prescription for levofloxacin, which my Janet had filled first thing.\n\n"
        "I am on amiodarone for the fibrillation, have been since before my stroke, and the heart clinic "
        "have a rule they remind me of at every visit: a new antibiotic of the strong sort means a "
        "tracing at their clinic that same day. They keep all my traces there since the stroke, so it is "
        "the one place it can be done properly. Up to five o'clock, when the clinic closes.\n\n"
        "I am tired with the broken nights but otherwise my own man. The heart has not troubled me."
    ),
    onset="Up five times a night for a week; the night doctor's levofloxacin filled this morning.",
    severity=(
        "Tired and sore-eyed from the nights, nothing else. Nothing felt from the heart. The clinic's "
        "same-day tracing rule with the new antibiotic is why I am on the telephone."
    ),
    history="Fibrillation for donkey's years, the stroke five years back and a full recovery, amiodarone throughout.",
    medications="Amiodarone, apixaban, the statin, folic acid — and now the night doctor's levofloxacin.",
    context="Janet lives two streets over and drives me; afternoons are simplest for her.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c15_ooh_home_visit_uti",
)

QUILLGARTH_SPLIT_INTAKE = (
    "Hello. Nothing pressing — the chemist mentioned my folic acid is on its last issue and the repeat "
    "wants signing again. Could that be done in the usual way? Janet collects my medicines on Fridays, "
    "so any time this week is grand."
)

pt_quillgarth_b = _caller(
    "pt_quillgarth_b",
    "Janet Quillgarth",
    55,
    "F",
    chart=(
        "Migraine with aura, longstanding; triptan responsive.",
        "Repeat medication: sumatriptan 50 mg as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I get my sumatriptan repeat authorised? The chemist says the slip has run out of "
        "issues. The migraines are their usual selves — two or three a month, the tablet sorts them — so "
        "it is only the paperwork I need. No appointment necessary unless the doctor wants one."
    ),
    onset="Nothing new — the repeat has run out of issues.",
    severity="The usual migraines, managed fine with the tablet.",
    history="Migraine since my twenties, same pattern for years.",
    medications="Sumatriptan when one lands; nothing daily.",
    context="I work from home and ferry my father about; afternoons suit us both.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c15_kin_triptan_repeat",
)

QUILLGARTH_B_SPLIT_INTAKE = (
    "Hi. Could I get my sumatriptan repeat authorised? The chemist says the slip has run out of issues — "
    "no appointment needed, the migraines are their usual selves.\n\n"
    "The other reason I am ringing is my dad — Maurice Quillgarth. The night doctor came out to him for "
    "a water infection and started levofloxacin; I collected it first thing. I keep his medicines in "
    "the dosette box, so I like his record with you kept square with the box — could the new one be "
    "added?"
)

QUILLGARTH_SPLIT_FACTS = {
    "onset": (
        "Up five times a night for a week; the night doctor left a prescription and Janet had it filled "
        "first thing. My own call was the folic acid slip."
    ),
    "severity": "Tired and sore-eyed from the broken nights, nothing else. The heart has not troubled me.",
    "medications": (
        "Amiodarone, apixaban, the statin, folic acid — and the night doctor's new tablets. Janet keeps "
        "my boxes straight; ask her the name, not me."
    ),
}

# ── contest 16: Audrey Rylstone — recall split ───────────────────────────────────────────────────────────
pt_rylstone = _caller(
    "pt_rylstone",
    "Audrey Rylstone",
    73,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone two years after other agents disagreed with her.",
        "Cardiology clinic reviews with tracing; sings in a choir, keeps active.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, amlodipine.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. A doctor from the 111 service rang me back before midnight about my face — "
        "sinusitis, properly infected, he said — and sent levofloxacin to the all-night chemist. I "
        "started it at breakfast.\n\n"
        "I am on amiodarone for the fibrillation and your heart clinic gave me the talk when I started: "
        "that antibiotic is one of the ones that quarrels with it, and the clinic traces me the same day "
        "any such tablet begins — their machine, before the clinic closes at five o'clock.\n\n"
        "In myself I am just thick-headed with the sinuses. The heart has kept perfect time, and I "
        "sang two services on Sunday to prove it."
    ),
    onset="The face pressure built for a week; the 111 doctor's levofloxacin started at breakfast.",
    severity=(
        "Thick-headed and sore across the cheekbones, that is all. Nothing from the heart. The clinic's "
        "same-day tracing talk covers exactly this, so I am doing as told."
    ),
    history="Fibrillation two years; two other tablets disagreed with me before amiodarone settled things.",
    medications="Amiodarone, edoxaban, amlodipine — and the 111 doctor's levofloxacin since breakfast.",
    context="I am retired and ten minutes away on the bus; any time today works.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c16_111_sinusitis",
)

RYLSTONE_SPLIT_INTAKE = (
    "Good morning. Could you book me a routine hearing check with the nurse — or point me at whoever "
    "does them now? The choir mistress says I am flat on the low notes, which I maintain is slander, but "
    "a check would settle it. Whenever suits the diary; nothing urgent."
)

RYLSTONE_RECALL_TEXT = (
    "It is Audrey Rylstone again — never mind my ears a moment. Tidying the kitchen just now I found "
    "the all-night chemist's bag with the leaflet still stapled to it, which reminded me I never told "
    "you: a doctor from the 111 service put me on levofloxacin last night for infected sinuses, first "
    "dose at breakfast. I am thick-headed but otherwise myself; the heart has kept perfect time. I "
    "would rather it were on my record than only on my kitchen table."
)

RYLSTONE_SPLIT_FACTS = {
    "onset": (
        "The face pressure built for a week; the 111 doctor sent tablets to the all-night chemist. My "
        "call was about a hearing check, of all things."
    ),
    "severity": (
        "Thick-headed and sore across the cheekbones, that is all. The heart has kept perfect time."
    ),
    "medications": (
        "Amiodarone, edoxaban, amlodipine — and the sinus tablets from the 111 doctor, levo-something; "
        "I have the chemist's bag here if you want it letter by letter."
    ),
}

# ── contest 17: Leonard Quornsett — kin split (wife Beryl) ────────────────────────────────────────────────
pt_quornsett = _caller(
    "pt_quornsett",
    "Leonard Quornsett",
    79,
    "M",
    chart=(
        "Persistent atrial fibrillation on amiodarone; chronic kidney disease stage 3, stable.",
        "Cardiology clinic reviews with tracing; renal bloods shared with the same clinic visit.",
        "Repeat medication: amiodarone 200 mg daily, apixaban (renal dose), doxazosin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The out-of-hours doctor saw me at the hub last night about this chest — infection, no "
        "question, he said — and with my kidneys he was careful choosing, but he has started me on "
        "levofloxacin at a lower dose.\n\n"
        "I am on amiodarone under your heart clinic, and their standing orders are stuck to our fridge: "
        "that family of antibiotic means a heart tracing at the clinic the same day it starts. With my "
        "kidneys the clinic said it matters double for me, because things linger in my system. The clinic "
        "traces up to five, when they close.\n\n"
        "In myself: chesty and short of puff on the hill, same as any infection does me, and I am "
        "otherwise steady."
    ),
    onset="The chest went downhill from Sunday; the hub's lower-dose levofloxacin started last night.",
    severity=(
        "Chesty, and the hill takes me longer — no worse than past infections. Nothing felt from the "
        "heart. The fridge list says same-day tracing, doubly with my kidneys."
    ),
    history="Fibrillation on amiodarone; the kidneys sit at their usual level, watched with the same bloods.",
    medications="Amiodarone, the kidney-dose apixaban, doxazosin — and the hub's levofloxacin.",
    context="My wife Beryl rings the lifts; our neighbour drives us both. Today after eleven suits.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c17_ooh_chest_ckd",
)

QUORNSETT_SPLIT_INTAKE = (
    "Morning. My wife says I am to book my over-seventy-fives check — the letter has been on the "
    "mantelpiece a month and she has run out of patience with it. A routine appointment whenever the "
    "nurse has one, please. Nothing else; I am ticking along."
)

pt_quornsett_b = _caller(
    "pt_quornsett_b",
    "Beryl Quornsett",
    77,
    "F",
    chart=(
        "Osteoarthritis of both hands; annual review of function.",
        "Repeat medication: paracetamol 1 g as required, capsaicin cream.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My hand cream — the chilli one, capsaicin — has run out of repeats and the winter has the "
        "knuckles complaining. Could it be re-authorised? And if the doctor wants to see the hands before "
        "signing, a routine appointment is fine by me. No hurry either way."
    ),
    onset="The knuckles always worsen in the cold; the cream has simply run out of repeats.",
    severity="Stiff mornings, workable afternoons. Nothing new.",
    history="Arthritis in the hands for a decade.",
    medications="Paracetamol and the capsaicin cream.",
    context="Home most days; our neighbour drives my husband and me where we need.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c17_kin_capsaicin_repeat",
)

QUORNSETT_B_SPLIT_INTAKE = (
    "Hello. Could my capsaicin hand cream be re-authorised? The winter has the knuckles complaining and "
    "the repeats have run out. Routine appointment first if the doctor prefers.\n\n"
    "The other thing: my husband, Leonard Quornsett. The out-of-hours hub started him on levofloxacin "
    "last night for a chest infection — a careful lower dose, the doctor said, to be kind to his "
    "kidneys. I write everything in the medicines book at home, and I would like your record to say "
    "what my book says."
)

QUORNSETT_SPLIT_FACTS = {
    "onset": (
        "The chest went downhill from Sunday; the hub doctor started me on a careful low dose of "
        "something for it. I rang about my over-seventy-fives check."
    ),
    "severity": (
        "Chesty, and the hill takes me longer — no worse than past infections. Nothing felt from the "
        "heart."
    ),
    "medications": (
        "Amiodarone, the kidney-dose apixaban, doxazosin — and the hub's new tablets. Beryl writes them "
        "in the medicines book; the name escapes me."
    ),
}

# ── contest 18: Hilda Quornridge — recall split ───────────────────────────────────────────────────────────
pt_quornridge = _caller(
    "pt_quornridge",
    "Hilda Quornridge",
    84,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone; lives alone with a morning carer call.",
        "Cardiology clinic reviews with tracing; transport usually her nephew.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, bumetanide.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor came to me in the night for the waterworks — a bad infection, he "
        "said, from the sample — and my carer fetched the levofloxacin at eight. First tablet is down.\n\n"
        "I take amiodarone for the heart, and the clinic here have told me and my nephew both: if a "
        "doctor ever starts an antibiotic of that strength, I am to be traced at the clinic before that "
        "day ends. My nephew wrote it inside the kitchen cupboard door. The clinic closes at five, so "
        "before five.\n\n"
        "I am not ill in myself beyond the stinging and feeling my age. The heart is quiet as far as I "
        "can tell."
    ),
    onset="The waterworks turned nasty overnight; the levofloxacin started at eight this morning.",
    severity=(
        "Stinging and weary, and that is the sum of it. The heart quiet. The cupboard-door rule says "
        "same-day tracing at the clinic, so I am ringing."
    ),
    history="Fibrillation on amiodarone for years; the clinic and my nephew keep me right between them.",
    medications="Amiodarone, edoxaban, the water tablet — and the levofloxacin since eight.",
    context="My carer comes mornings; my nephew can fetch me any time after his lunch shift.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c18_ooh_uti_carer",
)

QUORNRIDGE_SPLIT_INTAKE = (
    "Hello. It is only the district nurse I am asking after — my leg dressing is due its change tomorrow "
    "and nobody has confirmed the visit. Could somebody check I am on tomorrow's list? That is all, "
    "thank you kindly."
)

QUORNRIDGE_RECALL_TEXT = (
    "It is Hilda Quornridge again, dear. My carer was straightening the kitchen before she left and "
    "said the new box on the side ought to be rung in to you. The out-of-hours doctor came to me in the "
    "night for the waterworks and started me on levofloxacin — my carer fetched it at eight and the "
    "first tablet is down. I am stinging and weary and no worse than that. There, it is on the record "
    "and the kitchen is tidy."
)

QUORNRIDGE_SPLIT_FACTS = {
    "onset": (
        "The waterworks turned nasty overnight; the doctor who came out left tablets and my carer "
        "fetched them at eight. The district nurse list was my question."
    ),
    "severity": "Stinging and weary, and that is the sum of it. The heart is quiet as far as I can tell.",
    "medications": (
        "Amiodarone, edoxaban, the water tablet — and the new ones from eight o'clock this morning, "
        "levo-something; my nephew wrote it down somewhere."
    ),
}

# ── contest 19: Raymond Quexby — kin split (wife Carol) ───────────────────────────────────────────────────
pt_quexby = _caller(
    "pt_quexby",
    "Raymond Quexby",
    66,
    "M",
    chart=(
        "Atrial fibrillation on amiodarone eighteen months; works part-time as a school caretaker.",
        "Cardiology clinic reviews with tracing; youngest of the clinic's amiodarone cohort, told so often.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, atorvastatin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I used one of those online private GP services last night — the chest has been rattling "
        "all week and I could not lose a day's work queueing — and the doctor on the video prescribed "
        "levofloxacin. Collected it before my shift this morning.\n\n"
        "Here is the thing: I am on amiodarone for the fibrillation, and the heart clinic gave me a "
        "wallet card when I started — antibiotics in the quinolone family need a same-day tracing at the "
        "clinic, it says, with a little lightning bolt drawn next to it. Levofloxacin is the first one "
        "printed on the card's list. Clinic traces till it closes at five.\n\n"
        "I feel rough with the chest and nothing else. I can get released from the school whenever suits."
    ),
    onset="The chest rattling all week; the video doctor's levofloxacin collected before this morning's shift.",
    severity=(
        "Rough with the cough, working through it. Nothing from the heart. The wallet card says same-day "
        "tracing with this exact antibiotic, so I am ringing as instructed."
    ),
    history="Fibrillation eighteen months; the clinic tease me for being their youngest amiodarone case.",
    medications="Amiodarone, apixaban, the statin — and the video doctor's levofloxacin.",
    context="At the school till three but they release me for medical things; my wife Carol drives.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c19_private_video_chest",
)

QUEXBY_SPLIT_INTAKE = (
    "Morning. Quick admin one: work want a copy of my last fit note for their file — the one from the "
    "shoulder strain back in the winter. Could a copy be left at reception for me to collect after "
    "three? No new problems; the shoulder is long mended."
)

pt_quexby_b = _caller(
    "pt_quexby_b",
    "Carol Quexby",
    63,
    "F",
    chart=(
        "Hypercholesterolaemia on a statin; annual bloods each spring round.",
        "Repeat medication: simvastatin 40 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Two dull things: my simvastatin repeat needs re-authorising, the chemist says, and I "
        "think my annual cholesterol bloods are due around now — could I book the nurse for those at the "
        "same time? Routine, whenever the book has room."
    ),
    onset="Nothing new; the repeat and the annual bloods have both come round.",
    severity="Perfectly well.",
    history="The cholesterol, managed on the same tablet for years.",
    medications="Simvastatin at night.",
    context="Part-time at the library; Tuesdays and Thursdays off. I drive my husband where he needs.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c19_kin_statin_repeat",
)

QUEXBY_B_SPLIT_INTAKE = (
    "Hello. Could my simvastatin repeat be re-authorised, and the nurse booked for my annual cholesterol "
    "bloods — routine, whenever there is room?\n\n"
    "And I promised I would pass this on: my husband Raymond Quexby saw a private video GP last night "
    "about his rattly chest and was prescribed levofloxacin — he collected it before his shift at the "
    "school. Those video people post nothing on to anyone, so I said I would tell the surgery myself "
    "and have it on his record."
)

QUEXBY_SPLIT_FACTS = {
    "onset": (
        "The chest has rattled all week; a video doctor sorted a prescription last night and I "
        "collected it before my shift. I rang you about a fit-note copy."
    ),
    "severity": "Rough with the cough, working through it. Nothing from the heart.",
    "medications": (
        "Amiodarone, apixaban, the statin — and the video doctor's chest tablets. The box is at home "
        "and the name will not come to me while I am on the school clock."
    ),
}

# ── contest 20: Dorothy Quarnwell — recall split ──────────────────────────────────────────────────────────
pt_quarnwell = _caller(
    "pt_quarnwell",
    "Dorothy Quarnwell",
    77,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone; glaucoma drops both eyes.",
        "Cardiology clinic reviews with tracing; last review in the winter, steady.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, latanoprost drops.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor at the hub started me on levofloxacin last night — a chest "
        "infection that would not shift on its own — and I have had the first dose with my toast.\n\n"
        "I am on amiodarone for the heart rhythm, and the heart clinic have schooled me well: that "
        "antibiotic is on the short list that quarrels with amiodarone, and the clinic does a tracing the "
        "same day one begins — at the clinic, on their machine, before they close at five.\n\n"
        "In myself I am coughing and slow but perfectly sensible. My heart did flutter for a moment while "
        "I queued at the chemist, and it settled before I reached the counter — I mention it only to be "
        "thorough."
    ),
    onset="The chest would not shift for a week; the hub's levofloxacin started this morning.",
    severity=(
        "Coughing and slow, and one settled flutter in the chemist's queue. The clinic's same-day tracing "
        "rule for this antibiotic is the point of me ringing."
    ),
    history="Fibrillation on amiodarone these several years; the eyes have their drops and behave.",
    medications="Amiodarone, apixaban, the eye drops — and the hub's levofloxacin since breakfast.",
    context="My neighbour drives me on Thursdays but will make an exception today, she says. Any hour.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c20_ooh_chest_infection",
)

QUARNWELL_SPLIT_INTAKE = (
    "Hello. My eye drops, please — the latanoprost. The chemist says the repeat has expired and the "
    "bottle in the fridge is my last. Could it be signed off this week? The eyes themselves are fine; "
    "the pressure clinic saw me in the autumn and was happy."
)

QUARNWELL_RECALL_TEXT = (
    "It is Dorothy Quarnwell again — one more for the same list, if you are still there. As well as the "
    "eye drops I should have said: the out-of-hours hub started me on levofloxacin last night for my "
    "chest, first dose with my toast. My heart fluttered for a moment in the chemist's queue this "
    "morning and settled before I reached the counter; the rest of me is just coughing and slow. Now "
    "the list is complete."
)

QUARNWELL_SPLIT_FACTS = {
    "onset": (
        "The chest would not shift for a week; the hub started me on tablets last night. The eye drops "
        "were my errand when I rang."
    ),
    "severity": (
        "Coughing and slow, and one settled flutter in the chemist's queue this morning — gone before I "
        "reached the counter."
    ),
    "medications": (
        "Amiodarone, apixaban, the eye drops — and the hub's chest tablets since breakfast, "
        "levo-something on the chemist's sticker."
    ),
}

# ── contest 21: Eric Quorngill — kin split (daughter Fiona) ───────────────────────────────────────────────
pt_quorngill = _caller(
    "pt_quorngill",
    "Eric Quorngill",
    72,
    "M",
    chart=(
        "Atrial fibrillation on amiodarone; type of man to walk the dog five miles daily.",
        "Cardiology clinic reviews with tracing; bloods each half-year, in range.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban, tamsulosin.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Walk-in centre yesterday evening for a water infection — I shall spare you the "
        "details — and their doctor has started me on levofloxacin. First one taken on the dog walk this "
        "morning.\n\n"
        "I am on amiodarone under your heart clinic, and their instruction has been the same for years: "
        "start an antibiotic from that family and present myself at the clinic for a tracing the same "
        "day, because the pair of them can pull the heart's timing about. The clinic runs the machine "
        "till five, when it closes.\n\n"
        "I am absolutely fine in myself — did my full five miles this morning, dog disgusted at the pace "
        "as usual. It is the rule that brings me, not a symptom."
    ),
    onset="The waterworks since the weekend; the walk-in centre's levofloxacin started this morning.",
    severity=(
        "Nothing to report — the full dog walk done this morning. It is the clinic's same-day tracing "
        "instruction for the antibiotic, plain and simple."
    ),
    history="Fibrillation on amiodarone; otherwise fit as a flea and intent on staying so.",
    medications="Amiodarone, edoxaban, tamsulosin — and the walk-in centre's levofloxacin.",
    context="Retired; I can walk up at any hour you name, today included. My daughter Fiona drives if it rains.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c21_walkin_uti",
)

QUORNGILL_SPLIT_INTAKE = (
    "Morning. A nothing of a call: the surgery's text reminder says I am due my half-year bloods for the "
    "heart clinic, and the link to book has expired. Could somebody put me in for a routine blood "
    "appointment — any morning, I walk up? That is the whole of it."
)

pt_quorngill_b = _caller(
    "pt_quorngill_b",
    "Fiona Quorngill",
    47,
    "F",
    chart=(
        "Hypertension in pregnancy history; annual blood-pressure check advised.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I book my annual blood-pressure check with the nurse? It is the one they advised after "
        "my second pregnancy — I get a reminder each spring and then forget by summer, so I am striking "
        "while the iron is warm. Any routine slot suits; I am flexible around school hours."
    ),
    onset="Nothing new — the annual check has come round.",
    severity="Well; it is a check, not a complaint.",
    history="The blood-pressure business in my second pregnancy; fine every year since.",
    medications="None at all.",
    context="School hours are mine; I drive my father in bad weather.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_c21_kin_bp_check",
)

QUORNGILL_B_SPLIT_INTAKE = (
    "Hi. Could I book my annual blood-pressure check with the nurse — any routine slot around school "
    "hours?\n\n"
    "Also, because he will not say it himself: my dad, Eric Quorngill, was started on levofloxacin by "
    "the walk-in centre yesterday evening for a water infection. He did his full five miles with the "
    "dog this morning, so you can imagine how much fuss he thinks it deserves — but I would like it on "
    "his record all the same."
)

QUORNGILL_SPLIT_FACTS = {
    "onset": (
        "The waterworks since the weekend; the walk-in centre gave me a course yesterday evening. I "
        "rang about my half-year bloods, that is all."
    ),
    "severity": "Nothing to report — the full five miles with the dog done this morning at my usual pace.",
    "medications": (
        "Amiodarone, edoxaban, tamsulosin — and the walk-in centre's course for the waterworks. Fiona "
        "would know the name; I take what I am given."
    ),
}

# ── contest 22: Nancy Quexcote — recall split ─────────────────────────────────────────────────────────────
pt_quexcote = _caller(
    "pt_quexcote",
    "Nancy Quexcote",
    81,
    "F",
    chart=(
        "Atrial fibrillation on amiodarone; hearing aids both ears; husband recently in respite care.",
        "Cardiology clinic reviews with tracing; last review in the winter round, satisfactory.",
        "Repeat medication: amiodarone 200 mg daily, apixaban, sertraline 50 mg.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor came to the house last night — my chest, a proper infection he "
        "said after listening — and he started me on levofloxacin there and then from his bag, with a "
        "prescription for the rest.\n\n"
        "I am on amiodarone for the heart. The clinic have a rule I have heard so many times I could sing "
        "it: an antibiotic of that strength means a tracing at the clinic the same day it starts, on "
        "their machine, before the clinic closes at five. With Bill in respite I have no one to remind "
        "me, so I am ringing while it is fresh.\n\n"
        "In myself I am chesty and a little teary with everything, but managing. The heart has not made "
        "itself felt."
    ),
    onset="The chest came on over three days; the doctor's levofloxacin started from his bag last night.",
    severity=(
        "Chesty, tired, a little teary with the house so quiet — nothing beyond that. The clinic's "
        "same-day tracing rule is what I am ringing to keep."
    ),
    history="Fibrillation on amiodarone for years; the clinic knows me and my Bill both.",
    medications="Amiodarone, apixaban, the sertraline — and the levofloxacin begun last night.",
    context="I am home alone with Bill in respite; the volunteer car service can fetch me with an hour's notice.",
    gold=board_gold(CARDIOLOGY),
    source="authored:amiodarone_qt_c22_ooh_home_visit_chest",
)

QUEXCOTE_SPLIT_INTAKE = (
    "Hello. I am ringing to ask whether my husband's respite discharge letter has reached his file yet — "
    "the home said they would copy the surgery in, and I like to know the paperwork is where it should "
    "be. Nothing is wrong; I am only keeping the threads tidy."
)

QUEXCOTE_RECALL_TEXT = (
    "It is Nancy Quexcote again — I rang about Bill's paperwork and walked away from the telephone "
    "having forgotten my own errand entirely. The out-of-hours doctor came to the house last night for "
    "my chest and started me on levofloxacin there and then from his bag, with a prescription for the "
    "rest. I am chesty and a little teary with the house so quiet, but managing. With Bill in respite "
    "there is nobody at home to remember these things, so the record had better do it."
)

QUEXCOTE_SPLIT_FACTS = {
    "onset": (
        "The chest came on over three days; the doctor who came out started me on tablets from his bag "
        "last night. Bill's paperwork was my first call."
    ),
    "severity": "Chesty, tired, a little teary with the house so quiet — nothing beyond that.",
    "medications": (
        "Amiodarone, apixaban, the sertraline — and the chest tablets begun last night, levo-something; "
        "the rest of the course is coming from the chemist."
    ),
}

# ══ THE 22 HOLDERS ════════════════════════════════════════════════════════════════════════════════════════
# Holders never call. Each intake is what they say if a desk RINGS them (`rebooking._rebookee`'s
# convention): an ordinary, human reason to want the slot they hold — never obstruction, never consent to
# being moved (a card must not contradict its world).

pt_ramsdijk = _caller(
    "pt_ramsdijk",
    "Peter Ramsdijk",
    69,
    "M",
    chart=(
        "Pacemaker in situ three years; annual practice cardiology check alongside the device clinic.",
        "Repeat medication: bisoprolol 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, that is me — my yearly heart check this afternoon. My neighbour has arranged his whole day "
        "around driving me there and back, so I am glad it is finally come round; it took some getting."
    ),
    onset="Nothing new — the yearly check.",
    severity="I am well. The appointment is the routine one.",
    history="The pacemaker three years ago, checks ever since.",
    medications="The bisoprolol each morning.",
    context="My neighbour drives me; he has kept this afternoon free specially.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h01_pacemaker_annual",
)

pt_quatford = _caller(
    "pt_quatford",
    "Gwen Quatford",
    72,
    "F",
    chart=(
        "Mitral regurgitation, mild; echo surveillance with clinic review.",
        "Repeat medication: ramipril 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, yes — my valve follow-up this afternoon. My daughter has taken the afternoon off work to "
        "bring me, which took some arranging with her rota, so today suits us very well indeed."
    ),
    onset="Nothing new; it is the follow-up after my scan.",
    severity="I feel fine — the appointment is to go over the echo.",
    history="The leaky valve, watched for a few years now.",
    medications="Ramipril, one a day.",
    context="My daughter booked leave for this afternoon's appointment.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h02_echo_followup",
)

pt_ramsfold = _caller(
    "pt_ramsfold",
    "Arthur Ramsfold",
    80,
    "M",
    chart=(
        "Chronic heart failure, stable; annual cardiology review with bloods.",
        "Repeat medication: furosemide, ramipril, bisoprolol.",
        "No known drug allergies.",
    ),
    intake=(
        "That is right, my heart-failure review this afternoon. The hospital-transport volunteers have "
        "me down for it, there and back — you have to give them notice, you know — so I am all set."
    ),
    onset="Nothing new; the annual review.",
    severity="Steady as she goes. It is the routine look-over.",
    history="The heart failure, stable a good while on the tablets.",
    medications="The water tablet, ramipril and bisoprolol.",
    context="The community car is booked for this afternoon, both directions.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h03_hf_annual",
)

pt_ramsgill = _caller(
    "pt_ramsgill",
    "Olive Ramsgill",
    75,
    "F",
    chart=(
        "Hypertension with a past episode of fast atrial fibrillation, resolved; rhythm review yearly.",
        "Repeat medication: amlodipine 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes — my blood pressure and rhythm review, this afternoon. My grandson is between college terms "
        "and has promised the lift; next week he is away, so the timing is a small miracle."
    ),
    onset="Nothing new; the yearly review.",
    severity="Quite well. The visit is routine.",
    history="The blood pressure, and that one fast-heart episode a few years back.",
    medications="Amlodipine each morning.",
    context="My grandson drives me this week only, before his term starts.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h04_bp_rhythm_review",
)

pt_ramslund = _caller(
    "pt_ramslund",
    "Frank Ramslund",
    78,
    "M",
    chart=(
        "Stable angina, well controlled; annual cardiology review.",
        "Repeat medication: isosorbide mononitrate, atorvastatin, GTN spray as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Aye, my angina review this afternoon. My son is over from his rig fortnight and taking me in — "
        "he flies back Friday, so this afternoon is the one that works for the pair of us."
    ),
    onset="Nothing new; the annual review of the angina.",
    severity="The angina behaves itself if I do. Routine visit.",
    history="Angina for years, steady on the tablets.",
    medications="The nitrate, the statin, and the spray in my pocket.",
    context="My son is home from the rigs and driving me; he leaves Friday.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h05_angina_annual",
)

pt_quinbury = _caller(
    "pt_quinbury",
    "Betty Quinbury",
    83,
    "F",
    chart=(
        "Heart-failure with preserved function; cardiology medication review due.",
        "Repeat medication: furosemide, candesartan.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, dear, my medicines review at the heart clinic this afternoon. My carer has swapped her "
        "rounds to sit with my husband while I am out — that took two telephone calls to arrange, so I do "
        "hope all is in order."
    ),
    onset="Nothing new; the medicines review has come round.",
    severity="I am as I always am — it is the routine review.",
    history="The heart failure, the preserved sort, they tell me.",
    medications="The water tablet and the candesartan.",
    context="My carer has rearranged her rounds so I can attend this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h06_med_review",
)

pt_ramsridge = _caller(
    "pt_ramsridge",
    "Clifford Ramsridge",
    74,
    "M",
    chart=(
        "Aortic stenosis, moderate; surveillance review with the practice cardiology clinic.",
        "Repeat medication: atorvastatin 40 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "That is me — the valve surveillance this afternoon. I have a taxi booked and the fare agreed; "
        "at my age you plan these outings like a military campaign, and this one is planned."
    ),
    onset="Nothing new; the surveillance visit.",
    severity="No change in me. Routine surveillance.",
    history="The narrowing valve, watched twice a year.",
    medications="The statin at night.",
    context="Taxi booked both ways for this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h07_valve_surveillance",
)

pt_ramsroyd = _caller(
    "pt_ramsroyd",
    "Muriel Ramsroyd",
    79,
    "F",
    chart=(
        "Atrial flutter, ablated two years ago; annual post-ablation review.",
        "Repeat medication: bisoprolol 1.25 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — yes, my after-the-ablation check this afternoon. My sister is staying with me just this "
        "week and insists on coming along; she has planned tea in town around it, bless her."
    ),
    onset="Nothing new; the annual check after my ablation.",
    severity="I have been very well since the procedure. Routine check.",
    history="The flutter, fixed with the ablation two years back.",
    medications="A small bisoprolol each day.",
    context="My sister is staying this week and coming with me.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h08_post_ablation",
)

pt_ramssett = _caller(
    "pt_ramssett",
    "Donald Ramssett",
    71,
    "M",
    chart=(
        "Palpitation episodes, benign ectopy on prior tracing; follow-up review arranged.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my follow-up about the palpitations this afternoon — the harmless extra-beat sort, the "
        "doctor thought, but she wanted one more look. I have arranged cover at the charity shop "
        "specially; we are short-staffed as it is."
    ),
    onset="Nothing new; the arranged follow-up.",
    severity="The flutters are rarer than ever. Routine follow-up.",
    history="The extra beats, checked once already and thought harmless.",
    medications="Nothing at all.",
    context="Cover arranged at the charity shop for this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h09_palpitation_followup",
)

pt_ramsthwaite = _caller(
    "pt_ramsthwaite",
    "Kathleen Ramsthwaite",
    76,
    "F",
    chart=(
        "Heart failure, stable on treatment; annual review with bloods.",
        "Repeat medication: furosemide, bisoprolol, dapagliflozin.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes — my yearly heart-failure review this afternoon. My neighbour does my lifts and she has "
        "moved her own hair appointment to manage it, so we are rather invested in the time now."
    ),
    onset="Nothing new; the yearly review.",
    severity="Steady. It is the routine one with the bloods.",
    history="The heart failure, stable a long while.",
    medications="The water tablet, bisoprolol and the newer one, dapagliflozin.",
    context="My neighbour rearranged her day to drive me this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h10_hf_annual",
)

pt_ramswell = _caller(
    "pt_ramswell",
    "Sidney Ramswell",
    82,
    "M",
    chart=(
        "Pacemaker in situ; annual practice cardiology check.",
        "Repeat medication: ramipril 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is me, the pacemaker check this afternoon. My daughter has her day off today and is "
        "bringing me — her days off move about with the hospital rota, so this landing together was a "
        "stroke of luck."
    ),
    onset="Nothing new; the annual check.",
    severity="I am very well on it. Routine check.",
    history="The pacemaker, going strong.",
    medications="Ramipril in the morning.",
    context="My daughter's day off is today and she is driving me.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h11_pacemaker_annual",
)

pt_rookgarth = _caller(
    "pt_rookgarth",
    "Marjorie Rookgarth",
    77,
    "F",
    chart=(
        "Aortic regurgitation, mild; echo follow-up with clinic review.",
        "Repeat medication: losartan 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, yes — my echo follow-up this afternoon. My husband is driving and we have tied it to his "
        "hospital eye appointment across town at half past four, so our whole day is threaded on this "
        "pin."
    ),
    onset="Nothing new; the follow-up on the scan.",
    severity="I am well; the appointment reviews the echo.",
    history="The leaky valve, mild, watched yearly.",
    medications="Losartan each morning.",
    context="Tied to my husband's own appointment across town later this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h12_echo_followup",
)

pt_rookcliffe = _caller(
    "pt_rookcliffe",
    "Wilfred Rookcliffe",
    84,
    "M",
    chart=(
        "Ischaemic heart disease, stable; cardiology medication review due.",
        "Repeat medication: aspirin, atorvastatin, bisoprolol, isosorbide mononitrate.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes — my heart medicines review this afternoon. The sheltered housing minibus runs to the "
        "surgery Thursdays only, and the warden has me on today's list, so it has all come together for "
        "once."
    ),
    onset="Nothing new; the medicines review.",
    severity="As well as I ever am. Routine review.",
    history="The heart trouble years back, steady since.",
    medications="Aspirin, the statin, bisoprolol and the nitrate.",
    context="My neighbour kept her half-day for it; she works the rest of the week.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h13_med_review",
)

pt_rooklund = _caller(
    "pt_rooklund",
    "Rita Rooklund",
    70,
    "F",
    chart=(
        "Hypertension with left ventricular thickening on echo; rhythm and pressure review yearly.",
        "Repeat medication: indapamide, candesartan.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, that is my review this afternoon — pressure and rhythm. I work the till at the garden "
        "centre and swapped my shift with the Saturday girl for this; I owe her a favour now, so I am "
        "keen it goes ahead."
    ),
    onset="Nothing new; the yearly review.",
    severity="Fit and well; the visit is routine.",
    history="Blood pressure, and the thickened heart wall they keep an eye on.",
    medications="The indapamide and candesartan.",
    context="Shift swapped at the garden centre for this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h14_bp_rhythm_review",
)

pt_rushmead = _caller(
    "pt_rushmead",
    "Cyril Rushmead",
    81,
    "M",
    chart=(
        "Stable angina; annual cardiology review.",
        "Repeat medication: bisoprolol, GTN spray as required, atorvastatin.",
        "No known drug allergies.",
    ),
    intake=(
        "Aye, the angina review this afternoon. My son-in-law is on lates this week so he can run me in "
        "before his shift — next week he is on earlies and I would be stuck. Today is the day, as far as "
        "this house is concerned."
    ),
    onset="Nothing new; the annual angina review.",
    severity="The angina is quiet on the tablets. Routine.",
    history="Angina a good ten years, steady.",
    medications="Bisoprolol, the spray for emergencies, and the statin.",
    context="My son-in-law's late shift this week makes the lift possible today.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h15_angina_annual",
)

pt_rushgarth = _caller(
    "pt_rushgarth",
    "Phyllis Rushgarth",
    78,
    "F",
    chart=(
        "Mitral valve repair four years ago; surveillance review yearly.",
        "Repeat medication: bisoprolol 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — my valve check this afternoon, yes. My friend from church drives me to these and she has "
        "already set off her end, more or less; we make an outing of it with lunch first."
    ),
    onset="Nothing new; the yearly valve check.",
    severity="I have been splendid since the repair. Routine check.",
    history="The valve repair four years ago, checked yearly.",
    medications="The small bisoprolol.",
    context="My church friend drives; we have lunch planned before it.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h16_valve_surveillance",
)

pt_rydebrook = _caller(
    "pt_rydebrook",
    "Malcolm Rydebrook",
    73,
    "M",
    chart=(
        "Coronary stent last year; structured follow-up review at the practice cardiology clinic.",
        "Repeat medication: aspirin, ticagrelor, atorvastatin, ramipril.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes — my after-the-stent review this afternoon. I have booked the day off my delivery round for "
        "it, unpaid I might add, so I am rather counting on the appointment happening."
    ),
    onset="Nothing new; the planned follow-up.",
    severity="I feel grand since the stent. Routine follow-up.",
    history="The stent last year after the scare; good as new since.",
    medications="Aspirin, ticagrelor, the statin and ramipril.",
    context="An unpaid day booked off the delivery round for this.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h17_post_stent",
)

pt_quethiock = _caller(
    "pt_quethiock",
    "Edna Quethiock",
    85,
    "F",
    chart=(
        "Chronic heart failure; annual review with bloods, housebound in bad weather.",
        "Repeat medication: furosemide, bisoprolol, spironolactone.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my heart-failure review this afternoon. My granddaughter is visiting from university — she "
        "goes back Sunday — and she is taking me in as her good deed. I do like her to see me managing."
    ),
    onset="Nothing new; the annual review.",
    severity="Steady, taking the winter carefully. Routine review.",
    history="The heart failure, watched yearly.",
    medications="The water tablet, bisoprolol and spironolactone.",
    context="My granddaughter is home until Sunday and driving me.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h18_hf_annual",
)

pt_rokeby = _caller(
    "pt_rokeby",
    "Trevor Rokeby",
    68,
    "M",
    chart=(
        "Palpitations under investigation; monitor worn, results review booked.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "That is me — going over my heart-monitor results this afternoon. I drive a taxi and swapped my "
        "airport runs with another driver for this slot; his goodwill does not stretch to a second swap, "
        "I can tell you."
    ),
    onset="Nothing new; the results appointment.",
    severity="The odd flutter, nothing since the monitor came off. Routine results.",
    history="The palpitations, monitored last month.",
    medications="Nothing regular.",
    context="Taxi shifts swapped once already to make this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h19_monitor_results",
)

pt_rothgarth = _caller(
    "pt_rothgarth",
    "Ivy Rothgarth",
    80,
    "F",
    chart=(
        "Ischaemic heart disease; cardiology medication review due, carer-supported.",
        "Repeat medication: aspirin, bisoprolol, isosorbide mononitrate, atorvastatin.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, yes — my heart medicines review this afternoon. The agency have put my carer's visit back "
        "specially so she can bring me, and changing the agency's rota is not a thing you do twice in a "
        "month, believe me."
    ),
    onset="Nothing new; the medicines review.",
    severity="As usual, no better and no worse. Routine review.",
    history="The heart disease, stable on the tablets a long time.",
    medications="Aspirin, bisoprolol, the nitrate, the statin.",
    context="The carer's visit was moved specially so she can bring me this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h20_med_review",
)

pt_rothmead = _caller(
    "pt_rothmead",
    "Roy Rothmead",
    75,
    "M",
    chart=(
        "Dilated aortic root, mild; echo surveillance with review.",
        "Repeat medication: losartan 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes — my echo review this afternoon. My wife has her own hospital appointment across town at "
        "four, so we have built the day as a relay: mine first, hers after. Move one leg and the whole "
        "thing falls over."
    ),
    onset="Nothing new; the surveillance review.",
    severity="I feel fine; the scan is the point, not symptoms.",
    history="The widened artery root, watched on scans.",
    medications="Losartan daily.",
    context="A two-appointment relay with my wife's hospital slot at four.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h21_echo_surveillance",
)

pt_rixholm = _caller(
    "pt_rixholm",
    "Sheila Rixholm",
    74,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled without amiodarone; annual rhythm review.",
        "Repeat medication: bisoprolol 5 mg, edoxaban.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my yearly rhythm review this afternoon. My friend from the bowls club drives me and has "
        "given up her league practice for it — I shall be hearing about that sacrifice until the summer, "
        "so the appointment had better happen."
    ),
    onset="Nothing new; the yearly review.",
    severity="Quite well; the fibrillation is the steady sort. Routine.",
    history="The fibrillation, rate-controlled, reviewed yearly.",
    medications="Bisoprolol and edoxaban.",
    context="My bowls-club friend gave up league practice to drive me this afternoon.",
    gold=_holder_gold(),
    source="authored:amiodarone_qt_h22_rhythm_annual",
)

# ══ THE 3 DECOYS ══════════════════════════════════════════════════════════════════════════════════════════
# Sound urgent, correctly resolved WITHOUT a bump (§6). Radbrook and Quidenham defuse inside their own single
# call on both twins; Rushwell is the split-defused one — his call alone reads exactly like a claimant, and
# his daughter's call cancels it.

pt_radbrook = _caller(
    "pt_radbrook",
    "Norman Radbrook",
    76,
    "M",
    chart=(
        "Atrial fibrillation on amiodarone four years; stable.",
        "Cardiology clinic reviews with tracing; last in the winter, satisfactory.",
        "Repeat medication: amiodarone 200 mg daily, apixaban.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I want to do the right thing here, so bear with me. The emergency dentist lanced a "
        "tooth abscess for me yesterday and started me on an antibiotic — and I am on amiodarone, and "
        "the heart clinic have that rule about antibiotics and same-day tracings, so my first thought "
        "was to come straight in.\n\n"
        "But I asked the dentist about exactly that, and she looked it up in her book there and then: it "
        "is amoxicillin she has given me, and amoxicillin is not one of the ones on the heart clinic's "
        "list — not a quinolone, nothing that quarrels with amiodarone. Let the surgery know for the "
        "record, she said, and no more than that.\n\n"
        "So that is me doing so. If the record wants a routine note or a routine appointment sometime, "
        "grand; I feel perfectly well."
    ),
    onset="The tooth flared at the weekend; the dentist sorted it yesterday and started amoxicillin.",
    severity=(
        "The jaw is easing already and I am otherwise well. The dentist checked her book: amoxicillin is "
        "not on the heart clinic's watch-list, so there is no same-day anything needed — it is a note for "
        "the record."
    ),
    history="Fibrillation on amiodarone four years, steady; the teeth are their own saga.",
    medications="Amiodarone, apixaban — and the dentist's amoxicillin since yesterday.",
    context="Retired, five minutes away. No lift needed; I walk.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_d01_amoxicillin_defused",
)

pt_quidenham = _caller(
    "pt_quidenham",
    "Tracy Quidenham",
    34,
    "F",
    chart=(
        "No significant past medical history.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. I want to be sensible about this rather than dramatic. Twice this week my heart has gone "
        "fluttery in the small hours — properly racing for a minute or two, then fine.\n\n"
        "Before you reach for anything: I am three weeks into night shifts at the distribution centre "
        "and I have been living on those big energy-drink cans, two or three a night, which I only "
        "joined up in my head yesterday. Since I swapped to decaf tea for two nights there has been "
        "nothing at all. The pharmacist I spoke to said the same — cut the cans, and see the doctor "
        "routinely if it ever happens off the caffeine.\n\n"
        "So could I book a routine appointment sometime, just to have the once-over? No rush from me."
    ),
    onset="Two fluttery spells in the small hours this week, none since dropping the energy drinks.",
    severity=(
        "A minute or two of racing, then completely fine — and nothing at all in two nights since I "
        "stopped the cans. The pharmacist said routine review, not urgent."
    ),
    history="Nothing on my record; I am the healthy one of the family, allegedly.",
    medications="None — unless energy drinks count, which apparently they do.",
    context="Night shifts at the distribution centre; afternoons are my mornings, so afternoon suits.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_d02_caffeine_defused",
)

pt_rushwell = _caller(
    "pt_rushwell",
    "Walter Rushwell",
    78,
    "M",
    chart=(
        "Atrial fibrillation on amiodarone five years; stable.",
        "Cardiology clinic reviews with tracing; anxious in health matters, notes the clinic kindly.",
        "Repeat medication: amiodarone 200 mg daily, edoxaban.",
        "Cardiology clinic protocol on file: a same-day rhythm tracing at the clinic whenever a "
        "quinolone or other QT-prolonging antibiotic starts alongside amiodarone, on the clinic's own "
        "machine against the stored tracings; tracings run until clinic close at 17:00.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Now — I do not want a fuss, but my daughter says tell you everything, so here is "
        "everything. The out-of-hours doctor gave me a prescription for levofloxacin last night for a "
        "water infection. I am on amiodarone, and I know the heart clinic's rule about that antibiotic "
        "and a same-day tracing — I have the leaflet.\n\n"
        "But here is the other half: when my daughter took the prescription in, the chemist caught it "
        "straight away — flagged the amiodarone on his screen, rang the out-of-hours doctor back, and "
        "they changed it to doxycycline on the spot. I never had so much as one levofloxacin tablet in "
        "the house. It is the doxycycline I started this morning, and the chemist said that one sits "
        "perfectly well with my tablet.\n\n"
        "So I believe I need nothing today — but I wanted it all on the record, in case."
    ),
    onset="The water infection since midweek; doxycycline — not the levofloxacin — started this morning.",
    severity=(
        "I am comfortable enough, only the stinging. The chemist had the levofloxacin swapped to "
        "doxycycline before a single tablet was taken, so the heart clinic's same-day rule never came "
        "into play — his words, more or less."
    ),
    history="Fibrillation five years on amiodarone; a worrier, as my file doubtless says.",
    medications="Amiodarone, edoxaban — and the doxycycline the chemist arranged this morning.",
    context="My daughter Gail handles my prescriptions; I am home all day.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_d03_swapped_script_defused",
)

RUSHWELL_SPLIT_INTAKE = (
    "Hello. I do not want a fuss, but my daughter says everything goes on the record, so here it is. "
    "The out-of-hours doctor gave me a prescription for levofloxacin last night, for a water infection. "
    "My daughter took the prescription to the chemist for me first thing, so the tablets are not in the "
    "house yet.\n\n"
    "I am not poorly in myself beyond the waterworks stinging. If somebody would make a note of it on "
    "my record, that is all I am after."
)

pt_rushwell_b = _caller(
    "pt_rushwell_b",
    "Gail Rushwell",
    51,
    "F",
    chart=(
        "Cervical screening due this year; otherwise well.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I book my smear test, please? The reminder letter has been on the fridge a month and "
        "I keep missing the phone lines. Any routine nurse appointment works — I can do most days if I "
        "juggle."
    ),
    onset="Nothing new — the screening reminder has come round.",
    severity="Perfectly well; it is the routine smear.",
    history="Nothing of note; screening always clear before.",
    medications="None.",
    context="I juggle work and my father's errands, but most days can be made to work.",
    gold=_routine_gold(),
    source="authored:amiodarone_qt_d03_kin_smear_booking",
)

RUSHWELL_B_SPLIT_INTAKE = (
    "Hi. Could I book my smear test, please? The reminder has been on the fridge a month. Any routine "
    "nurse appointment works.\n\n"
    "Also — important, before my dad's call this morning sends anyone running. Walter Rushwell, my "
    "father: the out-of-hours doctor did write him levofloxacin last night, but when I took the "
    "prescription in first thing the chemist flagged his amiodarone on the screen, rang the prescriber "
    "back, and had it changed to doxycycline on the spot. Dad never took a single levofloxacin tablet — "
    "it is the doxycycline he started, which the chemist says sits perfectly well with his heart "
    "tablet. He just frightens easily, and I promised I would set the record straight."
)

#: The split twin's phone-probe answers for the decoy himself: his knowledge state stops at the
#: prescription leaving the house — the swap is his daughter's news to carry.
RUSHWELL_SPLIT_FACTS = {
    "onset": (
        "The water infection since midweek. The out-of-hours doctor left a prescription last night and "
        "my daughter has taken it to the chemist this morning."
    ),
    "severity": (
        "Comfortable enough, only the stinging. I have not started the new tablets — they are not back "
        "from the chemist yet."
    ),
    "medications": (
        "Amiodarone and edoxaban. There is a new antibiotic prescription with my daughter at the "
        "chemist as we speak — not a tablet of it taken yet."
    ),
}

# ══ THE BOARD SKELETON (shared by both twins byte-for-byte) ══════════════════════════════════════════════
CARDS = (
    # claimants, contest order
    pt_quenden,
    pt_redmire,
    pt_quendon,
    pt_rathmell,
    pt_quengarth,
    pt_quengill,
    pt_quenlund,
    pt_quenroyd,
    pt_quenthwaite,
    pt_quarnbrook,
    pt_quarncliffe,
    pt_quarndon,
    pt_quarngarth,
    pt_quillcote,
    pt_quillgarth,
    pt_rylstone,
    pt_quornsett,
    pt_quornridge,
    pt_quexby,
    pt_quarnwell,
    pt_quorngill,
    pt_quexcote,
    # kin carriers
    pt_quenden_b,
    pt_quendon_b,
    pt_quengarth_b,
    pt_quenlund_b,
    pt_quenthwaite_b,
    pt_quarncliffe_b,
    pt_quarngarth_b,
    pt_quillgarth_b,
    pt_quornsett_b,
    pt_quexby_b,
    pt_quorngill_b,
    # holders, contest order
    pt_ramsdijk,
    pt_quatford,
    pt_ramsfold,
    pt_ramsgill,
    pt_ramslund,
    pt_quinbury,
    pt_ramsridge,
    pt_ramsroyd,
    pt_ramssett,
    pt_ramsthwaite,
    pt_ramswell,
    pt_rookgarth,
    pt_rookcliffe,
    pt_rooklund,
    pt_rushmead,
    pt_rushgarth,
    pt_rydebrook,
    pt_quethiock,
    pt_rokeby,
    pt_rothgarth,
    pt_rothmead,
    pt_rixholm,
    # decoys + the split-defusal carrier
    pt_radbrook,
    pt_quidenham,
    pt_rushwell,
    pt_rushwell_b,
)

#: The sanctioned same-surname shapes: eleven claimant kin plus the decoy's daughter.
KIN_OF = {
    "pt_quenden_b": "pt_quenden",
    "pt_quendon_b": "pt_quendon",
    "pt_quengarth_b": "pt_quengarth",
    "pt_quenlund_b": "pt_quenlund",
    "pt_quenthwaite_b": "pt_quenthwaite",
    "pt_quarncliffe_b": "pt_quarncliffe",
    "pt_quarngarth_b": "pt_quarngarth",
    "pt_quillgarth_b": "pt_quillgarth",
    "pt_quornsett_b": "pt_quornsett",
    "pt_quexby_b": "pt_quexby",
    "pt_quorngill_b": "pt_quorngill",
    "pt_rushwell_b": "pt_rushwell",
}


def _contest(
    claimant: str, holder: str, provider_id: str, slot_hhmm: str, standing_reason: str
) -> BoardContest:
    """One P09 contest: the shared columns stated once (cardiology, 17:00, serious, levofloxacin).

    The decisive fact is the same word on every contest deliberately — the levofloxacin script IS the
    mechanism, present in every claimant's assembled calls and absent from every chart by the split gate's
    string assert.
    """
    return BoardContest(
        claimant=claimant,
        holder=holder,
        specialty=CARDIOLOGY,
        provider_id=provider_id,
        slot_hhmm=slot_hhmm,
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=standing_reason,
        decisive_fact="levofloxacin",
    )


CONTESTS = (
    _contest(
        "pt_quenden",
        "pt_ramsdijk",
        "dr_reyes_santos",
        "13:40",
        "Annual pacemaker check (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_redmire",
        "pt_quatford",
        "dr_reyes_santos",
        "15:00",
        "Echo follow-up review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quendon",
        "pt_ramsfold",
        "dr_reyes_santos",
        "16:20",
        "Heart-failure annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_rathmell",
        "pt_ramsgill",
        "dr_quenridge",
        "13:20",
        "Blood pressure and rhythm review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quengarth",
        "pt_ramslund",
        "dr_quenridge",
        "14:40",
        "Angina annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quengill",
        "pt_quinbury",
        "dr_quenridge",
        "15:20",
        "Heart-failure medication review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quenlund",
        "pt_ramsridge",
        "dr_quenridge",
        "16:40",
        "Valve surveillance review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quenroyd",
        "pt_ramsroyd",
        "dr_ramsholm",
        "13:20",
        "Post-ablation annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quenthwaite",
        "pt_ramssett",
        "dr_ramsholm",
        "13:40",
        "Palpitation follow-up review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quarnbrook",
        "pt_ramsthwaite",
        "dr_ramsholm",
        "15:00",
        "Annual heart-failure review and bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quarncliffe",
        "pt_ramswell",
        "dr_ramsholm",
        "16:20",
        "Pacemaker annual check (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quarndon",
        "pt_rookgarth",
        "dr_quensett",
        "13:40",
        "Echo review appointment (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quarngarth",
        "pt_rookcliffe",
        "dr_quensett",
        "14:40",
        "Cardiology medication review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quillcote",
        "pt_rooklund",
        "dr_quensett",
        "15:20",
        "Pressure and rhythm annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quillgarth",
        "pt_rushmead",
        "dr_quensett",
        "16:40",
        "Annual angina review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_rylstone",
        "pt_rushgarth",
        "dr_ramsgarth",
        "13:20",
        "Valve repair surveillance (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quornsett",
        "pt_rydebrook",
        "dr_ramsgarth",
        "14:40",
        "Post-stent follow-up review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quornridge",
        "pt_quethiock",
        "dr_ramsgarth",
        "15:00",
        "Heart-failure review with bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quexby",
        "pt_rokeby",
        "dr_ramsgarth",
        "16:40",
        "Heart-monitor results review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quarnwell",
        "pt_rothgarth",
        "dr_quenmead",
        "13:40",
        "Heart medication review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quorngill",
        "pt_rothmead",
        "dr_quenmead",
        "14:40",
        "Echo surveillance review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_quexcote",
        "pt_rixholm",
        "dr_quenmead",
        "16:20",
        "Annual rhythm review (wait-list backfill into a returned cancellation)",
    ),
)

#: Decoy ids are identical across twins (§6); the split twin moves Rushwell's defusal into his daughter's
#: call, so only there does the `defusing_caller_id` column point at her.
DECOYS_PLAIN = (
    Decoy(patient_id="pt_radbrook"),
    Decoy(patient_id="pt_quidenham"),
    Decoy(patient_id="pt_rushwell"),
)
DECOYS_SPLIT = (
    Decoy(patient_id="pt_radbrook"),
    Decoy(patient_id="pt_quidenham"),
    Decoy(patient_id="pt_rushwell", defusing_caller_id="pt_rushwell_b"),
)

#: Arrival plan, identical across the twins (the split adds eleven RECALL beats, which is call structure).
#: Claimants take desks in the v1 shifted pattern (holder desk + 2), kin land on a desk their claimant did
#: not, and the corpus background quartet carries the voicemail trio across three desks.
#:
#: ORDERING RULE (meshfull; reordered at integration to P08's ratified pattern): all twenty-two claimants
#: sit inside the first 26 distinct callers, so every claimant's meshfull seat is a single-letter
#: spreadsheet id. Two-letter seats (`AA`+) SORT between `A` and `B`, so their callers race in the naive
#: plan's first round ahead of the holders seated on desks B-V — on a single-diary board any contested
#: slot serves any claimant, so a claimant in an `AA+` seat would snipe a holder's slot and the
#: naive-starvation gate (rightly) refuses. The 15 late seats carry only the decoys and the kin carriers,
#: whose golds cannot touch the contested diary. Relative order within each group, every caller's mesh4
#: desk letter, and the authored arrival-time ladder are unchanged.
ARRIVALS = (
    ("pt_quenden", "C", 0),
    ("pt_redmire", "D", 4),
    ("pt_lachaux", "B", 9),
    ("pt_quendon", "A", 14),
    ("pt_rathmell", "B", 18),
    ("pt_quengarth", "C", 23),
    ("pt_dunmore", "C", 27),
    ("pt_quengill", "D", 32),
    ("pt_quenlund", "A", 36),
    ("pt_ledwidge", "A", 40),
    ("pt_quenroyd", "B", 44),
    ("pt_quenthwaite", "C", 49),
    ("pt_quarnbrook", "D", 53),
    ("pt_arundel", "D", 57),
    ("pt_quarncliffe", "A", 61),
    ("pt_quarndon", "B", 65),
    ("pt_quarngarth", "C", 69),
    ("pt_quillcote", "D", 73),
    ("pt_quillgarth", "A", 77),
    ("pt_rylstone", "B", 81),
    ("pt_quornsett", "C", 85),
    ("pt_quornridge", "D", 89),
    ("pt_quexby", "A", 93),
    ("pt_quarnwell", "B", 97),
    ("pt_quorngill", "C", 101),
    ("pt_quexcote", "D", 105),
    ("pt_radbrook", "A", 109),
    ("pt_quenden_b", "D", 113),
    ("pt_rushwell", "B", 117),
    ("pt_quendon_b", "B", 121),
    ("pt_quengarth_b", "A", 125),
    ("pt_quidenham", "C", 129),
    ("pt_quenlund_b", "C", 133),
    ("pt_quenthwaite_b", "A", 137),
    ("pt_rushwell_b", "D", 141),
    ("pt_quarncliffe_b", "D", 145),
    ("pt_quarngarth_b", "B", 149),
    ("pt_quillgarth_b", "C", 153),
    ("pt_quornsett_b", "B", 157),
    ("pt_quexby_b", "D", 161),
    ("pt_quorngill_b", "A", 165),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: Plain twin: every claimant's whole story in their own single intake.
EVIDENCE_PLAIN = tuple(
    EvidenceCall(caller_id=contest.claimant, about_claimant=contest.claimant)
    for contest in CONTESTS
)


def _recall(claimant: str, desk: str, at_min: int, text: str) -> EvidenceCall:
    """A claimant's ring-back piece (split twin), landing on a desk their intake did not."""
    return EvidenceCall(
        caller_id=claimant,
        about_claimant=claimant,
        kind="recall",
        at_min=at_min,
        desk=desk,
        text=text,
    )


def _kin_piece(kin: str, claimant: str) -> EvidenceCall:
    """A family carrier's intake piece (split twin) — the desk comes off their own arrival."""
    return EvidenceCall(caller_id=kin, about_claimant=claimant)


#: Split twin: piece 1 is each claimant's routine-sounding intake; piece 2 is a kin carrier's own call
#: (odd contests) or the claimant's ring-back (even contests), always on a second desk.
EVIDENCE_SPLIT = (
    *EVIDENCE_PLAIN,
    _kin_piece("pt_quenden_b", "pt_quenden"),
    _recall("pt_redmire", "B", 110, REDMIRE_RECALL_TEXT),
    _kin_piece("pt_quendon_b", "pt_quendon"),
    _recall("pt_rathmell", "D", 120, RATHMELL_RECALL_TEXT),
    _kin_piece("pt_quengarth_b", "pt_quengarth"),
    _recall("pt_quengill", "B", 132, QUENGILL_RECALL_TEXT),
    _kin_piece("pt_quenlund_b", "pt_quenlund"),
    _recall("pt_quenroyd", "D", 144, QUENROYD_RECALL_TEXT),
    _kin_piece("pt_quenthwaite_b", "pt_quenthwaite"),
    _recall("pt_quarnbrook", "B", 168, QUARNBROOK_RECALL_TEXT),
    _kin_piece("pt_quarncliffe_b", "pt_quarncliffe"),
    _recall("pt_quarndon", "D", 178, QUARNDON_RECALL_TEXT),
    _kin_piece("pt_quarngarth_b", "pt_quarngarth"),
    _recall("pt_quillcote", "B", 190, QUILLCOTE_RECALL_TEXT),
    _kin_piece("pt_quillgarth_b", "pt_quillgarth"),
    _recall("pt_rylstone", "D", 200, RYLSTONE_RECALL_TEXT),
    _kin_piece("pt_quornsett_b", "pt_quornsett"),
    _recall("pt_quornridge", "B", 212, QUORNRIDGE_RECALL_TEXT),
    _kin_piece("pt_quexby_b", "pt_quexby"),
    _recall("pt_quarnwell", "D", 222, QUARNWELL_RECALL_TEXT),
    _kin_piece("pt_quorngill_b", "pt_quorngill"),
    _recall("pt_quexcote", "A", 232, QUEXCOTE_RECALL_TEXT),
)

#: The split twin's voices: claimants say only their routine piece 1; kin add their mention; the
#: split-defused decoy loses the defusal his daughter now carries.
SPLIT_INTAKE_OVERRIDES: dict[str, str] = {
    "pt_quenden": QUENDEN_SPLIT_INTAKE,
    "pt_redmire": REDMIRE_SPLIT_INTAKE,
    "pt_quendon": QUENDON_SPLIT_INTAKE,
    "pt_rathmell": RATHMELL_SPLIT_INTAKE,
    "pt_quengarth": QUENGARTH_SPLIT_INTAKE,
    "pt_quengill": QUENGILL_SPLIT_INTAKE,
    "pt_quenlund": QUENLUND_SPLIT_INTAKE,
    "pt_quenroyd": QUENROYD_SPLIT_INTAKE,
    "pt_quenthwaite": QUENTHWAITE_SPLIT_INTAKE,
    "pt_quarnbrook": QUARNBROOK_SPLIT_INTAKE,
    "pt_quarncliffe": QUARNCLIFFE_SPLIT_INTAKE,
    "pt_quarndon": QUARNDON_SPLIT_INTAKE,
    "pt_quarngarth": QUARNGARTH_SPLIT_INTAKE,
    "pt_quillcote": QUILLCOTE_SPLIT_INTAKE,
    "pt_quillgarth": QUILLGARTH_SPLIT_INTAKE,
    "pt_rylstone": RYLSTONE_SPLIT_INTAKE,
    "pt_quornsett": QUORNSETT_SPLIT_INTAKE,
    "pt_quornridge": QUORNRIDGE_SPLIT_INTAKE,
    "pt_quexby": QUEXBY_SPLIT_INTAKE,
    "pt_quarnwell": QUARNWELL_SPLIT_INTAKE,
    "pt_quorngill": QUORNGILL_SPLIT_INTAKE,
    "pt_quexcote": QUEXCOTE_SPLIT_INTAKE,
    "pt_quenden_b": QUENDEN_B_SPLIT_INTAKE,
    "pt_quendon_b": QUENDON_B_SPLIT_INTAKE,
    "pt_quengarth_b": QUENGARTH_B_SPLIT_INTAKE,
    "pt_quenlund_b": QUENLUND_B_SPLIT_INTAKE,
    "pt_quenthwaite_b": QUENTHWAITE_B_SPLIT_INTAKE,
    "pt_quarncliffe_b": QUARNCLIFFE_B_SPLIT_INTAKE,
    "pt_quarngarth_b": QUARNGARTH_B_SPLIT_INTAKE,
    "pt_quillgarth_b": QUILLGARTH_B_SPLIT_INTAKE,
    "pt_quornsett_b": QUORNSETT_B_SPLIT_INTAKE,
    "pt_quexby_b": QUEXBY_B_SPLIT_INTAKE,
    "pt_quorngill_b": QUORNGILL_B_SPLIT_INTAKE,
    "pt_rushwell": RUSHWELL_SPLIT_INTAKE,
    "pt_rushwell_b": RUSHWELL_B_SPLIT_INTAKE,
}

#: The split twin's phone-probe channel: every card whose canonical fact answers
#: restate the assembled case — the 22 claimants and the split-defused decoy — answers a desk's ring-back
#: sub-threshold instead (the new tablets in passing, never the decisive name, never the maintenance link
#: in the same breath). Kin carriers keep their canonical answers: their own matters never carried it.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_quenden": QUENDEN_SPLIT_FACTS,
    "pt_redmire": REDMIRE_SPLIT_FACTS,
    "pt_quendon": QUENDON_SPLIT_FACTS,
    "pt_rathmell": RATHMELL_SPLIT_FACTS,
    "pt_quengarth": QUENGARTH_SPLIT_FACTS,
    "pt_quengill": QUENGILL_SPLIT_FACTS,
    "pt_quenlund": QUENLUND_SPLIT_FACTS,
    "pt_quenroyd": QUENROYD_SPLIT_FACTS,
    "pt_quenthwaite": QUENTHWAITE_SPLIT_FACTS,
    "pt_quarnbrook": QUARNBROOK_SPLIT_FACTS,
    "pt_quarncliffe": QUARNCLIFFE_SPLIT_FACTS,
    "pt_quarndon": QUARNDON_SPLIT_FACTS,
    "pt_quarngarth": QUARNGARTH_SPLIT_FACTS,
    "pt_quillcote": QUILLCOTE_SPLIT_FACTS,
    "pt_quillgarth": QUILLGARTH_SPLIT_FACTS,
    "pt_rylstone": RYLSTONE_SPLIT_FACTS,
    "pt_quornsett": QUORNSETT_SPLIT_FACTS,
    "pt_quornridge": QUORNRIDGE_SPLIT_FACTS,
    "pt_quexby": QUEXBY_SPLIT_FACTS,
    "pt_quarnwell": QUARNWELL_SPLIT_FACTS,
    "pt_quorngill": QUORNGILL_SPLIT_FACTS,
    "pt_quexcote": QUEXCOTE_SPLIT_FACTS,
    "pt_rushwell": RUSHWELL_SPLIT_FACTS,
}

#: One sentence of size cover: a fact about the morning that names no caller, no provider and
#: no action.
MEMO_COVER_LINE = (
    "The out-of-hours and walk-in services worked a two-day backlog of infection calls off our list "
    "overnight, prescribing to the urgent-care formulary, so an unusual share of this morning's callers "
    "will be ringing about medicines started since yesterday evening."
)

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=22,
    theme_slug=THEME,
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_PLAIN,
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
    size=22,
    theme_slug=THEME,
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_SPLIT,
    decoys=DECOYS_SPLIT,
    cards=CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="300",
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
