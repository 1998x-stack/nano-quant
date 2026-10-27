# Release readiness — human review and artifact sign-off

**Current classification: unreleased synthetic engineering prototype.**

## Release taxonomy

- `main`: latest **reviewed integrated** state, not every unreviewed branch.
- `feature/phase-*`: transient, stacked PR work; merge in dependency order.
- `release/vX.Y`: optional release stabilization branch **after** PR integration.
- immutable `vX.Y.Z`: version tag only after versioned artifacts and review.
- `v1.0.0`: **NOT APPROVED**. Real-data/point-in-time/universe/company-action
  and honest scope conditions described in the research acceptance plan remain.

Current package metadata declares `0.1.0` in `pyproject.toml`. It is a development
version here until explicitly released. A future experimental `v0.1.0` may be
appropriate for the **synthetic-only** developer baseline after proper review;
do not label it institutional investment readiness.

## Required sequential integration

1. Review and merge [PR #2](https://github.com/1998x-stack/nano-quant/pull/2) (Phase B) into `main`.
2. Retarget [PR #3](https://github.com/1998x-stack/nano-quant/pull/3) (Phase C) to `main`; rerun CI; review the diff and merge only if approved.
3. Retarget [PR #4](https://github.com/1998x-stack/nano-quant/pull/4) (Phase D) to `main`; rerun CI; review and merge only if approved.
4. Retarget the Phase E PR to `main` after preceding integration; rerun unit, integration and release-readiness checks; request review and merge if approved.
5. Configure and verify `main` protection/rulesets: Pull Request requirement,
   human review policy, required status checks, prohibition of force pushes.
   Settings require authorized repository action; a documented policy **does not**
   mean the server enforces it.
6. Verify `main` HEAD in GitHub: exact commit, all required Actions results, no
   known blocking vulnerabilities/permissions issues.
7. Decide a software license and distribution policy with the owner. If no
   license is selected, do not imply third-party redistribution rights.
8. Run `Release readiness (no publication)` against the final eligible commit.
   Download and inspect the wheel, sdist, evidence JSON and dependent files.
9. Rebuild from the chosen exact revision and compare the *financial outputs*
   and hashes to the archived test evidence. State wheel/source revision
   limitations; we **do not** claim bit-for-bit deterministic package builds.
10. Write a version-specific release note that explicitly states synthetic
    data, no learned model, no real alpha evidence and no live trading.
11. Only after all gates and authorized sign-off: create an immutable version tag
    on the **exact approved main commit** and (optionally) a GitHub release with
    intended artifact files. Ensure package version matches intended tag.
12. Record tag SHA, CI URL, artifact hashes, signing/attestation status if used,
    release date and supported/unsupported features. Never silently retag.

## Automated gate versus human gate

| Automated checks | Separate mandatory human decisions |
| --- | --- |
| Unit, integration and coverage | Architectural/code review and approval |
| Ruff, mypy, Python compatibility | Scope and product risk acceptance |
| Source/wheel build and wheel smoke | License and redistribution permission |
| Replay equality and accounting | Approve precise public release version |
| Dataset/revision/hash provenance | Main branch/ruleset enforcement |
| Phase D negative control and cost comparison | Real market validation requirements if claiming v1.0 |

Technical PASS only means **candidate checks succeeded on a synthetic project**.
It never constitutes a release, evidence of investment returns, approval,
a compliant license, or human sign-off.

## Rollback

Never move an existing release tag. For an issue found after release, publish a
new patch version or explicitly retract the compromised artifact in the
release notes; preserve an audit trail and propagate appropriate fixes forward.
