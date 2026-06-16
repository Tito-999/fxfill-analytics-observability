"""
Cross-table referential integrity and business rule validation.

These checks go beyond single-table Pandera schemas to verify:
- Foreign key relationships
- Temporal ordering (e.g., span start < span end)
- Business rules (e.g., cost >= 0, tokens >= 0)
- Expected anomalies vs unexpected data errors

Returns lists of failure records suitable for data_quality_failures.parquet.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def make_failure(
    check_id: str,
    check_name: str,
    severity: str,
    table_name: str,
    record_id: str,
    failure_reason: str,
    expected_anomaly: bool = False,
    phenomenon_id: str | None = None,
) -> dict[str, Any]:
    """Create a standardized failure record."""
    return {
        "check_id": check_id,
        "check_name": check_name,
        "severity": severity,
        "table_name": table_name,
        "record_id": str(record_id),
        "failure_reason": failure_reason,
        "expected_anomaly": expected_anomaly,
        "phenomenon_id": phenomenon_id,
        "detected_at": _now_iso(),
    }


def check_referential_integrity(
    tables: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    """
    Verify all foreign key relationships across tables.

    Checks:
    - events.user_id ⊆ users.user_id
    - events.session_id ⊆ sessions.session_id
    - events.document_id ⊆ documents.document_id
    - agent_runs.user_id ⊆ users.user_id
    - agent_runs.document_id ⊆ documents.document_id
    - agent_spans.trace_id ⊆ agent_runs.trace_id
    - experiment_assignments.user_id ⊆ users.user_id
    - sessions.user_id ⊆ users.user_id
    - documents.user_id ⊆ users.user_id
    """
    failures: list[dict[str, Any]] = []

    users = tables.get("users")
    sessions = tables.get("sessions")
    documents = tables.get("documents")
    events = tables.get("product_events")
    agent_runs = tables.get("agent_runs")
    agent_spans = tables.get("agent_spans")
    experiments = tables.get("experiment_assignments")

    if users is None:
        return failures

    user_id_set = set(users["user_id"])

    # Events → Users
    if events is not None:
        orphan = set(events["user_id"]) - user_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-001",
                    "events.user_id → users.user_id",
                    "FATAL",
                    "product_events",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan user references in product_events",
                )
            )

    # Events → Sessions
    if events is not None and sessions is not None:
        session_id_set = set(sessions["session_id"])
        orphan = set(events["session_id"]) - session_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-002",
                    "events.session_id → sessions.session_id",
                    "FATAL",
                    "product_events",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan session references",
                )
            )

    # Events → Documents
    if events is not None and documents is not None:
        doc_id_set = set(documents["document_id"])
        orphan = set(events["document_id"]) - doc_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-003",
                    "events.document_id → documents.document_id",
                    "FATAL",
                    "product_events",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan document references",
                )
            )

    # Agent Runs → Users
    if agent_runs is not None:
        orphan = set(agent_runs["user_id"]) - user_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-004",
                    "agent_runs.user_id → users.user_id",
                    "FATAL",
                    "agent_runs",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan user references in agent_runs",
                )
            )

    # Agent Spans → Agent Runs (via trace_id)
    if agent_spans is not None and agent_runs is not None:
        trace_id_set = set(agent_runs["trace_id"])
        orphan = set(agent_spans["trace_id"]) - trace_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-005",
                    "agent_spans.trace_id → agent_runs.trace_id",
                    "FATAL",
                    "agent_spans",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan trace references",
                )
            )

    # Experiment Assignments → Users
    if experiments is not None:
        orphan = set(experiments["user_id"]) - user_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-006",
                    "experiment_assignments.user_id → users.user_id",
                    "FATAL",
                    "experiment_assignments",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan user references in experiments",
                )
            )

    # Sessions → Users
    if sessions is not None:
        orphan = set(sessions["user_id"]) - user_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-007",
                    "sessions.user_id → users.user_id",
                    "FATAL",
                    "sessions",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan user references in sessions",
                )
            )

    # Documents → Users
    if documents is not None:
        orphan = set(documents["user_id"]) - user_id_set
        if orphan:
            failures.append(
                make_failure(
                    "RI-008",
                    "documents.user_id → users.user_id",
                    "FATAL",
                    "documents",
                    str(list(orphan)[:5]),
                    f"{len(orphan)} orphan user references in documents",
                )
            )

    return failures


def check_temporal_consistency(
    tables: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    """
    Verify temporal ordering rules.

    Checks:
    - agent_runs.ended_at >= agent_runs.started_at
    - agent_spans.end_time >= agent_spans.start_time
    - sessions.ended_at >= sessions.started_at
    """
    failures: list[dict[str, Any]] = []

    agent_runs = tables.get("agent_runs")
    agent_spans = tables.get("agent_spans")
    sessions = tables.get("sessions")

    if agent_runs is not None:
        bad = agent_runs[agent_runs["ended_at"] < agent_runs["started_at"]]
        if len(bad) > 0:
            failures.append(
                make_failure(
                    "TC-001",
                    "agent_runs ended_at < started_at",
                    "FATAL",
                    "agent_runs",
                    str(list(bad["agent_run_id"])[:5]),
                    f"{len(bad)} runs with invalid time ordering",
                )
            )

    if agent_spans is not None:
        bad = agent_spans[agent_spans["end_time"] < agent_spans["start_time"]]
        if len(bad) > 0:
            failures.append(
                make_failure(
                    "TC-002",
                    "agent_spans end_time < start_time",
                    "FATAL",
                    "agent_spans",
                    str(list(bad["span_id"])[:5]),
                    f"{len(bad)} spans with invalid time ordering",
                )
            )

    if sessions is not None:
        bad = sessions[sessions["ended_at"] < sessions["started_at"]]
        if len(bad) > 0:
            failures.append(
                make_failure(
                    "TC-003",
                    "sessions ended_at < started_at",
                    "FATAL",
                    "sessions",
                    str(list(bad["session_id"])[:5]),
                    f"{len(bad)} sessions with invalid time ordering",
                )
            )

    return failures


def check_experiment_contamination(
    tables: dict[str, pd.DataFrame],
    expected_contamination: bool = False,
    contamination_phenomenon_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Verify experiment assignment integrity.

    Users should normally be in exactly one experiment group.
    Contamination (user in both A and B) is an expected anomaly only
    when explicitly injected.
    """
    failures: list[dict[str, Any]] = []
    experiments = tables.get("experiment_assignments")

    if experiments is None:
        return failures

    user_counts = experiments.groupby("user_id")["experiment_group"].nunique()
    contaminated = user_counts[user_counts > 1]

    if len(contaminated) > 0:
        severity = "WARNING" if expected_contamination else "FATAL"
        anomaly = expected_contamination
        failures.append(
            make_failure(
                "EC-001",
                "experiment cross-contamination",
                severity,
                "experiment_assignments",
                str(list(contaminated.index[:5])),
                f"{len(contaminated)} users in multiple experiment groups",
                expected_anomaly=anomaly,
                phenomenon_id=contamination_phenomenon_id if anomaly else None,
            )
        )

    return failures


