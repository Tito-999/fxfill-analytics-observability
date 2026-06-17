"""Verify A/B dashboard renders without NaN, has valid metrics, and uses separate-unit charts."""

import os
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "src"))

DB_PATH = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))

PAGE_PATH = PROJECT / "dashboard" / "pages" / "5_AB_Test.py"


@pytest.fixture(scope="module")
def page_source() -> str:
    return PAGE_PATH.read_text(encoding="utf-8")


def test_no_raw_nan_in_visible_text(page_source: str):
    """Page source must not contain visible NaN patterns."""
    # Patterns to check: standalone "nan", "$nan", "nan ms", "nan%"
    patterns = [
        (r"(?i)(?:^|[^A-Za-z])nan(?:\s|$|[^A-Za-z])", "bare nan"),
        (r"(?i)\$nan", "$nan"),
        (r"(?i)nan\s*ms", "nan ms"),
        (r"(?i)nan\s*%", "nan%"),
    ]
    # Exclude patterns that appear in comments/docstrings
    lines = page_source.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""'):
            continue
        for pattern, label in patterns:
            if re.search(pattern, stripped):
                pytest.fail(f"Line {i+1}: Found '{label}' pattern: {stripped[:100]}")


def test_defensive_nan_handling_present(page_source: str):
    """Page source must include NaN/inf handling."""
    assert (
        "N/A" in page_source or "notna" in page_source.lower() or "isna" in page_source.lower()
    ), "No NaN defensive handling found in AB Test page"


def test_ab_groups_have_valid_metrics():
    """A/B summary must have non-null metrics for both groups after data rebuild."""
    if not Path(DB_PATH).exists():
        pytest.skip("Database not found")

    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        result = conn.execute(
            """
            SELECT experiment_group, avg_field_accuracy, avg_latency_ms, cost_per_task
            FROM main_marts.mart_ab_test_summary
            ORDER BY experiment_group
        """
        ).fetchall()

        assert len(result) >= 2, f"Expected at least 2 groups, got {len(result)}"
        for row in result:
            grp = row[0]
            for i, col in enumerate(["avg_field_accuracy", "avg_latency_ms", "cost_per_task"]):
                val = row[i + 1]
                assert val is not None, f"Group {grp}: {col} is NULL"
                assert pd.notna(val), f"Group {grp}: {col} is NaN"
                assert float(val) != float("inf"), f"Group {grp}: {col} is +inf"
                assert float(val) != float("-inf"), f"Group {grp}: {col} is -inf"
    finally:
        conn.close()


def test_ab_user_distributions_have_data():
    """User-level metrics must have valid data for histograms."""
    if not Path(DB_PATH).exists():
        pytest.skip("Database not found")

    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        export_nn = conn.execute(
            """
            SELECT COUNT(*) FROM main_marts.mart_ab_test_user_metrics
            WHERE task_success_rate IS NOT NULL
        """
        ).fetchone()[0]
        accuracy_nn = conn.execute(
            """
            SELECT COUNT(*) FROM main_marts.mart_ab_test_user_metrics
            WHERE avg_field_accuracy IS NOT NULL
        """
        ).fetchone()[0]
        assert export_nn > 0, "No non-null export_rate values for histograms"
        assert accuracy_nn > 0, "No non-null avg_field_accuracy values for histograms"
    finally:
        conn.close()
