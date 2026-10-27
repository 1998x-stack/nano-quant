"""Verify a *technical* synthetic release candidate; do not publish or tag.

Checks two full source-tree replays, data/source provenance, accounting
cross-checks, a Phase D diagnostic and (optionally) distribution hashes.
This does not establish real-market alpha, a security audit or review approval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence

RESULT_FILES = (
    "run-manifest.json",
    "metrics.json",
    "equity-curve.csv",
    "trade-ledger.csv",
    "rejections.csv",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


class GateError(ValueError):
    """Candidate evidence is missing, inconsistent or misleading."""


def _require(test: bool, reason: str) -> None:
    if not test:
        raise GateError(reason)


def _hash(path: Path) -> str:
    _require(path.is_file(), f"missing file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    _require(path.is_file(), f"missing JSON: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"invalid JSON: {path}") from exc
    _require(isinstance(value, dict), f"JSON root not an object: {path}")
    return value


def _csv(path: Path) -> list[dict[str, str]]:
    _require(path.is_file(), f"missing CSV: {path}")
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            _require(reader.fieldnames is not None, f"CSV header missing: {path}")
            rows = list(reader)
            _require(all(None not in row for row in rows), f"extra CSV columns: {path}")
            return rows
    except (OSError, csv.Error) as exc:
        raise GateError(f"invalid CSV: {path}") from exc


def _money(value: object, name: str) -> Decimal:
    try:
        _require(isinstance(value, str), f"{name} must be string")
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise GateError(f"invalid {name}") from exc
    _require(result.is_finite(), f"{name} is nonfinite")
    return result


def _run_id(manifest: dict[str, Any]) -> str:
    config = manifest["config"]
    serialized = json.dumps(
        config, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    config_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    message = (
        f"{manifest['package_version']}:{manifest['code_revision']}:"
        f"{manifest['dataset_sha256']}:{config_hash}"
    )
    return hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]


def _validate_run(run: Path, expected_revision: str) -> dict[str, Any]:
    manifest = _json(run / "run-manifest.json")
    metrics = _json(run / "metrics.json")

    _require(manifest.get("phase") == "C", "expected Phase C source simulation")
    _require(
        manifest.get("status") == "synthetic-research-baseline-not-investment-validated",
        "simulation limitations are missing",
    )
    _require(manifest.get("trading_mode") == "simulation_only", "not simulation-only")
    _require(
        manifest.get("model") == "deterministic_momentum_score_without_fitting",
        "unverified model changed",
    )
    _require(
        manifest.get("data_manifest_id") == "synthetic-equities-c-v1",
        "unapproved data source",
    )
    _require(
        manifest.get("code_revision") == expected_revision,
        "source revision does not match audited checkout",
    )
    digest = manifest.get("dataset_sha256")
    _require(isinstance(digest, str) and bool(SHA256_RE.fullmatch(digest)),
             "missing data content digest")
    config = manifest.get("config")
    _require(isinstance(config, dict) and config.get("schema_version") == 1,
             "unversioned configuration")
    _require(manifest.get("run_id") == _run_id(manifest), "run_id mismatch")

    nav = _csv(run / "equity-curve.csv")
    trades = _csv(run / "trade-ledger.csv")
    rejected = _csv(run / "rejections.csv")
    _require(len(nav) == config["sessions"] == metrics.get("sessions"),
             "NAV length does not match session count")
    _require(int(metrics.get("trades", -1)) == len(trades), "trade count inconsistent")
    _require(int(metrics.get("rejected_orders", -1)) == len(rejected),
             "rejection count inconsistent")
    _require(bool(nav), "empty NAV series")

    days = [r["session_date"] for r in nav]
    _require(days == sorted(set(days)), "NAV dates duplicated or unsorted")
    first = _money(nav[0]["nav_usd"], "opening NAV")
    last = _money(nav[-1]["nav_usd"], "ending NAV")
    _require(first > 0 and all(_money(r["nav_usd"], "NAV") > 0 for r in nav),
             "NAV must remain positive")
    _require(first == _money(metrics.get("initial_nav_usd"), "initial NAV"),
             "opening NAV differs from report")
    _require(last == _money(metrics.get("ending_nav_usd"), "final NAV"),
             "ending NAV differs from report")
    _require(first == _money(config["initial_cash_usd"], "initial_cash_usd"),
             "initial NAV differs from config")
    actual_return_pct = (last / first - 1) * 100
    reported_return = _money(metrics.get("net_total_return_pct"), "return")
    _require(abs(actual_return_pct - reported_return) <= Decimal("0.00005"),
             "return metric does not reconcile")

    fill_ids = [row["fill_id"] for row in trades]
    order_ids = [row["order_id"] for row in trades]
    _require(len(set(fill_ids)) == len(trades), "duplicate fill IDs")
    _require(len(set(order_ids)) == len(trades), "duplicate executed orders")
    _require(all(row["side"] in ("BUY", "SELL") for row in trades), "invalid trade side")
    _require(all(int(row["shares"]) > 0 for row in trades), "invalid share quantity")
    _require(all(_money(row["price_usd"], "fill price") > 0 for row in trades),
             "invalid fill price")
    fees = sum((_money(row["fee_usd"], "fee") for row in trades), Decimal("0"))
    _require(fees == _money(metrics.get("fees_paid_usd"), "reported fees"),
             "fees do not reconcile")
    _require(all(_money(row["fee_usd"], "fee") >= 0 for row in trades),
             "negative fees")
    _require(
        all(row["filled_at_utc"][:10] > row["order_id"][:10] for row in trades),
        "trade appears before or on signal session",
    )
    return {"manifest": manifest, "metrics": metrics, "trades": len(trades)}


def verify_candidate(
    first: Path,
    second: Path,
    audit_path: Path,
    *,
    expected_revision: str,
    dist_dir: Path | None = None,
    freeze_path: Path | None = None,
    wheel_run: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on false reproducibility, missing evidence or false alpha claim."""
    _require(bool(COMMIT_RE.fullmatch(expected_revision)), "invalid commit revision")
    a = _validate_run(first, expected_revision)
    _validate_run(second, expected_revision)
    file_hashes: dict[str, str] = {}
    for name in RESULT_FILES:
        digest = _hash(first / name)
        _require(digest == _hash(second / name), f"repeat-run drift: {name}")
        file_hashes[name] = digest

    audit = _json(audit_path)
    _require(audit.get("phase") == "D", "missing Phase D audit")
    _require(audit.get("trained_model") is False, "trained model claim not verified")
    _require(audit.get("out_of_sample_model_results") is False,
             "unverified held-out results claim")
    _require(
        audit.get("dataset_sha256") == a["manifest"]["dataset_sha256"],
        "audit used different data",
    )
    _require(audit.get("baseline_run_id") == a["manifest"]["run_id"],
             "audit used different code, configuration or run")
    _require(
        isinstance(audit.get("walk_forward_protocol_only"), list)
        and len(audit["walk_forward_protocol_only"]) > 0,
        "walk-forward protocol missing",
    )
    _require(
        "not-confirmatory" in str(audit.get("negative_control_method", "")),
        "misleading negative-control significance claim",
    )
    cost = audit.get("cost_sensitivity", {})
    _require(
        isinstance(cost, dict) and cost.get("same_order_path") is True
        and cost.get("comparison") == "PASS",
        "reference fee sensitivity is not demonstrably comparable and passing",
    )
    if wheel_run is not None:
        # Source checkout embeds its git revision in run_id; a standalone wheel
        # can lack .git. Compare financial outputs, not that run identifier.
        for name in RESULT_FILES[1:]:
            _require(_hash(first / name) == _hash(wheel_run / name),
                     f"wheel behavior differs: {name}")
        wheel_manifest = _json(wheel_run / "run-manifest.json")
        _require(wheel_manifest.get("dataset_sha256") ==
                 a["manifest"]["dataset_sha256"], "wheel data mismatch")
        _require(wheel_manifest.get("trading_mode") == "simulation_only",
                 "wheel is not simulation-only")

    distribution_hashes: dict[str, str] = {}
    if dist_dir is not None:
        dists = sorted(p for p in dist_dir.iterdir() if p.is_file())
        whls = [p for p in dists if p.name.endswith(".whl")]
        sdists = [p for p in dists if p.name.endswith(".tar.gz")]
        _require(len(whls) == 1 and len(sdists) == 1,
                 "need exactly one wheel and one source distribution")
        distribution_hashes = {p.name: _hash(p) for p in dists}
    freeze_sha = _hash(freeze_path) if freeze_path is not None else None
    return {
        "phase": "E",
        "verdict": "TECHNICAL_CANDIDATE_CHECKS_PASS",
        "released": False,
        "human_review_complete": False,
        "real_market_strategy_validated": False,
        "source_revision": expected_revision,
        "package_version": a["manifest"]["package_version"],
        "dataset_sha256": a["manifest"]["dataset_sha256"],
        "run_id": a["manifest"]["run_id"],
        "repeated_research_artifact_sha256": file_hashes,
        "validation_audit_sha256": _hash(audit_path),
        "build_artifact_sha256": distribution_hashes,
        "pip_freeze_sha256": freeze_sha,
        "financial_result": a["metrics"],
        "limitations": [
            "no real-market data or investment alpha validated",
            "no confirmation of human PR reviews, main integration, or branch protection",
            "distribution builds are hashed, not proven bit-for-bit reproducible",
            "wheel and source runs are compared economically; wheel Git provenance is external",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--dist-dir", type=Path)
    parser.add_argument("--freeze", type=Path)
    parser.add_argument("--wheel-run", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = verify_candidate(
            args.first, args.second, args.audit,
            expected_revision=args.revision, dist_dir=args.dist_dir,
            freeze_path=args.freeze, wheel_run=args.wheel_run,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "verdict": report["verdict"],
            "released": False,
            "source_revision": report["source_revision"],
            "output": str(args.output),
        }, sort_keys=True))
        return 0
    except (GateError, OSError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"RELEASE CANDIDATE GATE FAILED: {exc}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
