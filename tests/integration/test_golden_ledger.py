"""Golden Ledger A: independently calculated in docs/validation/acceptance.md."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from nano_quant.core import ContractError, OrderIntent, PortfolioState, RiskDecision, Side
from nano_quant.data import golden_bars
from nano_quant.execution import SimulatedLedger

UTC = timezone.utc
DECISION_AT = datetime(2026, 1, 5, 21, 2, tzinfo=UTC)


def scenario(cash: str = "1000.00") -> tuple[SimulatedLedger, OrderIntent, RiskDecision]:
    _, tomorrow = golden_bars()
    order = OrderIntent(
        order_id="golden-order", instrument_id="SYNTH-A", side=Side.BUY,
        quantity=10, created_at=DECISION_AT,
        earliest_execution_at=tomorrow.open_at,
        reference_price_context="close@T=10",
    )
    approval = RiskDecision(
        as_of=DECISION_AT, order_ids=(order.order_id,),
        approved=True, reason_codes=(), risk_policy_version="mock-risk-phase-b",
    )
    ledger = SimulatedLedger(
        PortfolioState(as_of=DECISION_AT, cash=Decimal(cash), positions={}, marks={})
    )
    return ledger, order, approval


def test_independently_computed_golden_ledger_a() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario()
    fill = ledger.execute_buy_at_next_open(
        order, approval, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1.00")
    )
    assert fill.price == Decimal("10.01")
    assert fill.quantity == 10
    assert fill.fee == Decimal("1.00")
    assert fill.filled_at == tomorrow.open_at
    assert ledger.state.cash == Decimal("898.90")
    assert ledger.state.positions == {"SYNTH-A": 10}
    assert ledger.state.nav == Decimal("1008.90")
    assert (ledger.state.nav - Decimal("1000")) / Decimal("1000") == Decimal("0.0089")
    assert ledger.state.as_of == tomorrow.available_at


def test_duplicate_order_is_rejected_without_modifying_cash() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario()
    ledger.execute_buy_at_next_open(
        order, approval, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1")
    )
    state = ledger.state
    with pytest.raises(ContractError, match="DUPLICATE_ORDER"):
        ledger.execute_buy_at_next_open(
            order, approval, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1")
        )
    assert ledger.state is state


def test_unapproved_or_wrong_order_is_rejected() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario()
    denied = RiskDecision(
        as_of=DECISION_AT, order_ids=(order.order_id,),
        approved=False, reason_codes=("POSITION_LIMIT",),
        risk_policy_version="mock-risk-phase-b",
    )
    with pytest.raises(ContractError, match="NO_RISK_APPROVAL"):
        ledger.execute_buy_at_next_open(
            order, denied, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1")
        )
    wrong = RiskDecision(
        as_of=DECISION_AT, order_ids=("other",),
        approved=True, reason_codes=(), risk_policy_version="mock-risk-phase-b",
    )
    with pytest.raises(ContractError, match="NO_RISK_APPROVAL"):
        ledger.execute_buy_at_next_open(
            order, wrong, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1")
        )
    assert ledger.state.nav == Decimal("1000")


def test_order_cannot_fill_before_earliest_execution_time() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario()
    later = OrderIntent(
        order_id=order.order_id, instrument_id=order.instrument_id,
        side=order.side, quantity=order.quantity,
        created_at=order.created_at,
        earliest_execution_at=tomorrow.open_at + timedelta(minutes=1),
        reference_price_context=order.reference_price_context,
    )
    with pytest.raises(ContractError, match="earliest_execution"):
        ledger.execute_buy_at_next_open(
            later, approval, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1")
        )


def test_cash_shortage_does_not_mutate_ledger() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario("10.00")
    before = ledger.state
    with pytest.raises(ContractError, match="CASH_SHORTAGE"):
        ledger.execute_buy_at_next_open(
            order, approval, tomorrow, slippage_bps=Decimal("10"), fee=Decimal("1")
        )
    assert ledger.state is before


def test_higher_transaction_fees_cannot_increase_nav() -> None:
    _, tomorrow = golden_bars()
    navs = []
    for fee in ("0", "1", "5"):
        ledger, order, approval = scenario()
        ledger.execute_buy_at_next_open(
            order, approval, tomorrow,
            slippage_bps=Decimal("10"), fee=Decimal(fee),
        )
        navs.append(ledger.state.nav)
    assert navs == [Decimal("1009.90"), Decimal("1008.90"), Decimal("1004.90")]


def test_fractional_cent_fee_rejected() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario()
    with pytest.raises(ContractError, match="USD cents"):
        ledger.execute_buy_at_next_open(
            order, approval, tomorrow,
            slippage_bps=Decimal("10"), fee=Decimal("0.005"),
        )


def test_sell_and_mismatched_instrument_are_not_implemented() -> None:
    _, tomorrow = golden_bars()
    ledger, order, approval = scenario()
    with pytest.raises(ContractError, match="BUY only"):
        ledger.execute_buy_at_next_open(
            OrderIntent(
                "golden-order", "SYNTH-A", Side.SELL, 10, DECISION_AT,
                tomorrow.open_at, "synthetic"
            ),
            approval, tomorrow, slippage_bps=Decimal("0"), fee=Decimal("1")
        )
    with pytest.raises(ContractError, match="mismatch"):
        ledger.execute_buy_at_next_open(
            OrderIntent(
                "golden-order", "OTHER", Side.BUY, 10, DECISION_AT,
                tomorrow.open_at, "synthetic"
            ),
            approval, tomorrow, slippage_bps=Decimal("0"), fee=Decimal("1")
        )
