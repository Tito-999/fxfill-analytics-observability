"""
Synthetic user dimension table generation.

Generates users with acquisition channels, device types, segments,
experience levels, and signup timestamps. All random processes use
a NumPy Generator with fixed seed for reproducibility.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from fxfill_analytics.generation.distributions import random_bool, weighted_choice
from fxfill_analytics.utils.dates import generate_timestamps

# ── Enum constants ──
ACQUISITION_CHANNELS = ["organic", "paid_search", "social", "referral", "campus"]
DEVICE_TYPES = ["desktop", "mobile", "tablet"]
USER_SEGMENTS = ["student", "individual", "small_business", "enterprise_trial"]
EXPERIENCE_LEVELS = ["new", "intermediate", "expert"]
COUNTRIES = ["US", "GB", "DE", "JP", "CN", "SG", "AU", "BR"]
COMPANY_SIZES = ["1-50", "51-200", "201-500", "501-1000", "1000+"]

# ── Default probability weights ──
CHANNEL_WEIGHTS = [0.35, 0.25, 0.20, 0.15, 0.05]
DEVICE_WEIGHTS = [0.60, 0.30, 0.10]
SEGMENT_WEIGHTS = [0.20, 0.35, 0.30, 0.15]
EXPERIENCE_WEIGHTS = [0.45, 0.35, 0.20]


def generate_users(
    rng: np.random.Generator,
    count: int,
    start_date: datetime,
    end_date: datetime,
    *,
    channels: list[str] | None = None,
    channel_weights: list[float] | None = None,
    devices: list[str] | None = None,
    device_weights: list[float] | None = None,
    segments: list[str] | None = None,
    segment_weights: list[float] | None = None,
    experience_levels: list[str] | None = None,
    experience_weights: list[float] | None = None,
    returning_user_rate: float = 0.30,
) -> pd.DataFrame:
    """
    Generate a synthetic user dimension table.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of users to generate.
        start_date: Earliest signup timestamp (inclusive).
        end_date: Latest signup timestamp (exclusive).
        channels: Acquisition channel options.
        channel_weights: Probability weights for channels.
        devices: Device type options.
        device_weights: Probability weights for devices.
        segments: User segment options.
        segment_weights: Probability weights for segments.
        experience_levels: Experience level options.
        experience_weights: Probability weights for experience levels.
        returning_user_rate: Fraction of users marked as returning.

    Returns:
        DataFrame with user_id, signup_time, and dimension columns.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")

    channels = channels or ACQUISITION_CHANNELS
    channel_weights = channel_weights or CHANNEL_WEIGHTS
    devices = devices or DEVICE_TYPES
    device_weights = device_weights or DEVICE_WEIGHTS
    segments = segments or USER_SEGMENTS
    segment_weights = segment_weights or SEGMENT_WEIGHTS
    experience_levels = experience_levels or EXPERIENCE_LEVELS
    experience_weights = experience_weights or EXPERIENCE_WEIGHTS

    user_ids = [f"U{i:06d}" for i in range(1, count + 1)]
    signup_times = generate_timestamps(rng, start_date, end_date, count)

    return pd.DataFrame(
        {
            "user_id": user_ids,
            "signup_time": signup_times,
            "acquisition_channel": weighted_choice(rng, channels, channel_weights, count),
            "country": list(rng.choice(COUNTRIES, size=count)),
            "device_type": weighted_choice(rng, devices, device_weights, count),
            "user_segment": weighted_choice(rng, segments, segment_weights, count),
            "company_size": list(rng.choice(COMPANY_SIZES, size=count)),
            "experience_level": weighted_choice(rng, experience_levels, experience_weights, count),
            "is_returning_user": random_bool(rng, returning_user_rate, count),
        }
    )
