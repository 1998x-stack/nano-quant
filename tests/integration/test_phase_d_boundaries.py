"""Phase D rejects unhandled real-world events rather than hiding their effect."""

from datetime import date

import pytest

from nano_quant.backtest import run_backtest
from nano_quant.core import ContractError
from nano_quant.core.backtest_config import BacktestConfig
from nano_quant.data.evidence import CorporateAction


@pytest.mark.parametrize("kind", ["DIVIDEND", "SPLIT", "DELISTING"])
def test_backtest_fails_closed_on_in_range_corporate_action(kind: str) -> None:
    action = CorporateAction("SYNTH-A", date(2026, 2, 10), kind, "scenario")
    with pytest.raises(ContractError, match="UNSUPPORTED_CORPORATE_ACTION"):
        run_backtest(BacktestConfig(sessions=90), corporate_actions=(action,))


def test_out_of_range_action_does_not_modify_fictional_baseline() -> None:
    action = CorporateAction("SYNTH-A", date(2025, 12, 1), "SPLIT", "scenario")
    cfg = BacktestConfig(sessions=90)
    assert run_backtest(cfg, corporate_actions=(action,)) == run_backtest(cfg)
