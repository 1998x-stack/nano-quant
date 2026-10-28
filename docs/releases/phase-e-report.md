# Phase E — reproducible candidate build and release governance

Date: 2026-10-27. **Status: technical candidate checks PASS on code commit `c7048136`, but publication NOT authorized**.

## Actual verification runs

- [Standard CI](https://github.com/1998x-stack/nano-quant/actions/runs/40488518133) on commit `c7048136`: Python 3.11 and 3.12 installation, lint, mypy, unit/integration tests, Phase B/C/D regression commands all passed. **117 tests passed**, Python 3.11 line coverage **94.83%**.
- [Release readiness workflow](https://github.com/1998x-stack/nano-quant/actions/runs/40488518124) on the same commit: wheel and source distribution built; Twine metadata check; clean wheel virtual-environment backtest matched source's financial CSV/JSON outputs; two separate source-run output files were bit-for-bit equal; Phase D audit and finance reconciliations passed. Gate produced `TECHNICAL_CANDIDATE_CHECKS_PASS`, `released=false`.
- The workflow retains distributable files and evidence with short retention. It does **not** create a Git tag, GitHub release, publish a wheel externally, attest builds cryptographically, or approve research results.
- After later documentation commits, verify the **new branch HEAD's** CI results before merging; do not cite an earlier SHA as if it covered later source changes.

## Starting evidence

At the start of this stage:
- PR #2, #3, #4 were **Open**, with sequential bases `main` <- Phase B <- Phase C.
- The fetched review lists for all three PRs were empty.
- GitHub repository ruleset collection returned `[]`; branch protection detail
  could not be verified because the connector returned HTTP 403 (not accessible
  by integration). Do not claim that protections are installed.
- No GitHub releases were reported. We did **not** create any Git tag.

## Work added

1. `tools/release_gate.py` validates two independently generated source-run
   reports byte for byte, reconciles NAV, fees, trade count, and chronological
   trades, and checks code_revision/config/dataset/run_id agreement.
2. The candidate gate rejects unverified alpha/held-out-training claims and
   requires diagnostic control/cost check evidence from Phase D.
3. A separate workflow builds sdist and wheel, checks distribution metadata,
   installs the wheel into a clean Python venv, and compares the actual
   **financial outputs** with those of source replay.
4. A build-evidence JSON records artifact SHA256 digests, source revision,
   dataset SHA256 and hash of an environment package inventory; GitHub Actions
   stores candidate evidence for a limited retention period.
5. Negative tests attempt drift, tampered reported results, false provenance
   and fake research validation claims.
6. `CHANGELOG.md` and the human approval checklist establish a clear difference
   between engineering prerelease readiness and real-market v1.0 readiness.

## Repeatable commands (from repo root)

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m nano_quant.cli backtest --config examples/daily_equity_v1.json --output-dir reports/release/first
python -m nano_quant.cli backtest --config examples/daily_equity_v1.json --output-dir reports/release/second
python -m nano_quant.cli validate --config examples/daily_equity_v1.json --output reports/release/audit.json
python -m tools.release_gate \
  --first reports/release/first \
  --second reports/release/second \
  --audit reports/release/audit.json \
  --revision "$(git rev-parse HEAD)" \
  --output reports/release/evidence.json
```

The separate `Release readiness (no publication)` Actions job additionally
performs wheel/sdist builds and clean wheel comparison, then stores build
artifact hashes plus `pip freeze` fingerprint.

## Important limitations and blockers

- The version in source remains pre-v1.0 (`0.1.0`); no tag, GitHub release or
  package registry publication is performed in Phase E.
- No historical live-market first-party data/permissions, true corporate-action
  cash accounting or real out-of-sample predictive performance.
- Environment inventory hashes are **not** equivalent to a committed locked
  dependency solver or signed reproducible-build attestation.
- Wheel-run Git SHA can differ or be unavailable from a standalone wheel;
  the evidence ties distribution hashes to the CI source revision, and compares
  wheel economic output rather than incorrectly requiring identical run IDs.
- All previous PRs require independent review and orderly merge before any
  stable publication. The automated candidate manifest is not approval.
- Branch integration, reviewer approval, license choice and release authorization remain pending; the evidence above covers the stated code commit, not the final reviewed release.
