"""Tests for Pandera schema validation and quality reporting."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest
from fxfill_analytics.generation import (
    generate_agent_runs,
    generate_agent_spans,
    generate_documents,
    generate_experiment_assignments,
    generate_product_events,
    generate_sessions,
    generate_users,
)
from fxfill_analytics.quality.checks import (
    check_duplicate_events,
    check_experiment_contamination,
    check_referential_integrity,
    check_temporal_consistency,
)
from fxfill_analytics.quality.quality_report import (
    generate_quality_report,
    validate_schemas,
)

FIXED_SEED = 20260616
START_DATE = datetime(2026, 2, 14, tzinfo=UTC)
END_DATE = datetime(2026, 6, 14, tzinfo=UTC)


@pytest.fixture(scope="module")
def tiny_tables():
    """Generate all tables at tiny scale for quality testing."""
    rng = np.random.default_rng(FIXED_SEED)
    users = generate_users(rng, 200, START_DATE, END_DATE)
    docs = generate_documents(rng, 100, list(users["user_id"]), START_DATE, END_DATE)
    sessions = generate_sessions(rng, 100, list(users["user_id"]), START_DATE, END_DATE)
    events = generate_product_events(
        rng,
        500,
        list(users["user_id"]),
        list(sessions["session_id"]),
        list(docs["document_id"]),
        START_DATE,
        END_DATE,
    )
    agent_runs = generate_agent_runs(
        rng, 100, list(users["user_id"]), list(docs["document_id"]), START_DATE, END_DATE
    )
    agent_spans = generate_agent_spans(rng, 300, list(agent_runs["trace_id"]), START_DATE, END_DATE)
    experiments = generate_experiment_assignments(
        rng, 50, list(users["user_id"]), START_DATE, END_DATE
    )
    return {
        "users": users,
        "documents": docs,
        "sessions": sessions,
        "product_events": events,
        "agent_runs": agent_runs,
        "agent_spans": agent_spans,
        "experiment_assignments": experiments,
    }


class TestSchemaValidation:
    """Test that valid generated data passes Pandera schema validation."""

    def test_all_schemas_validate(self, tiny_tables, tmp_path):
        _, failures = validate_schemas(tiny_tables)
        fatal = [f for f in failures if f["severity"] == "FATAL"]
        assert len(fatal) == 0, f"Schema validation fatal errors: {fatal}"

    def test_generate_quality_report(self, tiny_tables, tmp_path):
        summary = generate_quality_report(tiny_tables, tmp_path)
        assert summary["overall_status"] in ("passed", "warnings")
        assert (tmp_path / "data_quality_summary.json").exists()
        assert (tmp_path / "data_quality_failures.parquet").exists()


class TestReferentialIntegrity:
    """Test cross-table FK validation."""

    def test_referential_integrity_passes(self, tiny_tables):
        failures = check_referential_integrity(tiny_tables)
        assert len(failures) == 0, f"RI failures: {failures}"

    def test_referential_integrity_detects_orphans(self, tiny_tables):
        broken = dict(tiny_tables)
        # Break FK: events with non-existent user
        df = broken["product_events"].copy()
        df.loc[df.index[0], "user_id"] = "NONEXISTENT_USER"
        broken["product_events"] = df
        failures = check_referential_integrity(broken)
        assert len(failures) > 0, "Should detect orphan user reference"


class TestTemporalChecks:
    """Test temporal consistency checks."""

    def test_temporal_consistency_passes(self, tiny_tables):
        failures = check_temporal_consistency(tiny_tables)
        assert len(failures) == 0

    def test_temporal_consistency_detects_inversion(self, tiny_tables):
        broken = dict(tiny_tables)
        df = broken["sessions"].copy()
        # Swap start and end for first row
        tmp = df.loc[df.index[0], "started_at"]
        df.loc[df.index[0], "started_at"] = df.loc[df.index[0], "ended_at"]
        df.loc[df.index[0], "ended_at"] = tmp
        broken["sessions"] = df
        failures = check_temporal_consistency(broken)
        assert len(failures) > 0


class TestExperimentChecks:
    """Test experiment contamination checks."""

    def test_no_contamination_by_default(self, tiny_tables):
        failures = check_experiment_contamination(tiny_tables)
        assert len(failures) == 0

    def test_contamination_detected(self, tiny_tables):
        broken = dict(tiny_tables)
        df = broken["experiment_assignments"].copy()
        # Create contamination: duplicate a user with different group
        if len(df) > 1:
            row = df.iloc[0:1].copy()
            row["experiment_group"] = "B" if df.iloc[0]["experiment_group"] == "A" else "A"
            broken["experiment_assignments"] = pd.concat([df, row], ignore_index=True)
        failures = check_experiment_contamination(broken)
        assert len(failures) > 0


class TestDuplicateEventChecks:
    """Test duplicate event detection."""

    def test_no_duplicates_by_default(self, tiny_tables):
        failures = check_duplicate_events(tiny_tables["product_events"])
        assert len(failures) == 0

    def test_duplicates_detected_as_expected_anomaly(self, tiny_tables):
        df = tiny_tables["product_events"].copy()
        uploads = df[df["event_name"] == "document_uploaded"]
        if len(uploads) > 0:
            dup = uploads.iloc[0:1].copy()
            df = pd.concat([df, dup], ignore_index=True)
        failures = check_duplicate_events(
            df, expected_duplicates=True, duplicate_phenomenon_id="P07"
        )
        if len(failures) > 0:
            assert failures[0]["expected_anomaly"] is True
            assert failures[0]["severity"] == "WARNING"
