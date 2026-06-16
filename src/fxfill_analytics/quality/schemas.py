"""
Pandera schemas for all seven generated tables.

Each schema validates column presence, dtypes, nullability, enum values,
numeric ranges, and temporal constraints at the single-table level.
Cross-table and business rules live in checks.py.
"""

import pandera as pa
from pandera.typing import Series


# ── Users Schema ──
class UsersSchema(pa.DataFrameModel):
    """Schema for the generated users dimension table."""

    user_id: Series[str] = pa.Field(nullable=False, unique=True)
    signup_time: pa.typing.DateTime = pa.Field(nullable=False)
    acquisition_channel: Series[str] = pa.Field(
        nullable=False,
        isin=["organic", "paid_search", "social", "referral", "campus"],
    )
    country: Series[str] = pa.Field(nullable=False)
    device_type: Series[str] = pa.Field(nullable=False, isin=["desktop", "mobile", "tablet"])
    user_segment: Series[str] = pa.Field(
        nullable=False,
        isin=["student", "individual", "small_business", "enterprise_trial"],
    )
    company_size: Series[str] = pa.Field(nullable=False)
    experience_level: Series[str] = pa.Field(nullable=False, isin=["new", "intermediate", "expert"])
    is_returning_user: Series[bool] = pa.Field(nullable=False)


# ── Documents Schema ──
class DocumentsSchema(pa.DataFrameModel):
    """Schema for the generated documents dimension table."""

    document_id: Series[str] = pa.Field(nullable=False, unique=True)
    user_id: Series[str] = pa.Field(nullable=False)
    document_type: Series[str] = pa.Field(
        nullable=False,
        isin=[
            "bank_transfer_form",
            "invoice",
            "identity_document",
            "beneficiary_form",
            "exchange_declaration",
        ],
    )
    language: Series[str] = pa.Field(nullable=False)
    page_count: Series[int] = pa.Field(nullable=False, ge=1, coerce=True)
    complexity_level: Series[str] = pa.Field(nullable=False, isin=["simple", "medium", "complex"])
    contains_pii: Series[bool] = pa.Field(nullable=False)
    contains_high_risk_terms: Series[bool] = pa.Field(nullable=False)
    created_at: pa.typing.DateTime = pa.Field(nullable=False)


# ── Sessions Schema ──
class SessionsSchema(pa.DataFrameModel):
    """Schema for the generated sessions dimension table."""

    session_id: Series[str] = pa.Field(nullable=False, unique=True)
    user_id: Series[str] = pa.Field(nullable=False)
    started_at: pa.typing.DateTime = pa.Field(nullable=False)
    ended_at: pa.typing.DateTime = pa.Field(nullable=False)
    device_type: Series[str] = pa.Field(nullable=False, isin=["desktop", "mobile", "tablet"])
    platform: Series[str] = pa.Field(nullable=False, isin=["web", "api"])
    acquisition_channel: Series[str] = pa.Field(
        nullable=False,
        isin=["organic", "paid_search", "social", "referral", "campus"],
    )
    is_bounced: Series[bool] = pa.Field(nullable=False)
    page_views: Series[int] = pa.Field(nullable=False, ge=1)


# ── Product Events Schema ──
class ProductEventsSchema(pa.DataFrameModel):
    """Schema for the generated product events fact table."""

    event_id: Series[str] = pa.Field(nullable=False, unique=True)
    event_time: pa.typing.DateTime = pa.Field(nullable=False)
    event_date: Series[object] = pa.Field(nullable=False)  # date objects, not datetime64
    user_id: Series[str] = pa.Field(nullable=False)
    session_id: Series[str] = pa.Field(nullable=False)
    document_id: Series[str] = pa.Field(nullable=False)
    task_id: Series[str] = pa.Field(nullable=False)
    event_name: Series[str] = pa.Field(
        nullable=False,
        isin=[
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
        ],
    )
    event_status: Series[str] = pa.Field(nullable=False, isin=["success", "failure", "pending"])
    platform: Series[str] = pa.Field(nullable=False, isin=["web", "api"])
    app_version: Series[str] = pa.Field(nullable=False)
    experiment_id: Series[str] = pa.Field(nullable=True)
    experiment_group: Series[str] = pa.Field(nullable=True)
    latency_ms: Series[float] = pa.Field(nullable=False, ge=0, coerce=True)
    error_type: Series[str] = pa.Field(nullable=True)
    metadata_json: Series[str] = pa.Field(nullable=False)


