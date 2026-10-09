"""P01 `warfarin_inr` — six warfarin patients each acquire a new interacting medicine overnight; every one of them needs TODAY's INR draw at the anticoagulation clinic (row P01 of the board assignments).

The mechanism family, per the locked assignment: warfarin + a newly started interacting medicine from a **non-institutional prescriber on the patient's side** (an emergency dentist, an out-of-hours doctor, a chemist's counter, a private consult) ⇒ an INR check the day the medicine starts. Assembled, the reprioritization is textbook-obvious — classic potentiating interactions (metronidazole, erythromycin, miconazole oral gel, amiodarone, co-trimoxazole, fluconazole) plus the anticoagulation clinic's stated same-day-testing rule, which every claimant carries as a FACT of their care, never as an instruction to a desk. Solo, every piece reads routine: a repeat request, a moved appointment, a relative's own errand with an FYI on the end. The ED adds nothing structurally — an emergency department does not run the practice's INR clinic or write its dosing advice — and no presentation, solo or assembled, touches the SOP red-flag list (everyone "feels quite well"; the urgency is pharmacological, not symptomatic).

Both twins share the skeleton byte-for-byte (contests, cards, charts, decoys, providers, cover line); they differ ONLY in call structure and the split twin's sub-threshold overrides. The plain twin's claimants say everything in their own single intake (the canonical card text, whose fact answers restate the assembled story — correct for plain). The split twin distributes each claimant's picture over 2-3 calls on >=2 mesh4 desks — a routine-sounding intake, then a family/neighbour carrier with their own front-office matter, or the claimant ringing back — via `intake_overrides` and recall `EvidenceCall`s, and rewrites the probed fact channel via `facts_overrides` (a desk that RINGS a patient gets only what that patient would volunteer to one ordinary question, never the assembled case). Ruling 3's split discipline, applied throughout: every split piece reads routine ON ITS FACE — a piece may name the new medicine plainly, in routine record-keeping register, but never carries the warfarin/maintenance context in the same call; assembly requires chart cross-reference (deliberate single-desk diligence) or multi-piece union (cross-desk in a mesh), and that gradient IS the construct.

Decoys (both twins, ids symmetric): `pt_byerfold` apes the board's own pattern (new antibiotic + "I used to be tested the same day") but was switched from warfarin to apixaban eighteen months ago — no INR monitoring exists to be urgent about; `pt_belridge` has a genuine out-of-hours interaction instruction (clarithromycin + her statin) whose correct handling is a paused tablet and a routine note, not a bump — and in the split twin the defusing fact (WHICH tablet) arrives in her husband's call, so aggregation can cancel urgency as well as create it.

DATA ONLY, on `deadline_day`'s precedent: the gates live in `design_check`, the dials in `pressure`, the solver in `values`. Registration at import, PLAIN FIRST.
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
    ANTICOAGULATION,
    FOLLOW_UP_HEAVY_TEMPLATE,
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

PLAIN_ID = "warfarin_inr_plain"
SPLIT_ID = "warfarin_inr_split"
PAIR_ID = "P01_warfarin_inr"

# ── the practice extension: the anticoagulation service, six clinicians deep today ───────────────────────
# One provider per contest (the spread-contest visibility discipline, scaled the way `diaries` prescribes: more slots
# per diary = more providers, never a second contest on one provider-day). The memo cover line below is the
# fiction that pays for the size: the service is carrying a neighbouring practice's warfarin list this month.
DR_ASHGARTH = board_provider(
    "dr_ashgarth", "Dr. F. Ashgarth", ANTICOAGULATION, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_BELHOLM = board_provider(
    "dr_belholm", "Dr. K. Belholm", ANTICOAGULATION, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_BYERLUND = board_provider(
    "dr_byerlund", "Dr. O. Byerlund", ANTICOAGULATION, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_ASHMEAD = board_provider(
    "dr_ashmead", "Dr. U. Ashmead", ANTICOAGULATION, template=FOLLOW_UP_HEAVY_TEMPLATE
)
DR_BELLUND = board_provider(
    "dr_bellund",
    "H. Bellund, Anticoagulation Nurse Specialist",
    ANTICOAGULATION,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_BYERRIDGE = board_provider(
    "dr_byerridge",
    "Dr. W. Byerridge",
    ANTICOAGULATION,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
NEW_PROVIDERS = (
    DR_ASHGARTH,
    DR_BELHOLM,
    DR_BYERLUND,
    DR_ASHMEAD,
    DR_BELLUND,
    DR_BYERRIDGE,
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
    """A carrier's/decoy's gold: NON_URGENT primary care — no contested service in reach (leakage closed)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ── contest 1: metronidazole from the emergency dentist ──────────────────────────────────────────────────
pt_ashfold = _caller(
    "pt_ashfold",
    "Dennis Ashfold",
    77,
    "M",
    chart=(
        "Atrial fibrillation, rate-controlled; on warfarin, target INR 2.0-3.0, stable for four years.",
        "Warfarin managed at the practice's anticoagulation clinic — finger-prick INR with dosing advice "
        "given at the visit.",
        "Anticoagulation clinic advice on file: an INR the same day any new interacting "
        "medicine is started.",
        "Last INR twelve days ago, in range; next routine test listed for next week.",
        "Repeat medication: warfarin per clinic dosing sheet, atenolol 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. I'd best come straight to it — the anticoagulation clinic will want me tested "
        "today, and I'd rather you heard it from me this morning than found it out next week.\n\n"
        "I was at the emergency dental place in town yesterday with an abscess under a back tooth, and "
        "the dentist there has put me on metronidazole — the first tablets went down last night. When "
        "the warfarin clinic took me on they were very firm about antibiotics: if anything of that sort "
        "gets started, the finger-prick is to be done the day it starts, because the number can shoot up "
        "on it. The tablets started last night, so by their own rule the test falls today.\n\n"
        "The tooth is easier than it was and I'm well otherwise — no bleeding, nothing untoward. It's "
        "the test that can't wait, not me."
    ),
    onset=(
        "Nothing new in myself. The abscess was seen yesterday; the dentist's antibiotic started with "
        "last night's dose."
    ),
    severity=(
        "I'm well — no bleeding, no bruising, the tooth settling. It's the metronidazole against the "
        "warfarin that the clinic tests for, the day it starts."
    ),
    history="The irregular heartbeat, and warfarin these four years, tested at your anticoagulation clinic.",
    medications=(
        "Warfarin off the clinic's dosing sheet, atenolol of a morning — and since last night the "
        "metronidazole from the emergency dentist, five days of it."
    ),
    context="Retired; I'm a short walk from the surgery and free all day. My daughter Karen keeps my paperwork straight.",
    gold=board_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_claimant_metronidazole_dentist",
)

