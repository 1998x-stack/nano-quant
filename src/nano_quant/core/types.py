"""Minimal immutable contracts used by the Phase B vertical smoke test.

USD-only, integer-share, cash-equity semantics. Advanced research DTOs remain
specified in docs/architecture/contracts.md for Phase C.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class ContractError(ValueError):
    """Invalid financial, timestamp, or accounting contract."""


def ensure_utc(value: datetime, field: str = "timestamp") -> None:
    """Enforce explicitly timezone-aware UTC, never naive/local timestamps."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ContractError(f"{field} must be timezone-aware UTC")


def _positive(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ContractError(f"{field} must be finite and positive")


def _nonnegative(value: Decimal, field: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ContractError(f"{field} must be finite and nonnegative")


@dataclass(frozen=True)
class PriceBar:
    instrument_id: str
    session_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    open_at: datetime
    event_at: datetime
    available_at: datetime
    source_id: str

    def __post_init__(self) -> None:
        if not self.instrument_id or not self.source_id:
            raise ContractError("instrument_id and source_id are required")
        for field in ("open", "high", "low", "close"):
            _positive(getattr(self, field), field)
        if self.high < max(self.open, self.close, self.low):
            raise ContractError("high below other OHLC prices")
        if self.low > min(self.open, self.close, self.high):
            raise ContractError("low above other OHLC prices")
        if not isinstance(self.volume, int) or isinstance(self.volume, bool) or self.volume < 0:
            raise ContractError("volume must be a nonnegative integer")
        for field in ("open_at", "event_at", "available_at"):
            ensure_utc(getattr(self, field), field)
        if not (self.open_at < self.event_at <= self.available_at):
            raise ContractError("require open_at < event_at <= available_at")


@dataclass(frozen=True)
class DataSnapshot:
    as_of: datetime
    bars: tuple[PriceBar, ...]
    universe: tuple[str, ...]
    calendar_id: str
    data_manifest_id: str

    def __post_init__(self) -> None:
        ensure_utc(self.as_of, "as_of")
        if not self.calendar_id or not self.data_manifest_id:
            raise ContractError("calendar_id and data_manifest_id are required")
        if len(self.universe) != len(set(self.universe)) or not all(self.universe):
            raise ContractError("universe must contain unique, nonempty IDs")
        seen: set[tuple[str, date]] = set()
        for bar in self.bars:
            if bar.available_at > self.as_of or bar.event_at > self.as_of:
                raise ContractError("ASOF_VIOLATION")
            if bar.instrument_id not in self.universe:
                raise ContractError("bar instrument is not in the universe")
            key = (bar.instrument_id, bar.session_date)
            if key in seen:
                raise ContractError("duplicate price bar")
            seen.add(key)


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class OrderIntent:
    order_id: str
    instrument_id: str
    side: Side
    quantity: int
    created_at: datetime
    earliest_execution_at: datetime
    reference_price_context: str

    def __post_init__(self) -> None:
        if not self.order_id or not self.instrument_id or not self.reference_price_context:
            raise ContractError("order identifier, instrument, price context required")
        if not isinstance(self.side, Side):
            raise ContractError("side must be Side")
        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool) or self.quantity <= 0:
            raise ContractError("order quantity must be a positive integer")
        ensure_utc(self.created_at, "created_at")
        ensure_utc(self.earliest_execution_at, "earliest_execution_at")
        if self.earliest_execution_at <= self.created_at:
            raise ContractError("earliest execution must follow order creation")


@dataclass(frozen=True)
class RiskDecision:
    as_of: datetime
    order_ids: tuple[str, ...]
    approved: bool
    reason_codes: tuple[str, ...]
    risk_policy_version: str
    order_digest: str | None = None

    def __post_init__(self) -> None:
        ensure_utc(self.as_of, "as_of")
        if self.order_digest is not None and (
            len(self.order_digest) != 64
            or any(c not in "0123456789abcdef" for c in self.order_digest)
        ):
            raise ContractError("order_digest must be SHA256 hex")
        if not self.order_ids or len(self.order_ids) != len(set(self.order_ids)):
            raise ContractError("risk decision must reference distinct order IDs")
        if not self.risk_policy_version:
            raise ContractError("risk policy version required")
        if self.approved and self.reason_codes:
            raise ContractError("approved decision must not have rejection codes")
        if not self.approved and not self.reason_codes:
            raise ContractError("rejected decision must explain why")


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    instrument_id: str
    side: Side
    quantity: int
    price: Decimal
    fee: Decimal
    filled_at: datetime

    def __post_init__(self) -> None:
        if not self.fill_id or not self.order_id or not self.instrument_id:
            raise ContractError("fill identifiers required")
        if (not isinstance(self.side, Side) or not isinstance(self.quantity, int)
                or isinstance(self.quantity, bool) or self.quantity <= 0):
            raise ContractError("invalid fill side or quantity")
        _positive(self.price, "fill price")
        _nonnegative(self.fee, "fill fee")
        ensure_utc(self.filled_at, "filled_at")


@dataclass(frozen=True)
class PortfolioState:
    as_of: datetime
    cash: Decimal
    positions: Mapping[str, int]
    marks: Mapping[str, Decimal]
    ledger_version: str = "ledger-v1"

    def __post_init__(self) -> None:
        ensure_utc(self.as_of, "as_of")
        _nonnegative(self.cash, "cash")
        if self.cash != self.cash.quantize(Decimal("0.01")):
            raise ContractError("USD cash must use cents")
        if not self.ledger_version:
            raise ContractError("ledger_version required")
        if any(not symbol or not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0
               for symbol, qty in self.positions.items()):
            raise ContractError("positions must be positive whole shares")
        if set(self.positions) != set(self.marks):
            raise ContractError("each position requires exactly one valuation mark")
        for mark in self.marks.values():
            _positive(mark, "mark")
        object.__setattr__(self, "positions", MappingProxyType(dict(self.positions)))
        object.__setattr__(self, "marks", MappingProxyType(dict(self.marks)))

    @property
    def nav(self) -> Decimal:
        return self.cash + sum(
            (self.marks[symbol] * qty for symbol, qty in self.positions.items()),
            Decimal("0"),
        )
