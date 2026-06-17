"""
Data contracts for raw Parquet ingestion into DuckDB.

Each contract specifies required columns, types, primary keys,
foreign keys, and validation rules for a source table.
"""

from __future__ import annotations

from typing import Any

# ── Contract definitions ──
# Each entry: name, required_columns, primary_key, foreign_keys
RAW_CONTRACTS: dict[str, dict[str, Any]] = {
    "users": {
        "required_columns": [
            "user_id",
            "signup_time",
            "acquisition_channel",
            "country",
            "device_type",
            "user_segment",
            "company_size",
            "experience_level",
            "is_returning_user",
        ],
        "primary_key": "user_id",
        "foreign_keys": {},
        "date_columns": ["signup_time"],
    },
    "documents": {
        "required_columns": [
            "document_id",
            "user_id",
            "document_type",
            "language",
            "page_count",
            "complexity_level",
            "contains_pii",
            "contains_high_risk_terms",
            "created_at",
        ],
        "primary_key": "document_id",
        "foreign_keys": {"user_id": "users.user_id"},
        "date_columns": ["created_at"],
    },
    "sessions": {
        "required_columns": [
            "session_id",
            "user_id",
            "started_at",
            "ended_at",
            "device_type",
            "platform",
            "acquisition_channel",
            "is_bounced",
            "page_views",
        ],
        "primary_key": "session_id",
        "foreign_keys": {"user_id": "users.user_id"},
        "date_columns": ["started_at", "ended_at"],
    },
    "product_events": {
        "required_columns": [
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
        ],
        "primary_key": "event_id",
        "foreign_keys": {
            "user_id": "users.user_id",
            "session_id": "sessions.session_id",
            "document_id": "documents.document_id",
        },
        "date_columns": ["event_time", "event_date"],
    },
    "agent_runs": {
        "required_columns": [
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
        ],
        "primary_key": "agent_run_id",
        "foreign_keys": {
            "user_id": "users.user_id",
            "document_id": "documents.document_id",
        },
        "date_columns": ["started_at", "ended_at"],
    },
    "agent_spans": {
        "required_columns": [
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
        ],
        "primary_key": "span_id",
        "foreign_keys": {
            "trace_id": "agent_runs.trace_id",
        },
        "date_columns": ["start_time", "end_time"],
    },
    "experiment_assignments": {
        "required_columns": [
            "assignment_id",
            "experiment_id",
            "user_id",
            "experiment_group",
            "assigned_at",
            "is_intentional_contamination",
        ],
        "primary_key": "assignment_id",
        "foreign_keys": {"user_id": "users.user_id"},
        "date_columns": ["assigned_at"],
    },
}

REQUIRED_TABLES = sorted(RAW_CONTRACTS.keys())

REQUIRED_MANIFEST_FILES = [
    "generation_manifest.json",
    "data_quality_summary.json",
]


def validate_contracts(
    available_parquet: dict[str, bool],
    available_manifests: dict[str, bool],
) -> list[str]:
    """Validate that all required tables and manifests are present."""
    errors: list[str] = []
    for table in REQUIRED_TABLES:
        if not available_parquet.get(table):
            errors.append(f"MISSING REQUIRED TABLE: {table}.parquet not found in input directory")
    for mf in REQUIRED_MANIFEST_FILES:
        if not available_manifests.get(mf):
            errors.append(f"MISSING REQUIRED MANIFEST: {mf} not found in input directory")
    return errors
