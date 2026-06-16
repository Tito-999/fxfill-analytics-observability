"""
Phase 0 Smoke Test — Tiny Synthetic Data Generation & Validation.

This test validates the minimum viable data generation pipeline:
1. Generate tiny datasets with fixed seed
2. Validate row counts, column presence, data types
3. Validate referential integrity
4. Validate business rules (e.g., timestamps, status values)
5. Confirm seed reproducibility

ALL DATA IS SYNTHETIC — labeled clearly.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

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
END_DATE = datetime(2026, 6, 14, tzinfo=timezone.utc)
START_DATE = END_DATE - timedelta(days=DATE_RANGE_DAYS)

# ── Enum values ──
ACQUISITION_CHANNELS = ["organic", "paid_search", "social", "referral", "campus"]
DEVICE_TYPES = ["desktop", "mobile", "tablet"]
USER_SEGMENTS = ["student", "individual", "small_business", "enterprise_trial"]
EXPERIENCE_LEVELS = ["new", "intermediate", "expert"]
DOCUMENT_TYPES = [
    "bank_transfer_form",
    "invoice",
    "identity_document",
    "beneficiary_form",
    "exchange_declaration",
]
COMPLEXITY_LEVELS = ["simple", "medium", "complex"]

EVENT_NAMES = [
    "user_signed_up",
    "session_started",
    "document_uploaded",
    "ocr_started",
    "ocr_completed",
    "anonymization_started",
    "anonymization_completed",
    "risk_detection_started",
    "risk_detection_completed",
    "autofill_started",
    "autofill_completed",
    "form_review_started",
    "field_edited",
    "form_exported",
    "task_abandoned",
    "agent_run_failed",
]

SPAN_TYPES = ["agent", "llm", "tool", "retrieval", "validation"]
SPAN_NAMES = [
    "document_classification",
    "ocr_extraction",
    "pii_detection",
    "anonymization",
    "risk_detection",
    "field_mapping",
    "form_autofill",
    "output_validation",
]
MODEL_NAMES = ["gpt-4o-mini-2024-07-18", "gpt-4o-2024-08-06", "claude-haiku-3.5-20241022"]
PROMPT_VERSIONS = ["v1.0.0", "v1.1.0", "v2.0.0-beta"]
APP_VERSIONS = ["2.1.0", "2.2.0", "2.3.0"]
EXPERIMENT_GROUPS = ["A", "B"]


# ── Data Generators ──

def _gen_users(rng: np.random.Generator, count: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Generate synthetic user dimension table."""
    user_ids = [f"U{i:06d}" for i in range(1, count + 1)]
    signup_times = [
        start_date + timedelta(seconds=float(s))
        for s in np.sort(rng.uniform(0, (end_date - start_date).total_seconds(), size=count))
    ]
    return pd.DataFrame(
        {
            "user_id": user_ids,
            "signup_time": signup_times,
            "acquisition_channel": rng.choice(ACQUISITION_CHANNELS, size=count),
            "country": rng.choice(["US", "GB", "DE", "JP", "CN", "SG", "AU", "BR"], size=count),
            "device_type": rng.choice(DEVICE_TYPES, size=count, p=[0.60, 0.30, 0.10]),
            "user_segment": rng.choice(USER_SEGMENTS, size=count, p=[0.20, 0.35, 0.30, 0.15]),
            "company_size": rng.choice(["1-50", "51-200", "201-500", "501-1000", "1000+"], size=count),
            "experience_level": rng.choice(EXPERIENCE_LEVELS, size=count, p=[0.45, 0.35, 0.20]),
            "is_returning_user": rng.random(size=count) < 0.30,
        }
    )


