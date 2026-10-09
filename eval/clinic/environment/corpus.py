"""The four shared background callers and the hero-board patient registry.

Board-specific cards live beside their scenarios. The four original background
callers are reused by the frozen boards and retain their original facts."""

from __future__ import annotations


from collections.abc import Sequence


from .reprioritization import pt_ledwidge

from .resources import (
    FAMILY_MEDICINE,
    INTERNAL_MEDICINE,
    PEDIATRICS,
    URGENCY_WINDOW_HOURS,
    GoldTriage,
    PatientCard,
    PhoneBehavior,
    Urgency,
    facts_for,
)


def _gold(
    urgency: Urgency, primary: str, acceptable: tuple[str, ...] = ()
) -> GoldTriage:
    """A `GoldTriage` whose window and ED requirement follow from the urgency.

    `acceptable` is INCLUSIVE of `primary_specialty`, so callers pass only the ADDITIONAL
    specialties and the primary is unioned in here. For a SELF_CARE card `primary_specialty` names the
    specialty that would see them if somebody booked them anyway — it grades an inappropriate booking and
    never means one is wanted.
    """
    return GoldTriage(
        urgency=urgency,
        window_hours=URGENCY_WINDOW_HOURS[urgency],
        primary_specialty=primary,
        acceptable=frozenset(acceptable) | {primary},
        ed_required=urgency is Urgency.EMERGENT,
    )


pt_dunmore = PatientCard(
    id="pt_dunmore",
    name="Barry Dunmore",
    age=64,
    sex="M",
    phone=PhoneBehavior.VOICEMAIL,
    on_file=True,
    chart=(
        "Hypertension, diagnosed 11 years ago, well controlled.",
        "Repeat medication: amlodipine 5 mg daily, atorvastatin 20 mg nightly.",
        "Blood pressure at pharmacy check 5 weeks ago: 126/78.",
        "Bloods 4 months ago: kidney function and lipids both satisfactory.",
        "Annual review due in 3 months.",
        "No known drug allergies.",
    ),
    intake="Morning. It's Barry Dunmore here. Nothing wrong, I just need my tablets sorting out — the blood pressure ones, the amlodipine, and the cholesterol one while you're at it.\n\nI've got about two weeks left in the packet so there's no panic, I just know what you lot are like when I leave it to the last minute and then it's a Friday afternoon and nobody can do anything. So I'm being organised for once.\n\nI feel absolutely fine, before you ask. No headaches, nothing like that. I had it checked on the machine in the chemist about a month ago and it came out at 126 over 78, which the girl said was spot on.\n\nSo I don't need to see anybody, I don't think — I just need the prescription putting through to the chemist on the high street. If somebody could give me a ring back and tell me it's done, that'd be grand.",
    facts=facts_for(
        onset="Nothing's started, that's the thing — I'm just running low. About two weeks left in the packet.",
        severity="I've got no symptoms whatsoever — no headaches, no dizziness, nothing. I feel completely fine.",
        history="Blood pressure, on tablets about eleven years. Never given me any trouble.",
        medications="Amlodipine five milligrams and the atorvastatin at night, those are the two I need. I've not missed any.",
        allergies="No allergies, no.",
        context="I only want the repeat sent to the chemist on the high street. I don't need an appointment as far as I can see.",
    ),
    voice="plain",
    gold=_gold(Urgency.SELF_CARE, FAMILY_MEDICINE, (INTERNAL_MEDICINE,)),
    signal_channel="intake",
    source="authored:repeat_prescription",
)


pt_lachaux = PatientCard(
    id="pt_lachaux",
    name="Julien Lachaux",
    age=25,
    sex="M",
    phone=PhoneBehavior.ANSWERS,
    on_file=False,
    chart=(),
    intake="Hi. I, um. I'd like to talk to somebody about how I've been feeling, if that's the sort of thing you book.\n\nIt's — I've been low. Most days, really, for about the last two months. Sad nearly every day is probably the honest way to put it. I got married in the spring, which everyone keeps pointing out to me, so I feel a bit stupid ringing.\n\nThe main practical problem is work. I can't concentrate — more than half the days in the last couple of weeks I've just been staring at things. And I don't want to get up. If I could stay in bed all day I would. Sleep's been patchy too, several nights of it.\n\nI'm not ill otherwise, nothing physical, no pain or anything. And — I should probably say, I'm not having any thoughts of harming myself. Nothing like that. I'm just flat and I'd like to talk to somebody about it.",
    facts=facts_for(
        onset="About two months. It's been most days rather than coming and going.",
        severity="I'm managing to get to work, but I can't concentrate more than half the days. I'm not having any thoughts of harming myself.",
        history="Nothing. I've never seen anyone about my mood before and I'm physically well.",
        medications="Nothing at all, not even painkillers really.",
        allergies="No allergies.",
        context="I got married in the spring, so I feel a bit stupid ringing about it. Sleep's been patchy several nights in the last fortnight.",
    ),
    voice="plain",
    gold=_gold(Urgency.NON_URGENT, FAMILY_MEDICINE, (INTERNAL_MEDICINE,)),
    signal_channel="intake",
    source="ceney2021:V32",
)


