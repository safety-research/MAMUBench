"""The paper's clinic statistic: scenario-averaged joint success, with the paper's whole-episode bootstraps.

A scenario's rate pools the contests of all its episodes (`joint / contests`); a cell of the paper (one model,
formation and arm, per information condition) is the UNWEIGHTED mean of its scenarios' rates: 12 scenarios for
assembled (`plain`) or scattered (`split`) facts, 24 for both. The 95% interval resamples whole episodes with
replacement within each scenario, 2,000 draws, recomputes the average on every draw and takes the 2.5th and
97.5th percentiles.

The paper computed this in three scripts that seed and order their draws differently; `SCHEMES` ports each one
exactly, so the frozen per-episode table reproduces every printed interval to the digit
(`tests/test_reference_paper.py`), and a new run of the same cell is bootstrapped the same way:

- `corpus`, the coordinator and the peer-to-peer team (the paper's scenario-average script and, per scenario,
  its per-scenario appendix table): pooled `default_rng([20260908, model, formation,
  condition, column])`, a (2000 x episodes) index block per scenario, the assembled scenarios then the
  scattered ones, episodes in `episode_id` order (`e1, e10, e11, ...`); per scenario
  `default_rng([20260908, model, formation, twin, family])`.
- `silent`, the silent team (the paper's silent-team analysis): pooled
  `default_rng([20260908, model, 10, condition])` over the scenarios in board-id order, episodes by epoch;
  per scenario `default_rng([20260908, model, 90, board])`.
- `mitigation`, s1-s3 (the paper's mitigation figure and its per-scenario appendix table): pooled `default_rng([20260908, model, arm,
  condition])` drawing one episode set per replicate, scenarios in board-id order; per scenario
  `default_rng([20260908, model, board])`.

Indices: model = position in `PAPER_MODELS` (another model gets a stable index past them); formation
coordinator 0 / team 1; condition assembled 0 / scattered 1 / both 2; family = position among the 12 sorted
families; board = position among the 24 sorted board ids; arm = the figure's order (coordinator 0, control 1,
s1 2, s2 3, s3 4). Only numpy is needed (a hard dependency of the pinned inspect-ai).

The paper's silent-team contrasts are PAIRED (`paired_contrast` here; `silent_analysis.py` `boot_paired` in the
paper's analysis scripts, supplementary material): the silent team minus the peer-to-peer team (or the coordinator)
over the episodes both ran, per scenario the same epochs on both sides; one draw resamples the pairs within each
scenario and applies them to both arms, scenarios in board-id order, episodes by epoch,
`default_rng([20260908, model, comparison, condition])` with comparison team 0 / coordinator 2
(`silent_minus_team` / `silent_minus_coordinator`).
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

SEED = 20260908
REPS = 2000
#: The paper's five clinic models, in its scripts' order (the release's model ids).
PAPER_MODELS: tuple[str, ...] = (
    "claude-opus-5",
    "claude-sonnet-5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "qwen3.8-max",
)
#: The paper scripts' own model keys, same order (`opus-5`, ...; the mitigation scripts use `opus` / `sonnet`).
PAPER_MODEL_KEYS: tuple[str, ...] = (
    "opus-5",
    "sonnet-5",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "qwen3.8-max",
)
#: Information conditions: the paper's names, the boards' twins, and the pooled "both".
CONDITIONS: tuple[str, ...] = ("assembled", "scattered", "both")
TWIN_OF: dict[str, str] = {"assembled": "plain", "scattered": "split"}
CONDITION_OF_TWIN: dict[str, str] = {"plain": "assembled", "split": "scattered"}
#: The figure order of the mitigation arms (`ARMS` of the paper's `mitigation_cells.py`).
MITIGATION_ARM_INDEX: dict[str, int] = {
    "coordinator": 0,
    "control": 1,
    "s1": 2,
    "s2": 3,
    "s3": 4,
}
FORMATION_INDEX: dict[str, int] = {"coordinator": 0, "team": 1}

Scheme = Literal["corpus", "silent", "mitigation"]
SCHEMES: tuple[Scheme, ...] = ("corpus", "silent", "mitigation")


@dataclass(frozen=True)
class Morning:
    """One episode's contest counts: `joint` successes, `met` deadlines, `n` urgent contests, and its epoch."""

    epoch: int
    joint: int
    met: int
    n: int


