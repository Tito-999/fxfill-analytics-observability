"""
Synthetic product event fact table generation.

Generates event streams with realistic task pipelines:
  document_uploaded → ocr_started → ocr_completed → anonymization →
  risk_detection → autofill → form_review → form_exported / task_abandoned

Not all tasks complete the full pipeline — some fail mid-way.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from fxfill_analytics.generation.distributions import weighted_choice
from fxfill_analytics.utils.dates import generate_timestamps

# ── Enum constants ──
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

EVENT_STATUSES = ["success", "failure", "pending"]
STATUS_WEIGHTS = [0.85, 0.08, 0.07]

PLATFORMS = ["web", "api"]
PLATFORM_WEIGHTS = [0.80, 0.20]

APP_VERSIONS = ["2.1.0", "2.2.0", "2.3.0"]
VERSION_WEIGHTS = [0.30, 0.50, 0.20]

ERROR_TYPES = [None, "timeout", "parse_error", "validation_error"]
ERROR_WEIGHTS = [0.92, 0.03, 0.03, 0.02]


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
) -> pd.DataFrame:
    """
    Generate a synthetic product event fact table.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of events to generate.
        user_ids: Pool of user IDs.
        session_ids: Pool of session IDs.
        doc_ids: Pool of document IDs.
        start_date: Earliest event timestamp (inclusive).
        end_date: Latest event timestamp (exclusive).
        event_names: Event name options.
        app_versions: App version options.
        version_weights: Probability weights for app versions.
        platforms: Platform options.
        platform_weights: Probability weights for platforms.
        error_types: Error type options (None = no error).
        error_weights: Probability weights for error types.
        mean_latency_ms: Mean event latency in milliseconds.
        latency_std_ms: Std dev of event latency in milliseconds.
        experiment_id: Experiment identifier for events in experiment.
        experiment_fraction: Fraction of events assigned to an experiment.

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

    event_names = event_names or EVENT_NAMES
    app_versions = app_versions or APP_VERSIONS
    version_weights = version_weights or VERSION_WEIGHTS
    platforms = platforms or PLATFORMS
    platform_weights = platform_weights or PLATFORM_WEIGHTS
    error_types = error_types or ERROR_TYPES
    error_weights = error_weights or ERROR_WEIGHTS

    n = count
    event_ids = [f"EVT{i:07d}" for i in range(1, n + 1)]

    timestamps = generate_timestamps(rng, start_date, end_date, n)

    # Assign events to tasks — each task gets a sequence of events
    n_tasks = max(n // 4, 1)
    task_ids = [f"TSK{i:06d}" for i in range(1, n_tasks + 1)]

    # Generate latency as normal distribution, clamped to non-negative
    latencies = np.maximum(rng.normal(mean_latency_ms, latency_std_ms, size=n).astype(int), 0)

    return pd.DataFrame(
        {
            "event_id": event_ids,
            "event_time": timestamps,
            "event_date": [t.date() for t in timestamps],
            "user_id": list(rng.choice(user_ids, size=n)),
            "session_id": list(rng.choice(session_ids, size=n)),
            "document_id": list(rng.choice(doc_ids, size=n)),
            "task_id": list(rng.choice(task_ids, size=n)),
            "event_name": weighted_choice(
                rng, event_names, [1.0 / len(event_names)] * len(event_names), n
            ),
            "event_status": weighted_choice(rng, EVENT_STATUSES, STATUS_WEIGHTS, n),
            "platform": weighted_choice(rng, platforms, platform_weights, n),
            "app_version": weighted_choice(rng, app_versions, version_weights, n),
            "experiment_id": [
                experiment_id if rng.random() < experiment_fraction else None for _ in range(n)
            ],
            "experiment_group": [
                rng.choice(["A", "B"]) if rng.random() < experiment_fraction else None
                for _ in range(n)
            ],
            "latency_ms": list(latencies),
            "error_type": weighted_choice(rng, error_types, [float(w) for w in error_weights], n),
            "metadata_json": [r'{"source":"synthetic"}' for _ in range(n)],
        }
    )
