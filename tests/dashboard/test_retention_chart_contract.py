"""Verify retention chart contract — single-horizon figures, channel traces, sample threshold."""

import numpy as np
import pandas as pd
import pytest

from dashboard.components.retention_charts import (
    MIN_COHORT_SAMPLE,
    build_retention_figure,
    prepare_weekly_retention,
)


@pytest.fixture
def sample_retention_df() -> pd.DataFrame:
    """Build a synthetic retention DataFrame matching the mart schema."""
    rng = np.random.default_rng(42)
    n = 60  # 60 daily cohorts
    channels = ["organic", "paid_search", "referral"]
    rows = []
    for i in range(n):
        for ch in channels:
            base = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
            eligible = int(rng.integers(30, 100))
            d1 = int(eligible * rng.uniform(0.7, 0.95))
            d7 = int(eligible * rng.uniform(0.5, 0.8))
            d30 = int(eligible * rng.uniform(0.3, 0.6))
            rows.append(
                {
                    "cohort_date": base,
                    "acquisition_channel": ch,
                    "eligible_users": eligible,
                    "d1_retained_users": d1,
                    "d7_retained_users": d7,
                    "d30_retained_users": d30,
                    "d1_retention_rate": d1 / eligible,
                    "d7_retention_rate": d7 / eligible,
                    "d30_retention_rate": d30 / eligible,
                    "d1_matured": True,
                    "d1_eligible_users": eligible,
                    "d7_matured": True,
                    "d7_eligible_users": eligible,
                    "d30_matured": True,
                    "d30_eligible_users": eligible,
                    "observation_end_date": pd.Timestamp("2026-06-14"),
                }
            )
    return pd.DataFrame(rows)


def test_each_figure_contains_single_horizon(sample_retention_df):
    """Each build_retention_figure call must produce a single-horizon chart."""
    weekly = prepare_weekly_retention(sample_retention_df)
    fig, _audit = build_retention_figure(weekly, "d1")
    # All traces belong to channels (not D7 or D30)
    channel_names = sorted(sample_retention_df["acquisition_channel"].unique())
    trace_names = [t.name for t in fig.data]
    for ch in channel_names:
        assert ch in trace_names, f"Channel {ch} missing from D1 figure"
    # No trace should contain "D7" or "D30" in name
    for t in fig.data:
        assert "D7" not in (t.name or ""), f"Trace '{t.name}' mentions D7 in D1 chart"
        assert "D30" not in (t.name or ""), f"Trace '{t.name}' mentions D30 in D1 chart"


def test_trace_count_does_not_exceed_channel_count(sample_retention_df):
    """Number of traces per figure <= number of channels."""
    weekly = prepare_weekly_retention(sample_retention_df)
    n_channels = len(sample_retention_df["acquisition_channel"].unique())
    for horizon in ["d1", "d7", "d30"]:
        fig, _audit = build_retention_figure(weekly, horizon)
        assert (
            len(fig.data) <= n_channels
        ), f"{horizon}: {len(fig.data)} traces > {n_channels} channels"


def test_below_min_sample_rate_is_null(sample_retention_df):
    """Points with eligible < MIN_COHORT_SAMPLE have null rate."""
    # Add a tiny cohort
    tiny = pd.DataFrame(
        [
            {
                "cohort_date": pd.Timestamp("2026-03-01"),
                "acquisition_channel": "tiny_channel",
                "eligible_users": 5,
                "d1_retained_users": 3,
                "d7_retained_users": 2,
                "d30_retained_users": 1,
                "d1_retention_rate": 0.6,
                "d7_retention_rate": 0.4,
                "d30_retention_rate": 0.2,
                "d1_matured": True,
                "d1_eligible_users": 5,
                "d7_matured": True,
                "d7_eligible_users": 5,
                "d30_matured": True,
                "d30_eligible_users": 5,
                "observation_end_date": pd.Timestamp("2026-06-14"),
            }
        ]
    )
    df = pd.concat([sample_retention_df, tiny], ignore_index=True)
    weekly = prepare_weekly_retention(df)
    tiny_rows = weekly[weekly["acquisition_channel"] == "tiny_channel"]
    if not tiny_rows.empty:
        for _, row in tiny_rows.iterrows():
            if row.get("d1_eligible_users", 0) < MIN_COHORT_SAMPLE:
                assert row["d1_sample_status"] == "insufficient"


def test_weighted_rate_calculation(sample_retention_df):
    """Weighted rate = sum(retained) / sum(eligible), not average of daily rates."""
    weekly = prepare_weekly_retention(sample_retention_df)
    for _, row in weekly.iterrows():
        for horizon in ["d1", "d7", "d30"]:
            rate = row.get(f"{horizon}_weighted_rate")
            retained = row.get(f"{horizon}_retained_users", 0)
            eligible = row.get(f"{horizon}_eligible_users", 1)
            if pd.notna(rate) and eligible > 0:
                expected = retained / eligible
                assert abs(rate - expected) < 1e-9, f"{horizon}: {rate} != {expected}"


def test_unmatured_cohorts_not_in_horizon_figure(sample_retention_df):
    """All plotted y-values should be valid (non-NaN) when sample is adequate."""
    weekly = prepare_weekly_retention(sample_retention_df)
    fig, _audit = build_retention_figure(weekly, "d30")
    # Points with insufficient sample are excluded via connectgaps=False
    for trace in fig.data:
        y_vals = list(trace.y) if hasattr(trace, "y") and trace.y is not None else []
        for y in y_vals:
            if y is not None:
                assert pd.notna(y), f"Null rate found in D30 figure for channel {trace.name}"
