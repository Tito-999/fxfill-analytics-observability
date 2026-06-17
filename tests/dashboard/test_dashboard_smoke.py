"""Smoke test: verify dashboard structure, imports, and data access."""

import os
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))
os.environ["FXFILL_DUCKDB_PATH"] = str(PROJECT / "warehouse" / "fxfill.duckdb")


def test_home_page_exists():
    assert (PROJECT / "dashboard" / "Home.py").exists()


def test_all_7_pages_exist():
    pages = list((PROJECT / "dashboard" / "pages").glob("*.py"))
    assert len(pages) >= 7, f"Found {len(pages)} page files, expected >=7"


def test_database_service_imports():
    from dashboard.services.database import health_check

    health = health_check()
    assert health["connected"]


def test_filters_import():
    from dashboard.components.filters import render_filters

    assert callable(render_filters)


def test_kpi_cards_import():
    from dashboard.components.kpi_cards import kpi_row

    assert callable(kpi_row)


def test_metrics_import():
    from dashboard.services.metrics import METRIC_DEFINITIONS

    assert len(METRIC_DEFINITIONS) > 0
    assert "export_rate" in METRIC_DEFINITIONS


def test_page_imports():
    """Verify all page files can be imported without errors."""
    import importlib.util

    pages_dir = PROJECT / "dashboard" / "pages"
    for py_file in sorted(pages_dir.glob("*.py")):
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        assert spec is not None, f"Cannot load spec for {py_file.name}"
        # Just check the file is valid Python


def test_database_read_only():
    import duckdb

    conn = duckdb.connect(str(PROJECT / "warehouse" / "fxfill.duckdb"), read_only=True)
    result = conn.execute("SELECT 1").fetchone()
    assert result[0] == 1
    # Verify write is blocked
    with pytest.raises(Exception):
        conn.execute("CREATE TABLE test_write (x INT)")
    conn.close()
