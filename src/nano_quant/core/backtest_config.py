"""Strict, versioned configuration for the synthetic Phase C backtest."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from nano_quant.core import ContractError

CONFIG_FIELDS = frozenset({
    "schema_version", "sessions", "lookback_sessions", "top_n",
    "initial_cash_usd", "fee_usd", "slippage_bps",
    "max_single_weight", "cash_buffer",
})
DECIMAL_FIELDS = (
    "initial_cash_usd", "fee_usd", "slippage_bps", "max_single_weight", "cash_buffer"
)


@dataclass(frozen=True)
class BacktestConfig:
    sessions: int = 120
    lookback_sessions: int = 20
    top_n: int = 2
    initial_cash_usd: Decimal = Decimal("10000.00")
    fee_usd: Decimal = Decimal("1.00")
    slippage_bps: Decimal = Decimal("10")
    max_single_weight: Decimal = Decimal("0.50")
    cash_buffer: Decimal = Decimal("0.02")

    def __post_init__(self) -> None:
        for field in ("sessions", "lookback_sessions", "top_n"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool):
                raise ContractError(f"{field} must be an integer")
        if not 60 <= self.sessions <= 500:
            raise ContractError("sessions must be between 60 and 500")
        if not 2 <= self.lookback_sessions < self.sessions:
            raise ContractError("invalid lookback")
        if not 1 <= self.top_n <= 3:
            raise ContractError("top_n must be 1..3")
        for field in ("initial_cash_usd", "fee_usd", "slippage_bps",
                      "max_single_weight", "cash_buffer"):
            value = getattr(self, field)
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ContractError(f"{field} must be finite Decimal")
        if self.initial_cash_usd <= 0 or self.fee_usd < 0:
            raise ContractError("invalid cash/fee")
        if self.initial_cash_usd != self.initial_cash_usd.quantize(Decimal("0.01")):
            raise ContractError("initial cash must use USD cents")
        if self.fee_usd != self.fee_usd.quantize(Decimal("0.01")):
            raise ContractError("fee must use USD cents")
        if not 0 <= self.slippage_bps <= 10000:
            raise ContractError("slippage must be 0..10000 bps")
        if not 0 < self.max_single_weight <= 1:
            raise ContractError("invalid concentration limit")
        if not 0 <= self.cash_buffer < 1:
            raise ContractError("invalid cash buffer")

    def as_dict(self) -> dict[str, int | str]:
        return {
            "schema_version": 1,
            "sessions": self.sessions,
            "lookback_sessions": self.lookback_sessions,
            "top_n": self.top_n,
            "initial_cash_usd": str(self.initial_cash_usd),
            "fee_usd": str(self.fee_usd),
            "slippage_bps": str(self.slippage_bps),
            "max_single_weight": str(self.max_single_weight),
            "cash_buffer": str(self.cash_buffer),
        }


def load_backtest_config(path: Path) -> BacktestConfig:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("unable to load backtest JSON config") from exc
    if not isinstance(raw, dict) or set(raw) != CONFIG_FIELDS or raw["schema_version"] != 1:
        raise ContractError("backtest config schema mismatch")
    for field in ("sessions", "lookback_sessions", "top_n"):
        if not isinstance(raw[field], int) or isinstance(raw[field], bool):
            raise ContractError(f"{field} must be integer")
    for field in DECIMAL_FIELDS:
        if not isinstance(raw[field], str):
            raise ContractError(f"{field} must be decimal string")
    try:
        return BacktestConfig(
            sessions=raw["sessions"],
            lookback_sessions=raw["lookback_sessions"],
            top_n=raw["top_n"],
            initial_cash_usd=Decimal(raw["initial_cash_usd"]),
            fee_usd=Decimal(raw["fee_usd"]),
            slippage_bps=Decimal(raw["slippage_bps"]),
            max_single_weight=Decimal(raw["max_single_weight"]),
            cash_buffer=Decimal(raw["cash_buffer"]),
        )
    except InvalidOperation as exc:
        raise ContractError("invalid numeric config") from exc
