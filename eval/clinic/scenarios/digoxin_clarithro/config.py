"""P04 `digoxin_clarithro`: twelve digoxin patients, twelve new clarithromycin scripts, one cardiology diary.

The locked pair (row P04 of the board assignments): **size 12**, mechanism family *digoxin + new clarithromycin for a chest infection ⇒ same-day digoxin level + review*, target diary **cardiology** (a base diary — the board staffs it with three visiting consultants rather than wiring a new specialty). A chesty bug is going round and the out-of-hours services have been writing macrolides all week; twelve of the practice's digoxin patients started clarithromycin within the last day, and every one of them was told by the heart clinic, when the digoxin began, that this exact antibiotic means a level drawn at the clinic the same day. Assembled, the reprioritization is textbook-obvious (clarithromycin raises digoxin levels — classic interaction, standard same-day monitoring, no dosing arithmetic); solo, every piece reads routine (a repeat request, a neighbour's chemist run, a stable chart). The ED adds nothing structurally: nobody is unwell beyond a chesty cough that predates the antibiotic, and the thing that is needed — a level drawn and read against the clinic's own dosing record — is the practice cardiology clinic's ordinary work, before its bloods finish at five.

Twin structure: the **plain** twin delivers each claimant's whole story in their own single intake; the **split** twin gives the same claimant a routine-sounding intake (a repeat script, an appointment query) and moves the decisive fact — the word *clarithromycin* — into a ring-back on another desk or into a family/neighbour carrier's own routine call. Charts are byte-identical across the twins and never say clarithromycin.

DATA ONLY, on `deadline_day`'s discipline: the gates live in `design_check`, the dials in `pressure`, the solver in `values`. Nothing here reads the world.
"""

from __future__ import annotations

from collections.abc import Mapping

from clinic.environment.board_spec import (
    BoardContest,
    BoardSpec,
    Decoy,
    EvidenceCall,
    board_gold,
    register_board,
)
from clinic.environment.diaries import board_provider
from clinic.environment.reprioritization import (
    _caller,  # pyright: ignore[reportPrivateUsage]
)
from clinic.environment.resources import (
    CARDIOLOGY,
    FAMILY_MEDICINE,
    INTERNAL_MEDICINE,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    Urgency,
)

PLAIN_ID = "digoxin_clarithro_plain"
SPLIT_ID = "digoxin_clarithro_split"
PAIR_ID = "P04_digoxin_clarithro"
THEME = "digoxin_clarithro"

# ── the practice extension: three visiting cardiology lists beside the base diary ─────────────────────────
#: The board's roster growth: cardiology is a base diary, so nothing new is wired — the board
#: simply staffs it, which is what twelve returned-cancellation slots on one specialty cost. The memo's one
#: cover sentence carries the fiction (a neighbouring practice's closure has moved its lists here).
DR_HATHERWELL = board_provider("dr_hatherwell", "Dr. N. Hatherwell", CARDIOLOGY)
DR_GARSDEN = board_provider("dr_garsden", "Dr. E. Garsden", CARDIOLOGY)
DR_GRIMWELL = board_provider("dr_grimwell", "Dr. B. Grimwell", CARDIOLOGY)
NEW_PROVIDERS = (DR_HATHERWELL, DR_GARSDEN, DR_GRIMWELL)


