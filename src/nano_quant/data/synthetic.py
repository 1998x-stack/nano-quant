"""Deterministic fictional OHLCV prices. NOT an actual XNYS trading calendar."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from nano_quant.core import ContractError, PriceBar

CENT = Decimal("0.01")
UTC = timezone.utc
INSTRUMENTS = ("SYNTH-A", "SYNTH-B", "SYNTH-C")
DATASET_ID = "synthetic-equities-c-v1"


def synthetic_sessions(start: date, sessions: int) -> tuple[date, ...]:
    if not 25 <= sessions <= 500:
        raise ContractError("synthetic sessions must be between 25 and 500")
    days: list[date] = []
    day = start
    while len(days) < sessions:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return tuple(days)


def synthetic_equities(sessions: int = 120) -> tuple[PriceBar, ...]:
    """Pure deterministic arithmetic; prices are deliberately artificial.

    Times are fixed UTC convenience clock times for a *synthetic* exchange;
    they do NOT model New York DST or real exchange closures.
    """
    days = synthetic_sessions(date(2026, 1, 5), sessions)
    previous = {
        "SYNTH-A": Decimal("50"),
        "SYNTH-B": Decimal("70"),
        "SYNTH-C": Decimal("90"),
    }
    bars: list[PriceBar] = []
    for i, day in enumerate(days):
        for j, symbol in enumerate(INSTRUMENTS):
            open_change = Decimal(((i * 3 + j * 7) % 9) - 4) / Decimal("2000")
            drift = (Decimal((j - 1) * 2 + ((i + 3 * j) % 11) - 5)
                     / Decimal("1000"))
            # Rotate artificial strength after about every 30 trading sessions.
            regime = Decimal(((i // 30 + j) % 3) - 1) / Decimal("1000")
            op = (previous[symbol] * (1 + open_change)).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            close = (op * (1 + drift + regime)).quantize(CENT, rounding=ROUND_HALF_UP)
            high = (max(op, close) * Decimal("1.003")).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            low = (min(op, close) * Decimal("0.997")).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
            bar = PriceBar(
                instrument_id=symbol,
                session_date=day,
                open=op,
                high=high,
                low=low,
                close=close,
                volume=10000 + ((i * 31 + j * 113) % 3000),
                open_at=datetime.combine(day, time(14, 30), tzinfo=UTC),
                event_at=datetime.combine(day, time(21, 0), tzinfo=UTC),
                available_at=datetime.combine(day, time(21, 1), tzinfo=UTC),
                source_id=DATASET_ID,
            )
            bars.append(bar)
            previous[symbol] = close
    return tuple(bars)
