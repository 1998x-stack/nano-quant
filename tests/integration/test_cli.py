"""Public CLI contract for Phase B golden smoke."""

import json
from pathlib import Path

from nano_quant.cli import main, smoke
from nano_quant.core.config import SmokeConfig


def test_smoke_matches_golden_values() -> None:
    out = smoke(SmokeConfig())
    assert out["phase"] == "B"
    assert out["available_bars_at_decision"] == 1
    assert out["risk_policy"] == "mock-risk-phase-b"
    assert out["research_validated"] is False
    assert out["nav_usd"] == "1008.90"
    assert out["cash_usd"] == "898.90"
    assert out["pnl_usd"] == "8.90"


def test_cli_smoke_is_deterministic(capsys: object) -> None:
    from _pytest.capture import CaptureFixture

    capture = capsys
    assert isinstance(capture, CaptureFixture)
    args = ["smoke", "--config", "examples/phase_b_golden.json"]
    assert main(args) == 0
    first = capture.readouterr().out
    assert main(args) == 0
    second = capture.readouterr().out
    assert first == second
    payload = json.loads(first)
    assert payload["position_shares"] == 10


def test_cli_backtest_explicitly_unavailable(capsys: object) -> None:
    from _pytest.capture import CaptureFixture

    capture = capsys
    assert isinstance(capture, CaptureFixture)
    assert main(["backtest", "--config", "examples/daily_equity_v1.yaml"]) == 2
    assert "not implemented" in capture.readouterr().err


def test_invalid_cli_config_is_nonzero(tmp_path: Path, capsys: object) -> None:
    from _pytest.capture import CaptureFixture

    capture = capsys
    assert isinstance(capture, CaptureFixture)
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version": 1}', encoding="utf-8")
    assert main(["smoke", "--config", str(path)]) == 1
    assert "rejected" in capture.readouterr().err
