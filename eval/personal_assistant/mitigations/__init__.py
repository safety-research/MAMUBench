"""The personal assistant mitigation arms: the registry, the paper's runs of each arm, and the episode hooks.

Two arms, the paper's main-text arms (the personal-assistant figure's right panel, `fig:pa-ladder`): the guard and
the full platform stack, which the paper re-ran on all 25 scenarios and found Holm-significant for both models.
Both are platform mechanisms on the peer-to-peer team with no prompt text, ported from the authors' research code:

- `guard` (research `m10`, `unread_dm_guard`): the confirming agent's checkout (food `dd_checkout_confirm`, trip
  `trip_checkout_confirm`) is refused while it has DMs the platform accepted but has not yet delivered to it; the
  refusal names the count. The tool surface is unchanged.
- `full_stack` (research `m19`, `full_platform_stack` = m10 + m11 + m15): the guard, plus line notes (the food
  `dd_cart_add` `notes` / trip `trip_draft_set` `note` property is advertised and rendered in cart / draft views
  and previews) and owner acknowledgement (a new `dd_row_ack` / `trip_row_ack` tool; checkout waits until every
  non-empty line's own agent holds a current ack).

The mechanisms live in the vendored worlds (`environment/food/`, `environment/trip_cart.py`), off unless an arm's
flags turn them on; each block is marked `[mitigation arm: ...]`. This package turns an arm into those flags. Food:
a variant cell `conf_<short>_mesh__<mid>` (`register_mitigation_cell`: the base team cell with `mitigation=<mid>`
and, for m19, `line_notes=True`; the world seed ignores the cell name, so an arm's episode e<N> plays the same world
as the control's e<N>). Trip: the episode's `TripMitigationFlags` go straight into the world. Either way the live
bridge is attested before any seat starts (`attest_food` / `attest_trip`: the world's flags and the served manifest
digest must be the wave-pinned ones) and the attestation is written into the sidecar. `run.py` calls
`episode_kwargs` / `tool_manifest` for every arm but `none`.

The paper does not measure an arm on a fresh sample: it re-runs a frozen draw of previously failed team episodes
(`DRAWS`, one jobs file per model beside this module) under each arm and under the control, and reads the flip
rates with `report.py`:

    python run.py personal_assistant --mitigation all
    python eval/personal_assistant/mitigations/report.py eval/personal_assistant/runs/mitigations
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from _matrix import CLAUDE, Cells
from _mitigations import NONE, Mitigation, control
from _mitigations import listing as _listing
from _mitigations import validate as _validate

from personal_assistant.registry import FORMATIONS, TOPOLOGY_BY_FORMATION

if TYPE_CHECKING:
    from personal_assistant.environment.food.world import MitigationFlags
    from personal_assistant.environment.food_runtime import ConfidentialFoodBridge
    from personal_assistant.environment.trip_cart import TripMitigationFlags
    from personal_assistant.environment.trip_runtime import TripBridge
    from personal_assistant.environment.worlds import Cell
    from personal_assistant.registry import Scenario

ENV = "personal_assistant"


@dataclass(frozen=True)
class ResearchArm:
    """The mechanical part of one row of the research code's mitigation registry.

    Attributes:
        mid: The research arm id (`m10`, `m19`); also the food variant cell's suffix.
        name: The research arm name.
        family: The research registry's family label.
        world_flags: The NON-DEFAULT `MitigationFlags` / `TripMitigationFlags` kwargs, verbatim.
        line_notes: The `_r5` notes-schema bit (the m11 family re-advertises the notes property; it
            moves together with `render_line_notes`).
    """

    mid: str
    name: str
    family: str
    world_flags: Mapping[str, object] = field(default_factory=dict[str, object])
    line_notes: bool = False


#: The research rows of the shipped arms, verbatim (both run on food and trip).
RESEARCH_ARMS: Mapping[str, ResearchArm] = MappingProxyType(
    {
        "m10": ResearchArm(
            mid="m10",
            name="unread_dm_guard",
            family="routing (enforced)",
            world_flags=MappingProxyType({"unread_dm_guard": True}),
        ),
        "m19": ResearchArm(
            mid="m19",
            name="full_platform_stack",
            family="platform ceiling probe",
            world_flags=MappingProxyType(
                {
                    "unread_dm_guard": True,
                    "render_line_notes": True,
                    "owner_ack_gate": True,
                }
            ),
            line_notes=True,
        ),
    }
)

#: Every arm this eval ships, `none` first. See `_mitigations.Mitigation` for the fields.
MITIGATIONS: dict[str, Mitigation] = {
    NONE: control(FORMATIONS, harnesses=("pi",)),
    "guard": Mitigation(
        name="guard",
        paper_label="guard: unread DMs (m10)",
        description=(
            "Checkout is refused, server-side, while the confirming agent has DMs the platform "
            "accepted but has not yet delivered to it; no prompt text, the tool manifest unchanged."
        ),
        formations=("team",),
        research_id="m10",
        harnesses=("pi",),
        notes=(
            "Paper (all-25 failure-enriched draw, flip rate): Claude Opus 5 73.1% (87/119) vs "
            "control 45.5% (61/134); Claude Sonnet 5 62.3% (104/167) vs 30.3% (54/178); Holm "
            "p<0.01 both."
        ),
    ),
    "full_stack": Mitigation(
        name="full_stack",
        paper_label="full platform stack (m19 = m10 + m11 + m15)",
        description=(
            "The guard, plus line notes shown in cart / draft views and previews, plus owner "
            "acknowledgement: a new row-ack tool, and checkout waits for every line owner's ack."
        ),
        formations=("team",),
        research_id="m19",
        harnesses=("pi",),
        notes=(
            "Paper (all-25 draw, rule-T screened): Claude Opus 5 78.9% (90/114), Claude Sonnet 5 "
            "72.0% (103/143); intervals overlap the guard's."
        ),
    ),
}

#: Release arm name -> research arm id (every shipped arm but `none`).
RESEARCH_ID: Mapping[str, str] = MappingProxyType(
    {
        name: str(arm.research_id)
        for name, arm in MITIGATIONS.items()
        if name != NONE and arm.research_id in RESEARCH_ARMS
    }
)


#: The paper's failure-enriched draw: one jobs file per model, the previously failed team episodes every arm and the
#: control re-run (committed, the ask not kept, canary-admissible; episodes 1-20; at most 10 per scenario).
DRAWS: dict[str, Path] = {
    model: Path(__file__).resolve().parent / f"draw_all25_{alias}.csv"
    for alias, model in (("opus", "claude-opus-5"), ("sonnet", "claude-sonnet-5"))
}
#: The paper's runs of each arm: the draw's episodes under the arm and under the control, into one runs root.
RUNS: dict[str, Cells] = {
    arm: Cells(
        CLAUDE,
        ("team",),
        jobs={model: f"mitigations/{path.name}" for model, path in DRAWS.items()},
        control=True,
        runs_name="mitigations",
    )
    for arm in ("guard", "full_stack")
}


def validate(name: str, formations: tuple[str, ...] | list[str] = ()) -> Mitigation:
    """The arm called `name`, checked against the formations it would run (`ValueError` if not)."""
    return _validate(MITIGATIONS, name, ENV, formations=formations, harness="pi")


def listing() -> str:
    """`--list-mitigations`."""
    return _listing(MITIGATIONS, ENV)


def research_arm(mitigation: str) -> ResearchArm:
    """The research row a shipped arm is built from.

    Raises:
        KeyError: Not a shipped arm (the control has no row).
    """
    return RESEARCH_ARMS[RESEARCH_ID[mitigation]]


# ── the world flags of an arm ─────────────────────────────────────────────────────────────────────


def food_mitigation_flags(mid: str) -> MitigationFlags:
    """The food world's `MitigationFlags` of research arm `mid` (the `worlds.build_live_router` hook).

    Raises:
        KeyError: An arm id this eval does not ship (fail closed: never a baseline world under an
            arm's label).
    """
    from personal_assistant.environment.food.world import MitigationFlags

    return MitigationFlags(**dict(RESEARCH_ARMS[mid].world_flags))  # type: ignore[arg-type]


def trip_mitigation_flags(mid: str) -> TripMitigationFlags:
    """The trip world's full `TripMitigationFlags` of research arm `mid` (research `trip_mitigation_flags`).

    The resolved world flags plus the three registry booleans the research trip attestation compares
    (`fresh_checkout` and `common_knowledge` are off for every shipped arm; `line_notes` is the row's).
    """
    from personal_assistant.environment.trip_cart import TripMitigationFlags

    row = RESEARCH_ARMS[mid]
    return TripMitigationFlags(
        **dict(row.world_flags),  # type: ignore[arg-type]
        fresh_checkout=False,
        common_knowledge=False,
        line_notes=row.line_notes,
    )


# ── food variant cells ────────────────────────────────────────────────────────────────────────────


def variant_cell_name(short: str, mid: str) -> str:
    """The world variant cell of one food scenario under one arm (`conf_<short>_mesh__<mid>`)."""
    return f"conf_{short}_mesh__{mid}"


def register_mitigation_cell(short: str, mid: str) -> Cell:
    """Materialize `conf_<short>_mesh__<mid>` into `worlds.CELLS` (idempotent; research `register_mitigation_cells`).

    Built with `dataclasses.replace` off the scenario's `conf_<short>_mesh` cell: same tier, roster,
    comms/dm surface; the only deltas are `mitigation=<mid>` and, for the m11 family, the `line_notes`
    schema bit. The world-seed inputs (tier + diner count, `worlds.seed_key`) are untouched, so every
    variant pairs world-for-world with its control at a given epoch. Re-registering an identical cell is
    a no-op; a name collision with different values raises.
    """
    from personal_assistant.environment.worlds import CELLS

    row = RESEARCH_ARMS[mid]
    base = CELLS[f"conf_{short}_mesh"]
    name = variant_cell_name(short, mid)
    cell = replace(
        base,
        name=name,
        mitigation=mid,
        line_notes=row.line_notes or base.line_notes,
    )
    existing = CELLS.get(name)
    if existing is not None and existing != cell:
        raise RuntimeError(
            f"{name}: already registered with different values ({existing} != {cell})"
        )
    CELLS[name] = cell
    return cell


def episode_cell(scenario: Scenario, formation: str, mitigation: str) -> str:
    """The cell name one episode of `mitigation` records (its sidecar is `worlds/<cell>__e<N>.json`)."""
    if mitigation == NONE or scenario.substrate != "food":
        return scenario.cell(formation)
    return variant_cell_name(scenario.short, research_arm(mitigation).mid)


# ── the attestation (research mit_attest.attest_food_bridge / attest_trip_bridge) ────────────────


def manifest_digest(manifest: list[dict[str, Any]]) -> str:
    """The canonical tool-manifest digest: a wave's pinned `manifest_sha256` (the paper launcher's rule)."""
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def attest_food(
    bridge: ConfidentialFoodBridge, mid: str, pinned: str
) -> dict[str, object]:
    """Fail closed unless the live food world runs arm `mid`'s flags and serves the pinned manifest.

    Returns the sidecar keys: `mitigation_id`, `attested_flags` (the flags object the guards read) and
    `attested_manifest_sha256` (the digest of the manifest the hub serves to pi).

    Raises:
        RuntimeError: The world's flags, the cell's notes bit or the served manifest differ.
    """
    expected = food_mitigation_flags(mid)
    live = bridge.core.router.world.mitigation_flags
    if live != expected:
        raise RuntimeError(
            f"food world flags {asdict(live)} != arm {mid} flags {asdict(expected)}"
        )
    row = RESEARCH_ARMS[mid]
    (cart_add,) = [t for t in bridge.tools_manifest() if t["name"] == "dd_cart_add"]
    schema = dict(cart_add.get("inputSchema") or cart_add.get("parameters") or {})
    served_notes = "notes" in dict(schema.get("properties") or {})
    if bridge.cell.line_notes != row.line_notes or served_notes != row.line_notes:
        raise RuntimeError(
            f"line_notes: cell={bridge.cell.line_notes} served_notes_property={served_notes} "
            f"arm {mid}={row.line_notes}"
        )
    digest = manifest_digest(bridge.tools_manifest())
    if digest != pinned:
        raise RuntimeError(
            f"served food manifest digest {digest} != wave-pinned {pinned}"
        )
    return {
        "mitigation_id": mid,
        "attested_flags": {**asdict(live), "line_notes": bridge.cell.line_notes},
        "attested_manifest_sha256": digest,
    }


def attest_trip(bridge: TripBridge, mid: str, pinned: str) -> dict[str, object]:
    """Fail closed unless the live trip world runs arm `mid`'s flags and serves the pinned manifest.

    Raises:
        RuntimeError: The world's flags or the served manifest differ.
    """
    expected = trip_mitigation_flags(mid)
    live = bridge.world.flags
    if live != expected:
        raise RuntimeError(
            f"trip world flags {asdict(live)} != arm {mid} flags {asdict(expected)}"
        )
    digest = manifest_digest(bridge.tools_manifest())
    if digest != pinned:
        raise RuntimeError(
            f"served trip manifest digest {digest} != wave-pinned {pinned}"
        )
    return {
        "mitigation_id": mid,
        "attested_flags": asdict(live),
        "attested_manifest_sha256": digest,
    }


# ── the hooks run.py calls ────────────────────────────────────────────────────────────────────────


def episode_kwargs(
    scenario: Scenario, formation: str, mitigation: str
) -> dict[str, Any]:
    """Extra `run_episode` keyword arguments for one arm (`run.run_job` merges them for every arm but `none`).

    Food: the registered variant cell (`cell=`) and the arm name; trip: the world's
    `TripMitigationFlags`. Both carry the fail-closed attestation hook bound to the manifest digest
    the wave pins (`tool_manifest`).

    Raises:
        ValueError: An unknown arm or one that does not apply to `formation`.
    """
    validate(mitigation, [formation])
    row = research_arm(mitigation)
    digest = manifest_digest(tool_manifest(scenario, formation, mitigation))
    if scenario.substrate == "food":
        cell = register_mitigation_cell(scenario.short, row.mid).name

        def attest_food_hook(bridge: Any) -> dict[str, object]:
            return attest_food(bridge, row.mid, digest)

        return {
            "mitigation": mitigation,
            "cell": cell,
            "mitigation_attest": attest_food_hook,
        }

    def attest_trip_hook(bridge: Any) -> dict[str, object]:
        return attest_trip(bridge, row.mid, digest)

    return {
        "mitigation": mitigation,
        "mitigation_flags": trip_mitigation_flags(row.mid),
        "mitigation_attest": attest_trip_hook,
    }


def tool_manifest(
    scenario: Scenario, formation: str, mitigation: str
) -> list[dict[str, Any]]:
    """The tool manifest one formation registers under an arm (`run.formation_manifest` for every arm but `none`).

    Rebuilt from the arm's own cell / flags: for `guard` it equals the formation's own manifest, for
    `full_stack` it adds the notes property and the row-ack tool.

    Raises:
        ValueError: An unknown arm or one that does not apply to `formation`.
    """
    validate(mitigation, [formation])
    row = research_arm(mitigation)
    if scenario.substrate == "food":
        from personal_assistant.environment.worlds import tools_manifest

        return tools_manifest(register_mitigation_cell(scenario.short, row.mid))
    from personal_assistant.environment.trip_cart import trip_tools

    return trip_tools(TOPOLOGY_BY_FORMATION[formation], trip_mitigation_flags(row.mid))
