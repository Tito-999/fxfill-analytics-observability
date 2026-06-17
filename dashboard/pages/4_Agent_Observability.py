"""Agent Observability — Agent performance, latency, cost, errors, and quality trade-offs."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="Agent Observability", layout="wide")

st.title("Agent Observability")
st.markdown("Agent run performance, latency, cost, error analysis, and cost-quality trade-offs")

filters = render_filters(page_name="agent")
ds = filters["date_start"]
de = filters["date_end"]
model = filters.get("model_name", "All")

conn = get_connection()


def q(query_str: str) -> pd.DataFrame:
    return conn.execute(query_str).fetchdf()


model_clause = "" if model == "All" else f"AND model_name = '{model}'"
model_join_clause = "" if model == "All" else f"AND m.model_name = '{model}'"

# ── Daily KPIs ───────────────────────────────────────────────────────────
daily_kpis = q(
    f"""
    SELECT
        date,
        total_runs,
        successful_runs,
        success_rate,
        p50_latency_ms,
        p95_latency_ms,
        p99_latency_ms,
        avg_cost_per_run,
        cost_per_successful_task
    FROM main_marts.mart_agent_daily_kpis
    WHERE date BETWEEN '{ds}' AND '{de}'
      {model_clause}
    ORDER BY date
"""
)

# ── Stage Performance ────────────────────────────────────────────────────
stage_perf = q(
    f"""
    SELECT
        stage_name,
        avg_duration_ms,
        avg_input_tokens,
        avg_output_tokens,
        avg_cost_usd,
        error_rate,
        success_count,
        error_count
    FROM main_marts.mart_agent_stage_performance
    WHERE date BETWEEN '{ds}' AND '{de}'
      {model_clause}
    ORDER BY stage_name
"""
)

# ── Model Version Comparison ─────────────────────────────────────────────
model_comp = q(
    f"""
    SELECT
        model_name,
        date,
        success_rate,
        p50_latency_ms,
        p95_latency_ms,
        avg_cost_per_run,
        avg_field_accuracy,
        total_runs
    FROM main_marts.mart_model_version_comparison
    WHERE date BETWEEN '{ds}' AND '{de}'
      {model_clause}
    ORDER BY model_name, date
"""
)

# ── Error Root Cause (Pareto) ────────────────────────────────────────────
errors = q(
    f"""
    SELECT
        error_category,
        error_count,
        pct_of_total,
        cumulative_pct
    FROM main_marts.mart_error_root_cause
    {model_clause}
    ORDER BY error_count DESC
"""
)

# ── Cost-Quality Trade-off ───────────────────────────────────────────────
cost_quality = q(
    f"""
    SELECT
        model_name,
        date,
        avg_cost_per_run,
        avg_field_accuracy,
        avg_p95_latency_ms,
        total_runs
    FROM main_marts.mart_cost_quality_tradeoff
    WHERE date BETWEEN '{ds}' AND '{de}'
      {model_join_clause}
    ORDER BY model_name, date
"""
)

# ── Overall Averages ─────────────────────────────────────────────────────
overall = q(
    f"""
    SELECT
        AVG(success_rate)            AS avg_success_rate,
        AVG(p50_latency_ms)          AS avg_p50,
        AVG(p95_latency_ms)          AS avg_p95,
        AVG(p99_latency_ms)          AS avg_p99,
        AVG(avg_cost_per_run)        AS avg_cost_per_run,
        AVG(cost_per_successful_task) AS avg_cost_per_success,
        SUM(successful_runs)         AS total_successful,
        SUM(total_runs)              AS total_runs
    FROM main_marts.mart_agent_daily_kpis
    WHERE date BETWEEN '{ds}' AND '{de}'
      {model_clause}
"""
)

# ── Field Accuracy ───────────────────────────────────────────────────────
field_acc = q(
    f"""
    SELECT AVG(avg_field_accuracy) AS avg_field_accuracy
    FROM main_marts.mart_model_version_comparison
    WHERE date BETWEEN '{ds}' AND '{de}'
      {model_clause}
