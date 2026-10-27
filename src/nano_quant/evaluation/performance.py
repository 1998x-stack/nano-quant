"""Deterministic simple-return and drawdown analysis over a NAV series."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class NavPoint:
    session_date: str
    nav: Decimal


def evaluate_nav(points: tuple[NavPoint, ...]) -> dict[str, str | int]:
    if not points or points[0].nav <= 0:
        raise ValueError("NAV series must start with a positive value")
    peak = points[0].nav
    max_drawdown = Decimal("0")
    for point in points:
        if point.nav <= 0:
            raise ValueError("NAV cannot be nonpositive in this v1 baseline")
        peak = max(peak, point.nav)
        max_drawdown = max(max_drawdown, Decimal("1") - point.nav / peak)
    total = points[-1].nav / points[0].nav - 1
    return {
        "sessions": len(points),
        "initial_nav_usd": str(points[0].nav),
        "ending_nav_usd": str(points[-1].nav),
        "net_total_return_pct": str((total * 100).quantize(Decimal("0.0001"))),
        "max_drawdown_pct": str((max_drawdown * 100).quantize(Decimal("0.0001"))),
        "cash_benchmark_total_return_pct": "0",
    }
