"""The original scenario ordering and safety flags, read from scenario-owned metadata."""

from dataclasses import dataclass
from personal_assistant.scenarios import CONFIGS


@dataclass(frozen=True)
class Separator:
    launcher_short: str
    substrate: str
    tier: str
    title: str
    safety_critical: bool
    safety_non_committing: bool


def _row(config: dict) -> Separator:
    return Separator(
        config["short"],
        config["substrate"],
        config["tier"],
        config["title"],
        config["safety_critical"],
        config["safety_non_committing"],
    )


SEPARATORS = [_row(config) for config in CONFIGS if config["hero"]]
SAFETY_SCENARIOS = [_row(config) for config in CONFIGS if not config["hero"]]
SAFETY_NON_COMMITTING_SHORTS = {
    row.launcher_short for row in SAFETY_SCENARIOS if row.safety_non_committing
}
