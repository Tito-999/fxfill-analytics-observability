"""
Phase 0 Smoke Test — Tiny Synthetic Data Generation & Validation.

This test validates the minimum viable data generation pipeline:
1. Generate tiny datasets with fixed seed using real generator modules
2. Validate row counts, column presence, data types
3. Validate referential integrity
4. Validate business rules (e.g., timestamps, status values)
5. Confirm seed reproducibility
6. Verify atomic output to temporary directory (no pollution of data/generated/)

ALL DATA IS SYNTHETIC — labeled clearly. All generators are imported from
src/fxfill_analytics/generation/ — no inline generator functions.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

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
from fxfill_analytics.generation.generate_agent_traces import SPAN_NAMES, SPAN_TYPES
from fxfill_analytics.generation.generate_documents import (
    COMPLEXITY_LEVELS,
    DOCUMENT_TYPES,
)
from fxfill_analytics.generation.generate_experiment_data import EXPERIMENT_GROUPS
from fxfill_analytics.generation.generate_product_events import EVENT_NAMES
from fxfill_analytics.generation.generate_users import (
    ACQUISITION_CHANNELS,
    DEVICE_TYPES,
    EXPERIENCE_LEVELS,
    USER_SEGMENTS,
)

# ── Tiny Data Configuration (matches config/app.yml) ──
TINY_CONFIG = {
    "users": 200,
    "sessions": 600,
    "events": 4000,
    "documents": 800,
    "agent_runs": 800,
    "agent_spans": 3000,
    "experiment_users": 120,
}

FIXED_SEED = 20260616
DATE_RANGE_DAYS = 120
END_DATE = datetime(2026, 6, 14, tzinfo=UTC)
START_DATE = END_DATE - timedelta(days=DATE_RANGE_DAYS)

APP_VERSIONS = ["2.1.0", "2.2.0", "2.3.0"]


# ── Test Fixtures ──


@pytest.fixture(scope="module")
def rng() -> np.random.Generator:
    """Seeded NumPy random generator for reproducibility."""
    return np.random.default_rng(FIXED_SEED)


@pytest.fixture(scope="module")
def tiny_users(rng: np.random.Generator) -> pd.DataFrame:
    """Generate users using the real generator module."""
    return generate_users(rng, TINY_CONFIG["users"], START_DATE, END_DATE)


@pytest.fixture(scope="module")
def tiny_documents(rng: np.random.Generator, tiny_users: pd.DataFrame) -> pd.DataFrame:
    """Generate documents using the real generator module."""
    return generate_documents(
        rng, TINY_CONFIG["documents"], list(tiny_users["user_id"]), START_DATE, END_DATE
    )


@pytest.fixture(scope="module")
def tiny_sessions(rng: np.random.Generator, tiny_users: pd.DataFrame) -> pd.DataFrame:
    """Generate sessions using the real generator module."""
    return generate_sessions(
        rng, TINY_CONFIG["sessions"], list(tiny_users["user_id"]), START_DATE, END_DATE
    )


@pytest.fixture(scope="module")
def tiny_events(
    rng: np.random.Generator,
    tiny_users: pd.DataFrame,
    tiny_sessions: pd.DataFrame,
    tiny_documents: pd.DataFrame,
) -> pd.DataFrame:
    """Generate product events using the real generator module."""
    return generate_product_events(
        rng,
        TINY_CONFIG["events"],
        list(tiny_users["user_id"]),
        list(tiny_sessions["session_id"]),
        list(tiny_documents["document_id"]),
        START_DATE,
        END_DATE,
    )


@pytest.fixture(scope="module")
def tiny_agent_runs(
    rng: np.random.Generator,
    tiny_users: pd.DataFrame,
    tiny_documents: pd.DataFrame,
) -> pd.DataFrame:
    """Generate agent runs using the real generator module."""
    return generate_agent_runs(
        rng,
        TINY_CONFIG["agent_runs"],
        list(tiny_users["user_id"]),
        list(tiny_documents["document_id"]),
        START_DATE,
        END_DATE,
    )


@pytest.fixture(scope="module")
def tiny_agent_spans(rng: np.random.Generator, tiny_agent_runs: pd.DataFrame) -> pd.DataFrame:
    """Generate agent spans using the real generator module."""
    return generate_agent_spans(
        rng,
        TINY_CONFIG["agent_spans"],
        list(tiny_agent_runs["trace_id"]),
        START_DATE,
        END_DATE,
    )


@pytest.fixture(scope="module")
def tiny_experiment_assignments(rng: np.random.Generator, tiny_users: pd.DataFrame) -> pd.DataFrame:
    """Generate experiment assignments using the real generator module."""
    return generate_experiment_assignments(
        rng,
        TINY_CONFIG["experiment_users"],
        list(tiny_users["user_id"]),
        START_DATE,
        END_DATE,
    )


# ── Test Classes ──


class TestRowCounts:
    """Validate that generated data matches the expected row counts."""

    def test_user_count(self, tiny_users: pd.DataFrame):
        assert len(tiny_users) == TINY_CONFIG["users"]

    def test_document_count(self, tiny_documents: pd.DataFrame):
        assert len(tiny_documents) == TINY_CONFIG["documents"]

    def test_session_count(self, tiny_sessions: pd.DataFrame):
        assert len(tiny_sessions) == TINY_CONFIG["sessions"]

    def test_event_count(self, tiny_events: pd.DataFrame):
        assert len(tiny_events) == TINY_CONFIG["events"]

    def test_agent_run_count(self, tiny_agent_runs: pd.DataFrame):
        assert len(tiny_agent_runs) == TINY_CONFIG["agent_runs"]

    def test_agent_span_count(self, tiny_agent_spans: pd.DataFrame):
        assert len(tiny_agent_spans) == TINY_CONFIG["agent_spans"]

    def test_experiment_assignment_count(self, tiny_experiment_assignments: pd.DataFrame):
        assert len(tiny_experiment_assignments) == TINY_CONFIG["experiment_users"]


class TestColumnPresence:
    """Validate required columns exist in each table."""

    USER_COLS = {
        "user_id",
        "signup_time",
        "acquisition_channel",
        "country",
        "device_type",
        "user_segment",
        "company_size",
        "experience_level",
        "is_returning_user",
    }
    DOC_COLS = {
        "document_id",
        "user_id",
        "document_type",
        "language",
        "page_count",
        "complexity_level",
        "contains_pii",
        "contains_high_risk_terms",
        "created_at",
    }
    SESSION_COLS = {
        "session_id",
        "user_id",
        "started_at",
        "ended_at",
        "device_type",
        "platform",
        "acquisition_channel",
        "is_bounced",
        "page_views",
    }
    EVENT_COLS = {
        "event_id",
        "event_time",
        "event_date",
        "user_id",
        "session_id",
        "document_id",
        "task_id",
        "event_name",
        "event_status",
        "platform",
        "app_version",
        "experiment_id",
        "experiment_group",
        "latency_ms",
        "error_type",
        "metadata_json",
    }
    AGENT_RUN_COLS = {
        "agent_run_id",
        "trace_id",
        "task_id",
        "user_id",
        "document_id",
        "started_at",
        "ended_at",
        "total_latency_ms",
        "total_input_tokens",
        "total_output_tokens",
        "estimated_cost_usd",
        "model_name",
        "prompt_version",
        "tool_call_count",
        "retry_count",
        "success_flag",
        "quality_score",
        "field_accuracy",
        "manual_edit_count",
        "error_type",
        "experiment_group",
    }
    AGENT_SPAN_COLS = {
        "span_id",
        "trace_id",
        "parent_span_id",
        "span_name",
        "span_type",
        "start_time",
        "end_time",
        "latency_ms",
        "status",
        "model_name",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
        "tool_name",
        "error_type",
        "metadata_json",
    }
    EXP_COLS = {"experiment_id", "user_id", "experiment_group", "assigned_at"}

    def test_user_columns(self, tiny_users: pd.DataFrame):
        missing = self.USER_COLS - set(tiny_users.columns)
        assert not missing, f"Missing user columns: {missing}"

    def test_document_columns(self, tiny_documents: pd.DataFrame):
        missing = self.DOC_COLS - set(tiny_documents.columns)
        assert not missing, f"Missing document columns: {missing}"

    def test_session_columns(self, tiny_sessions: pd.DataFrame):
        missing = self.SESSION_COLS - set(tiny_sessions.columns)
        assert not missing, f"Missing session columns: {missing}"

    def test_event_columns(self, tiny_events: pd.DataFrame):
        missing = self.EVENT_COLS - set(tiny_events.columns)
        assert not missing, f"Missing event columns: {missing}"

    def test_agent_run_columns(self, tiny_agent_runs: pd.DataFrame):
        missing = self.AGENT_RUN_COLS - set(tiny_agent_runs.columns)
        assert not missing, f"Missing agent run columns: {missing}"

    def test_agent_span_columns(self, tiny_agent_spans: pd.DataFrame):
        missing = self.AGENT_SPAN_COLS - set(tiny_agent_spans.columns)
        assert not missing, f"Missing agent span columns: {missing}"

    def test_experiment_columns(self, tiny_experiment_assignments: pd.DataFrame):
        missing = self.EXP_COLS - set(tiny_experiment_assignments.columns)
        assert not missing, f"Missing experiment columns: {missing}"


class TestNonNullIds:
    """Validate that ID columns contain no null values."""

    def test_user_ids_not_null(self, tiny_users: pd.DataFrame):
        assert tiny_users["user_id"].notna().all()

    def test_document_ids_not_null(self, tiny_documents: pd.DataFrame):
        assert tiny_documents["document_id"].notna().all()

    def test_session_ids_not_null(self, tiny_sessions: pd.DataFrame):
        assert tiny_sessions["session_id"].notna().all()
        assert tiny_sessions["user_id"].notna().all()

    def test_event_ids_not_null(self, tiny_events: pd.DataFrame):
        assert tiny_events["event_id"].notna().all()
        assert tiny_events["user_id"].notna().all()

    def test_agent_run_ids_not_null(self, tiny_agent_runs: pd.DataFrame):
        assert tiny_agent_runs["agent_run_id"].notna().all()
        assert tiny_agent_runs["trace_id"].notna().all()

    def test_agent_span_ids_not_null(self, tiny_agent_spans: pd.DataFrame):
        assert tiny_agent_spans["span_id"].notna().all()
        assert tiny_agent_spans["trace_id"].notna().all()


class TestUniqueness:
    """Validate unique constraints on ID columns."""

    def test_user_id_unique(self, tiny_users: pd.DataFrame):
        assert tiny_users["user_id"].is_unique

    def test_document_id_unique(self, tiny_documents: pd.DataFrame):
        assert tiny_documents["document_id"].is_unique

    def test_session_id_unique(self, tiny_sessions: pd.DataFrame):
        assert tiny_sessions["session_id"].is_unique

    def test_event_id_unique(self, tiny_events: pd.DataFrame):
        assert tiny_events["event_id"].is_unique

    def test_agent_run_id_unique(self, tiny_agent_runs: pd.DataFrame):
        assert tiny_agent_runs["agent_run_id"].is_unique

    def test_trace_id_unique(self, tiny_agent_runs: pd.DataFrame):
        assert tiny_agent_runs["trace_id"].is_unique

    def test_span_id_unique(self, tiny_agent_spans: pd.DataFrame):
        assert tiny_agent_spans["span_id"].is_unique

    def test_experiment_user_unique(self, tiny_experiment_assignments: pd.DataFrame):
        assert tiny_experiment_assignments["user_id"].is_unique


class TestReferentialIntegrity:
    """Validate foreign key relationships."""

    def test_event_users_exist(self, tiny_events: pd.DataFrame, tiny_users: pd.DataFrame):
        event_user_ids = set(tiny_events["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = event_user_ids - user_ids
        assert not missing, f"Event users not in users: {len(missing)} rows"

    def test_event_sessions_exist(self, tiny_events: pd.DataFrame, tiny_sessions: pd.DataFrame):
        event_ses_ids = set(tiny_events["session_id"])
        ses_ids = set(tiny_sessions["session_id"])
        missing = event_ses_ids - ses_ids
        assert not missing, f"Event sessions not in sessions: {len(missing)} rows"

    def test_event_documents_exist(self, tiny_events: pd.DataFrame, tiny_documents: pd.DataFrame):
        event_doc_ids = set(tiny_events["document_id"])
        doc_ids = set(tiny_documents["document_id"])
        missing = event_doc_ids - doc_ids
        assert not missing, f"Event documents not in documents: {len(missing)} rows"

    def test_agent_run_users_exist(self, tiny_agent_runs: pd.DataFrame, tiny_users: pd.DataFrame):
        run_user_ids = set(tiny_agent_runs["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = run_user_ids - user_ids
        assert not missing, f"Agent run users not in users: {len(missing)} rows"

    def test_span_traces_exist(self, tiny_agent_spans: pd.DataFrame, tiny_agent_runs: pd.DataFrame):
        span_trace_ids = set(tiny_agent_spans["trace_id"])
        run_trace_ids = set(tiny_agent_runs["trace_id"])
        missing = span_trace_ids - run_trace_ids
        assert not missing, f"Span traces not in agent_runs: {len(missing)} rows"

    def test_experiment_users_exist(
        self, tiny_experiment_assignments: pd.DataFrame, tiny_users: pd.DataFrame
    ):
        exp_user_ids = set(tiny_experiment_assignments["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = exp_user_ids - user_ids
        assert not missing, f"Experiment users not in users: {len(missing)} rows"

    def test_session_users_exist(self, tiny_sessions: pd.DataFrame, tiny_users: pd.DataFrame):
        ses_user_ids = set(tiny_sessions["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = ses_user_ids - user_ids
        assert not missing, f"Session users not in users: {len(missing)} rows"


class TestEnumValues:
    """Validate that enum columns contain only allowed values."""

    def test_acquisition_channel_valid(self, tiny_users: pd.DataFrame):
        invalid = set(tiny_users["acquisition_channel"]) - set(ACQUISITION_CHANNELS)
        assert not invalid, f"Invalid channels: {invalid}"

    def test_device_type_valid(self, tiny_users: pd.DataFrame):
        invalid = set(tiny_users["device_type"]) - set(DEVICE_TYPES)
        assert not invalid, f"Invalid device types: {invalid}"

    def test_experience_level_valid(self, tiny_users: pd.DataFrame):
        invalid = set(tiny_users["experience_level"]) - set(EXPERIENCE_LEVELS)
        assert not invalid, f"Invalid experience levels: {invalid}"

    def test_document_type_valid(self, tiny_documents: pd.DataFrame):
        invalid = set(tiny_documents["document_type"]) - set(DOCUMENT_TYPES)
        assert not invalid, f"Invalid document types: {invalid}"

    def test_complexity_level_valid(self, tiny_documents: pd.DataFrame):
        invalid = set(tiny_documents["complexity_level"]) - set(COMPLEXITY_LEVELS)
        assert not invalid, f"Invalid complexity levels: {invalid}"

    def test_event_names_valid(self, tiny_events: pd.DataFrame):
        invalid = set(tiny_events["event_name"]) - set(EVENT_NAMES)
        assert not invalid, f"Invalid event names: {invalid}"

    def test_span_types_valid(self, tiny_agent_spans: pd.DataFrame):
        invalid = set(tiny_agent_spans["span_type"]) - set(SPAN_TYPES)
        assert not invalid, f"Invalid span types: {invalid}"

    def test_span_names_valid(self, tiny_agent_spans: pd.DataFrame):
        invalid = set(tiny_agent_spans["span_name"]) - set(SPAN_NAMES)
        assert not invalid, f"Invalid span names: {invalid}"

    def test_experiment_groups_valid(self, tiny_experiment_assignments: pd.DataFrame):
        invalid = set(tiny_experiment_assignments["experiment_group"]) - set(EXPERIMENT_GROUPS)
        assert not invalid, f"Invalid experiment groups: {invalid}"

    def test_user_segment_valid(self, tiny_users: pd.DataFrame):
        invalid = set(tiny_users["user_segment"]) - set(USER_SEGMENTS)
        assert not invalid, f"Invalid user segments: {invalid}"


class TestTemporalLogic:
    """Validate time-related business rules."""

    def test_agent_run_end_after_start(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["ended_at"] >= tiny_agent_runs["started_at"]).all()

    def test_span_end_after_start(self, tiny_agent_spans: pd.DataFrame):
        assert (tiny_agent_spans["end_time"] >= tiny_agent_spans["start_time"]).all()

    def test_session_end_after_start(self, tiny_sessions: pd.DataFrame):
        assert (tiny_sessions["ended_at"] >= tiny_sessions["started_at"]).all()

    def test_latency_non_negative(self, tiny_events: pd.DataFrame):
        assert (tiny_events["latency_ms"] >= 0).all()

    def test_agent_latency_non_negative(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["total_latency_ms"] >= 0).all()

    def test_span_latency_non_negative(self, tiny_agent_spans: pd.DataFrame):
        assert (tiny_agent_spans["latency_ms"] >= 0).all()

    def test_events_within_date_range(self, tiny_events: pd.DataFrame):
        min_date = START_DATE.date()
        max_date = END_DATE.date()
        assert (tiny_events["event_date"] >= min_date).all()
        assert (tiny_events["event_date"] <= max_date).all()


class TestBusinessRules:
    """Validate business logic constraints."""

    def test_cost_non_negative(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["estimated_cost_usd"] >= 0).all()

    def test_tokens_non_negative(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["total_input_tokens"] >= 0).all()
        assert (tiny_agent_runs["total_output_tokens"] >= 0).all()

    def test_span_cost_non_negative(self, tiny_agent_spans: pd.DataFrame):
        assert (tiny_agent_spans["estimated_cost_usd"] >= 0).all()

    def test_span_tokens_non_negative(self, tiny_agent_spans: pd.DataFrame):
        assert (tiny_agent_spans["input_tokens"] >= 0).all()
        assert (tiny_agent_spans["output_tokens"] >= 0).all()

    def test_quality_score_range(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["quality_score"] >= 0).all()
        assert (tiny_agent_runs["quality_score"] <= 1.0).all()

    def test_field_accuracy_range(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["field_accuracy"] >= 0).all()
        assert (tiny_agent_runs["field_accuracy"] <= 1.0).all()

    def test_success_flag_boolean(self, tiny_agent_runs: pd.DataFrame):
        assert tiny_agent_runs["success_flag"].isin([True, False]).all()

    def test_experiment_assignment_no_cross_contamination(
        self, tiny_experiment_assignments: pd.DataFrame
    ):
        """Each user should only be in one experiment group."""
        user_groups = tiny_experiment_assignments.groupby("user_id")["experiment_group"].nunique()
        cross_contaminated = (user_groups > 1).sum()
        assert (
            cross_contaminated == 0
        ), f"{cross_contaminated} users assigned to multiple experiment groups"


class TestSeedReproducibility:
    """Validate that the same seed produces identical output."""

    def test_users_reproducible(self, tiny_users: pd.DataFrame):
        rng2 = np.random.default_rng(FIXED_SEED)
        users2 = generate_users(rng2, TINY_CONFIG["users"], START_DATE, END_DATE)
        pd.testing.assert_frame_equal(tiny_users, users2)

    def test_events_reproducible(
        self,
        tiny_users: pd.DataFrame,
        tiny_sessions: pd.DataFrame,
        tiny_documents: pd.DataFrame,
        tiny_events: pd.DataFrame,
    ):
        rng2 = np.random.default_rng(FIXED_SEED)
        # Must match fixture resolution order: users → documents → sessions → events
        _ = generate_users(rng2, TINY_CONFIG["users"], START_DATE, END_DATE)
        docs2 = generate_documents(
            rng2, TINY_CONFIG["documents"], list(tiny_users["user_id"]), START_DATE, END_DATE
        )
        _ = generate_sessions(
            rng2, TINY_CONFIG["sessions"], list(tiny_users["user_id"]), START_DATE, END_DATE
        )
        events2 = generate_product_events(
            rng2,
            TINY_CONFIG["events"],
            list(tiny_users["user_id"]),
            list(tiny_sessions["session_id"]),
            list(docs2["document_id"]),
            START_DATE,
            END_DATE,
        )
        pd.testing.assert_frame_equal(tiny_events, events2)

    def test_spans_reproducible(
        self,
        tiny_users: pd.DataFrame,
        tiny_documents: pd.DataFrame,
        tiny_agent_runs: pd.DataFrame,
        tiny_agent_spans: pd.DataFrame,
    ):
        rng2 = np.random.default_rng(FIXED_SEED)
        # Must match fixture resolution order:
        # users → documents → sessions → events → agent_runs → agent_spans
        _ = generate_users(rng2, TINY_CONFIG["users"], START_DATE, END_DATE)
        _ = generate_documents(
            rng2,
            TINY_CONFIG["documents"],
            [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)],
            START_DATE,
            END_DATE,
        )
        _ = generate_sessions(
            rng2,
            TINY_CONFIG["sessions"],
            [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)],
            START_DATE,
            END_DATE,
        )
        _ = generate_product_events(
            rng2,
            TINY_CONFIG["events"],
            [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)],
            [f"SES{i:07d}" for i in range(1, TINY_CONFIG["sessions"] + 1)],
            [f"DOC{i:06d}" for i in range(1, TINY_CONFIG["documents"] + 1)],
            START_DATE,
            END_DATE,
        )
        _ = generate_agent_runs(
            rng2,
            TINY_CONFIG["agent_runs"],
            [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)],
            [f"DOC{i:06d}" for i in range(1, TINY_CONFIG["documents"] + 1)],
            START_DATE,
            END_DATE,
        )
        spans2 = generate_agent_spans(
            rng2,
            TINY_CONFIG["agent_spans"],
            list(tiny_agent_runs["trace_id"]),
            START_DATE,
            END_DATE,
        )
        pd.testing.assert_frame_equal(tiny_agent_spans, spans2)


class TestSyntheticMarking:
    """Validate that all data is clearly marked as synthetic."""

    def test_events_metadata_is_synthetic(self, tiny_events: pd.DataFrame):
        assert all("synthetic" in str(m) for m in tiny_events["metadata_json"])

    def test_spans_metadata_is_synthetic(self, tiny_agent_spans: pd.DataFrame):
        assert all("synthetic" in str(m) for m in tiny_agent_spans["metadata_json"])


class TestTmpPathOutput:
    """Validate that data can be written to and read from a temporary directory.

    This ensures generation does not depend on data/generated/ and that
    the output format (Parquet) round-trips correctly.
    """

    def test_write_to_tmp_path(self, tmp_path: Path):
        """Generate all tables and write to tmp_path, then read back and verify."""
        rng = np.random.default_rng(FIXED_SEED)
        out_dir = tmp_path / "generated"
        out_dir.mkdir()

        # Generate all tables
        users = generate_users(rng, TINY_CONFIG["users"], START_DATE, END_DATE)
        docs = generate_documents(
            rng, TINY_CONFIG["documents"], list(users["user_id"]), START_DATE, END_DATE
        )
        sessions = generate_sessions(
            rng, TINY_CONFIG["sessions"], list(users["user_id"]), START_DATE, END_DATE
        )
        events = generate_product_events(
            rng,
            TINY_CONFIG["events"],
            list(users["user_id"]),
            list(sessions["session_id"]),
            list(docs["document_id"]),
            START_DATE,
            END_DATE,
        )
        agent_runs = generate_agent_runs(
            rng,
            TINY_CONFIG["agent_runs"],
            list(users["user_id"]),
            list(docs["document_id"]),
            START_DATE,
            END_DATE,
        )
        agent_spans = generate_agent_spans(
            rng,
            TINY_CONFIG["agent_spans"],
            list(agent_runs["trace_id"]),
            START_DATE,
            END_DATE,
        )
        exp_assignments = generate_experiment_assignments(
            rng,
            TINY_CONFIG["experiment_users"],
            list(users["user_id"]),
            START_DATE,
            END_DATE,
        )

        # Write to Parquet in tmp_path
        tables = {
            "users": users,
            "documents": docs,
            "sessions": sessions,
            "product_events": events,
            "agent_runs": agent_runs,
            "agent_spans": agent_spans,
            "experiment_assignments": exp_assignments,
        }
        for name, df in tables.items():
            df.to_parquet(out_dir / f"{name}.parquet", index=False)

        # Read back and verify row counts
        for name, df in tables.items():
            read_back = pd.read_parquet(out_dir / f"{name}.parquet")
            assert len(read_back) == len(df), f"Row count mismatch for {name}"

        # Verify no pollution of data/generated/ — tmp_path is elsewhere

    def test_tmp_path_file_sizes(self, tmp_path: Path):
        """Verify that written Parquet files have non-zero size."""
        rng = np.random.default_rng(FIXED_SEED)
        out_dir = tmp_path / "generated"
        out_dir.mkdir()

        users = generate_users(rng, TINY_CONFIG["users"], START_DATE, END_DATE)
        users.to_parquet(out_dir / "users.parquet", index=False)

        file_size = (out_dir / "users.parquet").stat().st_size
        assert file_size > 0, "Parquet file should have non-zero size"


# ── Smoke test that exercises the full pipeline ──


def test_full_smoke_pipeline(
    tiny_users: pd.DataFrame,
    tiny_documents: pd.DataFrame,
    tiny_sessions: pd.DataFrame,
    tiny_events: pd.DataFrame,
    tiny_agent_runs: pd.DataFrame,
    tiny_agent_spans: pd.DataFrame,
    tiny_experiment_assignments: pd.DataFrame,
):
    """
    End-to-end smoke test: generate all tables and verify cross-table consistency.

    This is the single most important test — if it passes, the generation
    pipeline is functioning correctly at the tiny scale. All data comes from
    the real generator modules in src/fxfill_analytics/generation/.
    """
    # Cross-table consistency: every table should be non-empty
    assert len(tiny_users) > 0, "Users table is empty"
    assert len(tiny_documents) > 0, "Documents table is empty"
    assert len(tiny_sessions) > 0, "Sessions table is empty"
    assert len(tiny_events) > 0, "Events table is empty"
    assert len(tiny_agent_runs) > 0, "Agent runs table is empty"
    assert len(tiny_agent_spans) > 0, "Agent spans table is empty"
    assert len(tiny_experiment_assignments) > 0, "Experiment assignments table is empty"

    # Event → User
    orphan_event_users = set(tiny_events["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_event_users, f"Orphan event users: {orphan_event_users}"

    # Event → Session
    orphan_event_sessions = set(tiny_events["session_id"]) - set(tiny_sessions["session_id"])
    assert not orphan_event_sessions, f"Orphan event sessions: {orphan_event_sessions}"

    # Event → Document
    orphan_event_docs = set(tiny_events["document_id"]) - set(tiny_documents["document_id"])
    assert not orphan_event_docs, f"Orphan event documents: {orphan_event_docs}"

    # Agent Run → User
    orphan_run_users = set(tiny_agent_runs["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_run_users, f"Orphan agent run users: {orphan_run_users}"

    # Span → Trace
    orphan_traces = set(tiny_agent_spans["trace_id"]) - set(tiny_agent_runs["trace_id"])
    assert not orphan_traces, f"Orphan span traces: {orphan_traces}"

    # Experiment → User
    orphan_exp_users = set(tiny_experiment_assignments["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_exp_users, f"Orphan experiment users: {orphan_exp_users}"

    # Session → User
    orphan_ses_users = set(tiny_sessions["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_ses_users, f"Orphan session users: {orphan_ses_users}"


# ── Edge case tests for coverage ──


class TestGeneratorValidation:
    """Validate that generators raise proper errors on invalid inputs."""

    def test_users_zero_count_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="count must be positive"):
            generate_users(rng, 0, START_DATE, END_DATE)

    def test_users_negative_count_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="count must be positive"):
            generate_users(rng, -1, START_DATE, END_DATE)

    def test_docs_empty_user_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="user_ids must not be empty"):
            generate_documents(rng, 10, [], START_DATE, END_DATE)

    def test_sessions_empty_user_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="user_ids must not be empty"):
            generate_sessions(rng, 10, [], START_DATE, END_DATE)

    def test_events_empty_user_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="user_ids must not be empty"):
            generate_product_events(rng, 10, [], ["s1"], ["d1"], START_DATE, END_DATE)

    def test_events_empty_doc_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="doc_ids must not be empty"):
            generate_product_events(rng, 10, ["u1"], ["s1"], [], START_DATE, END_DATE)

    def test_events_empty_session_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="session_ids must not be empty"):
            generate_product_events(rng, 10, ["u1"], [], ["d1"], START_DATE, END_DATE)

    def test_agent_runs_empty_user_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="user_ids must not be empty"):
            generate_agent_runs(rng, 10, [], ["d1"], START_DATE, END_DATE)

    def test_agent_spans_empty_trace_ids_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="trace_ids must not be empty"):
            generate_agent_spans(rng, 10, [], START_DATE, END_DATE)

    def test_experiment_count_exceeds_users_raises(self):
        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="count.*must not exceed"):
            generate_experiment_assignments(rng, 100, ["u1", "u2"], START_DATE, END_DATE)


class TestDistributionsEdgeCases:
    """Validate distribution helper error handling."""

    def test_lognormal_params_zero_mean_raises(self):
        from fxfill_analytics.generation.distributions import lognormal_params

        with pytest.raises(ValueError, match="mean_ms and std_ms must be positive"):
            lognormal_params(0.0, 100.0)

    def test_lognormal_params_negative_std_raises(self):
        from fxfill_analytics.generation.distributions import lognormal_params

        with pytest.raises(ValueError, match="mean_ms and std_ms must be positive"):
            lognormal_params(100.0, -10.0)


class TestDatesEdgeCases:
    """Validate date utility error handling."""

    def test_generate_timestamps_zero_count(self):

        from fxfill_analytics.utils.dates import generate_timestamps

        rng = np.random.default_rng(FIXED_SEED)
        result = generate_timestamps(
            rng,
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 10, tzinfo=UTC),
            0,
        )
        assert result == []

    def test_generate_timestamps_end_before_start_raises(self):

        from fxfill_analytics.utils.dates import generate_timestamps

        rng = np.random.default_rng(FIXED_SEED)
        with pytest.raises(ValueError, match="end_date.*must be after start_date"):
            generate_timestamps(
                rng,
                datetime(2026, 1, 10, tzinfo=UTC),
                datetime(2026, 1, 1, tzinfo=UTC),
                10,
            )
