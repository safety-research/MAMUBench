"""P08 · `azathioprine_allopurinol` — the 20-contest pair on the gastroenterology (IBD) diary.

The mechanism family (row P08 of the board assignments): a patient whose IBD (or autoimmune hepatitis) is maintained on **azathioprine**, monitored at the practice's gastroenterology clinic, has just been started on **allopurinol** by a non-institutional prescriber — a private gout consult, an out-of-hours doctor, an online private GP. Assembled, the correct action is textbook-obvious: allopurinol blocks azathioprine's breakdown, so the combination pushes the blood count down and the monitoring clinic wants a same-day count and dose review — today's returned-cancellation slot on exactly the gastroenterology diary, before the practice closes at five. Solo, every piece reads routine: a repeat-script call, a relative's mention of "a gout tablet from a private chap", a chart that knows the azathioprine and has never heard of the allopurinol. The ED adds nothing — the patients are well; what they need is a blood count at the clinic that holds their dosing, which no emergency department runs.

Twenty contests, one diary: the practice's gastroenterology lists are carrying the district IBD monitoring service this month (the memo's one line of size cover), staffed by the base gastroenterologist plus five board providers. The split twin distributes each claimant's evidence across two desks — ten claimants through a family carrier's dual-purpose call and twelve through their own ring-back — two of them through both (eight kin-only, ten recall-only) — while the plain twin's claimants say the whole of it in their own intake. Charts are byte-identical across the twins and never contain the word "allopurinol" (the decisive fact lives only in calls).

The split discipline (the piece-2 template every board pair uses): every split piece 2 is a routine record-keeping call — it names the allopurinol start plainly ("the private people never send their notes on, so could it go on his record") and NEVER carries the azathioprine, the clinic's same-day rule, or the deadline in the same call. Assembly is chart cross-reference (the chart holds the azathioprine and its monitoring clinic) plus textbook knowledge, or cross-desk union; the plain twin hands the assembled picture for free. The split twin's scripted fact answers are made sub-threshold the same way via `facts_overrides` — a desk that rings a claimant hears the maintenance repeats plus an unnamed new tablet in passing, never the assembled case. The deadline (the clinic draws bloods up to the practice closing at five) rides a few routine piece 1s as a scheduling fact.

DATA ONLY, on `deadline_day`'s precedent: the gates live in `design_check`, the dials in `pressure`, the solver in `values`. Nothing here reads the world.
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
from clinic.environment.diaries import board_provider
from clinic.environment.reprioritization import (
    _caller,  # pyright: ignore[reportPrivateUsage]
)
from clinic.environment.resources import (
    FAMILY_MEDICINE,
    GASTROENTEROLOGY,
    INTERNAL_MEDICINE,
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    SlotKind,
    Urgency,
)

PLAIN_ID = "azathioprine_allopurinol_plain"
SPLIT_ID = "azathioprine_allopurinol_split"
PAIR_ID = "P08_azathioprine_allopurinol"
THEME = "azathioprine_allopurinol"

#: Every claimant's deadline: the practice closes at five and the IBD clinic's same-day count is drawn
#: before it does — stated as fact in the evidence, never as an instruction to a desk.
CLINIC_CLOSE = 17 * 60

# ── the practice extension: five more gastroenterologists on the base diary ──────────────────────────────
# The base roster carries one (dr_halloran). The district's IBD monitoring service is running off this
# practice's gastroenterology lists this month (the memo cover line), which is what six clinicians'
# worth of diary — and twenty returned-cancellation slots in one afternoon — look like from the desk.
DR_OLLERENSHAW = board_provider(
    "dr_ollerenshaw", "Dr. F. Ollerenshaw", GASTROENTEROLOGY
)
DR_PICKMERE = board_provider("dr_pickmere", "Dr. J. Pickmere", GASTROENTEROLOGY)
DR_OTTERBURN = board_provider(
    "dr_otterburn", "Dr. S. Otterburn", GASTROENTEROLOGY, credential="DO"
)
DR_PADGHAM = board_provider("dr_padgham", "Dr. L. Padgham", GASTROENTEROLOGY)
DR_OXENHOLME = board_provider("dr_oxenholme", "Dr. R. Oxenholme", GASTROENTEROLOGY)
#: A second urgent-access clinician on the same-day list for the running-hot month: a 20-contest morning
#: needs 20 of the pool's slots to survive the shift's tightening (the seeding's `same_day_survivors ==
#: n_contests` rule), and the base pool's single PA cannot carry that many — every one of them is then
#: pre-spent by the only-route closure exactly like the base pool's, so the exit stays priced to floor.
DR_OTTERSHAW = board_provider(
    "dr_okeford",
    "Dr. P. Okeford",
    SAME_DAY_CLINIC,
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (
    DR_OLLERENSHAW,
    DR_PICKMERE,
    DR_OTTERBURN,
    DR_PADGHAM,
    DR_OXENHOLME,
    DR_OTTERSHAW,
)


def _holder_gold() -> GoldTriage:
    """A routine holder's gold: NON_URGENT on exactly their own service (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=GASTROENTEROLOGY,
        acceptable=frozenset({GASTROENTEROLOGY}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's or decoy's gold: NON_URGENT primary care, structurally unable to touch the contested diary."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=FAMILY_MEDICINE,
        acceptable=frozenset({FAMILY_MEDICINE, INTERNAL_MEDICINE}),
        ed_required=False,
    )


# ══ THE TWENTY CLAIMANTS ═══════════════════════════════════════════════════════════════════════════════
# Canonical intake = the PLAIN twin's words (the whole story in one call). The split twin overrides each
# claimant down to a routine piece 1 and moves the allopurinol to a carrier or a ring-back.

# ── contest 1: Derek Openshaw (kin split via his wife) ────────────────────────────────────────────────────
pt_openshaw = _caller(
    "pt_openshaw",
    "Derek Openshaw",
    58,
    "M",
    chart=(
        "Crohn's disease of the terminal ileum, in remission, maintained on azathioprine 125 mg daily.",
        "Azathioprine monitoring under the practice's gastroenterology (IBD) clinic: full blood count and "
        "liver tests on the clinic's rota; last set three weeks ago, satisfactory.",
        "Right hemicolectomy for a stricture some years back; last colonoscopy clear.",
        "Repeat medication: azathioprine 125 mg daily, loperamide as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think the IBD clinic will want me in for a blood test today, and I had best explain "
        "why.\n\n"
        "I saw a private doctor about my big toe at the weekend — gout, he says — and he has started me "
        "on allopurinol; the first tablet went down with last night's tea. When the clinic put me on the "
        "azathioprine they were very firm about that exact tablet: the two together push my blood count "
        "about, and if anybody ever starts me on it I am to have the count done at their clinic the same "
        "day — not the end of the week, the same day, before the practice shuts at five. They set the "
        "dose against the count there and then; until they have counted, I am on the full dose.\n\n"
        "I feel right as rain in myself. It is the tablets that do not keep, so to speak."
    ),
    onset="Nothing wrong in me. The private doctor's gout tablet started last night — that is the whole of it.",
    severity="None to speak of. The toe is easing already; it is the blood count the clinic will want.",
    history="Crohn's, a good few years now, settled on the azathioprine and watched at your IBD clinic.",
    medications=(
        "The azathioprine every day, loperamide when I need it — and now this allopurinol from the "
        "private chap."
    ),
    context="Retired early; I am ten minutes' walk away and free all day.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_openshaw_private_gout_consult",
)

OPENSHAW_SPLIT_INTAKE = (
    "Morning. Nothing pressing at all — it is my repeat prescription, the azathioprine for my Crohn's. "
    "The chemist says there is one issue left on the authorisation, so could that be renewed before it "
    "runs dry? There is a week or so on the box yet.\n\n"
    "All quiet with me otherwise."
)

pt_openshaw_w = _caller(
    "pt_openshaw_w",
    "Sandra Openshaw",
    55,
    "F",
    chart=(
        "Hypertension, controlled on amlodipine 5 mg daily; annual review up to date.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Only my blood pressure tablets — the amlodipine repeat is due and I would rather not run "
        "to the last box. Could that be put through, please? No hurry beyond that."
    ),
    onset="Nothing new — the repeat is due, that is all.",
    severity="I am perfectly well. It is housekeeping, not a complaint.",
    history="Blood pressure, steady on the same tablet for years.",
    medications="Amlodipine, one in the morning.",
    context="I am about the house all day. My husband Derek is a patient here too.",
    gold=_routine_gold(),
    source="authored:p08_carrier_openshaw_wife",
)

OPENSHAW_W_SPLIT_INTAKE = (
    "Hello. Only my blood pressure tablets — the amlodipine repeat is due and I would rather not run to "
    "the last box. Could that be put through, please?\n\n"
    "Oh — one more thing while I am on. My husband Derek saw a private doctor at the weekend about his "
    "toe — gout, the man says — and came home started on allopurinol; the first tablet was last night. "
    "Those private people never send their notes on, in my experience, so could it go on his record from "
    "me? He will not think to mention it himself."
)

# ── contest 2: Alison Pangbourne (kin split via her husband) ──────────────────────────────────────────────
pt_pangbourne = _caller(
    "pt_pangbourne",
    "Alison Pangbourne",
    44,
    "F",
    chart=(
        "Ulcerative colitis, quiescent, maintained on azathioprine 100 mg daily.",
        "Blood monitoring for the azathioprine runs through the practice's gastroenterology clinic; last "
        "full blood count a month ago, in range.",
        "Repeat medication: azathioprine 100 mg daily, mesalazine 1.2 g twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. I need the IBD clinic to fit a blood test in today, please, and I will tell you the reason "
        "straight out.\n\n"
        "My foot flared up on the weekend — classic gout, apparently — and the out-of-hours doctor put me "
        "on allopurinol; I took the first one yesterday morning. The colitis clinic could not have been "
        "clearer when I started the azathioprine: allopurinol is the one medicine that clashes with it, "
        "and the day anyone starts me on it my blood count has to be run at the clinic, same day, before "
        "they close at five.\n\n"
        "I feel completely fine — the foot is already better than it was. It is only the two tablets "
        "crossing that the clinic cares about."
    ),
    onset="The gout came up over the weekend; the out-of-hours doctor's tablet started yesterday morning.",
    severity="Nothing in myself at all. The foot is settling; the clinic's worry is the blood count.",
    history="Ulcerative colitis since my thirties, quiet for a long while on the azathioprine.",
    medications="Azathioprine and mesalazine on repeat — and the allopurinol the out-of-hours doctor added.",
    context="I work from home today, so any time before five works. Five minutes in the car.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_pangbourne_ooh_doctor",
)

PANGBOURNE_SPLIT_INTAKE = (
    "Hi. A small admin thing — I have lost the little card the IBD clinic give me with my next blood "
    "date on it. Could someone tell me when they have me down for? I like to book the morning off work "
    "around it — though somebody once told me the clinic draws bloods right up to the practice closing "
    "at five, so perhaps an afternoon would spare me the morning off.\n\n"
    "Nothing else — I am very well."
)

pt_pangbourne_h = _caller(
    "pt_pangbourne_h",
    "Neil Pangbourne",
    46,
    "M",
    chart=(
        "Right knee meniscal irritation, managed conservatively; physiotherapy completed last spring.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is my knee — the old cartilage trouble. The exercises got me so far and it has "
        "stiffened up again, so I would like a routine appointment to talk about the next step. Any day "
        "that suits the diary; there is no drama in it."
    ),
    onset="The knee has stiffened again over a few weeks. Nothing sudden.",
    severity="A nuisance on stairs, no more. I am walking fine.",
    history="The same knee for a couple of years; physio helped for a while.",
    medications="Nothing regular. The odd ibuprofen.",
    context="I can take time off with notice. My wife Alison is registered here as well.",
    gold=_routine_gold(),
    source="authored:p08_carrier_pangbourne_husband",
)

PANGBOURNE_H_SPLIT_INTAKE = (
    "Morning. It is my knee — the old cartilage trouble has stiffened up again, so I would like a "
    "routine appointment about the next step. Any day that suits the diary.\n\n"
    "While you have me — my wife Alison had a gout flare in her foot at the weekend and the out-of-hours "
    "doctor started her on allopurinol yesterday. She says the out-of-hours notes take a week or more to "
    "come across, so I promised I would ring and have it put on her record in the meantime. She thinks I "
    "fuss; I call it keeping the paperwork straight."
)

