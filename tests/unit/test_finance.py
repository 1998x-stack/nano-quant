"""Independent hand-computed examples for financial mathematics."""

from decimal import Decimal

import pytest

from nano_quant.core import ContractError
from nano_quant.finance import (
    max_drawdown,
    sample_covariance,
    sample_volatility,
    simple_return,
)


def test_simple_total_return_with_distribution() -> None:
    assert simple_return(
        Decimal("100"), Decimal("105"), Decimal("2")
    ) == Decimal(".07")
    assert simple_return(Decimal("100"), Decimal("90")) == Decimal("-.1")


def test_finance_rejects_invalid_inputs() -> None:
    with pytest.raises(ContractError):
        simple_return(Decimal("0"), Decimal("100"))
    with pytest.raises(ContractError):
        simple_return(Decimal("100"), Decimal("NaN"))
    with pytest.raises(ContractError):
        sample_covariance((Decimal("1"),), (Decimal("2"),))
    with pytest.raises(ContractError):
        sample_covariance((Decimal("1"), Decimal("2")), (Decimal("3"),))
    with pytest.raises(ContractError):
        sample_covariance((Decimal("1"), Decimal("NaN")), (Decimal("1"), Decimal("2")))
    with pytest.raises(ContractError):
        max_drawdown(())
    with pytest.raises(ContractError):
        max_drawdown((Decimal("100"), Decimal("0")))


def test_covariance_and_volatility_manual() -> None:
    x = (Decimal("1"), Decimal("2"), Decimal("3"))
    y = (Decimal("2"), Decimal("4"), Decimal("6"))
    assert sample_covariance(x, y) == Decimal("2")
    assert sample_covariance(x, x) == Decimal("1")
    assert sample_volatility(x) == Decimal("1")
    assert sample_covariance(x, tuple(-v for v in x)) == Decimal("-1")


def test_max_drawdown_manual() -> None:
    assert max_drawdown((
        Decimal("100"), Decimal("120"), Decimal("90"), Decimal("105")
    )) == Decimal("0.25")
    assert max_drawdown((Decimal("100"), Decimal("120"))) == Decimal("0")
