# nano-quant

**Modular quantitative finance research framework — architecture phase.**

Status: **Phase A — architecture review**. This repository does **not** yet contain an executable backtest, tested finance calculations, or a validated investment strategy.

## Vision

Make the path from historical data to research, models, strategies, portfolio weights, risk controls, simulated orders, and evaluation explicit, testable, time-consistent, and reproducible.

The v1.0 reference use case is daily, long-only, unlevered equities in USD with versioned synthetic fixtures. This is a software/research baseline—not a performance claim.

## Phase A design

- [System architecture (中文)](docs/architecture/overview.md)
- [Core interface contracts](docs/architecture/contracts.md)
- [Point-in-time and event-time rules](docs/architecture/temporal-data.md)
- [Architecture decision record](docs/architecture/adr/0001-modular-monolith.md)
- [Primary evidence and research protocol](docs/research/evidence-policy.md)
- [Branch, PR, release and tag governance](docs/governance/branching-and-releases.md)
- [v1.0 scope, backlog, v2.0 evolution](docs/releases/v1.0-plan.md)
- [Objective acceptance and golden tests](docs/validation/acceptance.md)
- [Phase A decision log / handoff](docs/PHASE-A-REPORT.md)

## Branch policy

`main` is the reviewed stable integration branch. Module work happens in temporary `module/*` branches; `release/vX.Y` branches stabilize releases; immutable version tags `vX.Y.Z` identify shipped snapshots. Do not treat branches as module storage.

## Next step

Phase B will create the installable Python package, skeleton modules, tests and CI. The commands and test cases in design documents are **specifications**, not claims of successful execution.

No live trading, leverage, broker integration, or investment advice is provided.
