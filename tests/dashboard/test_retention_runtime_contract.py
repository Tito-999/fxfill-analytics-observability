"""Verify retention chart runtime contract."""

import pandas as pd
import pytest

from dashboard.components.retention_charts import (
    build_retention_figure,
    has_eligible_retention_points,
    prepare_weekly_retention,
)


def test_missing_maturity_columns_raises():
    """preparing with incomplete columns must raise ValueError."""
    df = pd.DataFrame(
        {
            "cohort_date": pd.to_datetime(["2026-01-01"]),
            "acquisition_channel": ["organic"],
        }
    )
    with pytest.raises(ValueError, match="Retention input contract is incomplete"):
        prepare_weekly_retention(df)


def test_full_contract_prepares():
    """Complete contract produces weekly aggregates without error."""
    df = pd.DataFrame(
        {
            "cohort_date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "acquisition_channel": ["organic", "organic"],
            "d1_matured": [True, True],
            "d1_eligible_users": [50, 60],
            "d1_retained_users": [45, 55],
            "d1_retention_rate": [0.9, 0.9167],
            "d7_matured": [True, True],
            "d7_eligible_users": [50, 60],
            "d7_retained_users": [40, 50],
            "d7_retention_rate": [0.8, 0.8333],
            "d30_matured": [False, False],
            "d30_eligible_users": [0, 0],
            "d30_retained_users": [0, 0],
            "d30_retention_rate": [None, None],
            "observation_end_date": [pd.Timestamp("2026-06-01"), pd.Timestamp("2026-06-01")],
        }
    )
    weekly = prepare_weekly_retention(df)
    assert not weekly.empty
    assert "d1_maturity_status" in weekly.columns
    assert "d7_maturity_status" in weekly.columns
    assert "d30_maturity_status" in weekly.columns


def test_unmatured_gives_no_points():
    """Unmatured horizon returns no eligible points."""
    df = pd.DataFrame(
        {
            "cohort_date": pd.to_datetime(["2026-05-30"]),
            "acquisition_channel": ["organic"],
            "d1_matured": [True],
            "d1_eligible_users": [50],
            "d1_retained_users": [45],
            "d1_retention_rate": [0.9],
            "d7_matured": [True],
            "d7_eligible_users": [50],
            "d7_retained_users": [40],
            "d7_retention_rate": [0.8],
            "d30_matured": [False],
            "d30_eligible_users": [0],
            "d30_retained_users": [0],
            "d30_retention_rate": [None],
            "observation_end_date": [pd.Timestamp("2026-06-01")],
        }
    )
    weekly = prepare_weekly_retention(df)
    assert not has_eligible_retention_points(
        weekly, "d30"
    ), "D30 should have no eligible points when unmatured"


def test_no_empty_traces_rendered():
    """build_retention_figure returns (None, 0) when no data exists."""
    df = pd.DataFrame(
        {
            "cohort_date": pd.to_datetime(["2026-06-01"]),
            "acquisition_channel": ["organic"],
            "d1_matured": [False],
            "d1_eligible_users": [0],
            "d1_retained_users": [0],
            "d1_retention_rate": [None],
            "d7_matured": [False],
            "d7_eligible_users": [0],
            "d7_retained_users": [0],
            "d7_retention_rate": [None],
            "d30_matured": [False],
            "d30_eligible_users": [0],
            "d30_retained_users": [0],
            "d30_retention_rate": [None],
            "observation_end_date": [pd.Timestamp("2026-06-01")],
        }
    )
    weekly = prepare_weekly_retention(df)
    fig, count = build_retention_figure(weekly, "d1")
    assert fig is None, "Should return None when no data to plot"
    assert count == 0
