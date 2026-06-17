"""Streamlit startup — uses shared smoke module."""

import os
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))

DB_PATH = os.environ.get(
    "FXFILL_DUCKDB_PATH", str((PROJECT / "warehouse" / "fxfill.duckdb").resolve())
)


def test_real_streamlit_startup():
    if not Path(DB_PATH).exists():
        pytest.fail(f"Database not found: {DB_PATH}. Set FXFILL_DUCKDB_PATH or build warehouse.")

    from fxfill_analytics.verification.streamlit_smoke import run_streamlit_smoke

    result = run_streamlit_smoke(DB_PATH)

    assert result["health_http_status"] == 200, f"Health: {result.get('health_http_status')}"
    assert result["home_http_status"] == 200, f"Home: {result.get('home_http_status')}"
    assert (
        result["fatal_log_error_count"] == 0
    ), f"Fatal errors: {result.get('fatal_log_error_count')}"
    assert result["port_released"], "Port not released"
    assert result["startup_passed"], "Startup failed"
