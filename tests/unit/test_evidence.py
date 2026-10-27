"""Synthetic original/revised disclosures and historical delisting controls."""

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from nano_quant.core import ContractError
from nano_quant.data.evidence import (
    CorporateAction,
    ListingRecord,
    Observation,
    historical_members,
    reject_unsupported_actions,
    vintage_as_of,
)

UTC = timezone.utc
D = date(2025, 12, 31)


def when(day: int) -> datetime:
    return datetime(2026, 2, day, 15, tzinfo=UTC)


def evidence(revision: int = 1) -> Observation:
    return Observation(
        source_id="fixture-issuer-doc",
        key="SYNTH-A:FY2025:revenue",
        period_end=D,
        value=Decimal("100") if revision == 1 else Decimal("112"),
        published_at=when(4 if revision == 1 else 20),
        available_at=when(5 if revision == 1 else 21),
        ingested_at=when(6 if revision == 1 else 22),
        revision=revision,
        source_document_sha256=("a" if revision == 1 else "b") * 64,
    )


def test_latest_restatement_is_not_visible_before_available_at() -> None:
    old, revised = evidence(1), evidence(2)
    assert vintage_as_of((revised, old), as_of=when(10)) == (old,)
    assert vintage_as_of((old, revised), as_of=when(21)) == (revised,)
    assert vintage_as_of((revised, old), as_of=when(4)) == ()
    # Public data already available, but this historical system had not ingested it.
    assert vintage_as_of((old, revised), as_of=when(21),
                         operational_replay=True) == (old,)
    assert vintage_as_of((old, revised), as_of=when(22),
                         operational_replay=True) == (revised,)


def test_future_publication_shift_cannot_backfill_past_research() -> None:
    original, revised = evidence(1), evidence(2)
    changed = replace(revised, available_at=when(25))
    asof = when(21)
    assert vintage_as_of((original, changed), as_of=asof) == (original,)
    assert vintage_as_of((original, revised), as_of=asof) == (revised,)


def test_original_evidence_is_retained_and_duplicates_rejected() -> None:
    a = evidence(1)
    with pytest.raises(ContractError, match="DUPLICATE_OBSERVATION_REVISION"):
        vintage_as_of((a, a), as_of=when(10))
    with pytest.raises(ContractError, match="source_document_sha256"):
        replace(a, source_document_sha256="unknown")
    with pytest.raises(ContractError, match="publication"):
        replace(a, available_at=when(3))
    with pytest.raises(ContractError, match="finite"):
        replace(a, value=Decimal("NaN"))


def test_historical_universe_includes_ultimately_delisted_security() -> None:
    listings = (
        ListingRecord("SURVIVOR", date(2025, 1, 1), None, "security-master-fixture"),
        ListingRecord("DELISTED", date(2025, 1, 1), date(2026, 1, 10), "security-master-fixture"),
    )
    assert historical_members(listings, date(2026, 1, 9)) == ("DELISTED", "SURVIVOR")
    assert historical_members(listings, date(2026, 1, 12)) == ("SURVIVOR",)
    with pytest.raises(ContractError, match="duplicate listing"):
        historical_members(listings + listings[:1], date(2026, 1, 9))
    with pytest.raises(ContractError, match="listing end"):
        ListingRecord("BAD", date(2026, 2, 1), date(2026, 1, 1), "source")


def test_unsupported_corporate_action_is_not_silently_ignored() -> None:
    action = CorporateAction("SYNTH-A", date(2026, 2, 10), "SPLIT", "synthetic-source")
    reject_unsupported_actions(
        (action,), first_session=date(2026, 1, 1), last_session=date(2026, 2, 9),
    )
    with pytest.raises(ContractError, match="UNSUPPORTED_CORPORATE_ACTION"):
        reject_unsupported_actions(
            (action,), first_session=date(2026, 1, 1), last_session=date(2026, 2, 10),
        )
    with pytest.raises(ContractError, match="invalid corporate"):
        reject_unsupported_actions(
            (), first_session=date(2026, 2, 2), last_session=date(2026, 1, 1),
        )
