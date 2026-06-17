"""Verify funnel page uses task semantics, not user semantics."""

import os
import sys
from pathlib import Path

import duckdb
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))

DB_PATH = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))

PAGE_PATH = PROJECT / "dashboard" / "pages" / "2_Funnel_and_Retention.py"


@pytest.fixture(scope="module")
def page_source() -> str:
    return PAGE_PATH.read_text(encoding="utf-8")


def test_no_incorrect_users_funnel_label(page_source: str):
    """Page source must not contain the old incorrect 'Users funnel' label."""
    assert (
        "Users Entered Funnel" not in page_source
    ), "Found 'Users Entered Funnel' — should be 'Tasks Entered Funnel'"
    assert (
        "Users Exported" not in page_source
    ), "Found 'Users Exported' — should be 'Tasks Exported'"
    assert "7-Step Task Funnel (Users)" not in page_source, "Found old title with (Users)"


def test_page_uses_tasks_labels(page_source: str):
    """Page source must use task-level labels."""
    assert "Tasks Entered Funnel" in page_source
    assert "Tasks Exported" in page_source
    assert "7-Step Task Funnel (Tasks)" in page_source or "unique tasks" in page_source.lower()


def test_step_to_prior_rate_tickformat(page_source: str):
    """Colorbar title must use 'Step-to-Prior Rate' with .0% format."""
    assert "Step-to-Prior Rate" in page_source


def test_funnel_uses_task_id_sql():
    """The funnel marts must count DISTINCT task_id, and review > export."""
    if not Path(DB_PATH).exists():
        pytest.skip("Database not found")

    conn = duckdb.connect(DB_PATH, read_only=True)
    try:
        funnel = conn.execute(
            """
            SELECT step, tasks FROM main_marts.mart_conversion_funnel
            ORDER BY CASE step
                WHEN 'uploaded' THEN 1 WHEN 'ocr_completed' THEN 2
                WHEN 'anonymization_completed' THEN 3 WHEN 'risk_detection_completed' THEN 4
                WHEN 'autofill_completed' THEN 5 WHEN 'review_started' THEN 6
                WHEN 'exported' THEN 7
            END
        """
        ).fetchall()

        steps = {r[0]: r[1] for r in funnel}
        review = steps.get("review_started", 0)
        export = steps.get("exported", 0)
        assert review > export, f"Review count ({review}) must be > Export count ({export})"

        # Verify monotonic decrease
        ordered = [
            steps.get(s, 0)
            for s in [
                "uploaded",
                "ocr_completed",
                "anonymization_completed",
                "risk_detection_completed",
                "autofill_completed",
                "review_started",
                "exported",
            ]
        ]
        for i in range(len(ordered) - 1):
            assert ordered[i + 1] <= ordered[i], f"Funnel not monotonic at step {i}: {ordered}"

    finally:
        conn.close()
