"""P02 `mtx_trimethoprim`: weekly methotrexate + a new trimethoprim script ⇒ same-day FBC + review (8 contests).

The locked P02 pair: eight claimants on weekly methotrexate, each started overnight on trimethoprim (one on co-trimoxazole) by a non-institutional prescriber — the out-of-hours doctor, an online private GP — against eight routine holders sitting in the rheumatology diary's returned-cancellation slots. Assembled, the reprioritization is textbook-obvious (two folate antagonists; every claimant's clinic rule says a same-day blood count and review when that combination starts); solo, every piece reads routine — a lost monitoring book, a repeat script, a neighbour's prescription run. The ED adds nothing: the need is a blood count and a dosing review at the clinic that holds the sheet, not resuscitation. The plain twin delivers each claimant whole in their own intake; the split twin scatters the same facts across ring-backs and family/neighbour carriers on other desks.

The same-day rule itself lives on every methotrexate chart as a standing-advice line (`MTX_CHART_ADVICE`, the P01/P04-ratified pattern): in the split twin no CALL recites the rule or the five-o'clock deadline, so the route to "today, before five" is a deliberate chart cross-reference from a routine "new antibiotic" mention — without it the live gate showed a steward that assembles the interaction but prices it "urgent waitlist, seen inside a day or two" and lets the deadline lapse.
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
from clinic.environment.diaries import (
    FOLLOW_UP_HEAVY_TEMPLATE,
    RHEUMATOLOGY,
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

PLAIN_ID = "mtx_trimethoprim_plain"
SPLIT_ID = "mtx_trimethoprim_split"
PAIR_ID = "P02_mtx_trimethoprim"

# ── the practice extension: the rheumatology diary, three lists ───────────────────────────────────────────
# Two drug-monitoring lists (follow-up heavy — the day is mostly established patients on their counts) and
# one specialist list. The memo's cover line is what makes three rheumatology lists at one practice read
# true: the diary is carrying a neighbouring practice's monitoring patients this fortnight.
DR_CHADDON = board_provider(
    "dr_chaddon",
    "Dr. P. Chaddon",
    RHEUMATOLOGY,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_DRAYMEAD = board_provider(
    "dr_draymead",
    "Dr. H. Draymead",
    RHEUMATOLOGY,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_CARNHOLM = board_provider("dr_carnholm", "Dr. E. Carnholm", RHEUMATOLOGY)
NEW_PROVIDERS = (DR_CHADDON, DR_DRAYMEAD, DR_CARNHOLM)

MEMO_COVER_LINE = (
    "The rheumatology lists are carrying a neighbouring practice's drug-monitoring patients this "
    "fortnight, which is why those diaries look fuller than usual."
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
    """A carrier's or decoy's gold: NON_URGENT family medicine — a non-contested booking is the answer."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


#: The standing-advice chart line (the P01/P04-ratified pattern), identical on every methotrexate chart:
#: the clinic's own rule — same-day count, drawn at the clinic, until five — stated as filed clinical advice
#: WITHOUT naming any antibiotic, so the chart stays consistent-but-insufficient (no decisive fact) while a
#: desk that cross-references a routine "new antibiotic started" mention can assemble the case, and its
#: deadline, single-handed. Shared card objects keep it byte-identical across the twins.
MTX_CHART_ADVICE = (
    "Rheumatology clinic advice on file: a same-day full blood count and dose review at the clinic "
    "whenever a new antibiotic is started alongside the weekly methotrexate; counts are drawn at the "
    "clinic until five o'clock."
)

# ══ claimants (canonical intake = the PLAIN twin's words; the split twin overrides) ═══════════════════════
pt_chadwell = _caller(
    "pt_chadwell",
    "Nora Chadwell",
    64,
    "F",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count four weeks ago, in range; next routine monitoring bloods listed for later "
        "this month.",
        "Repeat medication: methotrexate 15 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. It is about my methotrexate — the rheumatology clinic will want me in today rather than "
        "at my usual bloods, and I shall tell you why.\n\n"
        "The out-of-hours doctor started me on trimethoprim last night, for a water infection. The rule the "
        "clinic drummed into me from the first is this: if any doctor ever starts trimethoprim while I am "
        "on the weekly methotrexate, I come in for a blood count and a review the same day it starts, "
        "because the two together can knock the blood about. They do the counts up to five — their own "
        "draw at the clinic, not one the treatment-room nurse does; I asked once and was put right.\n\n"
        "I feel well enough in myself — it is the mixing of the two tablets the clinic tests for, not "
        "anything I can feel."
    ),
    onset="Nothing new in myself. The antibiotic started with last night's dose — that is the whole of it.",
    severity=(
        "I am well — no soreness, nothing to show you. It is the trimethoprim alongside the methotrexate "
        "the clinic always tests for."
    ),
    history="The rheumatoid arthritis, on the weekly tablet for years, counted at your rheumatology clinic.",
    medications=(
        "Methotrexate on Sundays, folic acid midweek — and since last night the trimethoprim from the "
        "out-of-hours doctor."
    ),
    context="I am retired and close by. Any time today suits; my sister can walk over with me.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_chadwell_ooh_uti",
)

#: The split twin's piece 1: the SAME woman, saying only the routine half.
CHADWELL_SPLIT_INTAKE = (
    "Morning. Nothing urgent at all — I have gone and lost the little monitoring book the rheumatology "
    "clinic gave me, the one with my blood-test dates in it.\n\n"
    "Could you tell me which day they have me down for the next test? I like to arrange my sister for the "
    "walk over in good time. I feel well enough in myself, no troubles."
)

#: The split twin's piece 2: her own ring-back, later in the morning, with the rest of it.
CHADWELL_RECALL_TEXT = (
    "It is Nora Chadwell — I rang earlier about my lost monitoring book, and losing the book is exactly "
    "why the other thing went clean out of my head. The out-of-hours doctor started me on a new tablet "
    "last night, for a water infection — I have the box in front of me now and am reading it off the "
    "label: trimethoprim. With the book lost I want that written on my record with you, and would you "
    "bring my notes up while we are speaking and see the rest of the record is right? Nothing falls "
    "between two stools that way."
)

