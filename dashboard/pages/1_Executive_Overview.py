"""Executive Overview — North Star metrics, DAU trends, and top-level KPIs."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="Executive Overview", layout="wide")

st.title("Executive Overview")
st.markdown("North star metrics and top-level product KPIs")

filters = render_filters(page_name="executive")
ds = filters["date_start"]
de = filters["date_end"]
channel = filters.get("acquisition_channel", "All")
device = filters.get("device_type", "All")

conn = get_connection()


# ── Queries ──────────────────────────────────────────────────────────────
def q(query_str: str) -> pd.DataFrame:
    """Helper: run raw SQL and return a DataFrame."""
    return conn.execute(query_str).fetchdf()


channel_clause = "" if channel == "All" else f"AND channel = '{channel}'"
device_clause = "" if device == "All" else f"AND device_type = '{device}'"

# 1. Mart daily product KPIs
daily_kpis = q(
    f"""
    SELECT
        date,
        dau,
        new_users,
        export_rate,
        agent_success_rate,
        p95_latency_ms,
        cost_per_successful_task
    FROM main_marts.mart_daily_product_kpis
    WHERE date BETWEEN '{ds}' AND '{de}'
      {channel_clause}
      {device_clause}
    ORDER BY date
"""
)

# 2. Executive daily scorecard
scorecard = q(
    f"""
    SELECT
        date,
        weekly_successful_exported_tasks,
        d7_retention_rate,
        active_users,
        revenue
    FROM main_marts.mart_executive_daily_scorecard
    WHERE date BETWEEN '{ds}' AND '{de}'
    ORDER BY date
"""
)

# 3. Overall averages
overall = q(
    f"""
    SELECT
        AVG(dau)                                                         AS avg_dau,
        AVG(export_rate)                                                 AS avg_export_rate,
        AVG(d7_retention_rate)                                           AS avg_d7_retention,
        AVG(agent_success_rate)                                          AS avg_agent_success_rate,
        AVG(p95_latency_ms)                                              AS avg_p95_latency,
        AVG(cost_per_successful_task)                                    AS avg_cost_per_task,
        MAX(weekly_successful_exported_tasks)                            AS weekly_exported_tasks
    FROM main_marts.mart_daily_product_kpis k
    LEFT JOIN main_marts.mart_executive_daily_scorecard s USING (date)
    WHERE k.date BETWEEN '{ds}' AND '{de}'
      {channel_clause}
      {device_clause}
"""
)

# ── KPIs ─────────────────────────────────────────────────────────────────
st.subheader("Key Metrics")
if not overall.empty and overall.iloc[0]["avg_dau"] is not None:
    r = overall.iloc[0]
    kpi_row(
        [
            {
                "label": "Weekly Successful Exported Tasks",
                "value": (
                    int(r["weekly_exported_tasks"]) if pd.notna(r["weekly_exported_tasks"]) else 0
                ),
                "help": "Number of tasks that reached form_exported in the latest week.",
            },
            {
                "label": "DAU",
                "value": int(r["avg_dau"]) if pd.notna(r["avg_dau"]) else 0,
                "help": "Daily active users — average over the selected period.",
            },
            {
                "label": "Export Rate",
                "value": r["avg_export_rate"] if pd.notna(r["avg_export_rate"]) else 0,
                "help": "Fraction of started tasks that reach form_exported.",
            },
            {
                "label": "D7 Retention",
                "value": r["avg_d7_retention"] if pd.notna(r["avg_d7_retention"]) else 0,
                "help": "Fraction of users active on signup_date + 7 days.",
            },
        ]
    )
    kpi_row(
        [
            {
                "label": "Agent Success Rate",
                "value": (
                    r["avg_agent_success_rate"] if pd.notna(r["avg_agent_success_rate"]) else 0
                ),
                "help": "Fraction of agent runs completed without error.",
            },
            {
                "label": "P95 Latency",
                "value": r["avg_p95_latency"] if pd.notna(r["avg_p95_latency"]) else 0,
                "help": "95th percentile of end-to-end task latency in milliseconds.",
            },
            {
                "label": "Cost / Successful Task",
                "value": r["avg_cost_per_task"] if pd.notna(r["avg_cost_per_task"]) else 0,
                "help": "Average estimated cost per successfully exported task (USD).",
            },
        ],
        cols=4,
    )
else:
    st.info("No KPI data available for the selected filters.")

# ── Charts ───────────────────────────────────────────────────────────────
st.subheader("Trends")

col1, col2 = st.columns(2)

with col1:
    if not scorecard.empty:
        fig = px.line(
            scorecard,
            x="date",
            y="weekly_successful_exported_tasks",
            title="North Star: Weekly Successful Exported Tasks",
            markers=True,
        )
        fig.update_layout(yaxis_title="Tasks")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No north star trend data.")

with col2:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["dau"],
                mode="lines+markers",
                name="DAU",
                line={"color": "#636EFA"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["new_users"],
                mode="lines+markers",
                name="New Users",
                line={"color": "#EF553B"},
            )
        )
        fig.update_layout(title="DAU + New Users", yaxis_title="Users")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No daily KPI data.")

col3, col4 = st.columns(2)

with col3:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["export_rate"],
                mode="lines+markers",
                name="Export Rate",
                line={"color": "#00CC96"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["agent_success_rate"],
                mode="lines+markers",
                name="Agent Success Rate",
                line={"color": "#AB63FA"},
            )
        )
        fig.update_layout(
            title="Export Rate vs Agent Success Rate", yaxis_title="Rate", yaxis_tickformat=".0%"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No rate trend data.")

with col4:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["p95_latency_ms"],
                mode="lines+markers",
                name="P95 Latency (ms)",
                yaxis="y1",
                line={"color": "#FFA15A"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["cost_per_successful_task"],
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

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ **ALL DATA IS SYNTHETIC.** No real user, financial, or business data is displayed.")
