"""Explicit Phase D *diagnostics* on the fictional Phase C market.

No model is fitted and no real-market observation is provided. Rolling windows
are a proposed chronological protocol, NOT completed out-of-sample results.
"""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

from nano_quant.backtest import run_backtest
from nano_quant.core import ContractError
from nano_quant.core.backtest_config import BacktestConfig
from nano_quant.data.synthetic import DATASET_ID, INSTRUMENTS, synthetic_equities
from nano_quant.validation.research import (
    circular_shift_negative_control,
    walk_forward_windows,
)


def validation_audit(config: BacktestConfig) -> dict[str, object]:
    """Compute reproducible diagnostics without implying predictive validity.

    Cost comparison is only interpretable if both runs execute identical
    ordered trade terms. A change in order list makes it INCOMPARABLE.
    """
    bars = tuple(
        bar for bar in synthetic_equities(config.sessions)
        if bar.instrument_id == INSTRUMENTS[0]
    )
    x: list[Decimal] = []
    y: list[Decimal] = []
    lookback = config.lookback_sessions
    for t in range(lookback, len(bars) - 1):
        x.append(bars[t].close / bars[t - lookback].close - Decimal("1"))
        y.append(bars[t + 1].close / bars[t].close - Decimal("1"))

    control = circular_shift_negative_control(
        x, y, label_horizon=1, draws=40, seed=42
    )
    train_size = max(30, config.sessions // 2)
    test_size = max(5, config.sessions // 10)
    windows = walk_forward_windows(
        config.sessions, train_size, test_size, label_horizon=1,
        step_size=test_size,
    )
    normal = run_backtest(config)
    stress = run_backtest(replace(config, fee_usd=config.fee_usd + Decimal("2.00")))

    def signature(run: object) -> tuple[tuple[str, str, int, str], ...]:
        from nano_quant.backtest import BacktestResult

        if not isinstance(run, BacktestResult):
            raise ContractError("invalid backtest result")
        return tuple((
            fill.order_id,
            fill.side.value,
            fill.quantity,
            fill.filled_at.isoformat(),
        ) for fill in run.fills)

    same_path = signature(normal) == signature(stress)
    baseline_nav = Decimal(str(normal.metrics["ending_nav_usd"]))
    stress_nav = Decimal(str(stress.metrics["ending_nav_usd"]))
    fee_check = (
        "INCOMPARABLE_DIFFERENT_TRADE_PATH"
        if not same_path else
        "PASS" if stress_nav <= baseline_nav else "FAIL"
    )
    if fee_check == "FAIL":
        raise ContractError("fee stress violates monotonicity on identical fills")

    return {
        "phase": "D",
        "data_manifest_id": DATASET_ID,
        "dataset_sha256": normal.dataset_hash,
        "baseline_run_id": normal.run_id,
        "scope": "synthetic-only diagnostic; not a real market or alpha test",
        "trained_model": False,
        "out_of_sample_model_results": False,
        "walk_forward_protocol_only": [
            {
                "train_start": w.train_start,
                "train_end_exclusive": w.train_end,
                "test_start": w.test_start,
                "test_end_exclusive": w.test_end,
                "label_horizon_sessions": w.horizon,
            }
            for w in windows
        ],
        "diagnostic_rank_ic": control.observed_rank_ic,
        "circular_shift_null_p_positive": control.one_sided_empirical_p,
        "negative_control_method": control.method,
        "negative_control_draws": len(control.null_rank_ics),
        "cost_sensitivity": {
            "fee_increment_usd_per_fill": "2.00",
            "same_order_path": same_path,
            "comparison": fee_check,
            "baseline_ending_nav_usd": str(baseline_nav),
            "stressed_ending_nav_usd": str(stress_nav),
        },
        "limitations": [
            "circular shift on dependent, nonstationary observations is not a confirmatory test",
            "walk-forward protocol is defined but no model has been fit across windows",
            "historical universe and disclosure timing tests use synthetic evidence",
            "corporate actions in the trading interval are rejected, not processed",
            "no real-world data, alpha, or market execution has been validated",
        ],
    }


def write_validation_audit(config: BacktestConfig, path: Path) -> dict[str, object]:
    report = validation_audit(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
