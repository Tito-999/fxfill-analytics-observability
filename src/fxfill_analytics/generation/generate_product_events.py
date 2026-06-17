"""
Synthetic product event fact table generation with realistic task pipelines.

Each task follows a sequential pipeline:
  document_uploaded → ocr_started → ocr_completed → anonymization_started
  → anonymization_completed → risk_detection_started → risk_detection_completed
  → autofill_started → autofill_completed → form_review_started
  → [field_edited …] → form_exported | task_abandoned

Tasks can fail at any stage. Events within a task have monotonically
increasing timestamps. Not every task generates every event.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from fxfill_analytics.generation.distributions import weighted_choice

# ── Event pipeline definition ──
# Each stage has: event_name, is_optional, failure_point (can task fail here?)
PIPELINE_STAGES: list[dict[str, Any]] = [
    {"event_name": "document_uploaded", "is_optional": False, "failure_point": False},
    {"event_name": "ocr_started", "is_optional": False, "failure_point": False},
    {"event_name": "ocr_completed", "is_optional": False, "failure_point": True},
    {"event_name": "anonymization_started", "is_optional": False, "failure_point": False},
    {"event_name": "anonymization_completed", "is_optional": False, "failure_point": True},
    {"event_name": "risk_detection_started", "is_optional": False, "failure_point": False},
    {"event_name": "risk_detection_completed", "is_optional": False, "failure_point": True},
    {"event_name": "autofill_started", "is_optional": False, "failure_point": False},
    {"event_name": "autofill_completed", "is_optional": False, "failure_point": True},
    {"event_name": "form_review_started", "is_optional": False, "failure_point": False},
    {"event_name": "form_exported", "is_optional": False, "failure_point": False},
]

# Stages where an agent_run_failed event replaces the completion event
FAILURE_REPLACEMENTS: dict[str, str] = {
    "ocr_completed": "agent_run_failed",
    "anonymization_completed": "agent_run_failed",
    "risk_detection_completed": "agent_run_failed",
    "autofill_completed": "agent_run_failed",
}

# Stages before which a user might abandon the task
ABANDONMENT_POINTS = {"form_review_started"}

# ── Enum constants (task pipeline events only; signup is in users table) ──
EVENT_NAMES = [
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

EVENT_STATUSES = ["success", "failure", "pending"]
STATUS_WEIGHTS = [0.85, 0.08, 0.07]

PLATFORMS = ["web", "api"]
PLATFORM_WEIGHTS = [0.80, 0.20]

APP_VERSIONS = ["2.1.0", "2.2.0", "2.3.0"]
VERSION_WEIGHTS = [0.30, 0.50, 0.20]

ERROR_TYPES = [None, "timeout", "parse_error", "validation_error"]
ERROR_WEIGHTS = [0.92, 0.03, 0.03, 0.02]


def _generate_task_events(
    rng: np.random.Generator,
    task_id: str,
    user_id: str,
    session_id: str,
    document_id: str,
    task_start: datetime,
    failure_rate: float,
    abandonment_rate: float,
    app_version: str,
    platform: str,
    experiment_id: str | None,
    experiment_group: str | None,
    phenomena_config: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Generate the event sequence for a single task.

    The task proceeds through PIPELINE_STAGES in order. At each failure_point,
    there is a chance the task fails (agent_run_failed) and stops. At the
    review stage, there is a chance of abandonment (task_abandoned).

    Returns a list of event dicts.
    """
    events: list[dict[str, Any]] = []
    current_time = task_start
    # Base gap between events: 0.5–5 seconds
    min_gap = timedelta(milliseconds=500)
    max_gap = timedelta(seconds=5)

    fail_at_stage: int | None = None
    abandon: bool = False

    for idx, stage in enumerate(PIPELINE_STAGES):
        event_name = stage["event_name"]

        # If we already failed, stop
        if fail_at_stage is not None:
            break

        # Check for failure at failure points
        if stage["failure_point"] and rng.random() < failure_rate:
            fail_at_stage = idx
            # Add a failure event instead of the normal completion
            fail_event = FAILURE_REPLACEMENTS.get(event_name, "agent_run_failed")
            current_time += timedelta(
                milliseconds=float(
                    rng.uniform(min_gap.total_seconds() * 1000, max_gap.total_seconds() * 1000)
                )
            )
            events.append(
                {
                    "event_name": fail_event,
                    "event_time": current_time,
                    "event_status": "failure",
                    "error_type": rng.choice(["ocr_error", "timeout", "api_error", "parse_error"]),
                    "latency_ms": 0,
                }
            )
            break

        # Check for abandonment at review
        if event_name in ABANDONMENT_POINTS and rng.random() < abandonment_rate:
            abandon = True

        # Add the normal event
        current_time += timedelta(
            milliseconds=float(
                rng.uniform(min_gap.total_seconds() * 1000, max_gap.total_seconds() * 1000)
            )
        )

        # Determine latency for this event
        latency = max(int(rng.normal(500, 200)), 0)

        events.append(
            {
                "event_name": event_name,
                "event_time": current_time,
                "event_status": "success",
                "error_type": None,
                "latency_ms": latency,
            }
        )

        # If abandoned at review, stop pipeline (do not generate form_exported)
        if abandon:
            break

    # If the task wasn't exported (abandoned at review)
    if abandon and fail_at_stage is None:
        current_time += timedelta(milliseconds=float(rng.uniform(1000, 10000)))
        events.append(
            {
                "event_name": "task_abandoned",
                "event_time": current_time,
                "event_status": "success",
                "error_type": None,
                "latency_ms": 0,
            }
        )

    # Add field_edited events (0-3) between review_started and export
    # Find the position after form_review_started
    review_idx = None
    for i, e in enumerate(events):
        if e["event_name"] == "form_review_started":
            review_idx = i
            break

    if review_idx is not None and not abandon and fail_at_stage is None:
        n_edits = rng.poisson(1)
        if n_edits > 0:
            # Insert field_edited events after review
            insert_pos = review_idx + 1
            for _ in range(n_edits):
                current_time += timedelta(milliseconds=float(rng.uniform(2000, 15000)))
                edit_event = {
                    "event_name": "field_edited",
                    "event_time": current_time,
                    "event_status": "success",
                    "error_type": None,
                    "latency_ms": max(int(rng.normal(300, 100)), 0),
                }
                events.insert(insert_pos, edit_event)
                insert_pos += 1

    # Fill in common fields for all events
    for e in events:
        e.update(
            {
                "task_id": task_id,
                "user_id": user_id,
                "session_id": session_id,
                "document_id": document_id,
                "platform": platform,
                "app_version": app_version,
                "experiment_id": experiment_id,
                "experiment_group": experiment_group,
            }
        )

    return events


