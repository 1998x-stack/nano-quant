"""Value-object invariants independent of strategy performance."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from nano_quant.core import (
    ContractError,
    DataSnapshot,
    OrderIntent,
    PortfolioState,
    RiskDecision,
    Side,
)
from nano_quant.data import golden_bars

UTC = timezone.utc


def _decision_time() -> datetime:
    return datetime(2026, 1, 5, 21, 2, tzinfo=UTC)


def _order() -> OrderIntent:
    return OrderIntent(
        "one", "SYNTH-A", Side.BUY, 10, _decision_time(),
        datetime(2026, 1, 6, 14, 30, tzinfo=UTC), "synthetic T close",
    )


def test_price_bar_accepts_valid_synthetic_input() -> None:
    today, _ = golden_bars()
    assert today.close == Decimal("10.00")
    assert today.volume == 1000


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("high", Decimal("9.00")),
        ("low", Decimal("10.01")),
        ("open", Decimal("0")),
        ("close", Decimal("NaN")),
        ("volume", -1),
        ("volume", True),
        ("source_id", ""),
        ("instrument_id", ""),
    ],
)
def test_price_bar_rejects_bad_values(field: str, value: object) -> None:
    today, _ = golden_bars()
    with pytest.raises(ContractError):
        replace(today, **{field: value})


def test_price_bar_rejects_naive_and_non_utc_times() -> None:
    today, _ = golden_bars()
    with pytest.raises(ContractError):
        replace(today, available_at=datetime(2026, 1, 5, 21, 1))
    with pytest.raises(ContractError):
        replace(today, event_at=datetime(2026, 1, 5, 16, tzinfo=timezone(timedelta(hours=-5))))


def test_price_bar_rejects_impossible_availability_order() -> None:
    today, _ = golden_bars()
    with pytest.raises(ContractError):
        replace(today, available_at=today.open_at)


def test_data_snapshot_requires_asof_and_unique_identifiers() -> None:
    today, tomorrow = golden_bars()
    with pytest.raises(ContractError, match="ASOF"):
        DataSnapshot(_decision_time(), (today, tomorrow), ("SYNTH-A",), "X", "manifest")
    with pytest.raises(ContractError, match="duplicate"):
        DataSnapshot(_decision_time(), (today, today), ("SYNTH-A",), "X", "manifest")
    with pytest.raises(ContractError, match="universe"):
        DataSnapshot(_decision_time(), (today,), ("SYNTH-A", "SYNTH-A"), "X", "manifest")
    with pytest.raises(ContractError, match="not in the universe"):
        DataSnapshot(_decision_time(), (today,), ("SYNTH-B",), "X", "manifest")


def test_order_rejects_invalid_chronology_and_quantities() -> None:
    order = _order()
    with pytest.raises(ContractError, match="positive"):
        replace(order, quantity=0)
    with pytest.raises(ContractError, match="positive"):
        replace(order, quantity=True)
    with pytest.raises(ContractError, match="follow"):
        replace(order, earliest_execution_at=order.created_at)
    with pytest.raises(ContractError, match="side"):
        replace(order, side="BUY")


def test_risk_approval_contract_enforces_reasons_and_order_references() -> None:
    at = _decision_time()
    with pytest.raises(ContractError):
        RiskDecision(at, (), True, (), "policy-v1")
    with pytest.raises(ContractError):
        RiskDecision(at, ("one",), True, ("some-warning",), "policy-v1")
    with pytest.raises(ContractError):
        RiskDecision(at, ("one",), False, (), "policy-v1")
    with pytest.raises(ContractError):
        RiskDecision(at, ("one",), True, (), "")


def test_portfolio_state_is_defensively_frozen_and_nav_is_derived() -> None:
    positions = {"SYNTH-A": 10}
    marks = {"SYNTH-A": Decimal("11.00")}
    state = PortfolioState(_decision_time(), Decimal("898.90"), positions, marks)
    positions["SYNTH-A"] = 999
    marks["SYNTH-A"] = Decimal("100")
    assert state.positions["SYNTH-A"] == 10
    assert state.nav == Decimal("1008.90")
    with pytest.raises(TypeError):
        state.positions["SYNTH-A"] = 20
    with pytest.raises(FrozenInstanceError):
        state.cash = Decimal("0")


def test_portfolio_rejects_invalid_cash_or_unmarked_shares() -> None:
    with pytest.raises(ContractError):
        PortfolioState(_decision_time(), Decimal("-1"), {}, {})
    with pytest.raises(ContractError):
        PortfolioState(_decision_time(), Decimal("100"), {"A": 1}, {})
    with pytest.raises(ContractError):
        PortfolioState(_decision_time(), Decimal("100"), {"A": -1}, {"A": Decimal("10")})
