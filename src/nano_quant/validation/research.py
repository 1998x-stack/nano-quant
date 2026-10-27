"""Purged chronological evaluation and diagnostic circular-shift nulls.

Research notes: windows are sample-index-based and need known label horizon.
Shifted targets keep their serial dependence but can still mislead under
nonstationarity, overlapping labels, regime changes, and multiple testing.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from nano_quant.core import ContractError


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: int
    train_end: int  # exclusive
    test_start: int
    test_end: int  # exclusive
    horizon: int

    def __post_init__(self) -> None:
        if not (0 <= self.train_start < self.train_end
                <= self.test_start < self.test_end):
            raise ContractError("invalid chronological window ordering")
        if self.test_start - self.train_end < self.horizon:
            raise ContractError("training label could overlap test information")


def walk_forward_windows(
    n_samples: int,
    train_size: int,
    test_size: int,
    *,
    label_horizon: int,
    step_size: int | None = None,
) -> tuple[WalkForwardWindow, ...]:
    """Rolling fixed-width train/test with an explicit label-horizon gap.

    Assumes a label at feature index t uses observations t+1 through t+h.
    For multi-asset labels and uneven calendars, use per-label event timestamps
    and a more specific interval-overlap purge in a later implementation.
    """
    fields = (n_samples, train_size, test_size, label_horizon)
    if any(type(x) is not int or x <= 0 for x in fields):
        raise ContractError("window inputs must be positive integers")
    if step_size is None:
        step_size = test_size
    if type(step_size) is not int or step_size <= 0:
        raise ContractError("step_size must be positive integer")
    windows = []
    for start in range(0, n_samples - train_size - label_horizon - test_size + 1,
                       step_size):
        end = start + train_size
        test_start = end + label_horizon
        windows.append(WalkForwardWindow(
            train_start=start, train_end=end, test_start=test_start,
            test_end=test_start + test_size, horizon=label_horizon,
        ))
    if not windows:
        raise ContractError("not enough observations for one held-out window")
    return tuple(windows)


def _ranks(values: tuple[Decimal, ...]) -> tuple[float, ...]:
    """Average ranks for ties, without importing a model-fitting library."""
    lookup = sorted(range(len(values)), key=lambda i: (values[i], i))
    rank = [0.0] * len(values)
    left = 0
    while left < len(lookup):
        right = left + 1
        while right < len(lookup) and values[lookup[right]] == values[lookup[left]]:
            right += 1
        average_rank = (left + 1 + right) / 2.0
        for idx in lookup[left:right]:
            rank[idx] = average_rank
        left = right
    return tuple(rank)


def rank_ic(factors: Sequence[Decimal], targets: Sequence[Decimal]) -> float:
    """Spearman rank correlation, requires a non-constant aligned sample."""
    x, y = tuple(factors), tuple(targets)
    if len(x) != len(y) or len(x) < 3:
        raise ContractError("rank IC needs >= 3 aligned observations")
    if any(not isinstance(a, Decimal) or not a.is_finite() for a in x + y):
        raise ContractError("rank IC needs finite Decimal inputs")
    rx, ry = _ranks(x), _ranks(y)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    xx = sum((v - mx) ** 2 for v in rx)
    yy = sum((v - my) ** 2 for v in ry)
    if not xx or not yy:
        raise ContractError("constant ranking has undefined rank IC")
    cross = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return cross / math.sqrt(xx * yy)


@dataclass(frozen=True)
class NegativeControlResult:
    observed_rank_ic: float
    null_rank_ics: tuple[float, ...]
    one_sided_empirical_p: float
    method: str


def circular_shift_negative_control(
    factors: Sequence[Decimal],
    realized: Sequence[Decimal],
    *,
    label_horizon: int,
    draws: int = 40,
    seed: int = 42,
) -> NegativeControlResult:
    """Diagnostic null preserving the order within the realized target series.

    Not a standalone hypothesis test proving alpha. Boundary wraps and common
    trends can violate the null model; consider block-bootstrap / cluster
    dependence when doing actual financial inference.
    """
    x, y = tuple(factors), tuple(realized)
    observed = rank_ic(x, y)
    n = len(x)
    if type(label_horizon) is not int or label_horizon < 1:
        raise ContractError("label_horizon must be positive")
    if type(draws) is not int or draws < 1:
        raise ContractError("draws must be positive")
    # Exclude trivially adjacent shifts; avoid shifts equivalent to +/-h days.
    valid_shifts = list(range(label_horizon + 1, n - label_horizon))
    if not valid_shifts:
        raise ContractError("series too short for independent circular shifts")
    rng = random.Random(seed)
    nulls = []
    for _ in range(draws):
        shift = rng.choice(valid_shifts)
        shifted = y[shift:] + y[:shift]
        try:
            nulls.append(rank_ic(x, shifted))
        except ContractError as exc:
            raise ContractError("invalid negative control sample") from exc
    # Add-one randomization p for >= observed, one-sided positive association.
    p = (1 + sum(value >= observed for value in nulls)) / (draws + 1)
    return NegativeControlResult(
        observed_rank_ic=observed,
        null_rank_ics=tuple(nulls),
        one_sided_empirical_p=p,
        method="circular-shift-diagnostic-not-confirmatory",
    )
