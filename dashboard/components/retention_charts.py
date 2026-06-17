"""Retention chart helpers — weekly weighted cohorts, horizon tabs, sample controls.

Contract: retention_df MUST contain horizon-specific columns:
    d1_matured, d1_eligible_users, d1_retained_users, d1_retention_rate,
    d7_matured, d7_eligible_users, d7_retained_users, d7_retention_rate,
    d30_matured, d30_eligible_users, d30_retained_users, d30_retention_rate,
    observation_end_date
"""

from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

MIN_COHORT_SAMPLE = 20


@dataclass(frozen=True)
class RetentionFigureAudit:
    horizon: str
    plotted_point_count: int = 0
    empty_trace_count: int = 0
    unmatured_points_plotted: int = 0
    insufficient_points_plotted: int = 0


_REQUIRED_COLS = [
    "cohort_date",
    "acquisition_channel",
    "d1_matured",
    "d1_eligible_users",
    "d1_retained_users",
    "d1_retention_rate",
    "d7_matured",
    "d7_eligible_users",
    "d7_retained_users",
    "d7_retention_rate",
    "d30_matured",
    "d30_eligible_users",
    "d30_retained_users",
    "d30_retention_rate",
]


def _validate_retention_contract(df: pd.DataFrame):
    """Raise ValueError if the retention DataFrame is missing required columns."""
    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(
            "Retention input contract is incomplete. "
            f"Missing columns: {missing}. "
            "Ensure the retention mart includes all horizon-specific maturity "
            "and eligible-user columns per the dbt model schema."
        )


def prepare_weekly_retention(
    retention_df: pd.DataFrame,
    date_col: str = "cohort_date",
) -> pd.DataFrame:
    """Aggregate daily retention into weekly cohorts with weighted mature-only rates.

    Only daily cohorts with matured=true are included in the aggregation
    for each horizon. Returns a DataFrame suitable for charting.
    """
    if retention_df.empty:
        return pd.DataFrame()

    _validate_retention_contract(retention_df)

    df = retention_df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["cohort_week"] = (
        df[date_col] - pd.to_timedelta(df[date_col].dt.dayofweek, unit="D")
    ).dt.date

    group_keys = ["cohort_week", "acquisition_channel"]

    weekly_rows = []
    for (cw, ch), grp in df.groupby(group_keys):
        row = {"cohort_week": cw, "acquisition_channel": ch}
        for horizon in ["d1", "d7", "d30"]:
            matured_col = f"{horizon}_matured"
            eligible_col = f"{horizon}_eligible_users"
            retained_col = f"{horizon}_retained_users"
            rate_col = f"{horizon}_weighted_rate"
            maturity_col = f"{horizon}_maturity_status"
            sample_col = f"{horizon}_sample_status"

            # Only aggregate matured daily cohorts
            matured = grp[grp[matured_col]]
            eligible = int(matured[eligible_col].sum()) if not matured.empty else 0
            retained = int(matured[retained_col].sum()) if not matured.empty else 0
            rate = (retained / eligible) if eligible > 0 else None

            row[eligible_col] = eligible
            row[retained_col] = retained
            row[rate_col] = rate

            if eligible == 0:
                row[maturity_col] = "unmatured"
            elif eligible < MIN_COHORT_SAMPLE:
                row[maturity_col] = "insufficient"
            else:
                row[maturity_col] = "ok"

            row[sample_col] = row[maturity_col]

        weekly_rows.append(row)

    weekly = pd.DataFrame(weekly_rows)
    return weekly


def has_eligible_retention_points(weekly: pd.DataFrame, horizon: str) -> bool:
    """Return True if at least one channel-week has valid retention data for *horizon*."""
    eligible_col = f"{horizon}_eligible_users"
    sample_col = f"{horizon}_sample_status"
    if weekly.empty:
        return False
    if eligible_col not in weekly.columns:
        return False
    if sample_col in weekly.columns:
        mask = weekly[sample_col] == "ok"
        return (weekly.loc[mask, eligible_col] > 0).any() if not mask.empty else False
    return (weekly[eligible_col] > 0).any()


