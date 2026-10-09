"""The paper's merge-queue world, as the variant transforms of the authors' research code applied to a built cell.

The paper's merge-queue numbers ran on the research variant `noprio_nocaptain_subtle_stakes_briefs_only`
(captainless cells: solo, coordinator, the two teams and the captainless mitigation arms) and
`noprio_subtle_stakes_briefs_only` (the lead arms, whose fifth seat is a real team lead):

- `noprio`: no priority labels; one neutral `release:queued` label, so the queue is first-come;
  AGENTS.md, the owner voices and RELEASING.md scrubbed of rank vocabulary;
- `nocaptain`: captainless cells name no release captain anywhere (RELEASING.md rewritten agent-neutral);
- `subtle_stakes`: owners state only their own consequences (a CVE advisory tomorrow, two customer
  launches on Monday, the build team's cache toil, a docs schedule), never the triage;
- `briefs_only`: only the minute-0 owner brief is scheduled; the reply-only voicer answers when addressed.

The transforms rewrite a cell built by `_context.finalize` from the scenario's base world (priority labels
release:p0-p3, owners stating the triage, four scheduled owner beats), which is the research `control`
variant the paper's world was derived from; this eval runs only the paper's world. `apply_variant` runs
the enabled flags' transforms in declaration order after `_context.finalize`, exactly as research
`variants.build_cell` does (`apply_variant(finalize(...))`); `releasing_md` is the RELEASING.md the flags
overlay into every clone.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from merge_queue.scenarios._world import (
    briefs_only,
    nocaptain,
    noprio,
    subtle_stakes,
)
from merge_queue.scenarios._world.flags import (
    PAPER_CAPTAINED,
    PAPER_CAPTAINLESS,
    WorldFlags,
    check_flag_compat,
)

if TYPE_CHECKING:
    from merge_queue.environment.resources import ScenarioConfig

#: The world every episode runs (recorded as `world` in each run dir's `config.json`).
PAPER = "paper"

Transform = Callable[["ScenarioConfig", WorldFlags], "ScenarioConfig"]

#: flag -> transform of the world's own flags, in `WorldFlags` declaration order.
WORLD_TRANSFORMS: dict[str, Transform] = {
    "noprio": noprio.transform,
    "nocaptain": nocaptain.transform,
    "subtle_stakes": subtle_stakes.transform,
    "briefs_only": briefs_only.transform,
}


def transforms() -> dict[str, Transform]:
    """flag -> transform for every `WorldFlags` flag, in declaration order (the order `apply_variant` runs them).

    The world's own flags, then the mitigation arms' clause flags (imported here, not at module load, so the
    mitigations package can build on the world without an import cycle).
    """
    # [mitigation arm: lead_cut_line, priorities, charter, charter_stakes] the arms' AGENTS.md clause transforms
    from merge_queue.mitigations.clauses import TRANSFORMS as CLAUSE_TRANSFORMS

    out = {**WORLD_TRANSFORMS, **CLAUSE_TRANSFORMS}
    if tuple(out) != tuple(WorldFlags.__dataclass_fields__):
        raise ValueError("the transforms must list every WorldFlags flag in declaration order")
    return out

#: The fixture's RELEASING.md (priority labels, a named captain), which `releasing_md` rewrites.
RELEASING_SOURCE = (
    Path(__file__).resolve().parents[2]
    / "environment"
    / "fixture"
    / "repo_files"
    / "RELEASING.md"
)


def base_flags(topology: str) -> WorldFlags:
    """The paper's world variant a cell of `topology` runs: the captained base on a lead cell, else captainless."""
    return PAPER_CAPTAINED if topology == "live_captain" else PAPER_CAPTAINLESS


def apply_variant(config: ScenarioConfig, flags: WorldFlags) -> ScenarioConfig:
    """Apply `flags`' transforms, in declaration order, to a finalized cell (no flags returns it unchanged)."""
    check_flag_compat(flags)
    table = transforms()
    for flag in flags.enabled_flags():
        config = table[flag](config, flags)
    return config


def releasing_md(flags: WorldFlags, source: Path = RELEASING_SOURCE) -> str | None:
    """The RELEASING.md every clone of a `flags` cell carries, or None when the fixture's file stands.

    The research transforms rewrote the fixture overlay process-wide (raw -> noprio iff on -> nocaptain
    iff on); the driver writes this text into the seed repository before its history is committed
    (`build_fixture(releasing_md=...)`), the same point.
    """
    if not (flags.noprio or flags.nocaptain):
        return None
    text = source.read_text(encoding="utf-8")
    if flags.noprio:
        text = noprio.noprio_releasing_text(text)
    if flags.nocaptain:
        text = nocaptain.nocaptain_releasing_text(text)
    return text


__all__ = [
    "PAPER",
    "PAPER_CAPTAINED",
    "PAPER_CAPTAINLESS",
    "RELEASING_SOURCE",
    "WORLD_TRANSFORMS",
    "WorldFlags",
    "apply_variant",
    "base_flags",
    "releasing_md",
    "transforms",
]
