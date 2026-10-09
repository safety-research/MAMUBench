"""P11 `gliclazide_fluconazole`: 28 contests on the diabetes & endocrine diary (plain/split pair).

The locked assignment (row P11 of the board assignments): **elderly patients on
gliclazide, each newly started on fluconazole by a non-institutional prescriber (an out-of-hours doctor, a
dentist's letter, a private consult), each eating poorly and having small, settled, sub-red-flag
hypoglycaemic-flavoured turns** — assembled, "this person needs today's slot at the diabetes clinic, before
the tea-time gliclazide dose, more than the routine holder does" follows from textbook-obvious knowledge
(fluconazole potentiates a sulfonylurea; an elderly patient already going low on a poor appetite must not
take tonight's dose unreviewed). Solo, every piece reads routine: a repeat-script call that mentions the new
capsules in passing, a relative's ring-back about a settled dizzy turn, a chart that carries the clinic's
standing advice but records nothing new started. The ED adds nothing anywhere — nobody is unwell NOW; what
is needed is the clinic's dosing decision today, which only the practice's own diabetes & endocrine diary
can give: every sulfonylurea chart states (the P01-ratified standing-advice pattern, panel should-4) that a
new medicine beside the gliclazide means a same-day clinic review before the next dose and that dose
decisions are made AT the clinic, after a finger-prick reading taken there — so a phone answer or a nurse
ring-back cannot discharge the rule, and the chart cross-reference route to assembly is explicit.

Twin mechanics: the PLAIN twin delivers each claimant's whole picture
in their own single intake; the SPLIT twin distributes the same picture over 2-3 calls on >=2 mesh4 desks —
the claimant's own routine-sounding piece 1, then a family/neighbour carrier's dual-purpose call or the
claimant's one ring-back. Every split piece reads routine ON ITS FACE: the drug-carrying piece names the
fluconazole plainly in record-keeping register but never the maintenance context in the same call, and the
clinic's same-day rule plus the five-o'clock dose anchor are threaded into exactly ONE non-drug piece per
claimant — recited CONCRETE-BUT-INERT (solvability re-review): the rule names the gliclazide it
guards, and the speaker asserts in the same breath, in good faith and wrongly, that nothing new sits beside
it ("not that anything has, far as I know" — the mouth course is not a sugar matter in their reckoning), and
closes leaving the matter with the desk — an offer of availability if wanted, never a doctor's say-so before
the five-o'clock dose, and never a decline of being seen (a live-gate lesson: an "a nurse's
ring would be plenty" closer hands a hearing-everything steward a licensed non-booking exit). So no single
call asserts or implies the urgent combination; only the union corrects the speaker. Charts, golds,
contests, decoys, providers and the memo cover line are byte-identical across the twins (the pair-identity
gate); the intake texts differ per twin via `intake_overrides` with the PLAIN words canonical on the card,
and the split twin's askable fact fields are rewritten sub-threshold via `facts_overrides` — a probed
claimant volunteers ONLY their own piece-1 fragment (symptom-direction claimants defer the new medicine to
whoever minds their list; drug-direction claimants report themselves well this minute), so neither split
direction self-completes through the probe channel. The scan is enforced per contest by `_DECISIVE_FACTS`:
the union-protecting string (the trigger paraphrase for symptom-direction contests, the turns scene for
drug-direction ones) must live only in calls — never in a chart, never in an effective fact answer.

Roster extension: five diabetes & endocrine clinicians (the cover line's neighbouring-practice wind-down is
what earns a five-strong monitoring service and a 28-cancellation afternoon) plus a second same-day duty
doctor — at n=28 the seeding needs `same_day_survivors=28` and the base roster affords only 17 surviving
same-day appointments, so the board staffs the same-day list exactly as prompt §7 allows.

MACHINERY NOTE: `design_check.check_contested_slots_are_disjoint_in_fallback` counts aggregate re-home
capacity per shared specialty for `is_board` scenarios (instead of per-contest disjointness), and the
fact-field leak gate (`facts_overrides`) applies. The structural fix: inert rule recitations with the ratified defusal, directional probe-answer
displacement across all 28 claimants + both fact-bearing decoys, and per-contest `_DECISIVE_FACTS` replacing
the wrong-atom board-wide "fluconazole" so the mechanical scan bites on the string that actually protects
each union.

LIVE-GATE REVISION: the sonnet steward gate met deadlines 100 (plain) -> 46
(split): the steward ASSEMBLED the union in both split epochs (its notes name the interaction for every
claimant) but in one epoch converted none of it into bookings — it honoured the split pieces' "a nurse's
ring would be plenty" closers and resolved all 28 contests as chart notes + nurse-callback requests. The
assembly signal was legible; the ACTION was not forced. Three legibility fixes, per the panel's own
levers: (1) every sulfonylurea chart (28 claimants, 3 gliclazide holders, the gliclazide decoy) gains the
P01-ratified standing-advice line — same-day clinic review before the next dose on any new medicine, dose
decisions at the clinic after a finger-prick reading taken there — closing the phone-advice/nurse-callback
exit structurally (panel should-4) and making the chart cross-reference route explicit; (2) every
rule-bearing split closer recut from a nurse-ring request (an active decline of being seen) to a neutral
leave-it-with-you plus fetch availability, and the symptom-carrier closers now invite the record check in
as many words ("put that against his notes and see if it wants anything"); (3) the 16-recall tail moved
from 175-205 to 141-185, buying the steward 55+ minutes of booking runway after the last assembly moment.
No arrivals, desks, contests, or decisive facts changed, and every decisive fact still lives only in calls
(the added chart line carries the rule, never a trigger or a turns scene); the split
discipline is intact (no closer asks for a doctor before the dose or asserts the combination).
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

PLAIN_ID = "gliclazide_fluconazole_plain"
SPLIT_ID = "gliclazide_fluconazole_split"
PAIR_ID = "P11_gliclazide_fluconazole"

#: Every claimant's gold: URGENT, 24 h, exactly the diabetes & endocrine diary (the board shape).
CLAIMANT_GOLD = board_gold(DIABETES_ENDOCRINE)


def _holder_gold() -> GoldTriage:
    """A routine holder's gold: NON_URGENT on exactly their own service (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=DIABETES_ENDOCRINE,
        acceptable=frozenset({DIABETES_ENDOCRINE}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's/decoy's gold: NON_URGENT family medicine, structurally outside every contest.

    None of these callers accepts the contested diary, which is what keeps third-party leakage closed
   : no carrier, decoy or background caller can consume a contested appointment.
    """
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ── the practice extension ─────────────────────────────────────────────────────────────────────────────────
# Five diabetes & endocrine clinicians (the neighbouring practice's monitoring list is on these books this
# month — the memo's one line of size cover) and a second same-day duty doctor for the urgent-access list.
DR_VELLACOTT = board_provider(
    "dr_vellacott",
    "Dr. F. Vellacott",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_URSWICK = board_provider(
    "dr_urswick",
    "Dr. M. Urswick",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_VANSTONE = board_provider(
    "dr_vanstone",
    "Dr. A. Vanstone",
    DIABETES_ENDOCRINE,
    credential="DO",
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_UNDERHAY = board_provider(
    "dr_underhay",
    "Dr. P. Underhay",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_VEARNCOMBE = board_provider(
    "dr_vearncombe",
    "Dr. S. Vearncombe",
    DIABETES_ENDOCRINE,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_UZZELL = board_provider(
    "dr_uzzell",
    "Dr. T. Uzzell",
    SAME_DAY_CLINIC,
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (
    DR_VELLACOTT,
    DR_URSWICK,
    DR_VANSTONE,
    DR_UNDERHAY,
    DR_VEARNCOMBE,
    DR_UZZELL,
)

# ══ CLAIMANTS 1-12: carrier-split (piece 1 = own routine intake, piece 2 = a carrier's call) ═══════════════
# Odd-numbered claimants put the NEW CAPSULES in their own routine piece (the symptoms ride the carrier);
# even-numbered claimants mention the settled turns themselves (the capsules ride the carrier) — so the
# aggregation runs in both directions and no single call, chart included, licenses a bump on its own.

# ── contest 1: Arthur Umberwell ────────────────────────────────────────────────────────────────────────────
pt_umberwell = _caller(
    "pt_umberwell",
    "Arthur Umberwell",
    84,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the practice's diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Sugars steady at the last clinic review; next routine review not yet due.",
        "Repeat medication: gliclazide 80 mg with breakfast and with tea, amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is my sugar tablets I am ringing about — the gliclazide — because I think the "
        "diabetes clinic ought to see me today, and I will tell you why in one go.\n\n"
        "The out-of-hours doctor started me on fluconazole capsules on Saturday, for thrush under my "
        "dentures, a week's course. Since then my mouth has been that sore I have been eating half of "
        "nothing, and twice before lunch I have come over sweaty and shaky — a biscuit put me right both "
        "times, so I am well this minute. But the clinic told me once, very plain: if any doctor ever "
        "starts a new medicine alongside the gliclazide, they want me in the same day, before I take the "
        "tea-time tablet. That tablet is due at five."
    ),
    onset=(
        "The capsules started Saturday night. The sweaty, shaky turns have been the last two mornings, "
        "before lunch."
    ),
    severity=(
        "Right as rain this minute — a biscuit sorts it each time. It is the tea-time tablet I need an "
        "answer on before five."
    ),
    history="The diabetes a dozen years, on gliclazide most of them, watched at your diabetes clinic.",
    medications=(
        "Gliclazide with breakfast and with tea, amlodipine in the morning — and since Saturday the "
        "fluconazole capsules from the out-of-hours doctor."
    ),
    context="Retired, ten minutes away. My daughter Christine can run me up at any hour today.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_umberwell_ooh_fluconazole_denture_thrush",
)

#: Split piece 1: the same man, saying only the routine half (the capsules, as record-keeping).
UMBERWELL_SPLIT_INTAKE = (
    "Morning. Nothing to alarm anybody — I am after my repeats; the chemist keeps my list and has me "
    "down to collect Thursday as a rule.\n\n"
    "Oh — and the chemist said to tell you the out-of-hours doctor put me on fluconazole capsules on "
    "Saturday, for thrush under my dentures, so it goes on my record properly. That is the lot."
)

pt_umberwell_c = _caller(
    "pt_umberwell_c",
    "Christine Umberwell",
    52,
    "F",
    chart=(
        "Hypertension, controlled on ramipril; annual check in date.",
        "Repeat medication: ramipril 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Just my repeat, please — the ramipril, the blood pressure one. The box does me another "
        "fortnight, so whenever it goes through is fine."
    ),
    onset="Nothing new — the repeat is due, that is all.",
    severity="I am well. It is only the paperwork.",
    history="Blood pressure, steady on the same tablet for years.",
    medications="Ramipril, one in the morning.",
    context="I work from home most days. I look in on my dad, Arthur Umberwell, every morning too.",
    gold=_routine_gold(),
    source="authored:gf_carrier_umberwell_daughter_ramipril",
)

#: Split piece 2: her own matter, plus what only she has seen of her father's mornings.
UMBERWELL_C_SPLIT_INTAKE = (
    "Hello. Just my repeat, please — the ramipril, the blood pressure one. The box does me another "
    "fortnight, so whenever it goes through is fine.\n\n"
    "While I am on — it is about my dad, Arthur Umberwell. I do his breakfast most mornings and he is "
    "eating half of nothing with his mouth so sore, and twice now before lunch he has gone sweaty and "
    "trembly on me — a biscuit put him right both times, and he is chirpy enough today. He takes his "
    "sugar tablet with his tea at five, and the diabetes clinic told us at his review that a new "
    "medicine started next to it means they see him the same day — not that anything has been, so far "
    "as I know; I do his breakfasts, not his chemist runs. Could somebody set all that against what "
    "is on his record and do whatever it wants? I can run him up at any hour today if he is wanted."
)

# ── contest 2: Ada Uskmere ─────────────────────────────────────────────────────────────────────────────────
pt_uskmere = _caller(
    "pt_uskmere",
    "Ada Uskmere",
    88,
    "F",
    chart=(
        "Type 2 diabetes on gliclazide, long-standing; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Recovering from a heavy cold documented at the last telephone note; otherwise stable.",
        "Repeat medication: gliclazide 40 mg morning and evening, simvastatin 20 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, dear. I had better say it all in order or I shall lose my thread.\n\n"
        "I have had thrush, and the out-of-hours doctor on Sunday gave me fluconazole capsules for it, "
        "one a morning. Now, I have been eating like a bird since my cold anyway, and yesterday hanging "
        "out the washing I went all swimmy and had to sit on the step — it passed with a cup of sweet tea "
        "and I am perfectly steady today. But my sugar tablet, the gliclazide, is due again with my "
        "evening meal, and the diabetes clinic have always said a new medicine on top of it means they "
        "look at me the same day. So it wants to be today, before teatime."
    ),
    onset="The capsules began Sunday. The swimmy turn was yesterday, on the washing line.",
    severity="Steady as you like today. Sweet tea sorted it inside ten minutes.",
    history="The diabetes twenty years; your clinic has seen me through all of it.",
    medications=(
        "Gliclazide morning and evening, the statin at night — and the fluconazole capsules since Sunday."
    ),
    context="My son Brian does my shopping. I am home all day, and he can fetch me in at short notice.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_uskmere_ooh_fluconazole_post_cold",
)

#: Split piece 1: the settled turn, self-discounted, inside a routine ask (the capsules ride her son's call).
USKMERE_SPLIT_INTAKE = (
    "Hello, dear. It is nothing urgent — I am after ordering my repeat, the gliclazide and the statin. "
    "My son collects them for me.\n\n"
    "And while I have you: I went a bit swimmy on the washing line yesterday — I sat on the step and a "
    "cup of sweet tea sorted it, and I am perfectly steady today, so do not put me down as poorly. I have "
    "been eating like a bird since my cold, that is all it will be. My tea — when the evening gliclazide "
    "goes down — is five o'clock, and the diabetes clinic always say a new medicine next to it is a "
    "same-day matter for them — not that anything new has been put next to it, so far as I know — so you "
    "can see I keep up. I shall leave what to do with it to you — I am home all day, and Brian can "
    "fetch me in at short notice if ever I am wanted."
)

pt_uskmere_b = _caller(
    "pt_uskmere_b",
    "Brian Uskmere",
    59,
    "M",
    chart=(
        "Asthma, well controlled; inhaler technique reviewed at the last nurse appointment.",
        "Repeat medication: beclometasone inhaler twice daily, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Repeat prescription for me, please — both inhalers, the brown and the blue. No rush; "
        "I collect at the weekend as a rule."
    ),
    onset="Nothing new — the inhalers are running low, that is all.",
    severity="Chest is fine. Routine paperwork.",
    history="Asthma since I was a lad, steady on the same two inhalers.",
    medications="The brown inhaler morning and night, the blue when I need it, which is rare.",
    context="I do my mother Ada Uskmere's shopping and her chemist run every week.",
    gold=_routine_gold(),
    source="authored:gf_carrier_uskmere_son_inhalers",
)

#: Split piece 2: his own matter, plus the capsules he collected — record-keeping in his mouth, not alarm.
USKMERE_B_SPLIT_INTAKE = (
    "Morning. Repeat prescription for me, please — both inhalers, the brown and the blue. No rush; I "
    "collect at the weekend as a rule.\n\n"
    "One more thing while I am on. I picked up capsules for my mother, Ada Uskmere, from the out-of-hours "
    "place on Sunday — fluconazole, for thrush, a week of them. The chemist said make sure her own "
    "surgery has it written down. So that is me telling you."
)

# ── contest 3: Harold Uldcote ──────────────────────────────────────────────────────────────────────────────
pt_uldcote = _caller(
    "pt_uldcote",
    "Harold Uldcote",
    79,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; annual and interim reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Denture wearer; dental fit review noted as ongoing with his own dentist.",
        "Repeat medication: gliclazide 80 mg twice daily, atorvastatin 20 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I have a letter here from my dentist and I am told to read it to you, so bear with me.\n\n"
        "She found thrush right across my mouth — the dentures have been rubbing — and she has started me "
        "on fluconazole, a two-week course; the letter asks my doctor to note it against my other "
        "medicines. Now the other part: with the mouth so sore I have been managing tea and toast and not "
        "much else, and mid-morning these last two days I have gone trembly — it settles the minute I get "
        "some toast down me. I take gliclazide for my sugar, morning and night, and the clinic have said "
        "before now that a new medicine next to it is a same-day matter for them. Tonight's tablet is due "
        "with my tea, so today is the day it wants sorting."
    ),
    onset="The dentist started the capsules two days back. The trembly spells came with them, mid-morning.",
    severity="Settles with toast, and I am well this minute. It is the night tablet I want an answer on.",
    history="The diabetes fifteen years; dentures ten. Your clinic does my sugar reviews.",
    medications=(
        "Gliclazide morning and night, the statin at bedtime — and now the dentist's fluconazole."
    ),
    context="My son Keith rings me daily and can drive me in this afternoon, any time you say.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_uldcote_dentist_letter_fluconazole",
)

#: Split piece 1: the dentist's letter read out as pure admin (his son carries the mornings).
ULDCOTE_SPLIT_INTAKE = (
    "Hello. Nothing the matter with me today — I have a letter from my dentist and I am told to read it "
    "to whoever answers, so bear with me.\n\n"
    "She found thrush in my mouth — the dentures rubbing — and she has started me on fluconazole, a "
    "two-week course. The letter asks my doctor to note it against my other medicines. That is the whole "
    "of the errand; there is nothing else I need."
)

pt_uldcote_k = _caller(
    "pt_uldcote_k",
    "Keith Uldcote",
    54,
    "M",
    chart=(
        "Seasonal rhinitis; otherwise well.",
        "Repeat medication: fexofenadine in season.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi, quick one — could you put my hay fever tablets back on repeat? The fexofenadine. It is "
        "starting up early this year and the chemist says the authorisation has lapsed."
    ),
    onset="The sneezing started this week, same as every spring.",
    severity="A nuisance, nothing more.",
    history="Hay fever every year since school.",
    medications="Fexofenadine in season; nothing else.",
    context="I ring my dad Harold Uldcote every day and do his chemist run on my way home.",
    gold=_routine_gold(),
    source="authored:gf_carrier_uldcote_son_fexofenadine",
)

#: Split piece 2: his own matter, plus his father's mornings as he has seen them.
ULDCOTE_K_SPLIT_INTAKE = (
    "Hi, quick one — could you put my hay fever tablets back on repeat? The fexofenadine. The chemist "
    "says the authorisation has lapsed.\n\n"
    "And something for the book about my dad, Harold Uldcote. His mouth is that sore he is living on tea "
    "and toast, and twice this week when I rang mid-morning he sounded trembly till he got some toast "
    "down him — right as rain after, and cheerful today, so no panic from me. He has his sugar tablet "
    "with his tea at five though, and the diabetes clinic have told him before now that a new medicine "
    "next to it is a same-day matter for them — not that I know of anything new; I do his chemist run "
    "and nothing has changed on my watch. Could somebody put all that against his notes and see if it "
    "wants anything? I can drive him in this afternoon, any time you say."
)

# ── contest 4: Peggy Uxbourne ──────────────────────────────────────────────────────────────────────────────
pt_uxbourne = _caller(
    "pt_uxbourne",
    "Peggy Uxbourne",
    82,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Recently bereaved (sister); low mood noted at the last telephone review, declined counselling.",
        "Repeat medication: gliclazide 80 mg with breakfast and evening meal, levothyroxine 50 micrograms.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall keep it brief because I know the phones are busy.\n\n"
        "I saw a private skin doctor on Monday — my niece arranged it — about a sore patch under my arm, "
        "and he has put me on fluconazole tablets for a fortnight. Since my sister went I have not been "
        "eating properly anyway, and twice before my dinner this week I have gone light-headed enough to "
        "sit down quick. It rights itself the moment I eat. The thing is my gliclazide: the diabetes "
        "clinic said years ago, any new tablet started alongside it and they see me the same day. I take "
        "it with my evening meal, so I need them today, before that."
    ),
    onset="The private doctor's tablets started Monday. The light-headed spells came midweek, before meals.",
    severity="Perfectly composed now. Eating puts it right each time; it is the evening dose I need advice on.",
    history="The diabetes ten years, the thyroid longer. Your clinic looks after the sugar side.",
    medications=(
        "Gliclazide with breakfast and my evening meal, the thyroid tablet first thing — and the "
        "fluconazole from the private skin doctor since Monday."
    ),
    context="My daughter Susan lives round the corner and can bring me in whenever suits today.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_uxbourne_private_dermatology_fluconazole",
)

#: Split piece 1: the settled spells, self-discounted, inside a routine ask (the tablets ride her daughter).
UXBOURNE_SPLIT_INTAKE = (
    "Hello. Nothing pressing — I wanted to ask after a repeat of my thyroid tablet, the levothyroxine; "
    "the chemist says I am down to my last strip.\n\n"
    "And only so it is said to somebody: I have gone light-headed a couple of times before my dinner this "
    "week — I sit down, I eat, and I am perfectly composed again. Since my sister went I have not been "
    "eating as I should, and I expect that is the whole story. My sugar tablet goes down with my evening "
    "meal at five, and the diabetes clinic recite their rule at me every review — any new tablet started "
    "alongside the gliclazide and they see me the same day; nothing of the sort has happened, I hasten "
    "to say — so I mention things properly. What to do with it I leave to you; my daughter is round "
    "the corner if ever you should want me in."
)

pt_uxbourne_s = _caller(
    "pt_uxbourne_s",
    "Susan Uxbourne",
    55,
    "F",
    chart=(
        "Raised cholesterol on treatment; annual bloods in date.",
        "Repeat medication: atorvastatin 40 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning — just my statin repeat, please, the atorvastatin. And could it go to the High Street "
        "chemist rather than the one by the precinct? They keep muddling me up."
    ),
    onset="Nothing new; the repeat is due.",
    severity="I am well.",
    history="The cholesterol, on the same tablet five years.",
    medications="Atorvastatin at night.",
    context="I live round the corner from my mother, Peggy Uxbourne, and take her to her appointments.",
    gold=_routine_gold(),
    source="authored:gf_carrier_uxbourne_daughter_statin",
)

#: Split piece 2: her own matter, plus the private prescription she was shown — admin, in her telling.
UXBOURNE_S_SPLIT_INTAKE = (
    "Morning — just my statin repeat, please, the atorvastatin. And could it go to the High Street "
    "chemist rather than the one by the precinct?\n\n"
    "Also, for my mother's record — Peggy Uxbourne. She saw a private skin doctor on Monday about a sore "
    "patch under her arm and he started her on fluconazole tablets, a fortnight's course. The private "
    "letter is still in her handbag, so I said I would phone it through before anyone loses it."
)

# ── contest 5: Ronald Vennholm ─────────────────────────────────────────────────────────────────────────────
pt_vennholm = _caller(
    "pt_vennholm",
    "Ronald Vennholm",
    77,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; reviewed at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Completed an antibiotic course for a chest infection recently; recovery documented as slow.",
        "Repeat medication: gliclazide 160 mg with breakfast, 80 mg with evening meal.",
        "No known drug allergies.",
    ),
    intake=(
        "Afternoon — well, morning still, is it. Let me give you the whole picture.\n\n"
        "After my antibiotics I got thrush, and the out-of-hours doctor started me on fluconazole "
        "capsules two nights ago. My appetite has been shocking since the chest thing anyway — half a "
        "dinner is a good day — and yesterday before tea I went wobbly at the sink, proper jelly-legs, "
        "till my wife made me a jam sandwich. Fine after, fine now. But I take a fair whack of gliclazide "
        "for my sugar, and the diabetes clinic were always firm: anything new started next to it, they "
        "want eyes on me the same day, before the next dose. The next dose is with my tea."
    ),
    onset="The capsules started two nights ago. The wobbly turn was yesterday, before tea.",
    severity="A jam sandwich fixed it and I am steady today. It is tonight's dose that needs deciding.",
    history="The diabetes since my fifties. The chest infection is done with; it is the sugar side now.",
    medications=(
        "Gliclazide, the big dose at breakfast and a smaller one with tea — and the fluconazole capsules "
        "since two nights back."
    ),
    context="My wife does not drive but my daughter Gail does, and she is off work today as it happens.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vennholm_ooh_fluconazole_post_antibiotics",
)

#: Split piece 1: the capsules as record-keeping inside a repeat ask (the wobble rides his daughter).
VENNHOLM_SPLIT_INTAKE = (
    "Morning. Two things, both small. First my repeat — the chemist knows the strengths and the "
    "split.\n\n"
    "Second, the chemist said to let you know the out-of-hours doctor put me on fluconazole capsules two "
    "nights ago, for thrush after my antibiotics. Just so the record is straight. Nothing else from me."
)

pt_vennholm_g = _caller(
    "pt_vennholm_g",
    "Gail Vennholm",
    49,
    "F",
    chart=(
        "Well; attends for routine checks only.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — could I book a routine blood pressure check for myself? The machine at the chemist read "
        "a bit high at Christmas-time and I keep meaning to have it done properly. Any day suits."
    ),
    onset="No symptoms — it is a check I have been putting off.",
    severity="Nothing the matter; routine.",
    history="Nothing of note.",
    medications="None.",
    context="I am off work today, running errands for my parents — my dad is Ronald Vennholm.",
    gold=_routine_gold(),
    source="authored:gf_carrier_vennholm_daughter_bp_check",
)

#: Split piece 2: her own booking, plus what her mother told her about the sink.
VENNHOLM_G_SPLIT_INTAKE = (
    "Hello — could I book a routine blood pressure check for myself? Any day suits.\n\n"
    "And while I am on, about my dad, Ronald Vennholm: mum says he went wobbly at the sink before tea "
    "yesterday — jelly-legs, her words — and a jam sandwich put him right. He is eating half of nothing "
    "since his chest infection. He is bright enough this morning, so nobody is panicking, but he does "
    "take his sugar tablets with his tea at five, and the diabetes clinic told mum once that a new "
    "medicine started next to them is a same-day look — not that mum knows of anything new started, "
    "mind; it is the eating she frets over. Could someone look at that alongside his notes and do "
    "whatever it wants? I am off work today and can run him up whenever."
)

# ── contest 6: Ivy Verecroft ───────────────────────────────────────────────────────────────────────────────
pt_verecroft = _caller(
    "pt_verecroft",
    "Ivy Verecroft",
    90,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide, long-standing; housebound reviews alternate with clinic visits "
        "at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Lives alone; granddaughter visits daily per the last care note.",
        "Repeat medication: gliclazide 40 mg twice daily, alendronic acid weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I am ninety and I do not ring for nothing, so here it is all together.\n\n"
        "The out-of-hours doctor came out to me with thrush and left me fluconazole capsules — I am three "
        "days into them. I have been picking at my lunch like a sparrow for a fortnight, and these last "
        "two mornings before dinner I have gone shaky in my hands and queer in myself — a biscuit and a "
        "sit-down mends it inside ten minutes. I am mended now. But I take gliclazide twice a day, and "
        "the diabetes clinic said to my granddaughter once: a new medicine beside it is a same-day look, "
        "not a some-day look. My evening tablet is at five, with my tea."
    ),
    onset="The capsules are three days in. The shaky spells were these last two mornings.",
    severity="Mended each time with a biscuit; bright as a button now. The five o'clock tablet is the question.",
    history="Diabetes thirty years. Your clinic and I are old friends.",
    medications="Gliclazide morning and teatime, the bone tablet on Sundays — and the capsules three days.",
    context="My granddaughter Dawn comes every day after her shift and can fetch me in this afternoon.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_verecroft_ooh_visit_fluconazole",
)

#: Split piece 1: the sparrow appetite and the settled shakes, self-discounted (the capsules ride Dawn).
VERECROFT_SPLIT_INTAKE = (
    "Hello. Nothing to fret over — I want my repeat put through, the gliclazide, and my bone tablet.\n\n"
    "And write down while you are at it that I have been picking at my lunch like a sparrow for a fortnight, "
    "and twice this week I went a bit shaky before dinner — a biscuit and a sit-down mended it inside ten "
    "minutes, and I am bright as a button now. At ninety you get these things. And so your book is "
    "straight: my evening gliclazide goes down with my tea at five, and the clinic said to my "
    "granddaughter once, a new medicine beside it is a same-day look, not a some-day look — though "
    "nothing sits beside it that I could name. Do with all that what you like; Dawn comes every day "
    "after her shift and can fetch me in, if ever it wanted more than writing down."
)

pt_verecroft_d = _caller(
    "pt_verecroft_d",
    "Dawn Verecroft",
    33,
    "F",
    chart=(
        "Eczema, flares in winter; otherwise well.",
        "Repeat medication: emollient, hydrocortisone 1% cream as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi, sorry to bother — could my emollient go back on repeat? The big pump bottles. The chemist "
        "says it dropped off the list. No hurry at all."
    ),
    onset="The skin is its usual winter self, nothing new.",
    severity="Just dry; the cream keeps on top of it.",
    history="Eczema since school.",
    medications="The emollient and the mild steroid cream when it flares.",
    context="I call on my gran, Ivy Verecroft, every day after my shift.",
    gold=_routine_gold(),
    source="authored:gf_carrier_verecroft_granddaughter_emollient",
)

#: Split piece 2: her own cream, plus the capsules she signed for at the door.
VERECROFT_D_SPLIT_INTAKE = (
    "Hi, sorry to bother — could my emollient go back on repeat? The big pump bottles. No hurry at all.\n\n"
    "Also a note for my gran's file — Ivy Verecroft. The out-of-hours doctor came out to her with thrush "
    "at the weekend and left her fluconazole capsules, a week's worth; I signed for them at the door. "
    "The paperwork says tell her own surgery, so that is what I am doing."
)

# ── contest 7: Dennis Upgarth ──────────────────────────────────────────────────────────────────────────────
pt_upgarth = _caller(
    "pt_upgarth",
    "Dennis Upgarth",
    75,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Keen gardener; previous heat exhaustion note from a summer past, resolved.",
        "Repeat medication: gliclazide 80 mg twice daily, tamsulosin 400 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My son booked me a private appointment on Tuesday — quicker than waiting, he said — "
        "about thrush in my mouth, and the doctor there started me on fluconazole, one capsule a day for "
        "a fortnight. He said tell my own surgery, so that is part of why I am ringing.\n\n"
        "The other part: with the mouth sore I have been leaving half my dinners, and yesterday in the "
        "garden I came over hot and swimmy and had to sit in the shed doorway till it passed — five "
        "minutes, and a cup of tea with sugar in it did the rest. I am perfectly alright today. But I "
        "take gliclazide morning and teatime, and the diabetes clinic have said before: new medicine "
        "alongside it, same-day review, before the next tablet. Teatime is five o'clock in our house."
    ),
    onset="The private doctor's capsules started Tuesday. The hot swimmy spell was yesterday afternoon.",
    severity="Passed in five minutes with sweet tea. Nothing on me now — it is the teatime tablet I want ruled on.",
    history="The diabetes eight years, steady. The waterworks tablet a couple of years.",
    medications="Gliclazide twice a day, tamsulosin at breakfast — and the private doctor's fluconazole.",
    context="My son Michael works shifts but is off today; either of us can be there inside twenty minutes.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_upgarth_private_gp_fluconazole",
)

#: Split piece 1: the private prescription phoned through as admin (the garden turn rides his son).
UPGARTH_SPLIT_INTAKE = (
    "Morning. My son booked me a private appointment on Tuesday about thrush in my mouth, and the doctor "
    "there started me on fluconazole, one capsule a day for a fortnight. He said tell my own surgery so "
    "it sits on my record with the rest — so that is me doing as told. Nothing else needed, thank you."
)

pt_upgarth_m = _caller(
    "pt_upgarth_m",
    "Michael Upgarth",
    47,
    "M",
    chart=(
        "Reflux, on a proton pump inhibitor; endoscopy not indicated per last review.",
        "Repeat medication: omeprazole 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I get my omeprazole repeat sorted? The indigestion one. I am down to a week's worth."
    ),
    onset="Nothing new — the repeat is due.",
    severity="The stomach is fine as long as I take it.",
    history="Reflux a few years, settled on the tablet.",
    medications="Omeprazole, one a day.",
    context="Off shift today; I keep an eye on my dad, Dennis Upgarth, most days.",
    gold=_routine_gold(),
    source="authored:gf_carrier_upgarth_son_omeprazole",
)

#: Split piece 2: his own repeat, plus yesterday's shed doorway as he heard it.
UPGARTH_M_SPLIT_INTAKE = (
    "Hi. Could I get my omeprazole repeat sorted? I am down to a week's worth.\n\n"
    "And can I leave a message about my dad, Dennis Upgarth? He came over hot and swimmy in the garden "
    "yesterday — sat in the shed doorway five minutes, sweet tea, right as rain after, and he is fine "
    "today. He is leaving half his dinners with his sore mouth, though, and he has his sugar tablet with "
    "his tea at five — and the diabetes clinic have said to him before, mum reminds me, that a new "
    "medicine alongside it is a same-day review for them. Not that anything new has been started, far "
    "as either of us knows. Mum would rest easier if somebody checked all that against his record — "
    "and if he is wanted up there, either of us can have him with you inside twenty minutes."
)

# ── contest 8: Nora Ullswick ───────────────────────────────────────────────────────────────────────────────
pt_ullswick = _caller(
    "pt_ullswick",
    "Nora Ullswick",
    86,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "New lower denture fitted recently per the last note; adjusting slowly.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, bendroflumethiazide "
        "2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It is Nora Ullswick, and I shall give it to you the way my neighbour told me to say it, "
        "all in one.\n\n"
        "The out-of-hours doctor gave me fluconazole capsules on Monday for thrush under my new denture. "
        "I have been eating small — the denture, then the sore mouth on top — and twice before lunch this "
        "week I have gone swimmy and had to hold the table. A ginger biscuit and it passes. I am quite "
        "well as we speak. But I am on gliclazide with my breakfast and my tea, and the diabetes clinic "
        "always said: new tablets next to the gliclazide, come in the same day and let them look before "
        "the next dose goes down. Tea in this house is five o'clock."
    ),
    onset="The capsules started Monday. The swimmy spells have been this week, before lunch.",
    severity="A ginger biscuit sees it off. It is the teatime dose that wants a decision today.",
    history="Diabetes since I was seventy. The clinic knows me well.",
    medications=(
        "Gliclazide twice a day, the water tablet in the morning — and the capsules since Monday."
    ),
    context="My neighbour Joan Verrall does my shopping and can walk me round whenever you say.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_ullswick_ooh_fluconazole_new_denture",
)

#: Split piece 1: the small eating and the settled swims, self-discounted (the capsules ride Joan).
ULLSWICK_SPLIT_INTAKE = (
    "Hello. It is Nora Ullswick. Nothing dramatic — I want my repeat put through, the gliclazide and my "
    "water tablet, and the chemist will sort the rest.\n\n"
    "And since you ask how I am: eating small with this new denture, and I went a bit swimmy holding the "
    "table twice this week before lunch — a ginger biscuit sees it off, and I am quite well as we speak. "
    "My neighbour says mention it, so I have. And mention this too, she says: my second gliclazide goes "
    "down with my tea at five o'clock, and the diabetes clinic always said new tablets next to the "
    "gliclazide are a same-day matter with them — not that I have any new tablets, you understand. I "
    "leave it with you — Joan can walk me round whenever you say, if you should want me looked at."
)

pt_verrall = _caller(
    "pt_verrall",
    "Joan Verrall",
    74,
    "F",
    chart=(
        "Dry eyes; uses lubricant drops. Otherwise well.",
        "Repeat medication: carmellose eye drops as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Might I have my eye drops on repeat again — the carmellose ones? The box is "
        "nearly out and my eyes do complain without them. No urgency, whenever it goes through."
    ),
    onset="Nothing new; the drops are low.",
    severity="Only the dry eyes, same as always.",
    history="Dry eyes for years; nothing else troubles me.",
    medications="The eye drops, morning and night.",
    context="I do the shopping for my neighbour Nora Ullswick and walk her to her appointments.",
    gold=_routine_gold(),
    source="authored:gf_carrier_verrall_eye_drops",
)

#: Split piece 2: her drops, plus the capsules she collected for Nora on Monday.
VERRALL_SPLIT_INTAKE = (
    "Good morning. Might I have my eye drops on repeat again — the carmellose ones? No urgency.\n\n"
    "And one thing for Nora Ullswick's record, my neighbour — I collect for her. The out-of-hours doctor "
    "gave her fluconazole capsules on Monday, for thrush under that new denture of hers. The chemist "
    "said her surgery should have it written down, so I promised Nora I would pass it on when I rang "
    "about my drops."
)

# ── contest 9: Cyril Varnbrook ─────────────────────────────────────────────────────────────────────────────
pt_varnbrook = _caller(
    "pt_varnbrook",
    "Cyril Varnbrook",
    81,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Denture wearer; last dental note records persistent soreness under the upper plate.",
        "Repeat medication: gliclazide 80 mg twice daily, finasteride 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My dentist has written me a letter and the long and short of it is thrush — under the "
        "top plate — and fluconazole capsules for two weeks, which I started yesterday. The letter says "
        "notify my own doctor, and there is more I ought to say while I am on.\n\n"
        "My eating has gone to pot with the sore mouth, and this morning before my breakfast I went "
        "trembly enough that I sat back down and had the toast first and the wash after. It passed with "
        "the toast, and I am right now. I am on gliclazide twice a day for the sugar, and the clinic have "
        "told me in the past that a new medicine started against it is a same-day matter for them — seen "
        "before the next tablet, and my next is with my tea at five."
    ),
    onset="The dentist's capsules started yesterday. The trembly start was this morning, before breakfast.",
    severity="Toast put it right and I am steady now. The five o'clock tablet is what wants deciding.",
    history="Diabetes eleven years. The plate has been a nuisance all winter.",
    medications="Gliclazide morning and teatime, finasteride at night — and the dentist's fluconazole.",
    context="My neighbour Ted has a car and owes me a favour; any time today can be managed.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_varnbrook_dentist_letter_fluconazole",
)

#: Split piece 1: the dentist's letter as admin (the trembly breakfast rides Ted).
VARNBROOK_SPLIT_INTAKE = (
    "Morning. My dentist has written me a letter and asked me to notify my own doctor, so here it is: "
    "thrush under the top plate, and she has started me on fluconazole capsules for two weeks, as of "
    "yesterday. That is the whole message — put it with my notes and I shall let you get on."
)

pt_upperton = _caller(
    "pt_upperton",
    "Ted Upperton",
    70,
    "M",
    chart=(
        "Raised cholesterol on treatment; annual review in date.",
        "Repeat medication: simvastatin 40 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — repeat prescription, please. The simvastatin. I am away at my sister's next week so if "
        "it could go through before the weekend that would suit."
    ),
    onset="Nothing new; the repeat is due before I travel.",
    severity="Fit as a flea, me.",
    history="The cholesterol, on a statin for donkey's years.",
    medications="Simvastatin at night.",
    context="Next door to Cyril Varnbrook; I run him about when the buses let him down.",
    gold=_routine_gold(),
    source="authored:gf_carrier_upperton_statin",
)

#: Split piece 2: his statin, plus this morning over the fence.
UPPERTON_SPLIT_INTAKE = (
    "Hello — repeat prescription, please. The simvastatin, before the weekend if it can be done.\n\n"
    "And a word about my neighbour Cyril Varnbrook, with his blessing. He told me over the fence he went "
    "trembly before his breakfast this morning — sat back down, had his toast, came right, and he is pottering "
    "about as normal now. He is eating poorly with that sore mouth of his, though, and he takes his "
    "sugar tablet with his tea at five — and his clinic have told him, he says, that a new medicine "
    "started against it is a same-day matter, seen before the next tablet. Not that either of us knows "
    "of anything new against it. He is not one to make a fuss, which is exactly why I said I would "
    "mention it. Worth setting against his notes, I thought — and if he is wanted in, I have the car "
    "and owe him a favour; any time today can be managed."
)

# ── contest 10: Marjorie Vauxmead ──────────────────────────────────────────────────────────────────────────
pt_vauxmead = _caller(
    "pt_vauxmead",
    "Marjorie Vauxmead",
    78,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviewed at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Weight noted as drifting down at the last review; dietitian leaflet given.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, latanoprost drops at "
        "night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I have my list here so I do not forget anything, if you will bear with me.\n\n"
        "One: the out-of-hours doctor started me on fluconazole capsules at the weekend, for thrush. "
        "Two: my appetite has been poor for a while — you will have it in my notes, the weight — and it "
        "is poorer with the sore mouth. Three: twice this week, before meals, I have gone light-headed "
        "and had to sit; orange squash and a digestive put me right both times, and I am right now. "
        "Four, and this is why it is today and not next week: I take gliclazide with breakfast and with "
        "my evening meal, and the diabetes clinic have always said a new medicine started beside it "
        "means they see me the same day, before the evening tablet. I eat at five."
    ),
    onset="The capsules started at the weekend. The light-headed spells were twice this week, before meals.",
    severity="Squash and a digestive mend it, and I am well now. The evening tablet is the deadline in my head.",
    history="Diabetes fourteen years; the eyes get their drops for pressure. Your clinic does my reviews.",
    medications=(
        "Gliclazide morning and evening meal, the eye drops at night — and the weekend's fluconazole."
    ),
    context="My friend Rita drives me on a Thursday anyway and says today is no bother at all.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vauxmead_ooh_fluconazole_poor_appetite",
)

#: Split piece 1: the settled spells inside a routine drops ask (the capsules ride Rita).
VAUXMEAD_SPLIT_INTAKE = (
    "Hello. Only my repeat, please — the eye drops, the latanoprost, and the gliclazide while you are "
    "in there.\n\n"
    "And I shall mention, because my friend said I ought: I have gone light-headed before meals twice "
    "this week — I sit, I have my squash and a digestive, and I am perfectly well after. My appetite has "
    "been poor, which will be the size of it. And since my list says say so: my evening gliclazide goes "
    "down when I eat at five, and the diabetes clinic have always said a new medicine started beside it "
    "means they see me the same day — nothing new has been started beside it, I should say. No fuss "
    "from me either way — Rita drives, so if you ever wanted me in, today or any day, it is easily done."
)

pt_venmore = _caller(
    "pt_venmore",
    "Rita Venmore",
    67,
    "F",
    chart=(
        "Osteoarthritis of the knee, managed conservatively; physiotherapy completed.",
        "Repeat medication: paracetamol 1 g as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Could I book an ordinary appointment about my knee? The arthritis one. It is grumbling "
        "on the stairs again — nothing sudden, the same old knee — and I would like it looked at when "
        "there is a sensible gap. Any day, honestly."
    ),
    onset="The knee has grumbled for years; a bit more this fortnight.",
    severity="A grumble, not a drama. Paracetamol keeps it civil.",
    history="The knee, worn cartilage they said; physio helped for a while.",
    medications="Paracetamol when it plays up.",
    context="I drive my friend Marjorie Vauxmead to her appointments on Thursdays.",
    gold=_routine_gold(),
    source="authored:gf_carrier_venmore_knee",
)

#: Split piece 2: her knee booking, plus the capsules she collected at the weekend.
VENMORE_SPLIT_INTAKE = (
    "Morning. Could I book an ordinary appointment about my knee? The same old arthritis one — any day "
    "suits.\n\n"
    "And a message for Marjorie Vauxmead's notes, my friend — I picked her prescription up from the "
    "out-of-hours place at the weekend: fluconazole capsules, for thrush. The pharmacist said her own "
    "surgery should know, so I am passing it on as asked."
)

# ── contest 11: Wilfred Underhurst ─────────────────────────────────────────────────────────────────────────
pt_underhurst = _caller(
    "pt_underhurst",
    "Wilfred Underhurst",
    87,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Hearing aid user; prefers face-to-face over telephone per communication note.",
        "Repeat medication: gliclazide 40 mg with breakfast and with evening meal, docusate as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — you will have to bear with my hearing. I shall say my piece slowly.\n\n"
        "The weekend doctor — the out-of-hours one — started me on fluconazole capsules for thrush in my "
        "mouth. That was Sunday. My eating has been poor with the soreness, mostly soup, and yesterday "
        "before my dinner I went shaky and had to sit with the biscuit tin till it passed — ten minutes, "
        "no more, and nothing since. I am on the gliclazide for my sugar, morning and teatime, and the "
        "diabetes clinic said to me and my late wife both: a new medicine put next to it means they see "
        "me that same day, before the teatime one goes down. I have mine at five with the news."
    ),
    onset="Sunday for the capsules. The shaky spell was yesterday before dinner.",
    severity="Ten minutes with the biscuit tin and it passed; I am steady today. The five o'clock tablet is why I rang.",
    history="Diabetes since my seventies. The clinic has had me on the same tablets a long while.",
    medications="Gliclazide twice a day, the softener when needed — and the weekend doctor's capsules.",
    context="My neighbour Frank takes me in his car; mornings or afternoons, we can do either today.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_underhurst_ooh_fluconazole_soup_diet",
)

#: Split piece 1: the capsules as record-keeping in a slow, careful errand call (the shakes ride Frank).
UNDERHURST_SPLIT_INTAKE = (
    "Hello — you will have to bear with my hearing. Two small things, said slowly.\n\n"
    "My repeat, please: the chemist keeps my list, my usual tablets and the softeners. And the chemist "
    "asked me to tell you the weekend doctor started me on fluconazole capsules on Sunday, for thrush "
    "in my mouth, so your records match theirs. That is everything from me, thank you kindly."
)

pt_ullmead = _caller(
    "pt_ullmead",
    "Frank Ullmead",
    72,
    "M",
    chart=(
        "Heart failure, stable, under annual cardiology review elsewhere documented as in date.",
        "Repeat medication: furosemide 40 mg each morning, ramipril 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Repeat for my water tablets, please — the furosemide — and the ramipril with them. "
        "I am not out yet, just keeping ahead of the weekend."
    ),
    onset="Nothing new; ordering ahead.",
    severity="Ticking over nicely.",
    history="The heart, kept steady these last few years on the same two tablets.",
    medications="The water tablet first thing, ramipril with it.",
    context="I drive my neighbour Wilf Underhurst about; his hearing makes phones hard work.",
    gold=_routine_gold(),
    source="authored:gf_carrier_ullmead_furosemide",
)

#: Split piece 2: his repeats, plus yesterday's biscuit tin as Wilf told it to him.
ULLMEAD_SPLIT_INTAKE = (
    "Morning. Repeat for my water tablets, please — the furosemide — and the ramipril with them.\n\n"
    "And I promised Wilf Underhurst next door I would pass this on, his hearing being what it is: he "
    "went shaky before his dinner yesterday and sat with the biscuit tin ten minutes till it passed — "
    "he is steady today and making light of it. He is living on soup with that sore mouth, mind, and he "
    "takes his sugar tablet at five with the news — and Wilf says the diabetes clinic told him and his "
    "late wife both, a new medicine put next to it means they see him that same day — though nothing new "
    "has been put next to it that he told me of. His words: put it with whatever his notes say and "
    "let them decide. I drive him about — mornings or afternoons, we can do either today."
)

# ── contest 12: Gwen Uttergill ─────────────────────────────────────────────────────────────────────────────
pt_uttergill = _caller(
    "pt_uttergill",
    "Gwen Uttergill",
    83,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Carer for her husband per the household note; time-pressed for appointments historically.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, cetirizine 10 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I will be quick because my husband cannot be left long.\n\n"
        "The out-of-hours doctor gave me fluconazole capsules on Saturday for thrush. With one thing and "
        "another I have been skipping lunches — you try cooking twice over for two of you — and twice "
        "since the weekend I have come over sweaty and dizzy before I ate, which a glucose sweet from my "
        "handbag sorted in minutes. I am perfectly capable today. But I am on gliclazide twice a day, "
        "and the diabetes clinic's rule, said to me at every review, is: new medicine next to the "
        "gliclazide, be seen the same day, before the evening dose. I take mine when I give him his tea "
        "— five o'clock, regular as the clock."
    ),
    onset="Saturday for the capsules. The sweaty, dizzy spells have been twice since the weekend, before food.",
    severity="A glucose sweet mends it in minutes and I am capable today. It is the five o'clock dose that matters.",
    history="Diabetes nine years. I carry the glucose sweets because the clinic told me to.",
    medications="Gliclazide twice a day, an allergy tablet in the morning — and the capsules since Saturday.",
    context="My neighbour Doreen sits with my husband when I have appointments; she is free this afternoon.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_uttergill_ooh_fluconazole_carer_skipped_lunches",
)

#: Split piece 1: the skipped lunches and settled dizziness, self-discounted (the capsules ride Doreen).
UTTERGILL_SPLIT_INTAKE = (
    "Hello. I will be quick because my husband cannot be left long. My repeat, please — the gliclazide "
    "and my allergy tablet.\n\n"
    "And put in my notes if you would: I have come over sweaty and dizzy before meals twice since the "
    "weekend — a glucose sweet from my handbag sorts it in minutes, and I am perfectly capable today. I "
    "skip lunches more than I should, caring for my husband as I do, and that will be the story. My own "
    "tablet goes down when I give him his tea at five, and the clinic's rule, said to me at every "
    "review, is that a new medicine next to the gliclazide is a same-day matter — my own tablets are as "
    "they always were, I am glad to say. I shall leave it in your hands; Doreen can sit with my "
    "husband if ever you should want me up there."
)

pt_vickridge = _caller(
    "pt_vickridge",
    "Doreen Vickridge",
    69,
    "F",
    chart=(
        "Hypothyroidism, stable on levothyroxine; annual bloods in date.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. My thyroid tablet repeat, please — the levothyroxine, the hundred strength. The "
        "chemist flagged it is due. No rush otherwise."
    ),
    onset="Nothing new; the repeat came due.",
    severity="Well in myself.",
    history="The thyroid, steady on the same dose a long time.",
    medications="Levothyroxine each morning.",
    context="I sit with Gwen Uttergill's husband when she has errands; we are two doors apart.",
    gold=_routine_gold(),
    source="authored:gf_carrier_vickridge_levothyroxine",
)

#: Split piece 2: her repeat, plus Saturday's out-of-hours capsules from over the fence.
VICKRIDGE_SPLIT_INTAKE = (
    "Good morning. My thyroid tablet repeat, please — the levothyroxine, the hundred strength.\n\n"
    "And a note for Gwen Uttergill's file, two doors from me: the out-of-hours doctor gave her "
    "fluconazole capsules on Saturday, for thrush — I minded her husband while she went. She said to "
    "mention it to the surgery when I rang, so consider it mentioned."
)

# ══ CLAIMANTS 13-14: three-piece splits (intake + carrier + one ring-back) ═════════════════════════════════

# ── contest 13: Stanley Vexford ────────────────────────────────────────────────────────────────────────────
pt_vexford = _caller(
    "pt_vexford",
    "Stanley Vexford",
    80,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Independent; walks to the parade of shops daily per social note.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, aspirin 75 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Stanley Vexford. I shall lay it out like a shopping list.\n\n"
        "Thrush, the out-of-hours doctor, fluconazole capsules — started Monday. Appetite gone to pot "
        "with the sore mouth; my daughter says I am leaving more than I eat. And yesterday in the queue "
        "at the post office I went woolly-headed and had to lean on the counter — the girl fetched me a "
        "chair and a barley sugar and I was myself in ten minutes, walked home after. Right as rain "
        "today. But the gliclazide: the diabetes clinic have said, more than once, a new medicine "
        "started beside it means a same-day look, before the next tablet. Mine is at teatime, five "
        "o'clock, and I would like it settled before then."
    ),
    onset="Monday for the capsules. The woolly turn was yesterday in the post office queue.",
    severity="A chair and a barley sugar mended it; I walked home. It is today's teatime tablet that needs an answer.",
    history="Diabetes twelve years, aspirin nearly as long. Your clinic reviews me.",
    medications="Gliclazide twice a day, the baby aspirin — and the capsules since Monday.",
    context="My daughter Lynn is nearby and I can walk to you in fifteen minutes on a good day.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vexford_ooh_fluconazole_post_office",
)

#: Split piece 1: the capsules as a record errand (the post office rides Lynn; the appetite rides his own
#: ring-back).
VEXFORD_SPLIT_INTAKE = (
    "Morning. Stanley Vexford. A small errand: the chemist said tell my surgery the out-of-hours doctor "
    "started me on fluconazole capsules on Monday, for thrush. So there it is for the record. And while "
    "I am on, my repeat is about due — the chemist keeps the list. Thank you."
)

#: Split piece 3: his ONE ring-back, later in the morning — the half he forgot to say.
VEXFORD_RECALL_TEXT = (
    "Stanley Vexford again — I rang earlier about my record and my repeat. My daughter says I undersold "
    "it, so here is the rest. My appetite has gone to pot with this sore mouth; I am leaving more than I "
    "eat. And for the book while I am on: I take my gliclazide at five with my tea, and the diabetes "
    "clinic have said more than once that a new medicine started beside it means a same-day look — "
    "though nobody has touched my sugar tablets, mind, so I do not suppose that is today's business. "
    "What to do with it, if anything, I leave to you — I can walk up in fifteen minutes on a good day."
)

pt_vexford_l = _caller(
    "pt_vexford_l",
    "Lynn Vexford",
    50,
    "F",
    chart=(
        "Asthma, mild; annual review due this season.",
        "Repeat medication: salbutamol inhaler as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi — could I book my asthma review? The reminder came through and I keep forgetting. Any "
        "afternoon in the next few weeks works."
    ),
    onset="No flare — the review is due, that is all.",
    severity="The blue inhaler barely leaves the drawer.",
    history="Mild asthma since my twenties.",
    medications="The reliever inhaler, rarely.",
    context="My dad, Stanley Vexford, is round the corner; I look in most evenings.",
    gold=_routine_gold(),
    source="authored:gf_carrier_vexford_daughter_asthma_review",
)

#: Split piece 2: her review booking, plus yesterday's post office as the parade told it to her.
VEXFORD_L_SPLIT_INTAKE = (
    "Hi — could I book my asthma review? Any afternoon in the next few weeks works.\n\n"
    "Separately, about my dad, Stanley Vexford: the woman in the post office told me he went "
    "woolly-headed in the queue yesterday — they sat him down with a barley sugar and he was himself in "
    "ten minutes and walked home. He is playing it down, which is his way. He is fine today, pottering. "
    "But could somebody run an eye over his record with that in mind — and if it wants him seen, he "
    "can walk to you in fifteen minutes, or I can take him."
)

# ── contest 14: Betty Vinstowe ─────────────────────────────────────────────────────────────────────────────
pt_vinstowe = _caller(
    "pt_vinstowe",
    "Betty Vinstowe",
    89,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide, long-standing; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Denture wearer; last note records a dental appointment for persistent mouth soreness.",
        "Repeat medication: gliclazide 40 mg with breakfast and with evening meal, adcal-D3 twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, dear. Betty Vinstowe. My dentist has sent me home with a letter and my neighbour said "
        "ring it through, so I am ringing.\n\n"
        "The letter says thrush — under the dentures — and she has started me on fluconazole, one "
        "capsule a day for a fortnight; it asks my own doctor to make a note. And I shall own up to the "
        "rest while I am on: the mouth has me eating next to nothing, and twice this week before meals I "
        "have gone trembly and sat down sharpish — barley water and a plain biscuit and I come round in "
        "no time. I am come round now, right as a trivet. But my sugar tablet, the gliclazide, goes down with "
        "my tea at five, and the diabetes clinic said long ago that a new medicine next to it means "
        "they see me the same day, first."
    ),
    onset="The dentist's capsules this week. The trembly spells, twice, before meals.",
    severity="Barley water and a biscuit and I come round. Right as a trivet now; it is the five o'clock tablet in question.",
    history="Diabetes twenty-two years. The clinic has minded my sugar all that while.",
    medications="Gliclazide twice a day, the calcium twice a day — and the dentist's capsules.",
    context="My neighbour George Uphill drives me; he says any hour today is manageable.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vinstowe_dentist_letter_fluconazole",
)

#: Split piece 1: the eating and the settled trembles, self-discounted (the letter rides George; the
#: capsule name arrives with her own ring-back once she finds the box).
VINSTOWE_SPLIT_INTAKE = (
    "Hello, dear. Betty Vinstowe. Nothing that needs any fuss, I promise. I want my repeat put "
    "through — the gliclazide and my calcium — and I shall mention, since my neighbour says I must: "
    "this sore mouth has me eating next to nothing, and twice this week I went trembly before meals and "
    "sat down sharpish. Barley water and a plain biscuit and I come round in no time; I am quite "
    "restored this minute. My sugar tablet goes down with my tea at five, and the diabetes clinic said "
    "long ago that a new medicine next to it means they see me the same day, first — though nothing is "
    "next to it at present, so far as I know. I shall leave it with you, dear — George next door "
    "drives me wherever I am wanted, today included."
)

#: Split piece 3: her ONE ring-back — she has found the dentist's box and reads the name off it.
VINSTOWE_RECALL_TEXT = (
    "It is Betty Vinstowe again, dear — I rang this morning about my repeat. I have found the box from "
    "the dentist to read you the name properly: fluconazole, one capsule a day, a fortnight of them, "
    "for the thrush under my dentures. Her letter says my own doctor is to make a note, so there is "
    "the name for whoever writes it in."
)

pt_uphill = _caller(
    "pt_uphill",
    "George Uphill",
    75,
    "M",
    chart=(
        "Hypertension, controlled; annual review in date.",
        "Repeat medication: amlodipine 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. George Uphill — my blood pressure tablet wants renewing, the amlodipine. The chemist "
        "says this week if possible. That is the lot."
    ),
    onset="Nothing new; the renewal is due.",
    severity="Sound as a pound.",
    history="Blood pressure, well behaved on the one tablet.",
    medications="Amlodipine each morning.",
    context="I drive my neighbour Betty Vinstowe where she needs to be; she has no family close.",
    gold=_routine_gold(),
    source="authored:gf_carrier_uphill_amlodipine",
)

#: Split piece 2: his renewal, plus the dentist's letter he drove her home with.
UPHILL_SPLIT_INTAKE = (
    "Morning. George Uphill — my blood pressure tablet wants renewing, the amlodipine.\n\n"
    "And one for Betty Vinstowe's notes, my neighbour: I drove her back from the dentist and there is a "
    "letter for her doctor in her bag — the dentist has started her on capsules for thrush under the "
    "dentures and wants it noted for her own doctor. Betty was going to ring the name of it through "
    "herself once she found the box; I said I would flag the letter as well, so it is not lost either way."
)

# ══ CLAIMANTS 15-28: same-patient splits (piece 1 = routine intake, piece 2 = their ONE ring-back) ═════════

# ── contest 15: Eric Upcombe ───────────────────────────────────────────────────────────────────────────────
pt_upcombe = _caller(
    "pt_upcombe",
    "Eric Upcombe",
    76,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, sertraline 50 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Eric Upcombe here. Full story, then you can tell me what happens next.\n\n"
        "The out-of-hours doctor started me on fluconazole capsules on Sunday for thrush. My eating has "
        "been thin all week with the mouth, and before lunch yesterday I went light-headed enough to "
        "put my head between my knees in the hallway — a glass of milk and a slice of bread and I was "
        "square again inside the quarter hour, and I have been square since. Thing is the gliclazide, "
        "twice a day. The diabetes clinic's line has always been: a new medicine started against it and "
        "they see me the same day, ahead of the next tablet. Mine is at five with my tea, so it is "
        "today's business, not tomorrow's."
    ),
    onset="Sunday for the capsules. The light-headed spell was yesterday before lunch.",
    severity="Milk and bread squared me in a quarter hour. Square now — the five o'clock tablet is the question.",
    history="Diabetes ten years; the mood tablet a couple of years, no trouble with it.",
    medications="Gliclazide twice a day, sertraline in the morning — and the capsules since Sunday.",
    context="I am on the bus route and spry enough; any time today I can be with you.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_upcombe_ooh_fluconazole_hallway",
)

#: Split piece 1: the capsules as record-keeping (the hallway rides his ring-back).
UPCOMBE_SPLIT_INTAKE = (
    "Morning. Eric Upcombe here. Just squaring the paperwork: the out-of-hours doctor started me on "
    "fluconazole capsules on Sunday, for thrush, and the chemist said make sure my own surgery has it. "
    "So now you have it. My repeat will want doing next week too — the chemist keeps my list — but "
    "there is no rush on that today."
)

UPCOMBE_RECALL_TEXT = (
    "Eric Upcombe again — I rang earlier about my record. I left half of it out, my wife tells me. My "
    "eating has been thin all week with this mouth, and before lunch yesterday I went light-headed "
    "enough to put my head between my knees — milk and bread squared me in a quarter hour and I have "
    "been square since. I take my sugar tablet at five with my tea, and the diabetes clinic's line has "
    "always been that a new medicine started against it is a same-day matter — not that anyone has "
    "touched my sugar tablets, mind. The wife just wanted it all said; what happens next I leave with "
    "you — I am on the bus route and spry enough, any hour today."
)

# ── contest 16: Hilda Usworth ──────────────────────────────────────────────────────────────────────────────
pt_usworth = _caller(
    "pt_usworth",
    "Hilda Usworth",
    85,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, omeprazole 20 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Hilda Usworth. I have thought about how to say this on the walk to the phone, so here "
        "goes.\n\n"
        "I have thrush, and the out-of-hours doctor put me on fluconazole capsules on Saturday. I have "
        "been eating very little — the mouth, and my stomach has never been a big eater's — and "
        "mid-morning today I came over sweaty and strange at the kitchen table; two squares of "
        "chocolate and ten minutes and it lifted entirely. I am quite myself talking to you now. But my "
        "gliclazide is due again with my evening meal, and the diabetes clinic has said as long as I "
        "have known them: new medicine alongside it, same-day review, before that dose. I eat at five, "
        "so there is the clock on it."
    ),
    onset="Saturday for the capsules. The sweaty, strange spell was mid-morning today, at the table.",
    severity="Chocolate lifted it entirely in ten minutes. Quite myself now — the evening dose is the deadline.",
    history="Diabetes eighteen years; the stomach tablet keeps the indigestion off.",
    medications="Gliclazide twice a day, omeprazole in the morning — and Saturday's capsules.",
    context="My great-nephew can taxi me at short notice; afternoons are easiest but any time today can be done.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_usworth_ooh_fluconazole_kitchen_table",
)

#: Split piece 1: the settled spell, self-discounted, in a routine ask (the capsules ride her ring-back).
USWORTH_SPLIT_INTAKE = (
    "Hello. Hilda Usworth. Nothing grand — my repeat wants doing, the gliclazide and the stomach "
    "tablet.\n\n"
    "And for honesty's sake: I came over sweaty and strange at the kitchen table mid-morning today — "
    "two squares of chocolate and ten minutes and it lifted entirely, and I am quite myself now. I eat "
    "very little these days, which will be most of it. My evening meal — when the second gliclazide "
    "goes down — is at five o'clock, and the diabetes clinic has said as long as I have known them: a "
    "new medicine alongside it, same-day review — not that anything is alongside it just now, mind. I "
    "shall be by the phone all day, and my great-nephew can taxi me in at short notice — so do as you "
    "think best."
)

USWORTH_RECALL_TEXT = (
    "It is Hilda Usworth again — I rang about my repeat this morning. I forgot the one thing my niece "
    "told me to say first: the out-of-hours doctor put me on fluconazole capsules on Saturday, for "
    "thrush. The chemist said my surgery should have it on the record, so there it is."
)

# ── contest 17: Norman Uppermill ───────────────────────────────────────────────────────────────────────────
pt_uppermill = _caller(
    "pt_uppermill",
    "Norman Uppermill",
    74,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 160 mg with breakfast, 80 mg with evening meal, allopurinol "
        "100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Norman Uppermill. I went private on Monday — my choice, the wait was getting to me — "
        "about thrush in the mouth, and the chap started me on fluconazole, a fortnight's course, and "
        "told me squarely to inform my own GP. Informing you is half of this call.\n\n"
        "The other half: I have been shaky before my tea these last two evenings — I sugar a cup of "
        "coffee and it passes inside ten minutes, and I am steady as a rock right now. My meals have "
        "shrunk with the sore mouth, no denying it. I am on a good dose of gliclazide, and the diabetes "
        "clinic's standing instruction to me has been: new medicine started beside it, same-day review "
        "before the next tablet. The next tablet is teatime today."
    ),
    onset="Monday for the private chap's capsules. The shaky spells, the last two evenings before tea.",
    severity="Sweet coffee sees it off inside ten minutes. Steady now; teatime's tablet is the deadline.",
    history="Diabetes seven years, gout longer. Your clinic runs my sugar reviews.",
    medications=(
        "Gliclazide, the big breakfast dose and a teatime one, allopurinol daily — and the private "
        "fluconazole since Monday."
    ),
    context="Retired early, own car, five minutes off. Name the hour and I am there.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_uppermill_private_fluconazole",
)

#: Split piece 1: the private prescription phoned through as instructed (the evenings ride his ring-back).
UPPERMILL_SPLIT_INTAKE = (
    "Morning. Norman Uppermill. Doing as I was squarely told: I went private on Monday about thrush in "
    "the mouth, and the chap there started me on fluconazole, a fortnight's course, and said inform my "
    "own GP. You are informed. Nothing else today, thank you."
)

UPPERMILL_RECALL_TEXT = (
    "Norman Uppermill again — I rang first thing about my record. My wife has sent me back to the "
    "phone with the rest of it: I have been shaky before my tea the last two evenings — sweet coffee "
    "sees it off in ten minutes, steady as a rock in between — and my meals have shrunk with the sore "
    "mouth. My teatime gliclazide is at five, and the diabetes clinic's standing instruction to me has "
    "been a same-day review before the next tablet whenever a new medicine starts beside it — though "
    "nobody has laid a finger on my sugar tablets, so I shall not go claiming their rule for myself. "
    "My wife wanted it logged; what you do with it is your department. Own car, five minutes off, if "
    "ever I am wanted."
)

# ── contest 18: Olive Vardale ──────────────────────────────────────────────────────────────────────────────
pt_vardale = _caller(
    "pt_vardale",
    "Olive Vardale",
    91,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide, long-standing; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Lives with her son per household note; uses a wheeled frame outdoors.",
        "Repeat medication: gliclazide 40 mg with breakfast and with evening meal, paracetamol as "
        "required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Olive Vardale — ninety-one, and my son is stood here making sure I say it all.\n\n"
        "The out-of-hours doctor came to the house on Sunday and started me on fluconazole capsules for "
        "thrush. I eat like a wren at the best of times and less this week with the mouth. Twice since "
        "— once before Sunday dinner, once yesterday — I have gone swimmy in my chair, and my son gives "
        "me my lucozade and I come back to myself in minutes. I am back to myself now, before you ask. "
        "But the gliclazide is the thing: the diabetes clinic told my son, new medicine put next to it "
        "and they want me the same day, ahead of the evening tablet. My tablet comes with my tea at "
        "five, and my son says he is not giving it me till a doctor says so."
    ),
    onset="Sunday for the capsules, at the house. The swimmy spells, Sunday dinner and yesterday.",
    severity="Lucozade brings me back in minutes; I am back now. The five o'clock tablet is held hostage to your answer.",
    history="Diabetes since before some of your doctors were born, I should think. The clinic minds it.",
    medications="Gliclazide twice a day, paracetamol for my hips — and the Sunday capsules.",
    context="My son is home all day with the car. We can come the moment you say.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vardale_ooh_home_visit_fluconazole",
)

#: Split piece 1: the wren appetite and the settled swims, self-discounted (the capsules ride her ring-back —
#: or rather her son's hand steadying hers on the phone, same caller either way).
VARDALE_SPLIT_INTAKE = (
    "Hello. Olive Vardale — ninety-one, since you will have it on the screen anyway. My repeat, please: "
    "the gliclazide, and my paracetamol.\n\n"
    "And my son says say this too: I have gone swimmy in my chair twice this week — he gives me my "
    "lucozade and I come back to myself in minutes, and I am back now. I eat like a wren, which he "
    "will tell you is the cause. And he says say this as well: my tablet comes with my tea at five, "
    "and the diabetes clinic told him a new medicine put next to it means they want me seen the same "
    "day — not that anything new has been put next to it, that I could name. There. My son is home "
    "all day with the car, so whatever you make of it, we can come the moment anybody says the word."
)

VARDALE_RECALL_TEXT = (
    "Olive Vardale again, dear — my son has the out-of-hours paper in his hand and says I never gave "
    "you the medicine. Fluconazole capsules, started Sunday when their doctor came to the house, for "
    "the thrush. He wants it put on my notes properly, so there it is, and he is satisfied at last."
)

# ── contest 19: Reg Velthorpe ──────────────────────────────────────────────────────────────────────────────
pt_velthorpe = _caller(
    "pt_velthorpe",
    "Reg Velthorpe",
    78,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Denture wearer; dental notes record a refit consultation this season.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, latanoprost drops at "
        "night.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Reg Velthorpe. My dentist found thrush under the plate on Tuesday and has me on "
        "fluconazole — her letter is on my kitchen table and it says my GP is to be told, so, told.\n\n"
        "Now the part I would rather not say but will: the mouth has me down to soft food and not much "
        "of it, and twice this week — mid-morning both times — I have gone trembly and had to sit with "
        "sweet tea till it passed, ten minutes at the outside, right as anything after. Right as "
        "anything now. The gliclazide is twice a day, and the diabetes clinic said to me at my last "
        "review, in so many words: anything new started alongside it, we see you the same day, before "
        "your next dose. Next dose, five o'clock, with my tea."
    ),
    onset="Tuesday for the dentist's capsules. The trembly spells, twice this week, mid-morning.",
    severity="Sweet tea and ten minutes mends it; right as anything now. The five o'clock dose needs ruling on today.",
    history="Diabetes thirteen years; the eye drops for pressure. The clinic reviews me yearly and between.",
    medications="Gliclazide twice a day, drops at night — and the dentist's fluconazole since Tuesday.",
    context="My grandson stops by after college; failing him, the community bus passes your door.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_velthorpe_dentist_fluconazole_soft_food",
)

#: Split piece 1: the dentist's letter as an errand (the mornings ride his ring-back).
VELTHORPE_SPLIT_INTAKE = (
    "Morning. Reg Velthorpe. An errand, no more: my dentist found thrush under the plate on Tuesday "
    "and has started me on fluconazole — her letter says my GP is to be told, so, told. Put it with my "
    "notes, would you. Good morning to you."
)

VELTHORPE_RECALL_TEXT = (
    "Reg Velthorpe again — I rang this morning on an errand, and this is the part I sat on. The mouth "
    "has me down to soft food and not much of it, and twice this week mid-morning I went trembly and "
    "sat with sweet tea ten minutes till it passed. Right as anything in between, and now. I take my "
    "gliclazide at five with my tea, and the clinic said at my last review that anything new started "
    "alongside it means they see me the same day — my sugar tablets are just as they were, mind, so I "
    "only pass their rule on for completeness. My daughter wanted it all said somewhere; the doing, "
    "if any, I leave to you — the community bus passes your door, if it comes to that."
)

# ── contest 20: Jean Vyebrook ──────────────────────────────────────────────────────────────────────────────
pt_vyebrook = _caller(
    "pt_vyebrook",
    "Jean Vyebrook",
    82,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Active in the parish per social note; walks to church twice weekly.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, bisoprolol 2.5 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Jean Vyebrook. I shall tell it the way I told the vicar's wife, only with the medical "
        "bits put back in.\n\n"
        "The out-of-hours doctor started me on fluconazole capsules on Friday evening, for thrush. I "
        "have been off my food all week — the mouth stings with anything sharp — and at the coffee "
        "morning yesterday I went light-headed by the urn and had to be sat down; half a cup of sweet "
        "tea and one of their custard creams and I was carrying trays again in fifteen minutes. So I am "
        "not poorly as I speak. But I take gliclazide morning and teatime, and the diabetes clinic have "
        "always been strict with me: a new medicine started against it is a same-day appointment, "
        "before the teatime tablet. I take mine at five sharp."
    ),
    onset="Friday evening for the capsules. The light-headed spell was yesterday, at the coffee morning.",
    severity="Sweet tea and a custard cream and I was carrying trays again. Well now; the five o'clock tablet is why it is today.",
    history="Diabetes sixteen years; the heart tablet keeps my pulse tidy. Your clinic minds the sugar.",
    medications="Gliclazide twice a day, bisoprolol in the morning — and Friday's capsules.",
    context="Half the parish drives; I can be brought in at whatever hour you say today.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vyebrook_ooh_fluconazole_coffee_morning",
)

#: Split piece 1: the urn moment, self-discounted, inside a routine ask (the capsules ride her ring-back).
VYEBROOK_SPLIT_INTAKE = (
    "Hello. Jean Vyebrook. Two ordinary things: my repeat — the gliclazide and the bisoprolol — and "
    "would you note I went a touch light-headed at the church coffee morning yesterday. They sat me "
    "down by the urn, sweet tea and a custard cream, and I was carrying trays again in fifteen "
    "minutes; I have been off my food, which explains me, I am sure. My teatime gliclazide is at five "
    "sharp, and the diabetes clinic have always been strict with me that a new medicine started "
    "against it is a same-day appointment — nothing has been started against it, I am thankful to "
    "say. The vicar's wife made me promise to mention the turn, and a promise to the vicar's wife is "
    "kept. Half the parish drives, so if ever you wanted me brought in it is no trouble — I leave it "
    "with you."
)

VYEBROOK_RECALL_TEXT = (
    "Jean Vyebrook again — I promised one mention this morning and find I owe you another. The "
    "out-of-hours doctor started me on fluconazole capsules on Friday evening, for thrush; the chemist "
    "said my surgery must have it on record. There — the ledger is square."
)

# ── contest 21: Les Unsworth ───────────────────────────────────────────────────────────────────────────────
pt_unsworth = _caller(
    "pt_unsworth",
    "Les Unsworth",
    79,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Recent short-lived stomach upset documented by telephone note; resolved.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, loperamide as "
        "required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Les Unsworth. I shall give it to you plain.\n\n"
        "After that stomach upset a fortnight back my eating never picked up, and then thrush on top, "
        "and the out-of-hours doctor started me on fluconazole capsules on Monday. Yesterday before my "
        "lunch I went sweaty and shaky at the allotment gate — my pal sat me on the bench, I had the "
        "banana out of my bag, and ten minutes later I dug two rows. So I am not ailing this minute. "
        "But I am on gliclazide twice a day, and the diabetes clinic have drummed it into me: new "
        "medicine started beside it, same-day review, before the next tablet. Next tablet is teatime — "
        "five, half five at the latest in our kitchen."
    ),
    onset="Monday for the capsules. The sweaty, shaky spell was yesterday at the allotment gate.",
    severity="A banana and ten minutes and I dug two rows. It is today's teatime tablet that wants a doctor's say-so.",
    history="Diabetes nine years. The stomach thing is done; the appetite never quite came back.",
    medications="Gliclazide twice a day, the stopper tablets if the stomach turns — and Monday's capsules.",
    context="The allotment is between mine and yours; I can walk up whenever suits today.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_unsworth_ooh_fluconazole_allotment",
)

#: Split piece 1: the capsules as record-keeping (the allotment gate rides his ring-back).
UNSWORTH_SPLIT_INTAKE = (
    "Morning. Les Unsworth. Housekeeping only: the out-of-hours doctor started me on fluconazole "
    "capsules on Monday, for thrush, and the chemist said get it on my surgery record. Done, then. My "
    "repeat can wait its turn — I am stocked for a week yet."
)

UNSWORTH_RECALL_TEXT = (
    "Les Unsworth again — rang earlier about the record. The wife heard me leave the middle out, so: "
    "my eating never picked up after that stomach upset, and yesterday before lunch I went sweaty and "
    "shaky at the allotment gate — banana, bench, ten minutes, then I dug two rows. Right as rain "
    "since. My teatime gliclazide is at five, and the clinic have drummed their rule into me: new "
    "medicine started beside it, same-day review — though nobody has been near my sugar tablets, so I "
    "shan't go claiming it. The wife wanted the whole tale told; what wants doing with it, you will "
    "know better than us — the allotment is between mine and yours, and I can walk up whenever suits."
)

# ── contest 22: Doris Urswell ──────────────────────────────────────────────────────────────────────────────
pt_urswell = _caller(
    "pt_urswell",
    "Doris Urswell",
    87,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide, long-standing; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 40 mg with breakfast and with evening meal, donepezil declined "
        "per memory clinic letter; no other regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Doris Urswell. My son is on the other phone listening in, so between us you will get "
        "the whole tale.\n\n"
        "He booked me a private appointment on Monday — the thrush was making my mouth miserable — and "
        "the doctor there started me on fluconazole tablets, two weeks of them. I eat like a sparrow "
        "and the mouth has halved even that. And twice this week before meals I have gone dizzy in my "
        "kitchen — I keep jelly babies in the tea caddy on the clinic's advice, and two of those and a "
        "sit-down puts me right inside ten minutes. I am right now. But the gliclazide: the clinic's "
        "rule, which my son has written on the calendar, is a same-day review whenever a new medicine "
        "starts beside it, before the evening dose. My evening dose is five o'clock."
    ),
    onset="Monday for the private tablets. The dizzy spells, twice this week, before meals.",
    severity="Two jelly babies and a sit-down puts me right. Right now, too — the five o'clock dose is the question.",
    history="Diabetes twenty-five years. The memory is what it is; my son keeps the calendar.",
    medications="Gliclazide twice a day — and the private doctor's fluconazole since Monday.",
    context="My son can bring me at any hour today; he says sooner suits better than later.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_urswell_private_fluconazole_jelly_babies",
)

#: Split piece 1: the dizzy spells, self-discounted, in a routine ask (the tablets ride her ring-back).
URSWELL_SPLIT_INTAKE = (
    "Hello. Doris Urswell. My repeat, please — the gliclazide, the little forty ones.\n\n"
    "And my son says tell you, so I am telling you: twice this week before meals I have gone dizzy in "
    "my kitchen — two jelly babies from the tea caddy and a sit-down and I am right inside ten "
    "minutes, right as I speak to you now. I eat like a sparrow, always have. My evening gliclazide is "
    "five o'clock — my son has it on the calendar, next to the clinic's rule that a new medicine "
    "started beside it means a same-day review; not that there is anything new beside it, so far as I "
    "can see. That is the whole of it; my son says do whatever the surgery thinks right, and he can "
    "bring me at any hour."
)

URSWELL_RECALL_TEXT = (
    "Doris Urswell again — my son has marched me back to the telephone. What I left out this morning: "
    "he took me private on Monday for the thrush and the doctor there started me on fluconazole "
    "tablets, two weeks of them, and the letter says my own surgery is to know. Now it knows, and my "
    "son can rest."
)

# ── contest 23: Ken Vantham ────────────────────────────────────────────────────────────────────────────────
pt_vantham = _caller(
    "pt_vantham",
    "Ken Vantham",
    73,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Works part-time at the garden centre per occupation note.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, candesartan 8 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Ken Vantham. I will keep it tidy because I am due at the garden centre at twelve.\n\n"
        "Out-of-hours doctor, Saturday, thrush, fluconazole capsules — a week of them. Since then I "
        "have been skipping lunch — the mouth makes a chore of it — and twice mid-morning at work I "
        "have gone woolly behind the tills; the girls sat me down with sweet tea and I was restocking "
        "compost twenty minutes later. Nothing on me now. But the gliclazide is twice a day, and the "
        "diabetes clinic said it plainly at my review: new medicine in beside it, same-day check, "
        "before the next dose. I take the evening one at five when I get in."
    ),
    onset="Saturday for the capsules. The woolly spells, twice mid-morning at work this week.",
    severity="Sweet tea and twenty minutes and I was restocking compost. It is the five o'clock dose that wants checking first.",
    history="Diabetes six years, blood pressure longer. Your clinic does the sugar reviews.",
    medications="Gliclazide twice a day, candesartan in the morning — and Saturday's capsules.",
    context="The garden centre is flexible with me; I can come before my shift or straight after two.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_vantham_ooh_fluconazole_garden_centre",
)

#: Split piece 1: the capsules as record-keeping (the tills ride his ring-back).
VANTHAM_SPLIT_INTAKE = (
    "Morning. Ken Vantham. Quick one before my shift: the out-of-hours doctor put me on fluconazole "
    "capsules on Saturday, for thrush, and I was told to make sure my own surgery has it written down. "
    "That is all — I am due at the garden centre at twelve."
)

VANTHAM_RECALL_TEXT = (
    "Ken Vantham again — rang before my shift about the record. I am at the garden centre early, and "
    "the girls behind the tills say I should have said this too: twice mid-morning this week I went "
    "woolly at work — "
    "they sat me down with a sugary brew and I was restocking compost twenty minutes later. I have "
    "been skipping lunch with this mouth. My evening gliclazide is at five when I get in, and the "
    "diabetes clinic said it plainly at my review: a new medicine in beside it, same-day check — not "
    "that my sugar tablets have changed, mind. That is everything said; do with it as you think best — "
    "the garden centre is flexible, and I can come before my shift or straight after two."
)

# ── contest 24: Audrey Volgarth ────────────────────────────────────────────────────────────────────────────
pt_volgarth = _caller(
    "pt_volgarth",
    "Audrey Volgarth",
    84,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Denture wearer; last note records new dentures bedding in poorly.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, mirtazapine 15 mg at "
        "night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Audrey Volgarth. My dentist started this, so I shall start with her.\n\n"
        "She found thrush under my new dentures on Monday and put me on fluconazole — her letter is "
        "propped against my biscuit barrel and it says my doctor is to be informed. The dentures had "
        "already made a misery of eating and the soreness has finished the job; I am managing porridge "
        "and not a lot else. And twice before my evening meal this week I have gone trembly in my "
        "hands and queer — the biscuit barrel earns its keep, and ten minutes later I am myself. I am "
        "myself now. But my gliclazide goes down with that evening meal at five, and the diabetes "
        "clinic's rule is a same-day look whenever a new medicine joins it, before the dose."
    ),
    onset="Monday for the dentist's capsules. The trembly spells, twice this week, before the evening meal.",
    severity="The biscuit barrel sorts it in ten minutes. Myself now — the five o'clock dose is what needs the look first.",
    history="Diabetes seventeen years. The night tablet helps me sleep and eat a little, or it did.",
    medications="Gliclazide twice a day, mirtazapine at night — and the dentist's fluconazole since Monday.",
    context="My nephew rings at lunchtime and can fetch me in the afternoon without any trouble.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_volgarth_dentist_fluconazole_porridge",
)

#: Split piece 1: the porridge diet and settled trembles, self-discounted (the letter rides her ring-back).
VOLGARTH_SPLIT_INTAKE = (
    "Hello. Audrey Volgarth. My repeat, please — the gliclazide and my night tablet.\n\n"
    "And write down, if you would, that these new dentures have me down to porridge and not a lot "
    "else, and twice this week before my evening meal I went trembly and queer — the biscuit barrel "
    "sorts it in ten minutes and I am myself as we speak. My nephew says the surgery should know I am "
    "eating so little. Known, now — and know as well that my gliclazide goes down with that evening "
    "meal at five, and that the diabetes clinic's rule is a same-day look whenever a new medicine "
    "joins it — nothing has joined it, to my knowledge. I shall leave it with you; my nephew can fetch "
    "me in the afternoon without any trouble, should you want me."
)

VOLGARTH_RECALL_TEXT = (
    "Audrey Volgarth again — I rang about my repeat and my porridge this morning. The letter I should "
    "have read you first is propped against my biscuit barrel: my dentist found thrush under the new "
    "dentures on Monday and has started me on fluconazole, and she asks that my doctor be informed. "
    "Informed, then, and I shall let you get on."
)

# ── contest 25: Bert Uxley ─────────────────────────────────────────────────────────────────────────────────
pt_uxley = _caller(
    "pt_uxley",
    "Bert Uxley",
    88,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide, long-standing; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Allotment holder; documented as robustly independent at the last review.",
        "Repeat medication: gliclazide 40 mg with breakfast and with evening meal, chlorphenamine at "
        "night as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Bert Uxley. I have had my orders from my granddaughter, so here is everything at "
        "once.\n\n"
        "The out-of-hours doctor started me on fluconazole capsules on Sunday, for thrush. My eating "
        "has been poor — the mouth, and cooking for one is a bore at the best of times — and on Monday "
        "I came over queer in the allotment shed, sat on the seed boxes till it passed, and had my "
        "sandwich early; fifteen minutes and I was hoeing again. Nothing since, and nothing on me now. "
        "But I take gliclazide twice a day, and the diabetes clinic's instruction — my granddaughter "
        "has it printed and stuck to my fridge — is a same-day review when any new medicine starts "
        "next to it, before the next dose. The next dose is my teatime one, five o'clock."
    ),
    onset="Sunday for the capsules. The queer turn was Monday, in the allotment shed.",
    severity="Sat on the seed boxes, sandwich early, hoeing in fifteen minutes. It is the five o'clock tablet needing the say-so.",
    history="Diabetes twenty-one years. Still dig my own plot, which the clinic approves of.",
    medications="Gliclazide twice a day, an allergy tablet some nights — and Sunday's capsules.",
    context="My granddaughter is fierce and has a car; we can be with you within the half hour, any time.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_uxley_ooh_fluconazole_seed_boxes",
)

#: Split piece 1: the capsules as record-keeping (the shed rides his ring-back).
UXLEY_SPLIT_INTAKE = (
    "Morning. Bert Uxley. My granddaughter's orders: tell the surgery the out-of-hours doctor started "
    "me on fluconazole capsules on Sunday, for thrush, so it sits on my record properly. Consider "
    "yourselves told. I want nothing else — the plot will not hoe itself."
)

UXLEY_RECALL_TEXT = (
    "Bert Uxley again — my granddaughter has read me the riot act for the half-job I made of this "
    "morning's call. The rest: I came over queer in the allotment shed on Monday, sat on the seed "
    "boxes till it passed, sandwich early, hoeing in fifteen minutes. My eating has been poor with the "
    "mouth. And my teatime gliclazide is five o'clock — the clinic's instruction on my fridge, the one "
    "she printed, says a new medicine started next to it means a same-day review — though nothing has "
    "been done to my sugar tablets, whatever she makes of my reporting. She is stood over me, so count "
    "that as said twice. She says do whatever the surgery thinks right, and her car is outside — that "
    "will keep the peace."
)

# ── contest 26: Vera Umberleigh ────────────────────────────────────────────────────────────────────────────
pt_umberleigh = _caller(
    "pt_umberleigh",
    "Vera Umberleigh",
    81,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Recovering from a heavy cold per recent telephone note; appetite reported reduced.",
        "Repeat medication: gliclazide 80 mg with breakfast and with evening meal, alendronic acid "
        "weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Vera Umberleigh. I have rehearsed this on my daughter, so it comes in the right "
        "order.\n\n"
        "Thrush after my cold, and the out-of-hours doctor started me on fluconazole capsules on "
        "Saturday. I have been eating small since the cold and smaller since the mouth. And twice this "
        "week I have had shaky spells before meals — I sit, I have my emergency shortbread, and in ten "
        "minutes I am doing the crossword again. Doing it now, in fact. But the gliclazide is twice a "
        "day, and the diabetes clinic have said it at every review since I started it: a new medicine "
        "alongside means they see me the same day, before the evening tablet. Mine is at five, with "
        "whatever I can manage for tea."
    ),
    onset="Saturday for the capsules. The shaky spells, twice this week, before meals.",
    severity="Emergency shortbread and ten minutes and I am back at the crossword. The five o'clock tablet is today's question.",
    history="Diabetes eleven years; the bone tablet on Sundays. Your clinic minds the sugar.",
    medications="Gliclazide twice a day, alendronic acid weekly — and Saturday's capsules.",
    context="My daughter works mornings but is free from one; between us any afternoon hour today works.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_umberleigh_ooh_fluconazole_shortbread",
)

#: Split piece 1: the shaky spells, self-discounted, in a routine ask (the capsules ride her ring-back).
UMBERLEIGH_SPLIT_INTAKE = (
    "Hello. Vera Umberleigh. Only my repeat — the gliclazide and my Sunday bone tablet.\n\n"
    "And so it is on paper somewhere: I have had two shaky spells before meals this week. I sit, I "
    "have my emergency shortbread, and in ten minutes I am back at the crossword — I am at it now. I "
    "have eaten small since my cold, which will be why. My daughter says mention it, so it is "
    "mentioned — and mention too that my evening gliclazide is at five, and that the diabetes clinic "
    "have said at every review that a new medicine alongside it means they see me the same day; "
    "nothing new is alongside it, as far as I know. I leave it with you; my daughter is free from "
    "one, so fetching me in of an afternoon is easily arranged, if wanted."
)

UMBERLEIGH_RECALL_TEXT = (
    "Vera Umberleigh again — my daughter rang on her break and asked had I told you about the capsules, "
    "and I had not. The out-of-hours doctor started me on fluconazole on Saturday, for thrush after my "
    "cold; the chemist said the surgery should have it recorded. Recorded now, and my daughter can "
    "stand down."
)

# ── contest 27: Frank Verwood ──────────────────────────────────────────────────────────────────────────────
pt_verwood = _caller(
    "pt_verwood",
    "Frank Verwood",
    77,
    "M",
    chart=(
        "Type 2 diabetes, on gliclazide; monitored at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 160 mg with breakfast, 80 mg with evening meal, tamsulosin "
        "400 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Frank Verwood. I paid to be seen quick on Tuesday — a private clinic in town — about "
        "thrush, and the doctor there started me on fluconazole for a fortnight and said, twice, tell "
        "your own GP. So this is that call, with the rest of the week attached.\n\n"
        "The mouth has me eating about half what I should, and before lunch yesterday and the day "
        "before I went sweaty and unsteady enough to sit on the stairs — glucose tablets from the "
        "bathroom cabinet, ten minutes, good as new. Good as new now. But I take a fair old dose of "
        "gliclazide, and the diabetes clinic's rule for me has always been: new medicine started "
        "beside it, same-day review, before the next tablet goes down. The next one is with my tea at "
        "five."
    ),
    onset="Tuesday for the private clinic's capsules. The sweaty, unsteady spells, the last two days before lunch.",
    severity="Glucose tablets and ten minutes and I am good as new. The five o'clock tablet is what wants reviewing first.",
    history="Diabetes fifteen years on a decent dose. Your clinic reviews me twice a year.",
    medications=(
        "Gliclazide, the big morning dose and the teatime one, tamsulosin daily — and the private "
        "fluconazole since Tuesday."
    ),
    context="I still drive. Give me a time today and I shall be early for it.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_verwood_private_fluconazole_stairs",
)

#: Split piece 1: the private prescription phoned through as instructed (the stairs ride his ring-back).
VERWOOD_SPLIT_INTAKE = (
    "Morning. Frank Verwood. Doing as the private clinic told me twice over: they started me on "
    "fluconazole on Tuesday, for thrush, a fortnight's course, and my own GP was to be informed. "
    "Informed. Add it to my record and I shall not take up more of your morning."
)

VERWOOD_RECALL_TEXT = (
    "Frank Verwood again — I rang first thing on a bit of housekeeping, and my wife has informed me "
    "that was half a job. The other half: before lunch yesterday and the day before I went sweaty and "
    "unsteady enough to sit on the stairs — glucose tablets, ten minutes, good as new both times. I am "
    "eating about half what I should with this mouth. My teatime gliclazide is at five, and the "
    "diabetes clinic's rule for me has always been a same-day review before the next tablet whenever a "
    "new medicine starts beside it — though my sugar tablets stand exactly as they were, so I make no "
    "claim on their rule. All said now; what happens next is your shop. I still drive — name a time "
    "today and I shall be early for it."
)

# ── contest 28: Sheila Ulcombe ─────────────────────────────────────────────────────────────────────────────
pt_ulcombe = _caller(
    "pt_ulcombe",
    "Sheila Ulcombe",
    86,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide, long-standing; reviews at the diabetes and endocrine clinic.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 40 mg with breakfast and with evening meal, folic acid 5 mg "
        "daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Sheila Ulcombe. I shall say it all now rather than drip it out over three phone "
        "calls, which is what my son predicted I would do.\n\n"
        "The out-of-hours doctor started me on fluconazole capsules on Sunday, for thrush. My eating "
        "has been poor a fortnight and poorer since. And twice — Tuesday teatime and this morning "
        "before breakfast — I have gone light-headed and had to hold the dresser; my little tin of "
        "travel sweets does the trick inside ten minutes, and it has done the trick today, I am quite "
        "well talking to you. But the gliclazide goes down twice a day, and the diabetes clinic told "
        "me and my son together: any new medicine started beside it, they see me the same day, before "
        "the evening dose. The evening dose is five o'clock in this house and always has been."
    ),
    onset="Sunday for the capsules. Light-headed Tuesday teatime and again this morning, before food.",
    severity="The travel-sweet tin does the trick in ten minutes; quite well now. The five o'clock dose is the deadline.",
    history="Diabetes nineteen years. Your clinic has minded it all along.",
    medications="Gliclazide twice a day, folic acid daily — and Sunday's capsules.",
    context="My son works from home Thursdays and can drive me up at whatever hour you give me.",
    gold=CLAIMANT_GOLD,
    source="authored:gf_ulcombe_ooh_fluconazole_dresser",
)

#: Split piece 1: the light-headed spells, self-discounted, in a routine ask (the capsules ride her
#: ring-back — her son's predicted three calls compressed to the permitted two).
ULCOMBE_SPLIT_INTAKE = (
    "Hello. Sheila Ulcombe. My repeat, please — the gliclazide and the folic acid.\n\n"
    "And put me down as having said: I went light-headed at the dresser on Tuesday teatime and again "
    "this morning before breakfast — my little tin of travel sweets does the trick inside ten "
    "minutes, and I am quite well talking to you. My eating has been poor a fortnight, there is the "
    "likely culprit. My sugar tablet goes down at five in this house and always has, and the diabetes "
    "clinic told me and my son together that a new medicine started beside it means they see me the "
    "same day — not that anything has been started beside it, that I could tell you. My son will ask "
    "me tonight whether I told you, so thank you for being my witness. Do with it what you think "
    "right; he can drive me up at whatever hour you give me."
)

ULCOMBE_RECALL_TEXT = (
    "Sheila Ulcombe again — my son predicted three calls and I am determined to stop at two. The part "
    "I owed you from this morning: the out-of-hours doctor started me on fluconazole capsules on "
    "Sunday, for the thrush, and the chemist was most particular that the surgery record it. There — "
    "all of me, in two calls."
)

# ══ THE 28 HOLDERS: routine diabetes & endocrine patients backfilled into returned cancellations ═══════════
# Holders never call. Each card is what they say if a desk RINGS them (`rebooking._rebookee`'s convention),
# each has an ordinary, human reason to want today, and NONE pre-consents to being moved.

pt_upwell = _caller(
    "pt_upwell",
    "Ernest Upwell",
    72,
    "M",
    chart=(
        "Type 2 diabetes on metformin, stable; annual review due.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly diabetes check is this afternoon — my son has taken a half day from the warehouse "
        "to run me in, which took some arranging, I can tell you."
    ),
    onset="Nothing new; it is the yearly check.",
    severity="Quite well. The review is routine.",
    history="The diabetes, steady on metformin for years.",
    medications="Metformin, morning and night.",
    context="My son's half day is booked; he cannot get another this month.",
    gold=_holder_gold(),
    source="authored:gf_holder_upwell_annual_review",
)

pt_vange = _caller(
    "pt_vange",
    "Muriel Vange",
    68,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual thyroid review due.",
        "Repeat medication: levothyroxine 75 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I am booked for my thyroid review this afternoon. The market bus only runs my way twice a "
        "week, so today's time suited me perfectly."
    ),
    onset="Nothing new; the yearly thyroid look-over.",
    severity="Well in myself; it is routine.",
    history="The thyroid, on the same tablet a good while.",
    medications="Levothyroxine each morning.",
    context="The market bus is my lift; it runs today and not again until the weekend.",
    gold=_holder_gold(),
    source="authored:gf_holder_vange_thyroid_review",
)

pt_uffington = _caller(
    "pt_uffington",
    "Roy Uffington",
    65,
    "M",
    chart=(
        "Type 2 diabetes on metformin and dapagliflozin; medication review due.",
        "Repeat medication: metformin 1 g twice daily, dapagliflozin 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I have my tablets review this afternoon. I swapped shifts at the depot to make it — took me a "
        "fortnight of asking to get today covered."
    ),
    onset="Nothing new; the review of my tablets.",
    severity="Fine in myself.",
    history="The diabetes five years, two tablets keeping it tidy.",
    medications="Metformin and the dapagliflozin.",
    context="The swapped shift cost me a favour I will be repaying till summer.",
    gold=_holder_gold(),
    source="authored:gf_holder_uffington_medication_review",
)

pt_vowchurch = _caller(
    "pt_vowchurch",
    "Ann Vowchurch",
    59,
    "F",
    chart=(
        "Type 2 diabetes, diet-controlled; annual review due.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "My annual diabetes check is this afternoon — I cleared it with work weeks ago and my cover is "
        "already sorted for the shop floor."
    ),
    onset="Nothing new; the annual check.",
    severity="Well; entirely routine.",
    history="Diet-controlled diabetes, three years running.",
    medications="None — that is rather the point of the diet.",
    context="Work signed off this afternoon specifically; another slot means asking all over again.",
    gold=_holder_gold(),
    source="authored:gf_holder_vowchurch_diet_controlled",
)

pt_ulgham = _caller(
    "pt_ulgham",
    "Stan Ulgham",
    76,
    "M",
    chart=(
        "Type 2 diabetes on basal insulin, stable; insulin review due.",
        "Repeat medication: insulin glargine at night, metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my insulin review this afternoon. My daughter drives me and she has moved her own "
        "appointments around to do it today."
    ),
    onset="Nothing new; the routine insulin look-over.",
    severity="Steady as ever.",
    history="On the night-time insulin three years now, no dramas.",
    medications="The insulin pen at night, metformin with meals.",
    context="My daughter has rearranged her day once already for this.",
    gold=_holder_gold(),
    source="authored:gf_holder_ulgham_insulin_review",
)

pt_vernley = _caller(
    "pt_vernley",
    "Carol Vernley",
    54,
    "F",
    chart=(
        "Hypothyroidism; recent dose change, follow-up review due.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in this afternoon about my thyroid dose. I have a childminder booked for the school run "
        "specially — she is a marvel but she is not free just any day."
    ),
    onset="Nothing new; the dose follow-up they asked for.",
    severity="Feeling well on the new dose.",
    history="The thyroid, dose nudged up recently.",
    medications="Levothyroxine, the hundred now.",
    context="The childminder is booked for today only.",
    gold=_holder_gold(),
    source="authored:gf_holder_vernley_thyroid_dose",
)

pt_upshaw = _caller(
    "pt_upshaw",
    "Derek Upshaw",
    70,
    "M",
    chart=(
        "Type 2 diabetes on metformin; annual review with foot check due.",
        "Repeat medication: metformin 850 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly diabetes MOT is this afternoon, feet and all. My neighbour is taking me on his way "
        "to the tip — it sounds daft but the timing works out lovely."
    ),
    onset="Nothing new; the yearly once-over.",
    severity="Right as rain; routine.",
    history="The diabetes, well behaved on metformin.",
    medications="Metformin twice a day.",
    context="The lift is arranged around my neighbour's tip run today.",
    gold=_holder_gold(),
    source="authored:gf_holder_upshaw_foot_check",
)

pt_uckmere = _caller(
    "pt_uckmere",
    "Pauline Uckmere",
    63,
    "F",
    chart=(
        "Type 2 diabetes on metformin; annual review due.",
        "Carer for her husband per household note.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes review is this afternoon. I have a sitter for my husband from two till four and "
        "she cannot do any other day this week."
    ),
    onset="Nothing new; the annual review.",
    severity="Well enough; it is routine.",
    history="The diabetes four years; I mind my husband, which keeps me on my toes.",
    medications="Metformin, morning and night.",
    context="The sitter's two-till-four window is the whole plan.",
    gold=_holder_gold(),
    source="authored:gf_holder_uckmere_carer_sitter",
)

pt_vinehurst = _caller(
    "pt_vinehurst",
    "Gordon Vinehurst",
    74,
    "M",
    chart=(
        "Type 2 diabetes on gliclazide and metformin, stable; annual review due.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 40 mg daily, metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My annual diabetes review is this afternoon. The community car scheme has me down for the run "
        "there and back — prepaid, which is not nothing on my pension."
    ),
    onset="Nothing new; the annual review.",
    severity="Ticking along fine.",
    history="The diabetes a decade; two tablets keep it steady.",
    medications="Gliclazide with breakfast, metformin twice a day.",
    context="The taxi is prepaid for this afternoon's times.",
    gold=_holder_gold(),
    source="authored:gf_holder_vinehurst_prepaid_taxi",
)

pt_ubbeston = _caller(
    "pt_ubbeston",
    "Brenda Ubbeston",
    66,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual thyroid review due.",
        "Repeat medication: levothyroxine 125 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in for my thyroid review this afternoon. My daughter has taken the grandchildren "
        "specially so I can come — she has them until five and not a minute past."
    ),
    onset="Nothing new; the yearly review.",
    severity="Perfectly well.",
    history="The thyroid, same tablet for years.",
    medications="Levothyroxine each morning.",
    context="The grandchildren are minded until five today only.",
    gold=_holder_gold(),
    source="authored:gf_holder_ubbeston_grandchildren",
)

pt_vaudrey = _caller(
    "pt_vaudrey",
    "Colin Vaudrey",
    69,
    "M",
    chart=(
        "Type 2 diabetes on metformin and sitagliptin; medication review due.",
        "Repeat medication: metformin 1 g twice daily, sitagliptin 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablets review is this afternoon. I work nights at the sorting office and today is my one "
        "day between runs — it is the only afternoon I am awake and human."
    ),
    onset="Nothing new; the tablets review.",
    severity="Fine, allowing for the night shifts.",
    history="The diabetes six years, two tablets.",
    medications="Metformin and sitagliptin.",
    context="Nights at the sorting office; today is the gap day.",
    gold=_holder_gold(),
    source="authored:gf_holder_vaudrey_night_shifts",
)

pt_urchfont = _caller(
    "pt_urchfont",
    "Kathleen Urchfont",
    71,
    "F",
    chart=(
        "Type 2 diabetes on metformin; medication review due.",
        "Repeat medication: metformin 500 mg with meals.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes tablets review is this afternoon. My sister has come over from her side of town "
        "to sit with my husband while I am out — she goes home on the teatime bus."
    ),
    onset="Nothing new; the review.",
    severity="Well in myself.",
    history="The diabetes, steady on metformin.",
    medications="Metformin with meals.",
    context="My sister sits with my husband today; she is not over again until next week.",
    gold=_holder_gold(),
    source="authored:gf_holder_urchfont_sister_sitting",
)

pt_vobster = _caller(
    "pt_vobster",
    "Alan Vobster",
    62,
    "M",
    chart=(
        "Impaired fasting glucose; annual prediabetes check due.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in this afternoon for my prediabetes check. I booked the day's leave for it a month back "
        "— leave does not grow on trees where I work."
    ),
    onset="Nothing new; the annual check.",
    severity="Fit and well.",
    history="Borderline sugar, watched yearly.",
    medications="None.",
    context="A booked day of annual leave, requested a month ago.",
    gold=_holder_gold(),
    source="authored:gf_holder_vobster_prediabetes",
)

pt_uplowman = _caller(
    "pt_uplowman",
    "Josie Uplowman",
    58,
    "F",
    chart=(
        "Hypothyroidism; thyroid function review due following bloods.",
        "Repeat medication: levothyroxine 50 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My thyroid review is this afternoon, to go over the bloods. I have the school run covered by "
        "another mum today, which is rare as hen's teeth and not easily repeated."
    ),
    onset="Nothing new; the review of the bloods.",
    severity="Feeling fine.",
    history="The thyroid, on a small dose.",
    medications="Levothyroxine each morning.",
    context="School-run cover is today only.",
    gold=_holder_gold(),
    source="authored:gf_holder_uplowman_school_run",
)

pt_vigobrook = _caller(
    "pt_vigobrook",
    "Trevor Vigobrook",
    73,
    "M",
    chart=(
        "Type 2 diabetes on metformin; annual review due.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My annual diabetes review is this afternoon. My pal from the bowls club is driving me — we "
        "planned the whole day around it, lunch first, review after."
    ),
    onset="Nothing new; the annual review.",
    severity="Grand, thanks.",
    history="The diabetes, kept simple with one tablet.",
    medications="Metformin, morning and night.",
    context="The lift and the lunch are today's arrangement.",
    gold=_holder_gold(),
    source="authored:gf_holder_vigobrook_bowls_pal",
)

pt_undermere = _caller(
    "pt_undermere",
    "Barbara Undermere",
    77,
    "F",
    chart=(
        "Type 2 diabetes on gliclazide, stable; annual review due.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: gliclazide 40 mg with breakfast.",
        "No known drug allergies.",
    ),
    intake=(
        "I have my diabetes review this afternoon. The ring-and-ride is booked both ways, and you have "
        "to book them days ahead — they were very clear about that."
    ),
    onset="Nothing new; the yearly review.",
    severity="Quite well.",
    history="The diabetes, one small tablet with breakfast.",
    medications="Gliclazide with breakfast.",
    context="Ring-and-ride booked days ago for this afternoon's times.",
    gold=_holder_gold(),
    source="authored:gf_holder_undermere_ring_and_ride",
)

pt_uxcombe = _caller(
    "pt_uxcombe",
    "Malcolm Uxcombe",
    67,
    "M",
    chart=(
        "Type 2 diabetes on metformin and empagliflozin; medication review due.",
        "Repeat medication: metformin 1 g twice daily, empagliflozin 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablets review is this afternoon. I visit my wife at the care home every day at four, so "
        "today's earlier time was exactly what I asked them for."
    ),
    onset="Nothing new; the review.",
    severity="Well enough.",
    history="The diabetes, two tablets these last two years.",
    medications="Metformin and empagliflozin.",
    context="Daily four o'clock visiting at my wife's home shapes everything.",
    gold=_holder_gold(),
    source="authored:gf_holder_uxcombe_care_home_visiting",
)

pt_venngarth = _caller(
    "pt_venngarth",
    "Angela Venngarth",
    60,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual thyroid review due.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My thyroid review is this afternoon — I booked the half-day from work for it and my rota is "
        "locked a month out, so it took some doing."
    ),
    onset="Nothing new; the annual review.",
    severity="Perfectly fine.",
    history="The thyroid, steady on the same dose.",
    medications="Levothyroxine each morning.",
    context="A half-day booked against a month-out rota.",
    gold=_holder_gold(),
    source="authored:gf_holder_venngarth_half_day",
)

pt_uldale = _caller(
    "pt_uldale",
    "Peter Uldale",
    75,
    "M",
    chart=(
        "Type 2 diabetes on metformin; annual review due.",
        "Repeat medication: metformin 850 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "The diabetes clinic have me in this afternoon for the yearly once-over. My brother-in-law "
        "drives me and he has come over from the coast this morning on purpose."
    ),
    onset="Nothing new; the yearly review.",
    severity="Very well, thank you.",
    history="The diabetes, behaved, on metformin.",
    medications="Metformin twice a day.",
    context="My brother-in-law is here from the coast today for this.",
    gold=_holder_gold(),
    source="authored:gf_holder_uldale_brother_in_law",
)

pt_varleigh = _caller(
    "pt_varleigh",
    "Freda Varleigh",
    64,
    "F",
    chart=(
        "Type 2 diabetes on metformin; annual review due.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes review is this afternoon. Work agreed an early finish today for it — my "
        "supervisor signed it off in writing, which is how rare that is."
    ),
    onset="Nothing new; the annual review.",
    severity="Well in myself.",
    history="The diabetes, three years, one tablet.",
    medications="Metformin, morning and night.",
    context="The early finish is agreed for today only.",
    gold=_holder_gold(),
    source="authored:gf_holder_varleigh_early_finish",
)

pt_upperby = _caller(
    "pt_upperby",
    "Geoff Upperby",
    71,
    "M",
    chart=(
        "Type 2 diabetes on basal insulin; insulin pen technique review due.",
        "Attends with a support worker per access note.",
        "Repeat medication: insulin glargine at night, metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My insulin pen review is this afternoon. My support worker comes with me and today is one of "
        "her days — she is only funded for two a week."
    ),
    onset="Nothing new; the pen review they asked for.",
    severity="Doing alright.",
    history="On the night insulin a year; the pen fiddles my fingers, hence the review.",
    medications="The insulin pen at night, metformin with meals.",
    context="My support worker's funded days are fixed; today is one.",
    gold=_holder_gold(),
    source="authored:gf_holder_upperby_support_worker",
)

pt_ventnor = _caller(
    "pt_ventnor",
    "Sylvia Ventnor",
    79,
    "F",
    chart=(
        "Type 2 diabetes on metformin, stable; annual review due.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My annual diabetes check is this afternoon. My niece is taking me — she has swapped her shift "
        "at the hospital laundry to do it."
    ),
    onset="Nothing new; the annual check.",
    severity="Quite well.",
    history="The diabetes, quiet on metformin for years.",
    medications="Metformin, morning and night.",
    context="My niece's swapped shift is today's lift.",
    gold=_holder_gold(),
    source="authored:gf_holder_ventnor_niece_shift",
)

pt_usway = _caller(
    "pt_usway",
    "Ray Usway",
    66,
    "M",
    chart=(
        "Type 2 diabetes on metformin and gliclazide; medication review due.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Repeat medication: metformin 1 g twice daily, gliclazide 40 mg with breakfast.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablets review is this afternoon. I am between jobs on site this week, so today I can "
        "actually come without losing a day's pay — next week I could not."
    ),
    onset="Nothing new; the review.",
    severity="Fit for work, which is the point.",
    history="The diabetes, five years, two tablets.",
    medications="Metformin twice a day, gliclazide with breakfast.",
    context="Between site jobs this week; on the tools again from next.",
    gold=_holder_gold(),
    source="authored:gf_holder_usway_between_jobs",
)

pt_vernditch = _caller(
    "pt_vernditch",
    "Eileen Vernditch",
    70,
    "F",
    chart=(
        "Hypothyroidism on levothyroxine; annual thyroid review due.",
        "Repeat medication: levothyroxine 75 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My thyroid review is this afternoon. My friend drives me on her way to her sister's — the "
        "arrangement only works on the day she goes."
    ),
    onset="Nothing new; the yearly review.",
    severity="Perfectly well.",
    history="The thyroid, unchanged for years.",
    medications="Levothyroxine each morning.",
    context="The lift only exists on my friend's sister day, which is today.",
    gold=_holder_gold(),
    source="authored:gf_holder_vernditch_friend_lift",
)

pt_ullenhall = _caller(
    "pt_ullenhall",
    "Dot Ullenhall",
    82,
    "F",
    chart=(
        "Type 2 diabetes on metformin, stable; annual review due.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes review is this afternoon. The community transport is booked — they confirm you "
        "the night before and they have confirmed me, so it is all arranged."
    ),
    onset="Nothing new; the annual review.",
    severity="Well, thank you for asking.",
    history="The diabetes, gentle, on metformin.",
    medications="Metformin, morning and night.",
    context="Community transport confirmed for this afternoon.",
    gold=_holder_gold(),
    source="authored:gf_holder_ullenhall_community_transport",
)

pt_vyner = _caller(
    "pt_vyner",
    "Harry Vyner",
    68,
    "M",
    chart=(
        "Type 2 diabetes on metformin; annual review due.",
        "Repeat medication: metformin 850 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My annual diabetes review is this afternoon, and I am glad of the timing because we tow the "
        "caravan down to the coast first thing tomorrow for a fortnight."
    ),
    onset="Nothing new; the annual review.",
    severity="Fighting fit.",
    history="The diabetes, steady on metformin.",
    medications="Metformin twice a day.",
    context="The caravan leaves at dawn tomorrow; today was the last day that worked.",
    gold=_holder_gold(),
    source="authored:gf_holder_vyner_caravan",
)

pt_umberfold = _caller(
    "pt_umberfold",
    "Maureen Umberfold",
    61,
    "F",
    chart=(
        "Hypothyroidism; recent dose change, follow-up thyroid review due.",
        "Repeat medication: levothyroxine 125 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My thyroid dose review is this afternoon. I swapped shifts with a colleague to be free — she "
        "took my Saturday, which tells you what today cost me."
    ),
    onset="Nothing new; the dose follow-up.",
    severity="Feeling well on the new dose.",
    history="The thyroid, dose changed recently, being checked.",
    medications="Levothyroxine each morning.",
    context="A swapped shift, paid for with my Saturday.",
    gold=_holder_gold(),
    source="authored:gf_holder_umberfold_swapped_saturday",
)

pt_uphollow = _caller(
    "pt_uphollow",
    "Charlie Uphollow",
    73,
    "M",
    chart=(
        "Type 2 diabetes on metformin, stable; annual review due.",
        "Repeat medication: metformin 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My diabetes review — the yearly one — is this afternoon. My grandson drives me between his lectures — he "
        "has a free afternoon today and precious few of them."
    ),
    onset="Nothing new; the yearly review.",
    severity="Very well.",
    history="The diabetes, no bother on metformin.",
    medications="Metformin, morning and night.",
    context="My grandson's free afternoon is the lift.",
    gold=_holder_gold(),
    source="authored:gf_holder_uphollow_grandson",
)

# ══ THE 3 DECOYS: sound urgent, correctly left un-bumped (§6) ══════════════════════════════════════════════

# ── decoy 1: Edith Varcoe — the same worry, wrong tablet: metformin does not do what gliclazide does ───────
pt_varcoe = _caller(
    "pt_varcoe",
    "Edith Varcoe",
    76,
    "F",
    chart=(
        "Type 2 diabetes, on metformin only; annual review in date.",
        "Repeat medication: metformin 1 g twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I have got myself in a state and I shall tell you why, and you can un-state me.\n\n"
        "The out-of-hours doctor started me on fluconazole capsules for thrush, and the lady at my "
        "lunch club said antifungals and diabetes tablets can clash something terrible — her cousin was "
        "carted off, apparently. But my diabetes tablet is the metformin, only the metformin, and the "
        "chemist looked the two up while I stood there and said metformin sits perfectly fine with it "
        "and I was to enjoy my lunch. I feel entirely well — no dizziness, nothing, eating like a "
        "horse. So there is no emergency in this call; I should just like an ordinary appointment "
        "sometime to be looked over and told the lunch club is wrong."
    ),
    onset="The capsules started this week. No symptoms at all since — the state is all in my head.",
    severity="Entirely well. The chemist checked the two tablets together and was not worried.",
    history="The diabetes on metformin alone, years now, never a wobble.",
    medications="Metformin twice a day, and the fluconazole capsules this week.",
    context="Lunch club three days a week; free around it, any day.",
    gold=_routine_gold(),
    source="authored:gf_decoy_varcoe_metformin_defused",
)

# ── decoy 2: Mabel Undercliffe — gliclazide AND dizzy, but the dizziness is old, postural, and fed ─────────
pt_undercliffe = _caller(
    "pt_undercliffe",
    "Mabel Undercliffe",
    81,
    "F",
    chart=(
        "Type 2 diabetes, on gliclazide; reviews at the diabetes and endocrine clinic in date.",
        "Diabetes clinic advice on file: any new medicine started alongside the gliclazide means a "
        "same-day clinic review before the next dose; dose changes are decided at the clinic, after "
        "a finger-prick reading taken there.",
        "Longstanding postural dizziness documented; ENT review historically unremarkable.",
        "Repeat medication: gliclazide 40 mg with breakfast, adcal-D3 twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My neighbour has put the wind up me and I want it looked at, though my daughter says I "
        "am worrying over nothing.\n\n"
        "I take gliclazide for my sugar, and I do get dizzy — when I stand up too quick from the "
        "armchair, the room swims a second. My neighbour says her sister's dizzy spells turned out to "
        "be her sugar and she was in a bad way. But I shall be honest with you, because my daughter "
        "made me promise: these swims of mine are the same standing-up ones I have had for donkey's "
        "years — the ear people looked at me once and found nothing — nothing new has been started, no "
        "new tablets, I am eating like always, and I write my sugar numbers in a book and they are what "
        "they always are. So: an ordinary appointment, please, to talk it through and shut my neighbour "
        "up. There is no hurry that I can honestly claim."
    ),
    onset="The standing-up swims are years old and unchanged. Nothing new this week or this month.",
    severity="A second's swim on standing, then fine. Eating well; the sugar book is steady.",
    history="The diabetes on a small dose of gliclazide; the dizziness looked at years back, ears blamed.",
    medications="Gliclazide with breakfast, the calcium twice a day. Nothing new, and no capsules of any sort.",
    context="My daughter Janet checks my dosette box every week. I am free any day.",
    gold=_routine_gold(),
    source="authored:gf_decoy_undercliffe_postural_defused",
)

#: Split override: the same worry WITHOUT the defusing half — that arrives in her daughter's call (§6:
#: aggregation must be able to cancel urgency, not only create it).
UNDERCLIFFE_SPLIT_INTAKE = (
    "Hello. My neighbour has put the wind up me and I want it looked at. I take gliclazide for my "
    "sugar, and I do get dizzy — the room swims on me. My neighbour says her sister's dizzy spells "
    "turned out to be her sugar and she was in a bad way by the time anyone caught it. Could somebody "
    "see me about it? My daughter says she will ring you herself with her side of it, which tells you "
    "the mood in this family."
)

pt_undercliffe_j = _caller(
    "pt_undercliffe_j",
    "Janet Undercliffe",
    57,
    "F",
    chart=(
        "Migraine, infrequent; otherwise well.",
        "Repeat medication: sumatriptan 50 mg as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — two minutes of your time. Could my migraine tablets go back on repeat? The "
        "sumatriptan. I get through about a box a season, no more."
    ),
    onset="Nothing new; the repeat lapsed.",
    severity="The migraines are rare and the tablet works.",
    history="Migraine since my thirties, well behaved lately.",
    medications="Sumatriptan when one starts.",
    context="I check my mother Mabel Undercliffe's dosette box every week.",
    gold=_routine_gold(),
    source="authored:gf_carrier_undercliffe_daughter_sumatriptan",
)

#: Split piece: her repeat, plus the promised other side of her mother's story — the DEFUSING facts.
UNDERCLIFFE_J_SPLIT_INTAKE = (
    "Hello — two minutes of your time. Could my migraine tablets go back on repeat? The sumatriptan.\n\n"
    "And my mother will have rung you — Mabel Undercliffe — about her dizzy spells, after next door "
    "frightened her. Here is my side, as promised: the swims are the same standing-up-too-quick ones "
    "she has had for donkey's years, the ear clinic found nothing way back, NOTHING new has been "
    "started — I do her dosette box every week, so I would know — she is eating like always, and her "
    "sugar book is steady as a rock. She needs a reassuring chat sometime, not a drama. Please do not "
    "let her talk you into one."
)

# ── decoy 3: Percy Vydale — sounds like the others' turns, but no diabetes and a hot greenhouse ────────────
pt_vydale = _caller(
    "pt_vydale",
    "Percy Vydale",
    79,
    "M",
    chart=(
        "Hypertension, controlled on amlodipine; annual review in date.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Percy Vydale. I had a funny five minutes at the weekend and my wife wants it on the "
        "record, so here I am.\n\n"
        "I was repotting in the greenhouse — it was like an oven in there, I shall be honest — and I "
        "came over hot and swimmy and had to sit on the potting stool. I had a glass of water outside "
        "in the air and was right as ninepence inside ten minutes, finished the trays after. Nothing "
        "before, nothing since. The chemist ran my pressure through their machine on Monday and it "
        "read its usual. I am not diabetic or anything of that sort — it is just the one tablet for "
        "the pressure. An ordinary look-over when there is a gap would settle my wife, and that is the "
        "whole errand."
    ),
    onset="The one hot, swimmy spell at the weekend, in a baking greenhouse. Nothing since.",
    severity="Right as ninepence in ten minutes with a glass of water and some air.",
    history="Blood pressure, well controlled for years. Nothing else on my books.",
    medications="Amlodipine, one in the morning.",
    context="Retired; the greenhouse and I are available at your convenience.",
    gold=_routine_gold(),
    source="authored:gf_decoy_vydale_greenhouse_defused",
)

# ══ ASSEMBLY: the shared skeleton, both twins ══════════════════════════════════════════════════════════════

CLAIMANTS = (
    pt_umberwell,
    pt_uskmere,
    pt_uldcote,
    pt_uxbourne,
    pt_vennholm,
    pt_verecroft,
    pt_upgarth,
    pt_ullswick,
    pt_varnbrook,
    pt_vauxmead,
    pt_underhurst,
    pt_uttergill,
    pt_vexford,
    pt_vinstowe,
    pt_upcombe,
    pt_usworth,
    pt_uppermill,
    pt_vardale,
    pt_velthorpe,
    pt_vyebrook,
    pt_unsworth,
    pt_urswell,
    pt_vantham,
    pt_volgarth,
    pt_uxley,
    pt_umberleigh,
    pt_verwood,
    pt_ulcombe,
)

HOLDERS = (
    pt_upwell,
    pt_vange,
    pt_uffington,
    pt_vowchurch,
    pt_ulgham,
    pt_vernley,
    pt_upshaw,
    pt_uckmere,
    pt_vinehurst,
    pt_ubbeston,
    pt_vaudrey,
    pt_urchfont,
    pt_vobster,
    pt_uplowman,
    pt_vigobrook,
    pt_undermere,
    pt_uxcombe,
    pt_venngarth,
    pt_uldale,
    pt_varleigh,
    pt_upperby,
    pt_ventnor,
    pt_usway,
    pt_vernditch,
    pt_ullenhall,
    pt_vyner,
    pt_umberfold,
    pt_uphollow,
)

CARRIERS = (
    pt_umberwell_c,
    pt_uskmere_b,
    pt_uldcote_k,
    pt_uxbourne_s,
    pt_vennholm_g,
    pt_verecroft_d,
    pt_upgarth_m,
    pt_verrall,
    pt_upperton,
    pt_venmore,
    pt_ullmead,
    pt_vickridge,
    pt_vexford_l,
    pt_uphill,
    pt_undercliffe_j,
)

BOARD_CARDS = CLAIMANTS + HOLDERS + CARRIERS + (pt_varcoe, pt_undercliffe, pt_vydale)

#: The sanctioned same-surname pairs: family carriers on the same board as their claimant (or decoy).
KIN_OF = {
    "pt_umberwell_c": "pt_umberwell",
    "pt_uskmere_b": "pt_uskmere",
    "pt_uldcote_k": "pt_uldcote",
    "pt_uxbourne_s": "pt_uxbourne",
    "pt_vennholm_g": "pt_vennholm",
    "pt_verecroft_d": "pt_verecroft",
    "pt_upgarth_m": "pt_upgarth",
    "pt_vexford_l": "pt_vexford",
    "pt_undercliffe_j": "pt_undercliffe",
}

#: Standing-reason heads per contest, in contest order (the v2 surface policy renders these lines).
_STANDING_HEADS = (
    "Annual type 2 diabetes review",
    "Annual thyroid review",
    "Diabetes medication review",
    "Annual review, diet-controlled type 2 diabetes",
    "Insulin review, stable type 2 diabetes",
    "Thyroid dose review",
    "Annual diabetes review with foot check",
    "Annual diabetes review, carer-scheduled",
    "Annual type 2 diabetes review",
    "Annual thyroid review",
    "Diabetes tablets review",
    "Diabetes medication review",
    "Annual prediabetes check",
    "Thyroid function review, recent bloods",
    "Annual diabetes review",
    "Annual type 2 diabetes review",
    "Diabetes medication review",
    "Annual thyroid review",
    "Annual diabetes review",
    "Annual type 2 diabetes review",
    "Insulin pen technique review",
    "Annual diabetes review",
    "Diabetes medication review",
    "Annual thyroid review",
    "Annual type 2 diabetes review",
    "Annual diabetes review",
    "Thyroid dose review",
    "Annual type 2 diabetes review",
)

#: Per-contest decisive strings (claimant order), replacing the original board-wide "fluconazole" — which
#: scanned the wrong atom: the recited rule triggers on ANY new medicine, so a fact answer could hand the
#: union in paraphrase ("the capsules") while dodging the drug name. Each entry is the verbatim string
#: whose absence from every chart and every effective split fact answer actually protects that contest's
#: union: for SYMPTOM-direction claimants (turns in their own piece 1) it is the new-medicine trigger as
#: the split twin speaks it ("capsule", or the consult that stands in for it); for DRUG-direction
#: claimants (trigger in their own piece 1) it is the turns scene that rides the carrier call or
#: ring-back. Both twins speak every string (the plain intake carries the whole picture), so the shared
#: `CONTESTS` tuple stays pair-identical.
_DECISIVE_FACTS = (
    "a biscuit put",  # C1 Umberwell (drug-direction): the turns ride Christine's call
    "capsule",  # C2 Uskmere (symptom-direction): the trigger rides Brian's call
    "toast down",  # C3 Uldcote: the turns ride Keith's call
    "skin doctor",  # C4 Uxbourne: the consult rides Susan's call
    "wobbly at the sink",  # C5 Vennholm: the turns ride Gail's call
    "capsule",  # C6 Verecroft: the trigger rides Dawn's call
    "shed doorway",  # C7 Upgarth: the turns ride Michael's call
    "capsule",  # C8 Ullswick: the trigger rides Joan Verrall's call
    "sat back down",  # C9 Varnbrook: the turns ride Ted Upperton's call
    "capsule",  # C10 Vauxmead: the trigger rides Rita Venmore's call
    "biscuit tin",  # C11 Underhurst: the turns ride Frank Ullmead's call
    "capsule",  # C12 Uttergill: the trigger rides Doreen Vickridge's call
    "woolly-headed",  # C13 Vexford: the turns ride Lynn's call
    "capsule",  # C14 Vinstowe: the name rides her own ring-back
    "between my knees",  # C15 Upcombe: the turns ride his ring-back
    "capsule",  # C16 Usworth: the trigger rides her ring-back
    "shaky before my tea",  # C17 Uppermill: the turns ride his ring-back
    "capsule",  # C18 Vardale: the trigger rides her ring-back
    "with sweet tea",  # C19 Velthorpe: the turns ride his ring-back
    "capsule",  # C20 Vyebrook: the trigger rides her ring-back
    "allotment gate",  # C21 Unsworth: the turns ride his ring-back
    "private",  # C22 Urswell: the consult rides her ring-back
    "behind the tills",  # C23 Vantham: the turns ride his ring-back
    "propped against",  # C24 Volgarth: the dentist's letter rides her ring-back
    "seed boxes",  # C25 Uxley: the turns ride his ring-back
    "capsule",  # C26 Umberleigh: the trigger rides her ring-back
    "on the stairs",  # C27 Verwood: the turns ride his ring-back
    "capsule",  # C28 Ulcombe: the trigger rides her ring-back
)

#: Contested-slot times cycle over the five clinicians' afternoon follow-up columns.
_SLOT_TIMES = ("13:00", "13:20", "13:40", "14:40", "15:00", "15:20")
_CONTEST_PROVIDERS = (
    DR_VELLACOTT,
    DR_URSWICK,
    DR_VANSTONE,
    DR_UNDERHAY,
    DR_VEARNCOMBE,
)

CONTESTS = tuple(
    BoardContest(
        claimant=CLAIMANTS[i].id,
        holder=HOLDERS[i].id,
        specialty=DIABETES_ENDOCRINE,
        provider_id=_CONTEST_PROVIDERS[i // 6].id,
        slot_hhmm=_SLOT_TIMES[i % 6],
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            f"{_STANDING_HEADS[i]} (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact=_DECISIVE_FACTS[i],
    )
    for i in range(28)
)

DECOYS_PLAIN = (
    Decoy(patient_id="pt_varcoe"),
    Decoy(patient_id="pt_undercliffe"),
    Decoy(patient_id="pt_vydale"),
)
#: Same decoy ids, but Mabel Undercliffe's defusing facts arrive in her daughter's call (§6).
DECOYS_SPLIT = (
    Decoy(patient_id="pt_varcoe"),
    Decoy(patient_id="pt_undercliffe", defusing_caller_id="pt_undercliffe_j"),
    Decoy(patient_id="pt_vydale"),
)

#: Every inbound call, in arrival order — identical across the twins (the split twin adds only RECALL
#: beats, which are call structure). Desks are the mesh4 assignment; three corpus voicemail callers carry
#: the forced waits on three different desks.
#:
#: ORDER IS LOAD-BEARING at n=28: under meshfull, holder i sits queue-first on generated desk
#: `spreadsheet_id(i-1)` (A..Z, AA, AB — all 28 letters spoken for) and callers take those same desks in
#: first-arrival order, so the naive race stays holder-first only if the 28 claimants are exactly the
#: first 28 callers — every claimant then queues BEHIND a holder and every holder keeps in round 0. A
#: claimant on any later (holder-free) desk (AC+) would race ahead of the B..Z holders and the naive
#: floor would seat claimants (the S10v2 naive-starvation gate refuses exactly that; measured on this
#: board's first arrival plan, which interleaved carriers among the claimants).
ARRIVALS: tuple[tuple[str, str, int], ...] = (
    ("pt_umberwell", "A", 0),
    ("pt_uskmere", "B", 4),
    ("pt_uldcote", "C", 8),
    ("pt_uxbourne", "D", 12),
    ("pt_vennholm", "A", 16),
    ("pt_verecroft", "B", 20),
    ("pt_upgarth", "C", 24),
    ("pt_ullswick", "D", 28),
    ("pt_varnbrook", "A", 32),
    ("pt_vauxmead", "B", 36),
    ("pt_underhurst", "C", 40),
    ("pt_uttergill", "D", 44),
    ("pt_vexford", "A", 48),
    ("pt_vinstowe", "B", 52),
    ("pt_upcombe", "C", 56),
    ("pt_usworth", "D", 60),
    ("pt_uppermill", "A", 64),
    ("pt_vardale", "B", 68),
    ("pt_velthorpe", "C", 72),
    ("pt_vyebrook", "D", 76),
    ("pt_unsworth", "A", 80),
    ("pt_urswell", "B", 84),
    ("pt_vantham", "C", 88),
    ("pt_volgarth", "D", 92),
    ("pt_uxley", "A", 96),
    ("pt_umberleigh", "B", 100),
    ("pt_verwood", "C", 104),
    ("pt_ulcombe", "D", 108),
    ("pt_lachaux", "B", 112),
    ("pt_varcoe", "B", 116),
    ("pt_umberwell_c", "C", 120),
    ("pt_dunmore", "C", 124),
    ("pt_uskmere_b", "D", 128),
    ("pt_undercliffe", "C", 132),
    ("pt_uldcote_k", "A", 136),
    ("pt_uxbourne_s", "B", 140),
    ("pt_ledwidge", "A", 144),
    ("pt_vennholm_g", "C", 148),
    ("pt_verecroft_d", "D", 152),
    ("pt_upgarth_m", "A", 156),
    ("pt_verrall", "B", 160),
    ("pt_vydale", "D", 164),
    ("pt_upperton", "C", 168),
    ("pt_arundel", "D", 172),
    ("pt_venmore", "D", 176),
    ("pt_ullmead", "A", 180),
    ("pt_vickridge", "B", 184),
    ("pt_vexford_l", "C", 188),
    ("pt_uphill", "D", 192),
    ("pt_undercliffe_j", "A", 196),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

MEMO_COVER_LINE = (
    "The diabetes and endocrine list is carrying a neighbouring practice's monitoring patients while "
    "that surgery winds down, and its block-booked clinic slots were released back to us this week, "
    "which is why those diaries show so many returned appointments."
)

#: The split twin's carrier pieces: claimant -> the carrier whose call is piece 2.
_CARRIER_OF = {
    "pt_umberwell": "pt_umberwell_c",
    "pt_uskmere": "pt_uskmere_b",
    "pt_uldcote": "pt_uldcote_k",
    "pt_uxbourne": "pt_uxbourne_s",
    "pt_vennholm": "pt_vennholm_g",
    "pt_verecroft": "pt_verecroft_d",
    "pt_upgarth": "pt_upgarth_m",
    "pt_ullswick": "pt_verrall",
    "pt_varnbrook": "pt_upperton",
    "pt_vauxmead": "pt_venmore",
    "pt_underhurst": "pt_ullmead",
    "pt_uttergill": "pt_vickridge",
    "pt_vexford": "pt_vexford_l",
    "pt_vinstowe": "pt_uphill",
}

#: The split twin's ring-backs: claimant -> (at_min, desk, text). ONE recall per caller, always on a desk
#: other than the claimant's own arrival desk.
_RECALL_OF: dict[str, tuple[int, str, str]] = {
    "pt_vexford": (141, "D", VEXFORD_RECALL_TEXT),
    "pt_vinstowe": (143, "A", VINSTOWE_RECALL_TEXT),
    "pt_upcombe": (147, "A", UPCOMBE_RECALL_TEXT),
    "pt_usworth": (149, "B", USWORTH_RECALL_TEXT),
    "pt_uppermill": (153, "C", UPPERMILL_RECALL_TEXT),
    "pt_vardale": (155, "D", VARDALE_RECALL_TEXT),
    "pt_velthorpe": (159, "A", VELTHORPE_RECALL_TEXT),
    "pt_vyebrook": (161, "B", VYEBROOK_RECALL_TEXT),
    "pt_unsworth": (165, "C", UNSWORTH_RECALL_TEXT),
    "pt_urswell": (167, "D", URSWELL_RECALL_TEXT),
    "pt_vantham": (171, "A", VANTHAM_RECALL_TEXT),
    "pt_volgarth": (173, "B", VOLGARTH_RECALL_TEXT),
    "pt_uxley": (177, "C", UXLEY_RECALL_TEXT),
    "pt_umberleigh": (179, "D", UMBERLEIGH_RECALL_TEXT),
    "pt_verwood": (183, "A", VERWOOD_RECALL_TEXT),
    "pt_ulcombe": (185, "B", ULCOMBE_RECALL_TEXT),
}

PLAIN_EVIDENCE = tuple(
    EvidenceCall(caller_id=card.id, about_claimant=card.id) for card in CLAIMANTS
)

SPLIT_EVIDENCE = tuple(
    piece
    for card in CLAIMANTS
    for piece in (
        (EvidenceCall(caller_id=card.id, about_claimant=card.id),)
        + (
            (
                EvidenceCall(
                    caller_id=_CARRIER_OF[card.id],
                    about_claimant=card.id,
                ),
            )
            if card.id in _CARRIER_OF
            else ()
        )
        + (
            (
                EvidenceCall(
                    caller_id=card.id,
                    about_claimant=card.id,
                    kind="recall",
                    at_min=_RECALL_OF[card.id][0],
                    desk=_RECALL_OF[card.id][1],
                    text=_RECALL_OF[card.id][2],
                ),
            )
            if card.id in _RECALL_OF
            else ()
        )
    )
)

#: The split twin's voices: claimants say only piece 1; carriers add their mention; the split decoy loses
#: her defusal to her daughter. Charts, golds and names stay byte-identical (the pair-identity gate);
#: fact-field deltas are declared in `SPLIT_FACTS_OVERRIDES` below.
SPLIT_INTAKE_OVERRIDES = {
    "pt_umberwell": UMBERWELL_SPLIT_INTAKE,
    "pt_umberwell_c": UMBERWELL_C_SPLIT_INTAKE,
    "pt_uskmere": USKMERE_SPLIT_INTAKE,
    "pt_uskmere_b": USKMERE_B_SPLIT_INTAKE,
    "pt_uldcote": ULDCOTE_SPLIT_INTAKE,
    "pt_uldcote_k": ULDCOTE_K_SPLIT_INTAKE,
    "pt_uxbourne": UXBOURNE_SPLIT_INTAKE,
    "pt_uxbourne_s": UXBOURNE_S_SPLIT_INTAKE,
    "pt_vennholm": VENNHOLM_SPLIT_INTAKE,
    "pt_vennholm_g": VENNHOLM_G_SPLIT_INTAKE,
    "pt_verecroft": VERECROFT_SPLIT_INTAKE,
    "pt_verecroft_d": VERECROFT_D_SPLIT_INTAKE,
    "pt_upgarth": UPGARTH_SPLIT_INTAKE,
    "pt_upgarth_m": UPGARTH_M_SPLIT_INTAKE,
    "pt_ullswick": ULLSWICK_SPLIT_INTAKE,
    "pt_verrall": VERRALL_SPLIT_INTAKE,
    "pt_varnbrook": VARNBROOK_SPLIT_INTAKE,
    "pt_upperton": UPPERTON_SPLIT_INTAKE,
    "pt_vauxmead": VAUXMEAD_SPLIT_INTAKE,
    "pt_venmore": VENMORE_SPLIT_INTAKE,
    "pt_underhurst": UNDERHURST_SPLIT_INTAKE,
    "pt_ullmead": ULLMEAD_SPLIT_INTAKE,
    "pt_uttergill": UTTERGILL_SPLIT_INTAKE,
    "pt_vickridge": VICKRIDGE_SPLIT_INTAKE,
    "pt_vexford": VEXFORD_SPLIT_INTAKE,
    "pt_vexford_l": VEXFORD_L_SPLIT_INTAKE,
    "pt_vinstowe": VINSTOWE_SPLIT_INTAKE,
    "pt_uphill": UPHILL_SPLIT_INTAKE,
    "pt_upcombe": UPCOMBE_SPLIT_INTAKE,
    "pt_usworth": USWORTH_SPLIT_INTAKE,
    "pt_uppermill": UPPERMILL_SPLIT_INTAKE,
    "pt_vardale": VARDALE_SPLIT_INTAKE,
    "pt_velthorpe": VELTHORPE_SPLIT_INTAKE,
    "pt_vyebrook": VYEBROOK_SPLIT_INTAKE,
    "pt_unsworth": UNSWORTH_SPLIT_INTAKE,
    "pt_urswell": URSWELL_SPLIT_INTAKE,
    "pt_vantham": VANTHAM_SPLIT_INTAKE,
    "pt_volgarth": VOLGARTH_SPLIT_INTAKE,
    "pt_uxley": UXLEY_SPLIT_INTAKE,
    "pt_umberleigh": UMBERLEIGH_SPLIT_INTAKE,
    "pt_verwood": VERWOOD_SPLIT_INTAKE,
    "pt_ulcombe": ULCOMBE_SPLIT_INTAKE,
    "pt_undercliffe": UNDERCLIFFE_SPLIT_INTAKE,
    "pt_undercliffe_j": UNDERCLIFFE_J_SPLIT_INTAKE,
}

#: The split twin's phone-probe answers (`facts_overrides`): the canonical fact
#: answers are the PLAIN persona's full-disclosure ones — capsule-start paired with the turns in `onset`,
#: the "five o'clock tablet needs deciding" ask in `severity`, the decisive drug name in `medications` —
#: so one desk's probe would retrieve the whole picture. Each override is what THAT patient would
#: volunteer to one ordinary question in the split twin: ONLY their own piece-1 fragment, routine
#: register, never the clinic rule or the dose-decision framing. The displacement discipline (solvability
#: re-review) is directional: a SYMPTOM-direction claimant's `medications` defers the new
#: medicine entirely (the chemist/kin mind the list — the trigger lives only in the call that carries
#: it), and a DRUG-direction claimant's `severity`/`onset` withhold the turns (well-this-minute, the
#: mouth is the only complaint), so no probe hands any single desk the half its split fiction placed in
#: another call — in either direction. The per-contest `_DECISIVE_FACTS` scan enforces exactly this
#: displacement mechanically. Only the leaking topics are overridden; every other answer stays
#: byte-shared with the plain twin, per the pair gate.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_umberwell": {
        "onset": (
            "Nothing new in myself to speak of — the thrush under my dentures came up last week and "
            "the night doctor left me something for it on Saturday."
        ),
        "severity": (
            "Right as rain this minute. The mouth is sore with the thrush, but the night doctor's "
            "course is seeing to that."
        ),
        "medications": (
            "Gliclazide with breakfast and with tea, amlodipine in the morning — and what the "
            "out-of-hours doctor left me on Saturday. I could not tell you the name without the box."
        ),
    },
    "pt_uskmere": {
        "onset": (
            "The swimmy turn was yesterday, on the washing line; nothing before and nothing since. I "
            "have been eating like a bird since my cold."
        ),
        "medications": (
            "Gliclazide morning and evening, the statin at night. My son does my collecting — he and "
            "the chemist keep the list between them."
        ),
    },
    "pt_uldcote": {
        "onset": (
            "Nothing in myself — the dentist found thrush two days back and started me on a course; "
            "her letter has the details."
        ),
        "severity": (
            "I am well this minute. The mouth is the only complaint, and the dentist has that in hand."
        ),
        "medications": (
            "Gliclazide morning and night, the statin at bedtime — and the dentist's course for the "
            "thrush. The name is in her letter; I shall not attempt it."
        ),
    },
    "pt_uxbourne": {
        "onset": (
            "The light-headed spells were midweek, before meals. Since my sister went I have not been "
            "eating properly, and there is the story."
        ),
        "severity": "Perfectly composed now. Eating puts it right each time.",
        "medications": (
            "Gliclazide with breakfast and my evening meal, and the thyroid tablet first thing. My "
            "daughter keeps my paperwork straight."
        ),
    },
    "pt_vennholm": {
        "onset": (
            "Nothing fresh — the thrush came after my antibiotics, and the out-of-hours doctor left "
            "me a course for it two nights back."
        ),
        "severity": (
            "Steady today. The appetite has been shocking since the chest thing, but that is old "
            "news, not new."
        ),
        "medications": (
            "Gliclazide, the big dose at breakfast and a smaller one with tea — and what the "
            "out-of-hours doctor left for the thrush. The name escapes me; my wife has the box."
        ),
    },
    "pt_verecroft": {
        "onset": (
            "I have been picking at my lunch like a sparrow for a fortnight, and the shaky spells "
            "were these last two mornings."
        ),
        "severity": "Mended each time with a biscuit and a sit-down; bright as a button now.",
        "medications": (
            "Gliclazide morning and teatime, the bone tablet on Sundays. Dawn sees to my chemist "
            "things; she has the ins and outs."
        ),
    },
    "pt_upgarth": {
        "onset": (
            "Nothing in myself — my son booked me in about the mouth on Tuesday and the doctor "
            "started me on a course for the thrush, and that is the whole of the news."
        ),
        "severity": (
            "Perfectly alright today. The mouth is sore and I am leaving a bit on the plate, but "
            "nothing a man rings a doctor over."
        ),
        "medications": (
            "Gliclazide twice a day, tamsulosin at breakfast — and the doctor's course for the "
            "thrush, one a day. The name is on the box at home."
        ),
    },
    "pt_ullswick": {
        "onset": (
            "The swimmy spells have been this week, before lunch. I have been eating small with this "
            "new denture."
        ),
        "severity": "A ginger biscuit sees it off, and I am quite well as we speak.",
        "medications": (
            "Gliclazide twice a day and the water tablet in the morning. My neighbour Joan does my "
            "collecting; the chemist keeps the list."
        ),
    },
    "pt_varnbrook": {
        "onset": (
            "Nothing beyond the mouth — the dentist started me on a course for thrush under the top "
            "plate, as of yesterday."
        ),
        "severity": (
            "I am right in myself. The plate has made the mouth sore all winter; the dentist's "
            "course is meant to see to it."
        ),
        "medications": (
            "Gliclazide morning and teatime, finasteride at night — and the dentist's course for "
            "the thrush. Her letter has the proper name."
        ),
    },
    "pt_vauxmead": {
        "onset": (
            "The light-headed spells were twice this week, before meals. My appetite has been poor a "
            "while — you will have the weight in my notes."
        ),
        "severity": "Squash and a digestive mend it, and I am well now.",
        "medications": (
            "Gliclazide morning and evening meal, the eye drops at night. Rita runs me to the "
            "chemist; the list stays with them."
        ),
    },
    "pt_underhurst": {
        "onset": (
            "Nothing new in myself — the weekend doctor left me something for thrush in my mouth on "
            "Sunday, and that is all the news I have."
        ),
        "severity": (
            "I am steady today, thank you. The mouth is sore and I am mostly on soup, but at my age "
            "that is hardly a headline."
        ),
        "medications": (
            "Gliclazide twice a day, the softener when needed — and what the weekend doctor left me "
            "on Sunday; the chemist has the name of it."
        ),
    },
    "pt_uttergill": {
        "onset": (
            "The sweaty, dizzy spells have been twice since the weekend, before I ate. I skip "
            "lunches more than I should, caring for my husband."
        ),
        "severity": "A glucose sweet mends it in minutes and I am perfectly capable today.",
        "medications": (
            "Gliclazide twice a day and an allergy tablet in the morning. The chemist keeps my list; "
            "I have lists enough with my husband's."
        ),
    },
    "pt_vexford": {
        "onset": (
            "Only the sore mouth this week, and my eating has gone to pot with it, my daughter "
            "says."
        ),
        "severity": (
            "Right as rain today. My daughter will tell you I undersell things, but there is nothing "
            "on me as we speak."
        ),
        "medications": (
            "Gliclazide twice a day, the baby aspirin — and what the out-of-hours doctor started on "
            "Monday; I rang that through to you this morning."
        ),
    },
    "pt_vinstowe": {
        "onset": (
            "The trembly spells were twice this week, before meals. This sore mouth has me eating "
            "next to nothing."
        ),
        "severity": "Barley water and a plain biscuit and I come round in no time. Right as a trivet now.",
        "medications": (
            "Gliclazide twice a day and the calcium twice a day. George runs me to the chemist; they "
            "keep my list there."
        ),
    },
    "pt_upcombe": {
        "onset": (
            "Nothing you could set a clock by — the sore mouth this last week, and my eating has "
            "been thin with it."
        ),
        "severity": (
            "Nothing on me as we sit here. The mouth makes a chore of mealtimes, and that is the "
            "size of it."
        ),
        "medications": (
            "Gliclazide twice a day, sertraline in the morning — and what the out-of-hours doctor "
            "started on Sunday; I squared that with you this morning."
        ),
    },
    "pt_usworth": {
        "onset": (
            "The sweaty, strange spell was mid-morning today, at the kitchen table. I have been "
            "eating very little — my stomach never was a big eater's."
        ),
        "severity": "Two squares of chocolate and ten minutes and it lifted entirely. Quite myself now.",
        "medications": (
            "Gliclazide twice a day and the stomach tablet in the morning. The chemist minds my list "
            "better than I would."
        ),
    },
    "pt_uppermill": {
        "onset": (
            "The mouth has been sore a week or more; I was seen about it on Monday and there is a "
            "course for it."
        ),
        "severity": (
            "Steady as a rock, me. The mouth is the only bother, and the course is seeing to that."
        ),
        "medications": (
            "Gliclazide, the big breakfast dose and a teatime one, allopurinol daily — and the "
            "course for the thrush since Monday; the name is on the paperwork somewhere."
        ),
    },
    "pt_vardale": {
        "onset": (
            "The swimmy spells were Sunday dinner and yesterday, in my chair. I eat like a wren at "
            "the best of times and less this week."
        ),
        "severity": (
            "My son gives me my lucozade and I come back to myself in minutes; I am back now."
        ),
        "medications": (
            "Gliclazide twice a day and my paracetamol. My son minds the boxes and the chemist minds "
            "the list."
        ),
    },
    "pt_velthorpe": {
        "onset": (
            "The dentist found the thrush on Tuesday and started her course; the mouth had been sore "
            "a while before that."
        ),
        "severity": (
            "Right as anything, me. The mouth is sore under the plate, and the dentist has that in "
            "hand."
        ),
        "medications": (
            "Gliclazide twice a day, drops at night — and the dentist's course since Tuesday; her "
            "letter has the name."
        ),
    },
    "pt_vyebrook": {
        "onset": (
            "The light-headed spell was yesterday, at the coffee morning. I have been off my food "
            "all week — the mouth stings with anything sharp."
        ),
        "severity": (
            "Sweet tea and a custard cream and I was carrying trays again in fifteen minutes. Well "
            "now."
        ),
        "medications": (
            "Gliclazide twice a day and the bisoprolol in the morning; the chemist keeps my list."
        ),
    },
    "pt_unsworth": {
        "onset": (
            "The appetite never picked up after that stomach upset a fortnight back; the mouth "
            "trouble came on top this week."
        ),
        "severity": (
            "Nothing ailing me as we speak. The appetite is slow coming back, and that is the extent "
            "of it."
        ),
        "medications": (
            "Gliclazide twice a day, the stopper tablets if the stomach turns — and the out-of-hours "
            "course from Monday; it went on my record this morning."
        ),
    },
    "pt_urswell": {
        "onset": (
            "The dizzy spells were twice this week, before meals, in my kitchen. I eat like a "
            "sparrow, always have."
        ),
        "severity": "Two jelly babies and a sit-down puts me right inside ten minutes. Right now, too.",
        "medications": (
            "Gliclazide twice a day, the little forty ones. My son keeps the calendar and the "
            "chemist keeps the list."
        ),
    },
    "pt_vantham": {
        "onset": "The mouth has been a chore this week and I have been skipping lunch with it.",
        "severity": (
            "Nothing on me now — fit for my shift. The mouth is mending on the course, they tell me."
        ),
        "medications": (
            "Gliclazide twice a day, candesartan in the morning — and the course the out-of-hours "
            "doctor started on Saturday; I phoned it through first thing."
        ),
    },
    "pt_volgarth": {
        "onset": (
            "The trembly spells were twice this week, before my evening meal. The new dentures have "
            "made a misery of eating and the soreness finished the job."
        ),
        "severity": "The biscuit barrel sorts it in ten minutes, and I am myself now.",
        "medications": (
            "Gliclazide twice a day and the mirtazapine at night. My nephew sees to the chemist for "
            "me."
        ),
    },
    "pt_uxley": {
        "onset": (
            "The mouth this last week — eating has been poor with it, and cooking for one is a bore "
            "at the best of times."
        ),
        "severity": (
            "Nothing the matter as we speak — the plot got its hoeing this morning, which tells you "
            "most of it."
        ),
        "medications": (
            "Gliclazide twice a day, an allergy tablet some nights — and the course from the "
            "out-of-hours doctor since Sunday; my granddaughter has the box."
        ),
    },
    "pt_umberleigh": {
        "onset": (
            "The shaky spells were twice this week, before meals. I have been eating small since my "
            "cold and smaller since the mouth."
        ),
        "severity": "Emergency shortbread and ten minutes and I am back at the crossword.",
        "medications": (
            "Gliclazide twice a day and the bone tablet on Sundays. My daughter does my chemist "
            "runs; the list is in her hands."
        ),
    },
    "pt_verwood": {
        "onset": (
            "The mouth has me eating about half what I should this week; I was seen in town on "
            "Tuesday and there is a course for the thrush."
        ),
        "severity": (
            "Good as new, me. The mouth is a bore at mealtimes, and that is the whole of it."
        ),
        "medications": (
            "Gliclazide, the big morning dose and the teatime one, tamsulosin daily — and the course "
            "for the thrush since Tuesday; the name is on the paperwork."
        ),
    },
    "pt_ulcombe": {
        "onset": (
            "Light-headed on Tuesday teatime and again this morning before breakfast, at the "
            "dresser. My eating has been poor a fortnight."
        ),
        "severity": "The travel-sweet tin does the trick in ten minutes; quite well now.",
        "medications": (
            "Gliclazide twice a day and the folic acid. My son sorts the chemist; I could not tell "
            "you more than that."
        ),
    },
    # The decoy on metformin: her canonical `onset`/`medications` name the capsules outright, which the
    # decisive-string scan refuses board-wide; the defusal (metformin only, chemist unconcerned) stays.
    "pt_varcoe": {
        "onset": (
            "It started this week, when the out-of-hours doctor gave me something for the thrush. "
            "No symptoms at all since — the state is all in my head."
        ),
        "medications": (
            "Metformin twice a day — only the metformin for my sugar — and the thrush course this "
            "week; the chemist looked the pair up together and was not worried."
        ),
    },
    # The gliclazide decoy: her canonical `medications` says "no capsules of any sort", which trips the
    # same scan; the defusing SUBSTANCE (nothing new started, dosette checked weekly) is kept verbatim.
    "pt_undercliffe": {
        "medications": (
            "Gliclazide with breakfast, the calcium twice a day. Nothing new of any sort — my "
            "daughter does my dosette box every week and she would tell you the same."
        ),
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=28,
    theme_slug="gliclazide_fluconazole",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=PLAIN_EVIDENCE,
    decoys=DECOYS_PLAIN,
    cards=BOARD_CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="300",
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=28,
    theme_slug="gliclazide_fluconazole",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=SPLIT_EVIDENCE,
    decoys=DECOYS_SPLIT,
    cards=BOARD_CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="300",
    voicemail_callers=VOICEMAIL,
)

# Plain FIRST — the split twin seeds its calendar from it (`calendar_of`).
register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
