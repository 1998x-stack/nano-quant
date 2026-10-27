"""Factor/model/strategy/portfolio correctness with point-in-time inputs."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from nano_quant.core import ContractError, PortfolioState
from nano_quant.core.research_types import (
    FactorFrame, Forecast, StrategySignal, TargetPortfolio,
)
from nano_quant.data import INSTRUMENTS, build_snapshot, synthetic_equities
from nano_quant.models import baseline_rank_forecast
from nano_quant.portfolio import equal_weight_target, plan_orders
from nano_quant.research import momentum_factor
from nano_quant.strategies import select_top_n

UTC = timezone.utc


def _pipeline():
    bars = synthetic_equities(70)
    day = bars[3 * 29:3 * 30]
    decision = day[0].available_at + timedelta(minutes=1)
    snap = build_snapshot(bars, as_of=decision, universe=INSTRUMENTS)
    factors = momentum_factor(snap, 20)
    forecast = baseline_rank_forecast(factors)
    signals = select_top_n(forecast, 2)
    return bars, snap, factors, forecast, signals


def test_factor_scores_match_independent_manual_formula() -> None:
    bars, _, factors, forecast, signals = _pipeline()
    for instrument, value in factors.scores:
        own = [bar for bar in bars if bar.instrument_id == instrument]
        expected = own[29].close / own[9].close - 1
        assert value == expected
    assert forecast.scores == factors.scores
    assert forecast.training_cutoff is None
    assert "uncalibrated" in forecast.target
    assert len(signals) == 2
    assert [s.instrument_id for s in signals] == [
        item[0] for item in sorted(factors.scores, key=lambda x: (-x[1], x[0]))[:2]
    ]


def test_future_perturbation_cannot_change_factor_or_prediction() -> None:
    bars, snap, factors, forecast, signals = _pipeline()
    next_bar = bars[3 * 55]
    changed = replace(
        next_bar, high=Decimal("900.00"), close=Decimal("900.00")
    )
    mutated = tuple(changed if b is next_bar else b for b in bars)
    snap2 = build_snapshot(mutated, as_of=snap.as_of, universe=INSTRUMENTS)
    assert snap == snap2
    assert momentum_factor(snap2, 20) == factors
    assert baseline_rank_forecast(momentum_factor(snap2, 20)) == forecast
    assert select_top_n(forecast) == signals


def test_insufficient_factor_warmup_is_explicit() -> None:
    bars = synthetic_equities(60)
    snap = build_snapshot(
        bars, as_of=bars[12].available_at, universe=INSTRUMENTS
    )
    with pytest.raises(ContractError, match="INSUFFICIENT_WARMUP"):
        momentum_factor(snap, 20)
    with pytest.raises(ContractError, match="lookback"):
        momentum_factor(snap, 0)


def test_rank_tie_break_is_stable() -> None:
    now = datetime(2026, 1, 5, 21, 2, tzinfo=UTC)
    f = Forecast(now, 20, "score", (("A", Decimal("1")), ("B", Decimal("1"))), "v1")
    assert [x.instrument_id for x in select_top_n(f, 2)] == ["A", "B"]
    with pytest.raises(ContractError, match="positive"):
        select_top_n(f, 0)


def test_equal_weight_target_and_plan_orders() -> None:
    bars, snap, _, _, signals = _pipeline()
    target = equal_weight_target(
        signals, as_of=snap.as_of,
        max_single_weight=Decimal("0.50"), cash_buffer=Decimal("0.02"),
    )
    assert len(target.weights) == 2
    assert all(weight == Decimal("0.49") for _, weight in target.weights)
    state = PortfolioState(snap.as_of, Decimal("10000.00"), {}, {})
    prices = {bar.instrument_id: bar.close for bar in bars[3*29:3*30]}
    next_open = bars[3*30].open_at
    orders = plan_orders(target, state, prices, next_open)
    assert len(orders) == 2
    assert all(order.side.value == "BUY" for order in orders)
    assert all(order.quantity > 0 for order in orders)
    assert all(order.earliest_execution_at > order.created_at for order in orders)


def test_plan_orders_sells_old_asset_and_rejects_missing_price() -> None:
    bars, snap, _, _, signals = _pipeline()
    target = equal_weight_target(signals, as_of=snap.as_of)
    state = PortfolioState(
        snap.as_of, Decimal("9000.00"),
        {"OLD": 5}, {"OLD": Decimal("10.00")},
    )
    prices = {bar.instrument_id: bar.close for bar in bars[3*29:3*30]}
    orders = plan_orders(target, state, prices, bars[3*30].open_at)
    assert orders[0].instrument_id == "OLD"
    assert orders[0].side.value == "SELL"
    with pytest.raises(ContractError, match="MISSING_BAR"):
        plan_orders(target, state, {}, bars[3*30].open_at)


def test_target_and_research_contract_invalid_cases() -> None:
    at = datetime(2026, 1, 5, 21, 2, tzinfo=UTC)
    with pytest.raises(ContractError, match="exceed"):
        TargetPortfolio(at, (("A", Decimal(".6")), ("B", Decimal(".6"))))
    with pytest.raises(ContractError, match="sorted"):
        TargetPortfolio(at, (("B", Decimal(".1")), ("A", Decimal(".1"))))
    with pytest.raises(ContractError, match="duplicate"):
        FactorFrame(at, 20, (("A", Decimal(".1")), ("A", Decimal(".2"))), "v1")
    with pytest.raises(ContractError, match="finite"):
        Forecast(at, 20, "score", (("A", Decimal("NaN")),), "v1")
    with pytest.raises(ContractError, match="training cutoff"):
        Forecast(at, 20, "score", (("A", Decimal("1")),), "v1", at + timedelta(days=1))
    with pytest.raises(ContractError, match="signal"):
        StrategySignal(at, "", Decimal("1"), "v1")
    with pytest.raises(ContractError, match="lookback"):
        FactorFrame(at, 0, (("A", Decimal("1")),), "v1")


def test_target_empty_and_wrong_signal_time() -> None:
    at = datetime(2026, 1, 5, 21, 2, tzinfo=UTC)
    assert equal_weight_target((), as_of=at).weights == ()
    signal = StrategySignal(at, "A", Decimal("1"), "v1")
    with pytest.raises(ContractError, match="time"):
        equal_weight_target((signal,), as_of=at + timedelta(days=1))
    with pytest.raises(ContractError, match="duplicate"):
        equal_weight_target((signal, signal), as_of=at)
    with pytest.raises(ContractError, match="constraints"):
        equal_weight_target((signal,), as_of=at, cash_buffer=Decimal("1"))