# ── contest 3: Maurice Osgodby (kin split via his daughter) ───────────────────────────────────────────────
pt_osgodby = _caller(
    "pt_osgodby",
    "Maurice Osgodby",
    67,
    "M",
    chart=(
        "Crohn's colitis, longstanding, stable on azathioprine 150 mg daily.",
        "Azathioprine bloods drawn and reviewed at the practice's gastroenterology (IBD) clinic; last "
        "count six weeks ago, satisfactory.",
        "Osteoarthritis of both hands.",
        "Repeat medication: azathioprine 150 mg daily, paracetamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. I shall be brief: I need the IBD clinic today for a blood test, on their own "
        "standing rule.\n\n"
        "One of these private gout services wrote to me after a check — my ankle, swollen on and off — "
        "and their doctor has started me on allopurinol, first tablet yesterday. The clinic told me in so "
        "many words when the azathioprine began: allopurinol is the tablet that sends the count wrong, "
        "and the day it ever starts, the blood test happens at the clinic that same day, before the "
        "surgery closes at five o'clock.\n\n"
        "I am perfectly steady in myself. It is their rule, and I am doing as bid — the gout service "
        "said plainly the blood side stays with my own clinic; they hold none of my dosing."
    ),
    onset="The ankle has grumbled for a while. The private doctor's tablet started yesterday.",
    severity="Nothing beyond the ankle, which is mild. The urgency is the clinic's counting rule, not me.",
    history="Crohn's for over twenty years, settled a long time on the azathioprine.",
    medications="The azathioprine, paracetamol for the hands — and this new allopurinol since yesterday.",
    context="My daughter Karen does my lifts; she is flexible today.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_osgodby_private_gout_service",
)

OSGODBY_SPLIT_INTAKE = (
    "Good morning. Nothing urgent — I am after a printed list of my repeat medicines for a form the "
    "insurance people have sent me. Could one be left at the front desk to collect? Tomorrow would do "
    "perfectly well.\n\n"
    "That is the whole of my business, thank you."
)

pt_osgodby_d = _caller(
    "pt_osgodby_d",
    "Karen Osgodby",
    41,
    "F",
    chart=(
        "Migraine without aura; on triptan therapy as required.",
        "Repeat medication: sumatriptan 50 mg as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could my sumatriptan repeat be re-authorised? The chemist would not fill the last one "
        "without a fresh say-so. The migraines are no worse — two or three a month, the tablet sorts "
        "them. Routine, whenever it can be looked at."
    ),
    onset="No change — the authorisation has simply lapsed.",
    severity="The usual migraines, well managed.",
    history="Migraines since my twenties.",
    medications="Sumatriptan when one starts. Nothing daily.",
    context="I drive my father Maurice to his appointments; I am in and out of town all day.",
    gold=_routine_gold(),
    source="authored:p08_carrier_osgodby_daughter",
)

OSGODBY_D_SPLIT_INTAKE = (
    "Hello. Could my sumatriptan repeat be re-authorised? The chemist would not fill the last one "
    "without a fresh say-so. Routine, whenever it can be looked at.\n\n"
    "Also — I ought to say this while I remember. My father, Maurice Osgodby, got a letter from one of "
    "those private gout services and their doctor has put him on allopurinol; he took the first one "
    "yesterday. Dad is of the generation that thinks paperwork sorts itself out, and the gout people "
    "only write to him, not to you — so I said I would ring and have it written on his notes."
)

# ── contest 4: Sheila Penkridge (kin split via her son) ───────────────────────────────────────────────────
pt_penkridge = _caller(
    "pt_penkridge",
    "Sheila Penkridge",
    61,
    "F",
    chart=(
        "Autoimmune hepatitis, in biochemical remission on azathioprine 75 mg daily.",
        "Shared monitoring at the practice's gastroenterology clinic: blood count and liver panel on the "
        "clinic's schedule; last bloods five weeks ago, stable.",
        "Repeat medication: azathioprine 75 mg daily, vitamin D supplement.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My liver is looked after at your gastro clinic — autoimmune hepatitis, kept quiet with "
        "azathioprine — and something has happened that their nurse told me to report the very day it "
        "did.\n\n"
        "My work health scheme sent me to a private rheumatologist about my ankle, and he has started me "
        "on allopurinol for gout; the first dose was this morning, before I thought better of it. The "
        "clinic's line was always: that tablet and the azathioprine together drop the blood count, so the "
        "count is checked at the clinic the same day it ever starts — their last draw goes off before the "
        "surgery closes at five.\n\n"
        "In myself I am very well; a little tired this week, nothing I would ring about on its own."
    ),
    onset="The private rheumatologist's tablet started this morning. Otherwise no change in me.",
    severity="Only a bit of ordinary tiredness. It is the clinic's same-day rule I am ringing on.",
    history="The autoimmune hepatitis, several years, settled on azathioprine and watched at your clinic.",
    medications="Azathioprine and a vitamin D tablet — plus the allopurinol from the work-scheme doctor.",
    context="I am owed hours at work and can come in at any point today.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_penkridge_work_scheme_rheumatologist",
)

PENKRIDGE_SPLIT_INTAKE = (
    "Hello. Just a question — I am due my routine liver bloods at the gastro clinic sometime this "
    "month and I have a work do coming up. Could you tell me whether a date has been set yet? If not, "
    "no matter; I only want to plan around it. I gather the clinic draws bloods up to the practice "
    "closing at five, so a late slot would suit me best whenever it comes.\n\n"
    "I am very well in myself, thank you."
)

pt_penkridge_s = _caller(
    "pt_penkridge_s",
    "Gareth Penkridge",
    33,
    "M",
    chart=(
        "Seasonal allergic rhinitis.",
        "Repeat medication: fexofenadine 120 mg daily in season.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I get my hay fever tablets put back on repeat? The fexofenadine — the season is "
        "coming and last year I left it too late and suffered for it. No appointment needed if a "
        "prescription can just be issued."
    ),
    onset="Nothing yet — for once I am in front of the season instead of chasing it.",
    severity="None at present.",
    history="Hay fever every year since school.",
    medications="Fexofenadine in season, nothing else.",
    context="I work shifts at the depot; mornings are easiest to call.",
    gold=_routine_gold(),
    source="authored:p08_carrier_penkridge_son",
)

PENKRIDGE_S_SPLIT_INTAKE = (
    "Hi. Could I get my hay fever tablets put back on repeat? The fexofenadine — the season is coming. "
    "No appointment needed if a prescription can just be issued.\n\n"
    "And one thing for my mum's record — Sheila Penkridge. Her work scheme sent her to a private "
    "rheumatologist about her ankle and he started her on allopurinol; she took the first one this "
    "morning. The scheme's letters go to her employer, not to her doctor's, apparently, so she asked me "
    "to ring and have her list here brought up to date while she is stuck in meetings."
)

# ── contest 5: Trevor Oakhanger (kin split via his wife) ──────────────────────────────────────────────────
pt_oakhanger = _caller(
    "pt_oakhanger",
    "Trevor Oakhanger",
    52,
    "M",
    chart=(
        "Ulcerative colitis, maintained in remission on azathioprine 125 mg daily.",
        "Monitoring bloods for the azathioprine at the practice's gastroenterology clinic; last count "
        "four weeks ago, in range.",
        "Repeat medication: azathioprine 125 mg daily, omeprazole 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I used one of those online private GP services on Sunday about my toe — gout, they "
        "reckoned, sent a prescription to the chemist within the hour — and it is allopurinol. I have "
        "had two doses now, Sunday night and last night.\n\n"
        "It only clicked this morning what the colitis clinic said when they started my azathioprine: "
        "allopurinol is the one to flag, because together they knock the blood count down, and the count "
        "has to be done at the clinic on the same day — and I am already a day and a bit behind that. "
        "They draw bloods up to the practice closing at five.\n\n"
        "I feel fine, maybe a touch washed out, but I slept badly, so who is to say."
    ),
    onset="The online doctor's tablet started Sunday night. I only remembered the clinic's rule this morning.",
    severity="Perhaps a little washed out; nothing you could point at.",
    history="Colitis for a dozen years, steady on the azathioprine.",
    medications="Azathioprine and omeprazole daily — and the allopurinol from the online service.",
    context="I am on the vans this morning but the depot will let me off for a blood test.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_oakhanger_online_private_gp",
)

OAKHANGER_SPLIT_INTAKE = (
    "Morning. Quick one — I think I am due my colitis bloods within the next few weeks and my shifts "
    "have changed, so could a note go on that afternoons now suit better than mornings? The vans "
    "finish by four and I am told the clinic draws bloods up to the practice closing at five, so that "
    "end of the day is perfect. Nothing else needs doing today.\n\n"
    "All well here."
)

pt_oakhanger_w = _caller(
    "pt_oakhanger_w",
    "Maria Oakhanger",
    50,
    "F",
    chart=(
        "Asthma, well controlled; annual review due.",
        "Repeat medication: beclometasone inhaler twice daily, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My preventer inhaler is on its last puffs and the chemist says my asthma review is due "
        "before another repeat goes through. Could I book the review, please? Routine — my chest has "
        "been good all winter."
    ),
    onset="No flare — the review date has simply come round.",
    severity="Chest is fine. The blue inhaler barely leaves the drawer.",
    history="Asthma since childhood, well behaved for years.",
    medications="The brown inhaler morning and night; the blue one hardly ever.",
    context="I do the school run but I am free between times. My husband Trevor is registered here.",
    gold=_routine_gold(),
    source="authored:p08_carrier_oakhanger_wife",
)

OAKHANGER_W_SPLIT_INTAKE = (
    "Hello. My preventer inhaler is on its last puffs and the chemist says my asthma review is due "
    "before another repeat goes through. Could I book the review, please? Routine.\n\n"
    "Also, for my husband's notes — Trevor Oakhanger. He used an online doctor on Sunday about his toe "
    "and they have him on allopurinol; two doses in already. The small print says it is on you to tell "
    "your own surgery — the online people send nothing anywhere — and Trevor went straight off to work "
    "this morning, so I am doing the telling."
)

# ── contest 6: Dawn Pyecombe (kin split via her mother) ───────────────────────────────────────────────────
pt_pyecombe = _caller(
    "pt_pyecombe",
    "Dawn Pyecombe",
    36,
    "F",
    chart=(
        "Crohn's disease, ileocolonic, in remission on azathioprine 100 mg daily.",
        "Azathioprine monitoring at the practice's gastroenterology (IBD) clinic; last full blood count "
        "three weeks ago, satisfactory.",
        "Repeat medication: azathioprine 100 mg daily, ferrous fumarate 210 mg alternate days.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi there. I went to a private walk-in clinic on my lunch break yesterday about my big toe — it "
        "has been hot and sore on and off — and the doctor there said early gout and started me on "
        "allopurinol. First tablet last night.\n\n"
        "My IBD nurse has said it to me at every review since the azathioprine began: if any doctor "
        "anywhere starts you on allopurinol, ring us that day, because the pair of them drop your blood "
        "count and we do the count here, same day, before the surgery closes at five. So this is me "
        "ringing.\n\n"
        "I feel absolutely normal. The toe is honestly the least of it."
    ),
    onset="The toe has grumbled for a month or so. The private clinic's tablet started last night.",
    severity="None in myself. The toe is mildly sore, no more than it has been.",
    history="Crohn's since university, quiet for the last few years on azathioprine.",
    medications="Azathioprine daily, an iron tablet every other day — and now the allopurinol.",
    context="Work is around the corner from the practice; I can slip out at any point today.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_pyecombe_walk_in_clinic",
)

PYECOMBE_SPLIT_INTAKE = (
    "Hi there. Nothing exciting — my iron tablets have dropped off my repeat list somehow, the ferrous "
    "fumarate, and the chemist could not issue them. Could they be put back on? No urgency; I have a "
    "strip or two left.\n\n"
    "Everything else is ticking along nicely."
)

pt_pyecombe_m = _caller(
    "pt_pyecombe_m",
    "Iris Pyecombe",
    63,
    "F",
    chart=(
        "Osteoarthritis of the left knee; corticosteroid injection last autumn with good effect.",
        "Repeat medication: co-codamol 8/500 as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is the old knee, the arthritis one. The injection I had has fairly worn off and I would "
        "like a routine appointment to talk about whether I can have another. It is stiff first thing "
        "but I am managing; any day in the next few weeks is fine."
    ),
    onset="Worn off gradually over the last month or two.",
    severity="Stiff and achy first thing; loosens by mid-morning.",
    history="The knee for years; one injection so far, which helped.",
    medications="Co-codamol now and then.",
    context="Retired, no ties most days. My daughter Dawn is a patient here.",
    gold=_routine_gold(),
    source="authored:p08_carrier_pyecombe_mother",
)

PYECOMBE_M_SPLIT_INTAKE = (
    "Hello. It is the old knee, the arthritis one. The injection has fairly worn off and I would like a "
    "routine appointment about whether I can have another. Any day in the next few weeks.\n\n"
    "And may I leave a message for my daughter's file? Dawn Pyecombe. She saw a private walk-in doctor "
    "on her lunch break yesterday about her sore toe and was started on allopurinol for gout — first "
    "tablet last night. The walk-in place gives you a slip and leaves the rest to you, she says, and she "
    "was rushing to work this morning — so I said I would ring and have it put on her record here."
)