pt_cransfold = _caller(
    "pt_cransfold",
    "Douglas Cransfold",
    58,
    "M",
    chart=(
        "Psoriatic arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count five weeks ago, in range; next routine monitoring bloods listed for next "
        "month.",
        "Repeat medication: methotrexate 20 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I need to be square with the rheumatology clinic today, and I will tell you the why of it.\n\n"
        "I used one of those online doctor services yesterday evening — waterworks trouble, I did not fancy "
        "sitting it out — and the doctor there put me on trimethoprim, started last night. The folder your "
        "clinic gave me is clear as day: any new trimethoprim on top of the weekly methotrexate means a "
        "blood test and a review at the clinic the same day it starts. The counts run up to five o'clock, "
        "and it is the clinic's own draw — the folder says the count is read against the dose there and "
        "then, so a nurse taking blood somewhere else does not do it.\n\n"
        "I am fine in myself. My wife said ring you first thing, so here I am."
    ),
    onset="Nothing in myself. The new tablets went in last night — that is the change.",
    severity="Nothing to report — I feel my usual self. It is the two medicines together the clinic checks.",
    history="The psoriatic arthritis, on the weekly methotrexate a good few years, watched at your clinic.",
    medications=(
        "Methotrexate on Fridays, the folic acid midweek — and now the trimethoprim from the online doctor, "
        "since last night."
    ),
    context="I work from home this week, so any time today does me. My wife Margaret is a patient here too.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_cransfold_online_gp",
)

#: The split twin's piece 1: the SAME man, routine repeat-script register.
CRANSFOLD_SPLIT_INTAKE = (
    "Hello. Small thing — the chemist says my folic acid repeat has run out of authorisations. Could "
    "somebody sort the repeat, please?\n\n"
    "No hurry on my account; I have enough for a week or two yet."
)

pt_drayfold = _caller(
    "pt_drayfold",
    "Cecily Drayfold",
    71,
    "F",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count three weeks ago, in range; next routine monitoring bloods listed for later "
        "this month.",
        "Repeat medication: methotrexate 17.5 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor came to me first thing for a bladder infection and has started me "
        "on trimethoprim — my neighbour Mr Dunbrook has already fetched it from the chemist, bless him.\n\n"
        "Now, my daughter read my rheumatology card down the phone to me and it says, in the clinic's own "
        "writing: if any new trimethoprim is started alongside the weekly methotrexate, the clinic does a "
        "blood test the same day, before they close at five. So I am ringing to say the tablets have "
        "started and the clinic will want me in today.\n\n"
        "I am comfortable in myself, only the stinging when I spend a penny, and the tablets are for that."
    ),
    onset="The bladder trouble since yesterday; the trimethoprim from this morning's visit.",
    severity="Only the stinging, and that is what the antibiotic is for. Nothing else at all.",
    history="The rheumatoid arthritis, the weekly tablet for a long while, counted at your clinic.",
    medications=(
        "Methotrexate on Mondays, folic acid on Thursdays — and the trimethoprim from this morning, which "
        "Mr Dunbrook collected for me."
    ),
    context="I am at home all day. My neighbour Mr Dunbrook does my prescription run.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_drayfold_ooh_visit",
)

#: The split twin's piece 1: the SAME woman, a chemist paperwork query and nothing else.
DRAYFOLD_SPLIT_INTAKE = (
    "Hello. The chemist has queried one of my repeats — he says the surgery has my folic acid down at the "
    "old strength and would somebody look at it. Could that be tidied up, please?\n\n"
    "There is no rush; I have plenty in the drawer. I am comfortable in myself."
)

#: The split twin's piece 3: her own ring-back — the clinic rule, without naming the tablet.
DRAYFOLD_RECALL_TEXT = (
    "It is Mrs Drayfold again — my daughter told me to ring back and say it properly. The out-of-hours "
    "doctor came to me first thing and started me on a new antibiotic for a bladder infection; I could "
    "not tell you the name, the box is in the kitchen and the print is tiny. My daughter says my "
    "rheumatology card names one antibiotic in particular to look out for, and neither of us could swear "
    "whether mine is the one the card means. So I am reporting a new antibiotic, and you have better "
    "eyes for these things than we do."
)

pt_chadgill = _caller(
    "pt_chadgill",
    "Stanley Chadgill",
    76,
    "M",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count six weeks ago, in range; next routine monitoring bloods listed for later "
        "this month.",
        "Repeat medication: methotrexate 10 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My daughter says I am to tell you the whole thing in one go, so bear with me.\n\n"
        "The out-of-hours doctor saw me last night for a waterworks infection and started me on "
        "trimethoprim. There is a sheet from the rheumatology clinic on my fridge door, and it says in big "
        "letters: trimethoprim and the weekly methotrexate do not mix — blood count and review at the "
        "clinic the same day it starts. The clinic takes bloods up to five o'clock.\n\n"
        "So that is me told, and now you are told. I feel right enough in myself, maybe a bit washed out, "
        "but I slept poorly with the trips to the bathroom."
    ),
    onset="The waterworks since the weekend, worse yesterday; the trimethoprim from last night.",
    severity="A bit washed out from broken sleep, nothing worse. No soreness anywhere new.",
    history="The rheumatoid arthritis, on the weekly tablet ten years or more, counted at your clinic.",
    medications=(
        "Methotrexate on Saturdays, folic acid midweek — and the trimethoprim from the out-of-hours "
        "doctor, started last night."
    ),
    context="My daughter drives me; she has said she can do any time today if the clinic wants me.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_chadgill_ooh_uti",
)

#: The split twin's piece 1: the SAME man, a repeat running low.
CHADGILL_SPLIT_INTAKE = (
    "Morning. I am ringing about my methotrexate repeat — the box is down to two, and the chemist likes a "
    "few days' notice. Could the repeat go through this week?\n\n"
    "No panic at this end; my daughter collects on her way over."
)

#: The split twin's piece 2: his ring-back, at his daughter's insistence.
CHADGILL_RECALL_TEXT = (
    "It is Stanley Chadgill again — my daughter's orders, she says I buried the lead this morning. The "
    "out-of-hours doctor saw me last night for a waterworks infection and started me on trimethoprim. My "
    "daughter keeps my medicine list taped inside the cupboard and she wants the surgery's list matching "
    "hers, so that is the whole errand: trimethoprim, started last night. Would somebody bring my list "
    "up on the screen and see it goes on, so I can tell her the two lists match?"
)

