"""Minimal snapshot construction with explicit data availability cutoffs."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from nano_quant.core import DataSnapshot, PriceBar, ensure_utc


def build_snapshot(
    bars: Iterable[PriceBar],
    *,
    as_of: datetime,
    universe: tuple[str, ...],
    calendar_id: str = "SYNTHETIC-XNYS",
    data_manifest_id: str = "synthetic-golden-v1",
) -> DataSnapshot:
    """Return only prices available by the decision time.

    This is **not** a real market data adapter. It cannot infer publication
    delays or true historical membership from an arbitrary file.
    """
    ensure_utc(as_of, "as_of")
    visible = tuple(
        sorted(
            (
                bar
                for bar in bars
                if bar.event_at <= as_of
                and bar.available_at <= as_of
                and bar.instrument_id in universe
            ),
            key=lambda bar: (bar.session_date, bar.instrument_id),
        )
    )
    return DataSnapshot(
        as_of=as_of,
        bars=visible,
        universe=universe,
        calendar_id=calendar_id,
        data_manifest_id=data_manifest_id,
    )
