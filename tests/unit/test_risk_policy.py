"""Independent risk decisions can veto executable order plans."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from nano_quant.core import OrderIntent, PortfolioState, Side
from nano_quant.core.research_types import TargetPortfolio
from nano_quant.risk import review_orders

UTC = timezone.utc
AT = datetime(2026, 2, 27, 21, 2, tzinfo=UTC)
OPEN = datetime(2026, 3, 2, 14, 30, tzinfo=UTC)


def _order(symbol="A", side=Side.BUY, quantity=10, oid="o", at=AT):
    return OrderIntent(oid, symbol, side, quantity, at, OPEN, "previous close")


def test_approval_happy_path() -> None:
    target = TargetPortfolio(AT, (("A", Decimal(".49")),))
    state = PortfolioState(AT, Decimal("1000.00"), {}, {})
    result = review_orders(target, (_order(),), state, allowed_instruments=("A",))
    assert len(result) == 1
    assert result[0].approved and not result[0].reason_codes


def test_risk_rejects_concentration_and_untradeable() -> None:
    target = TargetPortfolio(AT, (("A", Decimal(".6")),))
    state = PortfolioState(AT, Decimal("1000.00"), {}, {})
    result = review_orders(target, (_order(),), state, allowed_instruments=("B",))
    assert not result[0].approved
    assert set(result[0].reason_codes) == {"POSITION_LIMIT", "UNTRADEABLE"}


def test_risk_rejects_duplicate_orders_and_stale_state() -> None:
    target = TargetPortfolio(AT, (("A", Decimal(".49")),))
    state = PortfolioState(AT + timedelta(hours=1), Decimal("1000.00"), {}, {})
    order = _order()
    result = review_orders(target, (order, order), state, allowed_instruments=("A",))
    assert "ASOF_VIOLATION" in result[0].reason_codes
    assert "DUPLICATE_ORDER" in result[1].reason_codes


def test_sell_exceeding_holding_is_rejected() -> None:
    target = TargetPortfolio(AT, ())
    state = PortfolioState(AT, Decimal("1000.00"), {"A": 1}, {"A": Decimal("10")})
    result = review_orders(
        target, (_order(side=Side.SELL, quantity=2),),
        state, allowed_instruments=("A",),
    )
    assert result[0].reason_codes == ("POSITION_LIMIT",)


def test_buy_outside_target_and_wrong_time_rejected() -> None:
    target = TargetPortfolio(AT, ())
    state = PortfolioState(AT, Decimal("1000.00"), {}, {})
    order = _order(at=AT - timedelta(minutes=1))
    result = review_orders(target, (order,), state, allowed_instruments=("A",))
    assert set(result[0].reason_codes) == {"ASOF_VIOLATION", "UNTRADEABLE"}


def test_no_orders_requires_no_risk_decisions() -> None:
    target = TargetPortfolio(AT, ())
    state = PortfolioState(AT, Decimal("100.00"), {}, {})
    assert review_orders(target, (), state, allowed_instruments=("A",)) == ()
