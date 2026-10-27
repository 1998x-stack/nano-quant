"""Independent pretrade policy: target concentration and order admissibility."""

from __future__ import annotations

from decimal import Decimal

from nano_quant.core import OrderIntent, PortfolioState, RiskDecision, Side
from nano_quant.core.order_integrity import order_fingerprint
from nano_quant.core.research_types import TargetPortfolio


def review_orders(
    target: TargetPortfolio,
    orders: tuple[OrderIntent, ...],
    state: PortfolioState,
    *,
    max_single_weight: Decimal = Decimal("0.50"),
    allowed_instruments: tuple[str, ...],
) -> tuple[RiskDecision, ...]:
    """Reject invalid allocations and stale/unrecognized/oversell orders.

    Execution checks actual next-open purchasing power because overnight gaps
    can invalidate a close-price estimate. This is a basic control, not VaR.
    """
    global_reasons: list[str] = []
    if any(w > max_single_weight for _, w in target.weights):
        global_reasons.append("POSITION_LIMIT")
    if state.as_of > target.as_of:
        global_reasons.append("ASOF_VIOLATION")
    wanted = dict(target.weights)
    result: list[RiskDecision] = []
    seen: set[str] = set()
    for order in orders:
        reasons = global_reasons.copy()
        if order.order_id in seen:
            reasons.append("DUPLICATE_ORDER")
        seen.add(order.order_id)
        if order.created_at != target.as_of:
            reasons.append("ASOF_VIOLATION")
        if order.instrument_id not in allowed_instruments:
            reasons.append("UNTRADEABLE")
        if order.side is Side.BUY and order.instrument_id not in wanted:
            reasons.append("UNTRADEABLE")
        if order.side is Side.SELL and order.quantity > state.positions.get(
            order.instrument_id, 0
        ):
            reasons.append("POSITION_LIMIT")
        result.append(
            RiskDecision(
                as_of=target.as_of,
                order_ids=(order.order_id,),
                approved=not reasons,
                reason_codes=tuple(sorted(set(reasons))),
                risk_policy_version="long-only-basic-v1",
                order_digest=order_fingerprint(order),
            )
        )
    return tuple(result)
