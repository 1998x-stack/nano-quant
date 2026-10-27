# nano-quant

**A modular, testable, reproducible quantitative-finance research framework.**

> **Status: Phase E technical release-candidate checks (pre-v1.0, unreleased).** The eight-domain synthetic framework, point-in-time data controls and research diagnostics have automated replay and source/wheel consistency checks. **No official version tag, live trading, independent code approval, or real-market predictive validity is claimed.**

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

# Phase E source replay gate (candidate checks, not publication)
python -m nano_quant.cli backtest --config examples/daily_equity_v1.json --output-dir reports/release/first
python -m nano_quant.cli backtest --config examples/daily_equity_v1.json --output-dir reports/release/second
python tools/release_gate.py \
    --first reports/release/first \
    --second reports/release/second \
    --audit reports/validation/audit.json \
    --revision "$(git rev-parse HEAD)" \
    --output reports/release/evidence.json
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
- [Phase E candidate checks and limits](docs/releases/phase-e-report.md)
- [Release checklist and reviewer gates](docs/releases/release-checklist.md)
- [Development change log](CHANGELOG.md)
- [Independent acceptance test matrix](docs/validation/acceptance.md)
- [v1.0 release plan](docs/releases/v1.0-plan.md)
- [Branch and release rules](docs/governance/branching-and-releases.md)

## Development workflow

The stable integration branch is `main`. Phase B PR #2, Phase C PR #3, Phase D PR #4 and Phase E PR #5 form a **stacked review chain**. Merge and retarget in order, rerunning required CI before each change enters `main`. This technical evidence is **not** an approval to publish a version tag.

## License

No public software license has been selected by the repository owner. Public visibility alone does not confer a general reuse license.