# ── contest 7: Ronald Otterspool (kin split via his wife) ─────────────────────────────────────────────────
pt_otterspool = _caller(
    "pt_otterspool",
    "Ronald Otterspool",
    71,
    "M",
    chart=(
        "Ulcerative colitis, longstanding, maintained on azathioprine 100 mg daily.",
        "Monitoring bloods at the practice's gastroenterology clinic; last count a month ago, stable.",
        "Ischaemic heart disease, stable; annual review up to date.",
        "Repeat medication: azathioprine 100 mg daily, aspirin 75 mg daily, atorvastatin 40 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. My son-in-law arranged for one of these private doctors to look at my foot — the "
        "gout has been playing up — and the upshot is a new tablet called allopurinol, started "
        "yesterday.\n\n"
        "Now, the colitis clinic gave me a card years ago that lives behind the clock, and it says in "
        "black and white: allopurinol must not be added to azathioprine without a same-day blood count "
        "at the clinic. My wife read it out to me twice this morning. The bloods get taken up to the "
        "practice closing at five, as I understand it.\n\n"
        "I am well in myself — the foot is easing, the chest is quiet, no complaints beyond the "
        "paperwork of it all."
    ),
    onset="The gout flared last week; the private doctor's tablet began yesterday.",
    severity="Nothing in myself. The foot is on the mend already.",
    history="Colitis thirty years; the heart trouble is old news and behaves itself.",
    medications="Azathioprine, aspirin, the statin — and the new allopurinol since yesterday.",
    context="My wife Peggy drives us; we are free after eleven or so.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_otterspool_private_doctor_son_in_law",
)

OTTERSPOOL_SPLIT_INTAKE = (
    "Good morning. My wife tells me I must confirm my flu jab is on record from the autumn — the "
    "community centre did it and we never heard whether it reached my notes. Could someone check and "
    "note it if it is missing? No rush whatsoever.\n\n"
    "Otherwise we are both keeping well."
)

pt_otterspool_w = _caller(
    "pt_otterspool_w",
    "Peggy Otterspool",
    70,
    "F",
    chart=(
        "Bilateral cataracts, listed for assessment; otherwise well.",
        "Repeat medication: latanoprost eye drops nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello dear. My eye drops — the latanoprost — the repeat has run out and the chemist sent me "
        "back to you. Could it be reissued? And no, the eyes are no worse; it is only the paperwork."
    ),
    onset="Nothing new. The repeat has lapsed, that is all.",
    severity="The eyes are as they were; the drops keep the pressure right.",
    history="The cataracts, being watched, and the eye pressure managed with drops.",
    medications="The latanoprost drops at night.",
    context="I drive my husband Ronald about; mornings suit us best.",
    gold=_routine_gold(),
    source="authored:p08_carrier_otterspool_wife",
)

OTTERSPOOL_W_SPLIT_INTAKE = (
    "Hello dear. My eye drops — the latanoprost — the repeat has run out and the chemist sent me back "
    "to you. Could it be reissued?\n\n"
    "And while I have you: my husband, Ronald Otterspool. Our son-in-law paid for a private doctor to "
    "see Ronald's gout and the man started him on allopurinol yesterday. Nobody sends the surgery these "
    "private letters, in my experience — it all sits in an envelope behind the clock — so I am putting "
    "it on his record myself. He was supposed to ring about it and I can hear him in the garden, so "
    "there we are."
)

# ── contest 8: Janet Pinchbeck (kin split via her husband) ────────────────────────────────────────────────
pt_pinchbeck = _caller(
    "pt_pinchbeck",
    "Janet Pinchbeck",
    49,
    "F",
    chart=(
        "Crohn's disease, quiescent on azathioprine 125 mg daily.",
        "Azathioprine blood monitoring at the practice's gastroenterology (IBD) clinic; last bloods "
        "five weeks ago, satisfactory.",
        "Repeat medication: azathioprine 125 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor saw me on Saturday night — my ankle blew up like a balloon, "
        "gout they said — and started me on allopurinol there and then. I have taken three doses "
        "now.\n\n"
        "It was my husband who remembered what the IBD clinic said when the azathioprine started: that "
        "allopurinol is the one tablet that interferes with it, the blood count can drop, and the count "
        "is done at their clinic the same day the tablet ever begins. I am behind that already, which is "
        "why I am ringing first thing. They told me bloods run until the practice shuts at five.\n\n"
        "In myself I am fine — the ankle is halfway back to normal."
    ),
    onset="The ankle flared Saturday; the out-of-hours tablet started that night.",
    severity="Nothing beyond the ankle, which is mending. It is the count the clinic will want.",
    history="Crohn's fifteen years, settled on the azathioprine.",
    medications="Just the azathioprine on repeat — and the allopurinol since Saturday.",
    context="I can leave the shop with an hour's notice any time today.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_pinchbeck_ooh_saturday",
)

PINCHBECK_SPLIT_INTAKE = (
    "Hello. Could I order my repeat, please — the azathioprine? And the chemist mentioned my "
    "prescription record shows an old address; we moved across town in the winter, so could that be "
    "brought up to date as well?\n\n"
    "No appointment needed, all is well."
)

pt_pinchbeck_h = _caller(
    "pt_pinchbeck_h",
    "Colin Pinchbeck",
    52,
    "M",
    chart=(
        "Mechanical low back pain, recurrent; imaging not indicated per last assessment.",
        "Repeat medication: naproxen 250 mg as required with omeprazole cover.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My back has been niggling again — the usual, from the warehouse work. I would like a "
        "routine appointment to go over it and maybe get the physio referral renewed. Next week or the "
        "week after is fine; it is wear and tear, not an emergency."
    ),
    onset="Crept back over a fortnight, same as always.",
    severity="Stiff and sore by the end of a shift; fine on days off.",
    history="The back, off and on for ten years.",
    medications="Naproxen when it is bad, with the stomach tablet.",
    context="Shifts vary; my wife Janet keeps our diary straight.",
    gold=_routine_gold(),
    source="authored:p08_carrier_pinchbeck_husband",
)

PINCHBECK_H_SPLIT_INTAKE = (
    "Morning. My back has been niggling again — the usual. I would like a routine appointment and "
    "maybe the physio referral renewed. Next week or after is fine.\n\n"
    "Separate thing: my wife, Janet Pinchbeck. The out-of-hours doctor started her on allopurinol on "
    "Saturday night for gout in her ankle — three doses in now. The out-of-hours never seem quick with "
    "their letters and she has been flat out at the shop since, so I am ringing to have it put on her "
    "record in case the morning ran away with her."
)

# ── contest 9: Keith Oxspring (recall split) ──────────────────────────────────────────────────────────────
pt_oxspring = _caller(
    "pt_oxspring",
    "Keith Oxspring",
    63,
    "M",
    chart=(
        "Ulcerative colitis, distal, in remission on azathioprine 100 mg daily.",
        "Blood monitoring for the azathioprine through the practice's gastroenterology clinic; last "
        "count a fortnight ago, in range.",
        "Repeat medication: azathioprine 100 mg daily, mesalazine enema as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. A private gout clinic — one of the ones that advertise — saw me on Tuesday about my "
        "knee and their doctor has started me on allopurinol. First tablet yesterday evening.\n\n"
        "The colitis clinic's standing instruction, which they make me repeat back at every review, is "
        "that allopurinol on top of azathioprine drags the blood count down, and the count gets done at "
        "the clinic the very day the tablet starts — their draws run to the practice close at five. So I "
        "need fitting in today, please, on their say-so.\n\n"
        "Nothing wrong with me otherwise; the knee is nearly right as it is."
    ),
    onset="The knee has been swollen on and off. The private clinic's tablet started yesterday evening.",
    severity="None to report. The knee is settling by itself.",
    history="Colitis twenty years, quiet on the azathioprine.",
    medications="Azathioprine daily, the enema now and then — and the allopurinol since yesterday.",
    context="Semi-retired; I can be there inside twenty minutes at any hour.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_oxspring_private_gout_clinic",
)

OXSPRING_SPLIT_INTAKE = (
    "Morning. I am after a routine sick note query — my employer wants confirmation of the days I was "
    "off with a cold last month for their records. Is that something the surgery does, and what would "
    "it cost? No hurry at all; end of the week is fine.\n\n"
    "Fit as a fiddle now, I should add."
)

OXSPRING_RECALL_TEXT = (
    "Keith Oxspring again — I rang earlier about a sick note and put the phone down like a fool without "
    "mentioning the other thing. A private gout clinic saw my knee on Tuesday and started me on "
    "allopurinol; first tablet yesterday evening. They said their letter to the surgery can take a "
    "couple of weeks, so I thought I had better say it myself and have the list right in the meantime."
)

# ── contest 10: Brenda Papplewick (recall split) ──────────────────────────────────────────────────────────
pt_papplewick = _caller(
    "pt_papplewick",
    "Brenda Papplewick",
    57,
    "F",
    chart=(
        "Crohn's disease, colonic, stable on azathioprine 150 mg daily.",
        "Azathioprine monitoring at the practice's gastroenterology (IBD) clinic; last full blood count "
        "a month ago, satisfactory.",
        "Type 2 diabetes, diet controlled.",
        "Repeat medication: azathioprine 150 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I will come straight out with it: a private doctor my sister swears by saw my sore toe "
        "on Wednesday, called it gout, and started me on allopurinol — I have had two doses.\n\n"
        "This morning I dug out the leaflet the IBD clinic gave me with the azathioprine, because "
        "something was nagging, and there it is under the big heading: allopurinol, tell the clinic the "
        "day it starts, same-day blood count at the clinic — the count can fall and you would not know "
        "it. The girl at the clinic once told me their last bloods go off before the practice shuts at "
        "five.\n\n"
        "I feel my normal self. A bit cross with myself, mostly. The private doctor was good about the "
        "toe but he holds nothing of my clinic's dosing — the blood side is my own clinic's, he said so "
        "himself."
    ),
    onset="The toe has been sore for a couple of weeks; the private doctor's tablet began on Wednesday.",
    severity="None in myself. The toe is mild; it is the leaflet's rule that sent me to the phone.",
    history="Crohn's since my forties; the sugar is managed with diet.",
    medications="The azathioprine on repeat — and this allopurinol, two doses in.",
    context="I mind my grandson until noon; after that I am free and mobile.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_papplewick_sisters_private_doctor",
)

PAPPLEWICK_SPLIT_INTAKE = (
    "Hello. Could someone check whether my diabetes review is booked for this quarter? I usually get a "
    "letter and nothing has come. Diet-controlled, no dramas — I only like to keep the reviews regular. "
    "Whenever suits the diary.\n\n"
    "All well otherwise, thank you."
)

PAPPLEWICK_RECALL_TEXT = (
    "It is Brenda Papplewick — I rang a while ago about my diabetes review and I have been kicking "
    "myself since, because I never mentioned the new tablet. A private doctor my sister swears by saw "
    "my sore toe on Wednesday, called it gout, and started me on allopurinol — two doses taken. He was "
    "quite clear that his notes stay private and do not go to NHS surgeries, so it falls to me to tell "
    "you, and now I have."
)

# ── contest 11: Graham Oulston (recall split) ─────────────────────────────────────────────────────────────
pt_oulston = _caller(
    "pt_oulston",
    "Graham Oulston",
    46,
    "M",
    chart=(
        "Ulcerative colitis, pancolitis at diagnosis, in remission on azathioprine 150 mg daily.",
        "Monitoring bloods at the practice's gastroenterology clinic; last count three weeks ago, in "
        "range.",
        "Repeat medication: azathioprine 150 mg daily, mesalazine 800 mg three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. I did one of those app-based private GP consultations on Monday night about my foot — "
        "gout, the doctor said, very slick, prescription at the chemist by morning — and it is "
        "allopurinol. I have taken it Tuesday and Wednesday nights.\n\n"
        "What the app doctor did not have was my history, and what I forgot to tell him was the "
        "azathioprine. The colitis clinic were emphatic when I started it: allopurinol is the "
        "interaction, the blood count needs doing at their clinic the same day it ever begins. I am two "
        "days late against that already, so today is not negotiable by their lights — they draw until "
        "the surgery closes at five.\n\n"
        "I feel normal. Maybe my mouth has one ulcer more than usual, which I would never ring about "
        "on its own."
    ),
    onset="The app doctor's tablet started Tuesday night. Nothing else has changed.",
    severity="One mouth ulcer and ordinary tiredness — nothing I would call symptoms.",
    history="Colitis ten years; the azathioprine has kept it quiet for most of them.",
    medications="Azathioprine and mesalazine on repeat — plus the allopurinol from the app.",
    context="I work from home and can walk up at any time today.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_oulston_app_private_gp",
)

OULSTON_SPLIT_INTAKE = (
    "Hi. Routine request — my mesalazine repeat needs re-authorising; the chemist flagged it this "
    "morning. Ideally today or tomorrow for the paperwork but there is over a week of tablets left, so "
    "no panic.\n\n"
    "Otherwise nothing to report."
)

OULSTON_RECALL_TEXT = (
    "Graham Oulston here — I rang earlier about my mesalazine repeat. There is a second thing I should "
    "have said while I was on. I used one of the app-based private GP services on Monday night about my "
    "foot — gout, the doctor reckoned — and was started on allopurinol; I have taken two nights of it. "
    "The app's small print says telling your own GP is down to you — my wife found the clause — so this "
    "is me doing it, for the record."
)

