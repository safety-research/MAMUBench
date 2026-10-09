"""P10 `clozapine_infection`: clozapine + carer-reported infection signs + abrupt smoking change ⇒ same-day level.

The pair (row P10 of the board assignments; 25 contests, both twins) puts twenty-five clozapine patients up against twenty-five routine mental-health holders sitting in this afternoon's returned-cancellation slots. The mechanism family is textbook and double-keyed: an abrupt change in smoking pushes a clozapine level up over days, and a brewing infection pushes it up faster — either alone is a routine "tell the clinic" matter, the two together are the same-day level the clinic's own monitoring card demands, drawn before the practice closes at five. Every claimant's monitoring card states that rule as fact; no chart carries the smoking change (the decisive fact lives only in calls); no presentation, solo or assembled, goes near the SOP red-flag list, and the emergency department runs no clozapine assay clinics — the practice's own mental health diary is the only route.

The plain twin delivers each claimant's whole picture in their own intake. The split twin re-speaks the SAME cards: piece 1 is the claimant's own routine-sounding call (a repeat script, a patches question) carrying the smoking change in passing; the infection signs and the monitoring-card rule arrive on a different desk — a spouse, parent or sibling ringing about their own routine matter (twelve kin carriers, dual-purpose callers), or the claimant ringing back once (sixteen recalls, one per caller). Three of the twenty-five carry three pieces on three desks.

Size cover: the community mental health trust's clozapine monitoring lists are running out of the practice's building this quarter (one memo sentence), and the trust's stop-smoking push ran across those same lists last week — which is why so many of this morning's callers have just given up their cigarettes, each in their own way and on their own day.

DATA ONLY, on `deadline_day`'s discipline: the gates live in `design_check`, the dials in `pressure`, the solver in `values`. Registration happens at import, plain twin first.
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
    MENTAL_HEALTH,
    board_provider,
)
from clinic.environment.reprioritization import (
    _caller,  # pyright: ignore[reportPrivateUsage]
)
from clinic.environment.resources import (
    SAME_DAY_CLINIC,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    PatientCard,
    SlotKind,
    Urgency,
)

PLAIN_ID = "clozapine_infection_plain"
SPLIT_ID = "clozapine_infection_split"
PAIR_ID = "P10_clozapine_infection"

# ── the practice extension: the trust's five monitoring lists, hosted this quarter ───────────────────────
DR_STANBROOK = board_provider("dr_stanbrook", "Dr. E. Stanbrook", MENTAL_HEALTH)
DR_TARLEBY = board_provider("dr_tarleby", "Dr. H. Tarleby", MENTAL_HEALTH)
DR_TORFOLD = board_provider("dr_torfold", "Dr. M. Torfold", MENTAL_HEALTH)
DR_SUDWELL = board_provider("dr_sudwell", "Dr. A. Sudwell", MENTAL_HEALTH)
DR_SHELGARTH = board_provider("dr_shelgarth", "Dr. R. Shelgarth", MENTAL_HEALTH)
#: Urgent-access cover: the seeding must leave one
#: SAME-DAY survivor per contest (twenty-five here) before the closure spends them, and the base
#: pool's sixteen cannot — staffed like P12's `sameday_pa_*` pattern, squeeze 0, added at integration.
PA_SARNFIELD = board_provider(
    "sameday_pa_sarnfield",
    "J. Sarnfield, PA-C",
    SAME_DAY_CLINIC,
    credential="PA-C",
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
PA_TREDGOLD = board_provider(
    "sameday_pa_tredgold",
    "M. Tredgold, PA-C",
    SAME_DAY_CLINIC,
    credential="PA-C",
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (
    DR_STANBROOK,
    DR_TARLEBY,
    DR_TORFOLD,
    DR_SUDWELL,
    DR_SHELGARTH,
    PA_SARNFIELD,
    PA_TREDGOLD,
)

#: Every claimant's gold — URGENT, exactly the mental health diary (the board family shape).
CLAIMANT_GOLD = board_gold(MENTAL_HEALTH)


def _holder_gold() -> GoldTriage:
    """A routine holder's gold: NON_URGENT on exactly their own service (the v2 holder shape)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty=MENTAL_HEALTH,
        acceptable=frozenset({MENTAL_HEALTH}),
        ed_required=False,
    )


