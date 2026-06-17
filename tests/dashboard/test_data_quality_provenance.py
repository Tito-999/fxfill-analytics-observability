"""Verify Data Quality page provenance integrity."""

import json
import os
from pathlib import Path

import duckdb
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
DB_PATH = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))


@pytest.fixture(scope="module")
def conn():
    if not Path(DB_PATH).exists():
        pytest.skip("Database not found")
    c = duckdb.connect(DB_PATH, read_only=True)
    yield c
    c.close()


def test_snapshot_exists():
    """Data quality snapshot must exist."""
    path = PROJECT / "reports" / "portfolio" / "data_quality_snapshot.json"
    assert path.exists(), "Missing data_quality_snapshot.json"


def test_snapshot_has_provenance():
    """Snapshot must contain provenance block."""
    path = PROJECT / "reports" / "portfolio" / "data_quality_snapshot.json"
    if not path.exists():
        pytest.skip("Snapshot not found")
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    assert "provenance" in snap, "Snapshot missing provenance"
    prov = snap["provenance"]
    assert prov.get("run_id"), "Provenance missing run_id"
    assert prov.get("database_fingerprint"), "Provenance missing database fingerprint"


def test_warehouse_has_source_run_id(conn):
    """Warehouse staging tables must contain _source_run_id."""
    result = conn.execute(
        "SELECT DISTINCT _source_run_id FROM main_staging.stg_product_events LIMIT 1"
    ).fetchone()
    assert result is not None and result[0] is not None, "Warehouse missing _source_run_id"


def test_raw_staging_consistent(conn):
    """Stage tables should have same row count as raw views for 1:1 tables."""
    for t in [
        "users",
        "documents",
        "sessions",
        "product_events",
        "agent_runs",
        "agent_spans",
        "experiment_assignments",
    ]:
        try:
            raw = conn.execute(f"SELECT COUNT(*) FROM raw.raw_{t}").fetchone()[0]
            stg = conn.execute(f"SELECT COUNT(*) FROM main_staging.stg_{t}").fetchone()[0]
            assert raw == stg, f"{t}: raw({raw}) != staging({stg})"
        except Exception as e:
            pytest.fail(f"{t}: {e}")
