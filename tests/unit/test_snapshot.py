"""As-of snapshots are immune to future data changes."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from nano_quant.core import ContractError
from nano_quant.data import build_snapshot, golden_bars

DECISION_AT = datetime(2026, 1, 5, 21, 2, tzinfo=timezone.utc)


def test_asof_snapshot_keeps_only_available_bars() -> None:
    today, tomorrow = golden_bars()
    snap = build_snapshot([today, tomorrow], as_of=DECISION_AT, universe=("SYNTH-A",))
    assert snap.bars == (today,)
    assert snap.universe == ("SYNTH-A",)


def test_future_price_perturbation_cannot_change_past_snapshot() -> None:
    today, tomorrow = golden_bars()
    before = build_snapshot([today, tomorrow], as_of=DECISION_AT, universe=("SYNTH-A",))
    mutated_future = replace(tomorrow, close=Decimal("200"), high=Decimal("200"))
    after = build_snapshot(
        [today, mutated_future], as_of=DECISION_AT, universe=("SYNTH-A",)
    )
    assert before == after


def test_future_data_publication_is_not_visible() -> None:
    today, _ = golden_bars()
    late = replace(
        today,
        available_at=datetime(2026, 1, 7, 21, 1, tzinfo=timezone.utc),
    )
    snap = build_snapshot([late], as_of=DECISION_AT, universe=("SYNTH-A",))
    assert snap.bars == ()


def test_no_duplicate_bars_are_silently_accepted() -> None:
    today, _ = golden_bars()
    with pytest.raises(ContractError, match="duplicate"):
        build_snapshot([today, today], as_of=DECISION_AT, universe=("SYNTH-A",))


def test_snapshot_rejects_naive_asof() -> None:
    with pytest.raises(ContractError):
        build_snapshot([], as_of=datetime(2026, 1, 5), universe=("SYNTH-A",))
