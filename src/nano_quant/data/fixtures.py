"""Deterministic two-session fixture, explicitly not real market data."""

from datetime import date, datetime, timezone
from decimal import Decimal

from nano_quant.core import PriceBar

UTC = timezone.utc


def golden_bars() -> tuple[PriceBar, PriceBar]:
    """Two synthetic trading sessions for acceptance Golden Ledger A."""
    return (
        PriceBar(
            instrument_id="SYNTH-A",
            session_date=date(2026, 1, 5),
            open=Decimal("9.50"),
            high=Decimal("10.00"),
            low=Decimal("9.50"),
            close=Decimal("10.00"),
            volume=1000,
            open_at=datetime(2026, 1, 5, 14, 30, tzinfo=UTC),
            event_at=datetime(2026, 1, 5, 21, tzinfo=UTC),
            available_at=datetime(2026, 1, 5, 21, 1, tzinfo=UTC),
            source_id="synthetic-golden-v1",
        ),
        PriceBar(
            instrument_id="SYNTH-A",
            session_date=date(2026, 1, 6),
            open=Decimal("10.00"),
            high=Decimal("11.00"),
            low=Decimal("9.90"),
            close=Decimal("11.00"),
            volume=1100,
            open_at=datetime(2026, 1, 6, 14, 30, tzinfo=UTC),
            event_at=datetime(2026, 1, 6, 21, tzinfo=UTC),
            available_at=datetime(2026, 1, 6, 21, 1, tzinfo=UTC),
            source_id="synthetic-golden-v1",
        ),
    )
