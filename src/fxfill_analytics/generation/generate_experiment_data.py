"""
Synthetic A/B test experiment assignment generation.

Each assignment has a unique assignment_id (physical PK).
The business key is (experiment_id, user_id), which is normally unique.
P08 creates intentional contamination by duplicating (experiment_id, user_id)
with different groups.
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

    Each row has a unique assignment_id. Normally (experiment_id, user_id)
    is unique, but P08 can inject contamination duplicates.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of users to assign (must be ≤ len(user_ids)).
        user_ids: Pool of user IDs (sampled without replacement).
        start_date: Earliest assignment timestamp (inclusive).
        end_date: Latest assignment timestamp (exclusive).
        experiment_id: Experiment identifier.

    Returns:
        DataFrame with assignment_id, experiment_id, user_id,
        experiment_group, assigned_at, is_intentional_contamination.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if count > len(user_ids):
        raise ValueError(f"count ({count}) must not exceed available user_ids ({len(user_ids)})")

    assigned_users = list(rng.choice(user_ids, size=count, replace=False))
    assigned_ats = generate_timestamps(rng, start_date, end_date, count)
    groups = list(rng.choice(EXPERIMENT_GROUPS, size=count))

    return pd.DataFrame(
        {
            "assignment_id": [f"ASGN_{i:07d}" for i in range(1, count + 1)],
            "experiment_id": [experiment_id] * count,
            "user_id": assigned_users,
            "experiment_group": groups,
            "assigned_at": assigned_ats,
            "is_intentional_contamination": [False] * count,
        }
    )
