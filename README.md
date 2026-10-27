# nano-quant

**A modular, testable, reproducible quantitative-finance research framework.**

> **Status: Phase C synthetic research baseline (pre-v1.0).** Phase B's Golden Ledger remains supported. This repository now runs a complete *synthetic-data* eight-domain research path, but does not yet meet all real-market or v1.0 release verification requirements. The untrained momentum rank score is not an empirically validated return forecast.

## Quick start

Requires Python 3.11+; no market data subscription or broker credentials.

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src/nano_quant
python -m pytest -q --cov=nano_quant --cov-report=term-missing --cov-fail-under=85

# Phase B golden ledger regression
python -m nano_quant.cli smoke --config examples/phase_b_golden.json

# Phase C full synthetic monthly momentum baseline
python -m nano_quant.cli backtest \
    --config examples/daily_equity_v1.json \
    --output-dir reports/daily_equity_v1
```

The backtest creates:
`run-manifest.json`, `metrics.json`, `equity-curve.csv`,
`trade-ledger.csv`, and `rejections.csv`.

The reference scenario: 120 **fictional weekday** sessions, three fictitious USD stocks, 20-session momentum, no-fitting ranking baseline, top two assets at calendar-month-end, capped equal weights and a cash buffer, independent basic risk approval, and **T close signal → next synthetic session open fill → close NAV**. Explicit commission and slippage apply. The synthetic venue uses fixed UTC times, not real-world holidays or DST.

**Not supported:** live trading, actual market data validation, corporate actions, shorting, leverage, complex intraday orders, trained predictive models, real-world alpha claims, or real-exchange execution. Public code availability is not permission to trade or advice to invest.

## Architecture and evidence

- [System architecture](docs/architecture/overview.md)
- [Actual Phase C module interfaces](docs/modules/phase-c-interfaces.md)
- [Point-in-time/temporal requirements](docs/architecture/temporal-data.md)
- [Phase C synthetic data manifest](docs/research/phase-c-synthetic-manifest.json)
- [Phase C implementation and verification report](docs/PHASE-C-REPORT.md)
- [Independent acceptance test matrix](docs/validation/acceptance.md)
- [v1.0 release plan](docs/releases/v1.0-plan.md)
- [Branch and release rules](docs/governance/branching-and-releases.md)

## Development workflow

The stable integration branch is `main`. PR #2 contains Phase B; **Phase C PR #3 is stacked on Phase B** until #2 has been reviewed and merged, after which PR #3 should be retargeted to `main` and CI rechecked. No `v1.0.0` tag is issued for the engineering baseline.

## License

No public software license has been selected by the repository owner. Public visibility alone does not confer a general reuse license.
