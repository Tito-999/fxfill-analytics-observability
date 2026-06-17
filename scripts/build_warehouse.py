"""
CLI entry point for DuckDB + dbt warehouse build.

Usage:
    python scripts/build_warehouse.py --input-run data/generated/medium_in/run_* --database warehouse/fxfill.duckdb --full-refresh
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FxFill Analytics Warehouse")
    parser.add_argument("--input-run", type=str, required=True, help="Path to input run directory")
    parser.add_argument(
        "--database", type=str, default="warehouse/fxfill.duckdb", help="DuckDB path"
    )
    parser.add_argument("--full-refresh", action="store_true", help="Drop and rebuild")
    parser.add_argument("--skip-dbt", action="store_true", help="Skip dbt run/test")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root / "src"))

    run_dir = Path(args.input_run)
    if not run_dir.exists():
        print(f"ERROR: Input run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    db_path = Path(args.database)
    if not db_path.is_absolute():
        db_path = project_root / db_path

    started_at = datetime.now(UTC)

    # ── Step 1: Validate input ──
    print("[Phase 2A] Validating input data...")
    from fxfill_analytics.ingestion.contracts import (
        REQUIRED_MANIFEST_FILES,
        REQUIRED_TABLES,
        validate_contracts,
    )

    available_pq = {tbl: (run_dir / f"{tbl}.parquet").exists() for tbl in REQUIRED_TABLES}
    available_mf = {mf: (run_dir / mf).exists() for mf in REQUIRED_MANIFEST_FILES}

    errors = validate_contracts(available_pq, available_mf)
    if errors:
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    with open(run_dir / "generation_manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    source_run_id = manifest.get("run_id", run_dir.name)
    print(f"  Run ID: {source_run_id}")

    # ── Step 2: Create raw schema ──
    print("[Phase 2A] Creating raw schema...")
    from fxfill_analytics.ingestion.database import connect, create_raw_schema, verify_raw_layer

    if args.full_refresh and db_path.exists():
        db_path.unlink()

    conn = connect(db_path)
    row_counts = create_raw_schema(conn, run_dir, source_run_id)
    for fname, count in row_counts.items():
        print(f"  {fname}: {count:,} rows")

    # ── Step 3: Verify raw layer ──
    print("[Phase 2A] Verifying raw layer...")
    verify_results = verify_raw_layer(conn, manifest)
    status = "OK" if verify_results["passed"] else "DISCREPANCY"
    print(f"  Raw layer verification: {status}")

    finished_at = datetime.now(UTC)
    wh_manifest = {
        "input_run_id": source_run_id,
        "input_config_hash": manifest.get("config_hash", "unknown"),
        "database_path": str(db_path),
        "build_started_at": started_at.isoformat(),
        "build_finished_at": finished_at.isoformat(),
        "build_duration_seconds": (finished_at - started_at).total_seconds(),
        "raw_layer": {"tables": row_counts, "verification": verify_results},
        "dbt_status": "skipped" if args.skip_dbt else "pending",
        "git_commit": manifest.get("git_commit", "unknown"),
    }

    reports_dir = project_root / "reports"
    reports_dir.mkdir(exist_ok=True)
    with open(reports_dir / "phase2_warehouse_manifest.json", "w", encoding="utf-8") as f:
        json.dump(wh_manifest, f, indent=2, default=str, ensure_ascii=False)

    print(f"\n[Phase 2A] Complete! ({wh_manifest['build_duration_seconds']:.1f}s)")
    print(f"  Database: {db_path}")
    conn.close()


if __name__ == "__main__":
    main()
