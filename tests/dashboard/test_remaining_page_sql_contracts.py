"""SQL contract tests for Feature, Agent, A/B pages — reuse acceptance logic."""
import os, sys
from pathlib import Path
import pytest

PROJECT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT))

DB = os.environ.get("FXFILL_DUCKDB_PATH", str(PROJECT / "warehouse" / "fxfill.duckdb"))


def test_feature_adoption_contract():
    if not Path(DB).exists():
        pytest.skip("Database not found")
    from scripts.check_remaining_dashboard_pages import check_sql_contracts
    r = check_sql_contracts(DB)
    assert r["feature_adoption"]["passed"], f"Feature adoption: {r['feature_adoption']['failures']}"
    assert r["feature_adoption"]["row_count"] > 0


def test_feature_ttfu_contract():
    if not Path(DB).exists():
        pytest.skip("Database not found")
    from scripts.check_remaining_dashboard_pages import check_sql_contracts
    r = check_sql_contracts(DB)
    assert r["feature_ttfu"]["passed"]


def test_agent_observability_contract():
    if not Path(DB).exists():
        pytest.skip("Database not found")
    from scripts.check_remaining_dashboard_pages import check_sql_contracts
    r = check_sql_contracts(DB)
    assert r["agent_observability"]["passed"]


def test_ab_test_contract():
    if not Path(DB).exists():
        pytest.skip("Database not found")
    from scripts.check_remaining_dashboard_pages import check_sql_contracts
    r = check_sql_contracts(DB)
    assert r["ab_test"]["passed"]
    assert r["ab_test"]["row_count"] > 0
