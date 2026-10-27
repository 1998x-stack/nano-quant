"""20-session momentum factor over time-safe end-of-session price snapshots."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from nano_quant.core import ContractError, DataSnapshot
from nano_quant.core.research_types import FactorFrame


def momentum_factor(snapshot: DataSnapshot, lookback_sessions: int = 20) -> FactorFrame:
    """Score each instrument as close[-1]/close[-lookback-1]-1.

    Missing warmup assets are excluded rather than represented by a made-up zero.
    """
    if lookback_sessions < 1:
        raise ContractError("lookback must be positive")
    history: dict[str, list[tuple[date, Decimal]]] = defaultdict(list)
    for bar in snapshot.bars:
        history[bar.instrument_id].append((bar.session_date, bar.close))
    scores: dict[str, Decimal] = {}
    for instrument in snapshot.universe:
        series = sorted(history[instrument], key=lambda item: item[0])
        if len(series) >= lookback_sessions + 1:
            scores[instrument] = series[-1][1] / series[-lookback_sessions - 1][1] - 1
    if not scores:
        raise ContractError("INSUFFICIENT_WARMUP")
    return FactorFrame(
        as_of=snapshot.as_of,
        lookback_sessions=lookback_sessions,
        scores=tuple(sorted(scores.items())),
        data_manifest_id=snapshot.data_manifest_id,
    )