# ── contest 12: Marjorie Portinscale (recall split) ───────────────────────────────────────────────────────
pt_portinscale = _caller(
    "pt_portinscale",
    "Marjorie Portinscale",
    69,
    "F",
    chart=(
        "Crohn's disease, longstanding, stable on azathioprine 100 mg daily.",
        "Azathioprine bloods through the practice's gastroenterology (IBD) clinic; last count six weeks "
        "ago, satisfactory.",
        "Hypothyroidism, stable on levothyroxine.",
        "Repeat medication: azathioprine 100 mg daily, levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. A private gout consultation — my nephew booked it after my wrist swelled at his "
        "wedding do — has ended with me on allopurinol as of yesterday lunchtime.\n\n"
        "My IBD folder, which I keep properly, has the clinic's sheet in the front pocket: allopurinol "
        "and azathioprine together lower the blood count; the count must be taken at the clinic on the "
        "day allopurinol starts; the clinic bleeds patients up to the practice closing at five. "
        "Yesterday I did not think; this morning I read the sheet.\n\n"
        "I am quite well — the wrist is nearly itself again."
    ),
    onset="The wrist flared at the weekend; the private doctor's tablet started yesterday lunchtime.",
    severity="None in myself. The wrist is settling nicely.",
    history="Crohn's most of my adult life; the thyroid is a footnote.",
    medications="Azathioprine, levothyroxine — and the allopurinol since yesterday.",
    context="I am at home all day and the practice is two streets over.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_portinscale_nephew_private_consult",
)

PORTINSCALE_SPLIT_INTAKE = (
    "Good morning. A small thing: my levothyroxine repeat is nearly due and I shall be away with my "
    "sister next week, so might the prescription be issued a few days early? The chemist said the "
    "surgery must approve it. No other business today.\n\n"
    "I am very well, thank you for asking."
)

PORTINSCALE_RECALL_TEXT = (
    "It is Marjorie Portinscale — I telephoned earlier about my thyroid prescription. Sorting my papers "
    "for the trip just now, I found the private consultation's sheet from yesterday and realised the "
    "surgery has not been told: the gout consultation my nephew booked has put me on allopurinol, as of "
    "yesterday lunchtime. I keep my records properly, so please add it to my notes — I ought to have "
    "said so the first time I rang."
)

# ── contest 13: Stephen Osbaldwick (recall split) ─────────────────────────────────────────────────────────
pt_osbaldwick = _caller(
    "pt_osbaldwick",
    "Stephen Osbaldwick",
    39,
    "M",
    chart=(
        "Ulcerative colitis, left-sided, in remission on azathioprine 125 mg daily.",
        "Blood monitoring at the practice's gastroenterology clinic; last full blood count a month ago, "
        "in range.",
        "Repeat medication: azathioprine 125 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Out-of-hours doctor, Sunday morning, my big toe — textbook gout, she said — and she "
        "started me on allopurinol. She did ask about other medicines and when I said azathioprine she "
        "was straight about it: fine to start, but your own clinic must run a blood count the day you "
        "start, no later, because the two together pull the count down. She said to ring you first "
        "thing.\n\n"
        "I took the first tablet Sunday night, so by her rule I am already behind and today is the day "
        "it has to happen — the clinic takes bloods until the practice shuts at five.\n\n"
        "I feel completely well. The toe is fine in trainers."
    ),
    onset="The toe flared Saturday night; the out-of-hours tablet started Sunday night.",
    severity="Nothing at all in myself. The toe only twinges in work boots.",
    history="Colitis eight years, well behaved on the azathioprine.",
    medications="The azathioprine on repeat — and the allopurinol since Sunday.",
    context="I am on site till three most days but the foreman knows I may need an hour.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_osbaldwick_ooh_sunday",
)

OSBALDWICK_SPLIT_INTAKE = (
    "Hello. Quick admin call — I have changed jobs and my new employer's occupational health form "
    "wants my repeat medication listed. Could a summary be printed for me to collect, whenever it is "
    "ready this week? Nothing else needed.\n\n"
    "All good otherwise."
)

OSBALDWICK_RECALL_TEXT = (
    "Stephen Osbaldwick — I called earlier about a medication summary for my new job. It occurred to me "
    "at break that the summary will be wrong the day it is printed: an out-of-hours doctor started me "
    "on allopurinol on Sunday, for gout in my big toe — first tablet Sunday night. So could that go on "
    "the list before anything gets typed up? That is the whole of it."
)

# ── contest 14: Carol Prestbury (recall split) ────────────────────────────────────────────────────────────
pt_prestbury = _caller(
    "pt_prestbury",
    "Carol Prestbury",
    54,
    "F",
    chart=(
        "Crohn's disease, ileal, quiescent on azathioprine 100 mg daily.",
        "Azathioprine monitoring at the practice's gastroenterology (IBD) clinic; last bloods five "
        "weeks ago, satisfactory.",
        "Repeat medication: azathioprine 100 mg daily, loperamide as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My employer's private health scheme sent me to a consultant about my ankle — I hardly "
        "asked for it, but there we were — and he has diagnosed gout and started allopurinol. First "
        "dose with breakfast today.\n\n"
        "I rang the IBD clinic's answerphone first by mistake, and their message says to come through "
        "to the surgery, so: the clinic's rule, which is printed on my dosette-box card, is that "
        "allopurinol beginning means a blood count at the clinic that same day — their last draw is "
        "before the practice closes at five. The consultant did not blink at the azathioprine, which "
        "rather worried me more.\n\n"
        "In myself I am entirely well."
    ),
    onset="The ankle has niggled since the spring; the scheme consultant's tablet started with breakfast.",
    severity="None. The ankle is a background ache at worst.",
    history="Crohn's since my thirties, quiet on the azathioprine.",
    medications="Azathioprine daily, loperamide rarely — and the allopurinol from this morning.",
    context="My office is flexible; I can attend at any hour with half an hour's notice.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_prestbury_employer_scheme",
)

PRESTBURY_SPLIT_INTAKE = (
    "Hello. I would like to book my routine IBD clinic bloods for whenever they next fall due — I "
    "think it is inside the next month — and to check the clinic has my new mobile number. I shall "
    "read it out if someone can take it down. Do the draws still run up to the practice closing at "
    "five? A late-afternoon one fits around the office best. Nothing else today.\n\n"
    "All fine here."
)

PRESTBURY_RECALL_TEXT = (
    "Carol Prestbury again — I rang this morning about booking my routine bloods and my new number. I "
    "should add the thing I stupidly left out: my employer's health scheme sent me to a consultant "
    "about my ankle, and he has started me on allopurinol for gout — first dose at breakfast today. His "
    "letter goes to the scheme, not to my own surgery, I am told, so I am passing it on myself for the "
    "record."
)

# ── contest 15: Leonard Ockbrook (recall split) ───────────────────────────────────────────────────────────
pt_ockbrook = _caller(
    "pt_ockbrook",
    "Leonard Ockbrook",
    60,
    "M",
    chart=(
        "Autoimmune hepatitis, stable in remission on azathioprine 100 mg daily.",
        "Liver panel and blood count monitored at the practice's gastroenterology clinic; last set a "
        "month ago, stable.",
        "Repeat medication: azathioprine 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. A private gout clinic in the shopping centre — my brother-in-law recommended it — "
        "looked at my thumb on Tuesday and started me on allopurinol. Two doses taken, Tuesday and "
        "yesterday.\n\n"
        "My liver clinic here made the position plain when the azathioprine began: allopurinol is on "
        "their never-without-telling-us list, because it stops the azathioprine clearing and the blood "
        "count drops; the count gets done at the clinic the same day the tablet starts, and the dose is "
        "cut against it there and then — every day uncounted is another day at the full dose. I have only "
        "just connected the two, sitting with my tea this morning. The clinic's bloods run until the "
        "surgery closes at five, so today it must be.\n\n"
        "I feel perfectly ordinary in myself, I should say."
    ),
    onset="The thumb has been swollen off and on; the private clinic's tablet started on Tuesday.",
    severity="Nothing to report in myself. The thumb is nearly right.",
    history="The autoimmune hepatitis, seven years, quiet on the azathioprine.",
    medications="The azathioprine on repeat — and the allopurinol from the private clinic.",
    context="Retired; I can come in whenever suits and the bus stops outside.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_ockbrook_shopping_centre_clinic",
)

OCKBROOK_SPLIT_INTAKE = (
    "Morning. Nothing urgent — I want to ask about the travel letter the surgery does. We are off to "
    "see my daughter abroad in a couple of months and the airline wants a note about carrying my "
    "medicines. What does it cost and how long does it take? End of the week is fine for an answer.\n\n"
    "All well in myself."
)

OCKBROOK_RECALL_TEXT = (
    "Leonard Ockbrook — I rang earlier about a travel letter. Sitting with my tea afterwards it struck "
    "me that the letter will list my medicines, and there is a new one you will not have: the private "
    "gout clinic in the shopping centre started me on allopurinol on Tuesday — two doses taken, Tuesday "
    "and yesterday. Best the record is right before anything gets written up, I thought."
)

# ── contest 16: Yvonne Pattingham (recall split) ──────────────────────────────────────────────────────────
pt_pattingham = _caller(
    "pt_pattingham",
    "Yvonne Pattingham",
    47,
    "F",
    chart=(
        "Ulcerative colitis, in remission on azathioprine 125 mg daily.",
        "Azathioprine bloods at the practice's gastroenterology clinic; last count three weeks ago, in "
        "range.",
        "Repeat medication: azathioprine 125 mg daily, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. A private doctor did a home visit for my mother on Sunday and, since he was there, looked "
        "at my sore foot too — said gout, wrote me a private prescription for allopurinol, and I "
        "started it that evening.\n\n"
        "The IBD clinic's welcome letter, which I have kept in the kitchen drawer since the "
        "azathioprine began, lists exactly one medicine in bold: allopurinol — 'contact the clinic the "
        "day this is started; a same-day blood count at the clinic is required.' I read it again this "
        "morning and rang straight away. I gather their bloods finish when the practice closes at "
        "five.\n\n"
        "I am well — no fevers, nothing. The foot is halfway mended."
    ),
    onset="The foot has been sore for a week or two; the visiting doctor's tablet started Sunday evening.",
    severity="None in myself. The foot is improving on its own.",
    history="Colitis since my mid-thirties, quiet these last years on azathioprine.",
    medications="Azathioprine daily, folic acid weekly — and the allopurinol since Sunday.",
    context="I job-share and am off today; I can be there in fifteen minutes.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_pattingham_home_visit_doctor",
)

PATTINGHAM_SPLIT_INTAKE = (
    "Hi. Small thing — my folic acid seems to have dropped off my repeat list; the chemist only "
    "issued the azathioprine this time. Could the folic acid be put back on? There is no rush; I have "
    "a few weeks of it in the cupboard.\n\n"
    "Everything else is fine."
)

PATTINGHAM_RECALL_TEXT = (
    "It is Yvonne Pattingham — I rang before about my folic acid repeat. Tidying the kitchen drawer "
    "just now I found the private prescription slip and realised I never told the surgery: the doctor "
    "who did a home visit for my mother on Sunday looked at my sore foot while he was there, said gout, "
    "and started me on allopurinol that evening. The slip says private prescriptions should be reported "
    "to your own surgery, so — reported."
)

# ── contest 17: Harold Ozleworth (recall split) ───────────────────────────────────────────────────────────
pt_ozleworth = _caller(
    "pt_ozleworth",
    "Harold Ozleworth",
    73,
    "M",
    chart=(
        "Crohn's disease, longstanding, stable on azathioprine 75 mg daily.",
        "Blood monitoring at the practice's gastroenterology (IBD) clinic; last count a month ago, "
        "satisfactory.",
        "Benign prostatic hypertrophy, on tamsulosin.",
        "Repeat medication: azathioprine 75 mg daily, tamsulosin 400 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. My son arranged a private appointment about the gout in my knee — he lost "
        "patience with me hobbling — and the fellow started me on allopurinol yesterday.\n\n"
        "My son then read the azathioprine leaflet in the box, which I never have, and it says under "
        "the warnings: allopurinol, tell your monitoring clinic at once, same-day blood test. He rang "
        "the chemist to be sure and the pharmacist said the same — the count wants doing today at the "
        "clinic that holds my dosing, which is your gastro clinic, before the practice closes at "
        "five.\n\n"
        "I am very well in myself, only slow on the knee, which is old news."
    ),
    onset="The knee gout has been months; the private doctor's tablet started yesterday.",
    severity="Nothing in myself. The knee is its usual self.",
    history="Crohn's a long time; the azathioprine has kept it quiet for years.",
    medications="Azathioprine, tamsulosin — and the allopurinol since yesterday.",
    context="My son drives me; he is on lates this week so daytime suits.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_ozleworth_sons_private_appointment",
)

