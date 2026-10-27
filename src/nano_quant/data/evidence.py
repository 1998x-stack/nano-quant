"""Point-in-time evidence vintages, never 'latest value' historical lookups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from nano_quant.core import ContractError, ensure_utc


@dataclass(frozen=True)
class Observation:
    """One *published revision* of an observation about a historical period.

    revision is an identifier scoped to (source_id, key, period_end), not the
    availability order. Original evidence is retained, never overwritten.
    """
    source_id: str
    key: str
    period_end: date
    value: Decimal
    published_at: datetime
    available_at: datetime
    ingested_at: datetime
    revision: int
    source_document_sha256: str

    def __post_init__(self) -> None:
        if not self.source_id or not self.key:
            raise ContractError("source and observation key required")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ContractError("observation value must be finite Decimal")
        for field in ("published_at", "available_at", "ingested_at"):
            ensure_utc(getattr(self, field), field)
        if not (self.published_at <= self.available_at):
            raise ContractError("publication must precede availability")
        if self.ingested_at < self.published_at:
            raise ContractError("ingestion cannot predate original publication")
        if type(self.revision) is not int or self.revision < 1:
            raise ContractError("revision must be a positive integer")
        if (len(self.source_document_sha256) != 64 or
            any(ch not in "0123456789abcdef" for ch in self.source_document_sha256)):
            raise ContractError("source_document_sha256 must be lowercase 64-digit hex")


def vintage_as_of(
    observations: Iterable[Observation],
    *,
    as_of: datetime,
    operational_replay: bool = False,
) -> tuple[Observation, ...]:
    """Pick latest visible vintage by (source, key, period) at an as-of time.

    Publication-as-of simulates *public knowledge*, not a historical live
    system's archived holdings. operational_replay also requires ingested_at
    <= as_of. Refuses conflicting/duplicate revision identifiers.
    """
    ensure_utc(as_of, "as_of")
    seen: set[tuple[str, str, date, int]] = set()
    latest: dict[tuple[str, str, date], Observation] = {}
    for observation in observations:
        ident = (
            observation.source_id, observation.key,
            observation.period_end, observation.revision,
        )
        if ident in seen:
            raise ContractError("DUPLICATE_OBSERVATION_REVISION")
        seen.add(ident)
        if observation.available_at > as_of:
            continue
        if operational_replay and observation.ingested_at > as_of:
            continue
        group = ident[:3]
        previous = latest.get(group)
        if previous is None or (
            observation.available_at, observation.revision
        ) > (
            previous.available_at, previous.revision
        ):
            latest[group] = observation
    return tuple(latest[k] for k in sorted(latest))


@dataclass(frozen=True)
class ListingRecord:
    """Historical instrument lifetime, not a verified announcement-time universe."""
    instrument_id: str
    first_session: date
    last_session: date | None
    source_id: str

    def __post_init__(self) -> None:
        if not self.instrument_id or not self.source_id:
            raise ContractError("listing source and instrument required")
        if self.last_session is not None and self.last_session < self.first_session:
            raise ContractError("listing end precedes start")


def historical_members(
    listings: Iterable[ListingRecord], session: date
) -> tuple[str, ...]:
    """Reconstruct historical membership without survivorship filtering.

    Real PIT eligibility additionally needs announcement/delisting *known_at*,
    security master, and trading-status data. This function alone is insufficient
    for an investment-grade equity universe.
    """
    rows = tuple(listings)
    ids = [record.instrument_id for record in rows]
    if len(ids) != len(set(ids)):
        raise ContractError("duplicate listing identities")
    return tuple(sorted(
        item.instrument_id
        for item in rows
        if item.first_session <= session
        and (item.last_session is None or session <= item.last_session)
    ))


@dataclass(frozen=True)
class CorporateAction:
    instrument_id: str
    effective_session: date
    kind: str
    source_id: str

    def __post_init__(self) -> None:
        if not all((self.instrument_id, self.kind, self.source_id)):
            raise ContractError("corporate action identity required")


def reject_unsupported_actions(
    actions: Iterable[CorporateAction], *, first_session: date, last_session: date
) -> None:
    """Fail closed rather than silently omitting dividends/splits/delisting.

    The v1 simulated ledger does not book corporate actions.
    """
    if first_session > last_session:
        raise ContractError("invalid corporate action check interval")
    if any(
        first_session <= item.effective_session <= last_session
        for item in actions
    ):
        raise ContractError("UNSUPPORTED_CORPORATE_ACTION")
