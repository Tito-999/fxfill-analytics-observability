"""Verify all Agent page sections obey the date filter."""

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


def test_stage_performance_has_run_date(conn):
    """mart_agent_stage_performance must have run_date column."""
    cols = [
        r[0].lower()
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='mart_agent_stage_performance'"
        ).fetchall()
    ]
    assert "run_date" in cols, "Stage performance missing run_date column"


def test_error_root_cause_has_run_date(conn):
    """mart_error_root_cause must have run_date column."""
    cols = [
        r[0].lower()
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='mart_error_root_cause'"
        ).fetchall()
    ]
    assert "run_date" in cols, "Error root cause missing run_date column"


def test_model_version_comparison_has_run_date(conn):
    """mart_model_version_comparison must have run_date column."""
    cols = [
        r[0].lower()
        for r in conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='mart_model_version_comparison'"
        ).fetchall()
    ]
    assert "run_date" in cols, "Model version comparison missing run_date column"


def test_narrower_date_reduces_total_runs(conn):
    """A shorter date range must yield fewer total runs."""
    full = (
        conn.execute(
            "SELECT SUM(total_runs) FROM main_marts.mart_agent_daily_kpis WHERE run_date BETWEEN '2026-02-15' AND '2026-06-14'"
        ).fetchone()[0]
        or 0
    )
    narrow = (
        conn.execute(
            "SELECT SUM(total_runs) FROM main_marts.mart_agent_daily_kpis WHERE run_date BETWEEN '2026-03-01' AND '2026-03-07'"
        ).fetchone()[0]
        or 0
    )
    assert narrow < full, f"Narrow window ({narrow}) not < full ({full})"


def test_all_sections_within_date_range(conn):
    """All agent mart dates should be within the available date range."""
    max_date = conn.execute(
        "SELECT MAX(run_date) FROM main_marts.mart_agent_daily_kpis"
    ).fetchone()[0]
    min_date = conn.execute(
        "SELECT MIN(run_date) FROM main_marts.mart_agent_daily_kpis"
    ).fetchone()[0]
    assert max_date is not None and min_date is not None
    # Stage perf dates
    stage_min = conn.execute(
        "SELECT MIN(run_date) FROM main_marts.mart_agent_stage_performance"
    ).fetchone()[0]
    stage_max = conn.execute(
        "SELECT MAX(run_date) FROM main_marts.mart_agent_stage_performance"
    ).fetchone()[0]
    assert stage_min >= min_date, f"Stage min {stage_min} < KPI min {min_date}"
    assert stage_max <= max_date, f"Stage max {stage_max} > KPI max {max_date}"
