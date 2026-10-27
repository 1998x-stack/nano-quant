# nano-quant

**A modular, testable, reproducible quantitative-finance research framework.**

> **Status: Phase D independent-validation scaffold (pre-v1.0).** The eight-domain synthetic pipeline now includes point-in-time revision and historical-universe tests, order approval fingerprinting, unsupported corporate-action rejection, walk-forward split **protocols** and negative-control/cost diagnostics. No trained or empirically validated real-market model is claimed.

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

# Phase D research diagnostics (no training, no real-market alpha claim)
python -m nano_quant.cli validate \
    --config examples/daily_equity_v1.json \
    --output reports/validation/audit.json
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
- [Phase D validation APIs](docs/modules/phase-d-validation.md)
- [Phase D actual CI report](docs/PHASE-D-REPORT.md)
- [Real-data onboarding gates](docs/research/real-data-readiness.md)
- [Independent acceptance test matrix](docs/validation/acceptance.md)
- [v1.0 release plan](docs/releases/v1.0-plan.md)
- [Branch and release rules](docs/governance/branching-and-releases.md)

## Development workflow

The stable integration branch is `main`. PR #2 contains Phase B; **Phase C PR #3 is stacked on Phase B** and **Phase D PR #4 is stacked on Phase C**. Merge in sequence, retargeting and checking CI before each downstream PR reaches `main`. No `v1.0.0` tag is issued for the engineering baseline.

## License

No public software license has been selected by the repository owner. Public visibility alone does not confer a general reuse license.
