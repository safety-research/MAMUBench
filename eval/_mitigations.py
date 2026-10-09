"""Mitigation arms shared by the four evals: the registry record, the run-dir stamp and the report keying.

Each eval keeps its mitigations in one package, `eval/<env>/mitigations/`: the arms as `MITIGATIONS: dict[str,
Mitigation]`, always with the control arm `none` (the formation exactly as the benchmark defines it), the runs the
paper made of each arm (`RUNS`), and the texts and hooks that build an arm's episode. `python run.py <env>
--mitigation all` plays every arm's paper runs, `--mitigation NAME` one arm's; the eval's own runner and
`modal_app.py` take `--mitigation NAME`, and a `--jobs-file` names an arm per episode (see `_jobs.py`).

Three rules keep arms apart everywhere downstream:

- **Run dirs**: `stamp(name)` is appended to the cell part of a run-dir name (`<cell>__mit-<name>__<model>
  __e<N>...`) and to personal_assistant's wave dir, and is empty for `none`, so every run dir banked before
  mitigations existed keeps its name and its resume path.
- **Records**: an arm's `config.json` / `wave_config.json` carries `"mitigation": "<name>"`; the control arm
  records nothing new (the simulated harness has always written `"mitigation": null`), so a DONE-skip never
  sees drift on a control run. `of(record)` reads any of these back as a name, `none` when absent.
- **Reports**: a cell is keyed by (scenario, formation, model, mitigation), pooled and contrast rows are
  computed per mitigation (`partition`), and `check.py` compares a mitigation cell only with a reference
  cell of the same mitigation (a reference cell without the key is a control cell).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

#: The control arm: no mitigation, the formation as the benchmark defines it.
NONE = "none"
#: `--mitigation all` on the root launcher: every arm's paper runs in one launch (never an arm's name).
ALL = "all"
#: The marker `stamp` puts between the cell and the rest of a run-dir name.
STAMP_PREFIX = "__mit-"
#: Characters an arm name may use (it lands in directory names and in the merge queue's run-dir grammar).
NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")

T = TypeVar("T")


@dataclass(frozen=True)
class Mitigation:
    """One mitigation arm of one eval.

    Attributes:
        name: The CLI name (`--mitigation NAME`), lowercase `[a-z0-9_]`; `none` is the control arm.
        paper_label: How the paper (or its appendix) names the arm, e.g. "team + lead + value".
        description: One or two sentences on what the arm changes (prompt, tool, guard, extra seat).
        formations: The formations the arm applies to (its runs are keyed under these formations).
        research_id: The arm's id in the authors' research code (`on_m1_mesh`, `r2_stack_s11`, ...), `None`
            for the control arm.
        harnesses: The harnesses the arm is implemented for (`pi`, `sim`).
        notes: Anything a reader needs beside the description (provenance, caveats, the paper's number).
    """

    name: str
    paper_label: str
    description: str
    formations: tuple[str, ...]
    research_id: str | None
    harnesses: tuple[str, ...] = ("pi", "sim")
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.name or set(self.name) - NAME_CHARS or self.name == ALL:
            raise ValueError(
                f"mitigation name {self.name!r} must be non-empty lowercase [a-z0-9_], not {ALL!r}"
            )
        if not self.formations:
            raise ValueError(f"mitigation {self.name!r} applies to no formation")


def control(formations: Iterable[str], harnesses: Iterable[str]) -> Mitigation:
    """The `none` entry every registry starts with: every formation, every harness, the paper's control."""
    return Mitigation(
        name=NONE,
        paper_label="control (no mitigation)",
        description="The formation exactly as the benchmark defines it; the control every arm is read against.",
        formations=tuple(formations),
        research_id=None,
        harnesses=tuple(harnesses),
    )


def lookup(registry: Mapping[str, Mitigation], name: str, env: str) -> Mitigation:
    """The arm called `name`, or a `ValueError` that lists the registry."""
    try:
        return registry[name]
    except KeyError:
        raise ValueError(
            f"unknown {env} mitigation {name!r}; available: {', '.join(registry)} "
            f"(see --list-mitigations)"
        ) from None


def validate(
    registry: Mapping[str, Mitigation],
    name: str,
    env: str,
    *,
    formations: Iterable[str] = (),
    harness: str | None = None,
) -> Mitigation:
    """`lookup`, plus: every formation given is one the arm applies to, and the arm runs on `harness`.

    Raises:
        ValueError: An unknown arm, a formation it does not apply to, or a harness it is not built for.
    """
    arm = lookup(registry, name, env)
    foreign = [f for f in formations if f not in arm.formations]
    if foreign:
        raise ValueError(
            f"{env} mitigation {name!r} applies to formation(s) {', '.join(arm.formations)}, "
            f"not {', '.join(foreign)}"
        )
    if harness is not None and harness not in arm.harnesses:
        raise ValueError(
            f"{env} mitigation {name!r} is implemented for the {'/'.join(arm.harnesses)} harness, "
            f"not {harness}"
        )
    return arm


def listing(registry: Mapping[str, Mitigation], env: str) -> str:
    """The registry as text (`--list-mitigations`)."""
    lines = [f"{env} mitigations ({len(registry)}):"]
    for arm in registry.values():
        lines.append(
            f"  {arm.name:20} {arm.paper_label}  "
            f"formations={','.join(arm.formations)} harness={','.join(arm.harnesses)}"
        )
        lines.append(f"  {'':20} {arm.description}")
        if arm.notes:
            lines.append(f"  {'':20} {arm.notes}")
    return "\n".join(lines)


def stamp(name: str) -> str:
    """The run-dir stamp of an arm: empty for the control arm, `__mit-<name>` otherwise."""
    return "" if name == NONE else f"{STAMP_PREFIX}{name}"


def label(name: str) -> str:
    """A display suffix for report and check lines: empty for the control arm, ` [mitigation <name>]` otherwise."""
    return "" if name == NONE else f" [mitigation {name}]"


def of(record: Mapping[str, Any] | None) -> str:
    """The arm a record (config, reference cell, report row) names; `none` when absent, null or empty."""
    if not record:
        return NONE
    value = record.get("mitigation")
    return str(value) if value else NONE


def partition(
    items: Iterable[T], key: Callable[[T], str] | None = None
) -> dict[str, list[T]]:
    """Items grouped by arm, the control arm first, then by name; input order is kept within an arm.

    `key` maps an item to its arm; the default reads `item["mitigation"]` through `of`.
    """

    def default_key(item: T) -> str:
        return of(item if isinstance(item, Mapping) else None)  # pyright: ignore[reportUnknownArgumentType]

    read = key or default_key
    groups: dict[str, list[T]] = {}
    for item in items:
        groups.setdefault(read(item), []).append(item)
    return {name: groups[name] for name in sorted(groups, key=lambda n: (n != NONE, n))}


def cells_of(cells: Iterable[Mapping[str, Any]], name: str) -> list[dict[str, Any]]:
    """The reference cells of one arm (a cell without a `mitigation` key is a control cell)."""
    return [dict(cell) for cell in cells if of(cell) == name]


def arms_of(*groups: Iterable[Mapping[str, Any]]) -> list[str]:
    """Every arm named across `groups` of records, the control arm first (`partition`'s order)."""
    names = {of(record) for group in groups for record in group}
    return sorted(names, key=lambda n: (n != NONE, n))


def arm_columns(
    columns: Iterable[str], rows: Iterable[Mapping[str, Any]], *, after: str
) -> tuple[str, ...]:
    """`columns` with `mitigation` inserted after `after` when any row names an arm besides the control arm.

    The reports' markdown views stay as they were for a control-only run and gain the column once an
    arm is present (the CSVs always carry it).
    """
    out = tuple(columns)
    if all(of(row) == NONE for row in rows) or "mitigation" in out:
        return out
    index = out.index(after) + 1
    return (*out[:index], "mitigation", *out[index:])


def tag(rows: Iterable[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    """Set every row's `mitigation` column to `name` in place (keeping the column order); returns the rows."""
    out = list(rows)
    for row in out:
        row["mitigation"] = name
    return out
