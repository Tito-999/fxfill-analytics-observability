"""Verify model inventory completeness."""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
INV_PATH = PROJECT / "reports" / "phase2_model_inventory.json"


def test_inventory_exists():
    assert INV_PATH.exists()


def test_inventory_counts():
    with open(INV_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("raw_count") == 7
    assert data.get("staging_count") == 7
    assert data.get("intermediate_count") == 12
    assert data.get("mart_count") == 18
    assert data.get("total") == 44
    inv = data.get("inventory", [])
    assert len(inv) == 44
    for obj in inv:
        assert obj.get("model_name"), f"Missing model_name in {obj}"
        assert obj.get("layer"), f"Missing layer in {obj}"
