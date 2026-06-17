"""Retention chart helpers — weekly weighted cohorts, horizon tabs, sample controls."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

MIN_COHORT_SAMPLE = 20


def prepare_weekly_retention(
    retention_df: pd.DataFrame,
    date_col: str = "cohort_date",
) -> pd.DataFrame:
    """Aggregate daily retention data into weekly cohorts with weighted rates.

    Each row in *retention_df* is a daily cohort × channel observation.
    Returns a DataFrame with columns:
        cohort_week, acquisition_channel,
        d1_eligible_users, d7_eligible_users, d30_eligible_users,
        d1_retained_users, d7_retained_users, d30_retained_users,
        d1_weighted_rate, d7_weighted_rate, d30_weighted_rate,
        d1_matured, d7_matured, d30_matured,
        d1_sample_status, d7_sample_status, d30_sample_status,
        total_users (sum of eligible_users across all weeks for the channel)
    """
    if retention_df.empty:
        return pd.DataFrame()

    df = retention_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])

    # Create cohort_week (Monday of each week)
    df["cohort_week"] = df[date_col] - pd.to_timedelta(df[date_col].dt.dayofweek, unit="D")
    df["cohort_week"] = df["cohort_week"].dt.date

    # Check which maturity columns exist
    has_maturity = "d1_matured" in df.columns

    # Build aggregation keys
    group_keys = ["cohort_week", "acquisition_channel"]

    # Sum retained and eligible users per weekly cohort × channel
    agg_dict = {
        "d1_retained_users": "sum",
        "d7_retained_users": "sum",
        "d30_retained_users": "sum",
    }
    if has_maturity:
        for col in ["d1_eligible_users", "d7_eligible_users", "d30_eligible_users"]:
            if col in df.columns:
                agg_dict[col] = "sum"
        for col in ["d1_matured", "d7_matured", "d30_matured"]:
            if col in df.columns:
                agg_dict[col] = "max"  # TRUE if any daily cohort is matured

    # Legacy: if no eligible_users columns, derive from "eligible_users"
    if "eligible_users" in df.columns:
        agg_dict["eligible_users"] = "sum"

    weekly = df.groupby(group_keys, as_index=False).agg(agg_dict)

    # Derive eligible users if not present
    if "d1_eligible_users" not in weekly.columns:
        if "eligible_users" in weekly.columns:
            weekly["d1_eligible_users"] = weekly["eligible_users"]
            weekly["d7_eligible_users"] = weekly["eligible_users"]
            weekly["d30_eligible_users"] = weekly["eligible_users"]
        else:
            # Fallback: use retained + assumed non-retained
            weekly["d1_eligible_users"] = weekly["d1_retained_users"] * 2
            weekly["d7_eligible_users"] = weekly["d7_retained_users"] * 2
            weekly["d30_eligible_users"] = weekly["d30_retained_users"] * 2

    # Weighted retention rates by eligible users
    for horizon in ["d1", "d7", "d30"]:
        retained_col = f"{horizon}_retained_users"
        eligible_col = f"{horizon}_eligible_users"
        rate_col = f"{horizon}_weighted_rate"
        sample_col = f"{horizon}_sample_status"

        weekly[rate_col] = weekly[retained_col] / weekly[eligible_col].replace(0, float("nan"))
        weekly[sample_col] = weekly[eligible_col].apply(
            lambda v: "ok" if v >= MIN_COHORT_SAMPLE else "insufficient"
        )

    # Total per channel (across all weeks)
    chan_totals = weekly.groupby("acquisition_channel")["d1_eligible_users"].transform("sum")
    weekly["total_users"] = chan_totals

    return weekly


def build_retention_figure(
    weekly: pd.DataFrame,
    horizon: str,
    palette: list[str] | None = None,
) -> go.Figure:
    """Build a single-horizon retention chart with one trace per channel.

    Args:
        weekly: Output from ``prepare_weekly_retention``.
        horizon: One of ``"d1"``, ``"d7"``, ``"d30"``.
        palette: Colour palette for channels.

    Returns:
        A Plotly Figure with properly configured axes and legend.
    """
    if palette is None:
        palette = px.colors.qualitative.Plotly

    fig = go.Figure()

    eligible_col = f"{horizon}_eligible_users"
    rate_col = f"{horizon}_weighted_rate"
    sample_col = f"{horizon}_sample_status"

    available_channels = sorted(weekly["acquisition_channel"].dropna().unique())
    for i, ch in enumerate(available_channels):
        subset = weekly[weekly["acquisition_channel"] == ch].sort_values("cohort_week")
        # Mask points with insufficient sample
        mask = subset[sample_col] == "ok"
        color = palette[i % len(palette)]

        fig.add_trace(
            go.Scatter(
                x=subset.loc[mask, "cohort_week"],
                y=subset.loc[mask, rate_col],
                mode="lines+markers",
                name=ch,
                line={"color": color},
                connectgaps=False,
                hovertemplate=(
                    f"<b>{ch}</b><br>"
                    "Week: %{x}<br>"
                    f"{horizon.upper()} Rate: %{{y:.1%}}<br>"
                    f"Eligible: %{{customdata:,}}"
                    "<extra></extra>"
                ),
                customdata=subset.loc[mask, eligible_col],
            )
        )

    fig.update_layout(
        title=f"{horizon.upper()} Retention by Channel",
        xaxis_title="Cohort Week",
        yaxis_title=f"{horizon.upper()} Retention Rate",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1],
        height=450,
        margin={"t": 80, "b": 60, "l": 60, "r": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
        },
    )

    return fig


def build_sample_summary_table(weekly: pd.DataFrame) -> pd.DataFrame:
    """Build a sample-size summary table across all horizons."""
    if weekly.empty:
        return pd.DataFrame()

    rows = []
    for _, row in weekly.iterrows():
        ch = row.get("acquisition_channel", "Unknown")
        cw = row.get("cohort_week", "Unknown")
        for horizon in ["d1", "d7", "d30"]:
            eligible = row.get(f"{horizon}_eligible_users", 0)
            retained = row.get(f"{horizon}_retained_users", 0)
            rate = row.get(f"{horizon}_weighted_rate", None)
            sample = row.get(f"{horizon}_sample_status", "unknown")
            rows.append(
                {
                    "cohort_week": cw,
                    "channel": ch,
                    "horizon": horizon.upper(),
                    "eligible_users": int(eligible) if pd.notna(eligible) else 0,
                    "retained_users": int(retained) if pd.notna(retained) else 0,
                    "retention_rate": rate,
                    "sample_status": sample,
                }
            )
    return pd.DataFrame(rows)
