"""Schema-checked config for Phase B golden smoke only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from nano_quant.core import ContractError

_ALLOWED = frozenset(
    {"schema_version", "initial_cash_usd", "quantity", "fee_usd", "slippage_bps"}
)


@dataclass(frozen=True)
class SmokeConfig:
    initial_cash: Decimal = Decimal("1000.00")
    quantity: int = 10
    fee: Decimal = Decimal("1.00")
    slippage_bps: Decimal = Decimal("10")

    def __post_init__(self) -> None:
        if not self.initial_cash.is_finite() or self.initial_cash <= 0:
            raise ContractError("initial_cash must be positive and finite")
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool):
            raise ContractError("quantity must be an integer")
        if self.quantity <= 0:
            raise ContractError("quantity must be positive")
        if not self.fee.is_finite() or self.fee < 0:
            raise ContractError("fee must be finite and nonnegative")
        if not self.slippage_bps.is_finite() or not (0 <= self.slippage_bps <= 10000):
            raise ContractError("slippage_bps must be between 0 and 10000")


def load_smoke_config(path: Path) -> SmokeConfig:
    """Strict JSON schema: no silently ignored configuration parameters."""
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ContractError("smoke config must be a JSON object")
    if set(payload) != _ALLOWED or payload["schema_version"] != 1:
        raise ContractError("unknown/missing config keys or schema version")
    if not isinstance(payload["quantity"], int) or isinstance(payload["quantity"], bool):
        raise ContractError("quantity must be integer")
    for name in ("initial_cash_usd", "fee_usd", "slippage_bps"):
        if not isinstance(payload[name], str):
            raise ContractError(f"{name} must be a decimal string")
    try:
        return SmokeConfig(
            initial_cash=Decimal(payload["initial_cash_usd"]),
            quantity=payload["quantity"],
            fee=Decimal(payload["fee_usd"]),
            slippage_bps=Decimal(payload["slippage_bps"]),
        )
    except InvalidOperation as exc:
        raise ContractError("invalid decimal config") from exc
