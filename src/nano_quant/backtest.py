"""Synthetic monthly ranking backtest: full eight-domain research flow.

All factor inputs are cut off at the current session close. Pending orders
from that decision are first eligible at the next synthetic trading session
OPEN. Fills and cash are updated before that day's CLOSE mark is available.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from nano_quant import __version__
from nano_quant.core import ContractError, Fill, OrderIntent, RiskDecision
from nano_quant.core.backtest_config import BacktestConfig
from nano_quant.data import build_snapshot
from nano_quant.data.evidence import CorporateAction, reject_unsupported_actions
from nano_quant.data.synthetic import DATASET_ID, INSTRUMENTS, synthetic_equities
from nano_quant.evaluation.performance import NavPoint, evaluate_nav
from nano_quant.execution.account import SimulatedAccount
from nano_quant.models.baseline import baseline_rank_forecast
from nano_quant.portfolio.allocator import equal_weight_target, plan_orders
from nano_quant.research.momentum import momentum_factor
from nano_quant.risk.policy import review_orders
from nano_quant.strategies.ranking import select_top_n

ONE_MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class BacktestResult:
    config: BacktestConfig
    nav_points: tuple[NavPoint, ...]
    fills: tuple[Fill, ...]
    rejections: tuple[tuple[str, str], ...]
    metrics: dict[str, str | int]
    dataset_hash: str
    run_id: str
    decisions: int
    signals_generated: int


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def run_backtest(
    config: BacktestConfig, *, corporate_actions: tuple[CorporateAction, ...] = ()
) -> BacktestResult:
    """Run an explicitly synthetic, no-fitting, next-open simulation.

    Any supplied corporate action in the simulated interval is rejected until
    accounting support exists; no silent real-market cash-flow omission.
    """
    all_bars = synthetic_equities(config.sessions)
    reject_unsupported_actions(
        corporate_actions,
        first_session=all_bars[0].session_date,
        last_session=all_bars[-1].session_date,
    )
    rows_by_day: dict[str, dict[str, Any]] = {}
    for bar in all_bars:
        rows_by_day.setdefault(bar.session_date.isoformat(), {})[bar.instrument_id] = bar
    days = sorted(rows_by_day)
    dataset_hash = hashlib.sha256(
        _canonical([
            [bar.instrument_id, bar.session_date.isoformat(),
             str(bar.open), str(bar.high), str(bar.low), str(bar.close),
             bar.volume, bar.available_at.isoformat()]
            for bar in all_bars
        ]).encode("utf-8")
    ).hexdigest()
    config_hash = hashlib.sha256(_canonical(config.as_dict()).encode("utf-8")).hexdigest()
    run_id = hashlib.sha256(
        f"{__version__}:{_source_revision()}:{dataset_hash}:{config_hash}".encode("utf-8")
    ).hexdigest()[:16]

    account = SimulatedAccount(config.initial_cash_usd)
    equity: list[NavPoint] = []
    rejections: list[tuple[str, str]] = []
    pending: tuple[tuple[OrderIntent, RiskDecision], ...] = ()
    decisions = 0
    signals_generated = 0

    for idx, session in enumerate(days):
        today = rows_by_day[session]
        if pending:
            for order, approval in sorted(
                pending, key=lambda pair: (pair[0].side.value == "BUY", pair[0].instrument_id)
            ):
                if not approval.approved:
                    rejections.append((order.order_id, ",".join(approval.reason_codes)))
                    continue
                try:
                    account.execute_at_open(
                        order, approval, today[order.instrument_id],
                        fee=config.fee_usd, slippage_bps=config.slippage_bps,
                    )
                except ContractError as exc:
                    rejections.append((order.order_id, str(exc)))
            pending = ()

        latest_at = max(bar.available_at for bar in today.values())
        state = account.mark_to_close(today, at=latest_at)
        equity.append(NavPoint(session_date=session, nav=state.nav))

        # Trading calendar knowledge (session labels) is not future price information.
        is_month_end_session = (
            idx + 1 < len(days)
            and session[:7] != days[idx + 1][:7]
        )
        if not is_month_end_session or idx < config.lookback_sessions:
            continue

        as_of = latest_at + ONE_MINUTE
        snapshot = build_snapshot(
            all_bars, as_of=as_of, universe=INSTRUMENTS,
            calendar_id="SYNTHETIC-WEEKDAYS-UTC",
            data_manifest_id=DATASET_ID,
        )
        factors = momentum_factor(snapshot, config.lookback_sessions)
        forecast = baseline_rank_forecast(factors)
        signals = select_top_n(forecast, config.top_n)
        signals_generated += len(signals)
        target = equal_weight_target(
            signals, as_of=as_of, max_single_weight=config.max_single_weight,
            cash_buffer=config.cash_buffer,
        )
        next_open = min(
            bar.open_at for bar in rows_by_day[days[idx + 1]].values()
        )
        raw_closes = {instrument: bar.close for instrument, bar in today.items()}
        proposed = plan_orders(target, state, raw_closes, next_open)
        approvals = review_orders(
            target, proposed, state, max_single_weight=config.max_single_weight,
            allowed_instruments=INSTRUMENTS,
        )
        decisions += len(approvals)
        pending = tuple(zip(proposed, approvals))

    # The last scheduled session cannot create an unexecutable pending order.
    metrics = evaluate_nav(tuple(equity))
    metrics["trades"] = len(account.fills)
    metrics["fees_paid_usd"] = str(
        sum((fill.fee for fill in account.fills), Decimal("0"))
    )
    metrics["rejected_orders"] = len(rejections)
    return BacktestResult(
        config=config,
        nav_points=tuple(equity),
        fills=tuple(account.fills),
        rejections=tuple(rejections),
        metrics=metrics,
        dataset_hash=dataset_hash,
        run_id=run_id,
        decisions=decisions,
        signals_generated=signals_generated,
    )


def _source_revision() -> str:
    # Attribute Git HEAD only to this checked-out project's root, not an
    # unrelated repository from which the installed command was invoked.
    root = Path(__file__).resolve().parents[2]
    if not (root / ".git").exists():
        return "unavailable"
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return r.stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return "unavailable"


def write_report(result: BacktestResult, directory: Path) -> dict[str, object]:
    """Export canonical JSON and CSV artifacts; never source market data externally."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "phase": "C",
        "status": "synthetic-research-baseline-not-investment-validated",
        "run_id": result.run_id,
        "package_version": __version__,
        "code_revision": _source_revision(),
        "data_manifest_id": DATASET_ID,
        "dataset_sha256": result.dataset_hash,
        "config": result.config.as_dict(),
        "python": sys.version.split()[0],
        "event_policy": "T close signal, T+1 synthetic UTC open fill, T+1 close mark",
        "model": "deterministic_momentum_score_without_fitting",
        "calendar": "synthetic weekdays, ignores holidays and DST",
        "corporate_actions": "none",
        "trading_mode": "simulation_only",
        "decisions_reviewed": result.decisions,
        "signals_generated": result.signals_generated,
    }
    (directory / "run-manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (directory / "metrics.json").write_text(
        json.dumps(result.metrics, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    with (directory / "equity-curve.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["session_date", "nav_usd"])
        writer.writerows((point.session_date, str(point.nav)) for point in result.nav_points)
    with (directory / "trade-ledger.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow([
            "fill_id", "order_id", "instrument", "side", "shares",
            "price_usd", "fee_usd", "filled_at_utc",
        ])
        writer.writerows(
            (
                fill.fill_id, fill.order_id, fill.instrument_id, fill.side.value,
                fill.quantity, str(fill.price), str(fill.fee), fill.filled_at.isoformat(),
            )
            for fill in result.fills
        )
    with (directory / "rejections.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["order_id", "reason"])
        writer.writerows(result.rejections)
    return manifest
