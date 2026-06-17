"""Verify warehouse manifest (via final audit) completeness."""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
MAN_PATH = PROJECT / "reports" / "phase2_warehouse_manifest.json"
AUDIT_PATH = PROJECT / "reports" / "phase2_final_audit.json"


def test_manifest_exists():
    assert MAN_PATH.exists()


def test_audit_manifest_contents():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    wh = data.get("warehouse", {})
    assert wh.get("dbt_model_count") == 37, f"Expected 37, got {wh.get('dbt_model_count')}"
    assert wh.get("raw_view_count") == 7
    assert wh.get("analytics_mart_count") == 18
    assert wh.get("singular_test_count") == 10
    assert wh.get("interview_query_count") == 20
    db_path = str(wh.get("database_relative_path", ""))
    assert "warehouse/fxfill.duckdb" in db_path
    assert "F:" not in db_path  # no absolute Windows paths
