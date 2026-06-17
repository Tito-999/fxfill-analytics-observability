"""Verify 20 SQL portfolio queries exist, compile, and return results."""

import glob
import os
from pathlib import Path

import duckdb
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
SQL_DIR = PROJECT / "sql" / "interview_queries"
DB = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))


def test_20_query_files_exist():
    files = sorted(glob.glob(str(SQL_DIR / "*.sql")))
    assert len(files) == 20, f"Expected 20 SQL files, found {len(files)}"


def test_no_placeholder_queries():
    for f in sorted(glob.glob(str(SQL_DIR / "*.sql"))):
        content = Path(f).read_text(encoding="utf-8")
        assert "SELECT 1" not in content.upper().replace(
            " ", ""
        ), f"{Path(f).name} contains SELECT 1 placeholder"


def test_all_queries_executable():
    if not Path(DB).exists():
        pytest.skip("DuckDB not built — run build_warehouse first")
    conn = duckdb.connect(DB, read_only=True)
    try:
        for f in sorted(glob.glob(str(SQL_DIR / "*.sql"))):
            sql = Path(f).read_text(encoding="utf-8")
            try:
                conn.execute(sql).fetchall()
            except Exception as e:
                pytest.fail(f"{Path(f).name}: {e}")
    finally:
        conn.close()