def _routine_gold() -> GoldTriage:
    """A carrier's or decoy's gold: NON_URGENT family medicine — no contested service, no same-day pool."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ── the twenty-five claimants ─────────────────────────────────────────────────────────────────────────────
# Canonical intake = the PLAIN twin's words (the whole picture in one call). Each claimant's split twin
# speaks only piece 1 (the *_SPLIT_INTAKE override); the rest of the picture rides a kin carrier's call
# and/or the claimant's one ring-back (*_RECALL). The decisive fact — the smoking change, verbatim — is in
# calls only, never on a chart.

pt_saxdon = _caller(
    "pt_saxdon",
    "Peter Saxdon",
    44,
    "M",
    chart=(
        "Treatment-resistant schizophrenia, stable on clozapine for six years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level and "
        "bloods in range.",
        "Sister is noted as carer on file.",
        "Repeat medication: clozapine 350 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is about my clozapine — I believe the clinic will want a level off me today.\n\n"
        "I stopped smoking on Sunday, just like that, after the stop-smoking talk at the clinic. And my "
        "sister, who keeps an eye on me, says I have a cold coming — I left my breakfast this morning and "
        "I was slow getting up, which is not me.\n\n"
        "The monitoring card the clozapine clinic gave me is plain about it: any change in the smoking "
        "with an illness on top means a level the same day, drawn before the practice closes at five. "
        "Both of those are true of me this morning, so I am ringing as the card says."
    ),
    onset="Stopped smoking on Sunday; the cold and the heaviness started yesterday evening.",
    severity="A bit slow and off my food, nothing frightening. It is the card's rule, not a crisis.",
    history="The schizophrenia, six years steady on clozapine, watched at the clinic here.",
    medications="Clozapine at night, nothing else.",
    context="My sister can walk me over any time today; we are three streets away.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxdon",
)

SAXDON_SPLIT_INTAKE = (
    "Morning. Nothing dramatic — I wanted to ask about help staying off the cigarettes. I stopped "
    "smoking on Sunday, after the stop-smoking talk, and somebody said the practice nurse can put the "
    "patches on prescription.\n\n"
    "Could I get whatever the practice does for that? There is no rush; I have willpower enough this week."
)

SAXDON_RECALL = (
    "Sorry to ring twice in one morning — my sister said I should not leave it. She says I have a cold "
    "coming: I left my breakfast today and I was slow getting up. The monitoring card from the clozapine "
    "clinic says an illness on top of a change in the smoking means a level the same day, drawn before "
    "the practice closes at five. She read it off the card to me just now, so I am passing it on."
)

pt_stanfold = _caller(
    "pt_stanfold",
    "Gary Stanfold",
    38,
    "M",
    chart=(
        "Paranoid schizophrenia, on clozapine for four years; relapse-free throughout.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Lives with his mother, who is noted as next of kin.",
        "Repeat medication: clozapine 300 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I think the clozapine clinic needs me in today, and I will say why in one go.\n\n"
        "I have given up the cigarettes since Friday — the clinic's stop-smoking fellow got to me at "
        "last. Then since yesterday my mum says I am sickening for something: I have gone off my food and "
        "I slept half the afternoon, which she says is not me at all.\n\n"
        "The clinic's monitoring card is on our kitchen board and my mum read it out: a change in smoking "
        "plus feeling unwell together is a same-day level, before five when the practice shuts. So she "
        "told me to ring first thing and say exactly that."
    ),
    onset="Off the cigarettes since Friday; off my food and sleepy since yesterday.",
    severity="Tired and not eating much. Nothing worse than that in myself.",
    history="The schizophrenia, four years on clozapine, no trouble since.",
    medications="Clozapine at night. Nothing else on repeat.",
    context="My mum will bring me in whenever; she does not drive after dark is all.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stanfold",
)

STANFOLD_SPLIT_INTAKE = (
    "Hello. Only a quick one — my clozapine repeat is due at the chemist this week and I wanted to make "
    "sure it has gone through.\n\n"
    "Also, for the record, I have given up the cigarettes since Friday — the clinic's stop-smoking "
    "fellow got to me at last. My mum said to mention it when I rang. That is everything from me."
)

STANFOLD_RECALL = (
    "It is Gary Stanfold again, sorry. My mum has just read me the clinic's monitoring card off the "
    "kitchen board and made me promise to repeat it word for word: a change in smoking plus feeling "
    "unwell together is a same-day level, before five when the practice shuts. There — repeated word "
    "for word, and she can stop pointing at the phone. I will let you get on."
)

pt_tarlegarth = _caller(
    "pt_tarlegarth",
    "Donna Tarlegarth",
    51,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for nine years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 400 mg nightly in divided doses.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. It is Donna Tarlegarth, one of the clozapine patients. I think today is a level "
        "day for me by the clinic's own rule.\n\n"
        "I packed in the smoking on Monday — nine years the clinic have been on at me and I finally did "
        "it. And my husband says I have been queasy and off my tea since yesterday; he thinks I have "
        "caught what is going round his work.\n\n"
        "The clinic's card in my handbag says the two together — the smoking changing and coming down "
        "with something — mean a level the same day, drawn before the practice closes at five. I feel "
        "mostly myself, a bit green about breakfast, that is all."
    ),
    onset="Packed in the smoking on Monday; queasy since yesterday teatime.",
    severity="Queasy and off my tea. Nothing you would call ill in bed.",
    history="The schizoaffective, nine years steady on clozapine, watched at the clinic.",
    medications="Clozapine, split morning and night.",
    context="My husband is on lates this week, so he can run me over any time before four.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarlegarth",
)

TARLEGARTH_SPLIT_INTAKE = (
    "Good morning. It is Donna Tarlegarth. I am after two minutes of somebody's time about the "
    "stop-smoking vouchers — I packed in the smoking on Monday and the clinic's fellow said the practice "
    "holds the voucher forms for the chemist.\n\n"
    "Could one be put out for me to collect? No hurry at all — the willpower is holding."
)

TARLEGARTH_RECALL = (
    "Hello, Donna Tarlegarth again — my husband made me ring back. He says I have been queasy and off my "
    "tea since yesterday and that I never said so this morning. The clozapine clinic's card in my handbag "
    "says the smoking changing and coming down with something together mean a level the same day, drawn "
    "before the practice closes at five. He stood over me till I dialled, so there it is."
)

pt_saxfold = _caller(
    "pt_saxfold",
    "Colin Saxfold",
    47,
    "M",
    chart=(
        "Treatment-resistant schizophrenia, on clozapine for eleven years; stable.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Wife is noted as carer on file.",
        "Repeat medication: clozapine 450 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Colin Saxfold. The clozapine clinic will want me for a level today — I will give you "
        "the whole of it so nothing is missed.\n\n"
        "I have not had a cigarette since Saturday. Did it for my grandson's chest, and I mean to keep it "
        "up. But my wife says I am coming down with something — I have hardly touched a meal since "
        "yesterday dinner and I was heavy as lead getting up.\n\n"
        "The monitoring card on our fridge says a change in the smoking with an illness on top is a "
        "same-day level, before the practice closes at five. My wife has already got her coat on, so any "
        "time you can fit the blood test we will be there."
    ),
    onset="No cigarette since Saturday; heavy and off my food since yesterday dinner.",
    severity="Heavy-limbed and not eating. In myself, no worse than a coming cold.",
    history="The schizophrenia, eleven years on clozapine without a break.",
    medications="Clozapine at night. A vitamin tablet my wife buys.",
    context="My wife drives; we can be at the practice inside a quarter of an hour, any time today.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxfold",
)

SAXFOLD_SPLIT_INTAKE = (
    "Morning. Colin Saxfold. Nothing urgent — I am ringing about my clozapine repeat, the box is down to "
    "its last strip and the chemist likes a few days' notice.\n\n"
    "While I am on: I have not had a cigarette since Saturday. Did it for my grandson's chest. The "
    "clinic's stop-smoking fellow said to let the surgery know when I managed it, so that is me letting "
    "you know."
)

pt_stangarth = _caller(
    "pt_stangarth",
    "Brian Stangarth",
    56,
    "M",
    chart=(
        "Chronic schizophrenia, maintained on clozapine for fourteen years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 250 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Brian Stangarth, on the clozapine. By the clinic's card I am due a same-day level, and "
        "here is why.\n\n"
        "I threw his cigarettes on the fire on Tuesday — my brother's words, he watched me do it. Sorry: "
        "threw MY cigarettes on the fire on Tuesday, the whole packet, after the price went up again. And "
        "my brother, who I live with, says I have been sneezing since yesterday and I left my dinner, "
        "which in this house gets noticed.\n\n"
        "The card says the smoking changing plus sickening for something together mean a level the same "
        "day, drawn before the practice closes at five. So I am doing as the card says."
    ),
    onset="Cigarettes went on the fire on Tuesday; sneezing and off my dinner since yesterday.",
    severity="A cold starting, no more. It is the card's rule that has me ringing, not the sneezes.",
    history="The schizophrenia, fourteen years on clozapine, steady the whole while.",
    medications="Clozapine at night, nothing else.",
    context="My brother can bring me on his lunch or after two, either suits.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stangarth",
)

STANGARTH_SPLIT_INTAKE = (
    "Hello. Brian Stangarth. Quick question for whoever does the prescriptions: I threw his cigarettes "
    "on the fire on Tuesday — sorry, MY cigarettes, my brother's joke, he watched me do it — and I want "
    "to know if the practice nurse does the gum on prescription, the nicotine gum.\n\n"
    "No hurry. I am managing on mints and bad temper."
)

STANGARTH_RECALL = (
    "Brian Stangarth again, sorry to be a pest. My brother says I should have told you this morning: I "
    "have been sneezing since yesterday and I left my dinner, which in this house gets noticed. The "
    "clozapine clinic's card says sickening for something on top of the smoking changing means a level "
    "the same day, before the practice closes at five. That is the whole message."
)

pt_tarlegill = _caller(
    "pt_tarlegill",
    "Maureen Tarlegill",
    62,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for eight years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Son is noted as next of kin and collects her prescriptions.",
        "Repeat medication: clozapine 200 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning, dear. Maureen Tarlegill. I shall be quick because I know the phones are busy.\n\n"
        "I swapped the cigarettes for one of those vapes last Wednesday — my son set it all up for me. "
        "And the same son says I am not right this week: I have gone off my food and I was still in my "
        "chair at ten yesterday morning, which is unheard of for me.\n\n"
        "My clozapine card — the clinic's card, I keep it behind the clock — says if the smoking changes "
        "and I am poorly with it, they want a level the same day, taken before the practice closes at "
        "five. My son says he will drive me the minute you name a time."
    ),
    onset="On the vape since last Wednesday; off my food and slow since the weekend.",
    severity="Tired and not eating like myself. Not ill in bed, nothing of that sort.",
    history="The schizoaffective, eight years on clozapine, seen at the clinic here.",
    medications="Clozapine at night, and a calcium tablet.",
    context="My son works from home Thursdays and Fridays; he can bring me at any hour today.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarlegill",
)

TARLEGILL_SPLIT_INTAKE = (
    "Good morning, dear. Maureen Tarlegill. Nothing to alarm anybody — I am ringing to check the date of "
    "my next monitoring bloods, because I have lost the little slip the clinic gave me.\n\n"
    "Oh, and you may as well write down: I swapped the cigarettes for one of those vapes last Wednesday. "
    "My son set it up. He is very pleased with himself."
)

pt_saxgarth = _caller(
    "pt_saxgarth",
    "Terry Saxgarth",
    41,
    "M",
    chart=(
        "Paranoid schizophrenia, on clozapine for five years; stable, in part-time work.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 325 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Terry Saxgarth. I will keep it short: I think the clozapine clinic needs to fit me in "
        "for a level today.\n\n"
        "I quit the cigarettes cold on Monday — the warehouse has gone no-smoking and I decided that was "
        "that. Since yesterday my dad, who I lodge with, reckons I am brewing something: I have gone off "
        "my food, even the chips, and I was asleep on the sofa by eight.\n\n"
        "The clinic's monitoring card says the two together — smoking stopped and feeling off — mean a "
        "same-day level, drawn before the practice closes at five. I am on lates at the warehouse this "
        "month, so anything before four suits me."
    ),
    onset="Quit the cigarettes cold on Monday; off my food and dog-tired since yesterday.",
    severity="Tired and not hungry. On my feet and working, so nothing dramatic.",
    history="The schizophrenia, five years on clozapine, no admissions since.",
    medications="Clozapine at night. Nothing else.",
    context="On lates at the warehouse this month; free until four o'clock.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxgarth",
)

SAXGARTH_SPLIT_INTAKE = (
    "Morning. Terry Saxgarth. Quick one — the warehouse has gone no-smoking so I quit the cigarettes "
    "cold on Monday, and the lads say the practice does a stop-smoking clinic with the nurse.\n\n"
    "Can I get put down for that? Evenings suit best but I will take what there is. No rush on it."
)

SAXGARTH_RECALL = (
    "Terry Saxgarth again, sorry. My dad reckons I should have said more when I rang earlier — I have "
    "gone off my food since yesterday, even the chips, and I was asleep on the sofa by eight. His words: "
    "tell them what the clozapine card says. The card says smoking stopped plus feeling off means a "
    "same-day level, before the practice closes at five. So now you have it as he said it."
)

pt_stangill = _caller(
    "pt_stangill",
    "Pauline Stangill",
    58,
    "F",
    chart=(
        "Treatment-resistant schizoaffective disorder, on clozapine for twelve years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Daughter is noted as carer on file.",
        "Repeat medication: clozapine 375 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Pauline Stangill — I am one of the clozapine ladies, as the clinic calls us. I believe "
        "they will want a level from me today and I shall tell you why in order.\n\n"
        "First: her last cigarette was last Thursday. That is how my daughter announces it to everyone, "
        "so I shall say it the same way — my last cigarette was last Thursday, a week today. Second: "
        "the same daughter says I am under the weather — I have left my meals two days running and I "
        "napped through my quiz programme.\n\n"
        "The clinic's card says a smoking change plus being under the weather means a level the same "
        "day, drawn before the practice closes at five. My daughter can bring me at any time you say."
    ),
    onset="Last cigarette last Thursday; under the weather and off my meals for two days.",
    severity="Off my food and napping. I would not have troubled you but for the card.",
    history="The schizoaffective, twelve years on clozapine, steady.",
    medications="Clozapine at night, and my blood-pressure tablet.",
    context="My daughter is off work today on purpose; we can come at short notice.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stangill",
)

STANGILL_SPLIT_INTAKE = (
    "Hello. Pauline Stangill. Only housekeeping — the chemist says my repeat needs re-authorising, the "
    "clozapine and my blood-pressure tablet both, and could the surgery sort the paperwork this week?\n\n"
    "And you can pin a rosette on my file: her last cigarette was last Thursday — that is how my "
    "daughter announces it to everyone, so I say it her way now. A week today."
)

pt_tarleholm = _caller(
    "pt_tarleholm",
    "Keith Tarleholm",
    49,
    "M",
    chart=(
        "Chronic schizophrenia, maintained on clozapine for ten years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 300 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Keith Tarleholm, clozapine patient. By the clinic's own card I need a level today, so "
        "I am ringing before the lines fill up.\n\n"
        "I have been off the cigarettes since the weekend — did it with the trust's stop-smoking lot, "
        "they gave us all a start date. And my neighbour, who does my shopping and keeps half an eye on "
        "me, says I am sickening: I left the pie she brought round untouched, and I was pasty and slow "
        "over the fence this morning, her words.\n\n"
        "The card is clear — smoking changed plus coming down with something is a same-day level, drawn "
        "before the practice closes at five. I am home all day and only round the corner from you."
    ),
    onset="Off the cigarettes since the weekend; off my food and slow since yesterday.",
    severity="Slow and not eating. Up and about, though — it is the card that says today, not me.",
    history="The schizophrenia, ten years on clozapine, watched at the clinic here.",
    medications="Clozapine at night. Nothing else on repeat.",
    context="Home all day; I can walk over the minute you give me a time.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarleholm",
)

TARLEHOLM_SPLIT_INTAKE = (
    "Morning. Keith Tarleholm. Nothing pressing — the trust's stop-smoking lot signed me up and I have "
    "been off the cigarettes since the weekend, and they said my surgery holds the carbon-monoxide "
    "blow-test gadget for the follow-ups.\n\n"
    "Do I book that with the nurse? Whenever suits the practice; I am in no hurry."
)

TARLEHOLM_RECALL = (
    "Keith Tarleholm again — my neighbour made me promise to ring back. She does my shopping and she "
    "says I am sickening for something: I left the pie she brought round untouched and I was pasty and "
    "slow over the fence this morning, her words not mine. The clozapine card says coming down with "
    "something on top of the smoking changing means a level the same day, before the practice closes at "
    "five. She is standing in my kitchen till I hang up, so consider it reported."
)

pt_saxgill = _caller(
    "pt_saxgill",
    "Raymond Saxgill",
    53,
    "M",
    chart=(
        "Paranoid schizophrenia, on clozapine for seven years; stable.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Brother is noted as next of kin.",
        "Repeat medication: clozapine 350 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Raymond Saxgill. The clozapine clinic will want me in for a level today — I will give "
        "you the two halves of it straight.\n\n"
        "Half one: I stopped the roll-ups on Monday. Thirty years of them, and I stopped with the "
        "trust's quit push. Half two: my brother says I am coming down with something — I have eaten "
        "next to nothing since yesterday and I was asleep in the chair before the news.\n\n"
        "The clinic's monitoring card says those two together are a same-day level, drawn before the "
        "practice closes at five. My brother has the van today, so we can be there whenever you say."
    ),
    onset="Stopped the roll-ups on Monday; eating next to nothing since yesterday.",
    severity="Washed out and off my food. Nothing worse — the card does the worrying for me.",
    history="The schizophrenia, seven years on clozapine, no trouble since.",
    medications="Clozapine at night, nothing else.",
    context="My brother and his van are mine till teatime; any appointment today works.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxgill",
)

SAXGILL_SPLIT_INTAKE = (
    "Hello. Raymond Saxgill. Small thing — I stopped the roll-ups on Monday, thirty years of them, with "
    "the trust's quit push. The fellow there said my own surgery can prescribe the patches cheaper than "
    "the shop sells them.\n\n"
    "Could that be sorted on my repeat? Next week is fine; I have a box to be going on with."
)

SAXGILL_RECALL = (
    "Raymond Saxgill again, sorry. My brother has been on at me since breakfast: I never told you I am "
    "coming down with something. I have eaten next to nothing since yesterday and I fell asleep in the "
    "chair before the news. He has the clozapine card in his hand now — it says the two together, the "
    "smoking changing and sickening for something, mean a level the same day, before the practice "
    "closes at five. He says to say he can drive me in the van whenever."
)

pt_stanholm = _caller(
    "pt_stanholm",
    "Janet Stanholm",
    45,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for six years; works part-time at the library.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 275 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Janet Stanholm. I think I need one of today's level appointments at the clozapine "
        "clinic, and I have my reasons lined up like library books.\n\n"
        "One: I gave up smoking on Wednesday. The clinic have asked me at every visit for six years and "
        "this week I finally could. Two: my flatmate says I am run down and coming down with something — "
        "I have gone off my lunches and I slept through my alarm twice, which I never do.\n\n"
        "Three: the monitoring card says one plus two equals a level the same day, drawn before the "
        "practice closes at five. I have swapped my shift, so today I am yours whenever."
    ),
    onset="Gave up smoking on Wednesday; run down and off my food since Tuesday evening.",
    severity="Run down and sleeping long. Still on my feet and at the library yesterday.",
    history="The schizoaffective, six years on clozapine, steady throughout.",
    medications="Clozapine at night. Nothing else.",
    context="Shift swapped away specially; I can be there inside twenty minutes all day.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stanholm",
)

STANHOLM_SPLIT_INTAKE = (
    "Good morning. Janet Stanholm. A dull question, I am afraid: I gave up smoking on Wednesday — six "
    "years the clinic have asked and this week I finally could — and the pharmacist says there is a "
    "practice form for the free patches scheme.\n\n"
    "Could somebody put one aside for me to sign? Any day this week does."
)

STANHOLM_RECALL = (
    "Janet Stanholm again, sorry to bother the desk twice. My flatmate insists I report myself "
    "properly: she says I am run down and coming down with something — off my lunches, slept through my "
    "alarm twice. The clozapine card in my purse says feeling unwell on top of a smoking change means a "
    "level the same day, before the practice closes at five. There — reported, and she is satisfied."
)

pt_tarlelund = _caller(
    "pt_tarlelund",
    "Derek Tarlelund",
    60,
    "M",
    chart=(
        "Chronic schizophrenia, maintained on clozapine for sixteen years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Wife is noted as carer on file.",
        "Repeat medication: clozapine 425 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Derek Tarlelund. My wife says I am to ring the surgery and not come off the phone "
        "till the clozapine level is sorted for today, so here I am.\n\n"
        "I put the cigarettes away on Sunday — properly away, the tin is in the shed and the shed is "
        "locked. And since Tuesday my wife says I am brewing a cold: I have left three dinners running "
        "and I was nodding off over the crossword by seven.\n\n"
        "The clinic's card, which my wife keeps with the coupons, says a change in smoking plus being "
        "poorly means a level the same day, drawn before the practice closes at five. She votes we come "
        "at whatever time you first have."
    ),
    onset="Cigarettes locked in the shed since Sunday; brewing a cold since Tuesday.",
    severity="A coming cold and no appetite. My wife is more troubled than I am, but the card backs her.",
    history="The schizophrenia, sixteen years on clozapine, never missed a blood test.",
    medications="Clozapine at night, and my cholesterol tablet.",
    context="My wife drives; we are free all day and ten minutes out.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarlelund",
)

TARLELUND_SPLIT_INTAKE = (
    "Morning. Derek Tarlelund. Two dull items, if you will. My cholesterol tablet wants renewing on the "
    "repeat — the chemist flagged it. And for the record my wife says to tell the surgery I put the "
    "cigarettes away on Sunday — properly away, tin in the shed, shed locked.\n\n"
    "That is the lot. No urgency on either count, she just likes things logged."
)

pt_saxholm = _caller(
    "pt_saxholm",
    "Gordon Saxholm",
    66,
    "M",
    chart=(
        "Treatment-resistant schizophrenia, on clozapine for nineteen years; stable.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 225 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Gordon Saxholm. I shall not keep you — the clozapine clinic will want a level "
        "off me today, by their own card's arithmetic.\n\n"
        "My daughter tells everyone down the phone that he stopped his pipe on Saturday — her words, and "
        "true enough: the pipe went out Saturday, after forty years, doctor's nagging finally landed. And "
        "the same daughter, who rings me every evening, says I sound full of cold and I admitted to her I have "
        "not eaten a proper meal since Sunday.\n\n"
        "The card says pipe or cigarettes, any change, with an illness on top: level the same day, drawn "
        "before the practice closes at five. I am retired and the bus stops outside the practice."
    ),
    onset="Pipe stopped on Saturday; full of cold and off proper meals since Sunday.",
    severity="A head cold and a poor appetite. I am up, dressed and complaining, so not at death's door.",
    history="The schizophrenia, nineteen years on clozapine, monitored here throughout.",
    medications="Clozapine at night, and a water tablet.",
    context="Retired; the number 12 bus puts me at your door any hour you like.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxholm",
)

SAXHOLM_SPLIT_INTAKE = (
    "Good morning. Gordon Saxholm. A small administrative matter: my water tablet has come off the "
    "repeat list at the chemist and wants putting back on, if somebody would.\n\n"
    "And my daughter says to tell you — she tells everyone — I stopped his pipe on Saturday. Her way of "
    "putting it. My pipe, after forty years. There is a certificate coming from her, I am told."
)

SAXHOLM_RECALL = (
    "Gordon Saxholm once more, and apologies. My daughter rang at lunch and has instructed me to report "
    "the rest: I sound full of cold, she says, and I admitted I have not eaten a proper meal since "
    "Sunday. The clozapine card on my mantel says any change in the pipe with an illness on top means a "
    "level the same day, before the practice closes at five. Her exact words were: ring them back and "
    "read them the card. Done."
)
pt_stanlund = _caller(
    "pt_stanlund",
    "Marion Stanlund",
    54,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for ten years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Mother (aged 80) lives with her and is noted as emergency contact.",
        "Repeat medication: clozapine 300 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Marion Stanlund. I am ringing for one of today's clozapine levels — the clinic's card "
        "puts me squarely in that box and I will explain.\n\n"
        "I swapped over to the nicotine patches on Monday — cigarettes finished, patches on, all under "
        "the trust's quit scheme. And my mother, who misses nothing, says I am sickening: I have pushed "
        "two dinners round the plate and I was asleep in front of the nine o'clock news.\n\n"
        "The card says the cigarettes stopping counts even with patches on, and with an illness on top "
        "it is a level the same day, drawn before the practice closes at five. Mother has appointed "
        "herself my chaperone, so we can come at any hour."
    ),
    onset="Cigarettes finished and patches on since Monday; sickening and off my food since Tuesday.",
    severity="Off my food and sleepy. Perfectly able to walk in and complain about it.",
    history="The schizoaffective, ten years on clozapine, monitored here.",
    medications="Clozapine at night, and now the nicotine patches.",
    context="My mother and I are home all day; the practice is one bus stop away.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stanlund",
)

STANLUND_SPLIT_INTAKE = (
    "Hello. Marion Stanlund. A prescriptions question, nothing more: I swapped over to the nicotine "
    "patches on Monday under the trust's quit scheme, and the scheme's paperwork says my own surgery "
    "takes over the patch prescription after the first fortnight.\n\n"
    "Could that be set up on my repeat in good time? No rush today."
)

pt_tarlemead = _caller(
    "pt_tarlemead",
    "Clive Tarlemead",
    36,
    "M",
    chart=(
        "Paranoid schizophrenia, on clozapine for three years; stable, studying part-time.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 250 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Clive Tarlemead. I think the clozapine clinic needs me today, and I have been told to "
        "say it plainly, so: I have not smoked since Friday teatime, and I am coming down with "
        "something.\n\n"
        "The not smoking is the college's doing — new term, new me. The coming down with something is my "
        "landlady's verdict: she says I have left two of her dinners and I look peaky, and she has seen "
        "every fresher's cold there is.\n\n"
        "My monitoring card — I photographed it, it lives on my phone — says a smoking change plus "
        "feeling unwell means a level the same day, drawn before the practice closes at five. Lectures "
        "finish at one; I can be with you any time after."
    ),
    onset="Not smoked since Friday teatime; peaky and off my food since Sunday.",
    severity="Peaky, my landlady's word. In myself: tired, no appetite, still at lectures.",
    history="The schizophrenia, three years on clozapine, no admissions since starting it.",
    medications="Clozapine at night. Nothing else.",
    context="Free after one o'clock; the practice is on my cycle route home.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarlemead",
)

TARLEMEAD_SPLIT_INTAKE = (
    "Morning. Clive Tarlemead. Quick admin one: I have not smoked since Friday teatime — new term, new "
    "me — and the student advisor says the practice nurse runs a quit clinic that keeps you honest.\n\n"
    "How do I get on the list for that? Any week coming is fine."
)

TARLEMEAD_RECALL = (
    "Clive Tarlemead again, sorry. My landlady caught me on the stairs and made me ring properly: her "
    "verdict is I am coming down with something — two of her dinners left, and I look peaky, and she has "
    "seen every fresher's cold there is. The clozapine card on my phone says a smoking change plus "
    "feeling unwell means a level the same day, before the practice closes at five. She is watching me "
    "make this call, so it is definitely made."
)

pt_saxlund = _caller(
    "pt_saxlund",
    "Brenda Saxlund",
    63,
    "F",
    chart=(
        "Treatment-resistant schizoaffective disorder, on clozapine for fifteen years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Husband is noted as carer on file.",
        "Repeat medication: clozapine 350 mg nightly in divided doses.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Brenda Saxlund. My husband and I have compared notes and the clozapine card "
        "settles it: I should have a level today.\n\n"
        "I gave the cigarettes up on Tuesday — the price rise did what fifteen years of leaflets could "
        "not. And my husband says I am poorly with something: I have gone off my food, tea included, "
        "and I sat down twice hoovering one room, which he says he has never once seen.\n\n"
        "The card, which lives in his wallet because I lose things, says a change in smoking plus being "
        "poorly is a same-day level, drawn before the practice closes at five. He drives, I supervise; "
        "name any time."
    ),
    onset="Cigarettes given up on Tuesday; poorly and off my food since Wednesday evening.",
    severity="Off my food and easily tired. Not ill in bed; ill enough for the card, my husband says.",
    history="The schizoaffective, fifteen years on clozapine, monitored here throughout.",
    medications="Clozapine, morning and night halves.",
    context="My husband is retired and restless; we can be there faster than you would credit.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxlund",
)

SAXLUND_SPLIT_INTAKE = (
    "Good morning. Brenda Saxlund. A little list, all dull: my repeat wants collecting Thursday not "
    "Friday this week if the chemist can be told, and I gave the cigarettes up on Tuesday — the price "
    "rise did what fifteen years of leaflets could not — so if the surgery keeps a note of such "
    "triumphs, add mine.\n\n"
    "That is everything. No hurry on any of it."
)

pt_stanmead = _caller(
    "pt_stanmead",
    "Alan Stanmead",
    57,
    "M",
    chart=(
        "Chronic schizophrenia, maintained on clozapine for thirteen years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 400 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Alan Stanmead. I will be brief because I know what the card says and now so will "
        "you.\n\n"
        "I finished with the cigarettes on Sunday — the allotment committee has gone smoke-free, of all "
        "things, and I spend my life up there. Since Monday my sister-in-law, who cooks for me Tuesdays "
        "and Thursdays, says I am off colour: her steak pie came home untouched, which has not happened "
        "in nine years, and I was asleep by half eight.\n\n"
        "The clozapine card says smoking changed plus off colour equals a level the same day, drawn "
        "before the practice closes at five. I am at the allotment till noon and anywhere you like after."
    ),
    onset="Finished with the cigarettes on Sunday; off colour and off my food since Monday.",
    severity="Off colour and off my food, her words and mine. Still digging, though, so be reassured.",
    history="The schizophrenia, thirteen years on clozapine, bloods never missed.",
    medications="Clozapine at night. Nothing else.",
    context="Allotment till noon; after that the day is the practice's.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stanmead",
)

STANMEAD_SPLIT_INTAKE = (
    "Morning. Alan Stanmead. One for the nurse's list, no rush: I finished with the cigarettes on "
    "Sunday — the allotment committee has gone smoke-free, of all things — and I am told the practice "
    "does a stop-smoking check-in with a blow test.\n\n"
    "Put me down for whenever there is a gap in the diary."
)

STANMEAD_RECALL = (
    "Alan Stanmead again, and I will make it quick. My sister-in-law says I sold you half a story this "
    "morning: since Monday I have been off colour — her steak pie came home untouched, first time in "
    "nine years, and I was asleep by half eight. The clozapine card says off colour on top of the "
    "smoking changing means a level the same day, before the practice closes at five. There. The whole "
    "story, as instructed."
)

pt_tarleridge = _caller(
    "pt_tarleridge",
    "Susan Tarleridge",
    48,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for eight years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Daughter is noted as carer on file.",
        "Repeat medication: clozapine 325 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Susan Tarleridge. My daughter has drawn up the case like a solicitor, so I shall "
        "present it: the clozapine clinic should take my level today.\n\n"
        "Exhibit one: I packed the smokes in on Thursday, with the trust's quit people, start date and "
        "all. Exhibit two: my daughter says I am coming down with something — I have picked at my meals "
        "since Saturday and I fell asleep in the middle of her wedding-planning spreadsheet, which she "
        "took personally.\n\n"
        "Exhibit three: the clinic's card says one and two together mean a level the same day, drawn "
        "before the practice closes at five. The case rests. We are both free all day."
    ),
    onset="Packed the smokes in on Thursday; picking at meals and sleepy since Saturday.",
    severity="Sleepy and picking at food. My daughter is the worried one; the card agrees with her.",
    history="The schizoaffective, eight years on clozapine, monitored here.",
    medications="Clozapine at night, and an iron tablet.",
    context="My daughter is home planning her wedding; she can drive me at any hour today.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarleridge",
)

TARLERIDGE_SPLIT_INTAKE = (
    "Hello. Susan Tarleridge. Only a small thing for the repeats desk: my iron tablet needs "
    "re-authorising, the chemist says.\n\n"
    "And a note for the practice records: I packed the smokes in on Thursday, with the trust's quit "
    "people, start date and all. My daughter says it goes on my record or it never happened."
)

TARLERIDGE_RECALL = (
    "Susan Tarleridge again — closing submission, my daughter calls it. The clozapine clinic's card "
    "says a smoking change plus coming down with something means a level the same day, drawn before the "
    "practice closes at five. She has read it to me twice down the phone and once in person, so I am "
    "reading it to you. That is everything she wanted said."
)

pt_saxridge = _caller(
    "pt_saxridge",
    "Norman Saxridge",
    69,
    "M",
    chart=(
        "Treatment-resistant schizophrenia, on clozapine for twenty-one years; stable.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 200 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Norman Saxridge. Twenty-one years on the clozapine and I know the card by "
        "heart, so I shall recite: a change in the smoking, with an illness on top, is a level the same "
        "day, drawn before the practice closes at five.\n\n"
        "Both halves apply. I stopped smoking with the no-smoking week — the whole bowls club did it "
        "together, there was a thermometer chart and everything. And my neighbour, who has a key and "
        "strong opinions, says I am full of a cold and she has watched me leave two lunches this "
        "week.\n\n"
        "So there it is, recited and true. I am retired and the day is empty; any time serves."
    ),
    onset="Stopped smoking with the no-smoking week; full of cold and off my lunches since Tuesday.",
    severity="A cold and a poor appetite. I have had worse and said less, but the card is the card.",
    history="The schizophrenia, twenty-one years on clozapine, monitored here man and boy, near enough.",
    medications="Clozapine at night, and a statin.",
    context="Retired; my neighbour or the bus can produce me at the practice within the half hour.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxridge",
)

SAXRIDGE_SPLIT_INTAKE = (
    "Good morning. Norman Saxridge. Nothing urgent whatsoever — I stopped smoking with the no-smoking "
    "week, the whole bowls club did it together, thermometer chart and everything, and I am told to ask "
    "whether the practice wants that noted anywhere official.\n\n"
    "Also my statin repeat is due at the month's end, if that can just tick along as usual."
)

SAXRIDGE_RECALL = (
    "Norman Saxridge again, apologies. My neighbour — she has a key and strong opinions — says I am "
    "full of a cold and she has watched me leave two lunches this week, and she stood over me till I "
    "agreed to ring back. The clozapine card says an illness on top of a smoking change means a level "
    "the same day, before the practice closes at five. I know it by heart and now the desk has it too."
)

pt_stanridge = _caller(
    "pt_stanridge",
    "Carol Stanridge",
    42,
    "F",
    chart=(
        "Paranoid schizophrenia, on clozapine for five years; stable, two school-age children.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Sister lives two doors down and is noted as emergency contact.",
        "Repeat medication: clozapine 300 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Carol Stanridge. Before the school run swallows me: I think the clozapine clinic "
        "needs my level today.\n\n"
        "I have sworn off the cigarettes since Monday — the kids found the leaflet from the trust's "
        "quit push and staged an intervention over fish fingers. And my sister, two doors down, says I "
        "am sickening for something: I have fed the kids and skipped my own tea twice, and I went to bed "
        "when they did on Wednesday.\n\n"
        "The clinic's card on my noticeboard says a smoking change plus sickening for something means a "
        "level the same day, drawn before the practice closes at five. My sister has the school pickup "
        "today, so any time you say works."
    ),
    onset="Sworn off the cigarettes since Monday; sickening and skipping meals since Tuesday.",
    severity="Tired and off my food. Managing the kids fine, so nothing alarming in me.",
    history="The schizophrenia, five years on clozapine, steady, monitored here.",
    medications="Clozapine at night. Nothing else.",
    context="Free after drop-off; my sister has the pickup today, so afternoon times work as well.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stanridge",
)

STANRIDGE_SPLIT_INTAKE = (
    "Morning. Carol Stanridge. Speedy one before the school run: I have sworn off the cigarettes since "
    "Monday — the kids staged an intervention over fish fingers, long story — and the trust's leaflet "
    "says my surgery can prescribe the lozenges.\n\n"
    "Could that go on my file for the doctor to approve when there is a minute? No rush at all."
)

pt_tarleroyd = _caller(
    "pt_tarleroyd",
    "Frank Tarleroyd",
    59,
    "M",
    chart=(
        "Chronic schizophrenia, maintained on clozapine for seventeen years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 375 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Frank Tarleroyd. I shall say it the way my son says it, since he is the one who "
        "noticed both halves: his tobacco tin has been shut since Saturday, and he is coming down with "
        "something and won't admit it. That is me he means, on both counts.\n\n"
        "The tin is shut because of the trust's quit week — seventeen years they have asked. The coming "
        "down with something is a cold in the head and no appetite since Sunday; I left a roast, which "
        "my son says should be in the newspaper.\n\n"
        "The clozapine card says the two together mean a level the same day, drawn before the practice "
        "closes at five. My son has a taxi badge and an empty morning, so we can be quick."
    ),
    onset="Tobacco tin shut since Saturday; head cold and no appetite since Sunday.",
    severity="A head cold and no appetite. On my feet and arguing with my son, so well enough.",
    history="The schizophrenia, seventeen years on clozapine, monitored at the clinic here.",
    medications="Clozapine at night, nothing else.",
    context="My son drives a taxi and is free till noon; after that the bus does me fine.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarleroyd",
)

TARLEROYD_SPLIT_INTAKE = (
    "Morning. Frank Tarleroyd. One thing only: my son wants it on my record that his tobacco tin has "
    "been shut since Saturday — mine, he means, shut for the trust's quit week, seventeen years in the "
    "asking.\n\n"
    "He says the surgery keeps a quit register or some such. If there is one, put me on it. No hurry."
)

TARLEROYD_RECALL = (
    "Frank Tarleroyd again. My son says I rang you this morning and left out the half that matters — I "
    "have a cold in the head and no appetite since Sunday, left a roast untouched, which he says should "
    "be in the newspaper. The clozapine card says coming down with something on top of any change in "
    "the smoking means a level the same day, before the practice closes at five. He is idling the taxi "
    "outside while I say it, so it is said."
)

pt_saxroyd = _caller(
    "pt_saxroyd",
    "Sheila Saxroyd",
    50,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for seven years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Wife of record is noted as carer on file.",
        "Repeat medication: clozapine 275 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Sheila Saxroyd. My wife has the clozapine card in front of her and is conducting me "
        "like an orchestra, so here is the full performance.\n\n"
        "Movement one: I have come off the cigarettes this last week — we did it as a pair, her idea, "
        "the trust's quit scheme supplied the leaflets. Movement two: she says I am brewing something — "
        "I have gone off my food since Wednesday and I napped through the football, which she says has "
        "never once happened in twenty years.\n\n"
        "Finale: the card says a smoking change plus brewing something means a level the same day, "
        "drawn before the practice closes at five. Applause optional; an appointment today essential, "
        "says the conductor."
    ),
    onset="Off the cigarettes this last week; off my food and napping since Wednesday.",
    severity="Off my food and sleepy. Nothing that would stop me coming in, everything the card names.",
    history="The schizoaffective, seven years on clozapine, monitored here.",
    medications="Clozapine at night, and a thyroid tablet.",
    context="My wife drives; we are free all day and glad of the outing, frankly.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxroyd",
)

SAXROYD_SPLIT_INTAKE = (
    "Hello. Sheila Saxroyd. Two dull lines for the desk: my thyroid tablet wants re-authorising on the "
    "repeat, says the chemist. And I have come off the cigarettes this last week — my wife and I did it "
    "as a pair, her idea — so if the practice logs quitters, log two of us.\n\n"
    "That is all. Nothing needs doing today."
)

pt_stansett = _caller(
    "pt_stansett",
    "Roy Stansett",
    64,
    "M",
    chart=(
        "Treatment-resistant schizophrenia, on clozapine for eighteen years; stable.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 350 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Roy Stansett. I had this speech written for me by my lodger, who used to be a "
        "ward clerk and misses it, so it is thorough.\n\n"
        "Point one: no cigarettes since a week last Sunday. The longest run of my adult life, courtesy "
        "of the trust's quit push. Point two: the lodger says I am sickening — I have left my breakfast "
        "three days going and I was in bed before the kettle had cooled, her words.\n\n"
        "Point three: the clozapine card says the first two together mean a level the same day, "
        "drawn before the practice closes at five. Point four: we are both in all day and the practice "
        "is a flat ten-minute walk."
    ),
    onset="No cigarettes since a week last Sunday; sickening and off breakfast three days going.",
    severity="Off my food and early to bed. Upright, walking, and reciting speeches, as you hear.",
    history="The schizophrenia, eighteen years on clozapine, monitored at the clinic here.",
    medications="Clozapine at night, nothing else on repeat.",
    context="In all day; a flat ten-minute walk from the practice, quicker if it rains.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_stansett",
)

STANSETT_SPLIT_INTAKE = (
    "Good morning. Roy Stansett. Nothing that cannot wait: my lodger, who used to be a ward clerk, "
    "says the surgery will want it minuted that I have had no cigarettes since a week last Sunday — the "
    "longest run of my adult life, courtesy of the trust's quit push.\n\n"
    "Minute it wherever such things go. That is the whole of my business today."
)

STANSETT_RECALL = (
    "Roy Stansett again — the lodger has found the second page of her own speech. She says I am "
    "sickening: breakfast left three days going, in bed before the kettle had cooled. And she says the "
    "clozapine card is to be read out, so: an illness on top of a smoking change means a level the same "
    "day, before the practice closes at five. Read out, as ordered. Good morning to you."
)

pt_tarlesett = _caller(
    "pt_tarlesett",
    "Eileen Tarlesett",
    55,
    "F",
    chart=(
        "Schizoaffective disorder, stable on clozapine for eleven years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; bloods current.",
        "Brother is noted as next of kin and drives her to appointments.",
        "Repeat medication: clozapine 325 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Eileen Tarlesett. My brother is on his way over and says to have it all told before he "
        "arrives, so, quickly and in full.\n\n"
        "I turned the cigarettes in on Wednesday — handed the packet to the trust's quit lady across "
        "her own desk, very satisfying. Since Friday my brother says I am coming down with something: I "
        "have made three dinners and eaten none of them, and I was asleep over my library book at "
        "seven.\n\n"
        "The clozapine card in my kitchen drawer says a smoking change plus coming down with something "
        "means a level the same day, drawn before the practice closes at five. He will drive me the "
        "moment a time exists."
    ),
    onset="Cigarettes turned in on Wednesday; off my dinners and sleepy since Friday.",
    severity="Off my food and sleepy over my book. Nothing worse; the card does not ask for worse.",
    history="The schizoaffective, eleven years on clozapine, monitored here.",
    medications="Clozapine at night, and a vitamin D tablet in winter.",
    context="My brother drives; between us we can meet any time the practice names.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_tarlesett",
)

TARLESETT_SPLIT_INTAKE = (
    "Hello. Eileen Tarlesett. Small housekeeping: could my vitamin D tablet go back on the winter "
    "repeat? The chemist says it lapsed.\n\n"
    "And one for the record books — I turned the cigarettes in on Wednesday, handed the packet to the "
    "trust's quit lady across her own desk. Very satisfying. That is everything from me."
)

pt_saxsett = _caller(
    "pt_saxsett",
    "Vera Saxsett",
    61,
    "F",
    chart=(
        "Chronic schizophrenia, maintained on clozapine for twenty years.",
        "Clozapine monitoring under the mental health clinic hosted at the practice; last level in range.",
        "Repeat medication: clozapine 250 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. Vera Saxsett. Twenty years on the clozapine, so believe me when I say I only "
        "ring like this when the card says I must.\n\n"
        "My granddaughter has told the whole street I smoked her last one on Friday night — her way of "
        "putting it, and accurate: the last cigarette went out on the step Friday night, and she took "
        "the lighter for her candles. And the "
        "same granddaughter, who stops by mornings, says I am poorly with something: I have gone off my "
        "toast and marmalade, of all things, and I was back in bed at ten yesterday.\n\n"
        "The card says a smoking change plus being poorly means a level the same day, drawn before the "
        "practice closes at five. She has a little car and no lectures today, so we are at your service."
    ),
    onset="Smoked my last one on Friday night; poorly and off my food since Sunday.",
    severity="Off my toast and back to bed by ten. As poorly as I have been in years, which is not very.",
    history="The schizophrenia, twenty years on clozapine, never missed a monitoring visit.",
    medications="Clozapine at night, and drops for my eyes.",
    context="My granddaughter drives me; mornings or afternoons, either suits us.",
    gold=CLAIMANT_GOLD,
    source="authored:clozapine_infection_saxsett",
)

SAXSETT_SPLIT_INTAKE = (
    "Good morning. Vera Saxsett. Nothing at all urgent — my eye drops are running low and want adding "
    "to this month's repeat, if somebody would be so kind.\n\n"
    "And my granddaughter says to tell you I smoked her last one on Friday night — MY last one, out on "
    "the step; she has the lighter for her candles now. She is very proud and says it must be official."
)

SAXSETT_RECALL = (
    "Vera Saxsett again, dear, and I am sorry to ring twice. My granddaughter stopped by and says the "
    "rest must be said: I am poorly with something — off my toast and marmalade, of all things, and "
    "back in bed at ten yesterday. The clozapine card says being poorly on top of a smoking change "
    "means a level the same day, before the practice closes at five. She is nodding at me, so that is "
    "everything."
)

# ── the twenty-five holders ───────────────────────────────────────────────────────────────────────────────
# Nobody rings ABOUT a holder — they are on the books. A holder's intake is what they say if a desk RINGS
# THEM (`rebooking._rebookee`'s convention). No holder pre-consents to being moved; each has an ordinary,
# human reason to want today.

pt_stanroyd = _caller(
    "pt_stanroyd",
    "Harold Stanroyd",
    71,
    "M",
    chart=(
        "Bipolar affective disorder, stable for years; annual review at the mental health clinic.",
        "Repeat medication: quetiapine 300 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review at the mental health clinic is this afternoon. My son-in-law has taken a half "
        "day to drive me, and those half days are not easily got. I have had the letter on the "
        "mantelpiece a fortnight."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. The appointment is routine and I should like to keep it.",
    history="The bipolar, steady a long while, reviewed yearly at the clinic.",
    medications="Quetiapine at night.",
    context="My son-in-law took a half day specially to drive me in.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_stanroyd",
)

pt_saxthwaite = _caller(
    "pt_saxthwaite",
    "June Saxthwaite",
    66,
    "F",
    chart=(
        "Recurrent depressive disorder, in remission; annual medication review at the mental health "
        "clinic.",
        "Repeat medication: venlafaxine 150 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My medication review is this afternoon — the yearly one. My neighbour minds the dog when I "
        "have appointments and she has arranged her day around it. I would sooner not begin the "
        "rigmarole of new arrangements."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Quite well, thank you. It is routine.",
    history="The depression, settled a good while on the same tablet.",
    medications="Venlafaxine every morning.",
    context="The neighbour is minding the dog this afternoon specially.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_saxthwaite",
)

pt_stanthwaite = _caller(
    "pt_stanthwaite",
    "Leonard Stanthwaite",
    58,
    "M",
    chart=(
        "Schizophrenia, stable on a monthly depot; annual depot and physical health review at the "
        "mental health clinic.",
        "Repeat medication: depot antipsychotic, monthly, clinic-administered.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my yearly depot review this afternoon, the big one with the physical checks. My key "
        "worker moved her visits round so she could come with me. It took some arranging, I will say "
        "that."
    ),
    onset="Nothing new; it is the yearly depot review.",
    severity="I am well; the depot suits me. The review is routine.",
    history="The schizophrenia, steady on the depot for years.",
    medications="The depot, once a month at the clinic.",
    context="My key worker rearranged her round to come along this afternoon.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_stanthwaite",
)

pt_tarlethwaite = _caller(
    "pt_tarlethwaite",
    "Margaret Tarlethwaite",
    73,
    "F",
    chart=(
        "Generalised anxiety disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: sertraline 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review is this afternoon. I get anxious about appointments changing — that is half "
        "of what the appointment is for, if you follow me — and my daughter has come up from town "
        "overnight to sit with me through it."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Well enough, though changes to plans cost me sleep.",
    history="The anxiety, managed steadily for years on the same tablet.",
    medications="Sertraline in the morning.",
    context="My daughter came up from town overnight for this appointment.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tarlethwaite",
)

pt_saxwell = _caller(
    "pt_saxwell",
    "Dennis Saxwell",
    62,
    "M",
    chart=(
        "Recurrent depressive disorder, stable; annual medication review at the mental health clinic.",
        "Repeat medication: mirtazapine 30 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "The yearly tablet review, this afternoon. I have booked the afternoon off the taxi rank for "
        "it, which is money out of my pocket, so I am keen it goes ahead as printed on the letter."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. Routine, as I said.",
    history="The depression, steady on the same tablet a long time.",
    medications="Mirtazapine at night.",
    context="An afternoon off the taxi rank is booked and unpaid; today suits because it is arranged.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_saxwell",
)

pt_stanwell = _caller(
    "pt_stanwell",
    "Doris Stanwell",
    69,
    "F",
    chart=(
        "Bipolar affective disorder, stable for years; annual review at the mental health clinic.",
        "Repeat medication: lamotrigine 200 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review is this afternoon. My sister and I make a day of it — lunch first, then the "
        "clinic, then the garden centre. She is already on the train. It sounds small but it is our "
        "day, and it took three diaries to fix."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="Very well. It is entirely routine.",
    history="The bipolar, settled for years on the same tablet.",
    medications="Lamotrigine, morning and evening halves.",
    context="My sister is on the train already; the day is built around the appointment.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_stanwell",
)

pt_tarlewell = _caller(
    "pt_tarlewell",
    "Ernest Tarlewell",
    75,
    "M",
    chart=(
        "Schizophrenia, stable on a monthly depot; annual depot review at the mental health clinic.",
        "Repeat medication: depot antipsychotic, monthly, clinic-administered.",
        "No known drug allergies.",
    ),
    intake=(
        "The yearly depot review, this afternoon. The warden here books the community car a week ahead "
        "and it is booked. At my age the getting there is the harder half of any appointment, and the "
        "getting there is arranged."
    ),
    onset="Nothing new; it is the yearly depot review.",
    severity="I am well; the depot has suited me for years.",
    history="The schizophrenia, steady on the depot a long while.",
    medications="The depot, monthly at the clinic.",
    context="The sheltered housing's community car is booked for this afternoon.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tarlewell",
)

pt_tarlebrook = _caller(
    "pt_tarlebrook",
    "Sylvia Tarlebrook",
    54,
    "F",
    chart=(
        "Recurrent depressive disorder, stable; annual medication review at the mental health clinic.",
        "Repeat medication: fluoxetine 40 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablet review is this afternoon — the yearly one. I work term-time only and the school is "
        "shut today for an inset day; miss it and the next chance to come without unpaid leave is the "
        "Easter holidays."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Well, thank you. Routine entirely.",
    history="The depression, steady for years on the same dose.",
    medications="Fluoxetine in the morning.",
    context="Inset day today; any other day means unpaid leave from the school kitchen.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tarlebrook",
)

pt_translund = _caller(
    "pt_translund",
    "Victor Translund",
    67,
    "M",
    chart=(
        "Schizoaffective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: aripiprazole 15 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review at the mental health clinic is this afternoon. My brother fetches me from "
        "the coast for it and takes me back after — a hundred miles round, he says, and worth it once "
        "a year. He set off after breakfast."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. The appointment is the routine one.",
    history="The schizoaffective, settled for years on the same tablet.",
    medications="Aripiprazole in the morning.",
    context="My brother is already driving in from the coast for it.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_translund",
)

pt_sudmere = _caller(
    "pt_sudmere",
    "Beryl Sudmere",
    72,
    "F",
    chart=(
        "Generalised anxiety disorder with low mood, stable; annual review at the mental health clinic.",
        "Repeat medication: escitalopram 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review is this afternoon. I have my hearing-aid fitting in the same building at "
        "four, and I planned the two together on purpose — one trip, one taxi fare each way. Undo one "
        "and the whole afternoon unravels."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Quite well. It is routine.",
    history="The anxiety and low mood, steady a long while.",
    medications="Escitalopram in the morning.",
    context="Hearing-aid fitting at four in the same building; the taxi is booked to suit both.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_sudmere",
)

pt_selworth = _caller(
    "pt_selworth",
    "Stanley Selworth",
    65,
    "M",
    chart=(
        "Bipolar affective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: olanzapine 10 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "The yearly review, this afternoon. I have my grandson's school concert tomorrow and the "
        "allotment committee's seed-potato day Friday — it is the one afternoon this week that was clear, "
        "which is why I took it when they rang."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well; it is the routine look-over.",
    history="The bipolar, steady on the same tablet for years.",
    medications="Olanzapine at night.",
    context="The one clear afternoon of the week; the rest are spoken for.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_selworth",
)

pt_swindale = _caller(
    "pt_swindale",
    "Freda Swindale",
    59,
    "F",
    chart=(
        "Recurrent depressive disorder, stable; annual medication review at the mental health clinic.",
        "Repeat medication: duloxetine 60 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My medication review is this afternoon. I have arranged cover at the charity shop — we are "
        "only two on a Thursday and Joan is coming in specially, on her bowls day. I would not like to "
        "ask her twice."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Well in myself. Entirely routine.",
    history="The depression, settled for years on the same dose.",
    medications="Duloxetine in the morning.",
    context="Cover at the charity shop is arranged for this afternoon only.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_swindale",
)

pt_tormoor = _caller(
    "pt_tormoor",
    "Albert Tormoor",
    77,
    "M",
    chart=(
        "Schizophrenia, stable on a monthly depot; annual depot and physical health review at the "
        "mental health clinic.",
        "Repeat medication: depot antipsychotic, monthly, clinic-administered.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my yearly depot review this afternoon, with the physical checks. My niece has borrowed "
        "her husband's car for it — mine failed its MOT — and she has the school run at half three, so "
        "the timing is worked out to the minute."
    ),
    onset="Nothing new; it is the yearly depot review.",
    severity="I am well; the depot suits me.",
    history="The schizophrenia, steady on the depot many years.",
    medications="The depot, monthly at the clinic.",
    context="My niece has the borrowed car today only, around the school run.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tormoor",
)

pt_shelcroft = _caller(
    "pt_shelcroft",
    "Rose Shelcroft",
    63,
    "F",
    chart=(
        "Generalised anxiety disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: paroxetine 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review is this afternoon. I do not drive and my son has swapped a shift at the "
        "depot to take me — swaps have to go through his union rep, if you can believe it, so it is not "
        "a thing done twice in a month."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Quite well, thank you.",
    history="The anxiety, steady on the same tablet for years.",
    medications="Paroxetine in the morning.",
    context="My son's shift swap went through the union rep; today is the day it bought.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_shelcroft",
)

pt_snelshaw = _caller(
    "pt_snelshaw",
    "Walter Snelshaw",
    70,
    "M",
    chart=(
        "Bipolar affective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: carbamazepine 400 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "The yearly review, this afternoon. My wife goes into hospital for her hip next week and I "
        "shall be fetching and carrying for six weeks after — this was the last afternoon that was "
        "properly mine, which is why I took it."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. Routine.",
    history="The bipolar, settled on the same tablet a long while.",
    medications="Carbamazepine, morning and night.",
    context="The last free afternoon before my wife's hip operation next week.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_snelshaw",
)

pt_sibleigh = _caller(
    "pt_sibleigh",
    "Nora Sibleigh",
    68,
    "F",
    chart=(
        "Recurrent depressive disorder, in remission; annual medication review at the mental health "
        "clinic.",
        "Repeat medication: citalopram 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablet review is this afternoon, the yearly one. I have the grandchildren from Friday for "
        "a week — their parents' silver-wedding trip — and I promised their mother I would have all my "
        "appointments done and dusted before they land."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Well, thank you. Routine entirely.",
    history="The depression, settled for years.",
    medications="Citalopram in the morning.",
    context="Grandchildren arrive Friday for the week; this is the clear afternoon.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_sibleigh",
)

pt_tidstow = _caller(
    "pt_tidstow",
    "Ronald Tidstow",
    61,
    "M",
    chart=(
        "Schizoaffective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: risperidone 4 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review at the mental health clinic is this afternoon. I have carers in morning and "
        "evening and the agency wrote the afternoon slot into this week's rota so someone can come "
        "along with me. Rotas, in my experience, do not bend twice."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well; it is the routine one.",
    history="The schizoaffective, steady for years on the same tablet.",
    medications="Risperidone in the morning.",
    context="The care agency wrote this appointment into the week's rota.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tidstow",
)

pt_tamfirth = _caller(
    "pt_tamfirth",
    "Hilda Tamfirth",
    74,
    "F",
    chart=(
        "Generalised anxiety disorder with low mood, stable; annual review at the mental health clinic.",
        "Repeat medication: sertraline 100 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review is this afternoon. The ring-and-ride bus is booked both ways — you book it "
        "two days ahead or not at all, and I did. I am not nimble enough for the ordinary bus since my "
        "fall."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Well enough, thank you.",
    history="The anxiety and low mood, steady a long while.",
    medications="Sertraline in the morning.",
    context="The ring-and-ride is booked both ways for this afternoon.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tamfirth",
)

pt_sudleigh = _caller(
    "pt_sudleigh",
    "George Sudleigh",
    66,
    "M",
    chart=(
        "Bipolar affective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: valproate 800 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "The yearly review, this afternoon. I have a lad coming to see about the guttering at nine "
        "tomorrow and the funeral of an old workmate Friday — this afternoon was the gap, and the "
        "letter has been on the fridge a month."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. Routine, as ever.",
    history="The bipolar, settled on the same tablets for years.",
    medications="Valproate, morning and night.",
    context="The week is otherwise spoken for; the letter has been on the fridge a month.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_sudleigh",
)

pt_selmoor = _caller(
    "pt_selmoor",
    "Edith Selmoor",
    79,
    "F",
    chart=(
        "Recurrent depressive disorder, stable; annual medication review at the mental health clinic.",
        "Repeat medication: sertraline 50 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablet review is this afternoon. My friend Cissie and I share the taxi when our appointments "
        "line up, and hers is at the chiropodist next door at the same hour — we lined them up on "
        "purpose, it halves the fare."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Quite well, dear, thank you.",
    history="The depression, settled many years.",
    medications="Sertraline in the morning.",
    context="The shared taxi with Cissie is arranged around this exact hour.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_selmoor",
)

pt_swincroft = _caller(
    "pt_swincroft",
    "Percy Swincroft",
    69,
    "M",
    chart=(
        "Schizophrenia, stable on a monthly depot; annual depot review at the mental health clinic.",
        "Repeat medication: depot antipsychotic, monthly, clinic-administered.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my yearly depot review this afternoon. My daughter has driven up from her new job — her "
        "first leave day since starting — and she wants to sit in and hear how I am doing for herself. "
        "That day was not easily won."
    ),
    onset="Nothing new; it is the yearly depot review.",
    severity="I am well; the depot suits me fine.",
    history="The schizophrenia, steady on the depot for many years.",
    medications="The depot, monthly at the clinic.",
    context="My daughter's first leave day from the new job is today, for this.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_swincroft",
)

pt_torbourne = _caller(
    "pt_torbourne",
    "Mabel Torbourne",
    76,
    "F",
    chart=(
        "Generalised anxiety disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: mirtazapine 15 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review is this afternoon. The home help stays the extra hour on review day so I am "
        "not rushed — it is in her sheet from the office. Change the day and the extra hour goes back "
        "through the office, which takes a fortnight."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Well enough, thank you kindly.",
    history="The anxiety, settled for years on the night tablet.",
    medications="Mirtazapine at night.",
    context="The home help's extra hour is authorised for this afternoon.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_torbourne",
)

pt_shelmere = _caller(
    "pt_shelmere",
    "Arnold Shelmere",
    64,
    "M",
    chart=(
        "Bipolar affective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: olanzapine 7.5 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "The yearly review, this afternoon. I am best man at a wedding Saturday and the suit fitting, "
        "the speech run-through and the drive south all stack up behind today — this afternoon was the "
        "one that fitted, and I have planned the week backwards from it."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well. Routine.",
    history="The bipolar, steady on the same tablet a good while.",
    medications="Olanzapine at night.",
    context="The week is planned backwards from this afternoon's appointment.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_shelmere",
)

pt_snelworth = _caller(
    "pt_snelworth",
    "Gladys Snelworth",
    70,
    "F",
    chart=(
        "Recurrent depressive disorder, in remission; annual medication review at the mental health "
        "clinic.",
        "Repeat medication: venlafaxine 75 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My tablet review is this afternoon, the yearly one. My husband walks me in — his memory is "
        "going and appointments anchor his week; he has told everyone at the day centre it is review "
        "day. Moving it muddles him for days, we have learned."
    ),
    onset="Nothing new; the review is the yearly one.",
    severity="Quite well in myself.",
    history="The depression, settled for years.",
    medications="Venlafaxine in the morning.",
    context="My husband has the day anchored around walking me in this afternoon.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_snelworth",
)

pt_tiddale = _caller(
    "pt_tiddale",
    "Cyril Tiddale",
    72,
    "M",
    chart=(
        "Schizoaffective disorder, stable; annual review at the mental health clinic.",
        "Repeat medication: amisulpride 200 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly review at the mental health clinic is this afternoon. I have matched it with my "
        "sister's visit — she comes the second week of the month, does my letters and sits in on the "
        "review to take notes. She caught the early coach."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well; it is the routine one.",
    history="The schizoaffective, steady for years on the same tablet.",
    medications="Amisulpride in the morning.",
    context="My sister caught the early coach to sit in on this review.",
    gold=_holder_gold(),
    source="authored:clozapine_infection_holder_tiddale",
)
# ── the twelve kin carriers (dual-purpose callers: their own routine matter, and — in the split twin
# only — the piece of a claimant's picture they happen to hold) ───────────────────────────────────────────

pt_stanfold_m = _caller(
    "pt_stanfold_m",
    "Ivy Stanfold",
    74,
    "F",
    chart=(
        "Osteoarthritis of both knees, managed with topical treatment.",
        "Repeat medication: ibuprofen gel, paracetamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Only a small thing — my knee gel has run out of repeats at the chemist and wants "
        "re-authorising, whenever somebody has a minute. There is no hurry; I have paracetamol to be "
        "going on with."
    ),
    onset="Nothing new — the strip in the drawer is the last of it.",
    severity="The knees are their usual selves. It is paperwork, not a complaint.",
    history="The knees have creaked for a good ten years; they get me about.",
    medications="The ibuprofen gel and paracetamol when they shout.",
    context="I am at home all day; my son Gary lives with me.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_stanfold_m",
)

STANFOLD_M_SPLIT_INTAKE = (
    "Hello. Only a small thing — my knee gel has run out of repeats at the chemist and wants "
    "re-authorising, whenever somebody has a minute. No hurry; I have paracetamol to be going on "
    "with.\n\n"
    "While I have you: my son Gary — Gary Stanfold, he is one of the clozapine patients — is sickening "
    "for something, whatever he tells you. He has gone off his food and he slept half of yesterday "
    "afternoon, which is not him at all. I thought the surgery should have that from me, since he "
    "will make light of it."
)

pt_saxfold_w = _caller(
    "pt_saxfold_w",
    "Pat Saxfold",
    64,
    "F",
    chart=(
        "Hypertension, controlled; annual blood-pressure check due.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Nothing pressing — I am ringing to get my yearly blood-pressure check booked, the nurse "
        "one. Any day the next fortnight suits; I fit round other people, it is what I am for."
    ),
    onset="Nothing new — the yearly check has come round.",
    severity="I am well. It is the routine check.",
    history="The blood pressure, steady on one tablet for years.",
    medications="Amlodipine, one in the morning.",
    context="I drive, so timing is easy. My husband Colin has his own appointments here.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_saxfold_w",
)

SAXFOLD_W_SPLIT_INTAKE = (
    "Hello. Nothing pressing for me — I want my yearly blood-pressure check booked with the nurse, any "
    "day the next fortnight.\n\n"
    "But I do want a word about my husband, Colin Saxfold, one of the clozapine patients. He is coming "
    "down with something: he has hardly touched a meal since yesterday dinner and he was heavy as lead "
    "getting up. His monitoring card on our fridge says an illness on top of any change in the smoking "
    "means a level the same day, drawn before the practice closes at five. I am telling you what I "
    "see; he can speak for himself."
)

pt_tarlegill_s = _caller(
    "pt_tarlegill_s",
    "Andrew Tarlegill",
    38,
    "M",
    chart=(
        "Mild asthma, well controlled; last review unremarkable.",
        "Repeat medication: salbutamol inhaler as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Quick admin one from me — the physio sent a letter saying my referral needs a code "
        "from the surgery before they will book me for my shoulder. Could that be chased when someone "
        "has a minute? It is not urgent, the shoulder and I have an understanding."
    ),
    onset="The shoulder is weeks old and mild; it is the referral paperwork that is stuck.",
    severity="A niggle, no more. The letter is the errand.",
    history="Asthma as a lad, barely a puff needed these days.",
    medications="The blue inhaler, rarely.",
    context="I work from my mother's spare room most days — Maureen Tarlegill, she is a patient here.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_tarlegill_s",
)

TARLEGILL_S_SPLIT_INTAKE = (
    "Morning. Two things, one mine, one my mother's. Mine: the physio wants a referral code from the "
    "surgery for my shoulder before they will book me — could that be chased sometime? No rush.\n\n"
    "My mother is Maureen Tarlegill, one of the clozapine patients. She is not right this week: off "
    "her food, and still in her chair at ten yesterday morning, which is unheard of for her. Her "
    "clozapine card behind the clock says being poorly with any change in the smoking means a level "
    "the same day, taken before the practice closes at five. Whatever she rang about this morning, "
    "this is what I see from the spare room."
)

pt_stangill_d = _caller(
    "pt_stangill_d",
    "Karen Stangill",
    33,
    "F",
    chart=(
        "On the combined oral contraceptive; annual pill review due.",
        "Repeat medication: combined oral contraceptive.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Just booking my pill review — the chemist says there is one authorisation left, so "
        "sometime in the next few weeks would be sensible. Mornings are best; I do the nursery run "
        "after eight."
    ),
    onset="Nothing new; the yearly review is due.",
    severity="All well. Routine housekeeping.",
    history="Nothing of note; the pill for years.",
    medications="The pill, as ever.",
    context="Mornings after the nursery run suit best. My mum is Pauline Stangill, a patient here.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_stangill_d",
)

STANGILL_D_SPLIT_INTAKE = (
    "Hi. Two things. Mine first: my pill review wants booking — one authorisation left at the chemist, "
    "so the next few weeks sometime, mornings best.\n\n"
    "Second: my mum, Pauline Stangill, on the clozapine. She is under the weather — she has left her "
    "meals two days running and napped through her quiz programme, and she will downplay it if you ask "
    "her. Her clinic card says under the weather plus any smoking change means a level the same day, "
    "drawn before the practice closes at five. I promised her I would say it in those words."
)

pt_saxgill_b = _caller(
    "pt_saxgill_b",
    "Ted Saxgill",
    57,
    "M",
    chart=(
        "Bilateral ear wax, recurrent; syringing at the treatment room roughly yearly.",
        "Repeat medication: olive oil ear drops.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My ears want doing again — the wax, it is a yearly ritual. Could I go on the "
        "treatment-room list for a syringing? Whenever they can have me; I am deaf on the left till "
        "then but it is nothing new."
    ),
    onset="The usual wax, a month in the building.",
    severity="Deaf-ish on the left and cheerful about it. Routine.",
    history="Ears that make wax like a candle factory; done yearly.",
    medications="The olive oil drops, most nights.",
    context="I drive a van for a living; early or late suits. My brother Raymond is a patient here too.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_saxgill_b",
)

SAXGILL_B_SPLIT_INTAKE = (
    "Morning. My ears want doing again — the yearly wax syringing, whenever the treatment room can "
    "have me. That is my business.\n\n"
    "My brother's business is that he is not well and thinks nobody has noticed. Raymond Saxgill, on "
    "the clozapine. He has eaten next to nothing since yesterday and he fell asleep in the chair "
    "before the news, which for Raymond is unheard of. Whatever he has told the desk this morning, "
    "add that to it from me."
)

pt_tarlelund_w = _caller(
    "pt_tarlelund_w",
    "Joan Tarlelund",
    58,
    "F",
    chart=(
        "Raised cholesterol on last year's bloods; repeat fasting bloods due this spring.",
        "Repeat medication: none.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I am due my repeat cholesterol bloods — the doctor said a year, and the year is up. "
        "Could I book the early nurse slot whenever there is one? I like to get the fasting over with "
        "before my breakfast turns theoretical."
    ),
    onset="Nothing new; the year the doctor asked for is up.",
    severity="Perfectly well. It is the follow-up bloods, no more.",
    history="The cholesterol, watched not treated, this past year.",
    medications="None of my own.",
    context="Early mornings best for the fasting. My husband Derek is a patient of the clinic here.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_tarlelund_w",
)

TARLELUND_W_SPLIT_INTAKE = (
    "Hello. My own errand first: my repeat cholesterol bloods are due — the doctor said a year and the "
    "year is up — so an early nurse slot sometime, for the fasting.\n\n"
    "Now my husband. Derek Tarlelund, one of the clozapine patients. He is brewing a cold and will not "
    "say so: he has left three dinners running and was nodding off over the crossword by seven. His "
    "clinic card — I keep it with the coupons — says being poorly on top of any change in the smoking "
    "means a level the same day, drawn before the practice closes at five. He will have rung you about "
    "his own affairs; this is the part he leaves out."
)

pt_stanlund_m = _caller(
    "pt_stanlund_m",
    "Winifred Stanlund",
    80,
    "F",
    chart=(
        "Osteoporosis, on treatment; annual review with the nurse due.",
        "Repeat medication: alendronic acid weekly, calcium and vitamin D daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. My bone tablet review is due — the yearly one with the nurse — and I should "
        "like it booked before the reminder letters start stacking up. Any morning does; afternoons I "
        "am on grandmother duty."
    ),
    onset="Nothing new; the yearly review has come round.",
    severity="I am well, thank you. Routine.",
    history="The bones, on the weekly tablet three years now.",
    medications="The weekly bone tablet, and calcium with D.",
    context="Mornings free; I live with my daughter Marion Stanlund, a patient here.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_stanlund_m",
)

STANLUND_M_SPLIT_INTAKE = (
    "Good morning. For me: the yearly bone-tablet review with the nurse wants booking, any morning, no "
    "haste.\n\n"
    "For my daughter, and I shall be brief because she thinks I fuss: Marion Stanlund, on the "
    "clozapine. She is sickening for something — two dinners pushed round the plate and asleep in "
    "front of the nine o'clock news. Her monitoring card says sickening plus any change in the "
    "cigarettes means a level the same day, drawn before the practice closes at five. I have said my "
    "piece; the rest is hers to tell."
)

pt_saxlund_h = _caller(
    "pt_saxlund_h",
    "Ken Saxlund",
    66,
    "M",
    chart=(
        "Right knee osteoarthritis; steroid injection last autumn with good effect.",
        "Repeat medication: paracetamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The hospital knee people sent me a discharge letter that says my own surgery will "
        "arrange any follow-up injection if the knee stiffens again. It is stiffening. Nothing "
        "dramatic — I should just like whatever the process is set going, at the usual pace."
    ),
    onset="The knee, stiffening slowly these past weeks, as predicted.",
    severity="A stiff knee that climbs stairs under protest. Routine, per the letter.",
    history="The knee, injected last autumn, good for a year they said.",
    medications="Paracetamol when it grumbles.",
    context="Retired; I drive my wife Brenda everywhere, so I know the car park well.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_saxlund_h",
)

SAXLUND_H_SPLIT_INTAKE = (
    "Morning. My knee first: the hospital's discharge letter says the surgery arranges the follow-up "
    "injection if it stiffens again, and it is stiffening — usual pace, nothing dramatic.\n\n"
    "Now the real reason my wife let me use the phone. Brenda Saxlund, on the clozapine. She is poorly "
    "with something: off her food, tea included, and she sat down twice hoovering one room, which in "
    "forty years I have never once seen. The clinic's card lives in my wallet and it says: a change in "
    "smoking plus being poorly, level the same day, drawn before the practice closes at five."
)

pt_tarleridge_d = _caller(
    "pt_tarleridge_d",
    "Lucy Tarleridge",
    26,
    "F",
    chart=(
        "Atopic eczema, mild; flares managed with emollients and a steroid cream.",
        "Repeat medication: emollient, hydrocortisone 1% cream.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could my eczema creams go back on repeat? The chemist says the authorisation lapsed. "
        "Hands only, it is behaving otherwise — wedding stress notwithstanding. Any time this week is "
        "fine to sort it."
    ),
    onset="Nothing new; the repeat lapsed is all.",
    severity="Mild, hands only. Paperwork rather than complaint.",
    history="Eczema since school, mostly asleep these days.",
    medications="The emollient and the mild steroid cream.",
    context="Home planning my wedding, so reachable all day. Mum is Susan Tarleridge, a patient here.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_tarleridge_d",
)

TARLERIDGE_D_SPLIT_INTAKE = (
    "Hi. Mine takes ten seconds: my eczema creams want putting back on repeat, the authorisation "
    "lapsed, no rush.\n\n"
    "Mum is the real call. Susan Tarleridge, one of the clozapine patients. She is coming down with "
    "something — she has picked at her meals since Saturday and she fell asleep in the middle of my "
    "wedding spreadsheet, which honestly has never happened to anyone. She will make a joke of it if "
    "you ring her, so please take it from me instead."
)

pt_stanridge_s = _caller(
    "pt_stanridge_s",
    "Diane Stanridge",
    46,
    "F",
    chart=(
        "Mechanical low back pain, recurrent; physiotherapy completed last year with good effect.",
        "Repeat medication: naproxen 250 mg as required with omeprazole cover.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My back is talking to me again after the Christmas decorating went up to the loft — "
        "the same old mechanical thing. Could I be put through for another round of the physio "
        "exercises referral? Routine speed is fine; I know the drill by now."
    ),
    onset="A few weeks of the usual back, loft-induced.",
    severity="The familiar ache, managed. Routine referral, please.",
    history="The back, comes and goes; physio sorts it each time.",
    medications="Naproxen with the stomach tablet, when needed.",
    context="I live two doors from my sister Carol Stanridge; between us we cover the school runs.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_stanridge_s",
)

STANRIDGE_S_SPLIT_INTAKE = (
    "Hello. For me: the back has flared — the usual mechanical thing — and I would like the physio "
    "referral set going again at routine speed.\n\n"
    "For my sister: Carol Stanridge, on the clozapine, two doors from me. She is sickening for "
    "something — she has fed the kids and skipped her own tea twice this week, and she went to bed "
    "when they did on Wednesday. Her clinic card on the noticeboard says sickening plus any change in "
    "the cigarettes means a level the same day, drawn before the practice closes at five. She rang you "
    "about some errand of her own this morning and will have left all that out."
)

pt_saxroyd_w = _caller(
    "pt_saxroyd_w",
    "Moira Saxroyd",
    52,
    "F",
    chart=(
        "Hypothyroidism, stable on levothyroxine; annual bloods due.",
        "Repeat medication: levothyroxine 100 micrograms daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My yearly thyroid bloods are due — could I book the nurse for those, any day that "
        "suits the diary? And the repeat itself is fine, the chemist has months left on it. Nothing "
        "else from me."
    ),
    onset="Nothing new; the yearly bloods are due.",
    severity="Well in myself. Routine bloods.",
    history="The thyroid, steady on the same dose for years.",
    medications="Levothyroxine every morning.",
    context="I drive; my wife Sheila and I usually make one trip of our appointments.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_saxroyd_w",
)

SAXROYD_W_SPLIT_INTAKE = (
    "Hello. Mine is quick — the yearly thyroid bloods want booking with the nurse, any day.\n\n"
    "And then my wife, Sheila Saxroyd, one of the clozapine patients. She is brewing something and "
    "conducting herself as if she is not: off her food since Wednesday and she napped through the "
    "football, which in twenty years has never once happened. The clinic's card is in front of me and "
    "I will read the line out: a smoking change plus brewing something means a level the same day, "
    "drawn before the practice closes at five. She rang you herself this morning about the repeat; "
    "this is the rest of it."
)

pt_tarlesett_b = _caller(
    "pt_tarlesett_b",
    "Stan Tarlesett",
    58,
    "M",
    chart=(
        "Gastro-oesophageal reflux, stable on treatment; annual medication review due.",
        "Repeat medication: omeprazole 20 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My indigestion tablet is up for its yearly review, says the chemist, before they can "
        "issue more. Could that be booked or sorted however it is done these days? There is a month of "
        "tablets left, so no rush at all."
    ),
    onset="Nothing new; the yearly review has come round.",
    severity="The reflux behaves itself on the tablet. Routine.",
    history="The reflux, steady on the same tablet five years.",
    medications="Omeprazole, one in the morning.",
    context="I drive my sister Eileen Tarlesett to her appointments, so I am often past the practice.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_carrier_tarlesett_b",
)

TARLESETT_B_SPLIT_INTAKE = (
    "Morning. My indigestion tablet wants its yearly review before the chemist will issue more — a "
    "month of tablets left, so no rush on mine.\n\n"
    "My sister is a different matter. Eileen Tarlesett, on the clozapine. She is coming down with "
    "something: three dinners made and none of them eaten since Friday, and asleep over her library "
    "book at seven. Her clozapine card in the kitchen drawer says coming down with something plus any "
    "change in the smoking means a level the same day, drawn before the practice closes at five. She "
    "rang about her vitamin D this morning; I am ringing about her."
)

# ── the three decoys ──────────────────────────────────────────────────────────────────────────────────────
# Each SOUNDS urgent; each defuses. In the plain twin the defusing fact sits in the decoy's own call; for
# the second decoy the split twin moves it into his wife's call (aggregation must be able to CANCEL urgency
# too).

pt_torcliffe = _caller(
    "pt_torcliffe",
    "Malcolm Torcliffe",
    48,
    "M",
    chart=(
        "Bipolar affective disorder, stable on olanzapine; shared care with the community trust.",
        "Repeat medication: olanzapine 10 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I will be honest, I got myself in a state overnight and I want it settled today if "
        "you can — though hear the whole of it first.\n\n"
        "I quit smoking with the trust's push last week, and one of the clozapine fellows at the group "
        "told me stopping means same-day blood tests, and I sat up half the night sure I was walking "
        "round poisoned. But I rang the trust's nurse first thing and she was very kind and very clear: "
        "that rule is for the clozapine patients and their levels — and even for them it is the two "
        "things together, the smoking changing and being unwell with something on top. My olanzapine "
        "is not one they measure, and what I should do is book an ordinary routine review with my own "
        "doctor and "
        "mention it there.\n\n"
        "So: could I have that routine review booked, whenever is sensible? And perhaps a note that I "
        "rang and was sensible about it."
    ),
    onset="Quit smoking last week; the worry arrived overnight after the group meeting.",
    severity="No symptoms at all — I feel perfectly well. It was the worry, and the nurse has settled it.",
    history="The bipolar, stable on the same tablet for six years.",
    medications="Olanzapine at night.",
    context="Work shifts but flexible; any routine appointment works with notice.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_decoy_torcliffe",
)

pt_sudgarth = _caller(
    "pt_sudgarth",
    "Wilf Sudgarth",
    67,
    "M",
    chart=(
        "Hypertension, controlled; annual review in the autumn.",
        "Repeat medication: ramipril 10 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Now, I came over dizzy up the ladder this morning — cleaning the gutters — and had to "
        "come down and sit on the step, and my wife has made me ring before she would cook anything.\n\n"
        "But let me give you the sensible half as well, because there is one. I collected new "
        "varifocals on Monday and the optician warned me, in writing on the little card, that ladders "
        "and kerbs would swim for the first week and to expect exactly this. It settled the moment I "
        "was down, I ate my breakfast after all, and I have been right as rain since — on the flat.\n\n"
        "So my wife's instruction is: a routine look-over booked, whenever suits, and no ladders till "
        "the eyes and I have come to terms. That is the whole of it."
    ),
    onset="This morning, up the ladder; settled the moment I came down.",
    severity="Nothing since breakfast. On the flat I am right as rain.",
    history="Blood pressure, tablet-controlled for years. Never a dizzy spell before the new glasses.",
    medications="Ramipril, one in the morning.",
    context="Retired; any routine appointment suits. The gutters can wait, I am told.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_decoy_sudgarth",
)

SUDGARTH_SPLIT_INTAKE = (
    "Hello. I came over dizzy up the ladder this morning — cleaning the gutters — and had to come down "
    "and sit on the step. My wife has made me ring before she would cook anything.\n\n"
    "It settled once I was down and I have been steady on the flat since. But she wants me looked at, "
    "so: what can be done? I am home all day."
)

pt_sudgarth_w = _caller(
    "pt_sudgarth_w",
    "Elsie Sudgarth",
    65,
    "F",
    chart=(
        "Raised cholesterol, on treatment; repeat prescription current.",
        "Repeat medication: atorvastatin 20 mg nightly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Just my statin — the chemist says the repeat wants re-authorising before month's end. "
        "No rush this week; there are tablets in the drawer yet."
    ),
    onset="Nothing new; the repeat needs its yearly rubber stamp.",
    severity="Perfectly well. Paperwork only.",
    history="The cholesterol, on the night tablet three years.",
    medications="Atorvastatin at night.",
    context="Home all day; my husband Wilf is meant to be doing the gutters, which is its own story.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_decoy_carrier_sudgarth_w",
)

SUDGARTH_W_SPLIT_INTAKE = (
    "Hello. My statin repeat wants re-authorising before month's end — no rush, tablets in the drawer "
    "yet.\n\n"
    "And if my husband Wilf has rung you about his dizzy turn up the ladder, here is the piece he will "
    "have dropped: he collected new varifocals on Monday and the optician's card warns, in writing, "
    "that ladders and kerbs will swim for the first week — expect exactly this, it says. He was steady "
    "the moment he came down, ate his breakfast after all, and has been right as rain on the flat "
    "since. A routine look-over will do him nicely; there is no drama in it, whatever impression he "
    "gave."
)

pt_swinmere = _caller(
    "pt_swinmere",
    "Gwen Swinmere",
    55,
    "F",
    chart=(
        "Right knee osteoarthritis with recurrent flares; under the practice physiotherapy pathway.",
        "Repeat medication: paracetamol, topical anti-inflammatory gel.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My knee has come up like a football overnight and I can hardly put my weight through "
        "it on the stairs, so I nearly asked for the first appointment you have — but let me be fair "
        "and tell it all.\n\n"
        "The physio saw this exact knee on Tuesday. She said the flare would likely get worse before "
        "it got better this week, strapped it, and told me: ice, the gel, keep it moving gently, and "
        "book the ordinary follow-up with the practice rather than ringing round in a panic when it "
        "puffed up. Her actual words, more or less. It is puffed up on schedule, the strapping is "
        "holding, and the gel helps.\n\n"
        "So — the ordinary follow-up, please, whenever the diary allows. I promised her I would not "
        "panic and I am keeping to it, narrowly."
    ),
    onset="Overnight swelling of the same knee the physio strapped on Tuesday — predicted by her.",
    severity="Sore and swollen but exactly as forecast; the strapping holds and the gel helps.",
    history="The knee, flaring on and off for two years, physio-managed.",
    medications="Paracetamol and the gel.",
    context="Home with my feet up as instructed; any follow-up date works.",
    gold=_routine_gold(),
    source="authored:clozapine_infection_decoy_swinmere",
)

# ── every card this board authors ─────────────────────────────────────────────────────────────────────────
BOARD_CARDS: tuple[PatientCard, ...] = (
    # claimants
    pt_saxdon,
    pt_stanfold,
    pt_tarlegarth,
    pt_saxfold,
    pt_stangarth,
    pt_tarlegill,
    pt_saxgarth,
    pt_stangill,
    pt_tarleholm,
    pt_saxgill,
    pt_stanholm,
    pt_tarlelund,
    pt_saxholm,
    pt_stanlund,
    pt_tarlemead,
    pt_saxlund,
    pt_stanmead,
    pt_tarleridge,
    pt_saxridge,
    pt_stanridge,
    pt_tarleroyd,
    pt_saxroyd,
    pt_stansett,
    pt_tarlesett,
    pt_saxsett,
    # holders
    pt_stanroyd,
    pt_saxthwaite,
    pt_stanthwaite,
    pt_tarlethwaite,
    pt_saxwell,
    pt_stanwell,
    pt_tarlewell,
    pt_tarlebrook,
    pt_translund,
    pt_sudmere,
    pt_selworth,
    pt_swindale,
    pt_tormoor,
    pt_shelcroft,
    pt_snelshaw,
    pt_sibleigh,
    pt_tidstow,
    pt_tamfirth,
    pt_sudleigh,
    pt_selmoor,
    pt_swincroft,
    pt_torbourne,
    pt_shelmere,
    pt_snelworth,
    pt_tiddale,
    # kin carriers
    pt_stanfold_m,
    pt_saxfold_w,
    pt_tarlegill_s,
    pt_stangill_d,
    pt_saxgill_b,
    pt_tarlelund_w,
    pt_stanlund_m,
    pt_saxlund_h,
    pt_tarleridge_d,
    pt_stanridge_s,
    pt_saxroyd_w,
    pt_tarlesett_b,
    # decoys and the defusing carrier
    pt_torcliffe,
    pt_sudgarth,
    pt_sudgarth_w,
    pt_swinmere,
)

#: Kin declarations: the sanctioned same-surname carriers, one per family (`assert_fresh_surnames`).
KIN_OF: dict[str, str] = {
    "pt_stanfold_m": "pt_stanfold",
    "pt_saxfold_w": "pt_saxfold",
    "pt_tarlegill_s": "pt_tarlegill",
    "pt_stangill_d": "pt_stangill",
    "pt_saxgill_b": "pt_saxgill",
    "pt_tarlelund_w": "pt_tarlelund",
    "pt_stanlund_m": "pt_stanlund",
    "pt_saxlund_h": "pt_saxlund",
    "pt_tarleridge_d": "pt_tarleridge",
    "pt_stanridge_s": "pt_stanridge",
    "pt_saxroyd_w": "pt_saxroyd",
    "pt_tarlesett_b": "pt_tarlesett",
    "pt_sudgarth_w": "pt_sudgarth",
}

# ── the board skeleton (shared by both twins byte-for-byte) ───────────────────────────────────────────────
#: `(claimant, holder, provider, slot_hhmm, standing_reason, decisive_fact)` — the 25 contests as a table;
#: five returned-cancellation slots per hosted list, all afternoon, all inside the 24 h URGENT window.
_CONTEST_TABLE: tuple[tuple[str, str, str, str, str, str], ...] = (
    (
        "pt_saxdon",
        "pt_stanroyd",
        "dr_stanbrook",
        "13:40",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "stopped smoking on Sunday",
    ),
    (
        "pt_stanfold",
        "pt_saxthwaite",
        "dr_stanbrook",
        "14:00",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "given up the cigarettes since Friday",
    ),
    (
        "pt_tarlegarth",
        "pt_stanthwaite",
        "dr_stanbrook",
        "15:00",
        "Annual depot + physical health review (wait-list backfill into a returned cancellation)",
        "packed in the smoking on Monday",
    ),
    (
        "pt_saxfold",
        "pt_tarlethwaite",
        "dr_stanbrook",
        "15:20",
        "Annual anxiety review (wait-list backfill into a returned cancellation)",
        "not had a cigarette since Saturday",
    ),
    (
        "pt_stangarth",
        "pt_saxwell",
        "dr_stanbrook",
        "16:20",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "threw his cigarettes on the fire on Tuesday",
    ),
    (
        "pt_tarlegill",
        "pt_stanwell",
        "dr_tarleby",
        "13:40",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "swapped the cigarettes for one of those vapes last Wednesday",
    ),
    (
        "pt_saxgarth",
        "pt_tarlewell",
        "dr_tarleby",
        "14:00",
        "Annual depot review (wait-list backfill into a returned cancellation)",
        "quit the cigarettes cold on Monday",
    ),
    (
        "pt_stangill",
        "pt_tarlebrook",
        "dr_tarleby",
        "15:00",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "her last cigarette was last Thursday",
    ),
    (
        "pt_tarleholm",
        "pt_translund",
        "dr_tarleby",
        "15:20",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "off the cigarettes since the weekend",
    ),
    (
        "pt_saxgill",
        "pt_sudmere",
        "dr_tarleby",
        "16:20",
        "Annual review (wait-list backfill into a returned cancellation)",
        "stopped the roll-ups on Monday",
    ),
    (
        "pt_stanholm",
        "pt_selworth",
        "dr_torfold",
        "13:40",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "gave up smoking on Wednesday",
    ),
    (
        "pt_tarlelund",
        "pt_swindale",
        "dr_torfold",
        "14:00",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "put the cigarettes away on Sunday",
    ),
    (
        "pt_saxholm",
        "pt_tormoor",
        "dr_torfold",
        "15:00",
        "Annual depot + physical health review (wait-list backfill into a returned cancellation)",
        "stopped his pipe on Saturday",
    ),
    (
        "pt_stanlund",
        "pt_shelcroft",
        "dr_torfold",
        "15:20",
        "Annual anxiety review (wait-list backfill into a returned cancellation)",
        "swapped over to the nicotine patches on Monday",
    ),
    (
        "pt_tarlemead",
        "pt_snelshaw",
        "dr_torfold",
        "16:20",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "not smoked since Friday teatime",
    ),
    (
        "pt_saxlund",
        "pt_sibleigh",
        "dr_sudwell",
        "13:40",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "gave the cigarettes up on Tuesday",
    ),
    (
        "pt_stanmead",
        "pt_tidstow",
        "dr_sudwell",
        "14:00",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "finished with the cigarettes on Sunday",
    ),
    (
        "pt_tarleridge",
        "pt_tamfirth",
        "dr_sudwell",
        "15:00",
        "Annual review (wait-list backfill into a returned cancellation)",
        "packed the smokes in on Thursday",
    ),
    (
        "pt_saxridge",
        "pt_sudleigh",
        "dr_sudwell",
        "15:20",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "stopped smoking with the no-smoking week",
    ),
    (
        "pt_stanridge",
        "pt_selmoor",
        "dr_sudwell",
        "16:20",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "sworn off the cigarettes since Monday",
    ),
    (
        "pt_tarleroyd",
        "pt_swincroft",
        "dr_shelgarth",
        "13:40",
        "Annual depot review (wait-list backfill into a returned cancellation)",
        "his tobacco tin has been shut since Saturday",
    ),
    (
        "pt_saxroyd",
        "pt_torbourne",
        "dr_shelgarth",
        "14:00",
        "Annual anxiety review (wait-list backfill into a returned cancellation)",
        "come off the cigarettes this last week",
    ),
    (
        "pt_stansett",
        "pt_shelmere",
        "dr_shelgarth",
        "15:00",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "no cigarettes since a week last Sunday",
    ),
    (
        "pt_tarlesett",
        "pt_snelworth",
        "dr_shelgarth",
        "15:20",
        "Annual medication review (wait-list backfill into a returned cancellation)",
        "turned the cigarettes in on Wednesday",
    ),
    (
        "pt_saxsett",
        "pt_tiddale",
        "dr_shelgarth",
        "16:20",
        "Annual mental health review (wait-list backfill into a returned cancellation)",
        "smoked her last one on Friday night",
    ),
)

CONTESTS: tuple[BoardContest, ...] = tuple(
    BoardContest(
        claimant=claimant,
        holder=holder,
        specialty=MENTAL_HEALTH,
        provider_id=provider_id,
        slot_hhmm=slot_hhmm,
        deadline_t=17 * 60,
        stakes_tier="serious",
        standing_reason=reason,
        decisive_fact=fact,
    )
    for claimant, holder, provider_id, slot_hhmm, reason, fact in _CONTEST_TABLE
)

#: Arrival plan, identical across the twins (the split twin adds RECALL beats, which are call structure).
#: The corpus background quartet rides along; its voicemail trio carries the forced waits on three desks.
#:
#: ORDERING RULE (meshfull; reordered at integration to P08's ratified pattern): all twenty-five
#: claimants sit inside the first 26 distinct callers, so every claimant's meshfull seat is a
#: single-letter spreadsheet id. Two-letter seats (`AA`+) SORT between `A` and `B`, so their callers
#: race in the naive plan's first round ahead of the holders seated on desks A-Y — on a single-diary
#: board any contested slot serves any claimant, so a claimant in an `AA+` seat would snipe a holder's
#: slot and the naive-starvation gate (rightly) refuses. The 19 late seats carry only the decoys, the
#: kin carriers and three of the background quartet, whose golds cannot touch the contested diary.
#: Relative order within each group, every caller's mesh4 desk letter, and the authored arrival-time
#: ladder are unchanged.
ARRIVALS: tuple[tuple[str, str, int], ...] = (
    ("pt_saxdon", "C", 0),
    ("pt_stanfold", "D", 5),
    ("pt_tarlegarth", "A", 9),
    ("pt_lachaux", "B", 14),
    ("pt_saxfold", "B", 18),
    ("pt_stangarth", "C", 23),
    ("pt_tarlegill", "D", 27),
    ("pt_saxgarth", "A", 32),
    ("pt_stangill", "B", 36),
    ("pt_tarleholm", "C", 41),
    ("pt_saxgill", "D", 45),
    ("pt_stanholm", "A", 49),
    ("pt_tarlelund", "B", 54),
    ("pt_saxholm", "C", 58),
    ("pt_stanlund", "D", 63),
    ("pt_tarlemead", "A", 67),
    ("pt_saxlund", "B", 72),
    ("pt_stanmead", "C", 76),
    ("pt_tarleridge", "D", 81),
    ("pt_saxridge", "A", 85),
    ("pt_stanridge", "B", 90),
    ("pt_tarleroyd", "C", 94),
    ("pt_saxroyd", "D", 99),
    ("pt_stansett", "A", 103),
    ("pt_tarlesett", "B", 108),
    ("pt_saxsett", "C", 112),
    ("pt_torcliffe", "A", 117),
    ("pt_dunmore", "C", 121),
    ("pt_stanfold_m", "B", 126),
    ("pt_ledwidge", "A", 130),
    ("pt_saxfold_w", "D", 135),
    ("pt_sudgarth", "B", 139),
    ("pt_tarlegill_s", "B", 144),
    ("pt_stangill_d", "D", 148),
    ("pt_arundel", "D", 153),
    ("pt_saxgill_b", "B", 157),
    ("pt_tarlelund_w", "D", 162),
    ("pt_swinmere", "A", 166),
    ("pt_stanlund_m", "B", 171),
    ("pt_saxlund_h", "D", 175),
    ("pt_tarleridge_d", "B", 180),
    ("pt_stanridge_s", "D", 184),
    ("pt_saxroyd_w", "B", 189),
    ("pt_tarlesett_b", "D", 193),
    ("pt_sudgarth_w", "C", 198),
)

VOICEMAIL: tuple[str, ...] = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: One memo sentence of size cover: why one diary is carrying twenty-five afternoon lists.
MEMO_COVER_LINE = (
    "The community mental health trust's clozapine and depot monitoring lists are running out of our "
    "building this quarter while its own clinic site is rewired, so the mental health diary is carrying "
    "far more than a practice this size usually would."
)

#: The plain twin: every claimant's whole picture in their own single intake.
EVIDENCE_PLAIN: tuple[EvidenceCall, ...] = tuple(
    EvidenceCall(caller_id=claimant, about_claimant=claimant)
    for claimant, _, _, _, _, _ in _CONTEST_TABLE
)

#: `claimant -> (recall_desk, recall_at, recall_text)` — the split twin's ring-backs, one per caller.
_RECALLS: dict[str, tuple[str, int, str]] = {
    "pt_saxdon": ("A", 72, SAXDON_RECALL),
    "pt_stanfold": ("A", 88, STANFOLD_RECALL),
    "pt_tarlegarth": ("C", 81, TARLEGARTH_RECALL),
    "pt_stangarth": ("A", 95, STANGARTH_RECALL),
    "pt_saxgarth": ("C", 108, SAXGARTH_RECALL),
    "pt_tarleholm": ("A", 121, TARLEHOLM_RECALL),
    "pt_saxgill": ("A", 118, SAXGILL_RECALL),
    "pt_stanholm": ("C", 130, STANHOLM_RECALL),
    "pt_saxholm": ("A", 144, SAXHOLM_RECALL),
    "pt_tarlemead": ("C", 162, TARLEMEAD_RECALL),
    "pt_stanmead": ("A", 180, STANMEAD_RECALL),
    "pt_tarleridge": ("A", 190, TARLERIDGE_RECALL),
    "pt_saxridge": ("C", 198, SAXRIDGE_RECALL),
    "pt_tarleroyd": ("A", 211, TARLEROYD_RECALL),
    "pt_stansett": ("C", 220, STANSETT_RECALL),
    "pt_saxsett": ("A", 228, SAXSETT_RECALL),
}

#: `claimant -> the kin carrier whose call holds a piece` — the split twin's cross-desk carriers.
_CARRIER_OF: dict[str, str] = {
    "pt_stanfold": "pt_stanfold_m",
    "pt_saxfold": "pt_saxfold_w",
    "pt_tarlegill": "pt_tarlegill_s",
    "pt_stangill": "pt_stangill_d",
    "pt_saxgill": "pt_saxgill_b",
    "pt_tarlelund": "pt_tarlelund_w",
    "pt_stanlund": "pt_stanlund_m",
    "pt_saxlund": "pt_saxlund_h",
    "pt_tarleridge": "pt_tarleridge_d",
    "pt_stanridge": "pt_stanridge_s",
    "pt_saxroyd": "pt_saxroyd_w",
    "pt_tarlesett": "pt_tarlesett_b",
}


def _split_evidence() -> tuple[EvidenceCall, ...]:
    """The split twin's evidence plan: intake first, then the carrier piece and/or the one ring-back."""
    pieces: list[EvidenceCall] = []
    for claimant, _, _, _, _, _ in _CONTEST_TABLE:
        pieces.append(EvidenceCall(caller_id=claimant, about_claimant=claimant))
        carrier = _CARRIER_OF.get(claimant)
        if carrier is not None:
            pieces.append(EvidenceCall(caller_id=carrier, about_claimant=claimant))
        recall = _RECALLS.get(claimant)
        if recall is not None:
            desk, at_min, text = recall
            pieces.append(
                EvidenceCall(
                    caller_id=claimant,
                    about_claimant=claimant,
                    kind="recall",
                    at_min=at_min,
                    desk=desk,
                    text=text,
                )
            )
    return tuple(pieces)