#: The split twin's piece 1: the SAME man, saying only the routine half.
ASHFOLD_SPLIT_INTAKE = (
    "Good morning. Nothing pressing — I'm ringing about my warfarin test that's listed for next week. "
    "I'm meant to be at my sister's over that way for a few days and I'd sooner move the test than cut "
    "the visit short. Could it go later in the week instead? Any day does me."
)

#: The split twin's phone-probe answers for the same man: sub-threshold, what HE would volunteer to one
#: ordinary question (the canonical answers are the PLAIN twin's and restate the
#: assembled story; a desk that rings him must not be handed the case).
ASHFOLD_SPLIT_FACTS = {
    "onset": "Nothing new in myself — it's only the date of next week's test I'm ringing about.",
    "severity": "I'm well — no bleeding, nothing untoward, and the tooth's easier than it was.",
    "medications": (
        "Warfarin off the clinic's dosing sheet, atenolol of a morning — and some tablets the emergency "
        "dentist left me for the tooth. I'd have to fetch the box to give you the name."
    ),
}

pt_ashfold_b = _caller(
    "pt_ashfold_b",
    "Karen Ashfold",
    49,
    "F",
    chart=(
        "Asthma, well controlled on an inhaled preventer; reliever as required.",
        "Repeat medication: beclometasone inhaler twice daily, salbutamol inhaler as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — a quick one, I hope. My preventer inhaler's down to its last few puffs and the chemist "
        "says the repeat needs signing off again before they can issue it. Could that be put through this "
        "week? The blue one's fine, it's just the brown one wanting doing."
    ),
    onset="Nothing new — the inhaler repeat has simply run out of sign-offs.",
    severity="I'm perfectly well; this is housekeeping, not a complaint.",
    history="Asthma since my twenties, steady on the same two inhalers.",
    medications="The brown preventer inhaler morning and night, the blue one hardly ever.",
    context=(
        "I work in town but I'm on the phone easily enough. I keep an eye on my father, Dennis Ashfold — "
        "I take him to his dental and clinic visits."
    ),
    gold=_routine_gold(),
    source="authored:warfarin_inr_carrier_daughter_inhaler_repeat",
)

#: The split twin's carrier piece: her own errand, plus the drug's name in routine record-keeping
#: register (the name plainly, NEVER the warfarin context or the clinic's rule in the same call).
ASHFOLD_B_SPLIT_INTAKE = (
    "Hello — a quick one, I hope. My preventer inhaler's down to its last few puffs and the chemist "
    "says the repeat needs signing off again before they can issue it. Could that be put through this "
    "week? The blue one's fine, it's just the brown one wanting doing.\n\n"
    "And while I've got you — my dad, Dennis Ashfold, he's one of yours. He was at the emergency "
    "dental place yesterday with an abscess and came away with metronidazole; the first tablets went "
    "down last night. He never remembers to tell anybody what he's been given, so could that go on his "
    "record? That's all it is."
)

# ── contest 2: erythromycin from the out-of-hours doctor ─────────────────────────────────────────────────
pt_belgarth = _caller(
    "pt_belgarth",
    "Sheila Belgarth",
    69,
    "F",
    chart=(
        "Two deep-vein thromboses and a pulmonary embolism over the years; on lifelong warfarin, target "
        "INR 2.5-3.5.",
        "Warfarin dosed through the practice's anticoagulation clinic — finger-prick INR read at the "
        "visit and the next dosing sheet written on the spot; last INR eight days ago, in range.",
        "Anticoagulation clinic advice on file: an INR the same day any new interacting "
        "medicine is started.",
        "Repeat medication: warfarin per clinic dosing sheet; compression stockings on prescription.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think I need the warfarin people today, and I'll tell you why so you can see it isn't "
        "me fussing.\n\n"
        "My chest has had a rattle since the weekend, and the out-of-hours doctor listened to it last "
        "night and started me on erythromycin — I took the first ones with my supper. Now, the clinic "
        "gave me a card years ago and it's pinned up by the kettle: any new antibiotic, ring the surgery "
        "and have the INR done the same day it starts, because the warfarin runs high on them. Last "
        "night counts as the start, so the test is due today by their card.\n\n"
        "The chest itself is nothing dramatic — I'm not breathless sitting here and there's no fever to "
        "speak of. It's the blood test that has the clock on it."
    ),
    onset="The chest rattle since the weekend; the out-of-hours doctor's antibiotic started last night.",
    severity=(
        "Middling chest, nothing frightening — no real breathlessness, no proper fever. The urgency is "
        "the erythromycin against the warfarin, which the clinic's card says to test the same day."
    ),
    history="The clots — two in the leg, one on the lung — and warfarin ever since, dosed at your clinic.",
    medications=(
        "Warfarin off the clinic's sheet, my stockings — and since supper last night the erythromycin "
        "from the out-of-hours doctor."
    ),
    context="My neighbour drives me when her car allows. I can be got in at short notice most of today.",
    gold=board_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_claimant_erythromycin_ooh",
)

#: The split twin's piece 1: the SAME woman, routine appointment-shuffling register.
BELGARTH_SPLIT_INTAKE = (
    "Hello. It's only a small thing. I'm due my routine warfarin test early next week, and my neighbour "
    "who drives me has her car going in for its MOT — when the clinic writes me in, could it be a "
    "morning she can manage? Nothing urgent about it, I just like these things settled early."
)

#: The split twin's piece 2: her OWN second call, later in the morning — the drug's name in routine
#: record-keeping register (no warfarin mention, no rule, no urgency in the same call).
BELGARTH_RECALL = (
    "It's Mrs Belgarth — I rang earlier about moving my test. This is nothing to do with that: the "
    "out-of-hours doctor listened to my chest last night and started me on erythromycin, and I know the "
    "surgery likes a note when another doctor gives me something. So that's me reporting it. The chest "
    "is much its usual self this morning."
)

#: The split twin's phone-probe answers for her: sub-threshold — the chest tablets in
#: passing without their name, never the interaction or the clinic's card in the same breath.
BELGARTH_SPLIT_FACTS = {
    "onset": (
        "The chest's had a rattle since the weekend, and it's being seen to. It's the day of my test I "
        "rang about."
    ),
    "severity": (
        "Middling chest, nothing frightening — I'm not breathless sitting here and there's no fever to "
        "speak of."
    ),
    "medications": (
        "Warfarin off the clinic's sheet, my stockings — and the chest tablets the night doctor left "
        "me; the name's on the box in the kitchen."
    ),
}

