"""The eval's surface — scenarios, formations, models — read from the environment's registries.

The 25 scenarios of record are `separators.SEPARATORS` (the 16 original scenarios) plus
`separators.SAFETY_SCENARIOS` (the 9 safety scenarios). Nothing here re-declares a scenario:
a row's runner key is its `launcher_short`, the same key `food_run.py` / `trip_run.py` dispatch on,
and cell names come from those runners' own constructors.
"""

from __future__ import annotations

from dataclasses import dataclass

from _providers import THINKING_BY_PROVIDER
from _providers import provider_for as _provider_by_id

from personal_assistant._paths import bootstrap

bootstrap()

from personal_assistant.environment import food_run, trip_cart, trip_run  # noqa: E402
from personal_assistant.environment.ladder_report import ARMS  # noqa: E402
from personal_assistant.environment.separators import (  # noqa: E402
    SAFETY_NON_COMMITTING_SHORTS,
    SAFETY_SCENARIOS,
    SEPARATORS,
    Separator,
)
from personal_assistant.environment.worlds import CELLS  # noqa: E402

#: Eval-facing formation names -> the cell topology suffix, from the environment's own mapping
#: (`ladder_report.ARMS`). `solo` is deliberately absent: it is a formation for one fiction only.
FORMATIONS: tuple[str, ...] = ("coordinator", "team", "team_silent")
TOPOLOGY_BY_FORMATION: dict[str, str] = {
    formation: topology
    for topology, formation in ARMS.items()
    if formation in FORMATIONS
}
FORMATION_BY_TOPOLOGY: dict[str, str] = {v: k for k, v in TOPOLOGY_BY_FORMATION.items()}
DEFAULT_FORMATIONS: tuple[str, ...] = ("coordinator", "team")

#: The environment's target aliases (`opus` -> `claude-opus-5`, `sol` -> `gpt-5.6-sol`, ...), shared
#: by both substrate runners; used for the reference tables and accepted on `--model`.
MODEL_ALIASES: dict[str, str] = dict(food_run.TARGETS)
#: The provider each of the environment's model ids runs on (`food_run.PROVIDERS`, keyed by id here).
PROVIDER_BY_MODEL: dict[str, str] = {
    model: food_run.PROVIDERS[alias] for alias, model in MODEL_ALIASES.items()
}
assert THINKING_BY_PROVIDER == food_run.THINKING_BY_PROVIDER, (
    "eval/_providers.py and the campaign runtime disagree on thinking defaults"
)


@dataclass(frozen=True)
class Scenario:
    """One scenario of record and how the runners address it."""

    short: str
    substrate: str
    tier: str
    title: str
    safety_critical: bool
    safety_non_committing: bool

    def cell(self, formation: str) -> str:
        """The stable cell name for one formation (the sidecar's `cell` field), per the runner."""
        topology = TOPOLOGY_BY_FORMATION[formation]
        if self.substrate == "food":
            return food_run.cell_name(self.short, topology)
        return f"{trip_run.cell_prefix(self.short)}_{topology}"

    @property
    def cell_prefix(self) -> str:
        """The cell-name stem shared by every formation (`conf_<short>` / `trip_<short>`)."""
        return self.cell("team").removesuffix(f"_{TOPOLOGY_BY_FORMATION['team']}")

    @property
    def formations(self) -> tuple[str, ...]:
        """The formations this scenario is wired for.

        `team_silent` (comms-off team) exists where the food registry carries the `_mesh_nc`
        cell, and on the seven trip scenarios `trip_cart.TRIP_NC_SHORTS` allowlists (the
        silent-trips port), i.e. on all 25.
        """
        if self.substrate == "food" and self.cell("team_silent") in CELLS:
            return (*DEFAULT_FORMATIONS, "team_silent")
        if self.substrate == "trip" and self.short in trip_cart.TRIP_NC_SHORTS:
            return (*DEFAULT_FORMATIONS, "team_silent")
        return DEFAULT_FORMATIONS


def _row(sep: Separator) -> Scenario:
    return Scenario(
        short=sep.launcher_short,
        substrate=sep.substrate,
        tier=sep.tier,
        title=sep.title,
        safety_critical=sep.safety_critical,
        safety_non_committing=sep.safety_non_committing,
    )


#: Registry order = the 16 original scenarios, then the 9 safety scenarios.
SCENARIOS: dict[str, Scenario] = {
    row.short: row for row in (_row(sep) for sep in (*SEPARATORS, *SAFETY_SCENARIOS))
}
HERO_SHORTS: tuple[str, ...] = tuple(sep.launcher_short for sep in SEPARATORS)
SAFETY_SHORTS: tuple[str, ...] = tuple(sep.launcher_short for sep in SAFETY_SCENARIOS)
#: Re-exported so scoring code has one import for the flagged four.
SAFETY_NON_COMMITTING: frozenset[str] = frozenset(SAFETY_NON_COMMITTING_SHORTS)


def scenario(short: str) -> Scenario:
    """Look one scenario up by its launcher short; a typo names the registry, not a KeyError."""
    try:
        return SCENARIOS[short]
    except KeyError:
        raise SystemExit(
            f"unknown scenario {short!r}; the 25 of record are: {', '.join(SCENARIOS)}"
        ) from None


def model_id(name: str) -> str:
    """Resolve a model alias (`sonnet`, `terra`, ...) or pass a pi model id through."""
    return MODEL_ALIASES.get(name, name)


def provider_for(model: str, explicit: str | None = None) -> str:
    """The pi provider a model id runs on: the environment's own table, else the shared inference."""
    if explicit is None and model in PROVIDER_BY_MODEL:
        return PROVIDER_BY_MODEL[model]
    return _provider_by_id(model, explicit)


def resolve_thinking(provider: str, requested: str | None) -> str:
    """The pi thinking level to run: the environment's default unless overridden, gate-validated."""
    value = requested if requested is not None else THINKING_BY_PROVIDER[provider]
    return food_run.validate_thinking(value, provider)