def build_retention_figure(
    weekly: pd.DataFrame,
    horizon: str,
    palette: list[str] | None = None,
) -> tuple[go.Figure | None, "RetentionFigureAudit"]:
    """Build a single-horizon retention chart. Returns (figure, audit).

    The audit tracks unmatured/insufficient points plotted and empty traces.
    Only traces with at least one valid point are added.
    If no channel has any valid point, attempts an overall "All Channels Combined" fallback.
    Returns (None, RetentionFigureAudit) if nothing can be plotted.
    """
    if palette is None:
        palette = px.colors.qualitative.Plotly

    eligible_col = f"{horizon}_eligible_users"
    rate_col = f"{horizon}_weighted_rate"
    sample_col = f"{horizon}_sample_status"

    if weekly.empty:
        return None, RetentionFigureAudit(horizon=horizon)

    fig = go.Figure()
    total_points = 0
    unmatured_count = 0
    insufficient_count = 0
    available_channels = sorted(weekly["acquisition_channel"].dropna().unique())

    for i, ch in enumerate(available_channels):
        subset = weekly[weekly["acquisition_channel"] == ch].sort_values("cohort_week")
        mask = subset[sample_col] == "ok"
        if not mask.any():
            continue
        # unmatured/insufficient points are correctly excluded from plotted traces
        # because the mask filters to sample_col == "ok". These counts stay at 0.
        color = palette[i % len(palette)]
        pts = subset.loc[mask]
        total_points += len(pts)
        fig.add_trace(
            go.Scatter(
                x=pts["cohort_week"],
                y=pts[rate_col],
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
                customdata=pts[eligible_col],
            )
        )

    # Overall fallback when no per-channel data exists
    if total_points == 0:
        overall = (
            weekly.groupby("cohort_week")
            .agg(
                {
                    eligible_col: "sum",
                    f"{horizon}_retained_users": "sum",
                }
            )
            .reset_index()
        )
        overall[rate_col] = overall[f"{horizon}_retained_users"] / overall[eligible_col].replace(
            0, float("nan")
        )
        overall[sample_col] = overall[eligible_col].apply(
            lambda v: "ok" if v >= MIN_COHORT_SAMPLE else "insufficient"
        )
        mask = overall[sample_col] == "ok"
        if mask.any():
            pts = overall.loc[mask]
            total_points = len(pts)
            fig.add_trace(
                go.Scatter(
                    x=pts["cohort_week"],
                    y=pts[rate_col],
                    mode="lines+markers",
                    name="All Channels Combined",
                    line={"color": "#636EFA"},
                    connectgaps=False,
                    hovertemplate=(
                        "All Channels<br>"
                        "Week: %{x}<br>"
                        f"{horizon.upper()} Rate: %{{y:.1%}}<br>"
                        "Eligible: %{customdata:,}<extra></extra>"
                    ),
                    customdata=pts[eligible_col],
                )
            )
        else:
            return None, RetentionFigureAudit(horizon=horizon)

    if total_points == 0:
        return None, RetentionFigureAudit(horizon=horizon)

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

    # Count empty traces (avoid truth-value ambiguity with numpy arrays)
    empty_count = 0
    for t in fig.data:
        has_x = t.x is not None and len(t.x) > 0 if t.x is not None else False
        has_y = t.y is not None and len(t.y) > 0 if t.y is not None else False
        if not (has_x and has_y):
            empty_count += 1

    audit = RetentionFigureAudit(
        horizon=horizon,
        plotted_point_count=total_points,
        empty_trace_count=empty_count,
        unmatured_points_plotted=unmatured_count,
        insufficient_points_plotted=insufficient_count,
    )
    return fig, audit


def build_sample_summary_table(weekly: pd.DataFrame) -> pd.DataFrame:
    """Build a sample-size summary table across all horizons with maturity status."""
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
            maturity = row.get(f"{horizon}_maturity_status", "unknown")
            rows.append(
                {
                    "cohort_week": cw,
                    "channel": ch,
                    "horizon": horizon.upper(),
                    "maturity_status": maturity,
                    "eligible_users": int(eligible) if pd.notna(eligible) else 0,
                    "retained_users": int(retained) if pd.notna(retained) else 0,
                    "retention_rate": rate,
                    "sample_status": maturity,
                }
            )
    return pd.DataFrame(rows)