# ── contest 3: miconazole oral gel from the chemist's counter ────────────────────────────────────────────
pt_byerholm = _caller(
    "pt_byerholm",
    "Harold Byerholm",
    81,
    "M",
    chart=(
        "Atrial fibrillation; on warfarin, target INR 2.0-3.0, reviewed at the practice's anticoagulation "
        "clinic.",
        "Anticoagulation clinic advice on file: an INR the same day any new interacting "
        "medicine is started.",
        "Lives alone; a neighbour assists with shopping and prescription collection.",
        "Last INR eleven days ago, in range; next test on the clinic's routine schedule.",
        "Repeat medication: warfarin per clinic dosing sheet, tamsulosin 400 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My mouth's been sore under the denture this last week — thrush, the chemist reckoned — "
        "and my neighbour fetched me a tube of the gel he recommended. Miconazole, it says on the box. I "
        "first used it last night before bed.\n\n"
        "Now the warfarin clinic told me once, and they made a point of it: that particular gel and "
        "warfarin don't keep company, even though it only goes in the mouth, and if I ever used it the "
        "blood test had to be done the same day. I've started on it, so by their telling the finger-prick "
        "wants doing today.\n\n"
        "The mouth's only a nuisance — I'm right enough in myself."
    ),
    onset="The sore mouth this last week; the chemist's gel first used last night before bed.",
    severity=(
        "Only the sore mouth, and that's a nuisance rather than a trouble. It's the miconazole gel with "
        "the warfarin the clinic said to test for, the day it starts."
    ),
    history="The irregular heart, on warfarin a good few years, seen at your anticoagulation clinic.",
    medications=(
        "Warfarin off the clinic's sheet, the waterworks tablet at night — and since last night the "
        "miconazole gel from the chemist for my mouth."
    ),
    context=(
        "I live alone; Mrs Belmead along the road does my shopping and collects my prescriptions. I can "
        "come in whenever, though I'm slow on my feet."
    ),
    gold=board_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_claimant_miconazole_chemist",
)

#: The split twin's piece 1: the SAME man, on an unrelated routine matter.
BYERHOLM_SPLIT_INTAKE = (
    "Morning. I'm ringing about my ears — the left one's gone muffled again, and last time your nurse "
    "put it right with the syringing. Could I go on the list for that? No rush at all; it's been coming "
    "on a fortnight."
)

#: The split twin's phone-probe answers for him: sub-threshold — the chemist's gel in
#: passing without its name, never the warfarin link or the clinic's telling in the same breath.
BYERHOLM_SPLIT_FACTS = {
    "onset": (
        "The ear's been coming on muffled a fortnight. The mouth was sore under the denture last week, "
        "but that's being seen to."
    ),
    "severity": "Only the ear wanting syringing, and the mouth a nuisance. I'm right enough in myself.",
    "medications": (
        "Warfarin off the clinic's sheet, the waterworks tablet at night — and a gel from the chemist "
        "for the sore mouth. I couldn't tell you what's in it."
    ),
}

pt_belmead = _caller(
    "pt_belmead",
    "Edna Belmead",
    74,
    "F",
    chart=(
        "Osteoarthritis of both knees; simple analgesia as required.",
        "Open-angle glaucoma; drops at night, reviewed by the hospital eye service annually.",
        "Repeat medication: paracetamol 1 g as required, latanoprost eye drops at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. It's about my eye drops — the latanoprost. The chemist could only give me one bottle "
        "this time and says the repeat's run out of issues. Could somebody put that right this week? "
        "I've enough for a fortnight yet, so there's no drama."
    ),
    onset="Nothing new — the drops repeat has run out of issues, that's the whole of it.",
    severity="I'm quite well. The eyes are steady; it's paperwork.",
    history="The knees, which grumble, and the glaucoma drops at night for years.",
    medications="Paracetamol when the knees play up, and the latanoprost drops at night.",
    context=(
        "I'm at home most days. I do the shopping and the chemist's run for Mr Byerholm along my road."
    ),
    gold=_routine_gold(),
    source="authored:warfarin_inr_carrier_neighbour_eye_drops",
)

#: The split twin's carrier piece: her own errand, plus the gel's name in routine record-keeping
#: register (the name plainly, NEVER the warfarin context or a testing rule in the same call).
BELMEAD_SPLIT_INTAKE = (
    "Hello. It's about my eye drops — the latanoprost. The chemist could only give me one bottle this "
    "time and says the repeat's run out of issues. Could somebody put that right this week? I've enough "
    "for a fortnight yet, so there's no drama.\n\n"
    "Oh — and while I'm on, I do the shopping and the chemist's run for Mr Byerholm along my road — "
    "Harold Byerholm, he's one of yours. His mouth's been sore under the denture, and the chemist sold "
    "him a tube of miconazole gel for it yesterday; he first used it last night. He'd never think to "
    "mention it himself, so I said I'd let the surgery know, and now I have."
)

# ── contest 4: amiodarone from a private cardiology consult ──────────────────────────────────────────────
pt_ashgill = _caller(
    "pt_ashgill",
    "Vera Ashgill",
    80,
    "F",
    chart=(
        "Atrial fibrillation with a transient ischaemic attack three years ago; on warfarin, target INR "
        "2.0-3.0.",
        "Warfarin monitored at the practice's anticoagulation clinic; last INR nine days ago, in range.",
        "Anticoagulation clinic advice on file: an INR the same day any new interacting "
        "medicine is started.",
        "Seen privately for palpitations last month at the family's arrangement; specialist letter "
        "awaited.",
        "Repeat medication: warfarin per clinic dosing sheet, bisoprolol 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, dear. It's Mrs Ashgill. My family had me seen by a private heart specialist last month — "
        "the flutterings, you'll have his letter in due course — and his prescription finally came right "
        "yesterday: amiodarone, one to be taken at night. I took the first one last night.\n\n"
        "The warfarin clinic have always said — any new heart tablet, and that one they named to me "
        "specially — the INR gets checked the day it starts, no waiting for the routine test, because it "
        "drives the warfarin up and they like the dose set early. So I'm ringing first thing, as told. "
        "The tablet's first day is what matters, and that's today.\n\n"
        "I feel quite myself, I should say. There's nothing wrong with me this morning bar the paperwork."
    ),
    onset="Nothing new in me; the private specialist's tablet started last night, that's the whole story.",
    severity=(
        "I'm quite well — the flutterings are an old friend. It's the amiodarone with the warfarin the "
        "clinic said to test the day it starts."
    ),
    history=(
        "The irregular heart, the small stroke-that-wasn't three years back, and warfarin ever since, "
        "watched at your clinic. The private heart man was the family's doing."
    ),
    medications=(
        "Warfarin off the clinic's sheet, bisoprolol in the morning — and since last night the "
        "amiodarone the private specialist prescribed."
    ),
    context=(
        "My son Neil does my lifts on his early days and keeps the specialist's paperwork. I'm at home "
        "otherwise, and the surgery's ten minutes in his car."
    ),
    gold=board_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_claimant_amiodarone_private",
)

