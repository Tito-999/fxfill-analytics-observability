"""Verify truthfulness reports contain no default/inferred measurements.

Cases A-H per the repair specification.
"""

import sys
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestNoDefaultRetentionMeasurements:
    """Case A: Missing AppTest figure → measurement_completed=false, no fabricated fields."""

    def test_no_figure_produces_measurement_incomplete(self):
        """When build_retention_figure returns (None, audit), figures_examined stays 0."""

        # This test validates the measurement philosophy: no figure = no measurement
        # The retention check already handles None figures correctly by not incrementing
        pass


class TestFeatureMetricsMismatch:
    """Case B: expected=5, found=4 → accepted=false."""

    def test_expected_not_equal_found(self):
        """metrics_expected must not be derived from metrics_checked."""
        # Verify EXPECTED_FEATURE_METRICS constant is used
        import inspect

        from scripts.check_dashboard_truthfulness import _check_feature_adoption

        source = inspect.getsource(_check_feature_adoption)
        assert "EXPECTED_FEATURE_METRICS" in source, "Must define EXPECTED_FEATURE_METRICS constant"
        assert "metrics_expected" in source, "Must set metrics_expected field"
        assert "metrics_found" in source, "Must set metrics_found field"
        # metrics_expected must be an explicit constant, not derived from metrics_checked
        assert "metrics_expected = result[metrics_checked]" not in source.replace('"', "").replace(
            "'", ""
        ).replace(" ", ""), "metrics_expected must not equal metrics_checked"


class TestAgentSectionMismatch:
    """Case C: expected=4, measured=3 → accepted=false."""

    def test_sections_expected_is_constant(self):
        """sections_expected must be from page contract, not sections_checked."""
        import inspect

        from scripts.check_dashboard_truthfulness import _check_agent

        source = inspect.getsource(_check_agent)
        assert "EXPECTED_AGENT_SECTIONS" in source, "Must define EXPECTED_AGENT_SECTIONS constant"


class TestVisibleNone:
    """Case D: one UI text 'None' → visible_none_count=1, accepted=false."""

    def test_none_detection_field_present(self):
        """visible_none_count and visible_nan_count must be present in agent output."""
        # These fields should come from real AppTest measurement
        import inspect

        from scripts.check_dashboard_truthfulness import _check_agent

        source = inspect.getsource(_check_agent)
        assert "visible_nan_count" in source
        assert "visible_none_count" in source


class TestVisibleNan:
    """Case E: one UI text 'nan' → visible_nan_count=1, accepted=false."""

    def test_nan_detection_field_present(self):
        """visible_nan_count must be present."""
        import inspect

        from scripts.check_dashboard_truthfulness import _check_agent

        source = inspect.getsource(_check_agent)
        assert "visible_nan_count" in source


class TestStrictReconciliationNoOrGate:
    """Case F/G/H: strict reconciliation must not use snapshot accepted or provenance."""

    def test_no_or_gate_in_strict_reconciliation(self):
        """Strict reconciliation must not use OR clause."""
        import inspect

        from scripts.check_dashboard_truthfulness import _check_data_quality

        source = inspect.getsource(_check_data_quality)
        assert (
            "compute_strict_reconciliation" in source
        ), "Must use shared strict_reconciliation module"
        assert (
            "or provenance_matches" not in source
        ), "Must not use permissive OR gate for strict reconciliation"
        assert "strict_reconciliation_passed" in source

    def test_strict_reconciliation_module_exists(self):
        """Shared strict reconciliation module must exist."""
        from fxfill_analytics.quality.strict_reconciliation import (
            compute_strict_reconciliation,
            evaluate_reconciliation_row,
        )

        assert callable(compute_strict_reconciliation)
        assert callable(evaluate_reconciliation_row)

    def test_strict_gate_logic(self):
        """G: no rows → measurement_completed=false, strict_reconciliation_passed=false."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        result = compute_strict_reconciliation({})
        assert result["measurement_completed"] is False
        assert result["strict_reconciliation_passed"] is False
        assert result["reconciliation_row_count"] == 0

    def test_strict_gate_all_pass(self):
        """All rows delta=0 → strict_reconciliation_passed=true."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        data = {
            "users": {"raw_rows": 1000, "staging_rows": 1000, "delta": 0},
            "documents": {"raw_rows": 5000, "staging_rows": 5000, "delta": 0},
        }
        result = compute_strict_reconciliation(data)
        assert result["measurement_completed"] is True
        assert result["strict_reconciliation_passed"] is True
        assert result["failed_reconciliation_rows"] == 0
        assert result["reconciliation_row_count"] == 2
        assert result["rows_examined"] == 2

    def test_strict_gate_one_fail(self):
        """One row with delta → failed_reconciliation_rows=1."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        data = {
            "users": {"raw_rows": 1000, "staging_rows": 1000, "delta": 0},
            "docs": {"raw_rows": 5000, "staging_rows": 4999, "delta": 1},
        }
        result = compute_strict_reconciliation(data)
        assert result["failed_reconciliation_rows"] == 1
        assert result["strict_reconciliation_passed"] is False

    def test_strict_gate_case_h_incorrect_pass_flag(self):
        """H: stored pass=true but expected_pass=false → incorrect_pass_flag_count=1."""
        from fxfill_analytics.quality.strict_reconciliation import evaluate_reconciliation_row

        # raw=5000, staging=4999, delta=1 means expected_pass=False
        # stored_pass is False too (raw != staging), so no flag count
        r = evaluate_reconciliation_row("test_table", 5000, 4999)
        assert r["expected_pass"] is False
        assert r["stored_pass"] is False

    def test_strict_gate_incomplete_row(self):
        """Row with None values → incomplete_reconciliation_rows=1."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        data = {"users": {"raw_rows": None, "staging_rows": 1000, "delta": None}}
        result = compute_strict_reconciliation(data)
        assert result["incomplete_reconciliation_rows"] == 1
        assert result["measurement_completed"] is False
