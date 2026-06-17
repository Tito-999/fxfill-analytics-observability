"""Verify P01-P10 reconciliation report is complete and all-passing."""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
REC_PATH = PROJECT / "reports" / "phase2_reconciliation.json"


def test_reconciliation_file_exists():
    assert REC_PATH.exists(), "phase2_reconciliation.json missing"


def test_all_reconciliation_passed():
    with open(REC_PATH, encoding="utf-8") as f:
        data = json.load(f)
    recs = data.get("reconciliation", [])
    assert len(recs) == 11, f"Expected 11 checks, found {len(recs)}"
    for r in recs:
        assert r.get("passed"), f"{r.get('phenomenon_id')} {r.get('metric_name')} failed"
        # Some entries use diff/warehouse_value; check at least one numeric field exists
        has_value = r.get("warehouse_value") is not None or r.get("diff") is not None
        assert has_value, f"{r.get('phenomenon_id')} missing numeric value"