pt_arundel = PatientCard(
    id="pt_arundel",
    name="Poppy Arundel",
    age=5,
    sex="F",
    phone=PhoneBehavior.VOICEMAIL,
    on_file=False,
    chart=(),
    intake="Morning — this is about my daughter Poppy, she's five, and I'm fairly sure I know what it is, I just want to know what to buy and whether we all have to take it.\n\nShe's been complaining her bottom's itchy, mostly at night — she's been waking up and wriggling. And then yesterday, sorry, but I saw little white threads in the toilet, moving. So. I'm fairly confident that answers that.\n\nShe's been grumpy and tired with the broken sleep, which is the main effect on her. But she's otherwise well — eating fine, no temperature, no tummy ache, nothing else wrong with her.\n\nThere's her little brother as well and I've read you're supposed to treat everybody, so I want to be told properly rather than guessing in the chemist aisle. Can you leave me a message with what to do? I'm on shift till two so I won't get the phone.",
    facts=facts_for(
        onset="About a week of itching at night. I saw the threads yesterday.",
        severity="It's the itching and the broken sleep, that's all — she's grumpy and tired with it. No temperature and no tummy ache.",
        history="She's a healthy five-year-old, all up to date with her jabs. Never had this before.",
        medications="Nothing. I haven't given her anything for it yet.",
        allergies="No allergies.",
        context="I'm her mum, and there's a little brother in the house too, so I need to know whether we all get treated. I'm on shift till two.",
    ),
    voice="third_party",
    gold=_gold(Urgency.SELF_CARE, PEDIATRICS, (FAMILY_MEDICINE,)),
    signal_channel="intake",
    source="hill2020:T1-threadworm",
)


def _one_card_per_id(pool: Sequence[PatientCard]) -> dict[str, PatientCard]:
    """`{id: card}`, REFUSING a duplicate id instead of silently keeping the last one.

    The comprehension this replaces asserted in its own comment that "a duplicate id fails loudly here". It
    did not: `{card.id: card for card in ...}` keeps the LAST binding and says nothing, so an author reaching
    for an id the pool already carries does not get an error — they get a corpus in which another cell's
    patient has quietly become theirs, and that cell now runs with a different card's phone behaviour,
    availability and rendered surfaces.

    **Found by the anchor ritual rather than by the guard, which is the part worth keeping.** A v3 card took
    `pt_ingoldsby`, an existing `quiet_crowdout` caller. The SCORED dump stayed BYTE-IDENTICAL — both cards
    are NON_URGENT family medicine, so no plan and no utility moved — while the design_check table grew a
    forced wait and five scanned surfaces in a cell v3 has nothing to do with. A collision that moves no
    number is exactly the one an eye misses, so the check belongs at construction.
    """
    seen: dict[str, PatientCard] = {}
    for card in pool:
        if card.id in seen:
            raise ValueError(
                f"duplicate card id {card.id!r}: {seen[card.id].name} (from {seen[card.id].source}) is "
                f"already in the corpus, and {card.name} (from {card.source}) would silently replace them "
                "in every cell that draws that id"
            )
        seen[card.id] = card
    return seen


CORPUS: dict[str, PatientCard] = _one_card_per_id(
    (pt_arundel, pt_dunmore, pt_lachaux, pt_ledwidge)
)


def cards(*ids: str) -> tuple[PatientCard, ...]:
    """The named cards, in the order asked for.

    Args:
        *ids: Card ids from `CORPUS`.

    Returns:
        The cards, in the given order.

    Raises:
        KeyError: If an id is not in the corpus (a scenario naming a card that does not exist).
    """
    return tuple(CORPUS[pid] for pid in ids)


def register_board_cards(pool: Sequence[PatientCard]) -> None:
    """Fold a registered board's cards into `CORPUS` (called ONLY by `board_spec.register_board`).

    The additive twin of the `*DEADLINE_CARDS` fold above — a board's cast lives with the board's declaration and the corpus resolves the ids in one place — with one extra allowance the static fold never needed: a card that is ALREADY registered as the SAME OBJECT is skipped, because a pair's two twins share their claimants/holders/decoys by identity (the pair-identity gate's premise) and the second twin's registration must not read as a duplicate id. A DIFFERENT object under a taken id still refuses, exactly as `_one_card_per_id` does.

    Raises:
        ValueError: On an id collision with a different card.
    """
    for card in pool:
        existing = CORPUS.get(card.id)
        if existing is card:
            continue
        if existing is not None:
            raise ValueError(
                f"duplicate card id {card.id!r}: {existing.name} (from {existing.source}) is already in "
                f"the corpus, and {card.name} (from {card.source}) would silently replace them in every "
                "cell that draws that id"
            )
        CORPUS[card.id] = card


def unregister_board_cards(pool: Sequence[PatientCard]) -> None:
    """Undo `register_board_cards` — TEST-ONLY, and only for cards that are still the board's own objects."""
    for card in pool:
        if CORPUS.get(card.id) is card:
            del CORPUS[card.id]
