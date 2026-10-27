"""Foundational USD finance arithmetic with explicit assumptions and inputs."""

from __future__ import annotations

from decimal import Decimal

from nano_quant.core import ContractError


def _finite(values: tuple[Decimal, ...], *, field: str) -> None:
    if not values or any(
        not isinstance(value, Decimal) or not value.is_finite() for value in values
    ):
        raise ContractError(f"{field} requires finite Decimal values")


def simple_return(
    opening_value: Decimal, closing_value: Decimal,
    cash_distribution: Decimal = Decimal("0"),
) -> Decimal:
    """Holding-period simple total return, including a cash distribution.

    The valuation units must match; do not silently mix currencies/price adjustments.
    """
    _finite((opening_value, closing_value, cash_distribution), field="return")
    if opening_value <= 0:
        raise ContractError("return opening value must be positive")
    return (closing_value + cash_distribution) / opening_value - 1


def sample_covariance(
    x: tuple[Decimal, ...], y: tuple[Decimal, ...]
) -> Decimal:
    """Unbiased sample covariance of equally spaced, aligned observations."""
    _finite(x, field="first sample")
    _finite(y, field="second sample")
    if len(x) != len(y) or len(x) < 2:
        raise ContractError("covariance needs two aligned samples of length >= 2")
    count = Decimal(len(x))
    avg_x = sum(x, Decimal("0")) / count
    avg_y = sum(y, Decimal("0")) / count
    return sum(
        ((left - avg_x) * (right - avg_y) for left, right in zip(x, y)),
        Decimal("0"),
    ) / (count - 1)


def sample_volatility(returns: tuple[Decimal, ...]) -> Decimal:
    """Sample standard deviation for returns in their original period units."""
    variance = sample_covariance(returns, returns)
    return variance.sqrt()


def max_drawdown(nav: tuple[Decimal, ...]) -> Decimal:
    """Maximum high-water-mark decline as a positive fraction, not percentage."""
    _finite(nav, field="NAV")
    if any(value <= 0 for value in nav):
        raise ContractError("NAV must be positive")
    peak = nav[0]
    biggest = Decimal("0")
    for value in nav:
        peak = max(peak, value)
        biggest = max(biggest, Decimal("1") - value / peak)
    return biggest
