"""Funnel & Retention — 7-step task funnel and cohort retention curves."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="Funnel & Retention", layout="wide")

st.title("Funnel & Retention")
st.markdown("Task conversion funnel and user retention cohorts")

filters = render_filters(page_name="funnel")
ds = filters["date_start"]
de = filters["date_end"]
channel = filters.get("acquisition_channel", "All")
device = filters.get("device_type", "All")
complexity = filters.get("complexity", "All")

conn = get_connection()


def q(query_str: str) -> pd.DataFrame:
    return conn.execute(query_str).fetchdf()


channel_clause = "" if channel == "All" else f"AND channel = '{channel}'"
device_clause = "" if device == "All" else f"AND device_type = '{device}'"
complexity_clause = "" if complexity == "All" else f"AND complexity = '{complexity}'"

# ── Funnel Query ─────────────────────────────────────────────────────────
funnel = q(
    f"""
    SELECT
        step_name,
        step_order,
        user_count,
        event_count,
        pct_of_step1                                           AS step_to_start_pct,
        pct_of_prior_step                                      AS step_to_prior_pct
    FROM main_marts.mart_conversion_funnel
    WHERE date BETWEEN '{ds}' AND '{de}'
      {channel_clause}
      {device_clause}
      {complexity_clause}
    ORDER BY step_order
"""
)

# ── Retention Query ──────────────────────────────────────────────────────
retention = q(
    f"""
    SELECT
        cohort_date,
        channel,
        d1_retention,
        d7_retention,
        d30_retention
    FROM main_marts.mart_retention_cohort
    WHERE cohort_date BETWEEN '{ds}' AND '{de}'
      {channel_clause}
      {device_clause}
    ORDER BY cohort_date
"""
)

# ── Summary KPIs ─────────────────────────────────────────────────────────
if not funnel.empty:
    total_start = int(funnel.iloc[0]["user_count"]) if len(funnel) > 0 else 0
    total_exported = int(funnel.iloc[-1]["user_count"]) if len(funnel) > 0 else 0
    overall_conversion = total_exported / total_start if total_start > 0 else 0

    kpi_row(
        [
            {
                "label": "Users Entered Funnel",
                "value": total_start,
                "help": "Number of unique users who performed the first funnel step.",
            },
            {
                "label": "Users Exported",
                "value": total_exported,
                "help": "Number of unique users who reached form_exported (final step).",
            },
            {
                "label": "Overall Conversion Rate",
                "value": overall_conversion,
                "help": "Fraction of users who completed all 7 funnel steps.",
            },
            {
                "label": "Funnel Steps",
                "value": len(funnel),
                "help": "Number of discrete steps in the task funnel.",
            },
        ]
    )
else:
    st.info("No funnel data available for the selected filters.")

# ── Funnel Chart ─────────────────────────────────────────────────────────
st.subheader("Conversion Funnel")

if not funnel.empty:
    # Funnel bar chart
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=funnel["user_count"],
            y=funnel["step_name"],
            orientation="h",
            marker={
                "color": funnel["step_to_prior_pct"],
                "colorscale": "Blues",
                "reversescale": True,
                "colorbar": {"title": "Step-to-Prior %"},
            },
            text=funnel["user_count"].apply(lambda v: f"{v:,}"),
            textposition="inside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Users: %{x:,}<br>"
                "Step-to-start: %{customdata[0]:.1%}<br>"
                "Step-to-prior: %{customdata[1]:.1%}"
                "<extra></extra>"
            ),
            customdata=funnel[["pct_of_step1", "pct_of_prior_step"]],
        )
    )
    fig.update_layout(
        title="7-Step Task Funnel (Users)",
        xaxis_title="Users",
        yaxis={"autorange": "reversed"},
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Step-to-step conversion table
    st.subheader("Step-to-Step Conversion")
    display = funnel[
        ["step_name", "user_count", "event_count", "pct_of_step1", "pct_of_prior_step"]
    ].copy()
    display["user_count"] = display["user_count"].apply(lambda v: f"{v:,}")
    display["event_count"] = display["event_count"].apply(lambda v: f"{v:,}")
    display["pct_of_step1"] = display["pct_of_step1"].apply(lambda v: f"{v:.1%}")
    display["pct_of_prior_step"] = display["pct_of_prior_step"].apply(lambda v: f"{v:.1%}")
    display.columns = ["Step", "Users", "Events", "vs Step 1", "vs Prior Step"]
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No funnel data to display.")

# ── Retention Chart ──────────────────────────────────────────────────────
st.subheader("Retention Cohorts")

if not retention.empty:
    available_channels = retention["channel"].dropna().unique()
    palette = px.colors.qualitative.Plotly

    fig = go.Figure()
    for i, ch in enumerate(available_channels):
        subset = retention[retention["channel"] == ch].sort_values("cohort_date")
        fig.add_trace(
            go.Scatter(
                x=subset["cohort_date"],
                y=subset["d1_retention"],
                mode="lines+markers",
                name=f"D1 — {ch}",
                line={"color": palette[i % len(palette)], "dash": "dot"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["cohort_date"],
                y=subset["d7_retention"],
                mode="lines+markers",
                name=f"D7 — {ch}",
                line={"color": palette[i % len(palette)], "dash": "dash"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["cohort_date"],
                y=subset["d30_retention"],
                mode="lines+markers",
                name=f"D30 — {ch}",
                line={"color": palette[i % len(palette)], "dash": "solid"},
            )
        )

    fig.update_layout(
        title="D1 / D7 / D30 Retention by Channel",
        xaxis_title="Cohort Date",
        yaxis_title="Retention Rate",
        yaxis_tickformat=".0%",
        height=450,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    st.plotly_chart(fig, use_container_width=True)

    # Average retention summary
    avg_ret = (
        retention.groupby("channel")[["d1_retention", "d7_retention", "d30_retention"]]
        .mean()
        .reset_index()
    )
    for col in ["d1_retention", "d7_retention", "d30_retention"]:
        avg_ret[col] = avg_ret[col].apply(lambda v: f"{v:.1%}")
    avg_ret.columns = ["Channel", "Avg D1", "Avg D7", "Avg D30"]
    st.dataframe(avg_ret, use_container_width=True, hide_index=True)
else:
    st.info("No retention data available for the selected filters.")

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ **ALL DATA IS SYNTHETIC.** No real user, financial, or business data is displayed.")