# ── Agent Runs Schema ──
class AgentRunsSchema(pa.DataFrameModel):
    """Schema for the generated agent runs fact table."""

    agent_run_id: Series[str] = pa.Field(nullable=False, unique=True)
    trace_id: Series[str] = pa.Field(nullable=False, unique=True)
    task_id: Series[str] = pa.Field(nullable=False)
    user_id: Series[str] = pa.Field(nullable=False)
    document_id: Series[str] = pa.Field(nullable=False)
    started_at: pa.typing.DateTime = pa.Field(nullable=False)
    ended_at: pa.typing.DateTime = pa.Field(nullable=False)
    total_latency_ms: Series[int] = pa.Field(nullable=False, ge=0, coerce=True)
    total_input_tokens: Series[int] = pa.Field(nullable=False, ge=0, coerce=True)
    total_output_tokens: Series[int] = pa.Field(nullable=False, ge=0, coerce=True)
    estimated_cost_usd: Series[float] = pa.Field(nullable=False, ge=0)
    model_name: Series[str] = pa.Field(nullable=False)
    prompt_version: Series[str] = pa.Field(nullable=False)
    tool_call_count: Series[int] = pa.Field(nullable=False, ge=0)
    retry_count: Series[int] = pa.Field(nullable=False, ge=0)
    success_flag: Series[bool] = pa.Field(nullable=False)
    quality_score: Series[float] = pa.Field(nullable=False, ge=0, le=1)
    field_accuracy: Series[float] = pa.Field(nullable=False, ge=0, le=1)
    manual_edit_count: Series[int] = pa.Field(nullable=False, ge=0)
    error_type: Series[str] = pa.Field(nullable=True)
    experiment_group: Series[str] = pa.Field(nullable=True)


# ── Agent Spans Schema ──
class AgentSpansSchema(pa.DataFrameModel):
    """Schema for the generated agent spans fact table."""

    span_id: Series[str] = pa.Field(nullable=False, unique=True)
    trace_id: Series[str] = pa.Field(nullable=False)
    parent_span_id: Series[str] = pa.Field(nullable=True)
    span_name: Series[str] = pa.Field(
        nullable=False,
        isin=[
            "document_classification",
            "ocr_extraction",
            "pii_detection",
            "anonymization",
            "risk_detection",
            "field_mapping",
            "form_autofill",
            "output_validation",
        ],
    )
    span_type: Series[str] = pa.Field(
        nullable=False,
        isin=["agent", "llm", "tool", "retrieval", "validation"],
    )
    start_time: pa.typing.DateTime = pa.Field(nullable=False)
    end_time: pa.typing.DateTime = pa.Field(nullable=False)
    latency_ms: Series[int] = pa.Field(nullable=False, ge=0, coerce=True)
    status: Series[str] = pa.Field(nullable=False, isin=["ok", "error", "warning"])
    model_name: Series[str] = pa.Field(nullable=True)
    input_tokens: Series[int] = pa.Field(nullable=False, ge=0, coerce=True)
    output_tokens: Series[int] = pa.Field(nullable=False, ge=0, coerce=True)
    estimated_cost_usd: Series[float] = pa.Field(nullable=False, ge=0)
    tool_name: Series[str] = pa.Field(nullable=True)
    error_type: Series[str] = pa.Field(nullable=True)
    metadata_json: Series[str] = pa.Field(nullable=False)


# ── Experiment Assignments Schema ──
class ExperimentAssignmentsSchema(pa.DataFrameModel):
    """Schema for the generated experiment assignments table."""

    assignment_id: Series[str] = pa.Field(nullable=False, unique=True)
    experiment_id: Series[str] = pa.Field(nullable=False)
    user_id: Series[str] = pa.Field(nullable=False)
    experiment_group: Series[str] = pa.Field(nullable=False, isin=["A", "B"])
    assigned_at: pa.typing.DateTime = pa.Field(nullable=False)
    is_intentional_contamination: Series[bool] = pa.Field(nullable=False)


# ── Schema registry for programmatic access ──
SCHEMA_REGISTRY: dict[str, type[pa.DataFrameModel]] = {
    "users": UsersSchema,
    "documents": DocumentsSchema,
    "sessions": SessionsSchema,
    "product_events": ProductEventsSchema,
    "agent_runs": AgentRunsSchema,
    "agent_spans": AgentSpansSchema,
    "experiment_assignments": ExperimentAssignmentsSchema,
}