@dataclass(frozen=True)
class Average:
    """A scenario average and its interval, in percent (`nan` bounds without an interval)."""

    pct: float
    lo: float
    hi: float
    n_scenarios: int
    n_episodes: int
    n_contests: int
    joint: int
    met: int
    met_pct: float
    method: str


def family_of(board: str) -> str:
    """`warfarin_inr_split` -> `warfarin_inr`."""
    return board.rsplit("_", 1)[0]


def twin_of(board: str) -> str:
    """`warfarin_inr_split` -> `split`."""
    return board.rsplit("_", 1)[1]


def model_index(model: str) -> int:
    """The model's index in the paper's scripts; a model the paper did not run gets a stable index past them."""
    if model in PAPER_MODELS:
        return PAPER_MODELS.index(model)
    if model in PAPER_MODEL_KEYS:
        return PAPER_MODEL_KEYS.index(model)
    return len(PAPER_MODELS) + zlib.crc32(model.encode()) % 1000


def scheme_for(formation: str, mitigation: str) -> Scheme:
    """Which paper script bootstraps a cell: a mitigation arm, the silent team, else the corpus of record."""
    if mitigation != "none":
        return "mitigation"
    if formation == "team_silent":
        return "silent"
    return "corpus"


def order_mornings(mornings: Sequence[Morning], scheme: Scheme) -> list[Morning]:
    """Episodes in the order the scheme's script stacked them (`episode_id` string order for the corpus)."""
    if scheme == "corpus":
        return sorted(mornings, key=lambda m: f"e{m.epoch}")
    return sorted(mornings, key=lambda m: m.epoch)


def order_boards(boards: Sequence[str], scheme: Scheme, condition: str) -> list[str]:
    """Scenarios in the order the scheme's script drew them (the corpus puts every assembled one first)."""
    if scheme == "corpus" and condition == "both":
        return sorted(boards, key=lambda b: (twin_of(b) != "plain", family_of(b)))
    return sorted(boards)


def in_condition(board: str, condition: str) -> bool:
    """True when `board` belongs to the condition (`both` holds every board)."""
    return condition == "both" or twin_of(board) == TWIN_OF[condition]


def _array(mornings: Sequence[Morning]) -> NDArray[np.int64]:
    return np.array([[m.joint, m.n] for m in mornings], dtype=np.int64)


def _rate(values: NDArray[np.int64]) -> float:
    return float(values[:, 0].sum()) / float(values[:, 1].sum())


def pooled_seed(
    scheme: Scheme, model: str, formation: str, mitigation: str, condition: str
) -> list[int]:
    """The `default_rng` seed of a pooled (scenario-averaged) interval under `scheme`."""
    mi = model_index(model)
    ci = CONDITIONS.index(condition)
    if scheme == "corpus":
        return [SEED, mi, FORMATION_INDEX.get(formation, 2), ci, 1]
    if scheme == "silent":
        return [SEED, mi, 10, ci]
    # the mitigation figure's own references: the coordinator and the team with nothing added (`control`)
    arm = (
        mitigation
        if mitigation != "none"
        else ("coordinator" if formation == "coordinator" else "control")
    )
    return [SEED, mi, MITIGATION_ARM_INDEX.get(arm, 5), ci]


def cell_seed(
    scheme: Scheme,
    model: str,
    formation: str,
    board: str,
    boards_of_record: Sequence[str],
) -> list[int]:
    """The `default_rng` seed of one scenario's interval under `scheme`."""
    mi = model_index(model)
    ordered = sorted(boards_of_record)
    bi = ordered.index(board) if board in ordered else len(ordered)
    if scheme == "corpus":
        families = sorted({family_of(b) for b in boards_of_record})
        fam = family_of(board)
        si = families.index(fam) if fam in families else len(families)
        ti = ("plain", "split").index(twin_of(board))
        return [SEED, mi, FORMATION_INDEX.get(formation, 2), ti, si]
    if scheme == "silent":
        return [SEED, mi, 90, bi]
    return [SEED, mi, bi]


