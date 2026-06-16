"""
Synthetic A/B test experiment assignment generation.

Each user in the experiment is assigned to exactly one group (A or B).
By default there is no cross-contamination — that is injected as a
configurable anomaly in Phase 1.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from fxfill_analytics.utils.dates import generate_timestamps

EXPERIMENT_GROUPS = ["A", "B"]


def generate_experiment_assignments(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    experiment_id: str = "EXP001",
) -> pd.DataFrame:
    """
    Generate synthetic experiment assignment records.

    Each user is assigned to exactly one group. No user appears more than once.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of users to assign (must be ≤ len(user_ids)).
        user_ids: Pool of user IDs (sampled without replacement).
        start_date: Earliest assignment timestamp (inclusive).
        end_date: Latest assignment timestamp (exclusive).
        experiment_id: Experiment identifier.

    Returns:
        DataFrame with experiment_id, user_id, experiment_group, assigned_at.

    Raises:
        ValueError: If count exceeds available user_ids.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if count > len(user_ids):
        raise ValueError(f"count ({count}) must not exceed available user_ids ({len(user_ids)})")

    assigned_users = list(rng.choice(user_ids, size=count, replace=False))
    assigned_ats = generate_timestamps(rng, start_date, end_date, count)

    return pd.DataFrame(
        {
            "experiment_id": [experiment_id] * count,
            "user_id": assigned_users,
            "experiment_group": list(rng.choice(EXPERIMENT_GROUPS, size=count)),
            "assigned_at": assigned_ats,
        }
    )
