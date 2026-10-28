"""Independent, deterministic accounting replay for candidate release artifacts.

This function DOES NOT call the production execution or evaluation code.
It recomputes cash, holdings, every day's NAV and drawdown from the released
CSV outputs and the versioned synthetic OHLCV fixture. This is still a
synthetic software audit, not evidence that investment signals are sound.
"""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from nano_quant.data.synthetic import INSTRUMENTS, synthetic_equities


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _decimal(text: object, label: str) -> Decimal:
    try:
        _assert(isinstance(text, str), f"{label}: expected decimal string")
        value = Decimal(text)
        _assert(value.is_finite(), f"{label}: non-finite number")
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    return value


def verify_financial_replay(
    manifest: dict[str, Any],
    metrics: dict[str, Any],
    nav_rows: list[dict[str, str]],
    trade_rows: list[dict[str, str]],
) -> None:
    """Cross-check independently from the public deterministic fixture.

    The source data generator itself is not an independent real-market
    reference; only the ledger calculation is independently reimplemented.
    """
    config = manifest["config"]
    bars = synthetic_equities(int(config["sessions"]))
    by_day: dict[str, dict[str, Any]] = {}
    for bar in bars:
        by_day.setdefault(bar.session_date.isoformat(), {})[bar.instrument_id] = bar

    # The exact input-bar fingerprint must match the claimed simulation input.
    records = [
        [
            b.instrument_id, b.session_date.isoformat(), str(b.open),
            str(b.high), str(b.low), str(b.close), b.volume,
            b.available_at.isoformat(),
        ]
        for b in bars
    ]
    serialized = json.dumps(
        records, separators=(",", ":"), sort_keys=True, ensure_ascii=False
    )
    dataset_digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    _assert(
        dataset_digest == manifest.get("dataset_sha256"),
        "dataset hash disagrees with synthetic input fixture",
    )

    dates = [row["session_date"] for row in nav_rows]
    _assert(dates == sorted(by_day), "NAV dates disagree with market sessions")
    initial_cash = _decimal(config["initial_cash_usd"], "initial cash")
    fee_schedule = _decimal(config["fee_usd"], "fee schedule")
    slippage = _decimal(config["slippage_bps"], "slippage")
    fills_by_day: dict[str, list[dict[str, str]]] = {}
    for fill in trade_rows:
        day = fill["filled_at_utc"][:10]
        _assert(day in by_day, "trade outside simulated sessions")
        fills_by_day.setdefault(day, []).append(fill)

    cash = initial_cash
    held: dict[str, int] = {}
    peak = initial_cash
    maximum_drawdown = Decimal("0")
    for row in nav_rows:
        day = row["session_date"]
        market = by_day[day]
        for fill in fills_by_day.get(day, []):
            symbol = fill["instrument"]
            _assert(symbol in INSTRUMENTS and symbol in market, "unknown instrument")
            bar = market[symbol]
            _assert(
                fill["filled_at_utc"] == bar.open_at.isoformat(),
                "fill timing differs from raw synthetic opening event",
            )
            try:
                quantity = int(fill["shares"])
            except (ValueError, TypeError) as exc:
                raise ValueError("invalid share quantity") from exc
            _assert(quantity > 0, "nonpositive share quantity")
            fee = _decimal(fill["fee_usd"], "fill fee")
            _assert(fee == fee_schedule, "fill fee differs from fee schedule")
            executed_price = _decimal(fill["price_usd"], "execution price")
            multiplier = (
                Decimal("1") + slippage / Decimal("10000")
                if fill["side"] == "BUY"
                else Decimal("1") - slippage / Decimal("10000")
            )
            expected_price = (bar.open * multiplier).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            _assert(
                executed_price == expected_price,
                "fill price differs from opening market price and slippage",
            )
            if fill["side"] == "BUY":
                cash -= quantity * executed_price + fee
                held[symbol] = held.get(symbol, 0) + quantity
            elif fill["side"] == "SELL":
                _assert(held.get(symbol, 0) >= quantity, "trade would sell short")
                cash += quantity * executed_price - fee
                held[symbol] -= quantity
                if held[symbol] == 0:
                    del held[symbol]
            else:
                raise ValueError("invalid fill direction")
            _assert(cash >= 0, "trade would overdraw cash")
        reconstructed_nav = cash + sum(
            (bar.close * held[symbol] for symbol, bar in market.items()
             if symbol in held),
            Decimal("0"),
        )
        _assert(
            reconstructed_nav == _decimal(row["nav_usd"], "daily NAV"),
            f"daily NAV inconsistent with independent ledger: {day}",
        )
        peak = max(peak, reconstructed_nav)
        maximum_drawdown = max(
            maximum_drawdown, Decimal("1") - reconstructed_nav / peak
        )
    reported_drawdown = _decimal(metrics.get("max_drawdown_pct"), "drawdown")
    _assert(
        abs(reported_drawdown - maximum_drawdown * 100) <= Decimal("0.00005"),
        "maximum drawdown inconsistent with independent NAV calculation",
    )
