"""Deterministic long-only simulation, preserving true next-open fill timing."""

from __future__ import annotations

from datetime import datetime
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

from nano_quant.core.order_integrity import order_fingerprint

CENT = Decimal("0.01")
BPS = Decimal("10000")


class SimulatedAccount:
    """USD cash and integer shares; open fills, explicit end-of-day marks.

    Full-or-nothing execution. Affordability is rechecked at execution prices.
    No real broker connectivity, multi-currency or corporate-action support.
    """

    def __init__(self, initial_cash: Decimal) -> None:
        if not initial_cash.is_finite() or initial_cash <= 0:
            raise ContractError("invalid starting cash")
        if initial_cash != initial_cash.quantize(CENT):
            raise ContractError("USD cash must use cents")
        self.cash = initial_cash
        self.positions: dict[str, int] = {}
        self.fills: list[Fill] = []
        self._processed: set[str] = set()

    def execute_at_open(
        self,
        order: OrderIntent,
        approval: RiskDecision,
        bar: PriceBar,
        *,
        fee: Decimal,
        slippage_bps: Decimal,
    ) -> Fill:
        if order.order_id in self._processed:
            raise ContractError("DUPLICATE_ORDER")
        if not approval.approved or order.order_id not in approval.order_ids:
            raise ContractError("NO_RISK_APPROVAL")
        if not (order.created_at <= approval.as_of < bar.open_at):
            raise ContractError("ASOF_VIOLATION")
        if not (order.earliest_execution_at <= bar.open_at):
            raise ContractError("EXECUTION_TOO_EARLY")
        if approval.order_digest != order_fingerprint(order):
            raise ContractError("ORDER_APPROVAL_MISMATCH")
        if order.instrument_id != bar.instrument_id:
            raise ContractError("MISSING_BAR")
        if not fee.is_finite() or fee < 0 or fee != fee.quantize(CENT):
            raise ContractError("INVALID_FEE")
        if not slippage_bps.is_finite() or not (0 <= slippage_bps <= BPS):
            raise ContractError("INVALID_SLIPPAGE")

        multiplier = (
            Decimal("1") + slippage_bps / BPS
            if order.side is Side.BUY else Decimal("1") - slippage_bps / BPS
        )
        price = (bar.open * multiplier).quantize(CENT, rounding=ROUND_HALF_UP)
        if price <= 0:
            raise ContractError("INVALID_PRICE")
        traded_value = price * order.quantity
        if order.side is Side.BUY:
            required = traded_value + fee
            if required > self.cash:
                raise ContractError("CASH_SHORTAGE")
            new_cash = self.cash - required
            new_quantity = self.positions.get(order.instrument_id, 0) + order.quantity
        else:
            held = self.positions.get(order.instrument_id, 0)
            if order.quantity > held:
                raise ContractError("POSITION_LIMIT")
            proceeds = traded_value - fee
            if proceeds < 0:
                raise ContractError("INVALID_FEE")
            new_cash = self.cash + proceeds
            new_quantity = held - order.quantity

        fill = Fill(
            fill_id=f"fill-{order.order_id}",
            order_id=order.order_id,
            instrument_id=order.instrument_id,
            side=order.side,
            quantity=order.quantity,
            price=price,
            fee=fee,
            filled_at=bar.open_at,
        )
        self.cash = new_cash.quantize(CENT)
        if new_quantity:
            self.positions[order.instrument_id] = new_quantity
        else:
            self.positions.pop(order.instrument_id, None)
        self._processed.add(order.order_id)
        self.fills.append(fill)
        return fill

    def mark_to_close(
        self, bars_by_instrument: dict[str, PriceBar], *, at: datetime
    ) -> PortfolioState:
        marks: dict[str, Decimal] = {}
        for instrument in self.positions:
            bar = bars_by_instrument.get(instrument)
            if bar is None or bar.available_at > at:
                raise ContractError("MISSING_BAR")
            marks[instrument] = bar.close
        return PortfolioState(
            as_of=at, cash=self.cash, positions=self.positions, marks=marks
        )
