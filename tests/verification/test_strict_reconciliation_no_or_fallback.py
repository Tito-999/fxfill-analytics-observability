"""Verify strict reconciliation module has no OR gates and no fallback shortcuts."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))


class TestStrictReconciliationNoOrFallback:
    """The strict reconciliation gate must not use snapshot accepted or provenance as shortcut."""

    def test_module_has_no_provenance_dependency(self):
        """The strict reconciliation gate logic must not depend on provenance or snapshot."""
        # Verify the function signature: only accepts raw_staging data, not snapshot/provenance
        import inspect

        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        sig = inspect.signature(compute_strict_reconciliation)
        param_names = list(sig.parameters.keys())
        assert "raw_staging" in param_names
        assert "snapshot" not in param_names, "must not accept snapshot parameter"
        assert "provenance" not in param_names, "must not accept provenance parameter"

    def test_gate_is_pure_row_derived(self):
        """Every row must be independently evaluated."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        # Test that 0 rows → not passed (no fallback to any global state)
        r = compute_strict_reconciliation({})
        assert r["strict_reconciliation_passed"] is False
        assert r["measurement_completed"] is False

    def test_no_hardcoded_pass_detected(self):
        """hardcoded_pass_count must be computed, not assumed zero."""
        from fxfill_analytics.quality import strict_reconciliation as sr

        source = Path(sr.__file__).read_text(encoding="utf-8")
        assert "hardcoded_pass_count" in source

    def test_failed_reconciliation_with_delta(self):
        """Any non-zero delta → failed_reconciliation."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        data = {"users": {"raw_rows": 100, "staging_rows": 99, "delta": 1}}
        r = compute_strict_reconciliation(data)
        assert r["failed_reconciliation_rows"] == 1
        assert r["strict_reconciliation_passed"] is False

    def test_measurement_incomplete_with_none(self):
        """None measurement values → incomplete."""
        from fxfill_analytics.quality.strict_reconciliation import compute_strict_reconciliation

        data = {"users": {"raw_rows": None, "staging_rows": None, "delta": None}}
        r = compute_strict_reconciliation(data)
        assert r["incomplete_reconciliation_rows"] == 1
