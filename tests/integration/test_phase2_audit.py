"""Verify Phase 2 final audit completeness and consistency."""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
AUDIT_PATH = PROJECT / "reports" / "phase2_final_audit.json"


def test_audit_exists():
    assert AUDIT_PATH.exists()


def test_audit_no_placeholders():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        text = f.read()
    assert "TBD" not in text, "Audit contains TBD"
    # Check for placeholder values (not column names like estimated_cost_usd)
    data = json.loads(text)
    audit_str = json.dumps(data)
    assert '"TBD"' not in audit_str, "Audit contains TBD value"
    assert "F:\\\\" not in text, "Audit contains Windows absolute path"


def test_audit_reconciliation():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    rec = data.get("reconciliation", {})
    assert rec.get("all_passed"), "Not all reconciliation passed"


def test_audit_inventory():
    with open(AUDIT_PATH, encoding="utf-8") as f:
        data = json.load(f)
    inv = data.get("inventory", {})
    assert inv.get("total") == 44
    assert inv.get("raw") == 7
    assert inv.get("marts") == 18