def generate_product_events(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    session_ids: list[str],
    doc_ids: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    event_names: list[str] | None = None,
    app_versions: list[str] | None = None,
    version_weights: list[float] | None = None,
    platforms: list[str] | None = None,
    platform_weights: list[float] | None = None,
    error_types: list[str | None] | None = None,
    error_weights: list[float] | None = None,
    mean_latency_ms: float = 500.0,
    latency_std_ms: float = 200.0,
    experiment_id: str | None = "EXP001",
    experiment_fraction: float = 0.10,
    failure_rate: float = 0.12,
    abandonment_rate: float = 0.15,
    phenomena_config: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """
    Generate synthetic product events with realistic task pipelines.

    Tasks are created from documents. Each task follows the event pipeline
    with configurable failure and abandonment rates. Not all tasks complete.

    Args:
        rng: Seeded NumPy random generator.
        count: Target number of events (actual may vary due to task pipeline).
        user_ids: Pool of user IDs.
        session_ids: Pool of session IDs.
        doc_ids: Pool of document IDs.
        start_date: Earliest event timestamp.
        end_date: Latest event timestamp.
        failure_rate: Per-failure-point failure probability.
        abandonment_rate: Probability of task abandonment at review.
        phenomena_config: Optional phenomena configuration dict.

    Returns:
        DataFrame with event_id, timestamps, foreign keys, and metadata.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if not user_ids:
        raise ValueError("user_ids must not be empty")
    if not doc_ids:
        raise ValueError("doc_ids must not be empty")
    if not session_ids:
        raise ValueError("session_ids must not be empty")

    app_versions = app_versions or APP_VERSIONS
    version_weights = version_weights or VERSION_WEIGHTS
    platforms = platforms or PLATFORMS
    platform_weights = platform_weights or PLATFORM_WEIGHTS
    error_types = error_types or ERROR_TYPES
    error_weights = error_weights or ERROR_WEIGHTS

    # ── Create tasks (one per document, limited by count) ──
    # Estimate: ~8-9 events per task on average (some fail, some complete)
    avg_events_per_task = 8.0
    n_tasks = max(int(count / avg_events_per_task), 1)
    # Cap tasks to available documents
    n_tasks = min(n_tasks, len(doc_ids))

    task_ids = [f"TSK_{i:06d}" for i in range(1, n_tasks + 1)]

    # Assign docs to tasks (each doc gets at most one task)
    task_doc_ids = list(rng.choice(doc_ids, size=n_tasks, replace=False))
    # Assign users and sessions
    task_user_ids = list(rng.choice(user_ids, size=n_tasks))
    task_session_ids = list(rng.choice(session_ids, size=n_tasks))
    # Task start times distributed across the date range
    total_seconds = (end_date - start_date).total_seconds()
    task_starts = [
        start_date + timedelta(seconds=float(s))
        for s in np.sort(rng.uniform(0, total_seconds, size=n_tasks))
    ]
    # App versions and platforms per task
    task_versions = weighted_choice(rng, app_versions, version_weights, n_tasks)
    task_platforms = weighted_choice(rng, platforms, platform_weights, n_tasks)

    # Experiment assignment per task
    task_exp_id: list[str | None] = []
    task_exp_group: list[str | None] = []
    for _ in range(n_tasks):
        if rng.random() < experiment_fraction:
            task_exp_id.append(experiment_id)
            task_exp_group.append(rng.choice(["A", "B"]))
        else:
            task_exp_id.append(None)
            task_exp_group.append(None)

    # ── Generate events for each task ──
    all_events: list[dict[str, Any]] = []
    for i in range(n_tasks):
        task_events = _generate_task_events(
            rng,
            task_id=task_ids[i],
            user_id=task_user_ids[i],
            session_id=task_session_ids[i],
            document_id=task_doc_ids[i],
            task_start=task_starts[i],
            failure_rate=failure_rate,
            abandonment_rate=abandonment_rate,
            app_version=task_versions[i],
            platform=task_platforms[i],
            experiment_id=task_exp_id[i],
            experiment_group=task_exp_group[i],
            phenomena_config=phenomena_config,
        )
        all_events.extend(task_events)

    # ── Build DataFrame ──
    n_events = len(all_events)
    event_ids = [f"EVT_{i:07d}" for i in range(1, n_events + 1)]

    df = pd.DataFrame(all_events)
    df.insert(0, "event_id", event_ids)

    # Ensure event_date column
    df["event_date"] = df["event_time"].apply(lambda t: t.date() if t is not pd.NaT else None)

    # Add metadata
    df["metadata_json"] = r'{"source":"synthetic"}'

    # Fill missing columns for consistency
    if "latency_ms" not in df.columns:
        df["latency_ms"] = 0

    return df
