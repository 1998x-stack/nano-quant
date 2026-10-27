"""Phase B smoke command. Full backtest is reserved for Phase C."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from nano_quant.core import ContractError, OrderIntent, PortfolioState, RiskDecision, Side
from nano_quant.core.config import SmokeConfig, load_smoke_config
from nano_quant.data import build_snapshot, golden_bars
from nano_quant.execution import SimulatedLedger


def smoke(config: SmokeConfig) -> dict[str, str | int | bool]:
    """Exercise PIT snapshot -> authorized synthetic fill -> ledger mark.

    This deliberately does not involve research, prediction or real orders.
    """
    today, tomorrow = golden_bars()
    decision_at = datetime(2026, 1, 5, 21, 2, tzinfo=timezone.utc)
    snapshot = build_snapshot(
        (today, tomorrow), as_of=decision_at, universe=("SYNTH-A",)
    )
    if snapshot.bars != (today,):
        raise ContractError("smoke snapshot unexpectedly used future market data")
    order = OrderIntent(
        order_id="phase-b-golden-buy",
        instrument_id="SYNTH-A",
        side=Side.BUY,
        quantity=config.quantity,
        created_at=decision_at,
        earliest_execution_at=tomorrow.open_at,
        reference_price_context="T close=10.00 USD, synthetic",
    )
    # Deliberately mocked approval: the actual risk gate is a Phase C task.
    approval = RiskDecision(
        as_of=decision_at,
        order_ids=(order.order_id,),
        approved=True,
        reason_codes=(),
        risk_policy_version="mock-risk-phase-b",
    )
    ledger = SimulatedLedger(
        PortfolioState(
            as_of=decision_at,
            cash=config.initial_cash,
            positions={},
            marks={},
        )
    )
    fill = ledger.execute_buy_at_next_open(
        order, approval, tomorrow, slippage_bps=config.slippage_bps, fee=config.fee
    )
    return {
        "phase": "B",
        "fixture": "synthetic-golden-v1",
        "research_validated": False,
        "risk_policy": "mock-risk-phase-b",
        "available_bars_at_decision": len(snapshot.bars),
        "fill_at": fill.filled_at.isoformat(),
        "fill_price": str(fill.price),
        "fee_usd": str(fill.fee),
        "cash_usd": str(ledger.state.cash),
        "position_shares": ledger.state.positions["SYNTH-A"],
        "nav_usd": str(ledger.state.nav),
        "initial_cash_usd": str(config.initial_cash),
        "pnl_usd": str(ledger.state.nav - config.initial_cash),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nano-quant")
    sub = parser.add_subparsers(dest="command", required=True)
    smoke_parser = sub.add_parser("smoke", help="Run Phase B golden ledger")
    smoke_parser.add_argument("--config", type=Path, default=None)
    backtest = sub.add_parser("backtest", help="Full backtest: Phase C only")
    backtest.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.command == "backtest":
        print("Full research backtest is not implemented (planned for Phase C).", file=sys.stderr)
        return 2
    try:
        config = load_smoke_config(args.config) if args.config else SmokeConfig()
        print(json.dumps(smoke(config), indent=2, sort_keys=True))
        return 0
    except (ContractError, OSError, ValueError) as exc:
        print(f"smoke rejected: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
