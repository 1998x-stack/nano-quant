"""Release checks must detect drift, misreported results and false claims."""

import json
from pathlib import Path

import pytest

from nano_quant.backtest import run_backtest, write_report
from nano_quant.core.backtest_config import BacktestConfig
from nano_quant.validation.audit import write_validation_audit
from tools.release_gate import GateError, verify_candidate


@pytest.fixture
def candidate(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    first, second = tmp_path / "first", tmp_path / "second"
    config = BacktestConfig(sessions=90)
    result = run_backtest(config)
    write_report(result, first)
    write_report(result, second)
    audit = tmp_path / "audit.json"
    write_validation_audit(config, audit)
    manifest = json.loads((first / "run-manifest.json").read_text(encoding="utf-8"))
    return first, second, audit, manifest["code_revision"]


def test_technical_candidate_repeats_and_reconciles(candidate) -> None:
    first, second, audit, sha = candidate
    report = verify_candidate(first, second, audit, expected_revision=sha)
    assert report["verdict"] == "TECHNICAL_CANDIDATE_CHECKS_PASS"
    assert report["released"] is False
    assert report["human_review_complete"] is False
    assert report["real_market_strategy_validated"] is False
    assert len(report["repeated_research_artifact_sha256"]) == 5


def test_drift_between_repeated_runs_is_rejected(candidate) -> None:
    first, second, audit, sha = candidate
    path = second / "metrics.json"
    metrics = json.loads(path.read_text(encoding="utf-8"))
    metrics["trades"] += 1
    path.write_text(json.dumps(metrics), encoding="utf-8")
    with pytest.raises(GateError, match="trade count|repeat-run drift"):
        verify_candidate(first, second, audit, expected_revision=sha)


def test_false_source_identity_is_rejected(candidate) -> None:
    first, second, audit, sha = candidate
    with pytest.raises(GateError, match="revision"):
        verify_candidate(first, second, audit, expected_revision="f" * 40)
    with pytest.raises(GateError, match="invalid commit"):
        verify_candidate(first, second, audit, expected_revision="unavailable")


def test_forged_alpha_claim_is_rejected(candidate) -> None:
    first, second, audit, sha = candidate
    content = json.loads(audit.read_text(encoding="utf-8"))
    content["out_of_sample_model_results"] = True
    audit.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(GateError, match="held-out"):
        verify_candidate(first, second, audit, expected_revision=sha)


def test_cross_file_financial_inconsistency_is_rejected(candidate) -> None:
    first, second, audit, sha = candidate
    for directory in (first, second):
        path = directory / "metrics.json"
        content = json.loads(path.read_text(encoding="utf-8"))
        content["ending_nav_usd"] = "999999.00"
        path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(GateError, match="ending NAV"):
        verify_candidate(first, second, audit, expected_revision=sha)


def test_fee_or_trade_ledger_tamper_is_rejected(candidate) -> None:
    first, second, audit, sha = candidate
    for directory in (first, second):
        path = directory / "trade-ledger.csv"
        data = path.read_text(encoding="utf-8").replace(",1.00,", ",200.00,")
        path.write_text(data, encoding="utf-8")
    with pytest.raises(GateError, match="fees do not reconcile"):
        verify_candidate(first, second, audit, expected_revision=sha)


def test_distribution_requirements(candidate, tmp_path: Path) -> None:
    first, second, audit, sha = candidate
    empty = tmp_path / "dist"
    empty.mkdir()
    with pytest.raises(GateError, match="one wheel"):
        verify_candidate(first, second, audit, expected_revision=sha, dist_dir=empty)


def test_wheel_financial_outputs_must_match_source(candidate, tmp_path: Path) -> None:
    first, second, audit, sha = candidate
    wheel_dir = tmp_path / "wheel-output"
    wheel_dir.mkdir()
    import shutil

    for file in first.iterdir():
        shutil.copy2(file, wheel_dir / file.name)
    report = verify_candidate(first, second, audit, expected_revision=sha, wheel_run=wheel_dir)
    assert report["verdict"] == "TECHNICAL_CANDIDATE_CHECKS_PASS"
    with (wheel_dir / "equity-curve.csv").open("a", encoding="utf-8") as stream:
        stream.write("extra,row\n")
    with pytest.raises(GateError, match="wheel behavior"):
        verify_candidate(first, second, audit, expected_revision=sha, wheel_run=wheel_dir)