def scenario_average(
    per_board: Mapping[str, Sequence[Morning]],
    *,
    scheme: Scheme,
    seed: Sequence[int],
    reps: int = REPS,
    condition: str = "both",
) -> Average:
    """The scenario-averaged joint success of `per_board` (board -> its episodes) with the scheme's interval.

    Every board with at least one episode and one contest counts once; a board without either is left out, and
    with no board left the result is all `nan`.
    """
    boards = order_boards(
        [b for b, ms in per_board.items() if ms and sum(m.n for m in ms)],
        scheme,
        condition,
    )
    if not boards:
        nan = math.nan
        return Average(nan, nan, nan, 0, 0, 0, 0, 0, nan, method(scheme, reps))
    arrays = [_array(order_mornings(per_board[b], scheme)) for b in boards]
    rates = [_rate(a) for a in arrays]
    met_rates = [
        sum(m.met for m in per_board[b]) / sum(m.n for m in per_board[b])
        for b in boards
    ]
    if scheme == "mitigation":
        # fig08 `scenario_average`: a Python sum over the scenarios, then the mean.
        point, met_point = sum(rates) / len(rates), sum(met_rates) / len(met_rates)
    else:
        point, met_point = float(np.mean(rates)), float(np.mean(met_rates))
    rng = np.random.default_rng(list(seed))
    total = np.zeros(reps)
    if scheme == "mitigation":
        # fig08 `draws`: one resampled episode set per replicate, every scenario in turn.
        for r in range(reps):
            for a in arrays:
                drawn = a[rng.integers(0, len(a), size=len(a))]
                total[r] += float(drawn[:, 0].sum()) / float(drawn[:, 1].sum())
    else:
        for a in arrays:
            idx = rng.integers(0, len(a), size=(reps, len(a)))
            drawn = a[idx]
            total += drawn[:, :, 0].sum(axis=1) / drawn[:, :, 1].sum(axis=1)
    if scheme == "corpus":
        lo, hi = np.percentile(total / len(arrays), [2.5, 97.5])
        lo_pct, hi_pct = 100 * float(lo), 100 * float(hi)
    else:
        lo, hi = np.percentile(100 * total / len(arrays), [2.5, 97.5])
        lo_pct, hi_pct = float(lo), float(hi)
    mornings = [m for b in boards for m in per_board[b]]
    return Average(
        pct=100 * point,
        lo=lo_pct,
        hi=hi_pct,
        n_scenarios=len(boards),
        n_episodes=len(mornings),
        n_contests=sum(m.n for m in mornings),
        joint=sum(m.joint for m in mornings),
        met=sum(m.met for m in mornings),
        met_pct=100 * met_point,
        method=method(scheme, reps),
    )


def cell_interval(
    mornings: Sequence[Morning],
    *,
    scheme: Scheme,
    seed: Sequence[int],
    reps: int = REPS,
) -> tuple[float, float]:
    """One scenario's 95% interval of its pooled joint rate, in percent (the paper's per-scenario whiskers)."""
    if not mornings or not sum(m.n for m in mornings):
        return (math.nan, math.nan)
    a = _array(order_mornings(mornings, scheme))
    rng = np.random.default_rng(list(seed))
    idx = rng.integers(0, len(a), size=(reps, len(a)))
    drawn = a[idx]
    if scheme == "corpus":
        rates = drawn[:, :, 0].sum(axis=1) / drawn[:, :, 1].sum(axis=1)
        lo, hi = np.percentile(rates, [2.5, 97.5])
        return (100 * float(lo), 100 * float(hi))
    rates = 100 * drawn[:, :, 0].sum(axis=1) / drawn[:, :, 1].sum(axis=1)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return (float(lo), float(hi))


def method(scheme: Scheme, reps: int = REPS) -> str:
    """How a scheme's interval is drawn, for the tables' `ci_method` column."""
    return f"whole-episode bootstrap within scenario ({scheme} scheme), {reps} draws, seed {SEED}"


# ── the paper's paired silent-team contrasts ─────────────────────────────────────────────────────────

#: The formations the silent team is paired against, and each comparison's RNG index in `silent_analysis.py`
#: `COMPARISONS` (`silent_minus_team` 0, `silent_minus_coordinator` 2).
PAIRED_COMPARISON_INDEX: dict[str, int] = {"team": 0, "coordinator": 2}
#: The paper's own names for the two comparisons (`comparisons.csv` `comparison`).
PAIRED_PAPER_LABEL: dict[str, str] = {
    "team": "silent_minus_team",
    "coordinator": "silent_minus_coordinator",
}


@dataclass(frozen=True)
class Paired:
    """The silent team minus a reference formation over matched episodes, in percent (`nan` without a pair).

    `silent_*` / `reference_*` are each arm's scenario average over the pairs with its paired-draw interval;
    `diff`, `lo`, `hi` the difference and its interval; `silent_ahead` / `reference_ahead` / `ties` count the
    scenarios by the sign of their rate difference.
    """

    silent_pct: float
    silent_lo: float
    silent_hi: float
    reference_pct: float
    reference_lo: float
    reference_hi: float
    diff: float
    lo: float
    hi: float
    n_scenarios: int
    n_pairs: int
    silent_ahead: int
    reference_ahead: int
    ties: int
    method: str


