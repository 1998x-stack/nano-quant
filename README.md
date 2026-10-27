# nano-quant

**Modular and reproducible quantitative finance research framework.**

> **Status: Phase B engineering scaffold (pre-v1.0).** A tested synthetic-data harness exists. A full eight-module research backtest, real data ingestion, independent risk policy, and live brokerage integration do **not** yet exist.

## Quick start

Requires Python 3.11+.

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m mypy src/nano_quant
python -m pytest -q --cov=nano_quant --cov-report=term-missing --cov-fail-under=85
python -m nano_quant.cli smoke --config examples/phase_b_golden.json
# After installation, also available as:
nano-quant smoke --config examples/phase_b_golden.json
```

The **smoke** command uses fictional market data and an explicitly **mocked** risk approval. It checks a historical information cutoff, a single next-day-open BUY fill, and USD cash/share accounting. The independent Golden Ledger A expected values are: execution price $10.01, fee $1.00, remaining cash $898.90, 10 shares, close NAV $1008.90. These are software test values, **not real investment results**.

The full `backtest --config` CLI subcommand intentionally exits nonzero with "not implemented" until Phase C. Only the core contracts, synthetic data and minimal ledger are implemented; research/model/strategy/portfolio/evaluation packages are Phase C placeholders.

## Project documents

- [Architecture overview](docs/architecture/overview.md)
- [Core interface contracts](docs/architecture/contracts.md)
- [Point-in-time conventions](docs/architecture/temporal-data.md)
- [Phase B architecture decision](docs/architecture/adr/0002-phase-b-golden-scaffold.md)
- [Research evidence rules](docs/research/evidence-policy.md)
- [Git governance](docs/governance/branching-and-releases.md)
- [v1.0 rollout](docs/releases/v1.0-plan.md)
- [Objective acceptance tests](docs/validation/acceptance.md)
- [Phase B execution report](docs/PHASE-B-REPORT.md)

## Git workflow

Reviewed and tested changes merge into `main`. Short-lived `feature/*` / `module/*` branches isolate development; `release/vX.Y` stabilizes releases; immutable `vX.Y.Z` tags identify official releases.

## Licensing

The repository owner has **not selected a software license**. Public visibility alone does not grant reuse rights.
