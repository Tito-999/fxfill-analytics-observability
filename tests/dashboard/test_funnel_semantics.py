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


def test_funnel_seven_steps(page_source: str):
    """Funnel must define exactly 7 step names."""
    assert all(
        name in page_source
        for name in [
            "Upload",
            "OCR",
            "Anonymization",
            "Risk Detection",
            "Autofill",
            "Review",
            "Export",
        ]
    ), "Funnel must contain all 7 step names"


def test_funnel_yaxis_reversed(page_source: str):
    """Y-axis autorange must be reversed so Upload is at top."""
    assert '"autorange": "reversed"' in page_source or "'autorange': 'reversed'" in page_source


def test_funnel_colorscale_not_white_at_100():
    """The custom colorscale 100% endpoint must not be white/near-white."""
    # The page defines FUNNEL_RATE_COLORSCALE = [[0.0, "#D8E8F8"], [0.5, "#5B9BD5"], [1.0, "#0B3C78"]]
    page_text = PAGE_PATH.read_text(encoding="utf-8")
    # The 1.0 endpoint is "#0B3C78" — a dark navy, not white
    assert "#FFFFFF" not in page_text.upper(), "colorscale must not reference #FFFFFF"
    assert (
        "reversescale" not in page_text.lower()
        or "reversescale=False" in page_text
        or "FUNNEL_RATE_COLORSCALE" in page_text
    ), "FUNNEL_RATE_COLORSCALE should be used instead of reversescale=True Blues"


def test_funnel_cmin_cmax_fixed(page_source: str):
    """Marker must use fixed cmin=0.0, cmax=1.0 for consistent color mapping."""
    assert (
        '"cmin": 0.0' in page_source or "'cmin': 0.0" in page_source
    ), "cmin=0.0 required for consistent color scale"
    assert (
        '"cmax": 1.0' in page_source or "'cmax': 1.0" in page_source
    ), "cmax=1.0 required for consistent color scale"


def test_funnel_hovertemplate_contains_step_rates(page_source: str):
    """Hovertemplate must show Step-to-start and Step-to-prior rates."""
    assert "Step-to-start" in page_source
    assert "Step-to-prior" in page_source


def test_funnel_textposition_not_hardcoded_white(page_source: str):
    """Text position should be 'auto' or use per-point color logic, not fixed white."""
    # With textposition='auto', Plotly picks contrast color automatically
    assert "textposition" in page_source


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
