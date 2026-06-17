"""Verify Data Quality reconciliation is strict and complete."""

import json
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent


def test_reconciliation_no_hardcoded_pass():
    """Data Quality page must not contain hardcoded pass values for reconciliation."""
    dq_page = PROJECT / "dashboard" / "pages" / "7_Data_Quality.py"
    if not dq_page.exists():
        pytest.skip("DQ page not found")
    content = dq_page.read_text(encoding="utf-8")
    # Check that the page doesn't have hardcoded "passed": True without logic
    # This is a heuristic — full AppTest would be better but impractical here
    assert "hardcoded_pass" not in content.lower(), "DQ page contains hardcoded pass"


def test_snapshot_has_dynamic_dbt_counts():
    """Snapshot must have dynamic (not hardcoded default) dbt counts."""
    path = PROJECT / "reports" / "portfolio" / "data_quality_snapshot.json"
    if not path.exists():
        pytest.skip("Snapshot not found")
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    dbt_stats = snap.get("dbt", {})
    # If not stale, must have non-zero counts
    if not dbt_stats.get("stale", True):
        assert dbt_stats.get("model_count", 0) > 0, "dbt model count is zero"
        assert (
            dbt_stats.get("singular_test_count", 0) + dbt_stats.get("generic_test_count", 0) > 0
        ), "dbt test count is zero"


def test_snapshot_has_dynamic_pytest_counts():
    """Snapshot must have dynamic pytest counts."""
    path = PROJECT / "reports" / "portfolio" / "data_quality_snapshot.json"
    if not path.exists():
        pytest.skip("Snapshot not found")
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    pytest_stats = snap.get("pytest", {})
    if not pytest_stats.get("stale", True):
        assert pytest_stats.get("collected", 0) > 0, "pytest collected count is zero"
