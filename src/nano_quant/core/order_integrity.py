"""Canonical fingerprint binds a simulation risk decision to exact order terms.

This is an internal tamper-evident integrity check, NOT a signature, security
authorization system, or mechanism to prevent a malicious caller fabricating a
RiskDecision; production authentication is out of scope.
"""

from __future__ import annotations

import hashlib
import json

from nano_quant.core.types import OrderIntent


def order_fingerprint(order: OrderIntent) -> str:
    payload = {
        "order_id": order.order_id,
        "instrument_id": order.instrument_id,
        "side": order.side.value,
        "quantity": order.quantity,
        "created_at": order.created_at.isoformat(),
        "earliest_execution_at": order.earliest_execution_at.isoformat(),
        "reference_price_context": order.reference_price_context,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
