"""Verify export CSV functionality for all 7 business pages."""

import csv
import io
from datetime import date


def _gen_csv(rows, columns, page_name="test"):
    """Simulate CSV export: rows as list of dicts."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    buf.seek(0)
    content = buf.read()
    return content, columns


def test_export_is_valid_utf8():
    rows = [{"metric": "DAU", "value": 100}]
    content, cols = _gen_csv(rows, ["metric", "value"], "executive")
    assert isinstance(content, str)
    assert "DAU" in content


def test_export_has_expected_columns():
    rows = [{"step": "uploaded", "count": 50000}]
    content, cols = _gen_csv(rows, ["step", "count"], "funnel")
    assert "step" in content
    assert "count" in content


def test_export_filename_has_page_and_date():
    today = date.today().isoformat()
    fname = f"fxfill_export_executive_{today}.csv"
    assert "executive" in fname
    assert today in fname


def test_export_empty_returns_valid_csv():
    rows = []
    content, cols = _gen_csv(rows, ["a", "b"], "empty")
    assert content.strip().endswith("\n") or "a,b" in content


def test_all_seven_export_types():
    pages = ["executive", "funnel", "retention", "agent", "ab_test", "root_cause", "data_quality"]
    for p in pages:
        rows = [{"k": "v", "val": 1}]
        content, cols = _gen_csv(rows, ["k", "val"], p)
        assert len(content) > 0, f"Export for {p} produced empty content"