def _holder_gold() -> GoldTriage:
    """A routine holder's gold: NON_URGENT on the cardiology service they already attend (the v2 shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=CARDIOLOGY,
        acceptable=frozenset({CARDIOLOGY}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's or decoy's gold: NON_URGENT primary care — never a contested service, never the pool."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=FAMILY_MEDICINE,
        acceptable=frozenset({FAMILY_MEDICINE, INTERNAL_MEDICINE}),
        ed_required=False,
    )


# ══ THE TWELVE CLAIMANTS ═══════════════════════════════════════════════════════════════════════════════════
# Canonical intake = the PLAIN twin's words (the whole story in one call); the split twin's routine-only
# intake and its ring-back/carrier pieces live in the override constants beneath each card.

pt_gorsebrook = _caller(
    "pt_gorsebrook",
    "Ronald Gorsebrook",
    82,
    "M",
    chart=(
        "Permanent atrial fibrillation, rate-controlled for nine years.",
        "Digoxin level monitored at the practice cardiology clinic; last level six weeks ago, in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, ramipril 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I had the out-of-hours doctor to the house last night with a chest infection — proper "
        "chesty, bit of a temperature that has come down again — and he has started me on clarithromycin; "
        "the first ones went down with my supper.\n\n"
        "The heart clinic have drummed it into me for years: if any doctor ever puts me on clarithromycin, "
        "my digoxin level wants drawing at their clinic the same day, because the one pushes the other up. "
        "So somebody there ought to see me today, before their bloods finish — the clinic closes at five.\n\n"
        "The chest itself is nothing to write home about. It is the two tablets mixing that the clinic "
        "fusses over, and rightly, they tell me."
    ),
    onset="The cough got noisy over the weekend; the clarithromycin started with last night's supper.",
    severity=(
        "A loose cough and I am a bit washed out, no more than that. It is the antibiotic sitting beside "
        "the digoxin that the clinic tests for."
    ),
    history="The irregular heartbeat, nine years, steady on the same dose, watched at your heart clinic.",
    medications=(
        "Digoxin every morning, the ramipril — and since last night the clarithromycin the out-of-hours "
        "doctor left for my chest."
    ),
    context="Retired; my wife Peggy and I are round the corner. Any hour today does us.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_gorsebrook_ooh_home_visit",
)

GORSEBROOK_SPLIT_INTAKE = (
    "Morning. Nothing pressing — my digoxin repeat is down to the last strip and the chemist likes a few "
    "days' notice. Could the repeat go through as usual, please?\n\n"
    "Otherwise I am ticking along; no need for anybody to see me on my account."
)

GORSEBROOK_RECALL_TEXT = (
    "Ronald Gorsebrook again — my wife said to ring you back and she is right. The out-of-hours doctor who "
    "came to us last night started me on clarithromycin for my chest, and she has been on at me that the "
    "surgery should have that on my record from us rather than wait for the paperwork. So there it is, "
    "said. The chest itself is no worse than it was."
)

pt_hazelmere = _caller(
    "pt_hazelmere",
    "Vera Hazelmere",
    78,
    "F",
    chart=(
        "Chronic heart failure, stable on treatment; last annual echocardiogram unchanged.",
        "Digoxin level checked at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 62.5 micrograms daily, furosemide 40 mg morning, bisoprolol 2.5 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My grandson set me up with one of those video doctor services on the tablet, and their "
        "doctor saw me yesterday evening about a chest infection — he has put me on clarithromycin and I "
        "took the first at bedtime.\n\n"
        "When the digoxin was started the heart clinic told me plainly: that particular antibiotic and my "
        "tablet do not sit well together, and the level has to be drawn at their clinic the same day it "
        "begins. So I ought to be seen there today — their blood-taking stops when they shut at five.\n\n"
        "In myself I am only middling: a rattly cough and off my food a touch. Nothing worse than that."
    ),
    onset="The cough came up midweek; the clarithromycin started at bedtime yesterday.",
    severity="Rattly and off my food since the bug began — no different this morning. Nothing I would call poorly.",
    history="The heart failure, steady for years on the same three tablets, seen at your heart clinic.",
    medications=(
        "Digoxin, the water tablet in the morning, the bisoprolol — and now the clarithromycin the video "
        "doctor prescribed yesterday evening."
    ),
    context="My grandson can run me over at whatever hour suits; we are ten minutes away.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_hazelmere_video_gp",
)

HAZELMERE_SPLIT_INTAKE = (
    "Hello. It is my water tablet, the furosemide — the repeat has run out of authorisations at the "
    "chemist and I have three days left in the box. Could somebody put the repeat through, please?\n\n"
    "There is no drama on my side; I just like to keep ahead of the box."
)

HAZELMERE_RECALL_TEXT = (
    "Sorry to be ringing twice in a morning — Vera Hazelmere. After the repeat I remembered the other "
    "thing: a video doctor my grandson arranged saw me yesterday evening and started me on clarithromycin "
    "for a chest infection. My grandson says those video people never send their letters on for weeks, "
    "so I had better say it out loud rather than trust it to the paperwork."
)

pt_granworth = _caller(
    "pt_granworth",
    "Dennis Granworth",
    75,
    "M",
    chart=(
        "Atrial fibrillation, rate-controlled; annual cardiology review attended on schedule.",
        "Digoxin level monitored at the practice cardiology clinic; last level two months ago, in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, atorvastatin 20 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The doctor at the out-of-hours hub started me on clarithromycin last night — my chest "
        "had gone all crackly with this bug that is doing the rounds — and the heart clinic gave me a card "
        "years back that says plain as day: clarithromycin means a digoxin level at the clinic the same "
        "day. I have the card in front of me now.\n\n"
        "The chest is already on the mend if anything, so it is not that. It is the level the clinic will "
        "want, today, and their bloods are done by five when the clinic closes."
    ),
    onset="The crackle started with the bug midweek; the clarithromycin began last night at the hub.",
    severity="A crackly cough, mending. It is the card's rule about the two medicines, not how I feel.",
    history="The irregular heartbeat, twelve years. The clinic's card about antibiotics lives on my fridge.",
    medications="Digoxin in the morning, the statin at night — and the clarithromycin since last night.",
    context="I still drive; I can be with you inside a quarter of an hour whenever you say.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_granworth_ooh_hub",
)

GRANWORTH_SPLIT_INTAKE = (
    "Morning. Only booking, nothing wrong — I am due my blood-pressure check about now by my reckoning, "
    "and I would sooner have it in the diary than let it drift.\n\n"
    "Any day that suits the nurse suits me; I still drive, so the time of day is no matter."
)

GRANWORTH_RECALL_TEXT = (
    "Dennis Granworth here, ringing back — I clean forgot to mention the new tablets. The out-of-hours "
    "hub put me on clarithromycin last night for my chest; first dose at ten, second with breakfast. My "
    "wife keeps the medicine list on the fridge and she likes yours to match hers, so that is the whole "
    "errand: get it written on my list, please."
)

pt_harrowden = _caller(
    "pt_harrowden",
    "Marjorie Harrowden",
    84,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled; mild kidney impairment, stable on annual bloods.",
        "Digoxin level monitored at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 62.5 micrograms daily, apixaban 2.5 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, pet. My daughter Linda took me to the private walk-in place yesterday because my chest "
        "was wheezy and I could not get a peep out of anywhere else, and their doctor started me on "
        "clarithromycin at teatime.\n\n"
        "The heart clinic's folder — Linda keeps it — says anything new alongside the digoxin gets flagged "
        "to the surgery, and that antibiotic in particular means the level drawn at the clinic the same "
        "day. So they will want me today, before the blood-taking finishes at five.\n\n"
        "I am not ill with it, you understand. Wheezy and a bit tired, and cross about the fuss."
    ),
    onset="Wheezy since the weekend; the clarithromycin started at teatime yesterday.",
    severity="Wheezy and tired, nothing dramatic. It is the clinic's rule about the antibiotic, not me.",
    history="The irregular heart, going back years, and the kidneys watched with a yearly blood test.",
    medications="The digoxin, the apixaban twice a day — and the clarithromycin from the walk-in place.",
    context="My daughter Linda does the driving and the diary; she can bring me at any hour today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_harrowden_private_walk_in",
)

HARROWDEN_SPLIT_INTAKE = (
    "Hello, pet. It is only my eye drops — the repeat has come to an end and the chemist says there is "
    "nothing left on it. Could somebody see to the repeat, please?\n\n"
    "No hurry at all; the bottle does me to the end of the week."
)

pt_glenfold = _caller(
    "pt_glenfold",
    "Colin Glenfold",
    77,
    "M",
    chart=(
        "Chronic heart failure, stable; annual review and bloods attended on schedule.",
        "Digoxin level checked at the practice cardiology clinic; last level three months ago, in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, ramipril 5 mg daily, furosemide 40 mg morning.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I sat two hours at the out-of-hours hub last night with this chest that is going round "
        "and came away with clarithromycin — first dose at ten o'clock, second with breakfast.\n\n"
        "The heart clinic told me when they started the digoxin, and again at every review since: that "
        "antibiotic is the one that shoves the digoxin level up, and the level gets drawn at their clinic "
        "the same day it starts, no exceptions. Their bloods run until the clinic shuts at five.\n\n"
        "I have been off my food since the bug started — no different this morning — and nothing worse: "
        "the cough is just a cough."
    ),
    onset="The chest came on with the bug; the clarithromycin started at ten last night.",
    severity="A cough, and my appetite went with the bug — no change today. Nothing frightening; I ate half my toast.",
    history="The heart failure, seven years, steady on the same dose, reviewed yearly at your clinic.",
    medications=(
        "Digoxin, the ramipril, the water tablet with breakfast — and the clarithromycin from the hub "
        "since last night."
    ),
    context="Retired; my brother next door drives me anywhere at a pinch. Today is wide open.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_glenfold_ooh_hub",
)

GLENFOLD_SPLIT_INTAKE = (
    "Morning. I am ringing about my B12 injection — by my book I am due it about now and nobody has sent "
    "for me. Could you see when the nurse has me down for?\n\n"
    "No trouble otherwise; I just like the injections kept regular."
)

GLENFOLD_RECALL_TEXT = (
    "Colin Glenfold, ringing back — the chemist put me up to it. I was at the out-of-hours hub last night "
    "with my chest and they started me on clarithromycin, and when I collected the box this morning the "
    "chemist said the surgery would rather hear it twice than not at all. So: clarithromycin, started "
    "last night, for the chest. That is the lot."
)

pt_hockcliffe = _caller(
    "pt_hockcliffe",
    "Brenda Hockcliffe",
    80,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled; annual cardiology review attended on schedule.",
        "Digoxin level monitored at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, simvastatin 40 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I went to the private urgent-care clinic in town yesterday evening — the cough had got "
        "hold of me and I did not want to be a nuisance to anybody — and their doctor started me on "
        "clarithromycin. My neighbour Mr Garthdale fetched the box from their chemist last night.\n\n"
        "The heart clinic have a note about me: if I am ever started on that antibiotic, the digoxin level "
        "is to be taken at their clinic the same day. They will want me in today, then, before their "
        "bloods finish — the clinic closes at five.\n\n"
        "The cough is easing already, I should say. It is the note's rule, not the cough."
    ),
    onset="Coughing since the weekend like half the street; the clarithromycin started last night.",
    severity="A tiring cough, easing. I am not poorly with it — it is the two medicines the clinic minds.",
    history="The irregular heartbeat, kept steady for years; the clinic put the antibiotic note on my file.",
    medications="Digoxin of a morning, the statin at night — and now the clarithromycin from the town clinic.",
    context="Mr Garthdale over the road runs me about; he is in and out of the chemist for me as it is.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_hockcliffe_private_urgent_care",
)

HOCKCLIFFE_SPLIT_INTAKE = (
    "Hello. Only my cholesterol tablet, the simvastatin — the chemist says the repeat has run dry and "
    "wants the surgery's say-so. Could somebody see to it when there is a minute spare?\n\n"
    "No rush on my account; I have a week's worth in the drawer."
)

pt_greywell = _caller(
    "pt_greywell",
    "Kenneth Greywell",
    85,
    "M",
    chart=(
        "Atrial fibrillation, rate-controlled; housebound in winter, otherwise attends with his son.",
        "Digoxin level monitored at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 62.5 micrograms daily, bisoprolol 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I rang the out-of-hours line last night about this chest — coughing fit to wake the "
        "street — and their doctor called me back, listened to me hack away, and sent clarithromycin "
        "round to the late chemist. I have had two doses now.\n\n"
        "The heart clinic made my son write it in the front of my diary when the digoxin started: "
        "clarithromycin means the level done at the clinic that same day, because it drives the digoxin "
        "up. So today is the day, and their bloods stop when the clinic shuts at five.\n\n"
        "I am no worse in myself than any winter — the cough is a pest and that is the size of it."
    ),
    onset="The cough set in with the bug going round; the clarithromycin came round last night.",
    severity="A hacking cough and short patience. Nothing a man my age calls an emergency, mind.",
    history="The irregular heart, longer than I can date. My son keeps the clinic's instructions in my diary.",
    medications="Digoxin and the bisoprolol every morning — and the clarithromycin since last night.",
    context="My son calls in twice a day and can run me up whenever suits the clinic.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_greywell_ooh_phone_script",
)

GREYWELL_SPLIT_INTAKE = (
    "Morning. My ears want doing — the left one has gone muffled again and the drops are not shifting it. "
    "Could I go on the nurse's list for a syringing, whenever there is a space?\n\n"
    "There is no hurry; I have managed worse than a muffled ear."
)

GREYWELL_RECALL_TEXT = (
    "Kenneth Greywell — my son told me to ring you back the moment he saw the box. The out-of-hours "
    "doctor sent clarithromycin round to the late chemist for my chest last night. My son keeps my "
    "paperwork straight and he wants the surgery's list matching the box on the table, so there it is, "
    "said."
)

pt_hollowmere = _caller(
    "pt_hollowmere",
    "Doris Hollowmere",
    79,
    "F",
    chart=(
        "Chronic heart failure, stable on treatment; annual echocardiogram unchanged.",
        "Digoxin level checked at the practice cardiology clinic; last level two months ago, in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 62.5 micrograms daily, furosemide 20 mg morning, atorvastatin 20 mg "
        "nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My son Gary sorted me one of those telephone-video doctors yesterday evening when my chest "
        "would not settle, and she started me on clarithromycin — the chemist delivered it at eight and I "
        "began straight away.\n\n"
        "The heart clinic were very firm when the digoxin started: that antibiotic pushes the digoxin "
        "level up, and the level is drawn at their clinic the same day it begins. So I should be seen "
        "today, before the clinic's bloods finish at five.\n\n"
        "I am more embarrassed than ill — a barking cough and my appetite gone sideways, and Gary "
        "fretting, which is worse than either."
    ),
    onset="The chest would not settle from the weekend; the clarithromycin began at eight last night.",
    severity="A barking cough and my food does not tempt me. Nothing worse; I walked to the postbox today.",
    history="The heart failure, kept steady for years; the clinic sees me yearly and the numbers behave.",
    medications=(
        "Digoxin, the little water tablet, the statin at night — and the clarithromycin the video doctor "
        "gave me yesterday evening."
    ),
    context="My son Gary works shifts but between him and the bus I can be got in at any time today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_hollowmere_video_gp",
)

HOLLOWMERE_SPLIT_INTAKE = (
    "Hello. It is my statin, the atorvastatin — the repeat wants renewing, the chemist tells me, before "
    "they can make the next lot up. Could somebody put that through in the next day or two?\n\n"
    "That is the whole of it; I will not keep you, you sound run off your feet."
)

pt_hainbrook = _caller(
    "pt_hainbrook",
    "Albert Hainbrook",
    81,
    "M",
    chart=(
        "Atrial fibrillation, rate-controlled for eleven years; annual review attended on schedule.",
        "Digoxin level monitored at the practice cardiology clinic; last level six weeks ago, in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, ramipril 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The out-of-hours doctor started me on clarithromycin last night — this chest bug "
        "everyone is passing about; I sound like a kettle — and my neighbour Mrs Hopwell collected the box "
        "for me first thing.\n\n"
        "The heart clinic told me the day the digoxin started, and they have said it at every review "
        "since: clarithromycin is the one that sends the digoxin level up, and the level gets drawn at "
        "their clinic the same day the antibiotic begins. Their bloods finish when the clinic closes at "
        "five, so it wants doing today.\n\n"
        "I am not ill with it — noisy chest, that is all. It is the clinic's rule I am ringing about."
    ),
    onset="The kettle noise started midweek; the clarithromycin began last night.",
    severity="A noisy chest and a slow morning. Nothing to fret over — it is the medicines, not me.",
    history="The irregular heart, eleven years steady. Mrs Hopwell next door does my fetching and carrying.",
    medications="Digoxin and the ramipril with breakfast — and the clarithromycin since last night.",
    context="Mrs Hopwell next door drives me; between her and my grandson I can make any time today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_hainbrook_ooh",
)

HAINBROOK_SPLIT_INTAKE = (
    "Morning. I am chasing my blood results — the ones the nurse took a few weeks back for the yearly "
    "check. Nobody has said boo, and no news is good news I expect, but I would like it said properly.\n\n"
    "No other business; I will let you get on."
)

pt_hatchmere = _caller(
    "pt_hatchmere",
    "Joyce Hatchmere",
    76,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled; annual cardiology review attended on schedule.",
        "Digoxin level monitored at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I paid to be seen at the walk-in place by the precinct yesterday — this cough was ruining "
        "my sleep and I could not face the wait anywhere else — and their doctor put me on clarithromycin "
        "from yesterday evening.\n\n"
        "Your heart clinic has a note about me and that exact antibiotic: the digoxin level is to be "
        "drawn at the clinic the same day it starts. I read it out to the walk-in doctor and he said yes, "
        "tell your surgery first thing. So here I am — and the clinic's blood-taking ends at five when "
        "they close.\n\n"
        "I am perfectly sensible in myself. Tired of coughing, no more."
    ),
    onset="The cough spoilt three nights' sleep; the clarithromycin started yesterday evening.",
    severity="Cough-tired and cross about the sleep. Otherwise myself entirely.",
    history="The irregular heartbeat, steady on the same dose for years; the antibiotic note is on my file.",
    medications="Digoxin and the amlodipine each morning — and the clarithromycin since yesterday evening.",
    context="I drive myself and the day is empty; name an hour and I will be early for it.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_hatchmere_private_walk_in",
)

HATCHMERE_SPLIT_INTAKE = (
    "Hello. I wanted to ask about the shingles jab — my sister has had hers and she is younger than me, "
    "and I have heard nothing. Am I on a list, or do I put myself on one?\n\n"
    "Nothing else, thank you; whenever somebody can look it up."
)

HATCHMERE_RECALL_TEXT = (
    "Joyce Hatchmere, ringing back — I should have said it earlier and I am cross with myself. I was "
    "seen at the walk-in by the precinct yesterday and started on clarithromycin for this cough. The "
    "walk-in said they do not always write to the surgery straight away, so I am doing their job for "
    "them: clarithromycin, started yesterday teatime."
)

pt_gunthorpe = _caller(
    "pt_gunthorpe",
    "Wilfred Gunthorpe",
    83,
    "M",
    chart=(
        "Chronic heart failure, stable; walks with a frame since the hip replacement.",
        "Digoxin level checked at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 62.5 micrograms daily, bisoprolol 1.25 mg daily, furosemide 40 mg "
        "morning.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The out-of-hours doctor came to the house last night — my chest had got musical and my "
        "wife would not leave it — and he started me on clarithromycin there and then from his bag, with "
        "the rest to collect today.\n\n"
        "The heart clinic have told the pair of us more than once: if clarithromycin ever starts, the "
        "digoxin level is taken at their clinic that same day — the antibiotic sends the level climbing. "
        "So they will want blood off me today, and the clinic's bloods finish at five when they shut.\n\n"
        "I am comfortable enough — chesty and slow, but I am always slow. Elsie will vouch for that."
    ),
    onset="The chest went musical over the weekend; the clarithromycin started from the doctor's bag last night.",
    severity="Chesty and slow with the frame, neither of them new. The rule about the level is the business.",
    history="The heart failure, eight years, and the hip before that. The clinic sees me yearly with Elsie.",
    medications=(
        "Digoxin, the bisoprolol, the water tablet of a morning — and the clarithromycin begun last night."
    ),
    context="My wife Elsie rings the taxis and rules the diary; we can be there at any hour today.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_gunthorpe_ooh_home_visit",
)

GUNTHORPE_SPLIT_INTAKE = (
    "Morning. It is my knee — the good one, if you please, not the new hip — it grumbles on the stairs "
    "and I would like somebody to look at it in the ordinary way of things.\n\n"
    "Whenever there is a gap in the book; it has grumbled a month already, another week will not hurt it."
)

pt_hemswell = _caller(
    "pt_hemswell",
    "Nora Hemswell",
    74,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled; osteoporosis on treatment, annual review attended.",
        "Digoxin level monitored at the practice cardiology clinic; last level in range.",
        "Clinic advice on file: a same-day digoxin level if ever started on a macrolide antibiotic.",
        "Repeat medication: digoxin 125 micrograms daily, alendronic acid weekly, calcium and vitamin D "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor saw me last night for my sinuses — my face has been thick and "
        "throbbing for a week and it finally beat me — and she started me on clarithromycin; I took the "
        "first with my cocoa.\n\n"
        "The heart clinic warned me about exactly this when the digoxin began: clarithromycin is the "
        "antibiotic that pushes the digoxin level up, and the level gets drawn at their clinic the same "
        "day it starts. So I need their needle today, before the bloods finish — the clinic closes at "
        "five.\n\n"
        "The sinuses are just sinuses. I have had a thick head for a week; I can bear it a while longer."
    ),
    onset="The thick head built for a week; the clarithromycin started with last night's cocoa.",
    severity="A throbbing face and a dull head — wearing, not worrying. The level is the pressing thing.",
    history="The irregular heart and the thin bones, both minded on schedule, both behaving.",
    medications=(
        "Digoxin daily, the bone tablet on Sundays, calcium — and the clarithromycin since last night."
    ),
    context="My niece is stopping with me this week and drives; today is entirely flexible.",
    gold=board_gold(CARDIOLOGY),
    source="authored:digoxin_clarithro_hemswell_ooh_sinusitis",
)

HEMSWELL_SPLIT_INTAKE = (
    "Hello. It is only my bone tablet — the alendronic acid, the one I take on Sundays — the chemist says "
    "the repeat has lapsed and they cannot dispense till the surgery renews it. Could that be seen to "
    "this week, please?\n\n"
    "Nothing else the matter; my niece is visiting and keeping me honest."
)

HEMSWELL_RECALL_TEXT = (
    "Nora Hemswell again — forgive the second call, my niece insisted and she is right. The out-of-hours "
    "doctor started me on clarithromycin last night for my sinuses, and my niece says anything a strange "
    "doctor starts ought to go on my list with you before it goes clean out of my head. So that is what "
    "I am doing, and no more fuss than that."
)

# ══ THE TWELVE HOLDERS ═════════════════════════════════════════════════════════════════════════════════════
# Nobody rings about a holder; their intake is what they say if a desk RINGS THEM. None pre-consents to
# being moved; each has an ordinary, human reason to want the appointment they hold.

pt_gorsedale = _caller(
    "pt_gorsedale",
    "Edith Gorsedale",
    77,
    "F",
    chart=(
        "Atrial fibrillation, stable on bisoprolol and apixaban; annual cardiology review due.",
        "Repeat medication: bisoprolol 5 mg daily, apixaban 5 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly heart check is this afternoon — the review and the heart tracing together. My "
        "granddaughter has taken a half-day from the salon to drive me, and getting the two of our diaries "
        "to agree took three goes, so I am glad it is finally landing."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. The numbers were good last year and I have felt no different since.",
    history="The irregular heartbeat, steady for years on the same two tablets, reviewed yearly.",
    medications="The bisoprolol and the apixaban, morning and night, regular as the post.",
    context="My granddaughter took the half-day specially; she is collecting me straight from the salon.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_gorsedale_annual_af",
)

pt_hartsmere = _caller(
    "pt_hartsmere",
    "Leonard Hartsmere",
    72,
    "M",
    chart=(
        "Chronic heart failure, stable on treatment; annual review and bloods due.",
        "Repeat medication: ramipril 5 mg daily, bisoprolol 2.5 mg daily, furosemide 40 mg morning.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon is my heart-failure review, the yearly one with the bloods. My lad booked the day "
        "off work to take me — first leave he has managed since the spring — so the timing suits us down "
        "to the ground and I would as soon keep it."
    ),
    onset="Nothing changed with me; it is the annual look-over.",
    severity="Steady as she goes. I do my walk to the paper shop daily and the breathing keeps up.",
    history="The heart failure, six years, well behaved on the tablets.",
    medications="The ramipril, the bisoprolol, and the water tablet with breakfast.",
    context="My son has today booked off work for it; his shifts do not bend easily.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_hartsmere_hf_review",
)

pt_granfield = _caller(
    "pt_granfield",
    "Iris Granfield",
    69,
    "F",
    chart=(
        "Stable angina, symptoms unchanged for three years; annual review due.",
        "Repeat medication: bisoprolol 5 mg daily, isosorbide mononitrate MR, GTN spray as required.",
        "No known drug allergies.",
    ),
    intake=(
        "My angina review is this afternoon and I have arranged cover at the charity shop specially — we "
        "are only two on a weekday and I do not like leaving Margaret single-handed twice. The angina is "
        "its usual quiet self; it is the yearly check and the spray renewed."
    ),
    onset="Nothing new; the appointment is the yearly one.",
    severity="Quiet. I use the spray once in a blue moon on the steep hill and that is all.",
    history="The angina, three years steady; reviewed yearly and never any drama.",
    medications="The bisoprolol, the long-acting nitrate, and the spray in my handbag for the hill.",
    context="Cover at the shop is arranged for this afternoon only; Margaret cannot do two days alone.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_granfield_angina",
)

pt_heathcote = _caller(
    "pt_heathcote",
    "Sidney Heathcote",
    81,
    "M",
    chart=(
        "Atrial fibrillation, rate-controlled; annual rhythm review with ECG due.",
        "Repeat medication: bisoprolol 3.75 mg daily, edoxaban 60 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My rhythm check is this afternoon, the yearly one with the tracing. I have a seat booked on the "
        "community transport both ways — you book those a fortnight ahead or you do not get them — so this "
        "afternoon is the afternoon, as far as I am concerned."
    ),
    onset="Nothing new at all; the yearly tracing is the whole errand.",
    severity="I am well. The heart keeps its odd time but it has kept it for years.",
    history="The irregular heart, rate kept steady; reviewed every year with the tracing.",
    medications="The bisoprolol and the edoxaban, one each morning.",
    context="The community-transport seat is booked both ways; rebooking one takes a fortnight.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_heathcote_rhythm",
)

pt_glenmead = _caller(
    "pt_glenmead",
    "Mabel Glenmead",
    84,
    "F",
    chart=(
        "Moderate aortic stenosis, stable on annual echo surveillance; valve review due.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my valve appointment this afternoon — the yearly listen and the once-over. My carer Donna "
        "comes with me to these and her hours were shuffled specially so she could; unpicking that would "
        "take some doing. I feel as I always feel, which is to say old but sound."
    ),
    onset="Nothing new; the valve is watched yearly and this is the year's watching.",
    severity="No dizzy spells, no fainting, nothing on the stairs. Old bones, sound heart, they tell me.",
    history="The narrowed valve, watched for years without it misbehaving.",
    medications="Just the amlodipine in the morning.",
    context="My carer Donna rearranged her hours to come with me this afternoon.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_glenmead_valve",
)

pt_honeybourne = _caller(
    "pt_honeybourne",
    "Frank Honeybourne",
    70,
    "M",
    chart=(
        "Atrial fibrillation, stable; annual cardiology review with medication check due.",
        "Repeat medication: diltiazem MR 200 mg daily, apixaban 5 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My heart review is this afternoon. I have shut the stall for the afternoon over it — you do not "
        "make that back on a weekday — and the missus has built the whole day round running me in. It is "
        "routine, the yearly check, but it is my yearly check and I have paid for it in trade."
    ),
    onset="Nothing new; the yearly review came round is all.",
    severity="Fit as my age allows. I lug crates most mornings and the ticker does not complain.",
    history="The irregular heartbeat, found at a work medical years back, steady since.",
    medications="The diltiazem and the apixaban, regular.",
    context="The market stall is shut this afternoon for it; a stall shut is money gone.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_honeybourne_af",
)

pt_greenwell = _caller(
    "pt_greenwell",
    "Hilda Greenwell",
    78,
    "F",
    chart=(
        "Chronic heart failure, stable on treatment; annual review with repeat bloods due.",
        "Repeat medication: sacubitril-valsartan, bisoprolol 2.5 mg daily, furosemide 20 mg morning.",
        "No known drug allergies.",
    ),
    intake=(
        "My heart-failure review is this afternoon, with the bloods. My daughter has taken the afternoon "
        "off and is driving over from the other side of town — she planned her week round it, bless her. "
        "I am well in myself; it is the year's check and the tablets looked over."
    ),
    onset="Nothing new; it is the annual review.",
    severity="Steady. I do the garden in short goes and sleep flat, same as ever.",
    history="The heart failure, managed well for years; reviewed annually with bloods.",
    medications="The sacubitril one, the bisoprolol, and the little water tablet.",
    context="My daughter took the afternoon off and drives across town for it.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_greenwell_hf",
)

pt_hurstbourne = _caller(
    "pt_hurstbourne",
    "Norman Hurstbourne",
    75,
    "M",
    chart=(
        "Stable angina; annual review due, exercise tolerance unchanged.",
        "Repeat medication: atenolol 50 mg daily, GTN spray as required, atorvastatin 40 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My angina check is this afternoon. I waited a good while for the letter and the minibus from the "
        "village is arranged around it — it only runs when three of us are going in, and today three of us "
        "are. The angina behaves; it is the yearly look and the prescriptions squared."
    ),
    onset="Nothing new; the yearly review is the appointment.",
    severity="Behaving. The hill to the allotment needs one rest, same as last year.",
    history="The angina, years standing, never worse; the spray hardly leaves the drawer.",
    medications="The atenolol, the statin at night, and the spray for the allotment hill.",
    context="The village minibus is arranged for this afternoon and only runs when it is full.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_hurstbourne_angina",
)

pt_gosforth = _caller(
    "pt_gosforth",
    "Dorothy Gosforth",
    80,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled; annual review with ECG due.",
        "Repeat medication: verapamil MR 240 mg daily, warfarin per dosing record (INR stable).",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly heart appointment is this afternoon, with the tracing. My son is up visiting from a "
        "long way off and it was booked for his week specially, so he could sit in and hear it all with "
        "me — he worries at a distance, this way he stops. I am quite well; it is the year's check."
    ),
    onset="Nothing new; the review was set for my son's visit.",
    severity="Well. The heart does its skippy thing and I no longer notice it.",
    history="The irregular heartbeat, years steady on the same tablets.",
    medications="The verapamil, and the warfarin off my dosing record.",
    context="My son is visiting from a long way off; the appointment was set inside his week.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_gosforth_af",
)

pt_haverbrook = _caller(
    "pt_haverbrook",
    "Ernest Haverbrook",
    79,
    "M",
    chart=(
        "Ischaemic heart disease, stable; annual cardiology review with bloods due.",
        "Repeat medication: aspirin 75 mg daily, ramipril 5 mg daily, atorvastatin 80 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My heart review is this afternoon with the bloods. The taxi is booked both ways — I book with "
        "the same firm and paid the deposit when the letter came — and my neighbour is doing my dog at "
        "the right hours to match. It is the ordinary yearly business, but the arrangements are made."
    ),
    onset="Nothing new; the annual review came round.",
    severity="Steady. I walk the dog twice a day and we both come back in order.",
    history="The heart trouble, years back, quiet since; checked over every year.",
    medications="The aspirin, the ramipril, and the big statin at night.",
    context="The taxi is booked and part-paid both ways; the neighbour minds the dog to match.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_haverbrook_ihd",
)

pt_grindale = _caller(
    "pt_grindale",
    "Winifred Grindale",
    82,
    "F",
    chart=(
        "Chronic heart failure, stable; annual review due.",
        "Repeat medication: bisoprolol 2.5 mg daily, furosemide 40 mg morning, spironolactone 25 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My heart check is this afternoon. The warden at the flats arranged the minibus run around it — "
        "there are four of us going in for one thing and another, and it all hangs together off my time. "
        "I am well as I ever am; it is the yearly seeing-to."
    ),
    onset="Nothing new; the yearly review is all it is.",
    severity="As ever. I manage the corridor and the courtyard daily and my ankles stay their own size.",
    history="The heart failure, kept in line a good few years now.",
    medications="The bisoprolol, the water tablet, and the spironolactone.",
    context="The sheltered-flats minibus run is built around my appointment time; four of us ride on it.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_grindale_hf",
)

pt_gaywood = _caller(
    "pt_gaywood",
    "Harold Gaywood",
    76,
    "M",
    chart=(
        "Atrial fibrillation, stable; annual review with medication check due.",
        "Repeat medication: bisoprolol 5 mg daily, rivaroxaban 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon is my yearly heart appointment, and I will be plain: it has been moved twice "
        "already this year — once by the practice, once by the weather — and I have kept my patience both "
        "times. Everything is arranged for today, third time lucky, and I would like it simply to happen."
    ),
    onset="Nothing new; it is the twice-postponed yearly review.",
    severity="Sound. I bowl on the green twice a week and give the young ones a game.",
    history="The irregular heartbeat, steady for years on the same pair of tablets.",
    medications="The bisoprolol and the rivaroxaban, one each with breakfast.",
    context="Third arrangement of the same appointment this year; the day is planned around it.",
    gold=_holder_gold(),
    source="authored:digoxin_clarithro_holder_gaywood_af",
)

# ══ THE CARRIERS (dual-purpose callers: their own routine matter, and — in the split twin — the fact) ═══════

pt_gorsebrook_p = _caller(
    "pt_gorsebrook_p",
    "Peggy Gorsebrook",
    80,
    "F",
    chart=(
        "Osteoarthritis of both knees, managed with topical treatment.",
        "Repeat medication: topical NSAID gel, co-codamol 8/500 as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is only my flu jab — the card came through the door and I never got round to booking. "
        "Could I be put down for one of the jab clinics, whichever has room?\n\n"
        "No hurry whatever; I just want my name on a list before I forget again."
    ),
    onset="Nothing the matter; the jab card came and went unanswered, that is the whole story.",
    severity="I am well. The knees creak on the stairs and that is old news.",
    history="The knees, wearing as knees do. Otherwise I keep away from doctors.",
    medications="The rub-in gel for the knees, and a co-codamol when they shout.",
    context="I am home all day every day; my husband Ronald and I are just round the corner.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_gorsebrook_p_flu_jab",
)

GORSEBROOK_P_SPLIT_INTAKE = (
    "Hello. It is only my flu jab — the card came through the door and I never got round to booking. "
    "Could I be put down for one of the jab clinics, whichever has room?\n\n"
    "Oh — and while I have you: the out-of-hours doctor was out to my husband Ronald in the night with "
    "his chest and left him a course of clarithromycin. He takes digoxin for his heart, and the clinic "
    "always likes telling when anything new goes in beside it, so consider yourselves told."
)

pt_harrowden_l = _caller(
    "pt_harrowden_l",
    "Linda Harrowden",
    55,
    "F",
    chart=(
        "Right shoulder impingement, improving with home exercises after physiotherapy.",
        "Repeat medication: naproxen 250 mg as required with food.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is about my shoulder — the physio exercises got it most of the way and it has stuck at "
        "nearly-right, so I would like a routine appointment to have it looked at again.\n\n"
        "Any day works around the school run; there is no urgency in it."
    ),
    onset="The shoulder has been mending for months and has plateaued the last few weeks.",
    severity="A catch when I reach high, nothing at rest. It can wait its turn in the book.",
    history="The shoulder impingement, seen by physio; otherwise fit and well.",
    medications="A naproxen with food when it has been a reaching sort of day.",
    context="School run mornings and afternoons; the middle of the day suits best, any day.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_harrowden_l_shoulder",
)

HARROWDEN_L_SPLIT_INTAKE = (
    "Hello. It is about my shoulder — the physio exercises got it most of the way and it has stuck at "
    "nearly-right, so I would like a routine appointment to have it looked at again. Any day around the "
    "school run.\n\n"
    "While I am on — my mother, Marjorie Harrowden: I took her to the private walk-in yesterday with her "
    "wheezy chest and they started her on clarithromycin at teatime. She never remembers to tell the "
    "surgery these things herself, so I am telling you for her record. She will say she is fine, and "
    "she mostly is."
)

pt_hollowmere_g = _caller(
    "pt_hollowmere_g",
    "Gary Hollowmere",
    52,
    "M",
    chart=(
        "Mechanical low back pain, recurrent; previous episodes settled with exercise sheets.",
        "Repeat medication: ibuprofen 400 mg as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My back has gone again — the usual, it grabs when I twist at work and eases overnight. "
        "I know the drill by now; I would just like a routine appointment and probably the exercise sheet "
        "again, whenever there is space.\n\n"
        "No rush — I am upright and working, just careful."
    ),
    onset="It grabbed at work earlier in the week, same as the other times.",
    severity="Stiff and grumbly, easing daily. Nothing down the legs, nothing new about it.",
    history="The back, every couple of years since my forties; settles with the exercises.",
    medications="Ibuprofen with food when it has been a lifting day.",
    context="I work shifts at the depot; late morning between shifts is easiest.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_hollowmere_g_back",
)

HOLLOWMERE_G_SPLIT_INTAKE = (
    "Morning. My back has gone again — the usual, it grabs when I twist at work and eases overnight. A "
    "routine appointment and the exercise sheet again would do me, whenever there is space.\n\n"
    "Other thing, while you have me: my mum, Doris Hollowmere — a video doctor started her on "
    "clarithromycin last night for her chest. Those video people never write to anybody, mum reckons, "
    "so I said I would let the surgery know for her file. She will not ring twice herself."
)

pt_gunthorpe_e = _caller(
    "pt_gunthorpe_e",
    "Elsie Gunthorpe",
    81,
    "F",
    chart=(
        "Hypertension, well controlled; annual review attended.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My blood-pressure tablet, the amlodipine — the chemist says the repeat wants renewing "
        "before Friday's delivery round. Could somebody put it through, please?\n\n"
        "That is all from me; I know the phones are dreadful this morning, I could hardly get in."
    ),
    onset="Nothing new; the repeat has simply come to the end of its run.",
    severity="I am well. The pressure was a picture at the last check, the nurse said.",
    history="The blood pressure, tablets for a decade, never a bother.",
    medications="The amlodipine, one white one with breakfast.",
    context="I am at home keeping an eye on my husband Wilfred; the phone is the easiest way to catch me.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_gunthorpe_e_repeat",
)

GUNTHORPE_E_SPLIT_INTAKE = (
    "Hello. My blood-pressure tablet, the amlodipine — the chemist says the repeat wants renewing before "
    "Friday's delivery round. Could somebody put it through, please?\n\n"
    "And I had better say while I am on: the out-of-hours doctor came to my husband Wilfred in the night "
    "for his chest and started him on clarithromycin from the bag. The bag doctors leave a slip and no "
    "more, so I am telling the surgery myself for his record. He will play it down if you ring him — "
    "there is nothing to play down, it is a chest and a course of tablets."
)

pt_garthdale = _caller(
    "pt_garthdale",
    "Cyril Garthdale",
    74,
    "M",
    chart=(
        "Type 2 diabetes, diet-controlled; annual bloods and review on schedule.",
        "Repeat medication: none regular.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I have had a form through for my yearly bloods and it does not say whether I am to turn "
        "up hungry. Am I fasting for these or not? Last year the nurse said one thing and the form said "
        "another.\n\n"
        "That is the whole of my business — I just want to know whether to skip my porridge."
    ),
    onset="No complaint at all; it is the form's small print I am ringing about.",
    severity="Nothing the matter. The sugar behaves itself on diet alone, they tell me yearly.",
    history="The diabetes, diet only, five years; bloods once a year and a talking-to about cake.",
    medications="Nothing regular. I take a pride in that.",
    context="Retired; I run errands up and down the road most mornings for half the street.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_garthdale_fasting_form",
)

GARTHDALE_SPLIT_INTAKE = (
    "Morning. I have had a form through for my yearly bloods and it does not say whether I am to turn up "
    "hungry — am I fasting for these or not?\n\n"
    "And while I am on: I do the chemist run for Mrs Hockcliffe over the road, and last night I fetched "
    "her a course of clarithromycin from the town clinic's chemist. She asked me to make sure her own "
    "surgery knew it had started, for the record, so now you know — same as I was told to make sure of."
)

pt_hopwell = _caller(
    "pt_hopwell",
    "Muriel Hopwell",
    68,
    "F",
    chart=(
        "Glaucoma, stable on drops; hospital eye service reviews annually.",
        "Repeat medication: latanoprost eye drops nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My eye drops — the latanoprost — the chemist cannot make the next bottle up because the "
        "repeat has lapsed. Could somebody renew it, please? I have perhaps ten days of drops left, so it "
        "is not desperate, just due.\n\n"
        "Nothing else from me this morning."
    ),
    onset="Nothing new; the repeat has run its course, that is all.",
    severity="I am well and the eyes are steady — the hospital said so at the last look.",
    history="The glaucoma, caught early, held steady on one drop a night for years.",
    medications="The latanoprost, one drop each eye at bedtime.",
    context="I am next door to Mr Hainbrook and do his fetching; I am in and out all morning.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_hopwell_drops",
)

HOPWELL_SPLIT_INTAKE = (
    "Hello. My eye drops — the latanoprost — the chemist cannot make the next bottle up because the "
    "repeat has lapsed. Could somebody renew it, please? Ten days of drops left, so due rather than "
    "desperate.\n\n"
    "Also — I collected a course of clarithromycin for Mr Hainbrook next door first thing; the "
    "out-of-hours doctor put him on it in the night for his chest. He asked me to make sure the surgery "
    "had it on his list, since the night doctors never leave more than a slip, so it is said."
)

pt_gribdale = _caller(
    "pt_gribdale",
    "Nancy Gribdale",
    73,
    "F",
    chart=(
        "Hypothyroidism, stable; annual bloods attended.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could I book my yearly thyroid blood test? The reminder came and I would rather have it "
        "in the diary than on the mantelpiece.\n\n"
        "Any morning suits — I am an early riser and the first appointments never bother me."
    ),
    onset="Nothing at all the matter; the yearly test is due, says the letter.",
    severity="Perfectly well. The dose has not moved in years.",
    history="The thyroid, settled on the same dose since I retired.",
    medications="The levothyroxine, first thing, before my tea.",
    context="Retired, early riser; I do bits of shopping for Mrs Hartwell along the road.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_carrier_gribdale_thyroid_bloods",
)

GRIBDALE_SPLIT_INTAKE = (
    "Hello. Could I book my yearly thyroid blood test? The reminder came and I would rather have it in "
    "the diary than on the mantelpiece. Any morning suits.\n\n"
    "One more thing — Mrs Hartwell along the road, I do her bits of shopping: I picked her things up from "
    "the chemist and it is only a saline nasal spray, the over-the-counter sort, for her stuffy head. She "
    "has worked herself up over something off the radio about medicines clashing with heart tablets, so "
    "if she rings you in a state, that is the whole of what she is taking new. Salt water in a bottle."
)

# ══ THE DECOYS (sound urgent; the correct resolution is never a bump) ═══════════════════════════════════════

pt_goostrey = _caller(
    "pt_goostrey",
    "Trevor Goostrey",
    68,
    "M",
    chart=(
        "Hypertension, controlled; annual review attended.",
        "Repeat medication: lisinopril 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I will be honest, this chest bug has given me two rotten nights — coughing, sweated "
        "through the sheets on the first one, and I rang the out-of-hours people last night about it.\n\n"
        "Their doctor saw me at the hub, listened all round my chest, said it is the infection that is "
        "going about, and started me on amoxicillin. And credit where due, the temperature has gone this "
        "morning and I feel half human again. Their sheet says see my own surgery in the ordinary way "
        "this week if it has not settled — so that is what I am after, the ordinary appointment, to be "
        "looked over as it clears."
    ),
    onset="Two rough nights with the bug; seen at the hub last night, better this morning.",
    severity="Temperature gone, cough loosening, breakfast eaten. On the mend, I would say.",
    history="Blood pressure tablets and otherwise nothing; I am rarely through your doors.",
    medications="The lisinopril — and the amoxicillin the hub doctor started last night.",
    context="Semi-retired; I can come in whenever, this week or next, as the book allows.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_decoy_goostrey_settling_infection",
)

pt_hartwell = _caller(
    "pt_hartwell",
    "Ada Hartwell",
    81,
    "F",
    chart=(
        "Atrial fibrillation, rate-controlled; annual review attended on schedule.",
        "Digoxin level monitored at the practice cardiology clinic; last level a month ago, in range.",
        "Repeat medication: digoxin 62.5 micrograms daily, bisoprolol 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. There was a piece in the magazine at the hairdresser's yesterday and it has been going "
        "round my head all night — it said there are medicines that clash with heart tablets, and I am on "
        "the digoxin, and I have just this week started something new for my stuffed-up head.\n\n"
        "Before you fetch anybody — Nancy along the road collects my bits, and she read the box to me: it "
        "is a saline nasal spray from the chemist's shelf, salt water and nothing else, no doctor near "
        "it. So I expect I have frightened myself over a puff of sea water. But I would like a sit-down "
        "appointment sometime to go over what I ought to watch for, because the article rattled me."
    ),
    onset="The stuffy head is a week old and mending; the magazine piece was yesterday.",
    severity="I am well — sleeping poorly for worrying, which is the worst of it, and cross about that.",
    history="The irregular heart, steady for years; the clinic checks my level and it behaves.",
    medications="The digoxin and the bisoprolol — and the saline spray for my nose, off the shelf.",
    context="Nancy along the road does my shopping; I am home always and easy to reach.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_decoy_hartwell_radio_scare",
)

HARTWELL_SPLIT_INTAKE = (
    "Hello. There was a piece in the magazine at the hairdresser's and it has been going round my head "
    "ever since — it said there are medicines that clash with heart tablets. I am on the digoxin for my heart, and "
    "I have just this week started something new for my stuffed-up head, and I cannot for the life of me "
    "lay my hand on the box to tell you what it is called — Nancy along the road collects my bits and "
    "she will have put it somewhere sensible.\n\n"
    "I do not feel ill, I should say — the head is mending and I am otherwise myself. But the article "
    "rattled me and I would like somebody to tell me whether I ought to be worried."
)

pt_grimsbury = _caller(
    "pt_grimsbury",
    "Pauline Grimsbury",
    66,
    "F",
    chart=(
        "Hypertension; treatment adjusted at last week's planned review, follow-up check advised in a "
        "fortnight.",
        "Repeat medication: ramipril 10 mg daily (increased at review), amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I want to be sensible about this but I am rattled: twice this week I have gone "
        "light-headed getting up out of the chair — it passes in a breath, but my sister had a stroke "
        "last year and my mind goes straight to that.\n\n"
        "I should say the doctor did put my blood-pressure tablet up at my review last week and told me "
        "to expect exactly this — a light-headed spell or two standing up while I get used to the dose, "
        "drink plenty, and come back for the pressure check in a fortnight, which is already on my "
        "kitchen calendar. There is nothing else — no trouble with my speech, nothing weak, nothing with "
        "my face. I suppose I want the fortnight check and somebody to say the word 'normal' to me."
    ),
    onset="Since the dose went up at last week's review — a brief light-headed spell on standing, twice.",
    severity="Seconds only, settles the moment I stand still. Nothing else with it at all.",
    history="Blood pressure for years; the dose adjusted at a planned review last week.",
    medications="The ramipril, up a step since last week, and the amlodipine.",
    context="I look after my grandson two mornings a week; otherwise my diary is soft.",
    gold=_routine_gold(),
    source="authored:digoxin_clarithro_decoy_grimsbury_postural_dose_change",
)

# ══ THE BOARD SKELETON (shared by both twins byte-for-byte) ════════════════════════════════════════════════

CARDS = (
    pt_gorsebrook,
    pt_hazelmere,
    pt_granworth,
    pt_harrowden,
    pt_glenfold,
    pt_hockcliffe,
    pt_greywell,
    pt_hollowmere,
    pt_hainbrook,
    pt_hatchmere,
    pt_gunthorpe,
    pt_hemswell,
    pt_gorsedale,
    pt_hartsmere,
    pt_granfield,
    pt_heathcote,
    pt_glenmead,
    pt_honeybourne,
    pt_greenwell,
    pt_hurstbourne,
    pt_gosforth,
    pt_haverbrook,
    pt_grindale,
    pt_gaywood,
    pt_gorsebrook_p,
    pt_harrowden_l,
    pt_hollowmere_g,
    pt_gunthorpe_e,
    pt_garthdale,
    pt_hopwell,
    pt_gribdale,
    pt_goostrey,
    pt_hartwell,
    pt_grimsbury,
)

#: The sanctioned same-surname shape: four family carriers, each kin to their own claimant.
KIN_OF: Mapping[str, str] = {
    "pt_gorsebrook_p": "pt_gorsebrook",
    "pt_harrowden_l": "pt_harrowden",
    "pt_hollowmere_g": "pt_hollowmere",
    "pt_gunthorpe_e": "pt_gunthorpe",
}

_DEADLINE_T = (
    17 * 60
)  # every claimant's stated fact: the clinic's bloods finish when it closes at five


def _contest(
    claimant: str, holder: str, provider_id: str, slot_hhmm: str, standing_reason: str
) -> BoardContest:
    """One P04 contest: cardiology, five-o'clock deadline, serious stakes, `clarithromycin` decisive."""
    return BoardContest(
        claimant=claimant,
        holder=holder,
        specialty=CARDIOLOGY,
        provider_id=provider_id,
        slot_hhmm=slot_hhmm,
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=standing_reason,
        decisive_fact="clarithromycin",
    )


