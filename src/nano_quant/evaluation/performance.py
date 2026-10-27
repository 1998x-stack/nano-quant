"""Deterministic simple-return and drawdown analysis over a NAV series."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nano_quant.finance import max_drawdown, simple_return


@dataclass(frozen=True)
class NavPoint:
    session_date: str
    nav: Decimal


def evaluate_nav(points: tuple[NavPoint, ...]) -> dict[str, str | int]:
    if not points or points[0].nav <= 0:
        raise ValueError("NAV series must start with a positive value")
    try:
        drawdown = max_drawdown(tuple(point.nav for point in points))
    except ValueError as exc:
        raise ValueError("NAV cannot be nonpositive in this v1 baseline") from exc
    total = simple_return(points[0].nav, points[-1].nav)
    return {
        "sessions": len(points),
        "initial_nav_usd": str(points[0].nav),
        "ending_nav_usd": str(points[-1].nav),
        "net_total_return_pct": str((total * 100).quantize(Decimal("0.0001"))),
        "max_drawdown_pct": str((drawdown * 100).quantize(Decimal("0.0001"))),
        "cash_benchmark_total_return_pct": "0",
    }
