"""
Deterministic date/time generation utilities.

All times are stored in UTC. Functions receive a NumPy random generator
for reproducibility.
"""

from datetime import datetime, timedelta, timezone

import numpy as np


def generate_timestamps(
    rng: np.random.Generator,
    start_date: datetime,
    end_date: datetime,
    count: int,
) -> list[datetime]:
    """
    Generate uniformly distributed timestamps within a date range.

    Args:
        rng: Seeded NumPy random generator.
        start_date: Earliest timestamp (inclusive).
        end_date: Latest timestamp (exclusive).
        count: Number of timestamps to generate.

    Returns:
        Sorted list of datetime objects (UTC).
    """
    if count == 0:
        return []

    total_seconds = (end_date - start_date).total_seconds()
    if total_seconds <= 0:
        raise ValueError(f"end_date ({end_date}) must be after start_date ({start_date})")

    # Generate random offsets in seconds
    offsets = rng.uniform(0, total_seconds, size=count)
    timestamps = [start_date + timedelta(seconds=float(o)) for o in offsets]
    return sorted(timestamps)


def date_range_daily(
    start_date: datetime,
    end_date: datetime,
) -> list[datetime]:
    """Generate a list of daily midnight datetimes."""
    days = (end_date.date() - start_date.date()).days
    return [
        datetime.combine(start_date.date() + timedelta(days=i), datetime.min.time(), tzinfo=timezone.utc)
        for i in range(days + 1)
    ]


def utc_now() -> datetime:
    """Return current UTC time (used for validation checks)."""
    return datetime.now(tz=timezone.utc)