def paired_seed(model: str, reference_formation: str, condition: str) -> list[int]:
    """The `default_rng` seed of one paired contrast (`silent_analysis.py`: `[SEED, mi, ai, ci]`)."""
    return [
        SEED,
        model_index(model),
        PAIRED_COMPARISON_INDEX[reference_formation],
        CONDITIONS.index(condition),
    ]


def paired_method(reps: int = REPS) -> str:
    """How a paired contrast's interval is drawn, for the tables' `method` column."""
    return (
        f"paired bootstrap over matched episodes within scenario (silent_analysis.py boot_paired), "
        f"{reps} draws, seed {SEED}"
    )


def _by_epoch(mornings: Sequence[Morning], board: str) -> dict[int, Morning]:
    out: dict[int, Morning] = {}
    for m in mornings:
        if m.epoch in out:
            raise ValueError(
                f"{board}: episode {m.epoch} appears twice on one side of a pairing"
            )
        out[m.epoch] = m
    return out


def paired_contrast(
    silent: Mapping[str, Sequence[Morning]],
    reference: Mapping[str, Sequence[Morning]],
    *,
    seed: Sequence[int],
    reps: int = REPS,
    condition: str = "both",
) -> Paired:
    """The paper's paired silent-minus-reference contrast (`silent_analysis.py` `boot_paired`).

    Per scenario of the condition, the pairs are the epochs both sides hold (one episode per epoch and side);
    a scenario without a pair, or without a contest on either side, is left out. Scenarios in board-id
    order, pairs in epoch order; every draw resamples each scenario's pairs with replacement and applies them to
    both arms.

    Raises:
        ValueError: An epoch appears twice on one side of a scenario.
    """
    pairs: dict[str, list[tuple[Morning, Morning]]] = {}
    for board in sorted(set(silent) & set(reference)):
        if not in_condition(board, condition):
            continue
        xs, ys = _by_epoch(silent[board], board), _by_epoch(reference[board], board)
        matched = [(xs[e], ys[e]) for e in sorted(set(xs) & set(ys))]
        if matched and sum(x.n for x, _ in matched) and sum(y.n for _, y in matched):
            pairs[board] = matched
    if not pairs:
        nan = math.nan
        return Paired(
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            nan,
            0,
            0,
            0,
            0,
            0,
            paired_method(reps),
        )
    rng = np.random.default_rng(list(seed))
    tx, ty = np.zeros(reps), np.zeros(reps)
    rx: list[float] = []
    ry: list[float] = []
    for matched in pairs.values():
        ax = _array([x for x, _ in matched])
        ay = _array([y for _, y in matched])
        rx.append(_rate(ax))
        ry.append(_rate(ay))
        idx = rng.integers(0, len(ax), size=(reps, len(ax)))
        dx, dy = ax[idx], ay[idx]
        tx += dx[:, :, 0].sum(axis=1) / dx[:, :, 1].sum(axis=1)
        ty += dy[:, :, 0].sum(axis=1) / dy[:, :, 1].sum(axis=1)
    bx, by = 100 * tx / len(pairs), 100 * ty / len(pairs)
    sx, sy = 100 * float(np.mean(rx)), 100 * float(np.mean(ry))
    silent_lo, silent_hi = np.percentile(bx, [2.5, 97.5])
    reference_lo, reference_hi = np.percentile(by, [2.5, 97.5])
    lo, hi = np.percentile(bx - by, [2.5, 97.5])
    diffs = [a - b for a, b in zip(rx, ry, strict=True)]
    return Paired(
        silent_pct=sx,
        silent_lo=float(silent_lo),
        silent_hi=float(silent_hi),
        reference_pct=sy,
        reference_lo=float(reference_lo),
        reference_hi=float(reference_hi),
        diff=sx - sy,
        lo=float(lo),
        hi=float(hi),
        n_scenarios=len(pairs),
        n_pairs=sum(len(v) for v in pairs.values()),
        silent_ahead=sum(d > 1e-12 for d in diffs),
        reference_ahead=sum(d < -1e-12 for d in diffs),
        ties=sum(abs(d) <= 1e-12 for d in diffs),
        method=paired_method(reps),
    )
