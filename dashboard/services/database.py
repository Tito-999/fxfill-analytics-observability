"""DuckDB read-only connection service for Streamlit dashboard."""

import os
from pathlib import Path

import duckdb
import streamlit as st


@st.cache_resource(ttl=3600)
def get_connection() -> duckdb.DuckDBPyConnection:
    """Return a read-only DuckDB connection. Cached for 1 hour."""
    db_path = os.environ.get("FXFILL_DUCKDB_PATH", "warehouse/fxfill.duckdb")
    if not Path(db_path).is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        db_path = str(project_root / db_path)
    if not Path(db_path).exists():
        st.error(f"Database not found at: {db_path}")
        st.info(
            "Rebuild with: python scripts/build_warehouse.py --input-run data/generated/<run> --full-refresh"
        )
        st.stop()
    conn = duckdb.connect(db_path, read_only=True)
    return conn


@st.cache_data(ttl=600)
def run_query(query: str, params: dict | None = None) -> list:
    """Execute a read-only query with optional parameters. Cached 10min."""
    conn = get_connection()
    if params:
        for k, v in params.items():
            query = query.replace(f"{{{{{k}}}}}", str(v))
    return conn.execute(query).fetchall()


def get_min_max_dates():
    """Get the min and max event dates from the warehouse."""
    conn = get_connection()
    r = conn.execute(
        "SELECT MIN(event_date), MAX(event_date) FROM main_staging.stg_product_events"
    ).fetchone()
    return r[0], r[1] if r else (None, None)


def health_check() -> dict:
    """Verify database health and required schemas exist."""
    conn = get_connection()
    schemas = ["raw", "main_staging", "main_intermediate", "main_marts"]
    result = {"connected": True, "schemas": {}}
    for s in schemas:
        try:
            conn.execute(
                f"SELECT 1 FROM {s}.stg_users LIMIT 0"
                if s == "main_staging"
                else f"SELECT 1 FROM information_schema.schemata WHERE schema_name='{s}' LIMIT 0"
            )
            result["schemas"][s] = "ok"
        except Exception:
            result["schemas"][s] = "missing"
    return result
