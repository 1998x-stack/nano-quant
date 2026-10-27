"""Purging, rolling origin boundaries and negative-control diagnostics."""

from decimal import Decimal

import pytest

from nano_quant.core import ContractError
from nano_quant.validation import (
    circular_shift_negative_control, rank_ic, walk_forward_windows,
)


def test_walk_forward_windows_purge_full_label_horizon() -> None:
    windows = walk_forward_windows(120, 60, 12, label_horizon=5, step_size=10)
    assert len(windows) == 5
    assert windows[0].train_start == 0
    assert windows[0].train_end == 60
    assert windows[0].test_start == 65
    assert windows[0].test_end == 77
    for window in windows:
        assert window.train_end + window.horizon <= window.test_start
        assert window.test_end <= 120
        assert window.train_start < window.train_end < window.test_start


@pytest.mark.parametrize("kwargs", [
    {"n_samples": 50, "train_size": 40, "test_size": 20, "label_horizon": 5},
    {"n_samples": 50, "train_size": 0, "test_size": 4, "label_horizon": 5},
    {"n_samples": 50, "train_size": 20, "test_size": 5, "label_horizon": 0},
    {"n_samples": 50, "train_size": True, "test_size": 5, "label_horizon": 1},
    {"n_samples": 50, "train_size": 20, "test_size": 5, "label_horizon": 1, "step_size": 0},
])
def test_walk_forward_rejects_invalid_configs(kwargs) -> None:
    with pytest.raises(ContractError):
        walk_forward_windows(**kwargs)


def test_rank_ic_matches_manual_extremes_and_tie_handling() -> None:
    x = tuple(map(Decimal, range(1, 9)))
    assert rank_ic(x, x) == pytest.approx(1)
    assert rank_ic(x, x[::-1]) == pytest.approx(-1)
    mixed = (Decimal(1), Decimal(1), Decimal(2), Decimal(3))
    assert rank_ic(mixed, mixed) == pytest.approx(1)


def test_negative_control_is_reproducible_but_not_proof_of_alpha() -> None:
    x = tuple(Decimal(i + ((i * 17) % 5)) for i in range(50))
    y = tuple(Decimal((i * 11) % 17 - 8) for i in range(50))
    a = circular_shift_negative_control(x, y, label_horizon=3, draws=50, seed=123)
    b = circular_shift_negative_control(x, y, label_horizon=3, draws=50, seed=123)
    assert a == b
    assert len(a.null_rank_ics) == 50
    assert -1 <= a.observed_rank_ic <= 1
    assert 1 / 51 <= a.one_sided_empirical_p <= 1
    assert "not-confirmatory" in a.method


def test_negative_control_rejects_noninformative_samples() -> None:
    x = (Decimal(1),) * 10
    y = tuple(map(Decimal, range(10)))
    with pytest.raises(ContractError, match="constant"):
        rank_ic(x, y)
    with pytest.raises(ContractError, match="series too short"):
        circular_shift_negative_control(
            y, y, label_horizon=5, draws=10,
        )
    with pytest.raises(ContractError, match="draws"):
        circular_shift_negative_control(
            y, y, label_horizon=1, draws=0,
        )