"""
)

# ── KPIs ─────────────────────────────────────────────────────────────────
st.subheader("Key Metrics")

if not overall.empty and overall.iloc[0]["avg_success_rate"] is not None:
    r = overall.iloc[0]
    fa_val = field_acc.iloc[0]["avg_field_accuracy"] if not field_acc.empty else None

    kpi_row(
        [
            dict(
                label="Agent Success Rate",
                value=r["avg_success_rate"],
                help="Fraction of agent runs completed without error.",
            ),
            dict(
                label="P50 Latency",
                value=r["avg_p50"],
                help="Median end-to-end agent latency in milliseconds.",
            ),
            dict(
                label="P95 Latency",
                value=r["avg_p95"],
                help="95th percentile agent latency in milliseconds.",
            ),
            dict(
                label="P99 Latency",
                value=r["avg_p99"],
                help="99th percentile agent latency in milliseconds.",
            ),
        ]
    )
    kpi_row(
        [
            dict(
                label="Avg Cost / Run",
                value=r["avg_cost_per_run"],
                help="Average estimated cost per agent run (USD).",
            ),
            dict(
                label="Cost / Successful Task",
                value=r["avg_cost_per_success"],
                help="Average cost per successfully completed agent task (USD).",
            ),
            dict(
                label="Avg Field Accuracy",
                value=fa_val if pd.notna(fa_val) else 0,
                help="Average field-level accuracy score across all model runs.",
            ),
            dict(
                label="Total Runs",
                value=int(r["total_runs"]) if pd.notna(r["total_runs"]) else 0,
                help="Total number of agent runs in the selected period.",
            ),
        ],
        cols=4,
    )
else:
    st.info("No agent KPI data available for the selected filters.")

# ── Charts ───────────────────────────────────────────────────────────────
st.subheader("Performance Trends")

col1, col2 = st.columns(2)

with col1:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["success_rate"],
                mode="lines+markers",
                name="Success Rate",
                line=dict(color="#00CC96"),
            )
        )
        fig.update_layout(
            title="Agent Success Rate Trend", yaxis_title="Success Rate", yaxis_tickformat=".0%"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No success rate trend data.")

with col2:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["p50_latency_ms"],
                mode="lines+markers",
                name="P50",
                line=dict(color="#636EFA"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["p95_latency_ms"],
                mode="lines+markers",
                name="P95",
                line=dict(color="#EF553B"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["p99_latency_ms"],
                mode="lines+markers",
                name="P99",
                line=dict(color="#FFA15A"),
            )
        )
        fig.update_layout(title="Latency Percentiles (ms)", yaxis_title="Latency (ms)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No latency trend data.")

col3, col4 = st.columns(2)

with col3:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["cost_per_successful_task"],
                mode="lines+markers",
                name="Cost / Successful Task",
                line=dict(color="#AB63FA"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["date"],
                y=daily_kpis["avg_cost_per_run"],
                mode="lines+markers",
                name="Avg Cost / Run",
                line=dict(color="#19D3F3"),
            )
        )
        fig.update_layout(title="Cost Trends (USD)", yaxis_title="Cost (USD)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No cost trend data.")

with col4:
    if not model_comp.empty:
        latest = model_comp.sort_values("date").groupby("model_name").last().reset_index()
        fig = px.bar(
            latest,
            x="model_name",
            y="avg_field_accuracy",
            title="Latest Field Accuracy by Model",
            text_auto=".3f",
            color="model_name",
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No field accuracy data.")

# ── Stage Performance ────────────────────────────────────────────────────
st.subheader("Stage Performance")

if not stage_perf.empty:
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        fig = px.bar(
            stage_perf,
            x="stage_name",
            y="avg_duration_ms",
            title="Average Duration by Stage (ms)",
            color="stage_name",
            text_auto=".0f",
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_s2:
        fig = px.bar(
            stage_perf,
            x="stage_name",
            y="avg_cost_usd",
            title="Average Cost by Stage (USD)",
            color="stage_name",
            text_auto=".5f",
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    detail = stage_perf.copy()
    for col in ["avg_duration_ms", "avg_cost_usd"]:
        if col in detail.columns:
            detail[col] = detail[col].apply(
                lambda v: f"{v:,.1f}" if "duration" in col else f"${v:.5f}"
            )
    detail["error_rate"] = detail["error_rate"].apply(lambda v: f"{v:.2%}")
    st.dataframe(detail, use_container_width=True, hide_index=True)
else:
    st.info("No stage performance data available.")

# ── Error Pareto ─────────────────────────────────────────────────────────
st.subheader("Error Root Cause (Pareto)")

if not errors.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=errors["error_category"],
            y=errors["error_count"],
            name="Error Count",
            marker_color="#EF553B",
            text=errors["error_count"].apply(lambda v: f"{v:,}"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=errors["error_category"],
            y=errors["cumulative_pct"],
            name="Cumulative %",
            yaxis="y2",
            mode="lines+markers",
            marker=dict(color="#636EFA"),
            line=dict(color="#636EFA"),
        )
    )
    fig.update_layout(
        title="Error Categories — Pareto Analysis",
        xaxis_title="Error Category",
        yaxis=dict(title="Error Count"),
        yaxis2=dict(
            title="Cumulative %", overlaying="y", side="right", tickformat=".0%", range=[0, 1.05]
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    errors_display = errors.copy()
    errors_display["pct_of_total"] = errors_display["pct_of_total"].apply(lambda v: f"{v:.1%}")
    errors_display["cumulative_pct"] = errors_display["cumulative_pct"].apply(lambda v: f"{v:.1%}")
    st.dataframe(errors_display, use_container_width=True, hide_index=True)
else:
    st.info("No error root cause data available.")

# ── Cost-Quality Trade-off ───────────────────────────────────────────────
st.subheader("Cost-Quality Trade-off")

if not cost_quality.empty:
    fig = px.scatter(
        cost_quality,
        x="avg_cost_per_run",
        y="avg_field_accuracy",
        size="total_runs",
        color="model_name",
        hover_data=["date", "avg_p95_latency_ms"],
        title="Cost vs Field Accuracy (bubble size = total runs)",
        labels={
            "avg_cost_per_run": "Avg Cost / Run (USD)",
            "avg_field_accuracy": "Field Accuracy",
        },
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No cost-quality trade-off data available.")

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ **ALL DATA IS SYNTHETIC.** No real user, financial, or business data is displayed.")
