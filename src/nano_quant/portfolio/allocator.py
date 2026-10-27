"""Allocate a capped, long-only USD portfolio and plan whole-share orders."""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from nano_quant.core import ContractError, OrderIntent, PortfolioState, Side
from nano_quant.core.research_types import StrategySignal, TargetPortfolio


def equal_weight_target(
    signals: tuple[StrategySignal, ...],
    *,
    as_of: datetime,
    max_single_weight: Decimal = Decimal("0.50"),
    cash_buffer: Decimal = Decimal("0.02"),
) -> TargetPortfolio:
    if not isinstance(as_of, datetime):
        raise ContractError("as_of must be datetime")
    if not (0 < max_single_weight <= 1 and 0 <= cash_buffer < 1):
        raise ContractError("invalid portfolio constraints")
    if any(signal.as_of != as_of for signal in signals):
        raise ContractError("signal time inconsistent with target")
    if len(set(x.instrument_id for x in signals)) != len(signals):
        raise ContractError("duplicate selected instrument")
    if not signals:
        return TargetPortfolio(as_of, ())
    # Equally allocate investible wealth (cash buffer included) subject to the cap.
    per_asset = min(max_single_weight, (Decimal("1") - cash_buffer) / len(signals))
    return TargetPortfolio(
        as_of=as_of,
        weights=tuple(sorted((signal.instrument_id, per_asset) for signal in signals)),
    )


def plan_orders(
    target: TargetPortfolio,
    state: PortfolioState,
    reference_closes: dict[str, Decimal],
    earliest_execution_at: datetime,
) -> tuple[OrderIntent, ...]:
    if not isinstance(earliest_execution_at, datetime):
        raise ContractError("earliest execution must be datetime")
    if state.as_of > target.as_of:
        raise ContractError("portfolio state is newer than target")
    desired: dict[str, int] = {}
    for instrument, weight in target.weights:
        price = reference_closes.get(instrument)
        if price is None or not price.is_finite() or price <= 0:
            raise ContractError("MISSING_BAR")
        desired[instrument] = int(
            (state.nav * weight / price).to_integral_value(rounding=ROUND_DOWN)
        )
    orders: list[OrderIntent] = []
    for instrument in sorted(set(state.positions) | set(desired)):
        current = state.positions.get(instrument, 0)
        delta = desired.get(instrument, 0) - current
        if delta == 0:
            continue
        orders.append(
            OrderIntent(
                order_id=f"{target.as_of.date()}:{instrument}:{'B' if delta > 0 else 'S'}",
                instrument_id=instrument,
                side=Side.BUY if delta > 0 else Side.SELL,
                quantity=abs(delta),
                created_at=target.as_of,
                earliest_execution_at=earliest_execution_at,
                reference_price_context="previous-session raw close",
            )
        )
    # Sells precede buys in order to free cash; execution also applies this sorting.
    return tuple(sorted(orders, key=lambda order: (order.side is Side.BUY, order.instrument_id)))