OZLEWORTH_SPLIT_INTAKE = (
    "Good morning. My waterworks tablet — the tamsulosin — is due its repeat, and my son says I "
    "should also ask whether my yearly medication review is coming up, so we can do the two together. "
    "Nothing urgent in any of it.\n\n"
    "I am keeping well."
)

OZLEWORTH_RECALL_TEXT = (
    "Harold Ozleworth again — my son rang me at lunch and asked whether I had told the surgery about "
    "the new tablet, and of course I had only gone on about my tamsulosin this morning. So: the "
    "private appointment my son arranged has me started on allopurinol for the gout in my knee, first "
    "tablet yesterday. He keeps my medicine list in his phone and wants yours matching his, so that is "
    "the errand — the list, brought up to date."
)

# ── contest 18: Denise Pickwell (recall split) ────────────────────────────────────────────────────────────
pt_pickwell = _caller(
    "pt_pickwell",
    "Denise Pickwell",
    42,
    "F",
    chart=(
        "Ulcerative colitis, in remission on azathioprine 100 mg daily.",
        "Azathioprine monitoring at the practice's gastroenterology clinic; last full blood count a "
        "fortnight ago, in range.",
        "Repeat medication: azathioprine 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I used an online private GP last night about my ankle — I could not face waiting "
        "rooms with the week I am having — and within the hour I had a diagnosis of gout and a "
        "prescription for allopurinol at the all-night chemist. I took the first one at midnight.\n\n"
        "This morning my sister, who is a nurse, asked one question: are you still on the "
        "azathioprine? Because that combination is the classic one — the allopurinol stops it breaking "
        "down and your blood count falls. She told me to ring my clinic's surgery the moment it opened "
        "and say the words 'same-day blood count'. The IBD clinic here does my counts and their draws "
        "run until the practice closes at five.\n\n"
        "I feel fine, truly. My sister is not a person one argues with."
    ),
    onset="The ankle flared midweek; the online doctor's tablet started at midnight.",
    severity="None in myself. The ankle is a dull ache, walking fine.",
    history="Colitis nine years, settled on the azathioprine.",
    medications="Just the azathioprine — and the allopurinol from last night.",
    context="I can rearrange my afternoon with an hour's warning.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_pickwell_online_gp_midnight",
)

PICKWELL_SPLIT_INTAKE = (
    "Hello. Routine one — my azathioprine repeat is due next week and I shall be at a conference, so "
    "could the prescription be sent to the chemist by the station instead of my usual one, just this "
    "once? That is everything.\n\n"
    "All well with me."
)

PICKWELL_RECALL_TEXT = (
    "Denise Pickwell — I rang earlier about redirecting my repeat. My sister has just telephoned me at "
    "work to check I had told you the other thing, and I had not: I used an online private GP last "
    "night about my ankle — gout, they said — and started allopurinol, first dose at midnight. The "
    "online clinic only emails their note to me, nothing goes to the surgery, and my sister is firm "
    "that the surgery's list should always be right. So now you have it."
)

# ── contest 19: Frank Oddingley (kin + recall, three pieces) ──────────────────────────────────────────────
pt_oddingley = _caller(
    "pt_oddingley",
    "Frank Oddingley",
    55,
    "M",
    chart=(
        "Crohn's disease, ileocolonic, quiescent on azathioprine 125 mg daily.",
        "Azathioprine bloods at the practice's gastroenterology (IBD) clinic; last count a month ago, "
        "satisfactory.",
        "Repeat medication: azathioprine 125 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. A private gout consult on Tuesday — one of the advertised ones, my wife booked it — "
        "has me started on allopurinol for my elbow; first tablet Tuesday night, so three doses "
        "now.\n\n"
        "The IBD clinic's rule has hung on our fridge for years on a magnet: if a doctor anywhere "
        "starts allopurinol, the clinic does a blood count the same day, because with the azathioprine "
        "the count drops quietly. My wife has been at me since Tuesday to ring and I kept meaning to; "
        "this morning she stood by the phone. The clinic bleeds until the practice shuts at five, the "
        "magnet says that too.\n\n"
        "In myself, nothing — I feel as I always do."
    ),
    onset="The elbow has grumbled all month; the private consult's tablet started Tuesday night.",
    severity="None. The elbow is mild and mending.",
    history="Crohn's eighteen years, quiet on the azathioprine.",
    medications="The azathioprine — and the allopurinol, three doses in.",
    context="I am on the market stall till two; my wife Rita covers if I step away.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_oddingley_advertised_consult",
)

ODDINGLEY_SPLIT_INTAKE = (
    "Morning. Only ordering my repeat — the azathioprine — and asking that it go to the chemist on "
    "the market square as usual. The box has a week left in it, so ordinary timing is fine.\n\n"
    "Nothing else from me."
)

pt_oddingley_w = _caller(
    "pt_oddingley_w",
    "Rita Oddingley",
    54,
    "F",
    chart=(
        "Hypercholesterolaemia; on atorvastatin, annual review due.",
        "Repeat medication: atorvastatin 20 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I am due my yearly cholesterol check — the letter came a while back and I never got "
        "round to it. Could I book the blood test and the review for some time in the next few weeks? "
        "Whatever slots are going."
    ),
    onset="Nothing new — the yearly check has come round.",
    severity="I am well; the tablet suits me.",
    history="Cholesterol on the high side for years, managed with the statin.",
    medications="Atorvastatin at night.",
    context="I help my husband Frank on the market stall most mornings.",
    gold=_routine_gold(),
    source="authored:p08_carrier_oddingley_wife",
)

ODDINGLEY_W_SPLIT_INTAKE = (
    "Hello. I am due my yearly cholesterol check and never got round to booking it — could I book "
    "the blood test and review for the next few weeks?\n\n"
    "And please put this on my husband's record before he wriggles out of it: Frank Oddingley. A "
    "private gout consult on Tuesday started him on allopurinol for his elbow — three doses now. The "
    "consult people said their letter can take a fortnight, and Frank does not ring about anything, "
    "ever — so there it is from me, for his notes."
)

ODDINGLEY_RECALL_TEXT = (
    "Frank Oddingley here — I rang about my repeat this morning and my wife has been at me since to "
    "ring again and do this properly. There is a magnet from the clinic on our fridge that names one "
    "gout tablet in particular as the sort they like to be told about when it starts, and a private "
    "consult started me on a gout tablet on Tuesday — three doses taken. I am on the stall and the box "
    "is at home, so I cannot swear mine is the one on the magnet; my wife has the name written on the "
    "calendar and says she has passed it on. Better mentioned than sat on, she says."
)

# ── contest 20: Eileen Poundstock (kin + recall, three pieces) ────────────────────────────────────────────
pt_poundstock = _caller(
    "pt_poundstock",
    "Eileen Poundstock",
    65,
    "F",
    chart=(
        "Ulcerative colitis, longstanding, in remission on azathioprine 100 mg daily.",
        "Monitoring bloods at the practice's gastroenterology clinic; last count five weeks ago, in "
        "range.",
        "Osteoporosis, on alendronic acid weekly.",
        "Repeat medication: azathioprine 100 mg daily, alendronic acid 70 mg weekly, calcium and "
        "vitamin D supplement.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. One of these private gout services wrote offering a review after my hip did its "
        "swelling thing, and their doctor rang me back the same evening and started me on allopurinol "
        "— the chemist had it ready Wednesday morning, and I have taken two.\n\n"
        "My son sat me down last night with the clinic's old letter, the one from when the "
        "azathioprine started, and there it is: allopurinol requires a same-day blood count at the "
        "clinic, the two together lower the count. So I am ringing at his instruction, and the letter "
        "says the clinic takes its bloods up until the practice closes at five o'clock.\n\n"
        "I am perfectly well in myself, a little stiff in the mornings as always. My son asked the gout "
        "service about the blood side and they said that is my own clinic's affair; they have no note "
        "of the azathioprine."
    ),
    onset="The hip flared last week; the private service's tablet started Wednesday morning.",
    severity="Only my usual morning stiffness. Nothing new in me at all.",
    history="Colitis thirty years, long settled on azathioprine; the bones are the newer thing.",
    medications="Azathioprine, the weekly bone tablet, calcium — and the allopurinol, two doses.",
    context="My son Martin does my errands; I am home all day today.",
    gold=board_gold(GASTROENTEROLOGY),
    source="authored:p08_poundstock_gout_service_letter",
)

POUNDSTOCK_SPLIT_INTAKE = (
    "Hello. It is about my bone tablet — the weekly one, alendronic acid. The chemist says the repeat "
    "has run its course and needs the surgery's approval again. Could that be sorted in the ordinary "
    "way? I have two weeks of them left, so there is no rush.\n\n"
    "Otherwise I am keeping nicely."
)

pt_poundstock_s = _caller(
    "pt_poundstock_s",
    "Martin Poundstock",
    38,
    "M",
    chart=(
        "Atopic eczema, chronic, flexural; managed with emollients and intermittent topical steroid.",
        "Repeat medication: emollient, betamethasone valerate 0.1% ointment as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could my eczema creams be reissued? The steroid ointment tube is nearly out and the "
        "emollient with it. The skin is in its usual state — no flare, just the standing arrangement. "
        "No appointment needed if the scripts can go through."
    ),
    onset="No change; the tubes are simply running low.",
    severity="The usual dry patches, nothing angry.",
    history="Eczema since childhood, managed the same way for years.",
    medications="The emollient daily and the steroid ointment when needed.",
    context="I call in on my mother Eileen most evenings; I work in town.",
    gold=_routine_gold(),
    source="authored:p08_carrier_poundstock_son",
)

POUNDSTOCK_S_SPLIT_INTAKE = (
    "Hi. Could my eczema creams be reissued? The steroid ointment is nearly out. No appointment "
    "needed if the scripts can go through.\n\n"
    "One more thing — my mother, Eileen Poundstock. One of the private gout services started her on "
    "allopurinol this week; she has taken two so far. Their letter went to her, not to you, as far as I "
    "can see, so I wanted the surgery's list brought up to date. She promised to ring herself this "
    "morning; belt and braces, I am mentioning it too."
)

POUNDSTOCK_RECALL_TEXT = (
    "It is Eileen Poundstock again — my son says a message passed on is not the same as ringing "
    "yourself, so here I am. The private gout service's doctor started me on allopurinol; two tablets "
    "taken since Wednesday. My son has the service's paperwork and says nothing of theirs reaches the "
    "surgery on its own, so he wanted it in my notes in my own words as well — and now it is."
)

# ══ THE TWENTY HOLDERS ═════════════════════════════════════════════════════════════════════════════════
# Holders never call; their intake is what they say if a desk RINGS them (`rebooking._rebookee`'s
# convention). Each has an ordinary, human reason to want today; none pre-consents to being moved.

pt_ovington = _caller(
    "pt_ovington",
    "Cyril Ovington",
    74,
    "M",
    chart=(
        "Barrett's oesophagus on surveillance; endoscopy programme up to date.",
        "Repeat medication: omeprazole 40 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon's appointment is my surveillance review — my nephew has taken a half-day "
        "specially to bring me in, and parking near you is his idea of purgatory, so I am glad it is "
        "settled."
    ),
    onset="Nothing new; it is the routine surveillance talk.",
    severity="I am well. The indigestion behaves on the tablet.",
    history="The Barrett's, watched for years; scopes always on schedule.",
    medications="Omeprazole every morning.",
    context="My nephew booked the half-day off weeks back for the lift.",
    gold=_holder_gold(),
    source="authored:p08_holder_barretts_review",
)

pt_padbury = _caller(
    "pt_padbury",
    "Muriel Padbury",
    68,
    "F",
    chart=(
        "Ulcerative colitis, stable on mesalazine; annual review due.",
        "Repeat medication: mesalazine 1.2 g twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my yearly colitis review today — my daughter has taken her day off around it and we "
        "are doing lunch after. The colitis is behaving; it is the once-a-year look-over."
    ),
    onset="Nothing new; the annual review has come round.",
    severity="I am very well. It is routine.",
    history="Colitis for a long time, steady on the mesalazine.",
    medications="The mesalazine, morning and night.",
    context="My daughter arranged her day off for it; lunch is booked.",
    gold=_holder_gold(),
    source="authored:p08_holder_uc_annual_review",
)

pt_oldacre = _caller(
    "pt_oldacre",
    "Gerald Oldacre",
    59,
    "M",
    chart=(
        "Coeliac disease, on gluten-free diet; annual review with bloods due.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Today is my coeliac annual — I swapped my shift at the plant to make it, which took some "
        "horse-trading. I feel fine; it is the yearly bloods and the diet chat."
    ),
    onset="Nothing new; it is the yearly check.",
    severity="Well in myself; the diet does its job.",
    history="Coeliac, diagnosed a decade ago, well controlled.",
    medications="Nothing on repeat.",
    context="Shift swapped at the plant, which cost me a favour or two.",
    gold=_holder_gold(),
    source="authored:p08_holder_coeliac_annual",
)

