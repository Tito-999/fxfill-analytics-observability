"""
Synthetic session dimension table generation.

Each session belongs to a user, has a start/end timestamp,
device info, and a session-level channel attribution.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from fxfill_analytics.generation.distributions import random_bool, weighted_choice
from fxfill_analytics.utils.dates import generate_timestamps

# ── Enum constants ──
DEVICE_TYPES = ["desktop", "mobile", "tablet"]
PLATFORMS = ["web", "api"]
ACQUISITION_CHANNELS = ["organic", "paid_search", "social", "referral", "campus"]

# ── Default probability weights ──
DEVICE_WEIGHTS = [0.60, 0.30, 0.10]
PLATFORM_WEIGHTS = [0.80, 0.20]
CHANNEL_WEIGHTS = [0.35, 0.25, 0.20, 0.15, 0.05]


def generate_sessions(
    rng: np.random.Generator,
    count: int,
    user_ids: list[str],
    start_date: datetime,
    end_date: datetime,
    *,
    devices: list[str] | None = None,
    device_weights: list[float] | None = None,
    platforms: list[str] | None = None,
    platform_weights: list[float] | None = None,
    channels: list[str] | None = None,
    channel_weights: list[float] | None = None,
    mean_session_minutes: float = 15.0,
    bounce_rate: float = 0.10,
) -> pd.DataFrame:
    """
    Generate a synthetic session dimension table.

    Args:
        rng: Seeded NumPy random generator.
        count: Number of sessions to generate.
        user_ids: Pool of user IDs for session assignment.
        start_date: Earliest session start (inclusive).
        end_date: Latest session start (exclusive).
        devices: Device type options.
        device_weights: Probability weights for devices.
        platforms: Platform options.
        platform_weights: Probability weights for platforms.
        channels: Acquisition channel options.
        channel_weights: Probability weights for channels.
        mean_session_minutes: Mean session duration in minutes.
        bounce_rate: Fraction of single-page (bounced) sessions.

    Returns:
        DataFrame with session_id, user_id, timestamps, and dimension columns.
    """
    if count <= 0:
        raise ValueError(f"count must be positive, got {count}")
    if not user_ids:
        raise ValueError("user_ids must not be empty")

    devices = devices or DEVICE_TYPES
    device_weights = device_weights or DEVICE_WEIGHTS
    platforms = platforms or PLATFORMS
    platform_weights = platform_weights or PLATFORM_WEIGHTS
    channels = channels or ACQUISITION_CHANNELS
    channel_weights = channel_weights or CHANNEL_WEIGHTS

    session_ids = [f"SES{i:07d}" for i in range(1, count + 1)]
    started_ats = generate_timestamps(rng, start_date, end_date, count)

    # Session durations: exponential distribution with given mean (in minutes)
    durations_min = rng.exponential(mean_session_minutes, size=count)
    # Bounced sessions have very short duration
    is_bounced = random_bool(rng, bounce_rate, count)
    durations_min[is_bounced] = rng.uniform(0.1, 1.0, size=int(is_bounced.sum()))

    ended_ats = [started_ats[i] + timedelta(minutes=float(durations_min[i])) for i in range(count)]

    return pd.DataFrame(
        {
            "session_id": session_ids,
            "user_id": list(rng.choice(user_ids, size=count)),
            "started_at": started_ats,
            "ended_at": ended_ats,
            "device_type": weighted_choice(rng, devices, device_weights, count),
            "platform": weighted_choice(rng, platforms, platform_weights, count),
            "acquisition_channel": weighted_choice(rng, channels, channel_weights, count),
            "is_bounced": list(is_bounced),
            "page_views": list(np.maximum(rng.poisson(4, size=count), 1)),
        }
    )