pt_caldfold = _caller(
    "pt_caldfold",
    "Dorothy Caldfold",
    69,
    "F",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count four weeks ago, in range; next routine monitoring bloods listed for later "
        "this month.",
        "Repeat medication: methotrexate 15 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I went up to the out-of-hours place yesterday evening with a water infection and they have "
        "put me on trimethoprim — first one taken with my tea last night.\n\n"
        "My rheumatology sheet is pinned up by the calendar and it could not be plainer: a new trimethoprim "
        "on top of the weekly methotrexate means a blood test at the clinic the same day it starts. They "
        "told me the same thing to my face when they started the methotrexate. The bloods run to five "
        "o'clock.\n\n"
        "I am a little washed out this morning but nothing you could hang a hat on. It is the two tablets "
        "together the clinic will want to see about."
    ),
    onset="The water infection since midweek; the trimethoprim from yesterday evening.",
    severity="A bit washed out, no more. It is the tablets together, not how I feel, that wants the test.",
    history="The rheumatoid arthritis, on the weekly methotrexate a long while, counted at your clinic.",
    medications=(
        "Methotrexate on Sundays, the folic acid midweek — and the trimethoprim from the out-of-hours "
        "place, since yesterday evening."
    ),
    context=(
        "I am home all day. My friend Mrs Chadthwaite and I do the market run together on Thursdays — she "
        "would drop me at the clinic without a second thought."
    ),
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_caldfold_ooh_centre",
)

#: The split twin's piece 1: the SAME woman, only the routine half of it.
CALDFOLD_SPLIT_INTAKE = (
    "Hello. Only my folic acid repeat, please — the chemist says there is one authorisation left and to "
    "get it renewed before it runs dry.\n\n"
    "I am a little washed out this week but nothing to make a fuss over. Whenever it suits."
)

pt_draygarth = _caller(
    "pt_draygarth",
    "Edwin Draygarth",
    62,
    "M",
    chart=(
        "Psoriatic arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count five weeks ago, in range; next routine monitoring bloods listed for next "
        "month.",
        "Repeat medication: methotrexate 22.5 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The night doctor at the out-of-hours saw me late on for a water infection and has given "
        "me co-trimoxazole — Septrin, he called it as well. First dose last night.\n\n"
        "My clinic book from rheumatology names that exact one: co-trimoxazole and the weekly methotrexate "
        "are not to run together without a same-day blood count and a review at the clinic. It is "
        "underlined twice in the book. The clinic does the counts till five.\n\n"
        "I feel ordinary in myself — the book is why I am ringing, not how I feel."
    ),
    onset="The water infection over a couple of days; the co-trimoxazole from last night.",
    severity="Nothing in myself worth the name. It is the combination the clinic book flags.",
    history="The psoriatic arthritis, on the weekly methotrexate for years, counted at your clinic.",
    medications=(
        "Methotrexate on Wednesdays, folic acid at the weekend — and the co-trimoxazole from the night "
        "doctor, started last night."
    ),
    context="Semi-retired; I can be at the clinic inside twenty minutes any time today.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_draygarth_cotrimoxazole",
)

#: The split twin's piece 1: the SAME man, a plain repeat request.
DRAYGARTH_SPLIT_INTAKE = (
    "Morning. Could I get my methotrexate and folic acid repeats put through, please? The chemist will "
    "text me when they are ready.\n\n"
    "Nothing else from me — all steady at this end."
)

#: The split twin's piece 2: his ring-back once he has dug the clinic book out.
DRAYGARTH_RECALL_TEXT = (
    "It is Edwin Draygarth — I rang earlier about repeats, and my wife has just unpacked the bag from "
    "the night chemist and told me off. The night doctor at the out-of-hours gave me a course late on, "
    "for a water infection, first dose last night — and I never thought to mention it when I rang about "
    "the repeats. My wife has the packet in her hand and is reading it out to me: co-trimoxazole — "
    "Septrin, it says underneath. So it is mentioned now, and would you see my list on your screen is "
    "put straight while you have me?"
)

pt_carnfold = _caller(
    "pt_carnfold",
    "Winifred Carnfold",
    74,
    "F",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count four weeks ago, in range; next routine monitoring bloods listed for later "
        "this month.",
        "Repeat medication: methotrexate 12.5 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, sweetheart. The doctor who rang me back from the out-of-hours in the night has started me on "
        "trimethoprim for a water infection — my grandson fetched it from the all-night chemist.\n\n"
        "When they put me on the methotrexate, the rheumatology clinic sat me down and said: if ever a "
        "doctor starts you on trimethoprim, you come in for a blood count the same day, no waiting for "
        "your usual test. It is written on my card in red. The clinic sees people up to five.\n\n"
        "I am quite well in myself, only cross about the waterworks."
    ),
    onset="The waterworks since yesterday; the trimethoprim from the small hours.",
    severity="Quite well, only the stinging. It is the card's rule that wants me in, not a complaint.",
    history="The rheumatoid arthritis, the weekly tablet for a good ten years, counted at your clinic.",
    medications=(
        "Methotrexate on Tuesdays, folic acid on Fridays — and the trimethoprim my grandson fetched in the "
        "night."
    ),
    context="My grandson stops by after his shift; he can run me up to the clinic any time today.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_carnfold_ooh_callback",
)

#: The split twin's piece 1: the SAME woman, checking a repeat has gone through.
CARNFOLD_SPLIT_INTAKE = (
    "Hello, sweetheart. Only checking my repeat went across to the chemist — my grandson is calling in for it "
    "after his shift and I did not want him standing there for nothing.\n\n"
    "I am quite well in myself, no troubles to report."
)

#: The split twin's piece 2: her ring-back after finding the clinic card.
CARNFOLD_RECALL_TEXT = (
    "It is Winifred Carnfold again, dear. I rang earlier and never said a word about the night's "
    "excitement, which is the way round my head works these days. The out-of-hours doctor started me on "
    "an antibiotic in the night, for a water infection — my grandson fetched it from the all-night "
    "chemist, and he has just read the box out to me: trimethoprim. He says the surgery keeps the list "
    "and the list should be right, so would you look at what you have down for me and put it on? Then "
    "he can stop nagging."
)