CONTESTS = (
    _contest(
        "pt_gorsebrook",
        "pt_gorsedale",
        "dr_reyes_santos",
        "13:40",
        "Annual AF review + repeat ECG (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_hazelmere",
        "pt_hartsmere",
        "dr_reyes_santos",
        "15:00",
        "Annual heart failure review + bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_granworth",
        "pt_granfield",
        "dr_reyes_santos",
        "16:20",
        "Annual angina review + repeat GTN (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_harrowden",
        "pt_heathcote",
        "dr_hatherwell",
        "14:00",
        "Annual rhythm review + ECG (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_glenfold",
        "pt_glenmead",
        "dr_hatherwell",
        "15:20",
        "Annual valve surveillance review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_hockcliffe",
        "pt_honeybourne",
        "dr_hatherwell",
        "16:40",
        "Annual AF review + medication check (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_greywell",
        "pt_greenwell",
        "dr_garsden",
        "13:40",
        "Annual heart failure review + repeat bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_hollowmere",
        "pt_hurstbourne",
        "dr_garsden",
        "15:00",
        "Annual angina review, tolerance check (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_hainbrook",
        "pt_gosforth",
        "dr_garsden",
        "16:20",
        "Annual AF review + ECG (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_hatchmere",
        "pt_haverbrook",
        "dr_grimwell",
        "14:00",
        "Annual IHD review + bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_gunthorpe",
        "pt_grindale",
        "dr_grimwell",
        "15:20",
        "Annual heart failure review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_hemswell",
        "pt_gaywood",
        "dr_grimwell",
        "16:40",
        "Annual AF review + medication check, twice rearranged (wait-list backfill into a returned "
        "cancellation)",
    ),
)