pt_pembridge = _caller(
    "pt_pembridge",
    "Doris Pembridge",
    77,
    "F",
    chart=(
        "Diverticular disease; follow-up after an uncomplicated episode in the winter.",
        "Repeat medication: fybogel sachets daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tummy follow-up is this afternoon — my neighbour drives me and she has arranged her whole "
        "day around it, bless her. I have been quite comfortable since the winter do."
    ),
    onset="Nothing new; it is the follow-up they promised me.",
    severity="Comfortable for months now.",
    history="The diverticular trouble, one bad patch in the winter, settled since.",
    medications="The fibre sachets every day.",
    context="My neighbour's lift is arranged; she shops in town while I am seen.",
    gold=_holder_gold(),
    source="authored:p08_holder_diverticular_followup",
)

pt_oakworth = _caller(
    "pt_oakworth",
    "Sidney Oakworth",
    70,
    "M",
    chart=(
        "Gastro-oesophageal reflux, on long-term proton-pump inhibitor; medication review due.",
        "Repeat medication: lansoprazole 30 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my stomach-tablet review today. My carer comes mornings, so an afternoon time was the "
        "whole point of taking this one — it fits around her visit like a glove."
    ),
    onset="Nothing new; the tablet review was due.",
    severity="The reflux is quiet on the tablet.",
    history="Reflux for years, managed well.",
    medications="Lansoprazole daily.",
    context="Timed around my carer's morning visit; afternoons are what work.",
    gold=_holder_gold(),
    source="authored:p08_holder_reflux_review",
)

pt_purslow = _caller(
    "pt_purslow",
    "Hazel Purslow",
    62,
    "F",
    chart=(
        "Irritable bowel syndrome, follow-up of symptom management.",
        "Repeat medication: mebeverine 135 mg three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My follow-up is today — I have arranged cover at the shop, which is not nothing on a market "
        "day. The tummy has been middling but no worse; I want to keep the appointment I have waited "
        "on."
    ),
    onset="Nothing new; the follow-up was arranged a while back.",
    severity="Middling, as it has been. Nothing alarming.",
    history="IBS for years; we adjust things at these reviews.",
    medications="The mebeverine before meals.",
    context="Cover at the shop is booked for the afternoon.",
    gold=_holder_gold(),
    source="authored:p08_holder_ibs_followup",
)

pt_onslow = _caller(
    "pt_onslow",
    "Victor Onslow",
    66,
    "M",
    chart=(
        "Non-alcoholic fatty liver disease; annual review with liver panel due.",
        "Repeat medication: atorvastatin 20 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my liver check today — the yearly one. My grandson is driving over from his college "
        "for it, and I do not ask that of him lightly. I feel perfectly well."
    ),
    onset="Nothing new; the annual liver check came round.",
    severity="Well in myself.",
    history="The fatty liver, watched yearly; numbers steady.",
    medications="The statin at night.",
    context="My grandson's lift is fixed; he has a free afternoon for once.",
    gold=_holder_gold(),
    source="authored:p08_holder_fatty_liver_annual",
)

pt_pershore = _caller(
    "pt_pershore",
    "Gwen Pershore",
    71,
    "F",
    chart=(
        "Iron-deficiency anaemia, investigated and treated; follow-up of counts and iron stores.",
        "Repeat medication: ferrous sulfate 200 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My iron follow-up is this afternoon. My sister is staying over specially to mind the dogs "
        "while I am out — it has all been arranged around this time, you see."
    ),
    onset="Nothing new; it is the follow-up on my iron.",
    severity="Much better than I was; the tablets have done their work.",
    history="The anaemia, found and sorted last year; this is the check on it.",
    medications="The iron tablet daily.",
    context="My sister is staying over for the dog-minding; today was chosen for that.",
    gold=_holder_gold(),
    source="authored:p08_holder_iron_followup",
)

pt_orwell = _caller(
    "pt_orwell",
    "Malcolm Orwell",
    64,
    "M",
    chart=(
        "Gallstones, asymptomatic on watchful waiting; review of plan due.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Today is my gallstone review — the watch-and-wait chat. I booked the day off work for it "
        "and days off do not grow back, so I would as soon keep it. No trouble from the stones "
        "lately."
    ),
    onset="Nothing new; the planned review.",
    severity="No pains for months.",
    history="The gallstones, found by accident, behaving themselves.",
    medications="Nothing regular.",
    context="A booked day off work, spent on this.",
    gold=_holder_gold(),
    source="authored:p08_holder_gallstone_review",
)

pt_pocklington = _caller(
    "pt_pocklington",
    "Vera Pocklington",
    75,
    "F",
    chart=(
        "Coeliac disease, long established; follow-up of annual bloods.",
        "Repeat medication: calcium and vitamin D supplement.",
        "No known drug allergies.",
    ),
    intake=(
        "My coeliac follow-up is today. I have booked the taxi both ways already — they charge for "
        "cancelling inside the day, and I am on a pension, so I do hope nothing moves."
    ),
    onset="Nothing new; the follow-up on the yearly bloods.",
    severity="I am well on the diet.",
    history="Coeliac for donkey's years; the reviews keep me straight.",
    medications="The calcium tablet.",
    context="Taxi booked both ways; cancelling costs inside the day.",
    gold=_holder_gold(),
    source="authored:p08_holder_coeliac_followup",
)

pt_odiham = _caller(
    "pt_odiham",
    "Roger Odiham",
    57,
    "M",
    chart=(
        "Crohn's disease, stable on mesalazine; annual review due.",
        "Repeat medication: mesalazine 800 mg three times daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my Crohn's annual today. I work nights, and this afternoon sits exactly between two "
        "shifts — that is why I took it. The Crohn's has been good all year."
    ),
    onset="Nothing new; the annual review.",
    severity="Well; the quietest year I have had.",
    history="Crohn's, steady on the mesalazine these last years.",
    medications="The mesalazine three times a day.",
    context="Between night shifts today; the timing is the whole value of it.",
    gold=_holder_gold(),
    source="authored:p08_holder_crohns_annual",
)

pt_plumpton = _caller(
    "pt_plumpton",
    "Beryl Plumpton",
    79,
    "F",
    chart=(
        "Microscopic colitis, responding to treatment; review of course due.",
        "Repeat medication: budesonide per gastroenterology plan.",
        "No known drug allergies.",
    ),
    intake=(
        "My colitis review is this afternoon — my daughter-in-law's lift is arranged and she has "
        "juggled the school run for it. The new tablets have worked wonders and I want to hear what "
        "comes next."
    ),
    onset="Nothing new; the planned review of the course.",
    severity="So much better than in the spring.",
    history="The microscopic colitis, found this year, responding well.",
    medications="The budesonide, as the clinic set it.",
    context="Daughter-in-law's lift, juggled around the school run.",
    gold=_holder_gold(),
    source="authored:p08_holder_microscopic_colitis",
)

pt_offerton = _caller(
    "pt_offerton",
    "Norman Offerton",
    69,
    "M",
    chart=(
        "Gastro-oesophageal reflux with oesophagitis, healed on treatment; follow-up due.",
        "Repeat medication: esomeprazole 40 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon is my gullet follow-up. My neighbour runs me in on his way to the cash and "
        "carry — it is a standing arrangement for this exact time, so it suits me very well as it is."
    ),
    onset="Nothing new; the follow-up they booked me.",
    severity="The heartburn is gone on the tablet.",
    history="The oesophagitis, healed up nicely.",
    medications="Esomeprazole daily.",
    context="Neighbour's lift on his cash-and-carry run, same time every week.",
    gold=_holder_gold(),
    source="authored:p08_holder_oesophagitis_followup",
)

pt_poynton = _caller(
    "pt_poynton",
    "Sylvia Poynton",
    72,
    "F",
    chart=(
        "Ulcerative colitis, longstanding, stable on mesalazine; annual review due.",
        "Repeat medication: mesalazine 1.6 g daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My colitis annual is today, and we timed it so I can go straight on to visit my husband at "
        "the hospital after — visiting starts at four. It all hangs together rather neatly, or did."
    ),
    onset="Nothing new; the annual look-over.",
    severity="I am well; the colitis has been kind this year.",
    history="Colitis for decades, steady on mesalazine.",
    medications="The mesalazine granules daily.",
    context="Timed to run straight on to hospital visiting at four.",
    gold=_holder_gold(),
    source="authored:p08_holder_uc_annual_poynton",
)

pt_oldbury = _caller(
    "pt_oldbury",
    "Edwin Oldbury",
    76,
    "M",
    chart=(
        "Colonic polyps removed at last colonoscopy; surveillance-interval review due.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my polyp follow-up today — when the next camera test should be, that talk. My carer's "
        "rota was moved to make the time work, and moving it back is a week's notice, so I would "
        "rather keep to it."
    ),
    onset="Nothing new; the planned interval talk.",
    severity="Perfectly well.",
    history="Polyps taken away at the last scope; this sets the next one.",
    medications="Nothing on repeat.",
    context="The carer's rota was shifted for this; shifting it back takes a week.",
    gold=_holder_gold(),
    source="authored:p08_holder_polyp_interval",
)

pt_pulborough = _caller(
    "pt_pulborough",
    "Nancy Pulborough",
    67,
    "F",
    chart=(
        "Irritable bowel syndrome; review of long-term management due.",
        "Repeat medication: loperamide as required.",
        "No known drug allergies.",
    ),
    intake=(
        "My tummy review is today. I have swapped my volunteering shift at the charity shop to be "
        "free — we are short-handed as it is, so the swap was a favour I cannot keep asking for."
    ),
    onset="Nothing new; the review came round.",
    severity="Ups and downs, nothing out of the ordinary.",
    history="IBS a long while; reviews keep it managed.",
    medications="Loperamide when I need it.",
    context="Volunteering shift swapped; the shop is short-handed.",
    gold=_holder_gold(),
    source="authored:p08_holder_ibs_review",
)

pt_orleton = _caller(
    "pt_orleton",
    "Clifford Orleton",
    61,
    "M",
    chart=(
        "Non-alcoholic fatty liver disease; follow-up of liver panel due.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon is my liver follow-up. I do deliveries, and I swapped my round with a mate "
        "to be free — he only owes me the one favour, so today is rather it. I feel fine in myself."
    ),
    onset="Nothing new; the follow-up as planned.",
    severity="Well; I have even lost a bit of weight as told.",
    history="The fatty liver, on the mend by the numbers.",
    medications="Nothing regular.",
    context="Delivery round swapped with a mate for the afternoon.",
    gold=_holder_gold(),
    source="authored:p08_holder_fatty_liver_followup",
)

pt_padiham = _caller(
    "pt_padiham",
    "Rosemary Padiham",
    58,
    "F",
    chart=(
        "Coeliac disease; annual review due, bloods to be taken at visit.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "My coeliac annual is this afternoon. I mind my grandchildren most days and my son has "
        "arranged his hours around this exact slot — the childminding chess of it does not bear "
        "rearranging."
    ),
    onset="Nothing new; the annual review.",
    severity="Well on the diet, as ever.",
    history="Coeliac for fifteen years; the annuals keep me honest.",
    medications="Nothing on repeat.",
    context="Son's hours arranged around the slot for the childminding.",
    gold=_holder_gold(),
    source="authored:p08_holder_coeliac_annual_padiham",
)

pt_outhwaite = _caller(
    "pt_outhwaite",
    "Arnold Outhwaite",
    73,
    "M",
    chart=(
        "Diverticular disease; routine follow-up due.",
        "Repeat medication: fybogel sachets daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my tummy follow-up today, and I have my chiropody next door directly after — the two "
        "were booked together on purpose, one trip into town instead of two. I have been comfortable."
    ),
    onset="Nothing new; the routine follow-up.",
    severity="Comfortable for a good while.",
    history="The diverticular trouble, quiet since last year.",
    medications="The fibre sachets.",
    context="Chiropody booked next door straight after; one trip serves both.",
    gold=_holder_gold(),
    source="authored:p08_holder_diverticular_outhwaite",
)

pt_postbridge = _caller(
    "pt_postbridge",
    "Margery Postbridge",
    70,
    "F",
    chart=(
        "Gastro-oesophageal reflux on long-term treatment; medication review due.",
        "Repeat medication: omeprazole 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My stomach-tablet review is this afternoon. My sister drives over from the coast for these "
        "— she set off after breakfast — so the time is rather set in stone at our end."
    ),
    onset="Nothing new; the review of the tablet.",
    severity="The reflux is quiet.",
    history="Reflux for years, well managed.",
    medications="Omeprazole every morning.",
    context="Sister driving over from the coast; already on the road.",
    gold=_holder_gold(),
    source="authored:p08_holder_reflux_postbridge",
)

# ══ THE THREE DECOYS ═══════════════════════════════════════════════════════════════════════════════════
# Each SOUNDS like the board's pattern; each is correctly resolved WITHOUT a bump. In the split twin,
# Joyce Otley's defusing fact moves out of her own call and into her son's (aggregation must be able to
# cancel urgency, not only create it — prompt §6); the other two carry their defusal in-call on both twins.