def _gen_documents(
    rng: np.random.Generator, count: int, user_ids: list[str], start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    """Generate synthetic document dimension table."""
    doc_ids = [f"DOC{i:06d}" for i in range(1, count + 1)]
    created_ats = [
        start_date + timedelta(seconds=float(s))
        for s in np.sort(rng.uniform(0, (end_date - start_date).total_seconds(), size=count))
    ]
    return pd.DataFrame(
        {
            "document_id": doc_ids,
            "user_id": rng.choice(user_ids, size=count),
            "document_type": rng.choice(DOCUMENT_TYPES, size=count),
            "language": rng.choice(["en", "zh", "ja", "de", "es", "fr"], size=count),
            "page_count": rng.integers(1, 15, size=count),
            "complexity_level": rng.choice(COMPLEXITY_LEVELS, size=count, p=[0.40, 0.35, 0.25]),
            "contains_pii": rng.random(size=count) < 0.55,
            "contains_high_risk_terms": rng.random(size=count) < 0.25,
            "created_at": created_ats,
        }
    )


def _gen_events(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    doc_ids: list[str],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Generate synthetic product events fact table."""
    n = count
    event_ids = [f"EVT{i:07d}" for i in range(1, n + 1)]
    doc_ids_sample = doc_ids if doc_ids else [f"DOC{i:06d}" for i in range(1, n + 1)]

    timestamps = [
        start_date + timedelta(seconds=float(s))
        for s in np.sort(rng.uniform(0, (end_date - start_date).total_seconds(), size=n))
    ]

    # Assign events to tasks (approx 4 events per task on average)
    n_tasks = max(n // 4, 1)
    task_ids = [f"TSK{i:06d}" for i in range(1, n_tasks + 1)]

    return pd.DataFrame(
        {
            "event_id": event_ids,
            "event_time": timestamps,
            "event_date": [t.date() for t in timestamps],
            "user_id": rng.choice(user_ids, size=n),
            "session_id": [f"SES{i:07d}" for i in rng.integers(1, max(n // 3, 2), size=n)],
            "document_id": rng.choice(doc_ids_sample, size=n),
            "task_id": rng.choice(task_ids, size=n),
            "event_name": rng.choice(EVENT_NAMES, size=n),
            "event_status": rng.choice(["success", "failure", "pending"], size=n, p=[0.85, 0.08, 0.07]),
            "platform": rng.choice(["web", "api"], size=n, p=[0.80, 0.20]),
            "app_version": rng.choice(APP_VERSIONS, size=n),
            "experiment_id": rng.choice(["EXP001", None], size=n, p=[0.10, 0.90]),
            "experiment_group": rng.choice([*EXPERIMENT_GROUPS, None], size=n, p=[0.05, 0.05, 0.90]),
            "latency_ms": np.maximum(rng.normal(500, 200, size=n).astype(int), 0),
            "error_type": rng.choice([None, "timeout", "parse_error", "validation_error"], size=n, p=[0.92, 0.03, 0.03, 0.02]),
            "metadata_json": [r'{"source":"synthetic"}' for _ in range(n)],
        }
    )


def _gen_agent_runs(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    doc_ids: list[str],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Generate synthetic agent runs fact table."""
    n = count
    run_ids = [f"AGN{i:07d}" for i in range(1, n + 1)]
    trace_ids = [f"TRC{i:07d}" for i in range(1, n + 1)]
    task_ids = [f"TSK{i:06d}" for i in range(1, n + 1)]

    started_ats = [
        start_date + timedelta(seconds=float(s))
        for s in np.sort(rng.uniform(0, (end_date - start_date).total_seconds(), size=n))
    ]
    latencies = np.maximum(rng.lognormal(8.5, 0.5, size=n).astype(int), 100)
    ended_ats = [started_ats[i] + timedelta(milliseconds=float(latencies[i])) for i in range(n)]

    input_tokens = rng.integers(5000, 30000, size=n)
    output_tokens = rng.integers(500, 5000, size=n)

    return pd.DataFrame(
        {
            "agent_run_id": run_ids,
            "trace_id": trace_ids,
            "task_id": task_ids,
            "user_id": rng.choice(user_ids, size=n),
            "document_id": rng.choice(doc_ids, size=n),
            "started_at": started_ats,
            "ended_at": ended_ats,
            "total_latency_ms": latencies,
            "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
            "estimated_cost_usd": np.round(input_tokens * 0.00015 + output_tokens * 0.00060, 6).astype(float),
            "model_name": rng.choice(MODEL_NAMES, size=n, p=[0.40, 0.35, 0.25]),
            "prompt_version": rng.choice(PROMPT_VERSIONS, size=n, p=[0.50, 0.35, 0.15]),
            "tool_call_count": rng.integers(3, 10, size=n),
            "retry_count": rng.integers(0, 4, size=n),
            "success_flag": rng.random(size=n) < 0.88,
            "quality_score": np.round(rng.uniform(0.70, 1.0, size=n), 2),
            "field_accuracy": np.round(rng.uniform(0.75, 1.0, size=n), 2),
            "manual_edit_count": rng.poisson(2, size=n),
            "error_type": rng.choice([None, "ocr_error", "timeout", "api_error", "parse_error"], size=n, p=[0.85, 0.05, 0.04, 0.03, 0.03]),
            "experiment_group": rng.choice([*EXPERIMENT_GROUPS, None], size=n, p=[0.05, 0.05, 0.90]),
        }
    )


def _gen_agent_spans(
    rng: np.random.Generator,
    count: int,
    trace_ids: list[str],
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """Generate synthetic agent spans fact table."""
    n = count
    span_ids = [f"SPN{i:07d}" for i in range(1, n + 1)]

    # Each span belongs to a trace
    assigned_traces = rng.choice(trace_ids, size=n)
    # Some spans have parents (child spans within a trace)
    span_types_sample = rng.choice(SPAN_TYPES, size=n, p=[0.20, 0.40, 0.25, 0.10, 0.05])
    span_names_sample = rng.choice(SPAN_NAMES, size=n)

    # Generate parent-child relationships
    is_child = rng.random(size=n) < 0.70
    parent_span_ids: list[str | None] = []
    for i in range(n):
        if is_child[i] and i > 0:
            # Point to a span with the same trace (simplified: just use a nearby span)
            parent_span_ids.append(span_ids[max(0, i - rng.integers(1, min(5, i + 1)))])
        else:
            parent_span_ids.append(None)

    start_times = [
        start_date + timedelta(seconds=float(s))
        for s in np.sort(rng.uniform(0, (end_date - start_date).total_seconds(), size=n))
    ]
    span_latencies = np.maximum(rng.lognormal(5.5, 0.6, size=n).astype(int), 10)
    end_times = [start_times[i] + timedelta(milliseconds=float(span_latencies[i])) for i in range(n)]

    input_tokens = rng.integers(1000, 10000, size=n)
    output_tokens = rng.integers(100, 2000, size=n)

    return pd.DataFrame(
        {
            "span_id": span_ids,
            "trace_id": assigned_traces,
            "parent_span_id": parent_span_ids,
            "span_name": span_names_sample,
            "span_type": span_types_sample,
            "start_time": start_times,
            "end_time": end_times,
            "latency_ms": span_latencies,
            "status": rng.choice(["ok", "error", "warning"], size=n, p=[0.85, 0.08, 0.07]),
            "model_name": rng.choice([*MODEL_NAMES, None], size=n, p=[0.30, 0.30, 0.20, 0.20]),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": np.round(input_tokens * 0.00015 + output_tokens * 0.00060, 6).astype(float),
            "tool_name": rng.choice([None, "ocr_api", "pii_scanner", "risk_api", "field_mapper"], size=n, p=[0.40, 0.20, 0.15, 0.15, 0.10]),
            "error_type": rng.choice([None, "timeout", "rate_limit", "invalid_input", "internal_error"], size=n, p=[0.90, 0.03, 0.03, 0.02, 0.02]),
            "metadata_json": [r'{"source":"synthetic"}' for _ in range(n)],
        }
    )


def _gen_experiment_assignments(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
) -> pd.DataFrame:
    """Generate synthetic experiment assignment table."""
    n = count
    assigned_users = rng.choice(user_ids, size=n, replace=False)
    return pd.DataFrame(
        {
            "experiment_id": ["EXP001"] * n,
            "user_id": list(assigned_users),
            "experiment_group": rng.choice(EXPERIMENT_GROUPS, size=n),
            "assigned_at": [
                START_DATE + timedelta(seconds=float(s))
                for s in np.sort(rng.uniform(0, (END_DATE - START_DATE).total_seconds(), size=n))
            ],
        }
    )


# ── Test Fixtures ──

@pytest.fixture(scope="module")
def rng() -> np.random.Generator:
    """Seeded NumPy random generator for reproducibility."""
    return np.random.default_rng(FIXED_SEED)


@pytest.fixture(scope="module")
def tiny_users(rng: np.random.Generator) -> pd.DataFrame:
    return _gen_users(rng, TINY_CONFIG["users"], START_DATE, END_DATE)


@pytest.fixture(scope="module")
def tiny_documents(rng: np.random.Generator, tiny_users: pd.DataFrame) -> pd.DataFrame:
    return _gen_documents(rng, TINY_CONFIG["documents"], list(tiny_users["user_id"]), START_DATE, END_DATE)


@pytest.fixture(scope="module")
def tiny_events(rng: np.random.Generator, tiny_users: pd.DataFrame, tiny_documents: pd.DataFrame) -> pd.DataFrame:
    return _gen_events(rng, TINY_CONFIG["events"], list(tiny_users["user_id"]), list(tiny_documents["document_id"]), START_DATE, END_DATE)


@pytest.fixture(scope="module")
def tiny_agent_runs(rng: np.random.Generator, tiny_users: pd.DataFrame, tiny_documents: pd.DataFrame) -> pd.DataFrame:
    return _gen_agent_runs(rng, TINY_CONFIG["agent_runs"], list(tiny_users["user_id"]), list(tiny_documents["document_id"]), START_DATE, END_DATE)


@pytest.fixture(scope="module")
def tiny_agent_spans(rng: np.random.Generator, tiny_agent_runs: pd.DataFrame) -> pd.DataFrame:
    return _gen_agent_spans(rng, TINY_CONFIG["agent_spans"], list(tiny_agent_runs["trace_id"]), START_DATE, END_DATE)


@pytest.fixture(scope="module")
def tiny_experiment_assignments(rng: np.random.Generator, tiny_users: pd.DataFrame) -> pd.DataFrame:
    return _gen_experiment_assignments(rng, TINY_CONFIG["experiment_users"], list(tiny_users["user_id"]))


# ── Test Classes ──

class TestRowCounts:
    """Validate that generated data matches the expected row counts."""

    def test_user_count(self, tiny_users: pd.DataFrame):
        assert len(tiny_users) == TINY_CONFIG["users"], f"Expected {TINY_CONFIG['users']} users, got {len(tiny_users)}"

    def test_document_count(self, tiny_documents: pd.DataFrame):
        assert len(tiny_documents) == TINY_CONFIG["documents"]

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
        "user_id", "signup_time", "acquisition_channel", "country",
        "device_type", "user_segment", "company_size", "experience_level",
        "is_returning_user",
    }
    DOC_COLS = {
        "document_id", "user_id", "document_type", "language", "page_count",
        "complexity_level", "contains_pii", "contains_high_risk_terms", "created_at",
    }
    EVENT_COLS = {
        "event_id", "event_time", "event_date", "user_id", "session_id",
        "document_id", "task_id", "event_name", "event_status", "platform",
        "app_version", "experiment_id", "experiment_group", "latency_ms",
        "error_type", "metadata_json",
    }
    AGENT_RUN_COLS = {
        "agent_run_id", "trace_id", "task_id", "user_id", "document_id",
        "started_at", "ended_at", "total_latency_ms", "total_input_tokens",
        "total_output_tokens", "estimated_cost_usd", "model_name",
        "prompt_version", "tool_call_count", "retry_count", "success_flag",
        "quality_score", "field_accuracy", "manual_edit_count", "error_type",
        "experiment_group",
    }
    AGENT_SPAN_COLS = {
        "span_id", "trace_id", "parent_span_id", "span_name", "span_type",
        "start_time", "end_time", "latency_ms", "status", "model_name",
        "input_tokens", "output_tokens", "estimated_cost_usd", "tool_name",
        "error_type", "metadata_json",
    }
    EXP_COLS = {"experiment_id", "user_id", "experiment_group", "assigned_at"}

    def test_user_columns(self, tiny_users: pd.DataFrame):
        missing = self.USER_COLS - set(tiny_users.columns)
        assert not missing, f"Missing user columns: {missing}"

    def test_document_columns(self, tiny_documents: pd.DataFrame):
        missing = self.DOC_COLS - set(tiny_documents.columns)
        assert not missing, f"Missing document columns: {missing}"

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

    def test_event_id_unique(self, tiny_events: pd.DataFrame):
        assert tiny_events["event_id"].is_unique

    def test_agent_run_id_unique(self, tiny_agent_runs: pd.DataFrame):
        assert tiny_agent_runs["agent_run_id"].is_unique

    def test_span_id_unique(self, tiny_agent_spans: pd.DataFrame):
        assert tiny_agent_spans["span_id"].is_unique

    def test_user_id_unique(self, tiny_users: pd.DataFrame):
        assert tiny_users["user_id"].is_unique

    def test_experiment_user_unique(self, tiny_experiment_assignments: pd.DataFrame):
        assert tiny_experiment_assignments["user_id"].is_unique


class TestReferentialIntegrity:
    """Validate foreign key relationships."""

    def test_event_users_exist(self, tiny_events: pd.DataFrame, tiny_users: pd.DataFrame):
        event_user_ids = set(tiny_events["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = event_user_ids - user_ids
        assert not missing, f"Event users not in dim_users: {len(missing)} rows"

    def test_event_documents_exist(self, tiny_events: pd.DataFrame, tiny_documents: pd.DataFrame):
        event_doc_ids = set(tiny_events["document_id"])
        doc_ids = set(tiny_documents["document_id"])
        missing = event_doc_ids - doc_ids
        assert not missing, f"Event documents not in dim_documents: {len(missing)} rows"

    def test_agent_run_users_exist(self, tiny_agent_runs: pd.DataFrame, tiny_users: pd.DataFrame):
        run_user_ids = set(tiny_agent_runs["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = run_user_ids - user_ids
        assert not missing, f"Agent run users not in dim_users: {len(missing)} rows"

    def test_span_traces_exist(self, tiny_agent_spans: pd.DataFrame, tiny_agent_runs: pd.DataFrame):
        span_trace_ids = set(tiny_agent_spans["trace_id"])
        run_trace_ids = set(tiny_agent_runs["trace_id"])
        missing = span_trace_ids - run_trace_ids
        assert not missing, f"Span traces not in agent_runs: {len(missing)} rows"

    def test_experiment_users_exist(self, tiny_experiment_assignments: pd.DataFrame, tiny_users: pd.DataFrame):
        exp_user_ids = set(tiny_experiment_assignments["user_id"])
        user_ids = set(tiny_users["user_id"])
        missing = exp_user_ids - user_ids
        assert not missing, f"Experiment users not in dim_users: {len(missing)} rows"


class TestEnumValues:
    """Validate that enum columns contain only allowed values."""

    def test_acquisition_channel_valid(self, tiny_users: pd.DataFrame):
        invalid = set(tiny_users["acquisition_channel"]) - set(ACQUISITION_CHANNELS)
        assert not invalid, f"Invalid channels: {invalid}"

    def test_device_type_valid(self, tiny_users: pd.DataFrame):
        invalid = set(tiny_users["device_type"]) - set(DEVICE_TYPES)
        assert not invalid, f"Invalid device types: {invalid}"

    def test_event_names_valid(self, tiny_events: pd.DataFrame):
        invalid = set(tiny_events["event_name"]) - set(EVENT_NAMES)
        assert not invalid, f"Invalid event names: {invalid}"

    def test_span_types_valid(self, tiny_agent_spans: pd.DataFrame):
        invalid = set(tiny_agent_spans["span_type"]) - set(SPAN_TYPES)
        assert not invalid, f"Invalid span types: {invalid}"

    def test_experiment_groups_valid(self, tiny_experiment_assignments: pd.DataFrame):
        invalid = set(tiny_experiment_assignments["experiment_group"]) - set(EXPERIMENT_GROUPS)
        assert not invalid, f"Invalid experiment groups: {invalid}"


class TestTemporalLogic:
    """Validate time-related business rules."""

    def test_agent_run_end_after_start(self, tiny_agent_runs: pd.DataFrame):
        assert (tiny_agent_runs["ended_at"] >= tiny_agent_runs["started_at"]).all()

    def test_span_end_after_start(self, tiny_agent_spans: pd.DataFrame):
        assert (tiny_agent_spans["end_time"] >= tiny_agent_spans["start_time"]).all()

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

    def test_experiment_assignment_no_cross_contamination(self, tiny_experiment_assignments: pd.DataFrame):
        """Each user should only be in one experiment group."""
        user_groups = tiny_experiment_assignments.groupby("user_id")["experiment_group"].nunique()
        cross_contaminated = (user_groups > 1).sum()
        assert cross_contaminated == 0, f"{cross_contaminated} users assigned to multiple experiment groups"


class TestSeedReproducibility:
    """Validate that the same seed produces identical output."""

    def test_users_reproducible(self, tiny_users: pd.DataFrame):
        rng2 = np.random.default_rng(FIXED_SEED)
        users2 = _gen_users(rng2, TINY_CONFIG["users"], START_DATE, END_DATE)
        pd.testing.assert_frame_equal(tiny_users, users2)

    def test_events_reproducible(self, tiny_users: pd.DataFrame, tiny_documents: pd.DataFrame, tiny_events: pd.DataFrame):
        rng2 = np.random.default_rng(FIXED_SEED)
        _ = _gen_users(rng2, TINY_CONFIG["users"], START_DATE, END_DATE)
        docs2 = _gen_documents(rng2, TINY_CONFIG["documents"], list(tiny_users["user_id"]), START_DATE, END_DATE)
        events2 = _gen_events(rng2, TINY_CONFIG["events"], list(tiny_users["user_id"]), list(docs2["document_id"]), START_DATE, END_DATE)
        pd.testing.assert_frame_equal(tiny_events, events2)

    def test_spans_reproducible(self, tiny_agent_runs: pd.DataFrame, tiny_agent_spans: pd.DataFrame):
        rng2 = np.random.default_rng(FIXED_SEED)
        # Re-run the full chain to match RNG state after prior generators consumed
        _ = _gen_users(rng2, TINY_CONFIG["users"], START_DATE, END_DATE)
        _ = _gen_documents(rng2, TINY_CONFIG["documents"], [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)], START_DATE, END_DATE)
        _ = _gen_events(rng2, TINY_CONFIG["events"], [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)], [f"DOC{i:06d}" for i in range(1, TINY_CONFIG["documents"] + 1)], START_DATE, END_DATE)
        _ = _gen_agent_runs(rng2, TINY_CONFIG["agent_runs"], [f"U{i:06d}" for i in range(1, TINY_CONFIG["users"] + 1)], [f"DOC{i:06d}" for i in range(1, TINY_CONFIG["documents"] + 1)], START_DATE, END_DATE)
        spans2 = _gen_agent_spans(rng2, TINY_CONFIG["agent_spans"], list(tiny_agent_runs["trace_id"]), START_DATE, END_DATE)
        pd.testing.assert_frame_equal(tiny_agent_spans, spans2)


class TestSyntheticMarking:
    """Validate that all data is clearly marked as synthetic."""

    def test_events_metadata_is_synthetic(self, tiny_events: pd.DataFrame):
        assert all("synthetic" in str(m) for m in tiny_events["metadata_json"])

    def test_spans_metadata_is_synthetic(self, tiny_agent_spans: pd.DataFrame):
        assert all("synthetic" in str(m) for m in tiny_agent_spans["metadata_json"])


# ── Smoke test that exercises the full pipeline ──

def test_full_smoke_pipeline(
    tiny_users: pd.DataFrame,
    tiny_documents: pd.DataFrame,
    tiny_events: pd.DataFrame,
    tiny_agent_runs: pd.DataFrame,
    tiny_agent_spans: pd.DataFrame,
    tiny_experiment_assignments: pd.DataFrame,
):
    """
    End-to-end smoke test: generate all tables and verify cross-table consistency.

    This is the single most important test — if it passes, the generation
    pipeline is functioning correctly at the tiny scale.
    """
    # Cross-table consistency: events should reference real users and documents
    assert len(tiny_users) > 0, "Users table is empty"
    assert len(tiny_documents) > 0, "Documents table is empty"
    assert len(tiny_events) > 0, "Events table is empty"
    assert len(tiny_agent_runs) > 0, "Agent runs table is empty"
    assert len(tiny_agent_spans) > 0, "Agent spans table is empty"
    assert len(tiny_experiment_assignments) > 0, "Experiment assignments table is empty"

    # Event → User: every event user should exist
    orphan_event_users = set(tiny_events["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_event_users, f"Orphan event users: {orphan_event_users}"

    # Agent Run → User: every agent run user should exist
    orphan_run_users = set(tiny_agent_runs["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_run_users, f"Orphan agent run users: {orphan_run_users}"

    # Span → Trace: every span trace should exist
    orphan_traces = set(tiny_agent_spans["trace_id"]) - set(tiny_agent_runs["trace_id"])
    assert not orphan_traces, f"Orphan span traces: {orphan_traces}"

    # Experiment → User
    orphan_exp_users = set(tiny_experiment_assignments["user_id"]) - set(tiny_users["user_id"])
    assert not orphan_exp_users, f"Orphan experiment users: {orphan_exp_users}"
