"""Agent Observability — Agent performance, latency, cost, errors, and quality trade-offs."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="Agent Observability", layout="wide")

st.title("Agent Observability")
st.markdown("Agent run performance, latency, cost, error analysis, and quality overview")

filters = render_filters(page_name="agent")
ds = filters["date_start"]
de = filters["date_end"]

# ── Daily KPIs (date-filtered) ──────────────────────────────────────────────
daily_kpis = query_df(
    """
    SELECT run_date, total_runs, agent_success_rate, tool_error_rate,
           avg_retry_count, p50_latency_ms, p95_latency_ms, p99_latency_ms,
           avg_input_tokens, avg_output_tokens, avg_cost_per_run,
           cost_per_successful_task, avg_field_accuracy, avg_manual_edit_count
    FROM main_marts.mart_agent_daily_kpis
    WHERE run_date BETWEEN ? AND ?
    ORDER BY run_date
    """,
    [ds, de],
)

# ── Stage Performance (no date filter — overall summary) ────────────────────
stage_perf = query_df(
    """
    SELECT stage, span_type, span_count, avg_latency_ms, p50_latency_ms,
           p95_latency_ms, error_rate, avg_input_tokens, avg_output_tokens,
           avg_cost_usd
    FROM main_marts.mart_agent_stage_performance
    ORDER BY stage
    """
)

# ── Model Version Comparison (no date filter — overall summary) ─────────────
model_comp = query_df(
    """
    SELECT model_name, prompt_version, run_count, avg_cost_usd, avg_latency_ms,
           avg_field_accuracy, avg_quality_score, total_input_tokens,
           total_output_tokens, avg_retry_count, success_rate
    FROM main_marts.mart_model_version_comparison
    ORDER BY model_name
    """
)

# ── Error Root Cause (Pareto) ───────────────────────────────────────────────
errors = query_df(
    """
    SELECT error_category, error_count, pct_of_total, cumulative_pct
    FROM main_marts.mart_error_root_cause
    ORDER BY error_count DESC
    """
)

# ── Overall Averages from daily KPIs ────────────────────────────────────────
overall = query_df(
    """
    SELECT
        AVG(agent_success_rate)          AS avg_success_rate,
        AVG(p50_latency_ms)              AS avg_p50,
        AVG(p95_latency_ms)              AS avg_p95,
        AVG(p99_latency_ms)              AS avg_p99,
        AVG(avg_cost_per_run)            AS avg_cost_per_run,
        AVG(cost_per_successful_task)    AS avg_cost_per_success,
        AVG(avg_field_accuracy)          AS avg_field_accuracy,
        SUM(total_runs)                  AS total_runs
    FROM main_marts.mart_agent_daily_kpis
    WHERE run_date BETWEEN ? AND ?
    """,
    [ds, de],
)

# ── KPIs ─────────────────────────────────────────────────────────────────────
st.subheader("Key Metrics")

if not overall.empty and overall.iloc[0]["avg_success_rate"] is not None:
    r = overall.iloc[0]
    kpi_row(
        [
            {
                "label": "Agent Success Rate",
                "value": r["avg_success_rate"],
                "help": "Fraction of agent runs completed without error.",
            },
            {
                "label": "P50 Latency",
                "value": r["avg_p50"],
                "help": "Median end-to-end agent latency in milliseconds.",
            },
            {
                "label": "P95 Latency",
                "value": r["avg_p95"],
                "help": "95th percentile agent latency in milliseconds.",
            },
            {
                "label": "P99 Latency",
                "value": r["avg_p99"],
                "help": "99th percentile agent latency in milliseconds.",
            },
        ]
    )
    kpi_row(
        [
            {
                "label": "Avg Cost / Run",
                "value": r["avg_cost_per_run"],
                "help": "Average estimated cost per agent run (USD).",
            },
            {
                "label": "Cost / Successful Task",
                "value": r["avg_cost_per_success"],
                "help": "Average cost per successfully completed agent task (USD).",
            },
            {
                "label": "Avg Field Accuracy",
                "value": r["avg_field_accuracy"] if pd.notna(r["avg_field_accuracy"]) else 0,
                "help": "Average field-level accuracy score across all model runs.",
            },
            {
                "label": "Total Runs",
                "value": int(r["total_runs"]) if pd.notna(r["total_runs"]) else 0,
                "help": "Total number of agent runs in the selected period.",
            },
        ],
        cols=4,
    )
else:
    st.info("No agent KPI data available for the selected filters.")

# ── Charts ───────────────────────────────────────────────────────────────────
st.subheader("Performance Trends")

col1, col2 = st.columns(2)

with col1:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["run_date"],
                y=daily_kpis["agent_success_rate"],
                mode="lines+markers",
                name="Success Rate",
                line={"color": "#00CC96"},
            )
        )
        fig.update_layout(
            title="Agent Success Rate Trend",
            yaxis_title="Success Rate",
            yaxis_tickformat=".0%",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No success rate trend data.")

with col2:
    if not daily_kpis.empty:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["run_date"],
                y=daily_kpis["p50_latency_ms"],
                mode="lines+markers",
                name="P50",
                line={"color": "#636EFA"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["run_date"],
                y=daily_kpis["p95_latency_ms"],
                mode="lines+markers",
                name="P95",
                line={"color": "#EF553B"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["run_date"],
                y=daily_kpis["p99_latency_ms"],
                mode="lines+markers",
                name="P99",
                line={"color": "#FFA15A"},
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
                x=daily_kpis["run_date"],
                y=daily_kpis["cost_per_successful_task"],
                mode="lines+markers",
                name="Cost / Successful Task",
                line={"color": "#AB63FA"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=daily_kpis["run_date"],
                y=daily_kpis["avg_cost_per_run"],
                mode="lines+markers",
                name="Avg Cost / Run",
                line={"color": "#19D3F3"},
            )
        )
        fig.update_layout(title="Cost Trends (USD)", yaxis_title="Cost (USD)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No cost trend data.")

with col4:
    if not model_comp.empty:
        fig = px.bar(
            model_comp,
            x="model_name",
            y="avg_field_accuracy",
            title="Field Accuracy by Model",
            text_auto=".3f",
            color="model_name",
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No field accuracy data.")

# ── Stage Performance ────────────────────────────────────────────────────────
st.subheader("Stage Performance")

if not stage_perf.empty:
    col_s1, col_s2 = st.columns(2)

    with col_s1:
        fig = px.bar(
            stage_perf,
            x="stage",
            y="avg_latency_ms",
            title="Average Latency by Stage (ms)",
            color="stage",
            text_auto=".0f",
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_s2:
        fig = px.bar(
            stage_perf,
            x="stage",
            y="avg_cost_usd",
            title="Average Cost by Stage (USD)",
            color="stage",
            text_auto=".5f",
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    detail = stage_perf.copy()
    detail["avg_latency_ms"] = detail["avg_latency_ms"].apply(lambda v: f"{v:,.1f}")
    detail["avg_cost_usd"] = detail["avg_cost_usd"].apply(lambda v: f"${v:.5f}")
    detail["error_rate"] = detail["error_rate"].apply(lambda v: f"{v:.2%}")
    st.dataframe(detail, use_container_width=True, hide_index=True)
else:
    st.info("No stage performance data available.")

# ── Error Pareto ─────────────────────────────────────────────────────────────
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
            marker={"color": "#636EFA"},
            line={"color": "#636EFA"},
        )
    )
    fig.update_layout(
        title="Error Categories — Pareto Analysis",
        xaxis_title="Error Category",
        yaxis={"title": "Error Count"},
        yaxis2={
            "title": "Cumulative %",
            "overlaying": "y",
            "side": "right",
            "tickformat": ".0%",
            "range": [0, 1.05],
        },
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    errors_display = errors.copy()
    errors_display["pct_of_total"] = errors_display["pct_of_total"].apply(lambda v: f"{v:.1%}")
    errors_display["cumulative_pct"] = errors_display["cumulative_pct"].apply(lambda v: f"{v:.1%}")
    st.dataframe(errors_display, use_container_width=True, hide_index=True)
else:
    st.info("No error root cause data available.")

# ── Model Comparison Overview ────────────────────────────────────────────────
st.subheader("Model Version Comparison")

if not model_comp.empty:
    fig = px.scatter(
        model_comp,
        x="avg_cost_usd",
        y="avg_field_accuracy",
        size="run_count",
        color="model_name",
        hover_data=["prompt_version", "avg_latency_ms", "success_rate"],
        title="Cost vs Field Accuracy by Model (bubble size = run count)",
        labels={
            "avg_cost_usd": "Avg Cost / Run (USD)",
            "avg_field_accuracy": "Field Accuracy",
        },
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    detail_comp = model_comp[
        ["model_name", "prompt_version", "run_count", "avg_cost_usd",
         "avg_latency_ms", "avg_field_accuracy", "avg_quality_score",
         "success_rate", "avg_retry_count"]
    ].copy()
    detail_comp["avg_cost_usd"] = detail_comp["avg_cost_usd"].apply(lambda v: f"${v:.5f}")
    detail_comp["avg_latency_ms"] = detail_comp["avg_latency_ms"].apply(lambda v: f"{v:,.1f}")
    detail_comp["success_rate"] = detail_comp["success_rate"].apply(lambda v: f"{v:.2%}")
    st.dataframe(detail_comp, use_container_width=True, hide_index=True)
else:
    st.info("No model comparison data available.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