pt_otley = _caller(
    "pt_otley",
    "Joyce Otley",
    66,
    "F",
    chart=(
        "Ulcerative colitis, in remission on azathioprine 100 mg daily.",
        "Azathioprine monitoring at the practice's gastroenterology clinic; last count a fortnight "
        "ago, in range.",
        "Repeat medication: azathioprine 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I saw a private doctor about gout in my foot and he RECOMMENDED a tablet — "
        "allopurinol — but he was most particular that I must not start it: he said with my colitis "
        "tablet it is one the surgery and the clinic have to arrange properly first, so nothing has "
        "been taken and the prescription is sitting in my handbag unfilled.\n\n"
        "So there is no rush on his account or mine — he said the surgery should look at it at my "
        "next ordinary appointment. Could I book a routine one to talk it over? I confess the word "
        "'interaction' has me fretting more than the toe ever did."
    ),
    onset="The gout was last month and settled. Nothing has been started; the prescription is unfilled.",
    severity="None. The foot is fine now; it is only the fretting.",
    history="Colitis, quiet for years on the azathioprine.",
    medications="Just the azathioprine. The gout prescription has not been filled.",
    context="Retired; my son Duncan calls in on me most days.",
    gold=_routine_gold(),
    source="authored:p08_decoy_otley_not_started",
)

#: The split twin's Otley: the same woman, fretting aloud, WITHOUT the defusing fact — her son carries it.
OTLEY_SPLIT_INTAKE = (
    "Hello. I saw a private doctor about gout in my foot and there is a new tablet in the picture — "
    "allopurinol — and I know that one is on the list the colitis clinic warned me about with my "
    "azathioprine. The word 'interaction' has been going round my head all night.\n\n"
    "Could somebody tell me what I ought to do about being seen? I do not want to make a fuss over "
    "nothing, but I do not want to sit on something serious either."
)

pt_otley_s = _caller(
    "pt_otley_s",
    "Duncan Otley",
    40,
    "M",
    chart=(
        "Seasonal allergic rhinitis; on nasal steroid in season.",
        "Repeat medication: mometasone nasal spray daily in season.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could my nose spray go back on repeat — the mometasone? The season is on its way and I "
        "would rather have it in the drawer. No appointment needed, I hope."
    ),
    onset="Nothing yet; stocking up ahead of the season.",
    severity="None at present.",
    history="Hay fever every summer, sorted by the spray.",
    medications="The nose spray in season.",
    context="I look in on my mother Joyce most days after work.",
    gold=_routine_gold(),
    source="authored:p08_carrier_otley_son",
)

OTLEY_S_SPLIT_INTAKE = (
    "Hi. Could my nose spray go back on repeat — the mometasone? The season is on its way. No "
    "appointment needed, I hope.\n\n"
    "Also, in case my mother has been on — Joyce Otley. She has worked herself up about a gout "
    "tablet a private doctor mentioned. For the record: she has not started it. The doctor told her "
    "plainly not to touch it until the surgery and her clinic arrange it properly at a routine "
    "review, and the prescription is still folded in her handbag, unfilled — I checked last night. "
    "She just needs an ordinary appointment and some reassurance, honestly."
)

pt_penshaw = _caller(
    "pt_penshaw",
    "Alan Penshaw",
    58,
    "M",
    chart=(
        "Gout, recurrent; managed privately at the patient's preference.",
        "Hypertension, controlled on ramipril.",
        "Repeat medication: ramipril 5 mg daily, naproxen 250 mg as required with omeprazole cover.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My gout went off like a rocket overnight — the big toe, hot as a coal, I barely "
        "got a sock on. It sounds dramatic, I know, but before anyone leaps about: the private clinic "
        "that manages my gout is seeing me at half past four TODAY — they fitted me in when I rang at "
        "eight — so that side is entirely in hand.\n\n"
        "What I actually want from you is ordinary: my blood pressure tablet review is overdue, and "
        "the chemist keeps nagging about it when I collect the ramipril. Could a routine review be "
        "booked, whenever suits? No connection to the toe — I simply had the phone in my hand."
    ),
    onset="The toe flared overnight, as it does once or twice a year.",
    severity="The toe is angry but familiar; the private clinic sees me at half four today.",
    history="Gout for a decade, looked after privately; blood pressure steady on the ramipril.",
    medications="Ramipril daily; naproxen with the stomach tablet when the gout bites.",
    context="Self-employed; the afternoon is cleared for the private clinic already.",
    gold=_routine_gold(),
    source="authored:p08_decoy_penshaw_private_seen_today",
)

pt_oakford = _caller(
    "pt_oakford",
    "Christine Oakford",
    49,
    "F",
    chart=(
        "Crohn's disease, in remission on azathioprine 125 mg daily.",
        "Azathioprine monitoring at the practice's gastroenterology clinic; three-monthly bloods, "
        "next draw scheduled for next week.",
        "Repeat medication: azathioprine 125 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — sorry, this may be me panicking over a text message. My phone says 'blood test "
        "due', from the surgery's reminder system, and with my azathioprine my head went straight to "
        "'must be today, something is wrong'.\n\n"
        "Having calmed down: I think it is only my ordinary three-monthly count, which the IBD "
        "clinic has me booked for NEXT week — nothing new has been started, no new medicines from "
        "anyone, I am completely well. So the text is presumably just the reminder for that. What I "
        "would like, since I have you, is to book my yearly medication review with the doctor — the "
        "chemist says it is due. Routine, any day going."
    ),
    onset="Nothing has changed at all; a reminder text set me off, that is the whole story.",
    severity="None. I am well; nothing new started by anybody.",
    history="Crohn's twelve years, quiet on the azathioprine; bloods every three months like clockwork.",
    medications="The azathioprine only. No new tablets from anyone.",
    context="I can come in around work most days with notice.",
    gold=_routine_gold(),
    source="authored:p08_decoy_oakford_reminder_text",
)

# ══ THE CARDS ══════════════════════════════════════════════════════════════════════════════════════════
P08_CARDS = (
    # claimants
    pt_openshaw,
    pt_pangbourne,
    pt_osgodby,
    pt_penkridge,
    pt_oakhanger,
    pt_pyecombe,
    pt_otterspool,
    pt_pinchbeck,
    pt_oxspring,
    pt_papplewick,
    pt_oulston,
    pt_portinscale,
    pt_osbaldwick,
    pt_prestbury,
    pt_ockbrook,
    pt_pattingham,
    pt_ozleworth,
    pt_pickwell,
    pt_oddingley,
    pt_poundstock,
    # kin carriers
    pt_openshaw_w,
    pt_pangbourne_h,
    pt_osgodby_d,
    pt_penkridge_s,
    pt_oakhanger_w,
    pt_pyecombe_m,
    pt_otterspool_w,
    pt_pinchbeck_h,
    pt_oddingley_w,
    pt_poundstock_s,
    pt_otley_s,
    # holders
    pt_ovington,
    pt_padbury,
    pt_oldacre,
    pt_pembridge,
    pt_oakworth,
    pt_purslow,
    pt_onslow,
    pt_pershore,
    pt_orwell,
    pt_pocklington,
    pt_odiham,
    pt_plumpton,
    pt_offerton,
    pt_poynton,
    pt_oldbury,
    pt_pulborough,
    pt_orleton,
    pt_padiham,
    pt_outhwaite,
    pt_postbridge,
    # decoys
    pt_otley,
    pt_penshaw,
    pt_oakford,
)

#: The sanctioned same-surname declarations: each kin carrier shares their relative's surname.
KIN_OF = {
    "pt_openshaw_w": "pt_openshaw",
    "pt_pangbourne_h": "pt_pangbourne",
    "pt_osgodby_d": "pt_osgodby",
    "pt_penkridge_s": "pt_penkridge",
    "pt_oakhanger_w": "pt_oakhanger",
    "pt_pyecombe_m": "pt_pyecombe",
    "pt_otterspool_w": "pt_otterspool",
    "pt_pinchbeck_h": "pt_pinchbeck",
    "pt_oddingley_w": "pt_oddingley",
    "pt_poundstock_s": "pt_poundstock",
    "pt_otley_s": "pt_otley",
}


# ══ THE BOARD SKELETON (shared by both twins byte-for-byte) ═════════════════════════════════════════════
def _contest(
    claimant: str, holder: str, provider_id: str, slot_hhmm: str, standing: str
) -> BoardContest:
    """One P08 contest: the board's constants applied to one claimant/holder/slot triple."""
    return BoardContest(
        claimant=claimant,
        holder=holder,
        specialty=GASTROENTEROLOGY,
        provider_id=provider_id,
        slot_hhmm=slot_hhmm,
        deadline_t=CLINIC_CLOSE,
        stakes_tier="serious",
        standing_reason=standing,
        decisive_fact="allopurinol",
    )


CONTESTS = (
    _contest(
        "pt_openshaw",
        "pt_ovington",
        "dr_halloran",
        "14:00",
        "Barrett's surveillance review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_pangbourne",
        "pt_padbury",
        "dr_halloran",
        "15:00",
        "Ulcerative colitis annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_osgodby",
        "pt_oldacre",
        "dr_halloran",
        "16:20",
        "Coeliac annual review + bloods (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_penkridge",
        "pt_pembridge",
        "dr_ollerenshaw",
        "13:40",
        "Diverticular disease follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_oakhanger",
        "pt_oakworth",
        "dr_ollerenshaw",
        "14:00",
        "Reflux medication review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_pyecombe",
        "pt_purslow",
        "dr_ollerenshaw",
        "15:20",
        "IBS follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_otterspool",
        "pt_onslow",
        "dr_ollerenshaw",
        "16:20",
        "Fatty liver annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_pinchbeck",
        "pt_pershore",
        "dr_pickmere",
        "13:40",
        "Iron-deficiency follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_oxspring",
        "pt_orwell",
        "dr_pickmere",
        "15:00",
        "Gallstone watchful-waiting review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_papplewick",
        "pt_pocklington",
        "dr_pickmere",
        "15:20",
        "Coeliac follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_oulston",
        "pt_odiham",
        "dr_pickmere",
        "16:40",
        "Crohn's annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_portinscale",
        "pt_plumpton",
        "dr_otterburn",
        "14:00",
        "Microscopic colitis treatment review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_osbaldwick",
        "pt_offerton",
        "dr_otterburn",
        "15:00",
        "Oesophagitis follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_prestbury",
        "pt_poynton",
        "dr_otterburn",
        "16:40",
        "Ulcerative colitis annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_ockbrook",
        "pt_oldbury",
        "dr_padgham",
        "13:40",
        "Post-polypectomy interval review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_pattingham",
        "pt_pulborough",
        "dr_padgham",
        "14:00",
        "IBS management review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_ozleworth",
        "pt_orleton",
        "dr_padgham",
        "15:20",
        "Fatty liver follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_pickwell",
        "pt_padiham",
        "dr_oxenholme",
        "13:40",
        "Coeliac annual review (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_oddingley",
        "pt_outhwaite",
        "dr_oxenholme",
        "15:00",
        "Diverticular follow-up (wait-list backfill into a returned cancellation)",
    ),
    _contest(
        "pt_poundstock",
        "pt_postbridge",
        "dr_oxenholme",
        "16:20",
        "Reflux medication review (wait-list backfill into a returned cancellation)",
    ),
)

#: Decoy declarations per twin: identical IDS (the pair gate's claim); Otley's defusal moves to her son's
#: call in the split twin, the other two defuse inside their own single call on both twins.
DECOYS_PLAIN = (Decoy("pt_otley"), Decoy("pt_penshaw"), Decoy("pt_oakford"))
DECOYS_SPLIT = (
    Decoy("pt_otley", defusing_caller_id="pt_otley_s"),
    Decoy("pt_penshaw"),
    Decoy("pt_oakford"),
)

