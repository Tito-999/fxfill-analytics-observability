"""Verify strict reconciliation: re-computed pass, hardcoded pass detection."""

from src.fxfill_analytics.quality.reconciliation import (
    evaluate_reconciliation_row,
    validate_reconciliation_rows,
)


def test_failed_within_tolerance():
    """source=1.0, warehouse=1.5, tolerance=0.1 with stored_passed=True must fail."""
    row = {
        "metric_id": "test_1",
        "metric_name": "Test Metric",
        "source_value": 1.0,
        "warehouse_value": 1.5,
        "tolerance": 0.1,
        "passed": True,
    }
    eval_row = evaluate_reconciliation_row(row)
    assert eval_row["recomputed_passed"] is False, f"Expected False, got {eval_row}"
    assert eval_row["pass_flag_matches"] is False
    assert eval_row["is_complete"] is True


def test_pass_within_tolerance():
    """source=1.0, warehouse=1.05, tolerance=0.1 must pass."""
    row = {
        "metric_id": "test_2",
        "metric_name": "OK Metric",
        "source_value": 1.0,
        "warehouse_value": 1.05,
        "tolerance": 0.1,
        "passed": True,
    }
    eval_row = evaluate_reconciliation_row(row)
    assert eval_row["recomputed_passed"] is True


def test_none_source_incomplete():
    """source=None must be incomplete."""
    row = {"metric_id": "t3", "source_value": None, "warehouse_value": 1.0, "tolerance": 0.1}
    eval_row = evaluate_reconciliation_row(row)
    assert eval_row["is_complete"] is False


def test_nan_tolerance_non_finite():
    """tolerance=NaN must be non-finite."""
    row = {
        "metric_id": "t4",
        "source_value": 1.0,
        "warehouse_value": 1.0,
        "tolerance": float("nan"),
    }
    eval_row = evaluate_reconciliation_row(row)
    assert eval_row["is_finite"] is False
    assert eval_row["recomputed_passed"] is False


def test_aggregate_validation_detects_failures():
    rows = [
        {
            "metric_id": "a",
            "source_value": 1.0,
            "warehouse_value": 1.0,
            "tolerance": 0.01,
            "passed": True,
        },
        {
            "metric_id": "b",
            "source_value": 1.0,
            "warehouse_value": 2.0,
            "tolerance": 0.01,
            "passed": True,
        },
    ]
    result = validate_reconciliation_rows(rows)
    assert result["row_count"] == 2
    assert result["incorrect_pass_flag_count"] == 1
    assert result["failed_reconciliation_rows"] == 1
    assert result["hardcoded_pass_count"] >= 0
    assert result["accepted"] is False


def test_all_pass_aggregate_accepted():
    rows = [
        {"metric_id": "x", "source_value": 1.0, "warehouse_value": 1.0, "tolerance": 0.01},
        {"metric_id": "y", "source_value": 2.0, "warehouse_value": 2.0, "tolerance": 0.01},
    ]
    result = validate_reconciliation_rows(rows)
    assert result["accepted"] is True
    assert result["incorrect_pass_flag_count"] == 0
    assert result["failed_reconciliation_rows"] == 0
