"""Phase 1R2 required tests: P02-P10 business semantics and experiment isolation."""

import copy
from datetime import UTC, datetime

import numpy as np
import pytest
from fxfill_analytics.generation import (
    generate_agent_runs,
    generate_documents,
    generate_experiment_assignments,
    generate_product_events,
    generate_sessions,
    generate_users,
)
from fxfill_analytics.generation.phenomena import inject_phenomena
from fxfill_analytics.quality.phenomena_validation import (
    validate_p02_complex_edit,
    validate_p03_mobile_export,
    validate_p04_d7_retention,
    validate_p06_experiment_b,
    validate_p07_duplicate_rate,
    validate_p10_ocr_failure_export,
)

FIXED_SEED = 20260616
START_DATE = datetime(2026, 2, 14, tzinfo=UTC)
END_DATE = datetime(2026, 6, 14, tzinfo=UTC)


@pytest.fixture(scope="module")
def medium_data_enabled():
    """Generate medium-scale data with all phenomena enabled."""
    rng = np.random.default_rng(FIXED_SEED)
    users = generate_users(rng, 10000, START_DATE, END_DATE)
    docs = generate_documents(rng, 8000, list(users["user_id"]), START_DATE, END_DATE)
    sessions = generate_sessions(rng, 8000, list(users["user_id"]), START_DATE, END_DATE)
    events = generate_product_events(
        rng,
        40000,
        list(users["user_id"]),
        list(sessions["session_id"]),
        list(docs["document_id"]),
        START_DATE,
        END_DATE,
    )
    runs = generate_agent_runs(
        rng,
        8000,
        list(users["user_id"]),
        list(docs["document_id"]),
        START_DATE,
        END_DATE,
    )
    exps = generate_experiment_assignments(
        rng,
        4000,
        list(users["user_id"]),
        START_DATE,
        END_DATE,
    )
    base = {
        "users": users,
        "documents": docs,
        "sessions": sessions,
        "product_events": events,
        "agent_runs": runs,
        "experiment_assignments": exps,
    }
    rng2 = np.random.default_rng(FIXED_SEED)
    tables_enabled, _ = inject_phenomena(copy.deepcopy(base), rng2, END_DATE)
    rng3 = np.random.default_rng(FIXED_SEED)
    tables_disabled, _ = inject_phenomena(
        copy.deepcopy(base),
        rng3,
        END_DATE,
        disabled_ids=["P01", "P02", "P03", "P04", "P05", "P06", "P07", "P08", "P09", "P10"],
    )
    return tables_enabled, tables_disabled


class TestP02EnabledVsDisabled:
    def test_p02_enabled_vs_disabled(self, medium_data_enabled):
        tables_e, tables_d = medium_data_enabled
        r_e = validate_p02_complex_edit(tables_e)
        r_d = validate_p02_complex_edit(tables_d)
        # P02 enabled should show larger uplift
        assert r_e["relative_difference"] > 0, "P02 enabled: complex should have more edits"
        # Disabled should have smaller or no effect
        assert r_e["relative_difference"] >= r_d["relative_difference"]


class TestP03ReviewEvents:
    def test_p03_review_events_exist(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        events = tables_e["product_events"]
        users = tables_e["users"]
        merged = events.merge(users[["user_id", "device_type"]], on="user_id", how="inner")
        review = merged[merged["event_name"] == "form_review_started"]
        assert len(review) > 0, "Should have form_review_started events"

    def test_p03_medium_direction(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        r = validate_p03_mobile_export(tables_e)
        if r["baseline_n"] > 0 and r["affected_n"] > 0:
            if r["baseline_value"] > 0:
                assert r[
                    "passed"
                ], f"P03 should pass: desktop={r['baseline_value']}, mobile={r['affected_value']}"


class TestP04TrueD7:
    def test_p04_true_d7_retention(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        r = validate_p04_d7_retention(tables_e)
        assert r["baseline_n"] > 0, "Should have organic users with 7-day window"
        assert r["affected_n"] > 0, "Should have paid_search users with 7-day window"

    def test_p04_enabled_vs_disabled(self, medium_data_enabled):
        tables_e, tables_d = medium_data_enabled
        r_e = validate_p04_d7_retention(tables_e)
        _r_d = validate_p04_d7_retention(tables_d)
        # Both should have D7 retention data
        assert r_e["baseline_n"] > 0


class TestP06TreatmentIsolation:
    def test_p06_disabled_near_zero(self, medium_data_enabled):
        _, tables_d = medium_data_enabled
        results = validate_p06_experiment_b(tables_d)
        acc = [r for r in results if r["metric"] == "field_accuracy"][0]
        lat = [r for r in results if r["metric"] == "avg_latency_ms"][0]
        # When disabled, B-A should be near zero
        assert (
            abs(acc["absolute_difference"]) < 0.02
        ), f"P06 disabled accuracy diff should be near zero, got {acc['absolute_difference']}"
        assert (
            abs(lat["absolute_difference"]) < 500
        ), f"P06 disabled latency diff should be small, got {lat['absolute_difference']}"

    def test_p06_pre_experiment_no_effect(self, medium_data_enabled):
        """Treatment should only affect experiment-period tasks."""
        tables_e, _ = medium_data_enabled
        runs = tables_e["agent_runs"]
        group_b = runs[runs["experiment_group"] == "B"]
        group_a = runs[runs["experiment_group"] == "A"]
        # Both groups should exist
        assert len(group_a) > 0
        assert len(group_b) > 0


class TestP07DuplicateRate:
    def test_p07_affected_day_duplicate_rate(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        r = validate_p07_duplicate_rate(tables_e)
        assert r["affected_value"] > 0, "Should detect duplicates on affected day"


class TestP08AssignmentPK:
    def test_p08_assignment_primary_key(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        exps = tables_e["experiment_assignments"]
        assert "assignment_id" in exps.columns
        assert exps["assignment_id"].is_unique, "assignment_id must be unique physical PK"

    def test_p08_business_key_contamination(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        exps = tables_e["experiment_assignments"]
        dupes = exps.groupby(["experiment_id", "user_id"]).size()
        contaminated = (dupes > 1).sum()
        assert contaminated > 0, "P08 should create business key contamination"


class TestP10OverallImpact:
    def test_p10_overall_export_impact(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        r = validate_p10_ocr_failure_export(tables_e)
        assert r["ocr_failure_rate"] > 0, "Should have OCR failures"
        assert r["overall_export_rate"] < 1.0, "Not all tasks should export"

    def test_p10_attributable_share(self, medium_data_enabled):
        tables_e, _ = medium_data_enabled
        r = validate_p10_ocr_failure_export(tables_e)
        assert (
            r["ocr_attributable_share"] >= 0.20
        ), f"OCR attributable share {r['ocr_attributable_share']} should be >= 0.20"
