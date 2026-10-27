"""USD-only Phase B buy-side golden ledger, not a full backtesting engine."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from nano_quant.core import (
    ContractError,
    Fill,
    OrderIntent,
    PortfolioState,
    PriceBar,
    RiskDecision,
    Side,
)

CENT = Decimal("0.01")
BPS = Decimal("10000")


class SimulatedLedger:
    """Small deterministic event applier with an order idempotency gate.

    Only long BUY transactions for one synthetic instrument are supported.
    This class is a gold-test stepping stone, not a portfolio or risk engine.
    """

    def __init__(self, initial_state: PortfolioState) -> None:
        self.state = initial_state
        self._executed_orders: set[str] = set()

    def execute_buy_at_next_open(
        self,
        order: OrderIntent,
        approval: RiskDecision,
        bar: PriceBar,
        *,
        slippage_bps: Decimal,
        fee: Decimal,
    ) -> Fill:
        if order.order_id in self._executed_orders:
            raise ContractError("DUPLICATE_ORDER")
        if not approval.approved or order.order_id not in approval.order_ids:
            raise ContractError("NO_RISK_APPROVAL")
        if not (order.created_at <= approval.as_of < bar.open_at):
            raise ContractError("invalid risk-approval chronology")
        if order.earliest_execution_at > bar.open_at:
            raise ContractError("execution before earliest_execution_at")
        if self.state.as_of > order.created_at:
            raise ContractError("state snapshot is after order creation")
        if order.side is not Side.BUY:
            raise ContractError("Phase B ledger supports BUY only")
        if order.instrument_id != bar.instrument_id:
            raise ContractError("order/bar instrument mismatch")
        if self.state.positions and set(self.state.positions) != {order.instrument_id}:
            raise ContractError("Phase B ledger supports one instrument only")
        if not slippage_bps.is_finite() or not (0 <= slippage_bps <= BPS):
            raise ContractError("invalid slippage_bps")
        if not fee.is_finite() or fee < 0:
            raise ContractError("invalid fee")

        fill_price = (
            bar.open * (Decimal("1") + slippage_bps / BPS)
        ).quantize(CENT, rounding=ROUND_HALF_UP)
        cash_debit = (fill_price * order.quantity + fee).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        if cash_debit > self.state.cash:
            raise ContractError("CASH_SHORTAGE")

        fill = Fill(
            fill_id=f"fill-{order.order_id}",
            order_id=order.order_id,
            instrument_id=order.instrument_id,
            side=Side.BUY,
            quantity=order.quantity,
            price=fill_price,
            fee=fee,
            filled_at=bar.open_at,
        )
        positions = dict(self.state.positions)
        positions[order.instrument_id] = positions.get(order.instrument_id, 0) + order.quantity
        marks = dict(self.state.marks)
        marks[order.instrument_id] = bar.close
        # The close valuation is not available until bar.available_at.
        self.state = PortfolioState(
            as_of=bar.available_at,
            cash=(self.state.cash - cash_debit).quantize(CENT),
            positions=positions,
            marks=marks,
        )
        self._executed_orders.add(order.order_id)
        return fill