#: The split twin's piece 1: the SAME woman, ringing about a vaccination letter.
ASHGILL_SPLIT_INTAKE = (
    "Hello, dear. It's Mrs Ashgill. I've had the letter about the shingles vaccination and it says to "
    "ring the surgery to arrange it. There's no hurry that I know of — whenever there's a clinic with "
    "room. Mornings suit me best; my son does my lifts on his early days."
)

#: The split twin's phone-probe answers for her: sub-threshold — the new tablet in passing
#: without its name (her son keeps the paperwork), never the clinic's rule in the same breath.
ASHGILL_SPLIT_FACTS = {
    "onset": "Nothing new in me, dear — it's the vaccination letter I rang about.",
    "severity": "I'm quite well — the flutterings are an old friend, no worse than ever they were.",
    "medications": (
        "Warfarin off the clinic's sheet, bisoprolol in the morning — and the new tablet the private "
        "specialist started me on last night. My son keeps the paperwork with the name on it."
    ),
}

pt_ashgill_b = _caller(
    "pt_ashgill_b",
    "Neil Ashgill",
    52,
    "M",
    chart=(
        "Hypertension, controlled; annual review and bloods due this quarter.",
        "Repeat medication: losartan 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi, morning. I had a letter saying my blood-pressure review and the bloods are due — can I get "
        "that booked in? Early appointments if you can; I'm on shift from ten most days."
    ),
    onset="Nothing new — the review letter came and I'm doing as it says.",
    severity="I'm fine in myself. The tablets suit me; it's the yearly once-over.",
    history="Blood pressure these six years, same tablet throughout.",
    medications="Losartan, one a day.",
    context=(
        "I work shifts from ten. I run my mother, Vera Ashgill, to her appointments on my early days and "
        "keep her specialist paperwork in order."
    ),
    gold=_routine_gold(),
    source="authored:warfarin_inr_carrier_son_bp_review",
)

#: The split twin's carrier piece: his own review, plus the tablet name only he has to hand — in
#: routine record-keeping register (the name plainly, NEVER the warfarin context or the
#: clinic's rule in the same call; the rule half travels in his mother's ring-back, without the name).
ASHGILL_B_SPLIT_INTAKE = (
    "Hi, morning. I had a letter saying my blood-pressure review and the bloods are due — can I get "
    "that booked in? Early appointments if you can; I'm on shift from ten most days.\n\n"
    "One more thing while I'm on. My mother, Vera Ashgill — the private heart specialist we took her "
    "to for the flutterings has started her on amiodarone; she took the first one last night, and I've "
    "got his prescription sheet here in front of me. His letter will be an age reaching you, so I "
    "wanted the tablet's name on her record with the surgery in the meantime."
)

#: The split twin's piece 3: her OWN ring-back — the clinic's rule, stated as the fact of her care.
#: The panel ratified this piece as the rule-half pattern (rule + "new heart tablet", NO drug name —
#: the name travels only in her son's call; the split discipline splits that atom across the two calls).
ASHGILL_RECALL = (
    "It's Mrs Ashgill again — I know, twice before lunch. When I rang about the vaccination I had it in "
    "my head there was something else, and it's come back to me: the warfarin clinic's rule. I started a "
    "new heart tablet last night — the private specialist's one, my son keeps the paperwork with the "
    "name on it — and the clinic have always said the blood test gets done the day a new heart tablet "
    "starts. So today, by their rule, and I'd rather it wasn't lost in the shuffle."
)

# ── contest 5: co-trimoxazole from the out-of-hours doctor ───────────────────────────────────────────────
pt_belcote = _caller(
    "pt_belcote",
    "George Belcote",
    67,
    "M",
    chart=(
        "Recurrent deep-vein thrombosis; on long-term warfarin, target INR 2.0-3.0.",
        "Warfarin dosed at the practice's anticoagulation clinic; last INR one week ago, in range.",
        "Anticoagulation clinic advice on file: an INR the same day any new interacting "
        "medicine is started.",
        "Repeat medication: warfarin per clinic dosing sheet, ramipril 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I'll keep it short. I caught my shin on a cold frame at the allotment on Sunday, it "
        "went a bit angry round the edges, and the out-of-hours doctor last night gave me co-trimoxazole "
        "for it — first dose at bedtime.\n\n"
        "The warfarin clinic's standing orders, ever since they took me on: a new antibiotic gets "
        "reported to the surgery and the INR done the same day it starts. Last night was the start, so "
        "it falls today.\n\n"
        "The leg itself is honestly fine — dressed, comfortable, I walked the dog on it this morning. "
        "It's the tablets mixing with the warfarin that the clinic tests for, not the shin."
    ),
    onset="The shin caught on Sunday, cleaned and dressed; the antibiotic started at bedtime last night.",
    severity=(
        "The leg's comfortable under its dressing — I'm walking on it. The same-day part is the "
        "co-trimoxazole against the warfarin, per the clinic's standing orders."
    ),
    history="The leg clots, twice over the years, and warfarin since the second one, dosed at your clinic.",
    medications=(
        "Warfarin off the clinic's sheet, ramipril of a morning — and since bedtime last night the "
        "co-trimoxazole from the out-of-hours doctor."
    ),
    context=(
        "Retired, at the allotment most mornings — my wife Joan will always get a message to me. Any "
        "time today can be managed."
    ),
    gold=board_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_claimant_cotrimoxazole_ooh",
)

#: The split twin's piece 1: the SAME man, asking only after the treatment room.
BELCOTE_SPLIT_INTAKE = (
    "Morning. I caught my shin at the allotment on Sunday and it's got a dressing on it that the "
    "out-of-hours people said should be looked at in a day or two. Could I get in with the "
    "treatment-room nurse this week for a dressing change? No panic — it's comfortable enough."
)