pt_draybrook = _caller(
    "pt_draybrook",
    "Mabel Draybrook",
    67,
    "F",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Last full blood count three weeks ago, in range; next routine monitoring bloods listed for later "
        "this month.",
        "Repeat medication: methotrexate 15 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Good morning. The out-of-hours doctor saw me at the centre first thing — water infection — and I "
        "have come away with trimethoprim, first dose taken in the car park, on his say-so.\n\n"
        "He asked what else I take, and when I said the weekly methotrexate he said, word for word: your "
        "own surgery's rheumatology clinic will want a blood count and a review today, the same day it "
        "starts — ring them the moment they open. Their bloods run to five o'clock. So here I am, doing as "
        "bid.\n\n"
        "In myself I am fine — the hay fever has started early this year, but that is all it is."
    ),
    onset="The water infection since yesterday; the trimethoprim from first thing this morning.",
    severity="Fine in myself. The hay fever is off early this year, which is a nuisance and no more.",
    history="The rheumatoid arthritis, on the weekly methotrexate for years, counted at your clinic.",
    medications=(
        "Methotrexate on Thursdays, folic acid on Mondays — and the trimethoprim from the out-of-hours "
        "centre, first dose this morning."
    ),
    context="My husband drives; we are free all day and can come whenever the clinic says.",
    gold=board_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_draybrook_ooh_centre",
)

#: The split twin's piece 1: the SAME woman, booking the nurse and nothing more.
DRAYBROOK_SPLIT_INTAKE = (
    "Good morning. Could I book in with the nurse to have my ears looked at? The left one wants syringing "
    "again — same as every spring, and no hurry about it.\n\n"
    "Otherwise all is well at this end."
)

#: The split twin's piece 2: her ring-back, passing on the out-of-hours doctor's exact words.
DRAYBROOK_RECALL_TEXT = (
    "It is Mabel Draybrook — I rang about my ears earlier and my husband has been on at me since: I never "
    "mentioned this morning's business. The out-of-hours doctor saw me at the centre first thing for a "
    "water infection and started me on trimethoprim — it is written on the chemist's bag, plain as "
    "anything — first dose in the car park. My husband says the surgery would rather hear it from me "
    "than read it in a letter next month, so here I am saying it. Would you put it on my notes now, "
    "while we are speaking?"
)

# ══ holders (never call; the intake is what they say if a desk rings them) ════════════════════════════════
pt_cransholm = _caller(
    "pt_cransholm",
    "Albert Cransholm",
    78,
    "M",
    chart=(
        "Gout, on allopurinol, no flare in over a year; annual rheumatology review due.",
        "Repeat medication: allopurinol 300 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is right, my yearly gout review is this afternoon. My grandson has swapped a shift at the "
        "depot to run me in, so the time they gave me suits us very well."
    ),
    onset="Nothing new; it is the yearly look-over.",
    severity="I am well — the foot has behaved itself all year on the tablet.",
    history="The gout, settled on allopurinol these last few years, reviewed yearly at the clinic.",
    medications="Allopurinol, one a day, regular as the post.",
    context="My grandson swapped a shift at the depot to drive me in this afternoon.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_gout_annual",
)

pt_caldgarth = _caller(
    "pt_caldgarth",
    "Vera Caldgarth",
    70,
    "F",
    chart=(
        "Rheumatoid arthritis, stable on hydroxychloroquine; annual rheumatology review with the eye-check "
        "paperwork due.",
        "Repeat medication: hydroxychloroquine 200 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, I am in this afternoon for my yearly review — they do the eye-check form at the same visit, "
        "and the opticians are waiting on it. My daughter has taken the afternoon off specially."
    ),
    onset="Nothing new; it is the yearly review and the eye form.",
    severity="I am well — the joints have been kind this year.",
    history="The rheumatoid arthritis, steady on the hydroxychloroquine, seen yearly at the clinic.",
    medications="The hydroxychloroquine, one a day.",
    context="My daughter has taken the afternoon off work to bring me in; the opticians want the form back.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_hcq_annual",
)

pt_chadmead = _caller(
    "pt_chadmead",
    "Ronald Chadmead",
    74,
    "M",
    chart=(
        "Polymyalgia rheumatica, on a reducing course of prednisolone; taper review due at the "
        "rheumatology clinic.",
        "Repeat medication: prednisolone per taper sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "That is me — the steroid taper review, this afternoon. My neighbour has arranged his day around "
        "the lift, and I would like the next step of the taper settled before my sister comes to stay."
    ),
    onset="Nothing new; the shoulders are fine on the present dose.",
    severity="I am well. It is the planned look at the taper, nothing more.",
    history="The polymyalgia, much better on the steroid, being brought down step by step at the clinic.",
    medications="The prednisolone, per the sheet on the sideboard.",
    context="My neighbour has arranged his day around driving me in; my sister comes to stay at the weekend.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_pmr_taper",
)

pt_draywell = _caller(
    "pt_draywell",
    "Joyce Draywell",
    66,
    "F",
    chart=(
        "Rheumatoid arthritis, stable on sulfasalazine; drug-monitoring review due at the rheumatology "
        "clinic.",
        "Repeat medication: sulfasalazine 500 mg twice daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my sulfasalazine check is this afternoon. I swapped my shift at the garden centre to make "
        "it, so the time works out just right for me."
    ),
    onset="Nothing new; it is the planned tablet check.",
    severity="I am well — the tablets suit me and the joints are steady.",
    history="The rheumatoid arthritis, settled on sulfasalazine, checked at the clinic on schedule.",
    medications="The sulfasalazine, morning and night.",
    context="I swapped my shift at the garden centre to be free this afternoon.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_ssz_monitoring",
)

pt_carnridge = _caller(
    "pt_carnridge",
    "Harold Carnridge",
    81,
    "M",
    chart=(
        "Osteoporosis, on alendronic acid; bone-scan results discussion due at the rheumatology clinic.",
        "Repeat medication: alendronic acid weekly, calcium and vitamin D daily.",
        "No known drug allergies.",
    ),
    intake=(
        "That is right, I am in this afternoon to go over my bone-scan results. My son is driving over "
        "from town for it — he wants to hear what they say with his own ears."
    ),
    onset="Nothing new; it is the results talk.",
    severity="I am well in myself. No falls, no trouble — we are just to hear the numbers.",
    history="The thin bones, on the weekly tablet for them; scanned and reviewed at the clinic.",
    medications="The weekly bone tablet, and the calcium with the vitamin D.",
    context="My son is driving over from town specially to sit in on the results.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_dexa_results",
)

