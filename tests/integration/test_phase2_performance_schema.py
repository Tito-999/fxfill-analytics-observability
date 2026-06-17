"""Verify performance report schema and values."""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent.parent
PERF_PATH = PROJECT / "reports" / "phase2_performance.json"


def test_performance_exists():
    assert PERF_PATH.exists()


def test_performance_fields_present():
    with open(PERF_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for key in [
        "total_build_duration_seconds",
        "database_size_mb",
        "dbt_run_duration_seconds",
        "dbt_test_duration_seconds",
    ]:
        assert key in data, f"Missing {key}"
        assert data[key] is not None
        assert isinstance(data[key], int | float), f"{key} not numeric"


def test_mart_benchmarks():
    with open(PERF_PATH, encoding="utf-8") as f:
        data = json.load(f)
    marts = data.get("mart_query_benchmarks", {})
    required = [
        "mart_executive_daily_scorecard",
        "mart_conversion_funnel",
        "mart_retention_cohort",
        "mart_agent_daily_kpis",
        "mart_ab_test_summary",
    ]
    for name in required:
        assert name in marts, f"Missing mart benchmark: {name}"
        b = marts[name]
        for k in ["cold_duration_ms", "warm_median_ms", "row_count", "passed_under_2000ms"]:
            assert k in b, f"Missing {k} in {name} benchmark"
