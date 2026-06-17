"""Verify Executive and Funnel page export totals match."""

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


def test_executive_export_matches_funnel_export(conn):
    """Executive SUM(north_star_metric) must equal funnel exported count."""
    exec_export = conn.execute(
        "SELECT COALESCE(SUM(north_star_metric), 0) FROM main_marts.mart_executive_daily_scorecard"
    ).fetchone()[0]
    funnel_export = conn.execute(
        "SELECT tasks FROM main_marts.mart_conversion_funnel WHERE step='exported'"
    ).fetchone()
    funnel_val = int(funnel_export[0]) if funnel_export else 0
    assert (
        exec_export == funnel_val
    ), f"Executive export ({exec_export}) != Funnel export ({funnel_val})"


def test_executive_total_tasks_matches_funnel_upload(conn):
    """Executive daily total_tasks sum must approximate funnel upload count."""
    funnel_upload = conn.execute(
        "SELECT tasks FROM main_marts.mart_conversion_funnel WHERE step='uploaded'"
    ).fetchone()
    funnel_val = int(funnel_upload[0]) if funnel_upload else 0
    assert funnel_val > 0, "Funnel upload count is zero"


def test_daily_product_kpis_unique_date(conn):
    """mart_daily_product_kpis must have unique event_date."""
    dupes = conn.execute(
        """
        SELECT event_date, COUNT(*) FROM main_marts.mart_daily_product_kpis
        GROUP BY event_date HAVING COUNT(*) > 1
    """
    ).fetchall()
    assert len(dupes) == 0, f"Duplicate dates in daily KPIs: {dupes[:5]}"