pt_chadroyd = _caller(
    "pt_chadroyd",
    "Elsie Chadroyd",
    72,
    "F",
    chart=(
        "Rheumatoid arthritis, stable on hydroxychloroquine; annual rheumatology review due.",
        "Repeat medication: hydroxychloroquine 200 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my yearly arthritis review is this afternoon. The warden here has booked me onto the "
        "minibus for it — that is all arranged, so the time I have suits."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="I am well — the hands are no worse than last year.",
    history="The rheumatoid arthritis, steady on the tablet, reviewed once a year at the clinic.",
    medications="The hydroxychloroquine, one a day.",
    context="The warden has booked the sheltered-housing minibus around my appointment time.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_ra_annual",
)

pt_cransgill = _caller(
    "pt_cransgill",
    "Percy Cransgill",
    69,
    "M",
    chart=(
        "Ankylosing spondylitis, long-standing, on regular naproxen; annual rheumatology review due.",
        "Repeat medication: naproxen 500 mg twice daily with omeprazole cover.",
        "No known drug allergies.",
    ),
    intake=(
        "That is me — the yearly back review, this afternoon. I have booked the whole day off work for "
        "it, first leave I have taken since the new job started."
    ),
    onset="Nothing new; the back is its usual stiff self in the mornings and no worse.",
    severity="I am well. It is the planned yearly look, nothing has changed.",
    history="The ankylosing spondylitis, thirty years of it, reviewed yearly at the clinic.",
    medications="The naproxen morning and night, and the stomach tablet alongside.",
    context="I booked the whole day off work for the appointment — first leave since the new job.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_as_annual",
)

pt_calddon = _caller(
    "pt_calddon",
    "Muriel Calddon",
    75,
    "F",
    chart=(
        "Fibromyalgia, on amitriptyline at night; follow-up review due at the rheumatology clinic.",
        "Repeat medication: amitriptyline 20 mg at night.",
        "No known drug allergies.",
    ),
    intake=(
        "Yes, my follow-up is this afternoon — we are to see how the new bedtime dose has settled in. My "
        "cousin has arranged her afternoon around fetching me there and back."
    ),
    onset="Nothing new; it is the planned follow-up on the dose.",
    severity="I am much as usual — sleeping better on the new dose, which is what we are to talk over.",
    history="The fibromyalgia, some years now, seen at the clinic to keep the tablets right.",
    medications="The amitriptyline at bedtime.",
    context="My cousin has arranged her afternoon around the lift there and back.",
    gold=_holder_gold(RHEUMATOLOGY),
    source="authored:mtx_trimethoprim_holder_fibro_followup",
)

# ══ carriers (dual-purpose callers: their own routine matter, and — in the split twin — the fact) ═════════
pt_cransfold_m = _caller(
    "pt_cransfold_m",
    "Margaret Cransfold",
    56,
    "F",
    chart=(
        "Asthma, well controlled on a combination inhaler; annual asthma review due.",
        "Repeat medication: combination inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could I get my yearly asthma review booked in with the nurse? The reminder letter came "
        "last week and I keep not ringing.\n\n"
        "Any day works — I only need a bit of notice for the diary."
    ),
    onset="Nothing new — it is the yearly review the letter asks for.",
    severity="The chest is fine; the inhaler does its job.",
    history="The asthma, steady for years on the same inhaler.",
    medications="The purple inhaler morning and night, and the blue one hardly ever.",
    context="I am about the house most days; my husband Douglas is a patient here as well.",
    gold=_routine_gold(),
    source="authored:mtx_trimethoprim_carrier_cransfold_wife",
)

#: The split twin's carrier piece: the same routine matter, plus the fact only she thinks to pass on.
CRANSFOLD_M_SPLIT_INTAKE = (
    "Hello. Could I get my yearly asthma review booked in with the nurse? The reminder letter came last "
    "week and I keep not ringing. Any day works.\n\n"
    "Oh — and while I have you: my husband Douglas used one of those online doctor services yesterday "
    "evening for waterworks trouble, and the doctor there started him on trimethoprim last night. He "
    "will have rung you about his repeats this morning and said nothing of it, knowing him, so could it "
    "go on his record from me — the online people never send their notes on."
)

pt_dunbrook = _caller(
    "pt_dunbrook",
    "Leonard Dunbrook",
    73,
    "M",
    chart=(
        "Hypertension, controlled on ramipril; bloods and review annually.",
        "Repeat medication: ramipril 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My blood-pressure tablet repeat is due — ramipril — could that be put through to the "
        "chemist, please?\n\n"
        "No rush at all; I am walking down there tomorrow anyway."
    ),
    onset="Nothing new — the repeat is simply due.",
    severity="I am well. It is housekeeping, not a complaint.",
    history="The blood pressure, steady on the same tablet for years.",
    medications="Ramipril, one in the morning.",
    context="I am retired; I do the prescription run for my neighbour Mrs Drayfold as well.",
    gold=_routine_gold(),
    source="authored:mtx_trimethoprim_carrier_dunbrook_neighbour",
)

#: The split twin's carrier piece: his own repeat, plus what he fetched from the chemist this morning.
DUNBROOK_SPLIT_INTAKE = (
    "Morning. My blood-pressure tablet repeat is due — ramipril — could that be put through to the "
    "chemist, please? No rush; I am walking down tomorrow anyway.\n\n"
    "While I am on: I do the prescription run for my neighbour Mrs Drayfold, and this morning I fetched "
    "her a course of trimethoprim the out-of-hours doctor put her on — he came out to her first thing for "
    "a bladder infection. The out-of-hours never let the surgery know, so could it go on her notes that "
    "the new one has started? The bag is on my table and that is the name printed on it: trimethoprim."
)

pt_chadthwaite = _caller(
    "pt_chadthwaite",
    "Janet Chadthwaite",
    61,
    "F",
    chart=(
        "Hypertension, on amlodipine; blood-pressure check due this month.",
        "Repeat medication: amlodipine 5 mg daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I am due my blood-pressure check — the machine at the chemist keeps telling me different "
        "numbers and I would sooner the nurse did it properly. Could I book that in?\n\n"
        "Any day this fortnight suits."
    ),
    onset="Nothing new — the check is due and the chemist's machine is not to be trusted.",
    severity="I feel fine; it is only the routine check.",
    history="The blood pressure, on one tablet, checked at the surgery on schedule.",
    medications="Amlodipine, one in the morning.",
    context="I am flexible — my friend Mrs Caldfold and I do the market run on Thursdays.",
    gold=_routine_gold(),
    source="authored:mtx_trimethoprim_carrier_chadthwaite_friend",
)

#: The split twin's carrier piece: her own check, plus what her friend told her over the fence.
CHADTHWAITE_SPLIT_INTAKE = (
    "Hello. I am due my blood-pressure check — could I book that in with the nurse? The chemist's machine "
    "keeps telling me different numbers. Any day this fortnight.\n\n"
    "And one thing more, while you have me: my friend Mrs Caldfold — Dorothy — went up to the out-of-hours "
    "place yesterday evening with a water infection and they put her on trimethoprim. She will not have "
    "made a fuss when she rang you — she never does — so I said I would make sure the new one was "
    "written down on her notes."
)

pt_draysett = _caller(
    "pt_draysett",
    "Karen Draysett",
    44,
    "F",
    chart=(
        "Asthma, mild, on a preventer inhaler; repeat prescriptions in order.",
        "Repeat medication: beclometasone inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. Could I order my inhaler repeats, please — the preventer and the blue one? The app would not "
        "let me put it through for some reason.\n\n"
        "That is all from me, no dramas."
    ),
    onset="Nothing new — the app fell over, that is all.",
    severity="I am fine; the inhalers are routine.",
    history="Mild asthma since school, steady on the same inhalers.",
    medications="The brown preventer morning and night, the blue one now and then.",
    context="I work in town; my mum, Mrs Cransbrook, is a patient here — I keep half an eye on her.",
    gold=_routine_gold(),
    source="authored:mtx_trimethoprim_carrier_draysett_daughter",
)

#: The split twin's carrier piece: her inhalers, plus the fact that defuses her mother's morning call.
DRAYSETT_SPLIT_INTAKE = (
    "Hi. Could I order my inhaler repeats, please — the preventer and the blue one? The app would not let "
    "me put it through.\n\n"
    "Also — my mum, Ivy Cransbrook, will have rung you this morning in a state about her arthritis tablets "
    "and that antibiotic she had. For the record: she finished the course a fortnight ago, the rheumatology "
    "clinic took her monitoring bloods on Friday, and they rang her to say everything was in range. She "
    "heard something on the radio about medicines clashing and it set her off. She only actually needs her "
    "repeat sorted — please do not let her talk anyone into anything grander."
)

# ══ decoys (sound urgent; the correct resolution is NOT a bump) ═══════════════════════════════════════════
pt_croftby = _caller(
    "pt_croftby",
    "Iris Croftby",
    59,
    "F",
    chart=(
        "Osteoarthritis of the knees; flares managed with a written self-care plan from her GP.",
        "Repeat medication: ibuprofen 400 mg as required, with food.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My knee has swelled up again after a weekend in the garden and my sister says a swollen "
        "joint wants seeing today, no argument.\n\n"
        "But I will be honest with you — it did exactly this last spring, the doctor gave me a written "
        "plan, rest and ice and the tablets with food, and it settled inside the week. I started the same "
        "plan last night and it is already easing. So I would like a routine look-over booked, whenever "
        "there is one going, and my sister can stand down."
    ),
    onset="Since the weekend in the garden — the same knee, the same way as last spring.",
    severity="Puffy and stiff, already easing on the written plan. I can get about the house fine.",
    history="The knees, years of wear; one flare last spring that settled on the plan inside the week.",
    medications="Ibuprofen with food when it flares, per the plan.",
    context="Retired; any day suits for the look-over.",
    gold=_routine_gold(),
    source="authored:mtx_trimethoprim_decoy_knee_flare_defused",
)

pt_cransbrook = _caller(
    "pt_cransbrook",
    "Ivy Cransbrook",
    77,
    "F",
    chart=(
        "Rheumatoid arthritis, on weekly methotrexate with folic acid; drug monitoring at the practice's "
        "rheumatology clinic.",
        MTX_CHART_ADVICE,
        "Recent urinary infection, treated with a standard course, now resolved.",
        "Full blood count taken at the rheumatology clinic on Friday: in range; results given to the "
        "patient by phone.",
        "Repeat medication: methotrexate 7.5 mg once weekly, folic acid 5 mg weekly.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I heard a programme on the radio about medicines clashing and it has put the wind up me — "
        "I take the weekly methotrexate, and I had that antibiotic for my water infection, and the man on "
        "the radio said the two are a bad mix and people end up poorly. My daughter says I am to calm "
        "down, but I want somebody to tell me straight.\n\n"
        "Now, to be fair: I finished the course a fortnight ago, and the rheumatology clinic took my "
        "bloods on Friday and rang to say everything was in range. So the nurse has already had a look at "
        "me since, as my daughter keeps saying.\n\n"
        "Really I suppose it is my repeat I need sorting — the folic acid — but I did want to say my piece."
    ),
    onset="Nothing new — the infection cleared a fortnight ago; it was the radio that set me off.",
    severity="I am well in myself. The bloods on Friday were in range — the clinic rang me themselves.",
    history="The rheumatoid arthritis, on a small weekly dose for years, counted at your clinic.",
    medications="Methotrexate on Sundays, folic acid midweek. The antibiotic course finished a fortnight ago.",
    context="My daughter Karen keeps half an eye on me; she says I am not to let the radio run my life.",
    gold=_routine_gold(),
    source="authored:mtx_trimethoprim_decoy_finished_course_defused",
)

#: The split twin's decoy intake: the SAME woman, alarm WITHOUT the defusing half (her daughter carries it).
CRANSBROOK_SPLIT_INTAKE = (
    "Hello. I heard a programme on the radio about medicines clashing and it has put the wind up me — I "
    "take the weekly methotrexate for my arthritis, and I had that antibiotic for my water infection — "
    "trimethoprim, the same one the man on the radio named. He said the two are a bad mix and people end "
    "up poorly. I think somebody ought to see me today and make sure, bloods and all.\n\n"
    "My daughter says I am to calm down, but she is at work and the radio man sounded very sure of himself."
)

# ── the board skeleton (shared by both twins byte-for-byte) ───────────────────────────────────────────────
_DEADLINE_T = (
    17 * 60
)  # the clinic's bloods run to five — stated in every PLAIN intake and, for both twins, on every
# methotrexate chart's standing-advice line (MTX_CHART_ADVICE); the split twin's CALLS never recite
# the rule or the deadline, so the split route to "today, before five" is the chart.

CONTESTS = (
    BoardContest(
        claimant="pt_chadwell",
        holder="pt_cransholm",
        specialty=RHEUMATOLOGY,
        provider_id="dr_chaddon",
        slot_hhmm="13:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual gout review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
    BoardContest(
        claimant="pt_cransfold",
        holder="pt_caldgarth",
        specialty=RHEUMATOLOGY,
        provider_id="dr_chaddon",
        slot_hhmm="14:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual review + optician eye-check form (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
    BoardContest(
        claimant="pt_drayfold",
        holder="pt_chadmead",
        specialty=RHEUMATOLOGY,
        provider_id="dr_chaddon",
        slot_hhmm="15:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Steroid taper review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
    BoardContest(
        claimant="pt_chadgill",
        holder="pt_draywell",
        specialty=RHEUMATOLOGY,
        provider_id="dr_draymead",
        slot_hhmm="13:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Sulfasalazine monitoring review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
    BoardContest(
        claimant="pt_caldfold",
        holder="pt_carnridge",
        specialty=RHEUMATOLOGY,
        provider_id="dr_draymead",
        slot_hhmm="15:00",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Bone-scan results discussion (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
    BoardContest(
        claimant="pt_draygarth",
        holder="pt_chadroyd",
        specialty=RHEUMATOLOGY,
        provider_id="dr_draymead",
        slot_hhmm="16:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual rheumatoid arthritis review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="co-trimoxazole",
    ),
    BoardContest(
        claimant="pt_carnfold",
        holder="pt_cransgill",
        specialty=RHEUMATOLOGY,
        provider_id="dr_carnholm",
        slot_hhmm="14:00",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual ankylosing spondylitis review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
    BoardContest(
        claimant="pt_draybrook",
        holder="pt_calddon",
        specialty=RHEUMATOLOGY,
        provider_id="dr_carnholm",
        slot_hhmm="15:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Fibromyalgia dose follow-up (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="trimethoprim",
    ),
)

#: Plain twin: each decoy's own single call carries alarm AND defusal.
DECOYS_PLAIN = (Decoy(patient_id="pt_croftby"), Decoy(patient_id="pt_cransbrook"))
#: Split twin: Mrs Cransbrook's defusing fact rides her daughter's call instead (§6 — aggregation must be
#: able to CANCEL urgency, not only create it). Same decoy ids as the plain twin (the pair gate's claim).
DECOYS_SPLIT = (
    Decoy(patient_id="pt_croftby"),
    Decoy(patient_id="pt_cransbrook", defusing_caller_id="pt_draysett"),
)

BOARD_CARDS = (
    pt_chadwell,
    pt_cransfold,
    pt_drayfold,
    pt_chadgill,
    pt_caldfold,
    pt_draygarth,
    pt_carnfold,
    pt_draybrook,
    pt_cransholm,
    pt_caldgarth,
    pt_chadmead,
    pt_draywell,
    pt_carnridge,
    pt_chadroyd,
    pt_cransgill,
    pt_calddon,
    pt_cransfold_m,
    pt_dunbrook,
    pt_chadthwaite,
    pt_draysett,
    pt_croftby,
    pt_cransbrook,
)

#: Arrival plan, identical across the twins (the split adds RECALL beats, which is call structure). The
#: corpus background quartet rides along and carries the voicemail trio (forced waits, §15(5)).
ARRIVALS = (
    ("pt_chadwell", "A", 0),
    ("pt_lachaux", "B", 6),
    ("pt_cransfold", "B", 14),
    ("pt_drayfold", "C", 22),
    ("pt_croftby", "D", 28),
    ("pt_chadgill", "D", 34),
    ("pt_dunmore", "C", 40),
    ("pt_caldfold", "A", 46),
    ("pt_dunbrook", "A", 54),
    ("pt_draygarth", "B", 60),
    ("pt_cransbrook", "C", 66),
    ("pt_ledwidge", "A", 72),
    ("pt_carnfold", "C", 78),
    ("pt_cransfold_m", "D", 84),
    ("pt_chadthwaite", "C", 90),
    ("pt_draybrook", "D", 96),
    ("pt_arundel", "D", 102),
    ("pt_draysett", "B", 110),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

#: One family carrier shares a claimant's surname: Margaret Cransfold rings about her own asthma review
#: and (in the split twin) her husband Douglas's new script. Passed to BOTH registrations — the cards are
#: shared objects, and the surname gate runs on each twin's own call.
KIN_OF: Mapping[str, str] = {"pt_cransfold_m": "pt_cransfold"}

#: The split twin's phone-probe rewrites (`facts_overrides`): the canonical fact
#: answers are the PLAIN twin's and hand a probing desk the decisive antibiotic by name (and, on some
#: severities, the pairing-plus-rule in one breath). The split twin's probed claimant volunteers only the
#: sub-threshold fragment — the water infection and an unnamed new antibiotic, never the methotrexate
#: link or the clinic's rule.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_chadwell": {
        "medications": (
            "Methotrexate on Sundays, folic acid midweek — and since last night the antibiotic from "
            "the out-of-hours doctor; I could not tell you its name without the box in front of me."
        ),
        "severity": "I am well — no soreness, nothing to show you.",
    },
    "pt_cransfold": {
        "medications": (
            "Methotrexate on Fridays, the folic acid midweek — and now the antibiotic from the online "
            "doctor, since last night; the name has not stuck with me."
        ),
        "severity": "Nothing to report — I feel my usual self.",
    },
    "pt_drayfold": {
        "medications": (
            "Methotrexate on Mondays, folic acid on Thursdays — and the antibiotic from this morning, "
            "which Mr Dunbrook collected for me."
        ),
        "onset": "The bladder trouble since yesterday; the antibiotic from this morning's visit.",
    },
    "pt_chadgill": {
        "medications": (
            "Methotrexate on Saturdays, folic acid midweek — and the antibiotic from the out-of-hours "
            "doctor, started last night."
        ),
        "onset": "The waterworks since the weekend, worse yesterday; the antibiotic from last night.",
    },
    "pt_caldfold": {
        "medications": (
            "Methotrexate on Sundays, the folic acid midweek — and the antibiotic from the "
            "out-of-hours place, since yesterday evening."
        ),
        "onset": "The water infection since midweek; the antibiotic from yesterday evening.",
        "severity": "A bit washed out, no more.",
    },
    "pt_draygarth": {
        "medications": (
            "Methotrexate on Wednesdays, folic acid at the weekend — and the antibiotic from the night "
            "doctor, started last night; I would have to read the packet for its name."
        ),
        "onset": "The water infection over a couple of days; the antibiotic from last night.",
        "severity": "Nothing in myself worth the name.",
    },
    "pt_carnfold": {
        "medications": (
            "Methotrexate on Tuesdays, folic acid on Fridays — and the antibiotic my grandson fetched "
            "in the night; he would know the name, I never looked."
        ),
        "onset": "The waterworks since yesterday; the antibiotic from the small hours.",
        "severity": "Quite well, only the stinging — nothing to complain of.",
    },
    "pt_draybrook": {
        "medications": (
            "Methotrexate on Thursdays, folic acid on Mondays — and the antibiotic from the "
            "out-of-hours centre, first dose this morning."
        ),
        "onset": "The water infection since yesterday; the antibiotic from first thing this morning.",
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=8,
    theme_slug="mtx_trimethoprim",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=(
        EvidenceCall(caller_id="pt_chadwell", about_claimant="pt_chadwell"),
        EvidenceCall(caller_id="pt_cransfold", about_claimant="pt_cransfold"),
        EvidenceCall(caller_id="pt_drayfold", about_claimant="pt_drayfold"),
        EvidenceCall(caller_id="pt_chadgill", about_claimant="pt_chadgill"),
        EvidenceCall(caller_id="pt_caldfold", about_claimant="pt_caldfold"),
        EvidenceCall(caller_id="pt_draygarth", about_claimant="pt_draygarth"),
        EvidenceCall(caller_id="pt_carnfold", about_claimant="pt_carnfold"),
        EvidenceCall(caller_id="pt_draybrook", about_claimant="pt_draybrook"),
    ),
    decoys=DECOYS_PLAIN,
    cards=BOARD_CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=8,
    theme_slug="mtx_trimethoprim",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=(
        # pt_chadwell: own routine intake (A) + her ring-back (C).
        EvidenceCall(caller_id="pt_chadwell", about_claimant="pt_chadwell"),
        EvidenceCall(
            caller_id="pt_chadwell",
            about_claimant="pt_chadwell",
            kind="recall",
            at_min=44,
            desk="C",
            text=CHADWELL_RECALL_TEXT,
        ),
        # pt_cransfold: own routine intake (B) + his wife's dual-purpose call (D).
        EvidenceCall(caller_id="pt_cransfold", about_claimant="pt_cransfold"),
        EvidenceCall(caller_id="pt_cransfold_m", about_claimant="pt_cransfold"),
        # pt_drayfold: own routine intake (C) + her neighbour's prescription-run call (A) + her ring-back (B).
        EvidenceCall(caller_id="pt_drayfold", about_claimant="pt_drayfold"),
        EvidenceCall(caller_id="pt_dunbrook", about_claimant="pt_drayfold"),
        EvidenceCall(
            caller_id="pt_drayfold",
            about_claimant="pt_drayfold",
            kind="recall",
            at_min=90,
            desk="B",
            text=DRAYFOLD_RECALL_TEXT,
        ),
        # pt_chadgill: own routine intake (D) + his ring-back (B).
        EvidenceCall(caller_id="pt_chadgill", about_claimant="pt_chadgill"),
        EvidenceCall(
            caller_id="pt_chadgill",
            about_claimant="pt_chadgill",
            kind="recall",
            at_min=62,
            desk="B",
            text=CHADGILL_RECALL_TEXT,
        ),
        # pt_caldfold: own routine intake (A) + her friend's dual-purpose call (C).
        EvidenceCall(caller_id="pt_caldfold", about_claimant="pt_caldfold"),
        EvidenceCall(caller_id="pt_chadthwaite", about_claimant="pt_caldfold"),
        # pt_draygarth: own routine intake (B) + his ring-back (D).
        EvidenceCall(caller_id="pt_draygarth", about_claimant="pt_draygarth"),
        EvidenceCall(
            caller_id="pt_draygarth",
            about_claimant="pt_draygarth",
            kind="recall",
            at_min=92,
            desk="D",
            text=DRAYGARTH_RECALL_TEXT,
        ),
        # pt_carnfold: own routine intake (C) + her ring-back (A).
        EvidenceCall(caller_id="pt_carnfold", about_claimant="pt_carnfold"),
        EvidenceCall(
            caller_id="pt_carnfold",
            about_claimant="pt_carnfold",
            kind="recall",
            at_min=108,
            desk="A",
            text=CARNFOLD_RECALL_TEXT,
        ),
        # pt_draybrook: own routine intake (D) + her ring-back (A).
        EvidenceCall(caller_id="pt_draybrook", about_claimant="pt_draybrook"),
        EvidenceCall(
            caller_id="pt_draybrook",
            about_claimant="pt_draybrook",
            kind="recall",
            at_min=124,
            desk="A",
            text=DRAYBROOK_RECALL_TEXT,
        ),
    ),
    decoys=DECOYS_SPLIT,
    cards=BOARD_CARDS,
    intake_overrides={
        "pt_chadwell": CHADWELL_SPLIT_INTAKE,
        "pt_cransfold": CRANSFOLD_SPLIT_INTAKE,
        "pt_drayfold": DRAYFOLD_SPLIT_INTAKE,
        "pt_chadgill": CHADGILL_SPLIT_INTAKE,
        "pt_caldfold": CALDFOLD_SPLIT_INTAKE,
        "pt_draygarth": DRAYGARTH_SPLIT_INTAKE,
        "pt_carnfold": CARNFOLD_SPLIT_INTAKE,
        "pt_draybrook": DRAYBROOK_SPLIT_INTAKE,
        "pt_cransfold_m": CRANSFOLD_M_SPLIT_INTAKE,
        "pt_dunbrook": DUNBROOK_SPLIT_INTAKE,
        "pt_chadthwaite": CHADTHWAITE_SPLIT_INTAKE,
        "pt_draysett": DRAYSETT_SPLIT_INTAKE,
        "pt_cransbrook": CRANSBROOK_SPLIT_INTAKE,
    },
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
