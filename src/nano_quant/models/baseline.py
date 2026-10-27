"""Deterministic scoring baseline, explicitly NOT a statistically fitted predictor."""

from nano_quant.core.research_types import FactorFrame, Forecast


def baseline_rank_forecast(factors: FactorFrame) -> Forecast:
    """Treat observed momentum as an uncalibrated relative ranking heuristic.

    Predictions are *scores*, not probabilities, expected returns, or proven alpha.
    training_cutoff=None means no model parameters were fitted.
    """
    return Forecast(
        as_of=factors.as_of,
        horizon_sessions=20,
        target="uncalibrated_relative_momentum_score",
        scores=factors.scores,
        model_version="momentum-identity-baseline-v1",
        training_cutoff=None,
    )