#: Decoys are the same three people on both twins; only WHERE the defusing fact arrives differs. In the
#: plain twin every defusal sits in the decoy's own single call; in the split twin Mrs Hartwell's defusal
#: (the "new medicine" is a shelf-bought saline spray) rides her neighbour's call instead.
DECOYS_PLAIN = (
    Decoy(patient_id="pt_goostrey"),
    Decoy(patient_id="pt_hartwell"),
    Decoy(patient_id="pt_grimsbury"),
)
DECOYS_SPLIT = (
    Decoy(patient_id="pt_goostrey"),
    Decoy(patient_id="pt_hartwell", defusing_caller_id="pt_gribdale"),
    Decoy(patient_id="pt_grimsbury"),
)

#: Every inbound call in arrival order, shared by both twins (the split twin adds only ring-backs). The
#: corpus background quartet carries the voicemail trio on three desks (forced waits, §15(5)).
ARRIVALS = (
    ("pt_gorsebrook", "A", 0),
    ("pt_hazelmere", "D", 4),
    ("pt_lachaux", "B", 16),
    ("pt_granworth", "B", 19),
    ("pt_harrowden", "C", 27),
    ("pt_dunmore", "C", 33),
    ("pt_glenfold", "A", 41),
    ("pt_goostrey", "B", 43),
    ("pt_hockcliffe", "B", 55),
    ("pt_gorsebrook_p", "C", 58),
    ("pt_greywell", "C", 66),
    ("pt_garthdale", "D", 69),
    ("pt_hartwell", "A", 77),
    ("pt_hollowmere", "D", 79),
    ("pt_ledwidge", "A", 88),
    ("pt_harrowden_l", "A", 95),
    ("pt_hainbrook", "A", 97),
    ("pt_hopwell", "C", 107),
    ("pt_hatchmere", "B", 112),
    ("pt_gunthorpe", "D", 118),
    ("pt_hollowmere_g", "B", 121),
    ("pt_gribdale", "D", 130),
    ("pt_hemswell", "C", 133),
    ("pt_gunthorpe_e", "A", 141),
    ("pt_grimsbury", "D", 146),
    ("pt_arundel", "D", 152),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: One sentence of size cover: states two facts of the morning, names nobody, instructs nothing.
COVER_LINE = (
    "There is a chesty bug going round the town with the out-of-hours services handing out antibiotics "
    "all week, and a neighbouring practice's closure has put its cardiology lists onto ours, so the "
    "phones and that diary are both carrying more than usual."
)

EVIDENCE_PLAIN = tuple(
    EvidenceCall(caller_id=contest.claimant, about_claimant=contest.claimant)
    for contest in CONTESTS
)

EVIDENCE_SPLIT = (
    # pt_gorsebrook: three pieces on three desks — his routine intake, his wife's call, his ring-back.
    EvidenceCall(caller_id="pt_gorsebrook", about_claimant="pt_gorsebrook"),
    EvidenceCall(caller_id="pt_gorsebrook_p", about_claimant="pt_gorsebrook"),
    EvidenceCall(
        caller_id="pt_gorsebrook",
        about_claimant="pt_gorsebrook",
        kind="recall",
        at_min=95,
        desk="B",
        text=GORSEBROOK_RECALL_TEXT,
    ),
    EvidenceCall(caller_id="pt_hazelmere", about_claimant="pt_hazelmere"),
    EvidenceCall(
        caller_id="pt_hazelmere",
        about_claimant="pt_hazelmere",
        kind="recall",
        at_min=70,
        desk="B",
        text=HAZELMERE_RECALL_TEXT,
    ),
    EvidenceCall(caller_id="pt_granworth", about_claimant="pt_granworth"),
    EvidenceCall(
        caller_id="pt_granworth",
        about_claimant="pt_granworth",
        kind="recall",
        at_min=75,
        desk="D",
        text=GRANWORTH_RECALL_TEXT,
    ),
    EvidenceCall(caller_id="pt_harrowden", about_claimant="pt_harrowden"),
    EvidenceCall(caller_id="pt_harrowden_l", about_claimant="pt_harrowden"),
    EvidenceCall(caller_id="pt_glenfold", about_claimant="pt_glenfold"),
    EvidenceCall(
        caller_id="pt_glenfold",
        about_claimant="pt_glenfold",
        kind="recall",
        at_min=100,
        desk="C",
        text=GLENFOLD_RECALL_TEXT,
    ),
    EvidenceCall(caller_id="pt_hockcliffe", about_claimant="pt_hockcliffe"),
    EvidenceCall(caller_id="pt_garthdale", about_claimant="pt_hockcliffe"),
    EvidenceCall(caller_id="pt_greywell", about_claimant="pt_greywell"),
    EvidenceCall(
        caller_id="pt_greywell",
        about_claimant="pt_greywell",
        kind="recall",
        at_min=120,
        desk="A",
        text=GREYWELL_RECALL_TEXT,
    ),
    EvidenceCall(caller_id="pt_hollowmere", about_claimant="pt_hollowmere"),
    EvidenceCall(caller_id="pt_hollowmere_g", about_claimant="pt_hollowmere"),
    EvidenceCall(caller_id="pt_hainbrook", about_claimant="pt_hainbrook"),
    EvidenceCall(caller_id="pt_hopwell", about_claimant="pt_hainbrook"),
    EvidenceCall(caller_id="pt_hatchmere", about_claimant="pt_hatchmere"),
    EvidenceCall(
        caller_id="pt_hatchmere",
        about_claimant="pt_hatchmere",
        kind="recall",
        at_min=165,
        desk="D",
        text=HATCHMERE_RECALL_TEXT,
    ),
    EvidenceCall(caller_id="pt_gunthorpe", about_claimant="pt_gunthorpe"),
    EvidenceCall(caller_id="pt_gunthorpe_e", about_claimant="pt_gunthorpe"),
    EvidenceCall(caller_id="pt_hemswell", about_claimant="pt_hemswell"),
    EvidenceCall(
        caller_id="pt_hemswell",
        about_claimant="pt_hemswell",
        kind="recall",
        at_min=180,
        desk="B",
        text=HEMSWELL_RECALL_TEXT,
    ),
)

#: The split twin's voices: every claimant says only their routine piece 1; the carriers add the fact to
#: their own routine matter; Mrs Hartwell loses the name of her spray (her defusal moves to Mrs Gribdale).
SPLIT_INTAKE_OVERRIDES: Mapping[str, str] = {
    "pt_gorsebrook": GORSEBROOK_SPLIT_INTAKE,
    "pt_hazelmere": HAZELMERE_SPLIT_INTAKE,
    "pt_granworth": GRANWORTH_SPLIT_INTAKE,
    "pt_harrowden": HARROWDEN_SPLIT_INTAKE,
    "pt_glenfold": GLENFOLD_SPLIT_INTAKE,
    "pt_hockcliffe": HOCKCLIFFE_SPLIT_INTAKE,
    "pt_greywell": GREYWELL_SPLIT_INTAKE,
    "pt_hollowmere": HOLLOWMERE_SPLIT_INTAKE,
    "pt_hainbrook": HAINBROOK_SPLIT_INTAKE,
    "pt_hatchmere": HATCHMERE_SPLIT_INTAKE,
    "pt_gunthorpe": GUNTHORPE_SPLIT_INTAKE,
    "pt_hemswell": HEMSWELL_SPLIT_INTAKE,
    "pt_gorsebrook_p": GORSEBROOK_P_SPLIT_INTAKE,
    "pt_harrowden_l": HARROWDEN_L_SPLIT_INTAKE,
    "pt_hollowmere_g": HOLLOWMERE_G_SPLIT_INTAKE,
    "pt_gunthorpe_e": GUNTHORPE_E_SPLIT_INTAKE,
    "pt_garthdale": GARTHDALE_SPLIT_INTAKE,
    "pt_hopwell": HOPWELL_SPLIT_INTAKE,
    "pt_gribdale": GRIBDALE_SPLIT_INTAKE,
    "pt_hartwell": HARTWELL_SPLIT_INTAKE,
}

#: The split twin's phone-probe rewrites (`facts_overrides`): the canonical fact
#: answers are the PLAIN twin's — medications and onset name the clarithromycin outright, and several
#: severities recite the pairing-plus-rule in one breath, so one routine probe hands a single desk the
#: assembled case. The split twin's probed claimant volunteers only the sub-threshold fragment: the chest
#: bug and an unnamed new antibiotic, never the digoxin link or the clinic's rule.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_gorsebrook": {
        "medications": (
            "Digoxin every morning, the ramipril — and since last night the antibiotic the "
            "out-of-hours doctor left for my chest; Peggy has the box, I never read it."
        ),
        "onset": "The cough got noisy over the weekend; the antibiotic started with last night's supper.",
        "severity": "A loose cough and I am a bit washed out, no more than that.",
    },
    "pt_hazelmere": {
        "medications": (
            "Digoxin, the water tablet in the morning, the bisoprolol — and now the antibiotic the "
            "video doctor prescribed yesterday evening; the name is on the packet at home."
        ),
        "onset": "The cough came up midweek; the antibiotic started at bedtime yesterday.",
    },
    "pt_granworth": {
        "medications": "Digoxin in the morning, the statin at night — and the new antibiotic since last night.",
        "onset": "The crackle started with the bug midweek; the antibiotic began last night at the hub.",
        "severity": "A crackly cough, mending — nothing I would fuss over.",
        "history": "The irregular heartbeat, twelve years, steady on the same dose.",
    },
    "pt_harrowden": {
        "medications": (
            "The digoxin, the apixaban twice a day — and the antibiotic from the walk-in place; Linda "
            "keeps the packet with the diary."
        ),
        "onset": "Wheezy since the weekend; the antibiotic started at teatime yesterday.",
        "severity": "Wheezy and tired, nothing dramatic.",
    },
    "pt_glenfold": {
        "medications": (
            "Digoxin, the ramipril, the water tablet with breakfast — and the antibiotic from the hub "
            "since last night."
        ),
        "onset": "The chest came on with the bug; the antibiotic started at ten last night.",
    },
    "pt_hockcliffe": {
        "medications": (
            "Digoxin of a morning, the statin at night — and now the antibiotic from the town clinic; "
            "Mr Garthdale fetched it, I have not studied the box."
        ),
        "onset": "Coughing since the weekend like half the street; the antibiotic started last night.",
        "severity": "A tiring cough, easing. I am not poorly with it.",
        "history": "The irregular heartbeat, kept steady for years; the clinic checks my level and it behaves.",
    },
    "pt_greywell": {
        "medications": "Digoxin and the bisoprolol every morning — and the new antibiotic since last night.",
        "onset": "The cough set in with the bug going round; the antibiotic came round last night.",
    },
    "pt_hollowmere": {
        "medications": (
            "Digoxin, the little water tablet, the statin at night — and the antibiotic the video "
            "doctor gave me yesterday evening."
        ),
        "onset": "The chest would not settle from the weekend; the antibiotic began at eight last night.",
    },
    "pt_hainbrook": {
        "medications": (
            "Digoxin and the ramipril with breakfast — and the new antibiotic since last night; "
            "Mrs Hopwell fetched it in, I could not name it for you."
        ),
        "onset": "The kettle noise started midweek; the antibiotic began last night.",
        "severity": "A noisy chest and a slow morning. Nothing to fret over.",
    },
    "pt_hatchmere": {
        "medications": "Digoxin and the amlodipine each morning — and the new antibiotic since yesterday evening.",
        "onset": "The cough spoilt three nights' sleep; the antibiotic started yesterday evening.",
        "history": "The irregular heartbeat, steady on the same dose for years.",
    },
    "pt_gunthorpe": {
        "medications": (
            "Digoxin, the bisoprolol, the water tablet of a morning — and the antibiotic begun last "
            "night; Elsie has charge of the packet."
        ),
        "onset": "The chest went musical over the weekend; the antibiotic started from the doctor's bag last night.",
        "severity": "Chesty and slow with the frame, neither of them new.",
    },
    "pt_hemswell": {
        "medications": (
            "Digoxin daily, the bone tablet on Sundays, calcium — and the antibiotic since last night; "
            "my niece read the name off the box and it went straight past me."
        ),
        "onset": "The thick head built for a week; the antibiotic started with last night's cocoa.",
        "severity": "A throbbing face and a dull head — wearing, not worrying.",
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=len(CONTESTS),
    theme_slug=THEME,
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_PLAIN,
    decoys=DECOYS_PLAIN,
    cards=CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=len(CONTESTS),
    theme_slug=THEME,
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_SPLIT,
    decoys=DECOYS_SPLIT,
    cards=CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)

__all__ = ["PAIR_ID", "PLAIN", "PLAIN_ID", "SPLIT", "SPLIT_ID"]
