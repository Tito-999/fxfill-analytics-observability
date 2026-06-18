"""Generate a runtime data quality snapshot from dbt/pytest artifacts and warehouse.

Usage:
    python scripts/generate_data_quality_snapshot.py \
        --input-run <run-dir> \
        --database <db-path> \
        --dbt-manifest <manifest.json> \
        --dbt-model-results <run_results_models.json> \
        --dbt-test-results <run_results_tests.json> \
        --pytest-junit <junit.xml> \
        --verified-code-commit <commit> \
        --output <snapshot.json>
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        sha.update(f.read(1_048_576))
    return sha.hexdigest()[:16]


def _connect(db_path: str):
    import duckdb

    return duckdb.connect(db_path, read_only=True)


def _get_provenance(run_dir: Path, db_path: str) -> dict:
    """Extract provenance from manifest and warehouse source metadata."""
    manifest_path = run_dir / "generation_manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

    db_fp = _hash_file(Path(db_path)) if Path(db_path).exists() else "missing"

    run_ids = set()
    config_hashes = set()
    tables = [
        "users",
        "documents",
        "sessions",
        "product_events",
        "agent_runs",
        "agent_spans",
        "experiment_assignments",
    ]
    try:
        conn = _connect(db_path)
        for t in tables:
            try:
                r = conn.execute(
                    f"SELECT DISTINCT _source_run_id, _source_config_hash FROM main_staging.stg_{t} LIMIT 1"
                ).fetchone()
                if r and r[0]:
                    run_ids.add(r[0])
                if r and r[1]:
                    config_hashes.add(r[1])
            except Exception:
                pass
        conn.close()
    except Exception:
        pass

    manifest_run_id = manifest.get("run_id", "")
    manifest_config_hash = manifest.get("config_hash", "")
    warehouse_run_id = list(run_ids)[0] if len(run_ids) == 1 else ""
    warehouse_config_hash = list(config_hashes)[0] if len(config_hashes) == 1 else ""

    provenance_matches = (
        manifest_run_id == warehouse_run_id
        and manifest_config_hash == warehouse_config_hash
        and len(run_ids) == 1
        and len(config_hashes) == 1
        and Path(db_path).exists()
    )

    return {
        "manifest_run_id": manifest_run_id,
        "manifest_config_hash": manifest_config_hash,
        "warehouse_source_run_id": warehouse_run_id,
        "warehouse_source_config_hash": warehouse_config_hash,
        "warehouse_run_ids_found": sorted(run_ids),
        "warehouse_config_hashes_found": sorted(config_hashes),
        "warehouse_source_consistent": len(run_ids) == 1 and len(config_hashes) == 1,
        "provenance_matches": provenance_matches,
        "size_profile": manifest.get("size", "unknown"),
        "seed": manifest.get("seed"),
        "database_path_relative": "warehouse/fxfill.duckdb",
        "database_fingerprint": db_fp,
        "generated_at_utc": manifest.get("start_time", ""),
    }


def _get_dbt_stats(
    model_manifest: str,
    model_results: str,
    test_manifest: str,
    test_results: str,
) -> dict:
    """Use the shared dbt artifact validator for consistent measurement."""
    from fxfill_analytics.verification.dbt_artifacts import validate_dbt_artifacts

    evidence = validate_dbt_artifacts(
        model_manifest_path=Path(model_manifest) if model_manifest else Path("/nonexistent_mm"),
        model_results_path=Path(model_results) if model_results else Path("/nonexistent_mr"),
        test_manifest_path=Path(test_manifest) if test_manifest else Path("/nonexistent_tm"),
        test_results_path=Path(test_results) if test_results else Path("/nonexistent_tr"),
    )
    return {
        "measurement_completed": evidence["measurement_completed"],
        "model_count": evidence["model_count"],
        "model_execution_count": evidence["model_execution_count"],
        "model_success_count": evidence["model_success_count"],
        "model_fail_count": evidence["model_fail_count"],
        "model_error_count": evidence["model_error_count"],
        "model_skip_count": evidence["model_skip_count"],
        "generic_test_count": evidence["generic_test_count"],
        "singular_test_count": evidence["singular_test_count"],
        "test_definition_count": evidence["test_definition_count"],
        "test_execution_count": evidence["test_execution_count"],
        "test_pass": evidence["test_pass"],
        "test_fail": evidence["test_fail"],
        "test_error": evidence["test_error"],
        "test_skip": evidence["test_skip"],
        "model_results_sha256": evidence["model_results_sha256"],
        "test_results_sha256": evidence["test_results_sha256"],
        "artifacts_paths_distinct": evidence["artifacts_paths_distinct"],
        "artifacts_hashes_distinct": evidence["artifacts_hashes_distinct"],
        "artifacts_semantically_distinct": evidence["artifacts_semantically_distinct"],
        "artifacts_separated": evidence["artifacts_separated"],
        "distinct_model_statuses": evidence["distinct_model_statuses"],
        "distinct_test_statuses": evidence["distinct_test_statuses"],
        "failures": evidence["failures"],
        "accepted": evidence["accepted"],
        "stale": False,
    }


def _get_pytest_stats(junit_path: str) -> dict:
    p = Path(junit_path)
    stats = {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "stale": False}
    if not p.exists():
        stats["stale"] = True
        return stats
    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(p)
        root = tree.getroot()
        for ts in root.iter("testsuite"):
            stats["collected"] += int(ts.get("tests", 0))
            stats["failed"] += int(ts.get("failures", 0))
            stats["errors"] += int(ts.get("errors", 0))
            stats["skipped"] += int(ts.get("skipped", 0))
        stats["passed"] = stats["collected"] - stats["failed"] - stats["errors"] - stats["skipped"]
    except Exception:
        stats["stale"] = True
    return stats


def _get_raw_staging_counts(conn) -> dict:
    tables = [
        "users",
        "documents",
        "sessions",
        "product_events",
        "agent_runs",
        "agent_spans",
        "experiment_assignments",
    ]
    results = {}
    for t in tables:
        try:
            raw_cnt = conn.execute(f"SELECT COUNT(*) FROM raw.raw_{t}").fetchone()[0]
        except Exception:
            raw_cnt = None
        try:
            stg_cnt = conn.execute(f"SELECT COUNT(*) FROM main_staging.stg_{t}").fetchone()[0]
        except Exception:
            stg_cnt = None
        results[t] = {
            "raw_rows": raw_cnt,
            "staging_rows": stg_cnt,
            "delta": (raw_cnt - stg_cnt) if raw_cnt is not None and stg_cnt is not None else None,
        }
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-run", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--dbt-model-manifest", default=None)
    p.add_argument("--dbt-model-results", default=None)
    p.add_argument("--dbt-test-manifest", default=None)
    p.add_argument("--dbt-test-results", default=None)
    p.add_argument("--pytest-junit", default=None)
    p.add_argument("--verified-code-commit", default=None)
    p.add_argument("--output", default="reports/portfolio/data_quality_snapshot.json")
    args = p.parse_args()

    run_dir = Path(args.input_run)
    db_path = args.database
    out_path = Path(args.output)

    if not run_dir.exists():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Validate verified-code-commit if provided
    vcc = args.verified_code_commit
    if vcc:
        r = subprocess.run(["git", "cat-file", "-e", vcc], cwd=str(PROJECT), capture_output=True)
        if r.returncode != 0:
            print(f"WARNING: verified-code-commit {vcc[:12]} not found in repo", file=sys.stderr)

    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(PROJECT)
    ).stdout.strip()

    print("Generating data quality snapshot...")
    provenance = _get_provenance(run_dir, db_path)

    dbt_stats = {"stale": True, "accepted": False}
    if args.dbt_model_manifest and args.dbt_model_results:
        dbt_stats = _get_dbt_stats(
            args.dbt_model_manifest,
            args.dbt_model_results,
            args.dbt_test_manifest or "",
            args.dbt_test_results or "",
        )

    pytest_stats = {"stale": True}
    if args.pytest_junit:
        pytest_stats = _get_pytest_stats(args.pytest_junit)

    raw_staging = {}
    if Path(db_path).exists():
        conn = _connect(db_path)
        raw_staging = _get_raw_staging_counts(conn)
        conn.close()

    snapshot = {
        "schema_version": "1.0.0",
        "git": {
            "verified_code_commit": vcc or current_head,
            "report_generation_commit": current_head,
        },
        "provenance": provenance,
        "dbt": dbt_stats,
        "pytest": pytest_stats,
        "raw_staging_reconciliation": raw_staging,
        "accepted": provenance["provenance_matches"]
        and dbt_stats.get("accepted", False)
        and not dbt_stats.get("stale", True)
        and not pytest_stats.get("stale", True),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)
    print(f"Snapshot written to {out_path}")


if __name__ == "__main__":
    main()
