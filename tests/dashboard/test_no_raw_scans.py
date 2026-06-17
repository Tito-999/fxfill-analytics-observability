"""Verify dashboard pages do not query raw schema."""

from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
PAGES_DIR = PROJECT / "dashboard" / "pages"

BUSINESS_PAGES = [
    "1_Executive_Overview.py",
    "2_Funnel_and_Retention.py",
    "3_Feature_Adoption.py",
    "4_Agent_Observability.py",
    "5_AB_Test.py",
    "6_Root_Cause_Analysis.py",
]

RAW_PATTERNS = ["raw.", "raw_", "read_parquet", "parquet_scan"]


def test_business_pages_exist():
    for fname in BUSINESS_PAGES:
        assert (PAGES_DIR / fname).exists(), f"Missing page: {fname}"


def test_no_business_page_scans_raw():
    violations = []
    for fname in BUSINESS_PAGES:
        path = PAGES_DIR / fname
        content = path.read_text(encoding="utf-8")
        for pattern in RAW_PATTERNS:
            if pattern in content:
                violations.append(f"{fname}: contains '{pattern}'")
    assert len(violations) == 0, f"Raw schema scan violations: {violations}"


def test_database_service_queries_use_staging_marts():
    """Verify database.py references staging/intermediate/marts, not raw directly."""
    db_path = PROJECT / "dashboard" / "services" / "database.py"
    content = db_path.read_text(encoding="utf-8")
    assert "main_staging" in content or "main_marts" in content or "main_intermediate" in content