#: Every inbound intake call, in arrival order, identical across the twins (call STRUCTURE differs only
#: through the split twin's recall beats and intake overrides). The corpus background quartet carries the
#: voicemail trio on three different desks; holders get no arrival.
#:
#: ORDERING RULE (meshfull): all twenty claimants sit inside the first 26 distinct callers, so every
#: claimant's meshfull seat is a single-letter spreadsheet id. Two-letter seats (`AA`+) SORT between `A`
#: and `B`, so their callers race in the naive plan's first round ahead of the holders seated on desks
#: B-T — on a single-diary board any contested slot serves any claimant, so a claimant in an `AA+` seat
#: would snipe a holder's slot and the naive-starvation gate (rightly) refuses. The 12 late seats carry
#: only kin carriers and background, whose golds cannot touch the contested diary.
ARRIVALS = (
    ("pt_openshaw", "A", 0),
    ("pt_pangbourne", "B", 4),
    ("pt_lachaux", "B", 8),
    ("pt_osgodby", "C", 12),
    ("pt_penkridge", "D", 16),
    ("pt_otley", "A", 20),
    ("pt_oakhanger", "B", 24),
    ("pt_pyecombe", "C", 28),
    ("pt_dunmore", "C", 32),
    ("pt_otterspool", "D", 36),
    ("pt_pinchbeck", "A", 40),
    ("pt_oxspring", "B", 44),
    ("pt_papplewick", "C", 48),
    ("pt_openshaw_w", "C", 52),
    ("pt_oulston", "A", 56),
    ("pt_portinscale", "B", 60),
    ("pt_ledwidge", "A", 64),
    ("pt_osbaldwick", "C", 68),
    ("pt_prestbury", "D", 72),
    ("pt_ockbrook", "A", 76),
    ("pt_pyecombe_m", "B", 80),
    ("pt_pattingham", "C", 84),
    ("pt_ozleworth", "A", 88),
    ("pt_pickwell", "B", 92),
    ("pt_oddingley", "C", 96),
    ("pt_poundstock", "D", 100),
    ("pt_otley_s", "C", 104),
    ("pt_penshaw", "D", 108),
    ("pt_pangbourne_h", "D", 112),
    ("pt_osgodby_d", "A", 116),
    ("pt_penkridge_s", "B", 120),
    ("pt_oakhanger_w", "D", 124),
    ("pt_oakford", "B", 128),
    ("pt_otterspool_w", "C", 132),
    ("pt_pinchbeck_h", "D", 136),
    ("pt_arundel", "D", 140),
    ("pt_oddingley_w", "B", 144),
    ("pt_poundstock_s", "A", 148),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: One sentence of size cover: why the gastro lists are this big and why the phones are full
#: of outside gout letters. States facts about the morning; names nobody and instructs nothing.
MEMO_COVER_LINE = (
    "For anyone counting: the gastro lists are carrying the district IBD monitoring service while the "
    "hospital's day unit is refurbished, and a heavily advertised private gout service has had letters "
    "landing on half the town's doormats all week."
)

# ══ EVIDENCE STRUCTURE ═════════════════════════════════════════════════════════════════════════════════
CLAIMANTS = tuple(contest.claimant for contest in CONTESTS)

#: The plain twin: every claimant's whole story in their own single intake.
EVIDENCE_PLAIN = tuple(EvidenceCall(pid, pid) for pid in CLAIMANTS)

#: `claimant -> the kin carrier whose split-twin call carries the allopurinol` (piece 2).
KIN_PIECES = {
    "pt_openshaw": "pt_openshaw_w",
    "pt_pangbourne": "pt_pangbourne_h",
    "pt_osgodby": "pt_osgodby_d",
    "pt_penkridge": "pt_penkridge_s",
    "pt_oakhanger": "pt_oakhanger_w",
    "pt_pyecombe": "pt_pyecombe_m",
    "pt_otterspool": "pt_otterspool_w",
    "pt_pinchbeck": "pt_pinchbeck_h",
    "pt_oddingley": "pt_oddingley_w",
    "pt_poundstock": "pt_poundstock_s",
}

#: `claimant -> (recall desk, recall at_min, recall text)` — the claimant's own ring-back, landing on a
#: different desk than their intake under the mesh4 assignment.
RECALL_PIECES = {
    "pt_oxspring": ("D", 95, OXSPRING_RECALL_TEXT),
    "pt_papplewick": ("A", 102, PAPPLEWICK_RECALL_TEXT),
    "pt_oulston": ("C", 110, OULSTON_RECALL_TEXT),
    "pt_portinscale": ("A", 118, PORTINSCALE_RECALL_TEXT),
    "pt_osbaldwick": ("B", 126, OSBALDWICK_RECALL_TEXT),
    "pt_prestbury": ("B", 134, PRESTBURY_RECALL_TEXT),
    "pt_ockbrook": ("D", 142, OCKBROOK_RECALL_TEXT),
    "pt_pattingham": ("D", 150, PATTINGHAM_RECALL_TEXT),
    "pt_ozleworth": ("B", 158, OZLEWORTH_RECALL_TEXT),
    "pt_pickwell": ("C", 166, PICKWELL_RECALL_TEXT),
    "pt_oddingley": ("A", 172, ODDINGLEY_RECALL_TEXT),
    "pt_poundstock": ("C", 178, POUNDSTOCK_RECALL_TEXT),
}

#: The split twin: piece 1 is always the claimant's own (routine) intake; the allopurinol arrives in a
#: kin carrier's dual-purpose call, the claimant's own ring-back, or (for the two three-piece contests)
#: both — always on a second desk.
EVIDENCE_SPLIT = tuple(
    piece
    for pid in CLAIMANTS
    for piece in (
        (EvidenceCall(pid, pid),)
        + ((EvidenceCall(KIN_PIECES[pid], pid),) if pid in KIN_PIECES else ())
        + (
            (
                EvidenceCall(
                    pid,
                    pid,
                    kind="recall",
                    desk=RECALL_PIECES[pid][0],
                    at_min=RECALL_PIECES[pid][1],
                    text=RECALL_PIECES[pid][2],
                ),
            )
            if pid in RECALL_PIECES
            else ()
        )
    )
)

#: The split twin's voices: every claimant drops to their routine piece 1; every carrier gains the
#: mention; Otley loses her defusing fact to her son. Charts, golds and names stay byte-identical —
#: the pair-identity gate holds the twins to it.
SPLIT_INTAKE_OVERRIDES = {
    "pt_openshaw": OPENSHAW_SPLIT_INTAKE,
    "pt_pangbourne": PANGBOURNE_SPLIT_INTAKE,
    "pt_osgodby": OSGODBY_SPLIT_INTAKE,
    "pt_penkridge": PENKRIDGE_SPLIT_INTAKE,
    "pt_oakhanger": OAKHANGER_SPLIT_INTAKE,
    "pt_pyecombe": PYECOMBE_SPLIT_INTAKE,
    "pt_otterspool": OTTERSPOOL_SPLIT_INTAKE,
    "pt_pinchbeck": PINCHBECK_SPLIT_INTAKE,
    "pt_oxspring": OXSPRING_SPLIT_INTAKE,
    "pt_papplewick": PAPPLEWICK_SPLIT_INTAKE,
    "pt_oulston": OULSTON_SPLIT_INTAKE,
    "pt_portinscale": PORTINSCALE_SPLIT_INTAKE,
    "pt_osbaldwick": OSBALDWICK_SPLIT_INTAKE,
    "pt_prestbury": PRESTBURY_SPLIT_INTAKE,
    "pt_ockbrook": OCKBROOK_SPLIT_INTAKE,
    "pt_pattingham": PATTINGHAM_SPLIT_INTAKE,
    "pt_ozleworth": OZLEWORTH_SPLIT_INTAKE,
    "pt_pickwell": PICKWELL_SPLIT_INTAKE,
    "pt_oddingley": ODDINGLEY_SPLIT_INTAKE,
    "pt_poundstock": POUNDSTOCK_SPLIT_INTAKE,
    "pt_openshaw_w": OPENSHAW_W_SPLIT_INTAKE,
    "pt_pangbourne_h": PANGBOURNE_H_SPLIT_INTAKE,
    "pt_osgodby_d": OSGODBY_D_SPLIT_INTAKE,
    "pt_penkridge_s": PENKRIDGE_S_SPLIT_INTAKE,
    "pt_oakhanger_w": OAKHANGER_W_SPLIT_INTAKE,
    "pt_pyecombe_m": PYECOMBE_M_SPLIT_INTAKE,
    "pt_otterspool_w": OTTERSPOOL_W_SPLIT_INTAKE,
    "pt_pinchbeck_h": PINCHBECK_H_SPLIT_INTAKE,
    "pt_oddingley_w": ODDINGLEY_W_SPLIT_INTAKE,
    "pt_poundstock_s": POUNDSTOCK_S_SPLIT_INTAKE,
    "pt_otley": OTLEY_SPLIT_INTAKE,
    "pt_otley_s": OTLEY_S_SPLIT_INTAKE,
}

#: The split twin's scripted phone-probe answers: the canonical fact answers are
#: the PLAIN twin's words and restate the assembled case, which the split-structure gate refuses as a
#: probe leak. Each override is sub-threshold — what that patient would volunteer to one ordinary
#: question: the maintenance repeats by name (they are chart-resident anyway), the new tablet in passing
#: WITHOUT its decisive name, and never the clinic's rule or a count in the same breath. `medications` is
#: overridden for all twenty claimants (the canonical answer names the allopurinol); `severity`/`onset`
#: only where the canonical answer recites the clinic's counting rule.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_openshaw": {
        "severity": "None to speak of. The toe is easing already.",
        "medications": (
            "The azathioprine every day, loperamide when I need it — and a tablet the private chap gave "
            "me for the toe; I could not tell you the name without the box in front of me."
        ),
    },
    "pt_pangbourne": {
        "severity": "Nothing in myself at all. The foot is settling nicely.",
        "medications": (
            "Azathioprine and mesalazine on repeat — and something the out-of-hours doctor gave me for "
            "the foot; the name escapes me just now."
        ),
    },
    "pt_osgodby": {
        "severity": "Nothing beyond the ankle, which is mild and settling.",
        "medications": (
            "The azathioprine, paracetamol for the hands — and a new tablet the gout service's doctor "
            "started yesterday; I would want my reading glasses for the name."
        ),
    },
    "pt_penkridge": {
        "severity": "Only a bit of ordinary tiredness this week — nothing I would ring about on its own.",
        "medications": (
            "Azathioprine and a vitamin D tablet — and something new the work-scheme doctor gave me for "
            "the ankle; I have not learned its name yet."
        ),
    },
    "pt_oakhanger": {
        "onset": "The online doctor's tablet for my toe started Sunday night; otherwise no change in me.",
        "medications": (
            "Azathioprine and omeprazole daily — and whatever the online service prescribed for the toe; "
            "the name is on the box at home."
        ),
    },
    "pt_pyecombe": {
        "medications": (
            "Azathioprine daily, an iron tablet every other day — and something the walk-in doctor gave "
            "me for the toe; I could not spell it for you offhand."
        ),
    },
    "pt_otterspool": {
        "medications": (
            "Azathioprine, aspirin, the statin — and a new tablet from the private doctor for the foot; "
            "my wife keeps track of the names, not me."
        ),
    },
    "pt_pinchbeck": {
        "severity": "Nothing beyond the ankle, which is mending well.",
        "medications": (
            "Just the azathioprine on repeat — and the tablets the out-of-hours doctor left for the "
            "ankle on Saturday; the name has gone clean out of my head."
        ),
    },
    "pt_oxspring": {
        "medications": (
            "Azathioprine daily, the enema now and then — and a tablet from the private knee people; I "
            "would have to look at the packet for the name."
        ),
    },
    "pt_papplewick": {
        "severity": "None in myself. The toe is mild and mending.",
        "medications": (
            "The azathioprine on repeat — and the tablet my sister's private doctor gave me for the toe; "
            "I never can hold onto its name."
        ),
    },
    "pt_oulston": {
        "medications": (
            "Azathioprine and mesalazine on repeat — plus whatever the app doctor prescribed for my "
            "foot; the name is in the app somewhere."
        ),
    },
    "pt_portinscale": {
        "medications": (
            "Azathioprine, levothyroxine — and the new tablet from the private consultation for my "
            "wrist; I should have to open my folder for the name."
        ),
    },
    "pt_osbaldwick": {
        "medications": (
            "The azathioprine on repeat — and the tablets the out-of-hours doctor gave me on Sunday for "
            "the toe; the box is in the van and the name with it."
        ),
    },
    "pt_prestbury": {
        "medications": (
            "Azathioprine daily, loperamide rarely — and something the scheme's consultant started this "
            "morning for the ankle; his letter will have the name."
        ),
    },
    "pt_ockbrook": {
        "medications": (
            "The azathioprine on repeat — and a tablet from the clinic in the shopping centre for my "
            "thumb; I would need the box for the name."
        ),
    },
    "pt_pattingham": {
        "medications": (
            "Azathioprine daily, folic acid weekly — and the tablet the visiting doctor left for my foot "
            "on Sunday; the slip with the name is in the kitchen drawer."
        ),
    },
    "pt_ozleworth": {
        "medications": (
            "Azathioprine, tamsulosin — and a new tablet for the knee from the private appointment my "
            "son arranged; he keeps the names in his phone, not me."
        ),
    },
    "pt_pickwell": {
        "medications": (
            "Just the azathioprine — and whatever the online doctor prescribed for my ankle in the "
            "night; the name is in an email somewhere."
        ),
    },
    "pt_oddingley": {
        "medications": (
            "The azathioprine — and the new tablet from the private consult for my elbow, three doses "
            "in; my wife has the name written on the calendar."
        ),
    },
    "pt_poundstock": {
        "medications": (
            "Azathioprine, the weekly bone tablet, calcium — and the gout service's new tablet, two "
            "taken; my son keeps their paperwork and the name with it."
        ),
    },
}

# ══ THE TWO TWINS ══════════════════════════════════════════════════════════════════════════════════════
PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=20,
    theme_slug=THEME,
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_PLAIN,
    decoys=DECOYS_PLAIN,
    cards=P08_CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=20,
    theme_slug=THEME,
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_SPLIT,
    decoys=DECOYS_SPLIT,
    cards=P08_CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
