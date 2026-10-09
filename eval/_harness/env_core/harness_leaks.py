"""Reusable blocklist scanner for text exposed by deterministic environments."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextSurface:
    """One labelled string that an environment can expose to a target."""

    source: str
    text: str


@dataclass(frozen=True)
class LeakRule:
    """A named case-insensitive regular expression that target text must not match."""

    name: str
    pattern: str


@dataclass(frozen=True)
class LeakAllowance:
    """One narrowly scoped legitimate match, with its required rationale."""

    source_pattern: str
    text_pattern: str
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("a leak allowance requires a non-empty reason")


@dataclass(frozen=True)
class LeakFinding:
    """A blocklist match that was not covered by an explicit allowance."""

    surface: TextSurface
    rule: LeakRule
    start: int
    end: int

    @property
    def matched_text(self) -> str:
        """The exact substring of `surface.text` that matched `rule`."""
        return self.surface.text[self.start : self.end]


def find_harness_leaks(
    surfaces: tuple[TextSurface, ...],
    rules: tuple[LeakRule, ...],
    allowances: tuple[LeakAllowance, ...] = (),
) -> tuple[LeakFinding, ...]:
    """Return every unallowed blocklist match in `surfaces`.

    An allowance suppresses only matches contained inside its `text_pattern` and only on sources matching its `source_pattern`. This prevents a legitimate phrase from exempting a whole surface or token.

    Args:
        surfaces: Labelled target-visible strings to scan.
        rules: Case-insensitive blocked patterns.
        allowances: Narrow source-and-text exceptions, each with a rationale.

    Returns:
        All unallowed findings, in surface/rule/match order.
    """
    findings: list[LeakFinding] = []
    for surface in surfaces:
        allowed_spans = _allowed_spans(surface, allowances)
        for rule in rules:
            for match in re.finditer(rule.pattern, surface.text, flags=re.IGNORECASE):
                if _is_allowed(allowed_spans, match.start(), match.end()):
                    continue
                findings.append(
                    LeakFinding(
                        surface=surface,
                        rule=rule,
                        start=match.start(),
                        end=match.end(),
                    )
                )
    return tuple(findings)


def _allowed_spans(
    surface: TextSurface, allowances: tuple[LeakAllowance, ...]
) -> list[tuple[int, int]]:
    """The `(start, end)` spans in `surface.text` covered by a matching allowance."""
    spans: list[tuple[int, int]] = []
    for allowance in allowances:
        if re.search(allowance.source_pattern, surface.source, re.IGNORECASE) is None:
            continue
        for allowed_match in re.finditer(
            allowance.text_pattern, surface.text, flags=re.IGNORECASE
        ):
            spans.append((allowed_match.start(), allowed_match.end()))
    return spans


def _is_allowed(allowed_spans: list[tuple[int, int]], start: int, end: int) -> bool:
    return any(
        span_start <= start and end <= span_end
        for span_start, span_end in allowed_spans
    )


def format_leak_findings(findings: tuple[LeakFinding, ...]) -> str:
    """Format findings with compact source-local context for an assertion message."""
    lines: list[str] = []
    for finding in findings:
        start = max(0, finding.start - 60)
        context = finding.surface.text[start : finding.end + 60].replace("\n", "\\n")
        lines.append(
            f"- {finding.surface.source}: {finding.rule.name} matched "
            f"{finding.matched_text!r} in {context!r}"
        )
    return "\n".join(lines)


def shingles(text: str, n: int = 6) -> set[tuple[str, ...]]:
    """Every contiguous `n`-word shingle of `text`, lowercased and stripped of punctuation.

    The unit the leak checks compare authored prose on: an n-word overlap between two surfaces is evidence
    that one was copied into the other (a broadcast cast list, a templated operator reply), where a shorter
    match is just English. Callers pass the `n` their finding was stated in — 6 everywhere today.
    """
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


__all__ = [
    "LeakAllowance",
    "LeakFinding",
    "LeakRule",
    "TextSurface",
    "find_harness_leaks",
    "format_leak_findings",
    "shingles",
]
