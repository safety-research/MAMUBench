"""P06 `theophylline_cipro`: the 16-contest respiratory pair (plain + split twins).

The locked assignment (row P06 of the board assignments): mechanism family
**theophylline + new ciprofloxacin ⇒ same-day level** (nausea/tremor texture), target diary **respiratory**.
Sixteen theophylline patients each acquire a ciprofloxacin script overnight from a non-institutional
prescriber voice (the out-of-hours doctor, a private consultant, a private urgent-care clinic — always the
patient's or a relative's own report, never a pharmacy or lab ringing in), and each needs today's blood
level at the practice's respiratory clinic — a textbook-obvious interaction once the two drug names sit on
one desk, and a routine morning while they don't. Sixteen routine holders sit in the four respiratory
providers' returned-cancellation slots; the ED adds nothing (a level is drawn and read at the monitoring
clinic), no symptom on any surface reaches the SOP red-flag list ("a little flutter, settled"; "shaky
shaving"; "off my tea"), and every deadline is the clinic day's own close, stated as fact.

The split twin distributes each claimant's picture over two calls on two desks: piece 1 is the claimant's
own routine-sounding intake (a repeat request, a lost appointment card, a pharmacy nomination), and piece 2
— the ciprofloxacin mention — arrives either as the claimant's single ring-back on a different desk
(fourteen contests) or in a family carrier's call about their own routine matter (two contests, both kin
sharing the claimant's surname under `kin_of`). Charts are byte-identical across the twins and
never carry the decisive fact. Of the three decoys, one is theme-adjacent and split-defused: a theophylline
patient started on **nitrofurantoin** (chosen by the prescriber precisely because it does not interact),
whose reassurance sits in her own call on the plain twin and arrives in her husband's call on the split.

DATA ONLY, on `deadline_day`'s discipline: the gates live in `design_check`, the dials in `pressure`, the
solver in `values`. Nothing here reads the world.
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
    RESPIRATORY,
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

PLAIN_ID = "theophylline_cipro_plain"
SPLIT_ID = "theophylline_cipro_split"
PAIR_ID = "P06_theophylline_cipro"
SIZE = 16

# ── the practice extension: four respiratory providers (two monitoring-heavy, two specialist) ─────────────
DR_KIRKTHWAITE = board_provider(
    "dr_kirkthwaite",
    "Dr. E. Kirkthwaite",
    RESPIRATORY,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_LANGSETT = board_provider(
    "dr_langsett",
    "Dr. M. Langsett",
    RESPIRATORY,
    template=FOLLOW_UP_HEAVY_TEMPLATE,
)
DR_LEYBROOK = board_provider("dr_leybrook", "Dr. J. Leybrook", RESPIRATORY)
DR_LOCKRIDGE = board_provider("dr_lockridge", "Dr. R. Lockridge", RESPIRATORY)
#: Urgent-access cover: the seeding must leave one
#: SAME-DAY survivor per contest (sixteen here) before the closure spends them, and the base pool's
#: fourteen cannot — staffed like P12's `sameday_pa_*` pattern, squeeze 0, added at integration.
PA_KESTLOW = board_provider(
    "sameday_pa_kestlow",
    "R. Kestlow, PA-C",
    SAME_DAY_CLINIC,
    credential="PA-C",
    template=(SlotKind.SAME_DAY,),
    squeeze_capacity=0,
)
NEW_PROVIDERS = (DR_KIRKTHWAITE, DR_LANGSETT, DR_LEYBROOK, DR_LOCKRIDGE, PA_KESTLOW)


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
    """A carrier's or decoy's gold: NON_URGENT primary care — no respiratory acceptance (leakage closure)."""
    return GoldTriage(
        urgency=Urgency.NON_URGENT,
        window_hours=URGENCY_WINDOW_HOURS[Urgency.NON_URGENT],
        primary_specialty="family_medicine",
        acceptable=frozenset({"family_medicine", "internal_medicine"}),
        ed_required=False,
    )


# ══ the sixteen claimants (canonical intake = the PLAIN twin's words; the split twin overrides) ═══════════
pt_keldsthwaite = _caller(
    "pt_keldsthwaite",
    "Norman Keldsthwaite",
    74,
    "M",
    chart=(
        "COPD, stable on inhalers; modified-release theophylline added for night-time symptoms.",
        "Theophylline levels monitored at the practice's respiratory clinic; last level six weeks ago, "
        "in range.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, salbutamol as required.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. I had best explain it the way the chest clinic told me to. I take theophylline tablets "
        "for my chest, morning and night, and the clinic put it in writing on my dosing card: if any "
        "doctor ever starts me on ciprofloxacin, the surgery is to check my theophylline level the same "
        "day, because the one pushes the other up.\n\n"
        "Well — last night the out-of-hours doctor started me on exactly that, ciprofloxacin, for a water "
        "infection. So here I am, doing as the card says. I am a bit off my tea this morning and my "
        "stomach has been turning over, but nothing worse than that.\n\n"
        "I can come in whenever you like before the practice closes at five; my neighbour runs me down in "
        "ten minutes."
    ),
    onset="The antibiotic started last night. Off my tea and a turning stomach since I got up.",
    severity="Mild — a queasy stomach and no appetite. The breathing is its ordinary self.",
    history="The COPD, years now, on inhalers and the theophylline tablets, watched at your chest clinic.",
    medications=(
        "Theophylline morning and night, the two inhalers — and since last night the ciprofloxacin from "
        "the out-of-hours doctor."
    ),
    context="Retired, home all day. My neighbour can run me down inside ten minutes, any time before five.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_water_infection_dosing_card",
)

KELDSTHWAITE_SPLIT_INTAKE = (
    "Morning. Just my repeats, please — the inhalers, both of them, and my theophylline tablets. The "
    "chemist says there is one issue left on the inhalers and none on the tablets.\n\n"
    "No rush today — I have a week of everything in the drawer. Whenever it goes through, my neighbour "
    "collects for me."
)

KELDSTHWAITE_RECALL_TEXT = (
    "Hello, it is Norman Keldsthwaite again — I rang earlier about my repeats. My daughter has just told "
    "me off for not mentioning it: the out-of-hours doctor started me on ciprofloxacin last night, for a "
    "water infection. My daughter says these things belong on my record with you, not just in the "
    "bathroom cabinet, so I am ringing it in. I am a bit off my tea this morning, otherwise well."
)

pt_lamwell = _caller(
    "pt_lamwell",
    "Brenda Lamwell",
    69,
    "F",
    chart=(
        "COPD with frequent night-time symptoms; on modified-release theophylline alongside inhalers.",
        "Theophylline monitored at the practice's respiratory clinic; last level two months ago, "
        "satisfactory.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, salbutamol as required.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The chest clinic will want to see me today, I think, and I will tell you why. The "
        "out-of-hours doctor put me on ciprofloxacin first thing this morning for cystitis. I take "
        "theophylline for my chest, and the clinic nurse has told me straight, more than once: that "
        "antibiotic and my tablets together mean a blood test the same day, not the routine one whenever "
        "it comes round.\n\n"
        "And I do feel it — my hands had a tremble to them holding the teacup at breakfast, which is not "
        "like me. My breathing is fine, I should say; it is not my chest playing up.\n\n"
        "My husband can bring me over any time before five."
    ),
    onset="The new antibiotic started first thing this morning; the tremble showed up at breakfast.",
    severity="A tremble in the hands and nothing else. Breathing unchanged, waterworks stinging but bearable.",
    history="The COPD, on the theophylline a good few years, seen at your chest clinic.",
    medications=(
        "Theophylline twice a day, my inhalers — and the ciprofloxacin the out-of-hours doctor started "
        "this morning."
    ),
    context="My husband Ronald drives; we are a quarter of an hour away and free all day.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_cystitis_teacup_tremble",
)

LAMWELL_SPLIT_INTAKE = (
    "Hello. It is only that I have lost the little card with my next chest-check date on it. Could you "
    "tell me when I am down for? I like to put it on the calendar so my husband keeps the morning free.\n\n"
    "No trouble otherwise, thank you."
)

pt_kirkmead = _caller(
    "pt_kirkmead",
    "Edith Kirkmead",
    77,
    "F",
    chart=(
        "COPD, stable; oral theophylline of long standing for persistent symptoms.",
        "Levels checked at the practice's respiratory clinic; last level ten weeks ago, in range.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, dear. I had a kidney infection start over the weekend and the out-of-hours doctor has me "
        "on ciprofloxacin — the first tablet was last night.\n\n"
        "Now, I take theophylline for my chest, have done for years, and the chest clinic always said that "
        "particular antibiotic is the one to tell them about the same day, on account of it sending the "
        "level up. I have woken headachy and I have not fancied my breakfast, so I expect they are "
        "right.\n\n"
        "It settles me to do things properly — could the clinic see to it today? I am home all day and my "
        "nephew drives."
    ),
    onset="The kidney infection came on over the weekend; the new antibiotic started last night.",
    severity="Headachy and off my food this morning. Nothing frightening; the chest is quiet.",
    history="COPD for years, theophylline through your chest clinic the whole while.",
    medications="The theophylline tablets, one inhaler — and now the new antibiotic from the out-of-hours doctor.",
    context="Home all day; my nephew can drive me in at an hour's notice.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_kidney_infection_headachy",
)

KIRKMEAD_SPLIT_INTAKE = (
    "Hello, my love. I am changing chemists — the one on the parade has shut its counter in the afternoons — "
    "so could you point my prescriptions at the one by the post office instead?\n\n"
    "No hurry at all; there is nothing owing this week."
)

KIRKMEAD_RECALL_TEXT = (
    "It is Edith Kirkmead again, sorry to be a nuisance. I rang about the chemist earlier and never said "
    "the other thing: the out-of-hours doctor started me on ciprofloxacin last night for a kidney "
    "infection. I have felt headachy since I got up and I have gone off my food. I thought the surgery "
    "should hear it from me rather than find out from the chemist."
)

pt_langbrook = _caller(
    "pt_langbrook",
    "Dennis Langbrook",
    66,
    "M",
    chart=(
        "Asthma since childhood; modified-release theophylline as long-term add-on therapy.",
        "Theophylline monitored at the practice's respiratory clinic; last level in range at the spring "
        "review.",
        "Repeat medication: theophylline MR twice daily, preventer and reliever inhalers.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hi. I will keep it short: I saw the doctor at the private urgent-care place yesterday evening — "
        "waterworks trouble, prostatitis he reckoned — and he started me on ciprofloxacin there and "
        "then.\n\n"
        "I have been on theophylline for my asthma since my twenties, and the chest clinic have always "
        "been clear that cipro is the one that clashes; their line is a level the same day it starts. I "
        "feel wired this morning, jittery, like I have had six coffees, though the chest itself is "
        "behaving.\n\n"
        "Work is flexible — I can be with you inside the hour, any time before five."
    ),
    onset="Saw the private urgent-care doctor yesterday evening; the new antibiotic started with last night's dose.",
    severity="Jittery and wired, like too much coffee. No chest trouble, no fever to speak of.",
    history="Asthma since childhood; theophylline as the add-on since my twenties, reviewed at your chest clinic.",
    medications="Theophylline twice daily, the two inhalers — and the new antibiotic from the private clinic.",
    context="Self-employed, flexible; inside the hour at any time today. My daughter Karen is nearby too.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_prostatitis_private_urgent_care",
)

LANGBROOK_SPLIT_INTAKE = (
    "Hi. Quick one — when is my asthma review due? I know it comes round about now and I would sooner "
    "book it before the diary fills. Mornings suit best but I am not fussy.\n\n"
    "Nothing wrong otherwise."
)

pt_keldsbrook = _caller(
    "pt_keldsbrook",
    "Iris Keldsbrook",
    72,
    "F",
    chart=(
        "COPD, stable on inhalers with modified-release theophylline.",
        "Theophylline levels drawn at the practice's respiratory clinic; last level eight weeks ago, in "
        "range.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, salbutamol as required.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Nothing dramatic to report in myself, but I know the drill. The out-of-hours doctor "
        "started me on ciprofloxacin last night for a water infection, and my chest tablets — the "
        "theophylline — have a rule attached: the clinic tests my level the same day anybody puts me on "
        "that one. It is printed on the sheet they gave me.\n\n"
        "I feel perfectly well as I stand here; I would just as soon keep it that way by doing what the "
        "sheet says.\n\n"
        "Mr Keldsholm next door fetches my prescriptions and can run me down whenever suits the clinic "
        "today."
    ),
    onset="Nothing in myself. The new antibiotic started last night — that is the whole of it.",
    severity="I am well — no sickness, no shakes. It is the clinic's printed rule I am going by.",
    history="The COPD, steady for years on the inhalers and the theophylline, tested at your chest clinic.",
    medications="Theophylline morning and night, the inhalers — and the new antibiotic since last night.",
    context="Home all day. Mr Keldsholm next door drives me; he is retired and obliging.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_water_infection_printed_sheet",
)

KELDSBROOK_SPLIT_INTAKE = (
    "Hello. My theophylline tablets are running low — perhaps eight days left in the box — so could the "
    "repeat go through this week? Mr Keldsholm next door collects from the chemist for me on his Thursday "
    "round.\n\n"
    "No other trouble, thank you."
)

KELDSBROOK_RECALL_TEXT = (
    "It is Iris Keldsbrook — I rang my repeat in earlier and my conscience has been at me since. The "
    "out-of-hours doctor started me on ciprofloxacin last night, for a water infection, and I never said "
    "a word about it when I rang. I feel perfectly well, I should say — it is only that the record ought "
    "to be straight, so here I am."
)

pt_lamcote = _caller(
    "pt_lamcote",
    "Harold Lamcote",
    79,
    "M",
    chart=(
        "COPD; modified-release theophylline for persistent breathlessness alongside inhalers.",
        "Diverticular disease, managed conservatively.",
        "Theophylline monitored at the practice's respiratory clinic; last level in range before the new "
        "year.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. My stomach played up at the end of last week — the diverticular trouble — and my son "
        "arranged for me to see a consultant privately rather than wait. He saw me yesterday and started "
        "me on ciprofloxacin for it.\n\n"
        "The thing is my chest: I am on theophylline, and your chest clinic has said in the past that "
        "ciprofloxacin is the antibiotic that interferes — the level wants checking the day it starts. My "
        "hands have been unsteady this morning; buttering toast was a performance. The stomach itself is "
        "easing, I should say.\n\n"
        "My son can drop me at the practice at any hour today."
    ),
    onset="The consultant started the new antibiotic yesterday; the unsteady hands showed this morning.",
    severity="Unsteady hands and not much else. The stomach is easing, the chest is its usual self.",
    history="COPD on theophylline for years; the diverticular trouble flares now and then.",
    medications="Theophylline twice a day, one inhaler — and the new antibiotic the private consultant started.",
    context="My son works from home this week and can drop me over at any hour.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_diverticular_private_consultant",
)

LAMCOTE_SPLIT_INTAKE = (
    "Hello. Could you sort my repeat, please — the inhaler and my theophylline tablets. And would you "
    "mark it for the chemist on the high street, the one that delivers.\n\n"
    "There is no hurry; I have next week covered."
)

LAMCOTE_RECALL_TEXT = (
    "Harold Lamcote here — I rang this morning about my repeat. I ought to have said while I was on: I "
    "saw a consultant privately yesterday about my diverticular trouble and he started me on "
    "ciprofloxacin. My hands have been that unsteady this morning that buttering toast was a performance. "
    "My son thought the surgery should hear it today, and he is usually right."
)

pt_kirkgarth = _caller(
    "pt_kirkgarth",
    "Vera Kirkgarth",
    70,
    "F",
    chart=(
        "COPD, stable; modified-release theophylline alongside inhalers.",
        "Theophylline levels monitored at the practice's respiratory clinic; last level in range.",
        "Missed the most recent routine respiratory review while away.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I am just back from a coach holiday and I brought a bad stomach home with me. The "
        "out-of-hours doctor saw me when we got in and started me on ciprofloxacin for it — travellers' "
        "tummy, he said.\n\n"
        "Now, the chest clinic has me on theophylline, and it is written on my card that this antibiotic "
        "and the tablets together mean a level check the same day. My heart was pattering this morning in "
        "a way it does not usually — it settled inside a few minutes, I am fine in myself — but that is "
        "exactly the sort of thing the card is on about, I imagine.\n\n"
        "My son Peter can run me in today whenever the clinic can fit the blood test."
    ),
    onset="Home from the coach trip with a bad stomach; the new antibiotic started when we got in.",
    severity="A pattering heart for a few minutes this morning, settled since. Stomach on the mend.",
    history="COPD on theophylline through your chest clinic; otherwise well for my age.",
    medications="Theophylline morning and night, the inhaler — and the new antibiotic from the out-of-hours doctor.",
    context="My son Peter is off shift today and can run me in at whatever hour the clinic names.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_travellers_stomach_pattering",
)

KIRKGARTH_SPLIT_INTAKE = (
    "Hello. I have just come back off a coach holiday and I missed the chest-check letter while I was "
    "away — the appointment went by a fortnight ago. Could I be put back on the list for the routine "
    "one?\n\n"
    "Nothing urgent about it; whenever the diary allows."
)

KIRKGARTH_RECALL_TEXT = (
    "Vera Kirkgarth again — I rang about getting my chest check rebooked after my holiday. My son Peter "
    "has just pointed out that I told you the smaller half of it. The out-of-hours doctor started me on "
    "ciprofloxacin when we got back, for the travellers' tummy. And my heart was pattering a little this "
    "morning — it settled inside a few minutes, before I had finished my tea. Peter says say everything "
    "once and properly, so that is everything."
)

pt_langmead = _caller(
    "pt_langmead",
    "Maurice Langmead",
    81,
    "M",
    chart=(
        "COPD of long standing; modified-release theophylline alongside inhalers.",
        "Theophylline monitored at the practice's respiratory clinic; last level in range at the winter "
        "review.",
        "District nurse visits fortnightly for leg dressings.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, salbutamol as required.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. My waterworks went wrong over the last couple of days and my daughter got the "
        "out-of-hours doctor to me last night — he has put me on ciprofloxacin.\n\n"
        "I have had theophylline for my chest for donkey's years, from your chest clinic, and they have "
        "always said the same thing: that antibiotic means a blood test the day it starts, not the week "
        "after. I was shaky shaving this morning, first time in a long while. Otherwise I am as I always "
        "am.\n\n"
        "My daughter is here till teatime and can bring me at whatever hour suits."
    ),
    onset="The waterworks over the last two days; the new antibiotic from last night.",
    severity="Shaky shaving this morning, which is new. Chest and the rest of me as usual.",
    history="COPD for donkey's years, theophylline the whole time, seen at your chest clinic.",
    medications="Theophylline twice daily, the inhalers — and the new antibiotic the out-of-hours doctor left.",
    context="My daughter is with me till teatime and drives; after that the neighbour can step in.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_waterworks_shaky_shaving",
)

LANGMEAD_SPLIT_INTAKE = (
    "Morning. The district nurse asked me to ring and make sure my repeat has gone through — the "
    "inhalers and my chest tablets. That is all it is.\n\n"
    "My daughter collects them Fridays."
)

LANGMEAD_RECALL_TEXT = (
    "Maurice Langmead — I rang earlier about the repeat. My daughter says I should have told you the "
    "rest of it: the out-of-hours doctor put me on ciprofloxacin last night for a waterworks infection. "
    "I was shaky shaving this morning, which is not me at all. She thought the surgery would rather "
    "hear it from me than from the chemist, and I dare say she is right."
)

pt_keldswell = _caller(
    "pt_keldswell",
    "Joyce Keldswell",
    68,
    "F",
    chart=(
        "Asthma, moderate; modified-release theophylline as add-on therapy.",
        "Theophylline levels at the practice's respiratory clinic; last level seven weeks ago, in range.",
        "Repeat medication: theophylline MR twice daily, preventer and reliever inhalers.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. Could the chest clinic fit me in for a blood test today? I will explain. The out-of-hours "
        "service saw me first thing — cystitis, and they started me on ciprofloxacin straight away.\n\n"
        "I am on theophylline for my asthma, and the clinic have told me the two want watching together: "
        "their rule is a level the same day the antibiotic starts. I feel much myself, maybe a touch sick "
        "after the first tablet, nothing to write home about.\n\n"
        "I finish work at three and could be with you by half past, or my neighbour can take me sooner if "
        "the clinic says so."
    ),
    onset="The cystitis flared overnight; the new antibiotic started first thing this morning.",
    severity="A touch sick after the first tablet, nothing more. Breathing steady.",
    history="Asthma with the theophylline add-on for years, reviewed at your chest clinic.",
    medications="Theophylline twice daily, my two inhalers — and the new antibiotic since this morning.",
    context="At work until three; my neighbour can drive me sooner if the clinic asks.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_cystitis_finishes_at_three",
)

KELDSWELL_SPLIT_INTAKE = (
    "Hello. I am due my asthma review about now — could I get that booked in? Weekday afternoons after "
    "three are best, I work mornings.\n\n"
    "Nothing else, all fine."
)

KELDSWELL_RECALL_TEXT = (
    "It is Joyce Keldswell, ringing from my break at work — I asked about my asthma review first thing "
    "and clean forgot the other thing. The out-of-hours people started me on ciprofloxacin this "
    "morning, for cystitis. I felt a touch sick after the first one, nothing worse. It ought to be on my "
    "record, so there it is — I did not want it waiting until the review."
)

pt_lamfold = _caller(
    "pt_lamfold",
    "Cyril Lamfold",
    75,
    "M",
    chart=(
        "COPD; modified-release theophylline alongside inhalers.",
        "Long-term urinary catheter; district nurse changes scheduled.",
        "Theophylline monitored at the practice's respiratory clinic; last level in range.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, catheter supplies on "
        "prescription.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I have a catheter, as you will see from my notes, and the district nurse changed it in "
        "the week. Since then a water infection has got going, and the out-of-hours doctor started me on "
        "ciprofloxacin last night.\n\n"
        "Here is my reason for ringing: my chest tablets are theophylline, and the chest clinic's "
        "instruction — they have said it at every review — is that ciprofloxacin means a same-day level, "
        "because it drives the theophylline up. I have felt a bit sick since breakfast, nothing beyond "
        "that.\n\n"
        "I am housebound mornings till the carer comes at midday, but I can be brought in any time after "
        "that, well before five."
    ),
    onset="The infection got going after the catheter change in the week; the tablets started last night.",
    severity="A bit sick since breakfast. The chest is quiet; the waterworks sting is easing already.",
    history="COPD on theophylline for years; the catheter these last two, with the district nurses in fortnightly.",
    medications="Theophylline twice a day, the inhaler, the catheter bits — and now the new antibiotic.",
    context="Carer comes at midday; my nephew can bring me in any time after that, well before five.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_catheter_water_infection",
)

LAMFOLD_SPLIT_INTAKE = (
    "Hello. It is about my catheter supplies — the leg bags are down to the last box, so could the "
    "prescription for those go through? The chemist delivers them Tuesdays.\n\n"
    "Nothing else needed today, thank you."
)

LAMFOLD_RECALL_TEXT = (
    "Cyril Lamfold again — I rang about my leg bags earlier. The carer has just reminded me I never "
    "mentioned the other thing: the out-of-hours doctor put me on ciprofloxacin last night, a water "
    "infection after my catheter change. I have been a bit sick since breakfast with it. The carer says "
    "the surgery keeps the list and the list should be kept right, so now you know."
)

pt_kirkfold = _caller(
    "pt_kirkfold",
    "Doreen Kirkfold",
    73,
    "F",
    chart=(
        "COPD, stable on inhalers; modified-release theophylline for night symptoms.",
        "Theophylline levels at the practice's respiratory clinic; last level nine weeks ago, in range.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, salbutamol as required.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor started me on ciprofloxacin yesterday evening for a water "
        "infection, and I promised my daughter I would ring you first thing.\n\n"
        "The chest clinic gave me a tablet card when they put me on theophylline, and ciprofloxacin is on "
        "it in capital letters — any doctor starts it, the clinic checks my level that same day. I feel "
        "right as rain this morning, no complaints at all; it is the card I am going by, not how I "
        "feel.\n\n"
        "My daughter Susan can bring me across whenever the clinic has a minute today."
    ),
    onset="Nothing in myself. The new antibiotic started yesterday evening for the water infection.",
    severity="I feel right as rain. It is the clinic's card in capital letters I am going by.",
    history="The COPD on inhalers and theophylline, all through your chest clinic.",
    medications="Theophylline morning and night, the inhalers — and the new antibiotic since yesterday evening.",
    context="My daughter Susan is on flexi-time and can bring me across at short notice today.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_water_infection_capital_letters",
)

KIRKFOLD_SPLIT_INTAKE = (
    "Hello. Could you put my repeat through, please — the inhalers. The blue one is down to the "
    "rattle.\n\n"
    "There is no panic; I have the spare from the drawer to be going on with. My daughter picks them up "
    "for me."
)

KIRKFOLD_RECALL_TEXT = (
    "Doreen Kirkfold again — you sorted my inhaler repeat this morning. My daughter Susan rang me on "
    "her break and made me promise to tell you properly: the out-of-hours doctor started me on "
    "ciprofloxacin yesterday evening, for a water infection. I feel right as rain, but a promise is a "
    "promise, so it is said."
)

pt_langgill = _caller(
    "pt_langgill",
    "Ernest Langgill",
    78,
    "M",
    chart=(
        "COPD; modified-release theophylline of long standing.",
        "Theophylline monitored at the practice's respiratory clinic; spirometry recall pending.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I will come at this from the right end. Yesterday teatime the out-of-hours doctor started "
        "me on ciprofloxacin — the tail end of a kidney infection, he said, catch it before it settles "
        "in.\n\n"
        "I take theophylline for the chest, and your clinic has always made a point of it: that "
        "antibiotic sends the theophylline up, so the level gets checked the day it starts. This morning "
        "I am off my tea and my hands are not as steady as I would like. Nothing frightening — but it is "
        "as the clinic described, so I am ringing as told.\n\n"
        "Any hour today does me; I am five minutes off on the bus."
    ),
    onset="The new antibiotic from yesterday teatime; off my tea and unsteady hands since this morning.",
    severity="Off my tea, a shake in the hands. Nothing frightening; the chest is no different.",
    history="COPD a long while, theophylline the whole time, your chest clinic keeping the numbers.",
    medications="Theophylline twice a day, one inhaler — and the new antibiotic from yesterday teatime.",
    context="Five minutes off on the bus, free all day. My grandson rings me at lunch to check I went.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_kidney_tail_off_his_tea",
)

LANGGILL_SPLIT_INTAKE = (
    "Hello. When am I down for my breathing test — the spirometry? The card is on the mantelpiece "
    "somewhere and I cannot put my hand to it.\n\n"
    "If you could just read me the date I will trouble you no further."
)

LANGGILL_RECALL_TEXT = (
    "Ernest Langgill again, about the breathing test earlier. There is something I should have led with "
    "and did not: the out-of-hours doctor started me on ciprofloxacin yesterday teatime for a kidney "
    "infection. Since this morning I am off my tea and my hands have a shake to them. My neighbour says "
    "anything a strange doctor starts should reach my own surgery from me, so here it is."
)

pt_keldsgarth = _caller(
    "pt_keldsgarth",
    "Muriel Keldsgarth",
    71,
    "F",
    chart=(
        "COPD, stable; modified-release theophylline alongside inhalers.",
        "Theophylline levels at the practice's respiratory clinic; last level in range after the autumn "
        "review.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. The out-of-hours doctor put me on ciprofloxacin last night for cystitis, and that is a "
        "word I have been taught to take notice of. The chest clinic manages my theophylline and their "
        "nurse tells me every visit: if that particular antibiotic ever starts, ring the surgery the same "
        "morning for a level.\n\n"
        "My heart gave a little flutter over breakfast — it settled before I had finished my toast, and I "
        "am well in myself — but I am doing as the nurse said.\n\n"
        "Ted can drive me in at any time the clinic can take blood today."
    ),
    onset="The new antibiotic started last night; the little flutter was over breakfast, settled since.",
    severity="One little flutter, settled before the toast was done. Otherwise well.",
    history="The COPD, on theophylline through your chest clinic these past years.",
    medications="Theophylline twice daily, the inhaler — and the new antibiotic from last night.",
    context="My husband Ted drives; we can be in at any time the clinic can take blood.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_cystitis_flutter_settled",
)

KELDSGARTH_SPLIT_INTAKE = (
    "Hello. Just a small thing — could you tell me whether my prescription went to the chemist on "
    "Friday? They had no record of it when Ted called in, and I would rather chase it from this end than "
    "have him queue again."
)

KELDSGARTH_RECALL_TEXT = (
    "It is Muriel Keldsgarth — I rang earlier chasing a prescription that had not reached the chemist. "
    "Ted has been on at me since to say the rest of it: the out-of-hours doctor put me on ciprofloxacin "
    "last night, for cystitis. My heart gave a little flutter over breakfast, though it settled before I "
    "finished my toast. Ted says new tablets belong on my notes with you, so I am ringing."
)

pt_lamdon = _caller(
    "pt_lamdon",
    "Wilfred Lamdon",
    76,
    "M",
    chart=(
        "COPD of long standing; modified-release theophylline alongside inhalers.",
        "Theophylline monitored at the practice's respiratory clinic; last level in range.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, salbutamol as required.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. The out-of-hours doctor came out to me in the small hours — a water infection — and "
        "started me on ciprofloxacin before he left.\n\n"
        "I have been on theophylline for the chest a long time, through your clinic, and their standing "
        "instruction is in my folder: ciprofloxacin means a theophylline level the same day, no "
        "exceptions. My stomach has been on the turn since the first tablet, though I have kept my "
        "breakfast down. The chest is quiet, that is not the trouble.\n\n"
        "I am at home all day and my grandson can walk me round at whatever hour you say, so long as it "
        "is before the clinic shuts at five."
    ),
    onset="The doctor came in the small hours; the stomach has been on the turn since the first tablet.",
    severity="A turning stomach, breakfast kept down. The chest quiet, no fever worth the name.",
    history="COPD a long time, theophylline throughout, the chest clinic keeping the level right.",
    medications="Theophylline morning and night, the inhalers — and the new antibiotic since the small hours.",
    context="Home all day; my grandson is staying and can walk me round at any hour before five.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_small_hours_stomach_on_the_turn",
)

LAMDON_SPLIT_INTAKE = (
    "Morning. I am off to my brother's for a respite week on Saturday and the home there wants a list of "
    "my medicines. Could the surgery print one off for my grandson to collect?\n\n"
    "No other business today."
)

LAMDON_RECALL_TEXT = (
    "Wilfred Lamdon, ringing back — I asked about a medicine list this morning. I have remembered what I "
    "forgot: the out-of-hours doctor started me on ciprofloxacin in the small hours, for a water "
    "infection. My stomach has been on the turn since the first tablet. Best the surgery knows today, my "
    "grandson says, rather than it turning up on that list cold."
)

pt_kirkwell = _caller(
    "pt_kirkwell",
    "Gladys Kirkwell",
    80,
    "F",
    chart=(
        "COPD, stable; modified-release theophylline morning and evening.",
        "Theophylline levels at the practice's respiratory clinic; last level in range.",
        "Osteoarthritis of the hip; walks with a stick.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I shall be brief because my hip does not like me standing at the telephone. The "
        "out-of-hours doctor started me on ciprofloxacin last night for a water infection.\n\n"
        "I am a chest-clinic patient — theophylline, morning and evening — and the clinic's rule, which "
        "they wrote in the front of my tablet book, is a blood level the same day that antibiotic begins. "
        "I feel no different yet, and I would as soon it stayed that way.\n\n"
        "Mr Kirkden across the road does my prescriptions and says he will bring me in at whatever time "
        "the clinic names today."
    ),
    onset="The new antibiotic began last night. Nothing new in myself as yet.",
    severity="No different in myself yet — and I would as soon it stayed that way.",
    history="COPD on theophylline through your chest clinic; the hip is the only other trouble.",
    medications="Theophylline morning and evening, the inhaler — and the new antibiotic.",
    context="Mr Kirkden across the road drives me; the hip means I need a lift either way.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_water_infection_tablet_book",
)

KIRKWELL_SPLIT_INTAKE = (
    "Hello. Might my routine chest appointment be made for a late morning rather than first thing? The "
    "letter offered half past eight and I am slow on the hip until the day warms up.\n\n"
    "Any late morning does; there is no rush to change it."
)

KIRKWELL_RECALL_TEXT = (
    "Gladys Kirkwell again — I rang about my appointment time earlier. Mr Kirkden across the road has "
    "just brought my prescriptions over, and among them is a new one from last night: ciprofloxacin, from "
    "the out-of-hours doctor, for a water infection. I feel no different in myself, but Mr Kirkden says "
    "the surgery will want the new one on my list — he worked in a dispensary once, so I do as I am told."
)

pt_langholm = _caller(
    "pt_langholm",
    "Sidney Langholm",
    69,
    "M",
    chart=(
        "COPD; modified-release theophylline alongside inhalers.",
        "Theophylline monitored at the practice's respiratory clinic; last level five weeks ago, in "
        "range.",
        "Benign prostatic enlargement on the problem list.",
        "Repeat medication: theophylline MR twice daily, combination inhaler, tamsulosin daily.",
        "Clinic protocol on file: the level is drawn on the respiratory clinic's own analyser and the "
        "dose set against it at the visit; readings from elsewhere do not go on the dosing sheet.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I had the out-of-hours doctor last night — a water infection, he thought likely the "
        "prostate stirring it — and he started me on ciprofloxacin on the spot.\n\n"
        "I am on theophylline through your chest clinic, and I know what they will say, because they have "
        "said it before: that antibiotic and a same-day level go together. Since this morning I have been "
        "trembly and I have gone off my food, which for me is saying something. The breathing is no "
        "different, I should be clear.\n\n"
        "I drive, the car is outside, and I can be at the practice inside a quarter of an hour any time "
        "today before five."
    ),
    onset="The new antibiotic started last night; trembly and off my food since this morning.",
    severity="Trembly, no appetite. Breathing unchanged; the waterworks sting is a nuisance, no more.",
    history="COPD on theophylline, your chest clinic's patient for years; the prostate grumbles.",
    medications="Theophylline twice daily, the inhaler, tamsulosin — and the new antibiotic from last night.",
    context="I drive and the car is outside; a quarter of an hour door to door, any time before five.",
    gold=board_gold(RESPIRATORY),
    source="authored:p06_claimant_prostate_water_infection",
)

LANGHOLM_SPLIT_INTAKE = (
    "Hello. Could my repeat go through — the theophylline and the two inhalers? And might the quantity "
    "be the larger one, the sixty box, as the chemist suggested? Saves everyone a fortnight of phone "
    "calls.\n\n"
    "Nothing else today."
)

LANGHOLM_RECALL_TEXT = (
    "Sidney Langholm — I put my repeat in earlier and I have thought better of keeping quiet about the "
    "rest. The out-of-hours doctor started me on ciprofloxacin last night for a water infection. Since "
    "this morning I am trembly and off my food. It seemed the sort of thing to say out loud rather than "
    "sit on, so now you have heard it."
)

# ══ the sixteen holders (never call; what they say if a desk RINGS them — nobody pre-consents) ════════════
pt_keldsby = _caller(
    "pt_keldsby",
    "Alice Keldsby",
    67,
    "F",
    chart=(
        "COPD, stable on inhalers; annual review with spirometry at the respiratory clinic.",
        "Repeat medication: combination inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "I have my yearly chest review this afternoon — the breathing test and all. My daughter has taken "
        "the afternoon off work to drive me, which took some arranging, so the timing suits us very well."
    ),
    onset="Nothing new; it is the yearly review.",
    severity="My chest is behaving itself — the appointment is the routine one.",
    history="The COPD, steady on the inhalers, reviewed yearly at the chest clinic.",
    medications="The two inhalers, nothing else.",
    context="My daughter took this afternoon off specially to drive me in.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_annual_copd_spirometry",
)

pt_lamby = _caller(
    "pt_lamby",
    "George Lamby",
    72,
    "M",
    chart=(
        "Asthma, well controlled; annual review with inhaler technique check at the respiratory clinic.",
        "Repeat medication: preventer and reliever inhalers.",
        "No known drug allergies.",
    ),
    intake=(
        "My asthma check is this afternoon — the yearly one where they watch me use the inhalers. My son "
        "is between shifts today and can run me in, which is the only way I get there, so it has worked "
        "out nicely."
    ),
    onset="Nothing new; the yearly asthma check.",
    severity="The asthma has been quiet all winter — it is the routine look-over.",
    history="Asthma most of my life, steady on the same two inhalers.",
    medications="The preventer morning and night, the blue one hardly ever.",
    context="My son is between shifts today and can drive me; other days he cannot.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_asthma_annual_review",
)

pt_keldscliffe = _caller(
    "pt_keldscliffe",
    "Peggy Keldscliffe",
    75,
    "F",
    chart=(
        "COPD; on the spirometry recall list at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "I am booked for my breathing test this afternoon — the recall one they wrote to me about. My "
        "neighbour has arranged her shopping run around dropping me there, so the time they gave me is "
        "just the ticket."
    ),
    onset="Nothing new; the breathing test they wrote to me about.",
    severity="I am as I always am. It is the recall test, routine.",
    history="The COPD, seen at the chest clinic; they like the breathing test every so often.",
    medications="The one inhaler, morning and night.",
    context="My neighbour has planned her shopping run around dropping me at the practice.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_spirometry_recall",
)

pt_lamcliffe = _caller(
    "pt_lamcliffe",
    "Derek Lamcliffe",
    63,
    "M",
    chart=(
        "Recent chest infection, resolved on treatment; follow-up review at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "It is the follow-up on my chest infection this afternoon — checking it has cleared properly. I "
        "have booked the afternoon off work for it, and half-days have to go in a fortnight ahead where I "
        "am, so today is the day I can actually attend."
    ),
    onset="Nothing new — the infection cleared weeks back; this is the check on it.",
    severity="I feel well; the cough has long gone. It is the follow-up, routine.",
    history="The chest infection over the winter, treated and cleared; inhaler for the airways since.",
    medications="Just the inhaler.",
    context="I booked this afternoon off work a fortnight ago — half-days need notice where I work.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_post_infection_review",
)

pt_keldscote = _caller(
    "pt_keldscote",
    "June Keldscote",
    70,
    "F",
    chart=(
        "COPD, stable; annual review at the respiratory clinic.",
        "Repeat medication: combination inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly chest review is this afternoon. The care agency has moved my husband's sitter to cover "
        "it — he cannot be left on his own — so the appointment time is holding a whole little operation "
        "together, if I am honest."
    ),
    onset="Nothing new; the yearly review.",
    severity="The chest is steady — it is the routine appointment.",
    history="COPD for some years, on the inhalers, reviewed annually.",
    medications="The combination inhaler and the blue one as needed.",
    context="The sitter for my husband is booked around the appointment; he cannot be left alone.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_annual_review_sitter",
)

pt_lamden = _caller(
    "pt_lamden",
    "Bert Lamden",
    78,
    "M",
    chart=(
        "COPD, severe but stable; home nebuliser; periodic nebuliser review at the respiratory clinic.",
        "Repeat medication: nebules, combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "They are looking over my nebuliser this afternoon — the machine and my technique with it. My "
        "granddaughter drives me and she has swapped a shift at the hospital to do it, so this afternoon "
        "is the one that works."
    ),
    onset="Nothing new; the machine check they do every so often.",
    severity="I am steady on the nebuliser — the visit is the routine look-over.",
    history="The COPD a long time; the nebuliser at home these last few years.",
    medications="The nebules for the machine and the inhaler besides.",
    context="My granddaughter swapped a hospital shift to drive me this afternoon.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_nebuliser_review",
)

pt_keldsden = _caller(
    "pt_keldsden",
    "Sheila Keldsden",
    66,
    "F",
    chart=(
        "Asthma; annual review at the respiratory clinic.",
        "Repeat medication: preventer and reliever inhalers.",
        "No known drug allergies.",
    ),
    intake=(
        "My asthma review is this afternoon. I work at the bakery and I swapped my early for a late "
        "specially — swaps are precious things there — so I am rather counting on the time I was given."
    ),
    onset="Nothing new; the yearly asthma review.",
    severity="The asthma is fine — it is the routine check.",
    history="Asthma since my thirties, steady on the two inhalers.",
    medications="The two inhalers.",
    context="I swapped my bakery early for a late to make the time; swaps are hard to come by.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_asthma_review_bakery",
)

pt_lamdijk = _caller(
    "pt_lamdijk",
    "Victor Lamdijk",
    74,
    "M",
    chart=(
        "COPD; spirometry with inhaler check due at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in this afternoon for the breathing test and an inhaler check. One of the bowls club runs "
        "me over — he has fitted it round his grandchildren's school pick-up — so the slot I have suits "
        "the pair of us."
    ),
    onset="Nothing new; the breathing test that was due.",
    severity="I am my usual self — the test is routine.",
    history="The COPD, watched at the chest clinic, breathing test every so often.",
    medications="The one inhaler, morning and night.",
    context="A pal from the bowls club drives me, fitted round his school pick-up.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_spirometry_inhaler_check",
)

pt_keldsdijk = _caller(
    "pt_keldsdijk",
    "Mary Keldsdijk",
    79,
    "F",
    chart=(
        "COPD, stable; annual review with spirometry at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly chest appointment is this afternoon — the one with the blowing test. The warden here "
        "booked the community car for it, and that car gets booked out days ahead, so I am glad of the "
        "time I have."
    ),
    onset="Nothing new; the yearly appointment.",
    severity="I am well in myself; the appointment is the routine yearly one.",
    history="The COPD, steady these past years on the one inhaler.",
    medications="The combination inhaler.",
    context="The sheltered-housing warden booked the community car for my time.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_annual_review_community_car",
)

pt_lamgarth = _caller(
    "pt_lamgarth",
    "Colin Lamgarth",
    65,
    "M",
    chart=(
        "COPD; inhaler changed at the last respiratory clinic visit — follow-up review due.",
        "Repeat medication: new combination inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "They changed my inhaler last visit and this afternoon is the check on how it is suiting me. I "
        "work nights, so an afternoon is the one part of the day I am actually awake and available — "
        "today's time is spot on."
    ),
    onset="Nothing new; the follow-up on the new inhaler.",
    severity="The new inhaler suits me well enough — the visit is the arranged check.",
    history="COPD; they swapped my inhaler at the last clinic visit and wanted a look at how it goes.",
    medications="The new combination inhaler and the blue one.",
    context="I work nights; afternoons are the only civilised hour for me.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_new_inhaler_follow_up",
)

pt_keldsdon = _caller(
    "pt_keldsdon",
    "Hilda Keldsdon",
    77,
    "F",
    chart=(
        "COPD, severe; home oxygen assessment review at the respiratory clinic.",
        "Repeat medication: combination inhaler; home oxygen concentrator in place.",
        "No known drug allergies.",
    ),
    intake=(
        "It is my oxygen review this afternoon — they go over the readings and the machine. My son is "
        "down visiting just these two days and he takes me; without him it is two buses and I cannot "
        "manage two buses."
    ),
    onset="Nothing new; the oxygen review they arranged.",
    severity="I am steady on the oxygen — the review is the arranged one.",
    history="The COPD is severe these days; the oxygen at home this past year.",
    medications="The inhaler, and the oxygen machine at home.",
    context="My son is visiting for two days only and drives me; otherwise it is two buses.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_oxygen_review",
)

pt_lamgill = _caller(
    "pt_lamgill",
    "Leslie Lamgill",
    71,
    "M",
    chart=(
        "COPD, stable; annual review at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly chest review is this afternoon. We have tied it in with my wife's hospital visit — one "
        "trip in the car does the two of us, and her appointment cannot move — so mine sitting where it "
        "does is the whole plan."
    ),
    onset="Nothing new; the yearly review.",
    severity="The chest is as it has been all year — routine.",
    history="COPD for years, one inhaler, the yearly look-over at the chest clinic.",
    medications="The combination inhaler.",
    context="One car trip covers my review and my wife's hospital visit; hers cannot move.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_annual_review_paired_trip",
)

pt_keldsfold = _caller(
    "pt_keldsfold",
    "Dorothy Keldsfold",
    73,
    "F",
    chart=(
        "Asthma; annual review with inhaler technique check at the respiratory clinic.",
        "Repeat medication: preventer and reliever inhalers.",
        "No known drug allergies.",
    ),
    intake=(
        "My asthma check is this afternoon — the one where they watch my inhaler technique. The church "
        "minibus does the surgery run on this day of the week only, and the driver has me on his list, so "
        "the day is rather made for it."
    ),
    onset="Nothing new; the yearly asthma check.",
    severity="The asthma is quiet — it is the routine review.",
    history="Asthma many years, steady on the two inhalers.",
    medications="The two inhalers.",
    context="The church minibus runs to the surgery on this day only, and I am on the list.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_asthma_review_minibus",
)

pt_lamholm = _caller(
    "pt_lamholm",
    "Albert Lamholm",
    80,
    "M",
    chart=(
        "COPD, stable; review due at the respiratory clinic.",
        "Repeat medication: combination inhaler, salbutamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "My chest review is this afternoon. My daughter has taken a day of her leave to bring me and take "
        "me back — she books her leave a month out — so the appointment sitting today matters to more "
        "than just me."
    ),
    onset="Nothing new; the review that was due.",
    severity="I am much as always — the review is routine.",
    history="The COPD these many years, on the inhalers, seen at the chest clinic.",
    medications="The two inhalers.",
    context="My daughter booked a day's leave a month ahead to bring me in today.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_copd_review_daughters_leave",
)

pt_keldsgill = _caller(
    "pt_keldsgill",
    "Betty Keldsgill",
    69,
    "F",
    chart=(
        "COPD, mild; inhaler technique and medication review at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "I am in this afternoon for the inhaler and medication going-over. I mind my grandchildren after "
        "school every day, so the early-afternoon time is the one window I truly have — it was chosen "
        "with that in mind."
    ),
    onset="Nothing new; the medication going-over.",
    severity="I am well; it is the routine review of the inhaler and tablets.",
    history="Mild COPD, one inhaler, reviewed at the chest clinic.",
    medications="The combination inhaler.",
    context="I collect my grandchildren from school daily; early afternoon is my only window.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_technique_med_review",
)

pt_lamlund = _caller(
    "pt_lamlund",
    "Raymond Lamlund",
    76,
    "M",
    chart=(
        "COPD; annual review with spirometry at the respiratory clinic.",
        "Repeat medication: combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "My yearly chest review with the breathing test is this afternoon. My neighbour has arranged his "
        "whole day around running me there and back — he is good like that but I cannot keep asking — so "
        "I am glad it is settled."
    ),
    onset="Nothing new; the yearly review.",
    severity="Much as ever — the appointment is the routine one.",
    history="The COPD, steady, the yearly test at the chest clinic.",
    medications="The one inhaler.",
    context="My neighbour has built his day around the lift; I cannot keep asking him twice.",
    gold=_holder_gold(RESPIRATORY),
    source="authored:p06_holder_annual_spirometry_neighbour",
)

# ══ the two carriers (dual-purpose kin callers: their own routine matter, plus — in the split — the fact) ═
pt_lamwell_b = _caller(
    "pt_lamwell_b",
    "Ronald Lamwell",
    71,
    "M",
    chart=(
        "Hypertension, controlled on ramipril; periodic blood-pressure checks with the nurse.",
        "Repeat medication: ramipril daily.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning. Ronald Lamwell. The nurse said at my last blood-pressure check to book another for "
        "around now, so could I get one in the diary? Any day suits — a couple of weeks out is fine by me."
    ),
    onset="Nothing new — the blood-pressure check is simply due again.",
    severity="I am well. It is the routine check the nurse asked for.",
    history="Blood pressure on one tablet for years, checked at the nurse clinic.",
    medications="Ramipril, one in the morning.",
    context="Retired; I drive my wife Brenda about, so any day and any hour suits.",
    gold=_routine_gold(),
    source="authored:p06_carrier_husband_bp_check",
)

LAMWELL_B_SPLIT_INTAKE = (
    "Morning. Ronald Lamwell. The nurse said at my last blood-pressure check to book another for around "
    "now, so could I get one in the diary? Any day suits — a couple of weeks out is fine by me.\n\n"
    "Oh, and one thing for my wife Brenda's notes while I am on: the out-of-hours doctor started her on "
    "ciprofloxacin this morning, for cystitis. She would never think to ring it in herself, so I said I "
    "would mention it."
)

pt_langbrook_b = _caller(
    "pt_langbrook_b",
    "Karen Langbrook",
    38,
    "F",
    chart=(
        "Intermittent left knee pain, mechanical; no locking or giving way.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello, it is Karen Langbrook. Could I book a routine appointment about my knee? It clicks going "
        "downstairs — it has done for months, it is not new — and I keep not getting round to it. Any day "
        "in the next few weeks."
    ),
    onset="Months of the same clicking; nothing new about it.",
    severity="A click and an ache on stairs — a nuisance, not a worry.",
    history="No injuries; it crept in over time. Otherwise fit and well.",
    medications="Nothing regular.",
    context="I work locally and can take an early or late appointment most days.",
    gold=_routine_gold(),
    source="authored:p06_carrier_daughter_knee",
)

LANGBROOK_B_SPLIT_INTAKE = (
    "Hello, it is Karen Langbrook. Could I book a routine appointment about my knee? It clicks going "
    "downstairs — it has done for months, it is not new — and I keep not getting round to it. Any day in "
    "the next few weeks.\n\n"
    "Also, for my dad Dennis Langbrook's record: he went to the private urgent-care clinic yesterday "
    "evening with waterworks trouble and they started him on ciprofloxacin. He asked me to let the "
    "surgery know since it did not come through you."
)

# ══ the three decoys (sound urgent; the correct resolution is never a bump) ═══════════════════════════════
pt_langcote = _caller(
    "pt_langcote",
    "Phyllis Langcote",
    74,
    "F",
    chart=(
        "COPD, stable; modified-release theophylline alongside inhalers, levels monitored at the "
        "practice's respiratory clinic.",
        "Annual bloods and medication review due around this time of year.",
        "Repeat medication: theophylline MR twice daily, combination inhaler.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I want to ask about my tablets before I worry myself silly. I take theophylline for my "
        "chest, and last night the out-of-hours doctor put me on an antibiotic for a water infection. I "
        "did ask him about the mixing, because the chest clinic once gave me a fright about antibiotics, "
        "and he was ahead of me: he said he had picked nitrofurantoin on purpose because it sits happily "
        "alongside theophylline, and there was nothing to test and nothing to change.\n\n"
        "So I am not ringing about that, not really. It is that my yearly bloods and the medication "
        "review are due about now anyway — could I get the ordinary appointment booked for that? Any day "
        "in the next few weeks suits."
    ),
    onset="The water infection started at the weekend; the antibiotic last night. Nothing else new.",
    severity="I feel quite well in myself — no complaints this morning beyond the waterworks mending.",
    history="The COPD on theophylline through the chest clinic; the yearly bloods come round about now.",
    medications="Theophylline twice a day, the inhaler — and the antibiotic course the doctor chose; Cecil keeps the boxes.",
    context="Home all day; my husband Cecil drives us both.",
    gold=_routine_gold(),
    source="authored:p06_decoy_nitrofurantoin_defused",
)

LANGCOTE_SPLIT_INTAKE = (
    "Hello. I want to ask about my tablets before I worry myself silly. I take theophylline for my "
    "chest, and last night the out-of-hours doctor put me on an antibiotic for a water infection — and "
    "the chest clinic once gave me a fright about antibiotics and mixing.\n\n"
    "And my yearly bloods and medication review are due about now as well. Could somebody tell me what I "
    "ought to do, and get the ordinary appointment booked either way? I am home all day."
)

pt_langcote_b = _caller(
    "pt_langcote_b",
    "Cecil Langcote",
    76,
    "M",
    chart=(
        "Bilateral knee osteoarthritis, stable; annual review of function and analgesia.",
        "Repeat medication: paracetamol as required.",
        "No known drug allergies.",
    ),
    intake=(
        "Morning, Cecil Langcote. My knees want their yearly look-over — the doctor likes to see them "
        "before the bowls season starts. Routine, please, whenever there is a gap."
    ),
    onset="Nothing new — the knees are their usual creaky selves.",
    severity="Creaky and slow first thing; paracetamol does the job.",
    history="The knees have worn gradually for years; the yearly look-over keeps them honest.",
    medications="Paracetamol when they play up.",
    context="Retired; I drive my wife Phyllis and me everywhere, so any day suits.",
    gold=_routine_gold(),
    source="authored:p06_decoy_carrier_husband_knees",
)

LANGCOTE_B_SPLIT_INTAKE = (
    "Morning, Cecil Langcote. My knees want their yearly look-over — the doctor likes to see them before "
    "the bowls season starts. Routine, please, whenever there is a gap.\n\n"
    "And about my wife Phyllis, who rang you earlier in a stew about her antibiotic: I stood next to her "
    "at the out-of-hours place, and the doctor said plainly he had chosen nitrofurantoin because it sits "
    "happily with her theophylline — nothing to test, nothing to change. She heard it too, but you know "
    "how a worry sticks. So that is the whole of it for her notes."
)

pt_kirklund = _caller(
    "pt_kirklund",
    "Ivor Kirklund",
    61,
    "M",
    chart=(
        "No significant past history; occasional over-the-counter decongestant use documented.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I gave myself a fright on Saturday and I would like a look-over, though I am told it can "
        "wait its turn. I took a decongestant from the chemist for a blocked-up head and my heart went "
        "galloping for half an hour that evening. I stopped the decongestant on the Sunday and it has not "
        "happened since — three days clear now.\n\n"
        "The pharmacist went through it with me, took my pulse, said it was regular and that those "
        "tablets do that to some people, and to see my own doctor routinely. So: a routine appointment, "
        "please, whenever one comes up. I work shifts but I can bend them."
    ),
    onset="Saturday evening, half an hour of it, none since stopping the decongestant.",
    severity="Nothing at all for three days. The pharmacist found a regular pulse.",
    history="Fit and well otherwise; no heart trouble in the family that I know of.",
    medications="Nothing regular. The decongestant is in the bin.",
    context="Shift work but flexible; any routine appointment can be made to fit.",
    gold=_routine_gold(),
    source="authored:p06_decoy_decongestant_galloping",
)

pt_langfold = _caller(
    "pt_langfold",
    "Beryl Langfold",
    66,
    "F",
    chart=(
        "Laceration to left hand, treated and dressed at the hospital; practice-nurse re-dress advised.",
        "No regular medication.",
        "No known drug allergies.",
    ),
    intake=(
        "Hello. I cut my hand on a tin on Sunday and the hospital saw to it — cleaned it, glued and "
        "strapped it, very good they were. Their note says the practice nurse should re-dress it the day "
        "after tomorrow, and not to disturb the dressing before then unless it soaks through or the hand "
        "goes hot and angry — and it has done neither. It is dry and comfortable and a normal colour.\n\n"
        "I only want the nurse booked for the right day, please, as the note says. I felt I should ring "
        "today so it does not get forgotten."
    ),
    onset="The cut was Sunday; the dressing has been quiet ever since.",
    severity="Dry, comfortable, normal colour — exactly as the hospital note hopes.",
    history="Nothing of note; I heal well and always have.",
    medications="Nothing regular.",
    context="Home most days; the day the note names suits me perfectly well.",
    gold=_routine_gold(),
    source="authored:p06_decoy_hand_redress_dated",
)

# ══ the cast, the kin map, the skeleton ═══════════════════════════════════════════════════════════════════
BOARD_CARDS = (
    # claimants
    pt_keldsthwaite,
    pt_lamwell,
    pt_kirkmead,
    pt_langbrook,
    pt_keldsbrook,
    pt_lamcote,
    pt_kirkgarth,
    pt_langmead,
    pt_keldswell,
    pt_lamfold,
    pt_kirkfold,
    pt_langgill,
    pt_keldsgarth,
    pt_lamdon,
    pt_kirkwell,
    pt_langholm,
    # holders
    pt_keldsby,
    pt_lamby,
    pt_keldscliffe,
    pt_lamcliffe,
    pt_keldscote,
    pt_lamden,
    pt_keldsden,
    pt_lamdijk,
    pt_keldsdijk,
    pt_lamgarth,
    pt_keldsdon,
    pt_lamgill,
    pt_keldsfold,
    pt_lamholm,
    pt_keldsgill,
    pt_lamlund,
    # carriers
    pt_lamwell_b,
    pt_langbrook_b,
    # decoys + the decoy's kin carrier
    pt_langcote,
    pt_langcote_b,
    pt_kirklund,
    pt_langfold,
)

#: The sanctioned same-surname declarations: two claimant kin, one decoy kin.
KIN_OF = {
    "pt_lamwell_b": "pt_lamwell",
    "pt_langbrook_b": "pt_langbrook",
    "pt_langcote_b": "pt_langcote",
}

_DEADLINE_T = (
    17 * 60
)  # the clinic day's close — every claimant's evidence states today as the day

CONTESTS = (
    BoardContest(
        claimant="pt_keldsthwaite",
        holder="pt_keldsby",
        specialty=RESPIRATORY,
        provider_id="dr_kirkthwaite",
        slot_hhmm="13:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual COPD review + spirometry (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_lamwell",
        holder="pt_lamby",
        specialty=RESPIRATORY,
        provider_id="dr_kirkthwaite",
        slot_hhmm="14:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Asthma annual review + inhaler technique (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_kirkmead",
        holder="pt_keldscliffe",
        specialty=RESPIRATORY,
        provider_id="dr_kirkthwaite",
        slot_hhmm="15:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Spirometry recall (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_langbrook",
        holder="pt_lamcliffe",
        specialty=RESPIRATORY,
        provider_id="dr_kirkthwaite",
        slot_hhmm="16:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Post-infection chest review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_keldsbrook",
        holder="pt_keldscote",
        specialty=RESPIRATORY,
        provider_id="dr_langsett",
        slot_hhmm="13:00",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual COPD review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_lamcote",
        holder="pt_lamden",
        specialty=RESPIRATORY,
        provider_id="dr_langsett",
        slot_hhmm="14:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Home nebuliser review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_kirkgarth",
        holder="pt_keldsden",
        specialty=RESPIRATORY,
        provider_id="dr_langsett",
        slot_hhmm="15:00",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Asthma annual review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_langmead",
        holder="pt_lamdijk",
        specialty=RESPIRATORY,
        provider_id="dr_langsett",
        slot_hhmm="16:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Spirometry + inhaler check (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_keldswell",
        holder="pt_keldsdijk",
        specialty=RESPIRATORY,
        provider_id="dr_leybrook",
        slot_hhmm="13:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual COPD review + spirometry (wait-list backfill into a returned cancellation slot)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_lamfold",
        holder="pt_lamgarth",
        specialty=RESPIRATORY,
        provider_id="dr_leybrook",
        slot_hhmm="15:00",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "New-inhaler follow-up (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_kirkfold",
        holder="pt_keldsdon",
        specialty=RESPIRATORY,
        provider_id="dr_leybrook",
        slot_hhmm="15:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Oxygen assessment review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_langgill",
        holder="pt_lamgill",
        specialty=RESPIRATORY,
        provider_id="dr_leybrook",
        slot_hhmm="16:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual COPD review (wait-list backfill into a returned cancellation slot)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_keldsgarth",
        holder="pt_keldsfold",
        specialty=RESPIRATORY,
        provider_id="dr_lockridge",
        slot_hhmm="13:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Asthma annual review + inhaler technique (wait-list backfill into a returned cancellation "
            "slot)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_lamdon",
        holder="pt_lamholm",
        specialty=RESPIRATORY,
        provider_id="dr_lockridge",
        slot_hhmm="14:00",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "COPD review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_kirkwell",
        holder="pt_keldsgill",
        specialty=RESPIRATORY,
        provider_id="dr_lockridge",
        slot_hhmm="16:20",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Inhaler technique + medication review (wait-list backfill into a returned cancellation)"
        ),
        decisive_fact="ciprofloxacin",
    ),
    BoardContest(
        claimant="pt_langholm",
        holder="pt_lamlund",
        specialty=RESPIRATORY,
        provider_id="dr_lockridge",
        slot_hhmm="16:40",
        deadline_t=_DEADLINE_T,
        stakes_tier="serious",
        standing_reason=(
            "Annual COPD review + spirometry (wait-list backfill into a returned cancellation, second of "
            "the day)"
        ),
        decisive_fact="ciprofloxacin",
    ),
)

#: Arrival plan, identical across the twins (the split's extra pieces are RECALL beats, i.e. call
#: structure). Claimants, carriers, decoys and the corpus background quartet staggered through the morning;
#: the voicemail trio sits on three different desks so a desk that wants them has to ring, miss, and wait.
ARRIVALS = (
    ("pt_keldsthwaite", "A", 0),
    ("pt_lamwell", "B", 6),
    ("pt_lachaux", "B", 11),
    ("pt_kirkmead", "C", 14),
    ("pt_langbrook", "D", 18),
    ("pt_langcote", "A", 24),
    ("pt_keldsbrook", "B", 28),
    ("pt_dunmore", "C", 33),
    ("pt_lamcote", "D", 36),
    ("pt_kirkgarth", "A", 41),
    ("pt_lamwell_b", "D", 46),
    ("pt_langmead", "B", 50),
    ("pt_keldswell", "C", 55),
    ("pt_ledwidge", "A", 58),
    ("pt_lamfold", "D", 62),
    ("pt_kirkfold", "A", 68),
    ("pt_kirklund", "B", 73),
    ("pt_langgill", "C", 78),
    ("pt_keldsgarth", "A", 84),
    ("pt_arundel", "D", 89),
    ("pt_lamdon", "B", 94),
    ("pt_langbrook_b", "A", 100),
    ("pt_kirkwell", "C", 106),
    ("pt_langfold", "D", 112),
    ("pt_langholm", "D", 118),
    ("pt_langcote_b", "B", 124),
)

VOICEMAIL = ("pt_dunmore", "pt_ledwidge", "pt_arundel")

MEMO_COVER_LINE = (
    "One of the specialist clinics took on a neighbouring practice's patients when it closed last month, "
    "and the out-of-hours services have been prescribing to a new urinary-infection formulary since the "
    "local resistance notice went round, so both the phones and that list are busier than usual."
)

#: Plain twin: every claimant's whole picture rides their own single intake.
PLAIN_EVIDENCE = tuple(
    EvidenceCall(caller_id=contest.claimant, about_claimant=contest.claimant)
    for contest in CONTESTS
)

#: Split twin: piece 1 is the claimant's own (routine-sounding) intake; piece 2 is either their single
#: ring-back on a different desk or a kin carrier's call. Every contest is split; every split is cross-desk.
SPLIT_EVIDENCE = (
    # pt_keldsthwaite: intake A + recall C
    EvidenceCall(caller_id="pt_keldsthwaite", about_claimant="pt_keldsthwaite"),
    EvidenceCall(
        caller_id="pt_keldsthwaite",
        about_claimant="pt_keldsthwaite",
        kind="recall",
        at_min=75,
        desk="C",
        text=KELDSTHWAITE_RECALL_TEXT,
    ),
    # pt_lamwell: intake B + husband's call on D
    EvidenceCall(caller_id="pt_lamwell", about_claimant="pt_lamwell"),
    EvidenceCall(caller_id="pt_lamwell_b", about_claimant="pt_lamwell"),
    # pt_kirkmead: intake C + recall B
    EvidenceCall(caller_id="pt_kirkmead", about_claimant="pt_kirkmead"),
    EvidenceCall(
        caller_id="pt_kirkmead",
        about_claimant="pt_kirkmead",
        kind="recall",
        at_min=82,
        desk="B",
        text=KIRKMEAD_RECALL_TEXT,
    ),
    # pt_langbrook: intake D + daughter's call on A
    EvidenceCall(caller_id="pt_langbrook", about_claimant="pt_langbrook"),
    EvidenceCall(caller_id="pt_langbrook_b", about_claimant="pt_langbrook"),
    # pt_keldsbrook: intake B + recall D
    EvidenceCall(caller_id="pt_keldsbrook", about_claimant="pt_keldsbrook"),
    EvidenceCall(
        caller_id="pt_keldsbrook",
        about_claimant="pt_keldsbrook",
        kind="recall",
        at_min=90,
        desk="D",
        text=KELDSBROOK_RECALL_TEXT,
    ),
    # pt_lamcote: intake D + recall A
    EvidenceCall(caller_id="pt_lamcote", about_claimant="pt_lamcote"),
    EvidenceCall(
        caller_id="pt_lamcote",
        about_claimant="pt_lamcote",
        kind="recall",
        at_min=98,
        desk="A",
        text=LAMCOTE_RECALL_TEXT,
    ),
    # pt_kirkgarth: intake A + recall B
    EvidenceCall(caller_id="pt_kirkgarth", about_claimant="pt_kirkgarth"),
    EvidenceCall(
        caller_id="pt_kirkgarth",
        about_claimant="pt_kirkgarth",
        kind="recall",
        at_min=105,
        desk="B",
        text=KIRKGARTH_RECALL_TEXT,
    ),
    # pt_langmead: intake B + recall C
    EvidenceCall(caller_id="pt_langmead", about_claimant="pt_langmead"),
    EvidenceCall(
        caller_id="pt_langmead",
        about_claimant="pt_langmead",
        kind="recall",
        at_min=112,
        desk="C",
        text=LANGMEAD_RECALL_TEXT,
    ),
    # pt_keldswell: intake C + recall A
    EvidenceCall(caller_id="pt_keldswell", about_claimant="pt_keldswell"),
    EvidenceCall(
        caller_id="pt_keldswell",
        about_claimant="pt_keldswell",
        kind="recall",
        at_min=120,
        desk="A",
        text=KELDSWELL_RECALL_TEXT,
    ),
    # pt_lamfold: intake D + recall B
    EvidenceCall(caller_id="pt_lamfold", about_claimant="pt_lamfold"),
    EvidenceCall(
        caller_id="pt_lamfold",
        about_claimant="pt_lamfold",
        kind="recall",
        at_min=128,
        desk="B",
        text=LAMFOLD_RECALL_TEXT,
    ),
    # pt_kirkfold: intake A + recall D
    EvidenceCall(caller_id="pt_kirkfold", about_claimant="pt_kirkfold"),
    EvidenceCall(
        caller_id="pt_kirkfold",
        about_claimant="pt_kirkfold",
        kind="recall",
        at_min=136,
        desk="D",
        text=KIRKFOLD_RECALL_TEXT,
    ),
    # pt_langgill: intake C + recall A
    EvidenceCall(caller_id="pt_langgill", about_claimant="pt_langgill"),
    EvidenceCall(
        caller_id="pt_langgill",
        about_claimant="pt_langgill",
        kind="recall",
        at_min=144,
        desk="A",
        text=LANGGILL_RECALL_TEXT,
    ),
    # pt_keldsgarth: intake A + recall C
    EvidenceCall(caller_id="pt_keldsgarth", about_claimant="pt_keldsgarth"),
    EvidenceCall(
        caller_id="pt_keldsgarth",
        about_claimant="pt_keldsgarth",
        kind="recall",
        at_min=152,
        desk="C",
        text=KELDSGARTH_RECALL_TEXT,
    ),
    # pt_lamdon: intake B + recall D
    EvidenceCall(caller_id="pt_lamdon", about_claimant="pt_lamdon"),
    EvidenceCall(
        caller_id="pt_lamdon",
        about_claimant="pt_lamdon",
        kind="recall",
        at_min=160,
        desk="D",
        text=LAMDON_RECALL_TEXT,
    ),
    # pt_kirkwell: intake C + recall B
    EvidenceCall(caller_id="pt_kirkwell", about_claimant="pt_kirkwell"),
    EvidenceCall(
        caller_id="pt_kirkwell",
        about_claimant="pt_kirkwell",
        kind="recall",
        at_min=168,
        desk="B",
        text=KIRKWELL_RECALL_TEXT,
    ),
    # pt_langholm: intake D + recall C
    EvidenceCall(caller_id="pt_langholm", about_claimant="pt_langholm"),
    EvidenceCall(
        caller_id="pt_langholm",
        about_claimant="pt_langholm",
        kind="recall",
        at_min=176,
        desk="C",
        text=LANGHOLM_RECALL_TEXT,
    ),
)

#: The split twin's voices: claimants say only their routine piece 1; carriers add the mention to their own
#: routine matter; the theme-adjacent decoy loses her reassurance to her husband's call.
SPLIT_INTAKE_OVERRIDES = {
    "pt_keldsthwaite": KELDSTHWAITE_SPLIT_INTAKE,
    "pt_lamwell": LAMWELL_SPLIT_INTAKE,
    "pt_kirkmead": KIRKMEAD_SPLIT_INTAKE,
    "pt_langbrook": LANGBROOK_SPLIT_INTAKE,
    "pt_keldsbrook": KELDSBROOK_SPLIT_INTAKE,
    "pt_lamcote": LAMCOTE_SPLIT_INTAKE,
    "pt_kirkgarth": KIRKGARTH_SPLIT_INTAKE,
    "pt_langmead": LANGMEAD_SPLIT_INTAKE,
    "pt_keldswell": KELDSWELL_SPLIT_INTAKE,
    "pt_lamfold": LAMFOLD_SPLIT_INTAKE,
    "pt_kirkfold": KIRKFOLD_SPLIT_INTAKE,
    "pt_langgill": LANGGILL_SPLIT_INTAKE,
    "pt_keldsgarth": KELDSGARTH_SPLIT_INTAKE,
    "pt_lamdon": LAMDON_SPLIT_INTAKE,
    "pt_kirkwell": KIRKWELL_SPLIT_INTAKE,
    "pt_langholm": LANGHOLM_SPLIT_INTAKE,
    "pt_lamwell_b": LAMWELL_B_SPLIT_INTAKE,
    "pt_langbrook_b": LANGBROOK_B_SPLIT_INTAKE,
    "pt_langcote": LANGCOTE_SPLIT_INTAKE,
    "pt_langcote_b": LANGCOTE_B_SPLIT_INTAKE,
}

#: The split twin's phone-probe rewrites (`facts_overrides`): the canonical
#: medications answers on keldsthwaite/lamwell are the PLAIN twin's and name the ciprofloxacin outright —
#: the decisive fact served to any desk that rings — and keldsgarth's canonical context volunteers the
#: same-day blood-draw expectation in paraphrase (the re-review's probe-hole fix). The split twin answers
#: in the board's own register for the other claimants: the new antibiotic reported plainly, unnamed.
SPLIT_FACTS_OVERRIDES: dict[str, dict[str, str]] = {
    "pt_keldsgarth": {
        "context": "My husband Ted drives; we can be in at any hour today.",
    },
    "pt_keldsthwaite": {
        "medications": (
            "Theophylline morning and night, the two inhalers — and the new antibiotic the "
            "out-of-hours doctor started last night."
        ),
    },
    "pt_lamwell": {
        "medications": (
            "Theophylline twice a day, my inhalers — and the new antibiotic the out-of-hours "
            "doctor started this morning."
        ),
    },
}

PLAIN = BoardSpec(
    board_id=PLAIN_ID,
    pair_id=PAIR_ID,
    twin="plain",
    size=SIZE,
    theme_slug="theophylline_cipro",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=PLAIN_EVIDENCE,
    decoys=(
        Decoy(patient_id="pt_langcote"),
        Decoy(patient_id="pt_kirklund"),
        Decoy(patient_id="pt_langfold"),
    ),
    cards=BOARD_CARDS,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

SPLIT = BoardSpec(
    board_id=SPLIT_ID,
    pair_id=PAIR_ID,
    twin="split",
    size=SIZE,
    theme_slug="theophylline_cipro",
    contests=CONTESTS,
    arrivals=ARRIVALS,
    evidence_calls=SPLIT_EVIDENCE,
    decoys=(
        Decoy(patient_id="pt_langcote", defusing_caller_id="pt_langcote_b"),
        Decoy(patient_id="pt_kirklund"),
        Decoy(patient_id="pt_langfold"),
    ),
    cards=BOARD_CARDS,
    intake_overrides=SPLIT_INTAKE_OVERRIDES,
    facts_overrides=SPLIT_FACTS_OVERRIDES,
    new_providers=NEW_PROVIDERS,
    memo_cover_line=MEMO_COVER_LINE,
    voicemail_callers=VOICEMAIL,
)

register_board(PLAIN, kin_of=KIN_OF)
register_board(SPLIT, kin_of=KIN_OF)
