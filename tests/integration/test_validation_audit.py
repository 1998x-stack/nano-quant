"""The validation CLI cannot silently turn a diagnostic into an alpha claim."""

import json
from decimal import Decimal
from pathlib import Path

from nano_quant.cli import main
from nano_quant.core.backtest_config import BacktestConfig
from nano_quant.validation.audit import validation_audit, write_validation_audit


def test_audit_produces_reproducible_comparison_and_split_plan() -> None:
    config = BacktestConfig(sessions=90)
    result = validation_audit(config)
    assert result == validation_audit(config)
    assert result["phase"] == "D"
    assert result["trained_model"] is False
    assert result["out_of_sample_model_results"] is False
    assert len(result["walk_forward_protocol_only"]) >= 1
    comparison = result["cost_sensitivity"]
    assert comparison["comparison"] in (
        "PASS", "INCOMPARABLE_DIFFERENT_TRADE_PATH",
    )
    assert Decimal(comparison["fee_increment_usd_per_fill"]) > 0
    assert "not-confirmatory" in result["negative_control_method"]


def test_audit_file_is_byte_identical_for_same_config_and_revision(
    tmp_path: Path,
) -> None:
    cfg = BacktestConfig(sessions=90)
    a = tmp_path / "first.json"
    b = tmp_path / "second.json"
    assert write_validation_audit(cfg, a) == write_validation_audit(cfg, b)
    assert a.read_bytes() == b.read_bytes()
    assert json.loads(a.read_text(encoding="utf-8"))["phase"] == "D"


def test_validation_cli_prints_result_and_creates_json(tmp_path: Path, capsys) -> None:
    report = tmp_path / "audit.json"
    result = main([
        "validate", "--config", "examples/daily_equity_v1.json",
        "--output", str(report),
    ])
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["phase"] == "D"
    assert payload["validation_output"] == str(report)
    assert report.exists()
    artifact = json.loads(report.read_text(encoding="utf-8"))
    assert artifact["trained_model"] is False