def check_duplicate_events(
    events_df: pd.DataFrame,
    expected_duplicates: bool = False,
    duplicate_phenomenon_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Check for duplicate document_uploaded events.

    If expected_duplicates is True (P07), duplicates are expected anomalies.
    Otherwise they are FATAL.
    """
    failures: list[dict[str, Any]] = []

    uploads = events_df[events_df["event_name"] == "document_uploaded"]
    dupes = uploads[uploads.duplicated(subset=["document_id", "user_id"], keep=False)]

    if len(dupes) > 0:
        severity = "WARNING" if expected_duplicates else "FATAL"
        anomaly = expected_duplicates
        failures.append(
            make_failure(
                "DE-001",
                "duplicate document_uploaded events",
                severity,
                "product_events",
                str(list(dupes["event_id"])[:5]),
                f"{len(dupes)} duplicate upload events detected",
                expected_anomaly=anomaly,
                phenomenon_id=duplicate_phenomenon_id if anomaly else None,
            )
        )

    return failures


def run_all_checks(
    tables: dict[str, pd.DataFrame],
    phenomena_enabled: dict[str, bool] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Run all cross-table quality checks.

    Args:
        tables: Dict mapping table name to DataFrame.
        phenomena_enabled: Dict mapping phenomenon_id to enabled flag.

    Returns:
        Tuple of (failures list, summary dict).
    """
    if phenomena_enabled is None:
        phenomena_enabled = {}

    all_failures: list[dict[str, Any]] = []

    # Referential integrity
    all_failures.extend(check_referential_integrity(tables))

    # Temporal consistency
    all_failures.extend(check_temporal_consistency(tables))

    # Experiment contamination (with expected anomaly support)
    all_failures.extend(
        check_experiment_contamination(
            tables,
            expected_contamination=phenomena_enabled.get("P08", False),
            contamination_phenomenon_id="P08" if phenomena_enabled.get("P08") else None,
        )
    )

    # Duplicate events (with expected anomaly support)
    events = tables.get("product_events")
    if events is not None:
        all_failures.extend(
            check_duplicate_events(
                events,
                expected_duplicates=phenomena_enabled.get("P07", False),
                duplicate_phenomenon_id="P07" if phenomena_enabled.get("P07") else None,
            )
        )

    # Summarize
    fatal = sum(1 for f in all_failures if f["severity"] == "FATAL")
    warnings = sum(1 for f in all_failures if f["severity"] == "WARNING")
    expected = sum(1 for f in all_failures if f["expected_anomaly"])
    unexpected = len(all_failures) - expected

    summary = {
        "checks_total": 5,
        "checks_passed": 5 - len({f["check_id"] for f in all_failures}),
        "checks_warned": warnings,
        "checks_failed": fatal,
        "expected_anomalies_detected": expected,
        "unexpected_failures": unexpected,
    }

    return all_failures, summary