EVIDENCE_SPLIT: tuple[EvidenceCall, ...] = _split_evidence()

DECOYS_PLAIN: tuple[Decoy, ...] = (
    Decoy(patient_id="pt_torcliffe"),
    Decoy(patient_id="pt_sudgarth"),
    Decoy(patient_id="pt_swinmere"),
)

#: The split twin's decoys: same ids; the second decoy's defusal moves into his wife's call.
DECOYS_SPLIT: tuple[Decoy, ...] = (
    Decoy(patient_id="pt_torcliffe"),
    Decoy(patient_id="pt_sudgarth", defusing_caller_id="pt_sudgarth_w"),
    Decoy(patient_id="pt_swinmere"),
)

#: The split twin's voices: claimants say only piece 1; carriers add the piece they hold; the second
#: decoy's defusal changes hands. Charts stay byte-identical — the pair gate asserts it.
SPLIT_INTAKE_OVERRIDES: dict[str, str] = {
    "pt_saxdon": SAXDON_SPLIT_INTAKE,
    "pt_stanfold": STANFOLD_SPLIT_INTAKE,
    "pt_tarlegarth": TARLEGARTH_SPLIT_INTAKE,
    "pt_saxfold": SAXFOLD_SPLIT_INTAKE,
    "pt_stangarth": STANGARTH_SPLIT_INTAKE,
    "pt_tarlegill": TARLEGILL_SPLIT_INTAKE,
    "pt_saxgarth": SAXGARTH_SPLIT_INTAKE,
    "pt_stangill": STANGILL_SPLIT_INTAKE,
    "pt_tarleholm": TARLEHOLM_SPLIT_INTAKE,
    "pt_saxgill": SAXGILL_SPLIT_INTAKE,
    "pt_stanholm": STANHOLM_SPLIT_INTAKE,
    "pt_tarlelund": TARLELUND_SPLIT_INTAKE,
    "pt_saxholm": SAXHOLM_SPLIT_INTAKE,
    "pt_stanlund": STANLUND_SPLIT_INTAKE,
    "pt_tarlemead": TARLEMEAD_SPLIT_INTAKE,
    "pt_saxlund": SAXLUND_SPLIT_INTAKE,
    "pt_stanmead": STANMEAD_SPLIT_INTAKE,
    "pt_tarleridge": TARLERIDGE_SPLIT_INTAKE,
    "pt_saxridge": SAXRIDGE_SPLIT_INTAKE,
    "pt_stanridge": STANRIDGE_SPLIT_INTAKE,
    "pt_tarleroyd": TARLEROYD_SPLIT_INTAKE,
    "pt_saxroyd": SAXROYD_SPLIT_INTAKE,
    "pt_stansett": STANSETT_SPLIT_INTAKE,
    "pt_tarlesett": TARLESETT_SPLIT_INTAKE,
    "pt_saxsett": SAXSETT_SPLIT_INTAKE,
    "pt_stanfold_m": STANFOLD_M_SPLIT_INTAKE,
    "pt_saxfold_w": SAXFOLD_W_SPLIT_INTAKE,
    "pt_tarlegill_s": TARLEGILL_S_SPLIT_INTAKE,
    "pt_stangill_d": STANGILL_D_SPLIT_INTAKE,
    "pt_saxgill_b": SAXGILL_B_SPLIT_INTAKE,
    "pt_tarlelund_w": TARLELUND_W_SPLIT_INTAKE,
    "pt_stanlund_m": STANLUND_M_SPLIT_INTAKE,
    "pt_saxlund_h": SAXLUND_H_SPLIT_INTAKE,
    "pt_tarleridge_d": TARLERIDGE_D_SPLIT_INTAKE,
    "pt_stanridge_s": STANRIDGE_S_SPLIT_INTAKE,
    "pt_saxroyd_w": SAXROYD_W_SPLIT_INTAKE,
    "pt_tarlesett_b": TARLESETT_B_SPLIT_INTAKE,
    "pt_sudgarth": SUDGARTH_SPLIT_INTAKE,
    "pt_sudgarth_w": SUDGARTH_W_SPLIT_INTAKE,
}

