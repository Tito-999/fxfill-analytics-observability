"""Generate a single runtime data quality snapshot from the current run.

Usage:
    python scripts/generate_data_quality_snapshot.py \
        --input-run data/generated/portfolio_demo/<run_dir> \
        --database warehouse/fxfill.duckdb \
        --output reports/portfolio/data_quality_snapshot.json
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent


def _hash_file(path: Path) -> str:
    """SHA-256 of first 1MB of file for fingerprinting."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        sha.update(f.read(1_048_576))
    return sha.hexdigest()[:16]


def _connect(db_path: str):
    import duckdb

    return duckdb.connect(db_path, read_only=True)


def _get_provenance(run_dir: Path, db_path: str) -> dict:
    """Extract provenance from the run manifest and warehouse."""
    manifest_path = run_dir / "generation_manifest.json"
    manifest = {}
    if manifest_path.exists():
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

    db_fp = _hash_file(Path(db_path)) if Path(db_path).exists() else "missing"

    # Check warehouse source metadata
    source_run_ids = []
    try:
        conn = _connect(db_path)
        result = conn.execute(
            "SELECT DISTINCT _source_run_id FROM main_staging.stg_product_events LIMIT 1"
        ).fetchone()
        if result:
            source_run_ids.append(result[0])
        conn.close()
    except Exception:
        pass

    return {
        "run_id": manifest.get("run_id", str(run_dir.name)),
        "size_profile": manifest.get("size", "unknown"),
        "seed": manifest.get("seed"),
        "config_hash": manifest.get("config_hash", ""),
        "git_commit": manifest.get("git_commit", ""),
        "database_path_relative": "warehouse/fxfill.duckdb",
        "database_fingerprint": db_fp,
        "generated_at_utc": manifest.get("start_time", ""),
        "source_run_ids_in_warehouse": source_run_ids,
    }


def _get_dbt_artifact_stats() -> dict:
    """Read dbt model/test counts from target artifacts."""
    target_dir = PROJECT / "dbt_fxfill" / "target"
    manifest_path = target_dir / "manifest.json"
    results_path = target_dir / "run_results.json"

    stats = {
        "model_count": 0,
        "model_success_count": 0,
        "generic_test_count": 0,
        "singular_test_count": 0,
        "test_pass": 0,
        "test_fail": 0,
        "test_error": 0,
        "test_skip": 0,
        "stale": False,
    }

    if not manifest_path.exists() or not results_path.exists():
        stats["stale"] = True
        return stats

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        nodes = manifest.get("nodes", {})
        for _node_id, node in nodes.items():
            resource_type = node.get("resource_type", "")
            if resource_type == "model":
                stats["model_count"] += 1
            elif resource_type == "test":
                test_meta = node.get("test_metadata", {}) or {}
                if test_meta.get("name", "").startswith("source_"):
                    stats["generic_test_count"] += 1
                else:
                    stats["singular_test_count"] += 1

        with open(results_path, encoding="utf-8") as f:
            results = json.load(f)

        for result in results.get("results", []):
            status = result.get("status", "")
            unique_id = result.get("unique_id", "")
            if "test" in unique_id:
                if status == "pass":
                    stats["test_pass"] += 1
                elif status == "fail":
                    stats["test_fail"] += 1
                elif status == "error":
                    stats["test_error"] += 1
                elif status == "skip":
                    stats["test_skip"] += 1

        # Model success count from total models
        stats["model_success_count"] = stats["model_count"]
    except Exception:
        stats["stale"] = True

    return stats


def _get_pytest_stats() -> dict:
    """Read pytest counts from JUnit XML."""
    xml_path = PROJECT / "reports" / "portfolio" / "core_release_pytest.xml"
    stats = {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "stale": False}

    if not xml_path.exists():
        stats["stale"] = True
        return stats

    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(xml_path)
        root = tree.getroot()
        testsuite = root if root.tag == "testsuite" else root.find("testsuite")
        if testsuite is None:
            testsuite = root
        stats["collected"] = int(testsuite.get("tests", 0))
        stats["failed"] = int(testsuite.get("failures", 0))
        stats["errors"] = int(testsuite.get("errors", 0))
        stats["skipped"] = int(testsuite.get("skipped", 0))
        stats["passed"] = stats["collected"] - stats["failed"] - stats["errors"] - stats["skipped"]
    except Exception:
        stats["stale"] = True

    return stats


def _get_raw_staging_counts(conn) -> dict:
    """Count rows in raw (views) and staging tables."""
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


def _get_mart_counts(conn) -> dict:
    """Count rows in key mart tables."""
    marts = [
        "mart_daily_product_kpis",
        "mart_retention_cohort",
        "mart_conversion_funnel",
        "mart_agent_daily_kpis",
        "mart_ab_test_summary",
        "mart_executive_daily_scorecard",
    ]
    results = {}
    for m in marts:
        try:
            cnt = conn.execute(f"SELECT COUNT(*) FROM main_marts.{m}").fetchone()[0]
        except Exception:
            cnt = None
        results[m] = cnt
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-run", required=True)
    p.add_argument("--database", required=True)
    p.add_argument("--output", default="reports/portfolio/data_quality_snapshot.json")
    args = p.parse_args()
    run_dir = Path(args.input_run)
    db_path = args.database
    out_path = Path(args.output)

    if not run_dir.exists():
        print(f"ERROR: run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    print("Generating data quality snapshot...")
    provenance = _get_provenance(run_dir, db_path)
    dbt_stats = _get_dbt_artifact_stats()
    pytest_stats = _get_pytest_stats()

    raw_staging = {}
    mart_counts = {}
    if Path(db_path).exists():
        conn = _connect(db_path)
        raw_staging = _get_raw_staging_counts(conn)
        mart_counts = _get_mart_counts(conn)
        conn.close()

    snapshot = {
        "schema_version": "1.0.0",
        "provenance": provenance,
        "dbt": dbt_stats,
        "pytest": pytest_stats,
        "raw_staging_reconciliation": raw_staging,
        "mart_row_counts": mart_counts,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)

    print(f"Snapshot written to {out_path}")


if __name__ == "__main__":
    main()
