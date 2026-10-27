"""Research-side immutable cross-module contracts for the Phase C baseline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping

from nano_quant.core import ContractError, ensure_utc


def _freeze_scores(values: Mapping[str, Decimal], field: str) -> tuple[tuple[str, Decimal], ...]:
    if not values:
        raise ContractError(f"{field} cannot be empty")
    if not all(
        symbol and isinstance(value, Decimal) and value.is_finite()
        for symbol, value in values.items()
    ):
        raise ContractError(f"{field} has invalid instrument or score")
    return tuple(sorted(values.items()))


@dataclass(frozen=True)
class FactorFrame:
    as_of: datetime
    lookback_sessions: int
    scores: tuple[tuple[str, Decimal], ...]
    data_manifest_id: str

    def __post_init__(self) -> None:
        ensure_utc(self.as_of)
        if self.lookback_sessions < 1 or not self.data_manifest_id:
            raise ContractError("factor lookback or manifest is invalid")
        if len(self.scores) != len(set(symbol for symbol, _ in self.scores)):
            raise ContractError("duplicate factor instruments")
        if self.scores != _freeze_scores(dict(self.scores), "factor scores"):
            raise ContractError("factor scores must be finite and sorted")


@dataclass(frozen=True)
class Forecast:
    as_of: datetime
    horizon_sessions: int
    target: str
    scores: tuple[tuple[str, Decimal], ...]
    model_version: str
    training_cutoff: datetime | None = None

    def __post_init__(self) -> None:
        ensure_utc(self.as_of)
        if self.training_cutoff is not None:
            ensure_utc(self.training_cutoff)
            if self.training_cutoff > self.as_of:
                raise ContractError("training cutoff after decision time")
        if self.horizon_sessions <= 0 or not self.target or not self.model_version:
            raise ContractError("invalid forecast metadata")
        if self.scores != _freeze_scores(dict(self.scores), "forecast scores"):
            raise ContractError("forecast scores must be finite and sorted")


@dataclass(frozen=True)
class StrategySignal:
    as_of: datetime
    instrument_id: str
    score: Decimal
    strategy_version: str

    def __post_init__(self) -> None:
        ensure_utc(self.as_of)
        if not self.instrument_id or not self.strategy_version or not self.score.is_finite():
            raise ContractError("invalid signal")


@dataclass(frozen=True)
class TargetPortfolio:
    as_of: datetime
    weights: tuple[tuple[str, Decimal], ...]
    base_currency: str = "USD"
    constraints_id: str = "long-only-v1"

    def __post_init__(self) -> None:
        ensure_utc(self.as_of)
        if self.base_currency != "USD" or not self.constraints_id:
            raise ContractError("v1 target must use USD")
        if self.weights != tuple(sorted(self.weights)):
            raise ContractError("target weights must be sorted")
        if len(self.weights) != len(set(symbol for symbol, _ in self.weights)):
            raise ContractError("duplicate target instrument")
        if any(
            not symbol or not isinstance(weight, Decimal) or not weight.is_finite()
            or weight < 0 or weight > 1
            for symbol, weight in self.weights
        ):
            raise ContractError("invalid target weight")
        if sum((weight for _, weight in self.weights), Decimal("0")) > 1:
            raise ContractError("target weights exceed 100 percent")