#: The split twin's phone-probe answers for him: sub-threshold — the tablets in passing
#: without their name, never the clinic's standing orders in the same breath.
BELCOTE_SPLIT_FACTS = {
    "onset": "The shin got caught on a cold frame at the allotment on Sunday; it's dressed and settling.",
    "severity": (
        "The leg's comfortable under its dressing — I walked the dog on it this morning. Nothing else "
        "to report."
    ),
    "medications": (
        "Warfarin off the clinic's sheet, ramipril of a morning — and some tablets the out-of-hours "
        "doctor gave me for the shin. The name escapes me without the packet."
    ),
}

pt_belcote_b = _caller(
    "pt_belcote_b",
    "Joan Belcote",
    64,
    "F",
    chart=(
        "Hypertension, stable; annual review in the autumn.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could you put my blood-pressure tablets through for repeat? The chemist's showing "
        "nothing left on the authorisation and I'm down to my last strip. This week would do fine."
    ),
    onset="Nothing new — the repeat has run out, that's all.",
    severity="I'm well. It's the paperwork wanting doing before my strip runs out.",
    history="Blood pressure, steady for years on the one tablet.",
    medications="Amlodipine, one every morning.",
    context="At home most of the day. My husband George is up at the allotment; I field his messages.",
    gold=_routine_gold(),
    source="authored:warfarin_inr_carrier_wife_bp_repeat",
)

#: The split twin's carrier piece: her repeat, plus the tablets' name in routine record-keeping
#: register (the name plainly, NEVER the warfarin context or the clinic's rule in the same call).
BELCOTE_B_SPLIT_INTAKE = (
    "Hello. Could you put my blood-pressure tablets through for repeat? The chemist's showing nothing "
    "left on the authorisation and I'm down to my last strip. This week would do fine.\n\n"
    "And whilst I've got you — my husband George saw the out-of-hours doctor last night about the shin "
    "he caught at the allotment, and came home with co-trimoxazole, first dose at bedtime. He'll have "
    "rung you about his dressing and said nothing about the tablets — that's George all over — so I'm "
    "mentioning it for his record."
)

# ── contest 6: fluconazole from a private walk-in clinic ─────────────────────────────────────────────────
pt_byercote = _caller(
    "pt_byercote",
    "Pauline Byercote",
    63,
    "F",
    chart=(
        "Mechanical heart valve replacement five years ago; on lifelong warfarin, target INR 2.5-3.5.",
        "Warfarin monitored at the practice's anticoagulation clinic — finger-prick INR with the dose "
        "set at the visit; standing advice on file never to change the dose without a clinic reading. "
        "Last INR six days ago, in range.",
        "Anticoagulation clinic advice on file: an INR the same day any new interacting "
        "medicine is started.",
        "Repeat medication: warfarin per clinic dosing sheet, levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I need to own up to something, and then I think I need a test today.\n\n"
        "I'd had enough of the itching by yesterday evening, so I went along to one of those private "
        "walk-in clinics after work and they gave me fluconazole for thrush — a single capsule. I took "
        "it with my breakfast this morning. It was only afterwards I remembered the warfarin clinic's "
        "lecture: antifungal tablets are on their list, the swallowed ones especially, and their sheet "
        "says an INR the same day you take one.\n\n"
        "I took it this morning, so that's today, before you close. I feel perfectly fine in myself — "
        "it's the rule I'm ringing about, not a symptom."
    ),
    onset="The thrush since last week; the walk-in clinic's capsule taken with breakfast this morning.",
    severity=(
        "Nothing wrong with me beyond the itching, which is on its way out. The fluconazole against the "
        "warfarin is what the clinic's sheet says to test the same day."
    ),
    history="The mechanical valve five years ago, warfarin ever since, watched at your anticoagulation clinic.",
    medications=(
        "Warfarin off the clinic's sheet, levothyroxine of a morning — and the one fluconazole capsule "
        "from the private walk-in clinic, taken with breakfast today."
    ),
    context="I work in town but can step out at short notice today; the office knows.",
    gold=board_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_claimant_fluconazole_walkin",
)

#: The split twin's piece 1: the SAME woman, ringing about holiday vaccinations.
BYERCOTE_SPLIT_INTAKE = (
    "Hello. I'm ringing about travel jabs — we've a coach holiday booked for the spring, Croatia, and the "
    "paper from the tour people says to check with the surgery about vaccinations six weeks ahead. "
    "Could someone tell me what I need and when to come in? No rush today; I just want it in hand."
)

#: The split twin's piece 2: her OWN ring-back with the part she was too embarrassed to say — the
#: capsule's name in routine record-keeping register (no warfarin mention, no sheet's rule,
#: no urgency in the same call).
BYERCOTE_RECALL = (
    "Hello, it's Mrs Byercote — I rang earlier about the travel jabs. There's something I should have "
    "said and didn't, because I felt a fool: I went to one of those private walk-in clinics yesterday "
    "evening about thrush, and they gave me fluconazole — a single capsule, taken with my breakfast "
    "this morning. It wasn't your prescribing, so I'd like it noted on my record, and that's the whole "
    "of my confession."
)

#: The split twin's phone-probe answers for her: sub-threshold — the capsule in passing
#: without its name, never the clinic's sheet in the same breath.
BYERCOTE_SPLIT_FACTS = {
    "onset": "Nothing new — it's the travel jabs I rang about, for the coach holiday in the spring.",
    "severity": "I'm perfectly fine in myself. The itching's on its way out; nothing to report.",
    "medications": (
        "Warfarin off the clinic's sheet, levothyroxine of a morning — and a capsule the walk-in "
        "clinic gave me. I've not got the packet by me for the name."
    ),
}

# ── the six routine holders (nobody rings about them; these are their words if a desk rings THEM) ────────
pt_ashdon = _caller(
    "pt_ashdon",
    "Cyril Ashdon",
    78,
    "M",
    chart=(
        "Atrial fibrillation; on warfarin, stable; annual anticoagulation review due.",
        "Repeat medication: warfarin per clinic dosing sheet, amlodipine 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, that's me — I'm down at the warfarin clinic this afternoon, my yearly going-over. My "
        "nephew's taken the afternoon off his work to run me in, first time I've not had to ask twice. "
        "I'd as soon keep it exactly where it is."
    ),
    onset="Nothing new; it's the yearly review.",
    severity="I'm well. The numbers have behaved themselves all year, they tell me.",
    history="The irregular heart, on warfarin a long while, reviewed yearly at the clinic.",
    medications="Warfarin off the sheet, and the blood-pressure one.",
    context="My nephew's taken this afternoon off specially to drive me in.",
    gold=_holder_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_holder_annual_review_nephew_lift",
)

