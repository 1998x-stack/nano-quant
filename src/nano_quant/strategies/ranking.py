"""Top-N rank strategy with deterministic tie-breaking."""

from nano_quant.core import ContractError
from nano_quant.core.research_types import Forecast, StrategySignal


def select_top_n(forecast: Forecast, top_n: int = 2) -> tuple[StrategySignal, ...]:
    if top_n < 1:
        raise ContractError("top_n must be positive")
    ranked = sorted(forecast.scores, key=lambda item: (-item[1], item[0]))
    return tuple(
        StrategySignal(
            as_of=forecast.as_of,
            instrument_id=instrument,
            score=score,
            strategy_version="monthly-top-n-v1",
        )
        for instrument, score in ranked[:top_n]
    )
