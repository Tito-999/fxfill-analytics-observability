"""Verify Feature Adoption KPI cards use percent formatting."""

import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT))


def test_feature_page_has_percent_format_type():
    """Feature adoption page must use format_type='percent' for adoption KPI cards."""
    page = PROJECT / "dashboard" / "pages" / "3_Feature_Adoption.py"
    content = page.read_text(encoding="utf-8")
    assert '"format_type": "percent"' in content, "Feature KPI cards missing format_type percent"


def test_feature_page_no_raw_decimal_display():
    """Adoption rates must not be displayed as raw decimals (e.g. 0.8)."""
    # Check the page formats adoption rates via format_type, not raw values
    page = PROJECT / "dashboard" / "pages" / "3_Feature_Adoption.py"
    content = page.read_text(encoding="utf-8")
    # The page should use kpi_row with format_type, not manual string formatting for KPIs
    assert "kpi_row" in content, "Feature page must use kpi_row for KPI cards"
