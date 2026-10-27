"""End-to-end synthetic research chain, reproducible outputs, config validation."""

import csv
import json
from pathlib import Path

import pytest

from nano_quant.backtest import run_backtest, write_report
from nano_quant.cli import main
from nano_quant.core import ContractError
from nano_quant.core.backtest_config import BacktestConfig, load_backtest_config
from nano_quant.data.synthetic import DATASET_ID, synthetic_equities
from nano_quant.evaluation.performance import NavPoint, evaluate_nav
from decimal import Decimal


def test_end_to_end_generates_trades_and_reproducible_metrics() -> None:
    config = BacktestConfig()
    a = run_backtest(config)
    b = run_backtest(config)
    assert a == b
    assert len(a.nav_points) == 120
    assert a.dataset_hash == b.dataset_hash and len(a.dataset_hash) == 64
    assert a.run_id == b.run_id and len(a.run_id) == 16
    assert a.decisions > 0
    assert a.signals_generated > 0
    assert len(a.fills) > 0
    assert int(a.metrics["trades"]) == len(a.fills)
    assert a.metrics["cash_benchmark_total_return_pct"] == "0"
    assert all(point.nav > 0 for point in a.nav_points)
    # No fills on the same date as the after-close generation of orders.
    for fill in a.fills:
        assert fill.filled_at.date().isoformat() > fill.order_id.split(":")[0]


def test_backtest_cost_sensitivity_and_position_invariants() -> None:
    base = BacktestConfig()
    no_cost = run_backtest(BacktestConfig(fee_usd=Decimal("0"), slippage_bps=Decimal("0")))
    regular = run_backtest(base)
    # This synthetic deterministic fixture has low overnight gap and fixed trades;
    # cost-free reference should not be worse than cost-inclusive.
    assert Decimal(no_cost.metrics["ending_nav_usd"]) >= Decimal(
        regular.metrics["ending_nav_usd"]
    )
    assert Decimal(regular.metrics["fees_paid_usd"]) == (
        base.fee_usd * len(regular.fills)
    )


def test_reports_are_machine_readable_and_repeatable(tmp_path: Path) -> None:
    result = run_backtest(BacktestConfig(sessions=90))
    left = tmp_path / "one"
    right = tmp_path / "two"
    a = write_report(result, left)
    b = write_report(result, right)
    assert a == b
    assert a["data_manifest_id"] == DATASET_ID
    assert a["trading_mode"] == "simulation_only"
    assert a["status"].startswith("synthetic")
    for filename in ("metrics.json", "run-manifest.json", "trade-ledger.csv",
                     "equity-curve.csv", "rejections.csv"):
        assert (left / filename).read_bytes() == (right / filename).read_bytes()
    with (left / "equity-curve.csv").open(encoding="utf-8", newline="") as f:
        assert len(list(csv.DictReader(f))) == 90
    with (left / "trade-ledger.csv").open(encoding="utf-8", newline="") as f:
        assert len(list(csv.DictReader(f))) == len(result.fills)
    assert json.loads((left / "metrics.json").read_text()) == result.metrics


def test_cli_backtest_runs_and_invalid_config_exits_nonzero(tmp_path: Path, capsys) -> None:
    out = tmp_path / "report"
    assert main([
        "backtest", "--config", "examples/daily_equity_v1.json",
        "--output-dir", str(out),
    ]) == 0
    message = json.loads(capsys.readouterr().out)
    assert message["synthetic_only"] and not message["investment_validated"]
    assert (out / "run-manifest.json").exists()
    bad = tmp_path / "bad.json"
    bad.write_text('{"bad":true}', encoding="utf-8")
    assert main(["backtest", "--config", str(bad)]) == 1
    assert "schema mismatch" in capsys.readouterr().err


@pytest.mark.parametrize("kwargs", [
    {"sessions": 20},
    {"lookback_sessions": 500},
    {"top_n": 0},
    {"top_n": 4},
    {"initial_cash_usd": Decimal("0")},
    {"initial_cash_usd": Decimal("1000.001")},
    {"fee_usd": Decimal("-1")},
    {"fee_usd": Decimal("0.001")},
    {"slippage_bps": Decimal("20000")},
    {"max_single_weight": Decimal("1.1")},
    {"cash_buffer": Decimal("1")},
])
def test_invalid_backtest_configs_rejected(kwargs) -> None:
    with pytest.raises(ContractError):
        BacktestConfig(**kwargs)


def test_json_config_round_trip_and_strict_schema(tmp_path: Path) -> None:
    cfg = load_backtest_config(Path("examples/daily_equity_v1.json"))
    assert cfg == BacktestConfig()
    bad = cfg.as_dict()
    bad["unknown"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ContractError, match="schema mismatch"):
        load_backtest_config(path)
    bad.pop("unknown")
    bad["fee_usd"] = 1.0
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ContractError, match="decimal string"):
        load_backtest_config(path)
    bad["fee_usd"] = "NaN"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ContractError, match="finite"):
        load_backtest_config(path)
    bad["fee_usd"] = "garbage"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ContractError, match="numeric"):
        load_backtest_config(path)


def test_synthetic_data_count_and_order_are_deterministic() -> None:
    left = synthetic_equities(60)
    assert left == synthetic_equities(60)
    assert len(left) == 180
    assert [bar.instrument_id for bar in left[:3]] == ["SYNTH-A", "SYNTH-B", "SYNTH-C"]
    assert len(set((bar.instrument_id, bar.session_date) for bar in left)) == len(left)
    with pytest.raises(ContractError):
        synthetic_equities(20)


def test_drawdown_manual_baseline_and_error_cases() -> None:
    points = (
        NavPoint("a", Decimal("100")),
        NavPoint("b", Decimal("120")),
        NavPoint("c", Decimal("90")),
        NavPoint("d", Decimal("105")),
    )
    summary = evaluate_nav(points)
    assert summary["net_total_return_pct"] == "5.0000"
    assert summary["max_drawdown_pct"] == "25.0000"
    with pytest.raises(ValueError):
        evaluate_nav(())
    with pytest.raises(ValueError):
        evaluate_nav((NavPoint("x", Decimal("0")),))
    with pytest.raises(ValueError):
        evaluate_nav((NavPoint("a", Decimal("100")), NavPoint("b", Decimal("-1"))))
