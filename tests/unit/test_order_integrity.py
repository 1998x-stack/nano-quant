"""Order changes after risk approval must invalidate execution authorization."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from nano_quant.core import ContractError, OrderIntent, PortfolioState, RiskDecision, Side
from nano_quant.core.order_integrity import order_fingerprint
from nano_quant.core.research_types import TargetPortfolio
from nano_quant.data import golden_bars
from nano_quant.execution.account import SimulatedAccount
from nano_quant.risk import review_orders

UTC = timezone.utc
DECISION = datetime(2026, 1, 5, 21, 2, tzinfo=UTC)


def test_terms_change_invalidates_previous_risk_approval() -> None:
    _, next_day = golden_bars()
    original = OrderIntent(
        "order-1", "SYNTH-A", Side.BUY, 10, DECISION,
        next_day.open_at, "previous raw close",
    )
    account = SimulatedAccount(Decimal("1000.00"))
    state = PortfolioState(DECISION, Decimal("1000.00"), {}, {})
    target = TargetPortfolio(DECISION, (("SYNTH-A", Decimal(".10")),))
    decision = review_orders(
        target, (original,), state, allowed_instruments=("SYNTH-A",),
    )[0]
    assert decision.approved
    assert decision.order_digest == order_fingerprint(original)
    for altered in (
        replace(original, quantity=20),
        replace(original, side=Side.SELL),
        replace(original, reference_price_context="altered reference"),
    ):
        with pytest.raises(ContractError, match="ORDER_APPROVAL_MISMATCH"):
            account.execute_at_open(
                altered, decision, next_day,
                fee=Decimal("1"), slippage_bps=Decimal("10"),
            )
    assert account.cash == Decimal("1000.00")
    assert account.positions == {}


def test_approved_order_executes_but_unbound_mock_decision_does_not() -> None:
    _, bar = golden_bars()
    order = OrderIntent("ok", "SYNTH-A", Side.BUY, 10, DECISION,
                        golden_bars()[1].open_at, "close")
    unbound = RiskDecision(DECISION, ("ok",), True, (), "old-mock")
    account = SimulatedAccount(Decimal("1000.00"))
    with pytest.raises(ContractError, match="ORDER_APPROVAL_MISMATCH"):
        account.execute_at_open(
            order, unbound, golden_bars()[1],
            fee=Decimal("1"), slippage_bps=Decimal("10"),
        )
    assert bar.close == Decimal("11.00")
