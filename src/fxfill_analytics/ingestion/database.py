"""
DuckDB database connection management and raw schema creation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import duckdb


def get_db_path(db_path: str | Path | None = None) -> Path:
    """Resolve DuckDB path from env or argument."""
    if db_path:
        path = Path(db_path)
    else:
        path = Path(os.environ.get("FXFILL_DUCKDB_PATH", "warehouse/fxfill.duckdb"))
    if not path.is_absolute():
        # Resolve relative to project root (3 levels up from this file)
        project_root = Path(__file__).resolve().parent.parent.parent
        path = project_root / path
    return path


def connect(db_path: str | Path | None = None) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection, ensuring the parent directory exists."""
    resolved = get_db_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(resolved))
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    return conn


def create_raw_schema(
    conn: duckdb.DuckDBPyConnection, run_dir: Path, source_run_id: str
) -> dict[str, int]:
    """
    Create raw schema views reading directly from Parquet files.

    Each raw table includes technical columns: _source_run_id,
    _source_config_hash, _loaded_at_utc, _source_file.

    Returns dict of table_name -> row_count.
    """
    config_hash = source_run_id.split("_")[-1] if "_" in source_run_id else source_run_id
    row_counts: dict[str, int] = {}

    conn.execute("CREATE SCHEMA IF NOT EXISTS raw")

    table_files = {
        "raw_users": "users.parquet",
        "raw_documents": "documents.parquet",
        "raw_sessions": "sessions.parquet",
        "raw_product_events": "product_events.parquet",
        "raw_agent_runs": "agent_runs.parquet",
        "raw_agent_spans": "agent_spans.parquet",
        "raw_experiment_assignments": "experiment_assignments.parquet",
    }

    for view_name, file_name in table_files.items():
        parquet_path = run_dir / file_name
        if not parquet_path.exists():
            raise FileNotFoundError(f"Required Parquet file missing: {parquet_path}")

        # Create view directly on Parquet
        escaped_path = str(parquet_path).replace("\\", "/")
        conn.execute(
            f"""
            CREATE OR REPLACE VIEW raw.{view_name} AS
            SELECT
                *,
                '{source_run_id}' AS _source_run_id,
                '{config_hash}' AS _source_config_hash,
                CURRENT_TIMESTAMP AS _loaded_at_utc,
                '{escaped_path}' AS _source_file
            FROM read_parquet('{escaped_path}')
        """
        )
        result = conn.execute(f"SELECT COUNT(*) FROM raw.{view_name}").fetchone()  # type: ignore[index]
        assert result is not None, f"COUNT query returned None for {view_name}"
        row_count: int = result[0]
        row_counts[table_files[view_name]] = row_count

    return row_counts


def verify_raw_layer(conn: duckdb.DuckDBPyConnection, manifest: dict[str, Any]) -> dict[str, Any]:
    """Verify raw layer integrity against generation manifest."""
    results: dict[str, Any] = {"tables": {}, "passed": True}

    manifest_tables = {t["name"]: t for t in manifest.get("tables", [])}
    raw_table_map = {
        "raw_users": "users",
        "raw_documents": "documents",
        "raw_sessions": "sessions",
        "raw_product_events": "product_events",
        "raw_agent_runs": "agent_runs",
        "raw_agent_spans": "agent_spans",
        "raw_experiment_assignments": "experiment_assignments",
    }

    pk_map = {
        "raw_users": "user_id",
        "raw_documents": "document_id",
        "raw_sessions": "session_id",
        "raw_product_events": "event_id",
        "raw_agent_runs": "agent_run_id",
        "raw_agent_spans": "span_id",
        "raw_experiment_assignments": "assignment_id",
    }

    for raw_name, manifest_name in raw_table_map.items():
        raw_res = conn.execute(f"SELECT COUNT(*) FROM raw.{raw_name}").fetchone()
        assert raw_res is not None
        raw_count = raw_res[0]
        manifest_info = manifest_tables.get(manifest_name, {})
        expected = manifest_info.get("actual_rows", 0)

        pk_col = pk_map[raw_name]
        pk_res = conn.execute(
            f'SELECT COUNT(*) FROM raw.{raw_name} WHERE "{pk_col}" IS NULL'
        ).fetchone()
        assert pk_res is not None
        pk_null = pk_res[0]

        table_ok = raw_count == expected and pk_null == 0
        results["tables"][raw_name] = {
            "raw_rows": raw_count,
            "manifest_rows": expected,
            "row_count_ok": raw_count == expected,
            "pk_null_count": pk_null,
            "pk_ok": pk_null == 0,
        }
        if not table_ok:
            results["passed"] = False

    return results
