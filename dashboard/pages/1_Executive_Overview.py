"""Executive Overview — North Star metrics, DAU trends, and top-level KPIs."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="Executive Overview", layout="wide")

st.title("Executive Overview")
st.markdown("North star metrics and top-level product KPIs")

filters = render_filters(page_name="executive")
ds = filters["date_start"]
de = filters["date_end"]

# ── Query Scorecard ──────────────────────────────────────────────────────────
scorecard_df = query_df(
    """
    SELECT event_date, dau, north_star_metric, export_rate, abandonment_rate,
           avg_manual_edits, d7_retention, agent_success_rate,
           agent_p95_latency_ms, cost_per_successful_task, data_quality_status
    FROM main_marts.mart_executive_daily_scorecard
    WHERE event_date BETWEEN ? AND ?
    ORDER BY event_date
    """,
    [ds, de],
)

# ── KPIs ─────────────────────────────────────────────────────────────────────
st.subheader("Key Metrics")

if not scorecard_df.empty:
    agg = scorecard_df.agg({
        "north_star_metric": "sum",
        "dau": "mean",
        "export_rate": "mean",
        "d7_retention": "mean",
        "agent_success_rate": "mean",
        "agent_p95_latency_ms": "mean",
        "cost_per_successful_task": "mean",
    })
    kpi_row(
        [
            {
                "label": "Total Exported Tasks",
                "value": int(agg["north_star_metric"]) if pd.notna(agg["north_star_metric"]) else 0,
                "help": "North star metric — total successfully exported tasks.",
            },
            {
                "label": "Avg DAU",
                "value": int(agg["dau"]) if pd.notna(agg["dau"]) else 0,
                "help": "Daily active users — average over the selected period.",
            },
            {
                "label": "Avg Export Rate",
                "value": agg["export_rate"] if pd.notna(agg["export_rate"]) else 0,
                "help": "Fraction of started tasks that reach export.",
            },
            {
                "label": "Avg D7 Retention",
                "value": agg["d7_retention"] if pd.notna(agg["d7_retention"]) else 0,
                "help": "Fraction of users active on day 7 after signup.",
            },
        ]
    )
    kpi_row(
        [
            {
                "label": "Avg Agent Success Rate",
                "value": agg["agent_success_rate"] if pd.notna(agg["agent_success_rate"]) else 0,
                "help": "Fraction of agent runs completed without error.",
            },
            {
                "label": "Avg P95 Latency",
                "value": agg["agent_p95_latency_ms"] if pd.notna(agg["agent_p95_latency_ms"]) else 0,
                "help": "95th percentile agent latency in milliseconds.",
            },
            {
                "label": "Avg Cost / Task",
                "value": agg["cost_per_successful_task"] if pd.notna(agg["cost_per_successful_task"]) else 0,
                "help": "Average estimated cost per successfully exported task (USD).",
            },
        ],
        cols=4,
    )
else:
    st.info("No KPI data available for the selected filters.")

# ── Charts ───────────────────────────────────────────────────────────────────
st.subheader("Trends")

col1, col2 = st.columns(2)

with col1:
    if not scorecard_df.empty:
        fig = px.line(
            scorecard_df,
            x="event_date",
            y="north_star_metric",
            title="North Star: Total Exported Tasks",
            markers=True,
        )
        fig.update_layout(yaxis_title="Tasks")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No north star trend data.")

with col2:
    if not scorecard_df.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=scorecard_df["event_date"],
                y=scorecard_df["dau"],
                mode="lines+markers",
                name="DAU",
                line={"color": "#636EFA"},
            )
        )
        fig.update_layout(title="DAU Trend", yaxis_title="Users")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No DAU trend data.")

col3, col4 = st.columns(2)

with col3:
    if not scorecard_df.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=scorecard_df["event_date"],
                y=scorecard_df["export_rate"],
                mode="lines+markers",
                name="Export Rate",
                line={"color": "#00CC96"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=scorecard_df["event_date"],
                y=scorecard_df["agent_success_rate"],
                mode="lines+markers",
                name="Agent Success Rate",
                line={"color": "#AB63FA"},
            )
        )
        fig.update_layout(
            title="Export Rate vs Agent Success Rate",
            yaxis_title="Rate",
            yaxis_tickformat=".0%",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rate trend data.")

with col4:
    if not scorecard_df.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=scorecard_df["event_date"],
                y=scorecard_df["agent_p95_latency_ms"],
                mode="lines+markers",
                name="P95 Latency (ms)",
                yaxis="y1",
                line={"color": "#FFA15A"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=scorecard_df["event_date"],
                y=scorecard_df["cost_per_successful_task"],
                mode="lines+markers",
                name="Cost / Task ($)",
                yaxis="y2",
                line={"color": "#19D3F3"},
            )
        )
        fig.update_layout(
            title="P95 Latency + Cost Trend",
            yaxis={"title": "Latency (ms)", "side": "left"},
            yaxis2={"title": "Cost (USD)", "overlaying": "y", "side": "right"},
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No latency / cost trend data.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