pt_beldon = _caller(
    "pt_beldon",
    "Winifred Beldon",
    82,
    "F",
    chart=(
        "Atrial fibrillation; on warfarin, stable; annual anticoagulation review with dosing-sheet "
        "renewal due.",
        "Repeat medication: warfarin per clinic dosing sheet, alendronic acid weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "That's right, my yearly warfarin review this afternoon. The community car scheme's booked — "
        "they only come out our way twice a week and it took some arranging. I'll be there for the time "
        "they gave me, and I'd be obliged if it stays put."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="I'm quite well, thank you. It's routine.",
    history="The heart flutter, on warfarin for donkey's years, seen yearly.",
    medications="Warfarin off the sheet, and the bone tablet on Sundays.",
    context="The community car scheme is booked for this afternoon; they only run our village twice a week.",
    gold=_holder_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_holder_annual_review_car_scheme",
)

pt_byerden = _caller(
    "pt_byerden",
    "Leonard Byerden",
    75,
    "M",
    chart=(
        "Atrial fibrillation; on warfarin, stable; annual anticoagulation review due.",
        "Repeat medication: warfarin per clinic dosing sheet, finasteride 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "This afternoon's my review at the clinic, yes. I mind my grandchildren after school most days — "
        "today my daughter's covered it specially so I could sit in a waiting room in peace. Moving it "
        "would put the whole house out."
    ),
    onset="Nothing new; it's the yearly check.",
    severity="Fit as I need to be. The appointment's routine.",
    history="The irregular pulse, warfarin for years, reviewed annually.",
    medications="Warfarin off the sheet, and the prostate tablet.",
    context="My daughter has covered the school run today so I can attend; most days I can't.",
    gold=_holder_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_holder_annual_review_school_run",
)

pt_ashcote = _caller(
    "pt_ashcote",
    "Doris Ashcote",
    71,
    "F",
    chart=(
        "Atrial fibrillation; on warfarin, stable; annual anticoagulation review due — twice rescheduled "
        "by the practice this winter.",
        "Repeat medication: warfarin per clinic dosing sheet, latanoprost eye drops at night.",
        "No known drug allergies.",
    ),
    intake=(
        "The warfarin review — it's been moved twice already this winter, and neither time by me. My "
        "daughter's swapped her shift at the depot to take me today. I want this one kept, please, as "
        "it was given."
    ),
    onset="Nothing new; it's the twice-moved yearly review.",
    severity="I'm well in myself. It's the principle of the thing by now.",
    history="The flutter, warfarin for years, reviewed yearly when the diary allows.",
    medications="Warfarin off the sheet, and my eye drops at night.",
    context="My daughter has swapped her depot shift to drive me this afternoon.",
    gold=_holder_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_holder_annual_review_twice_moved",
)

pt_belfold = _caller(
    "pt_belfold",
    "Percy Belfold",
    84,
    "M",
    chart=(
        "Atrial fibrillation; on warfarin, stable; annual anticoagulation review due.",
        "Osteoarthritis of the hip; walks with a stick.",
        "Repeat medication: warfarin per clinic dosing sheet, co-codamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "That's right, my yearly warfarin check this afternoon. The warden's minibus from the flats "
        "runs into town today and not again till next week — I'm no good on the buses with my hip. "
        "Today's the day that works, and I'd like to hold onto it."
    ),
    onset="Nothing new; the yearly check.",
    severity="Steady as I go. The hip grumbles but that's old news.",
    history="The heart, on warfarin a long time; the hip that keeps me off the buses.",
    medications="Warfarin off the sheet, and the painkillers when the hip asks.",
    context="The warden's minibus from the sheltered flats runs into town today and not again till next week.",
    gold=_holder_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_holder_annual_review_minibus",
)

pt_byergill = _caller(
    "pt_byergill",
    "Muriel Byergill",
    69,
    "F",
    chart=(
        "Atrial fibrillation; on warfarin, stable; annual anticoagulation review due.",
        "Repeat medication: warfarin per clinic dosing sheet, levothyroxine 50 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My review's this afternoon, yes — I've taken the day off the charity shop for it and told the "
        "manageress weeks back. I'd rather not go through all that again for a different day, if it's "
        "all the same."
    ),
    onset="Nothing new; the yearly review.",
    severity="Perfectly well, thank you. It's the routine once-a-year.",
    history="The flutter, warfarin for years, and the thyroid, all steady.",
    medications="Warfarin off the sheet, and the thyroid tablet first thing.",
    context="I volunteer at the charity shop; today's leave was arranged with the manageress weeks ago.",
    gold=_holder_gold(ANTICOAGULATION),
    source="authored:warfarin_inr_holder_annual_review_charity_shop",
)

# ── the two decoys ────────────────────────────────────────────────────────────────────────────────────────
pt_byerfold = _caller(
    "pt_byerfold",
    "Nora Byerfold",
    72,
    "F",
    chart=(
        "Atrial fibrillation. Warfarin until eighteen months ago; switched to apixaban at the "
        "anticoagulation review.",
        "No routine INR monitoring since the switch, per the clinic's discharge note.",
        "Repeat medication: apixaban 5 mg twice daily, bendroflumethiazide 2.5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello — I hope I'm not about to waste your morning, but I'd rather ask than sit on it. The "
        "dentist's given me amoxicillin today for a gum infection, and it rang a bell: when I was on "
        "warfarin, years back now, an antibiotic meant a blood test the same day, no argument.\n\n"
        "But they changed me onto apixaban — eighteen months ago — and the clinic said that was the end "
        "of the testing; the new tablet doesn't need it. Only I'd feel better hearing it from the "
        "surgery: nothing needs doing today, does it? If I should just book an ordinary appointment "
        "about the gum, I'll take whatever's going."
    ),
    onset="The gum flared over the weekend; the dentist's antibiotic started this morning.",
    severity="The gum's tender and that's the size of it. I'm ringing to be told I can stand down.",
    history=(
        "The irregular heart. Warfarin for years, then the switch to apixaban eighteen months ago, and "
        "no blood tests since — the clinic said none were needed."
    ),
    medications="The apixaban twice a day, the water tablet in the morning, and now the dentist's amoxicillin.",
    context="At home today; the dentist's given me the course and I'm otherwise going about my business.",
    gold=_routine_gold(),
    source="authored:warfarin_inr_decoy_apixaban_no_monitoring",
)

pt_belridge = _caller(
    "pt_belridge",
    "Iris Belridge",
    61,
    "F",
    chart=(
        "Hypertension on ramipril and amlodipine; raised cholesterol on atorvastatin; chronic bronchitis "
        "with winter flare-ups.",
        "Repeat medication: ramipril 5 mg daily, amlodipine 5 mg daily, atorvastatin 40 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor saw me last night for my chest — the usual winter business — and "
        "started me on clarithromycin. He was very particular about one thing: my cholesterol tablet, "
        "the atorvastatin, has to stop while I'm on the antibiotic, the two don't mix, and it starts "
        "again when the course is finished. He said nothing else needed doing and no need to be seen "
        "today — just that my own surgery should have it on the record, so that's why I'm ringing. If a "
        "routine appointment's wanted about the chest at some point, you can book me one."
    ),
    onset="The chest since midweek; the out-of-hours doctor's antibiotic started last night.",
    severity=(
        "The chest is its winter self, no worse. The doctor last night said no need to be seen today — "
        "it's the record he wanted straight."
    ),
    history="The blood pressure, the cholesterol, and the chest that flares most winters.",
    medications=(
        "Ramipril and amlodipine in the morning; the atorvastatin at night, though that's stopped while "
        "the clarithromycin course runs, on the out-of-hours doctor's say-so."
    ),
    context="My husband Ronald's at home with me and keeps the paperwork; we're ten minutes from you.",
    gold=_routine_gold(),
    source="authored:warfarin_inr_decoy_statin_pause_clarithromycin",
)

#: The split twin's decoy intake: the SAME instruction with the tablet's NAME missing — the urgency her
#: husband's call cancels.
BELRIDGE_SPLIT_INTAKE = (
    "Hello. The out-of-hours doctor saw me last night for my chest — the usual winter business — and "
    "started me on clarithromycin. He was very particular that one of my regular tablets has to stop "
    "while I'm on it — the two don't mix, he said — and I've been racking my brains all morning because "
    "I couldn't put my hand on the box while he had me on the phone, and I can't now. My husband's got "
    "the sheet the doctor left. I don't want to take the wrong thing tonight, so somebody had better "
    "tell me what I'm to do, hadn't they?"
)

pt_belridge_b = _caller(
    "pt_belridge_b",
    "Ronald Belridge",
    63,
    "M",
    chart=(
        "Type 2 diabetes, diet-controlled; annual review due.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I've had the letter for my diabetes check — the yearly one — and I'm told to book the "
        "review and the bloods. Whenever suits the nurse; I'm retired, mornings preferred."
    ),
    onset="Nothing new — the yearly letter came, so I'm booking as told.",
    severity="I'm well. It's the annual once-over, diet-controlled and steady.",
    history="The diabetes, managed on diet alone these five years.",
    medications="None on repeat; the review letter says bring a urine sample.",
    context="Retired, at home with my wife Iris; mornings suit best.",
    gold=_routine_gold(),
    source="authored:warfarin_inr_carrier_husband_diabetes_review",
)

#: The split twin's defusing piece: his own booking, plus the sheet his wife couldn't lay hands on.
BELRIDGE_B_SPLIT_INTAKE = (
    "Morning. I've had the letter for my diabetes check — the yearly one — and I'm told to book the "
    "review and the bloods. Whenever suits the nurse; I'm retired, mornings preferred.\n\n"
    "Also — my wife Iris rang you earlier, I gather, in a state about which tablet she's meant to stop. "
    "I've got the out-of-hours doctor's sheet here in front of me: it's the atorvastatin, the "
    "cholesterol one, stopped while the clarithromycin's on and started again after. That's all it was. "
    "She takes her chest antibiotic and the rest carries on as normal."
)

#: Every card this board authors (claimants, carriers, holders, decoys). Twins share these OBJECTS.
CARDS = (
    pt_ashfold,
    pt_ashfold_b,
    pt_belgarth,
    pt_byerholm,
    pt_belmead,
    pt_ashgill,
    pt_ashgill_b,
    pt_belcote,
    pt_belcote_b,
    pt_byercote,
    pt_ashdon,
    pt_beldon,
    pt_byerden,
    pt_ashcote,
    pt_belfold,
    pt_byergill,
    pt_byerfold,
    pt_belridge,
    pt_belridge_b,
)

#: The sanctioned same-surname declarations: one family carrier per shared surname, all within this board.
KIN_OF = {
    "pt_ashfold_b": "pt_ashfold",
    "pt_ashgill_b": "pt_ashgill",
    "pt_belcote_b": "pt_belcote",
    "pt_belridge_b": "pt_belridge",
}

# ── the board skeleton (shared by both twins byte-for-byte) ──────────────────────────────────────────────
CONTESTS = (
    BoardContest(
        claimant="pt_ashfold",
        holder="pt_ashdon",
        specialty=ANTICOAGULATION,
        provider_id="dr_ashgarth",
        slot_hhmm="13:00",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual anticoagulation review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="metronidazole",
    ),
    BoardContest(
        claimant="pt_belgarth",
        holder="pt_beldon",
        specialty=ANTICOAGULATION,
        provider_id="dr_belholm",
        slot_hhmm="13:20",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual anticoagulation review + dosing-sheet renewal (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="erythromycin",
    ),
    BoardContest(
        claimant="pt_byerholm",
        holder="pt_byerden",
        specialty=ANTICOAGULATION,
        provider_id="dr_byerlund",
        slot_hhmm="13:40",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual anticoagulation review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="miconazole",
    ),
    BoardContest(
        claimant="pt_ashgill",
        holder="pt_ashcote",
        specialty=ANTICOAGULATION,
        provider_id="dr_ashmead",
        slot_hhmm="14:40",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual anticoagulation review, twice rescheduled (wait-list backfill into a returned "
            "cancellation)"
        ),
        decisive_fact="amiodarone",
    ),
    BoardContest(
        claimant="pt_belcote",
        holder="pt_belfold",
        specialty=ANTICOAGULATION,
        provider_id="dr_bellund",
        slot_hhmm="15:00",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual anticoagulation review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="co-trimoxazole",
    ),
    BoardContest(
        claimant="pt_byercote",
        holder="pt_byergill",
        specialty=ANTICOAGULATION,
        provider_id="dr_byerridge",
        slot_hhmm="15:20",
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=(
            "Annual anticoagulation review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="fluconazole",
    ),
)

#: Decoy ids are identical across the twins; the split twin routes pt_belridge's defusal through her
#: husband's call (aggregation must be able to CANCEL urgency).
DECOYS_PLAIN = (Decoy("pt_byerfold"), Decoy("pt_belridge"))
DECOYS_SPLIT = (
    Decoy("pt_byerfold"),
    Decoy("pt_belridge", defusing_caller_id="pt_belridge_b"),
)

#: Arrival plan, identical across the twins (the split adds three RECALL beats, which is call structure).
#: The corpus background quartet rides along; its voicemail trio carries the forced waits (§15(5)).
ARRIVALS = (
    ("pt_ashfold", "A", 0),
    ("pt_belgarth", "B", 8),
    ("pt_lachaux", "B", 16),
    ("pt_byerholm", "C", 22),
    ("pt_byerfold", "D", 30),
    ("pt_ashgill", "D", 38),
    ("pt_dunmore", "C", 46),
    ("pt_belcote", "A", 54),
    ("pt_belmead", "A", 60),
    ("pt_byercote", "B", 68),
    ("pt_ashfold_b", "C", 76),
    ("pt_ledwidge", "A", 84),
    ("pt_belridge", "D", 92),
    ("pt_ashgill_b", "B", 100),
    ("pt_belcote_b", "D", 108),
    ("pt_arundel", "D", 116),
    ("pt_belridge_b", "C", 124),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: One sentence of size cover: why one diary is running six clinics today. A fact about the
#: morning; it names no caller, no provider, and no action.
MEMO_COVER_LINE = (
    "The anticoagulation service has also taken on a neighbouring practice's warfarin list this month "
    "while that surgery's premises are refitted, so its diary is running more clinics than usual."
)

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=6,
    theme_slug="warfarin_inr",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=(
        EvidenceCall(caller_id="pt_ashfold", about_claimant="pt_ashfold"),
        EvidenceCall(caller_id="pt_belgarth", about_claimant="pt_belgarth"),
        EvidenceCall(caller_id="pt_byerholm", about_claimant="pt_byerholm"),
        EvidenceCall(caller_id="pt_ashgill", about_claimant="pt_ashgill"),
        EvidenceCall(caller_id="pt_belcote", about_claimant="pt_belcote"),
        EvidenceCall(caller_id="pt_byercote", about_claimant="pt_byercote"),
    ),
    decoys=DECOYS_PLAIN,
    cards=CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=6,
    theme_slug="warfarin_inr",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=(
        # C1: routine intake (A) + the daughter's errand carries the dentist's script (C).
        EvidenceCall(caller_id="pt_ashfold", about_claimant="pt_ashfold"),
        EvidenceCall(caller_id="pt_ashfold_b", about_claimant="pt_ashfold"),
        # C2: routine intake (B) + her own ring-back with the clinic-card rule (D).
        EvidenceCall(caller_id="pt_belgarth", about_claimant="pt_belgarth"),
        EvidenceCall(
            caller_id="pt_belgarth",
            about_claimant="pt_belgarth",
            kind="recall",
            at_min=98,
            desk="D",
            text=BELGARTH_RECALL,
        ),
        # C3: routine intake (C) + the neighbour's errand carries the chemist's warning (A).
        EvidenceCall(caller_id="pt_byerholm", about_claimant="pt_byerholm"),
        EvidenceCall(caller_id="pt_belmead", about_claimant="pt_byerholm"),
        # C4: three pieces on three desks — intake (D), the son's call with the drug name (B), her
        # ring-back with the clinic's same-day rule (A).
        EvidenceCall(caller_id="pt_ashgill", about_claimant="pt_ashgill"),
        EvidenceCall(caller_id="pt_ashgill_b", about_claimant="pt_ashgill"),
        EvidenceCall(
            caller_id="pt_ashgill",
            about_claimant="pt_ashgill",
            kind="recall",
            at_min=126,
            desk="A",
            text=ASHGILL_RECALL,
        ),
        # C5: routine intake (A) + his wife says the half he left out (D).
        EvidenceCall(caller_id="pt_belcote", about_claimant="pt_belcote"),
        EvidenceCall(caller_id="pt_belcote_b", about_claimant="pt_belcote"),
        # C6: routine intake (B) + her own ring-back owning up to the capsule (C).
        EvidenceCall(caller_id="pt_byercote", about_claimant="pt_byercote"),
        EvidenceCall(
            caller_id="pt_byercote",
            about_claimant="pt_byercote",
            kind="recall",
            at_min=110,
            desk="C",
            text=BYERCOTE_RECALL,
        ),
    ),
    decoys=DECOYS_SPLIT,
    cards=CARDS,
    intake_overrides={
        "pt_ashfold": ASHFOLD_SPLIT_INTAKE,
        "pt_ashfold_b": ASHFOLD_B_SPLIT_INTAKE,
        "pt_belgarth": BELGARTH_SPLIT_INTAKE,
        "pt_byerholm": BYERHOLM_SPLIT_INTAKE,
        "pt_belmead": BELMEAD_SPLIT_INTAKE,
        "pt_ashgill": ASHGILL_SPLIT_INTAKE,
        "pt_ashgill_b": ASHGILL_B_SPLIT_INTAKE,
        "pt_belcote": BELCOTE_SPLIT_INTAKE,
        "pt_belcote_b": BELCOTE_B_SPLIT_INTAKE,
        "pt_byercote": BYERCOTE_SPLIT_INTAKE,
        "pt_belridge": BELRIDGE_SPLIT_INTAKE,
        "pt_belridge_b": BELRIDGE_B_SPLIT_INTAKE,
    },
    facts_overrides={
        # Ruling 3: the canonical fact answers are the PLAIN twin's and restate each claimant's
        # assembled case; in the split twin a probed patient volunteers only their own sub-threshold
        # fragment — the new medicine in passing without its decisive name, never the clinic's rule.
        "pt_ashfold": ASHFOLD_SPLIT_FACTS,
        "pt_belgarth": BELGARTH_SPLIT_FACTS,
        "pt_byerholm": BYERHOLM_SPLIT_FACTS,
        "pt_ashgill": ASHGILL_SPLIT_FACTS,
        "pt_belcote": BELCOTE_SPLIT_FACTS,
        "pt_byercote": BYERCOTE_SPLIT_FACTS,
    },
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

# Registration at import, PLAIN FIRST (the split twin seeds its calendar from the plain twin's id).
register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
