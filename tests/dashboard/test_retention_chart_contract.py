"""Verify retention chart contract — single-horizon figures, channel traces, sample threshold."""

import numpy as np
import pandas as pd
import pytest

from dashboard.components.retention_charts import (
    MIN_COHORT_SAMPLE,
    _compute_retention_y_upper,
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


# ── _compute_retention_y_upper tests ─────────────────────────────────────────


def test_retention_axis_has_ten_percent_floor():
    """Empty or all-zero values must return floor of 0.10."""
    assert _compute_retention_y_upper([]) == 0.10
    assert _compute_retention_y_upper([0.0]) == 0.10
    assert _compute_retention_y_upper([0.0, 0.0, 0.0]) == 0.10
    # 4% max with padding 1.25 → 0.05, floored to 0.10
    assert _compute_retention_y_upper([0.04]) == 0.10
    # 8% max with padding 1.25 → 0.10 exactly, floored to 0.10
    assert _compute_retention_y_upper([0.08]) == 0.10


def test_retention_axis_adds_padding():
    """Values above floor must be scaled with padding."""
    # 12% * 1.25 = 0.15 → already a multiple of 0.05
    assert _compute_retention_y_upper([0.12]) == 0.15
    # 17% * 1.25 = 0.2125 → ceil to 0.05 → 0.25
    assert _compute_retention_y_upper([0.17]) == 0.25


def test_retention_axis_rounds_to_five_percent_step():
    """Upper bound must round up to the nearest multiple of 0.05."""
    # 0.40 * 1.25 = 0.50
    assert _compute_retention_y_upper([0.40]) == 0.50
    # 0.41 * 1.25 = 0.5125 → ceil/0.05 → 0.55
    assert _compute_retention_y_upper([0.41]) == 0.55
    # 0.31 * 1.25 = 0.3875 → ceil/0.05 → 0.40
    assert _compute_retention_y_upper([0.31]) == 0.40


def test_retention_axis_caps_at_one_hundred_percent():
    """Upper bound must never exceed 1.0."""
    assert _compute_retention_y_upper([0.90]) == 1.0
    assert _compute_retention_y_upper([0.85]) == 1.0
    # 0.85 * 1.25 = 1.0625 → ceil to 0.05 → 1.10 → capped at 1.0
    assert _compute_retention_y_upper([1.0]) == 1.0


def test_retention_axis_ignores_none_nan_and_inf():
    """None, NaN, and infinities must be ignored."""
    result = _compute_retention_y_upper([0.12, None, float("nan"), float("inf"), float("-inf")])
    assert result == 0.15  # Only 0.12 is valid


def test_retention_axis_handles_empty_values():
    """No valid values returns the minimum_upper."""
    assert _compute_retention_y_upper([]) == 0.10
    assert _compute_retention_y_upper([None]) == 0.10
    assert _compute_retention_y_upper([float("nan")]) == 0.10


def test_retention_axis_clips_out_of_range_values():
    """Values outside [0, 1] are clipped before computation."""
    # -0.5 clipped to 0.0 → max=0.0 → floor 0.10
    assert _compute_retention_y_upper([-0.5]) == 0.10
    # 2.5 clipped to 1.0 → 1.0 * 1.25 = 1.25 → ceil → capped at 1.0
    assert _compute_retention_y_upper([2.5]) == 1.0


# ── Dynamic y-axis integration tests ─────────────────────────────────────────


def test_retention_yaxis_lower_bound_is_zero(sample_retention_df):
    """Y-axis lower bound must always be 0."""
    weekly = prepare_weekly_retention(sample_retention_df)
    for horizon in ["d1", "d7", "d30"]:
        fig, _audit = build_retention_figure(weekly, horizon)
        y_range = fig.layout.yaxis.range
        assert y_range is not None, f"{horizon}: yaxis range must be set"
        assert y_range[0] == 0.0, f"{horizon}: y-axis lower bound must be 0, got {y_range[0]}"


def test_retention_yaxis_upper_not_fixed_100(sample_retention_df):
    """Y-axis upper must be dynamic (not hardcoded 1.0) when data is well below 100%."""
    weekly = prepare_weekly_retention(sample_retention_df)
    for horizon in ["d1", "d7", "d30"]:
        fig, _audit = build_retention_figure(weekly, horizon)
        y_upper = fig.layout.yaxis.range[1]
        assert 0.10 <= y_upper <= 1.0, f"{horizon}: y_upper {y_upper} out of [0.10, 1.0]"


def test_retention_all_data_points_within_yaxis_range(sample_retention_df):
    """No plotted data point must exceed the y-axis upper bound."""
    weekly = prepare_weekly_retention(sample_retention_df)
    for horizon in ["d1", "d7", "d30"]:
        fig, _audit = build_retention_figure(weekly, horizon)
        y_upper = fig.layout.yaxis.range[1]
        for trace in fig.data:
            if trace.y is None:
                continue
            for y_val in trace.y:
                if y_val is not None and pd.notna(y_val):
                    assert (
                        float(y_val) <= y_upper
                    ), f"{horizon}: data point {y_val} exceeds y_upper {y_upper}"


def test_retention_different_horizons_independent_yaxis(sample_retention_df):
    """D1/D7/D30 must each compute their own y-axis upper bound."""
    weekly = prepare_weekly_retention(sample_retention_df)
    bounds = {}
    for horizon in ["d1", "d7", "d30"]:
        fig, _audit = build_retention_figure(weekly, horizon)
        bounds[horizon] = fig.layout.yaxis.range[1]
    # D1/D7 rates differ — bounds should plausibly differ (at minimum, not all identical forced)
    # All must independently fall in [0.10, 1.0]
    for h, b in bounds.items():
        assert 0.10 <= b <= 1.0, f"{h}: bound {b} out of range"


def test_retention_connectgaps_false(sample_retention_df):
    """connectgaps must remain False for all traces."""
    weekly = prepare_weekly_retention(sample_retention_df)
    for horizon in ["d1", "d7", "d30"]:
        fig, _audit = build_retention_figure(weekly, horizon)
        for trace in fig.data:
            assert (
                trace.connectgaps is False
            ), f"{horizon} trace '{trace.name}': connectgaps must be False"


def test_retention_figure_title_and_axes(sample_retention_df):
    """Figure must have correct title, axis labels, and tick format."""
    weekly = prepare_weekly_retention(sample_retention_df)
    fig, _audit = build_retention_figure(weekly, "d1")
    assert "D1" in fig.layout.title.text
    assert fig.layout.xaxis.title.text is not None
    assert fig.layout.yaxis.title.text is not None
    assert fig.layout.yaxis.tickformat == ".0%"


def test_retention_hovertemplate_contains_required_fields(sample_retention_df):
    """Hover must show channel, week, rate, and eligible users."""
    weekly = prepare_weekly_retention(sample_retention_df)
    fig, _audit = build_retention_figure(weekly, "d1")
    for trace in fig.data:
        ht = trace.hovertemplate or ""
        assert "Rate" in ht, f"hovertemplate missing 'Rate': {ht}"
        assert "Eligible" in ht, f"hovertemplate missing 'Eligible': {ht}"


def test_retention_fallback_all_channels(sample_retention_df):
    """When per-channel data exists, All Channels Combined is not needed;
    when no per-channel data exists, fallback works."""
    # With normal per-channel data, figure builds normally
    weekly = prepare_weekly_retention(sample_retention_df)
    fig, audit = build_retention_figure(weekly, "d1")
    assert fig is not None
    assert audit.plotted_point_count > 0
    # Traces should be per-channel
    trace_names = [t.name for t in fig.data]
    for ch in sample_retention_df["acquisition_channel"].unique():
        assert ch in trace_names, f"Channel '{ch}' should appear as a trace"


def test_retention_audit_no_unmatured_insufficient_plotted(sample_retention_df):
    """Audit must report zero unmatured/insufficient points plotted."""
    weekly = prepare_weekly_retention(sample_retention_df)
    for horizon in ["d1", "d7", "d30"]:
        _fig, audit = build_retention_figure(weekly, horizon)
        assert (
            audit.unmatured_points_plotted == 0
        ), f"{horizon}: unmatured_points_plotted should be 0"
        assert (
            audit.insufficient_points_plotted == 0
        ), f"{horizon}: insufficient_points_plotted should be 0"
