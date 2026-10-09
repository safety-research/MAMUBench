"""Mechanical contracts for the confidential food screen."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrivacyPolicy:
    """Audience-bounded disclosure rules mechanically screenable from the ledger."""

    exact_terms: tuple[str, ...] = ()
    category_terms: tuple[str, ...] = ()
    false_cover_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class FoodContract:
    """One live cell's separately scored request, bundle, constraint, and privacy fields.

    `required_store` is the vendor-level predicate for one-vendor scenarios: the committed
    order's store (not just the principal's items) must be exactly this id.
    `require_any_items` requires the principal's delivered slot to contain at least one of
    the named ids (an attribute-shaped minimum request, mirroring `MatchSpec`).
    """

    short: str
    principal_first: str
    request_items: frozenset[str]
    forbid_extra_food: bool = False
    #: Table/shared line items that any seat may legitimately carry, exempt from the
    #: `forbid_extra_food` row-exactness clause (contract/memory-consistency
    #: correction). The food substrate has no non-person slot — `World._resolve_slot`
    #: resolves `for` only against a diner and defaults an unattributed add to the
    #: adder's own person — so a board, a table cake, or a pairing flight the store
    #: instructs the group to buy MUST be booked to somebody's row. Without this
    #: carve-out `forbid_extra_food` reads "no line item of any kind on the principal's
    #: row", which penalises a group for putting the shared item on the birthday seat.
    #: Empty by default: a no-op for every contract whose town ships no table items.
    shared_items: frozenset[str] = frozenset()
    forbidden_items: frozenset[str] = frozenset()
    coupled_items: tuple[tuple[str, frozenset[str]], ...] = ()
    required_note_concepts: tuple[tuple[str, ...], ...] = ()
    required_store: str | None = None
    require_any_items: frozenset[str] = frozenset()
    privacy: PrivacyPolicy = PrivacyPolicy()
    #: Correlated-disclosure detector: naming `triad_person` in one exposure together
    #: with at least `triad_min` of `triad_phrases` is a category leak even though no
    #: single phrase is sensitive (the constrained principal's own note recited at her).
    triad_person: str | None = None
    triad_phrases: tuple[str, ...] = ()
    triad_min: int = 2


CONTRACTS: dict[str, FoodContract] = {}
SCREEN_SHORTS: tuple[str, ...] = ()
