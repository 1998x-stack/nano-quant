"""Accounting, fill timing, risk approval, sell and failure invariants."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from nano_quant.core import ContractError, OrderIntent, RiskDecision, Side
from nano_quant.core.order_integrity import order_fingerprint
from nano_quant.data import golden_bars
from nano_quant.execution.account import SimulatedAccount

UTC = timezone.utc
AT = datetime(2026, 1, 5, 21, 2, tzinfo=UTC)


def _order(side=Side.BUY, qty=10, oid="a", symbol="SYNTH-A", earliest=None):
    _, tomorrow = golden_bars()
    return OrderIntent(
        oid, symbol, side, qty, AT,
        tomorrow.open_at if earliest is None else earliest, "T close",
    )


def _decision(order, approved=True):
    return RiskDecision(
        AT, (order.order_id,), approved,
        () if approved else ("POSITION_LIMIT",), "policy-v1",
        order_digest=order_fingerprint(order),
    )


def _fill(account, order, *, fee="1.00", slippage="10", bar=None, approval=None):
    _, tomorrow = golden_bars()
    return account.execute_at_open(
        order, _decision(order) if approval is None else approval,
        tomorrow if bar is None else bar,
        fee=Decimal(fee), slippage_bps=Decimal(slippage),
    )


def test_open_fill_then_close_mark_obeys_independent_golden_ledger() -> None:
    _, tomorrow = golden_bars()
    account = SimulatedAccount(Decimal("1000.00"))
    order = _order()
    fill = _fill(account, order)
    assert fill.price == Decimal("10.01")
    assert fill.filled_at == tomorrow.open_at
    assert account.cash == Decimal("898.90")
    state = account.mark_to_close({"SYNTH-A": tomorrow}, at=tomorrow.available_at)
    assert state.nav == Decimal("1008.90")
    assert state.positions["SYNTH-A"] == 10


def test_sell_uses_adverse_slippage_and_commission() -> None:
    _, tomorrow = golden_bars()
    account = SimulatedAccount(Decimal("1000.00"))
    _fill(account, _order())
    sell = _order(side=Side.SELL, qty=4, oid="sell")
    fill = _fill(account, sell)
    assert fill.price == Decimal("9.99")
    assert account.positions["SYNTH-A"] == 6
    assert account.cash == Decimal("937.86")
    assert len(account.fills) == 2
    assert account.mark_to_close({"SYNTH-A": tomorrow}, at=tomorrow.available_at).nav == Decimal("1003.86")


def test_sell_all_shares_and_mark_empty_account() -> None:
    _, tomorrow = golden_bars()
    account = SimulatedAccount(Decimal("1000.00"))
    _fill(account, _order())
    _fill(account, _order(side=Side.SELL, oid="sell"))
    assert account.positions == {}
    assert account.mark_to_close({}, at=tomorrow.available_at).nav == account.cash


def test_approval_and_order_ids_cannot_be_bypassed() -> None:
    account = SimulatedAccount(Decimal("1000.00"))
    order = _order()
    with pytest.raises(ContractError, match="NO_RISK_APPROVAL"):
        _fill(account, order, approval=_decision(order, approved=False))
    with pytest.raises(ContractError, match="NO_RISK_APPROVAL"):
        _fill(
            account, order,
            approval=RiskDecision(AT, ("different",), True, (), "policy-v1"),
        )
    assert account.positions == {}


def test_duplicate_and_overbuy_are_rejected_without_mutation() -> None:
    account = SimulatedAccount(Decimal("101.00"))
    with pytest.raises(ContractError, match="CASH_SHORTAGE"):
        _fill(account, _order())
    assert account.cash == Decimal("101.00")
    funded = SimulatedAccount(Decimal("1000.00"))
    order = _order()
    _fill(funded, order)
    with pytest.raises(ContractError, match="DUPLICATE_ORDER"):
        _fill(funded, order)
    assert len(funded.fills) == 1


def test_oversell_and_fee_errors_rejected() -> None:
    account = SimulatedAccount(Decimal("1000.00"))
    with pytest.raises(ContractError, match="POSITION_LIMIT"):
        _fill(account, _order(side=Side.SELL))
    with pytest.raises(ContractError, match="INVALID_FEE"):
        _fill(account, _order(), fee="0.001")
    with pytest.raises(ContractError, match="INVALID_FEE"):
        _fill(account, _order(), fee="-1")
    with pytest.raises(ContractError, match="INVALID_SLIPPAGE"):
        _fill(account, _order(), slippage="-1")


def test_time_bar_and_mark_checks() -> None:
    _, tomorrow = golden_bars()
    account = SimulatedAccount(Decimal("1000.00"))
    with pytest.raises(ContractError, match="EXECUTION_TOO_EARLY"):
        _fill(
            account, _order(earliest=tomorrow.open_at + timedelta(minutes=1))
        )
    with pytest.raises(ContractError, match="MISSING_BAR"):
        _fill(account, _order(symbol="OTHER"))
    order = _order()
    late_approval = RiskDecision(
        tomorrow.open_at + timedelta(minutes=1), (order.order_id,), True, (), "v1",
    )
    with pytest.raises(ContractError, match="ASOF_VIOLATION"):
        _fill(account, order, approval=late_approval)
    _fill(account, order)
    with pytest.raises(ContractError, match="MISSING_BAR"):
        account.mark_to_close({}, at=tomorrow.available_at)
    with pytest.raises(ContractError, match="MISSING_BAR"):
        account.mark_to_close({"SYNTH-A": tomorrow}, at=tomorrow.event_at)


def test_invalid_starting_cash() -> None:
    with pytest.raises(ContractError):
        SimulatedAccount(Decimal("-1"))
    with pytest.raises(ContractError):
        SimulatedAccount(Decimal("1.001"))