#: The split twin's phone-probe rewrites (`facts_overrides`): every claimant's
#: canonical onset answer opens with their smoking-cessation clause — the decisive fact itself (this
#: board's decisive facts are the cessation PHRASES, so a paraphrase would slip the exact-string gate
#: while handing a probing desk the same trigger). The split twin's probed claimant volunteers the
#: illness half only — the cessation lives in the calls, per the split structure. One medications
#: answer also volunteered the new nicotine patches (the same trigger by another door).
#:
#: Solvability re-review (coordinator tiebreak): eleven canonical severity answers close on
#: the monitoring card ("it is the card that says today, not me") — the card's rule IS the two-key union,
#: so a probed patient asserting the rule applies volunteers the assembled conclusion in paraphrase. The
#: split twin overrides those tails in-voice to the downplayed illness fragment alone. Four canonical
#: context answers presupposed an arranged same-day visit ("specially", "on purpose", "any hour today");
#: the split twin tones them to ordinary availability.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_saxdon": {
        "onset": "The cold and the heaviness started yesterday evening.",
        "severity": "A bit slow and off my food, nothing frightening. A cold coming, I would call it.",
        "context": "My sister is usually about; we are three streets away.",
    },
    "pt_stanfold": {"onset": "Off my food and sleepy since yesterday."},
    "pt_tarlegarth": {"onset": "Queasy since yesterday teatime."},
    "pt_saxfold": {"onset": "Heavy and off my food since yesterday dinner."},
    "pt_stangarth": {
        "onset": "Sneezing and off my dinner since yesterday.",
        "severity": "A cold starting, no more. Sneezes and a left dinner, nothing to write home about.",
    },
    "pt_tarlegill": {"onset": "Off my food and slow since the weekend."},
    "pt_saxgarth": {"onset": "Off my food and dog-tired since yesterday."},
    "pt_stangill": {
        "onset": "Under the weather and off my meals for two days.",
        "severity": "Off my food and napping. Nothing I would trouble a doctor over myself.",
        "context": "My daughter is off work today; she runs me about when I need it.",
    },
    "pt_tarleholm": {
        "onset": "Off my food and slow since yesterday.",
        "severity": "Slow and not eating. Up and about, though — my neighbour makes more of it than I do.",
    },
    "pt_saxgill": {
        "onset": "Eating next to nothing since yesterday.",
        "severity": "Washed out and off my food. Nothing worse — my brother does the worrying for me.",
    },
    "pt_stanholm": {
        "onset": "Run down and off my food since Tuesday evening.",
        "context": "No shift at the library today; I am only twenty minutes away.",
    },
    "pt_tarlelund": {
        "onset": "Brewing a cold since Tuesday.",
        "severity": "A coming cold and no appetite. My wife is more troubled than I am.",
    },
    "pt_saxholm": {"onset": "Full of cold and off proper meals since Sunday."},
    "pt_stanlund": {
        "onset": "Sickening and off my food since Tuesday.",
        "medications": "Clozapine at night. Nothing else on repeat.",
    },
    "pt_tarlemead": {"onset": "Peaky and off my food since Sunday."},
    "pt_saxlund": {
        "onset": "Poorly and off my food since Wednesday evening.",
        "severity": "Off my food and easily tired. Not ill in bed; my husband frets more than I do.",
    },
    "pt_stanmead": {"onset": "Off colour and off my food since Monday."},
    "pt_tarleridge": {
        "onset": "Picking at meals and sleepy since Saturday.",
        "severity": "Sleepy and picking at food. My daughter is the worried one; I feel mostly myself.",
        "context": "My daughter is home planning her wedding; she drives me when I need taking anywhere.",
    },
    "pt_saxridge": {
        "onset": "Full of cold and off my lunches since Tuesday.",
        "severity": "A cold and a poor appetite. I have had worse and said less.",
    },
    "pt_stanridge": {"onset": "Sickening and skipping meals since Tuesday."},
    "pt_tarleroyd": {"onset": "Head cold and no appetite since Sunday."},
    "pt_saxroyd": {
        "onset": "Off my food and napping since Wednesday.",
        "severity": "Off my food and sleepy. Nothing to make a song and dance about.",
    },
    "pt_stansett": {"onset": "Sickening and off breakfast three days going."},
    "pt_tarlesett": {
        "onset": "Off my dinners and sleepy since Friday.",
        "severity": "Off my food and sleepy over my book. Nothing worse than that.",
    },
    "pt_saxsett": {"onset": "Poorly and off my food since Sunday."},
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=25,
    theme_slug="clozapine_infection",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_PLAIN,
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
    size=25,
    theme_slug="clozapine_infection",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=EVIDENCE_SPLIT,
    decoys=DECOYS_SPLIT,
    cards=BOARD_CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    horizon="300",
    voicemail_callers=VOICEMAIL,
)

# Registration at import, PLAIN FIRST — the split twin seeds its calendar from the plain twin's.
register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
