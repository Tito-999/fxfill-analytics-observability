"""Agent Observability — Agent performance, latency, cost, errors, and quality trade-offs.

All sections (KPIs, charts, tables) obey the page-level date range filter.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import format_kpi_value, kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="Agent Observability", layout="wide")

st.title("Agent Observability")
st.markdown("Agent run performance, latency, cost, error analysis, and quality overview")

filters = render_filters(page_name="agent")
ds = filters["date_start"]
de = filters["date_end"]


def _fmt(val, fmt_type):
    """Shorthand for safe formatting."""
    return format_kpi_value(val, fmt_type)


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

# ── Stage Performance (date-filtered via agent_runs.run_date) ───────────────
stage_perf = query_df(
    """
    SELECT run_date, stage, span_type, span_count, avg_latency_ms, p50_latency_ms,
           p95_latency_ms, error_rate, avg_input_tokens, avg_output_tokens,
           avg_cost_usd
    FROM main_marts.mart_agent_stage_performance
    WHERE run_date BETWEEN ? AND ?
    ORDER BY run_date, stage
    """,
    [ds, de],
)

# ── Model Version Comparison (date-filtered) ────────────────────────────────
model_comp = query_df(
    """
    SELECT run_date, model_name, prompt_version, run_count, avg_cost_usd,
           avg_latency_ms, avg_field_accuracy, avg_quality_score,
           total_input_tokens, total_output_tokens, avg_retry_count, success_rate
    FROM main_marts.mart_model_version_comparison
    WHERE run_date BETWEEN ? AND ?
    ORDER BY run_date, model_name
    """,
    [ds, de],
)

# ── Error Root Cause (date-filtered) ────────────────────────────────────────
errors = query_df(
    """
    WITH grouped AS (
        SELECT
            error_category,
            SUM(error_count) AS error_count,
            SUM(error_count * error_share)
                / NULLIF(SUM(error_count), 0) AS weighted_error_share,
            SUM(affected_tasks) AS affected_tasks,
            AVG(avg_failed_latency_ms) AS avg_failed_latency_ms
        FROM main_marts.mart_error_root_cause
        WHERE run_date BETWEEN ? AND ?
        GROUP BY error_category
    ),
    ranked AS (
        SELECT
            error_category,
            error_count,
            error_count * 1.0
                / NULLIF(SUM(error_count) OVER (), 0) AS pct_of_total,
            affected_tasks,
            avg_failed_latency_ms
        FROM grouped
    )
    SELECT
        error_category,
        error_count,
        pct_of_total,
        SUM(pct_of_total) OVER (
            ORDER BY error_count DESC, error_category
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_pct,
        affected_tasks,
        avg_failed_latency_ms
    FROM ranked
    ORDER BY error_count DESC, error_category
    """,
    [ds, de],
)
_required_error_cols = {"error_category", "error_count", "pct_of_total", "cumulative_pct"}
_missing = _required_error_cols - set(errors.columns)
if _missing:
    raise RuntimeError("Agent error query contract failed: " + ", ".join(sorted(_missing)))

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

# ── KPIs with explicit format types ─────────────────────────────────────────
st.subheader("Key Metrics")

if not overall.empty and overall.iloc[0]["avg_success_rate"] is not None:
    r = overall.iloc[0]
    kpi_row(
        [
            {
                "label": "Agent Success Rate",
                "value": r["avg_success_rate"],
                "format_type": "percent",
                "help": "Fraction of agent runs completed without error.",
            },
            {
                "label": "P50 Latency",
                "value": r["avg_p50"],
                "format_type": "latency_ms",
                "help": "Median end-to-end agent latency in milliseconds.",
            },
            {
                "label": "P95 Latency",
                "value": r["avg_p95"],
                "format_type": "latency_ms",
                "help": "95th percentile agent latency in milliseconds.",
            },
            {
                "label": "P99 Latency",
                "value": r["avg_p99"],
                "format_type": "latency_ms",
                "help": "99th percentile agent latency in milliseconds.",
            },
        ]
    )
    kpi_row(
        [
            {
                "label": "Avg Cost / Run",
                "value": r["avg_cost_per_run"],
                "format_type": "currency",
                "help": "Average estimated cost per agent run (USD).",
            },
            {
                "label": "Cost / Successful Task",
                "value": r["avg_cost_per_success"],
                "format_type": "currency",
                "help": "Average cost per successfully completed agent task (USD).",
            },
            {
                "label": "Avg Field Accuracy",
                "value": r["avg_field_accuracy"],
                "format_type": "percent",
                "help": "Average field-level accuracy score across all model runs.",
            },
            {
                "label": "Total Runs",
                "value": int(r["total_runs"]) if pd.notna(r["total_runs"]) else 0,
                "format_type": "integer",
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
        agg_mc = model_comp.groupby("model_name", as_index=False).agg(
            {"avg_field_accuracy": "mean", "run_count": "sum"}
        )
        fig = px.bar(
            agg_mc,
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
    stage_agg = stage_perf.groupby(["stage", "span_type"], as_index=False).agg(
        {
            "avg_latency_ms": "mean",
            "avg_cost_usd": "mean",
            "avg_input_tokens": "mean",
            "avg_output_tokens": "mean",
            "error_rate": "mean",
            "span_count": "sum",
        }
    )

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        fig = px.bar(
            stage_agg,
            x="stage",
            y="avg_latency_ms",
            title="Average Latency by Stage (ms)",
            color="stage",
            text_auto=".0f",
        )
        fig.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig, use_container_width=True)

    with col_s2:
        llm_stages = stage_agg[stage_agg["span_type"] == "llm"]
        if not llm_stages.empty:
            fig = px.bar(
                llm_stages,
                x="stage",
                y="avg_cost_usd",
                title="Average LLM Cost by Stage (USD)",
                color="stage",
                text_auto=".5f",
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No LLM cost data available for the selected period.")

    # Table with safe formatting
    detail = stage_agg[
        [
            "stage",
            "span_type",
            "span_count",
            "avg_latency_ms",
            "avg_cost_usd",
            "avg_input_tokens",
            "avg_output_tokens",
            "error_rate",
        ]
    ].copy()
    detail["avg_latency_ms"] = detail["avg_latency_ms"].apply(lambda v: _fmt(v, "latency_ms"))
    detail["avg_cost_usd"] = detail["avg_cost_usd"].apply(lambda v: _fmt(v, "currency"))
    detail["error_rate"] = detail["error_rate"].apply(lambda v: _fmt(v, "percent"))
    detail["avg_input_tokens"] = detail.apply(
        lambda r: _fmt(r["avg_input_tokens"], "integer") if r["span_type"] == "llm" else "N/A",
        axis=1,
    )
    detail["avg_output_tokens"] = detail.apply(
        lambda r: _fmt(r["avg_output_tokens"], "integer") if r["span_type"] == "llm" else "N/A",
        axis=1,
    )
    detail["span_count"] = detail["span_count"].apply(lambda v: _fmt(v, "integer"))
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
    errors_display["pct_of_total"] = errors_display["pct_of_total"].apply(
        lambda v: _fmt(v, "percent")
    )
    errors_display["cumulative_pct"] = errors_display["cumulative_pct"].apply(
        lambda v: _fmt(v, "percent")
    )
    st.dataframe(errors_display, use_container_width=True, hide_index=True)
else:
    st.info("No error root cause data available.")

# ── Model Comparison Overview ────────────────────────────────────────────────
st.subheader("Model Version Comparison")

if not model_comp.empty:
    agg_mc2 = model_comp.groupby(["model_name", "prompt_version"], as_index=False).agg(
        {
            "avg_cost_usd": "mean",
            "avg_field_accuracy": "mean",
            "avg_latency_ms": "mean",
            "success_rate": "mean",
            "avg_retry_count": "mean",
            "run_count": "sum",
            "total_input_tokens": "sum",
            "total_output_tokens": "sum",
            "avg_quality_score": "mean",
        }
    )

    fig = px.scatter(
        agg_mc2,
        x="avg_cost_usd",
        y="avg_field_accuracy",
        size="run_count",
        color="model_name",
        hover_data=["prompt_version", "avg_latency_ms", "success_rate"],
        title="Cost vs Field Accuracy by Model (bubble size = run count)",
        labels={"avg_cost_usd": "Avg Cost / Run (USD)", "avg_field_accuracy": "Field Accuracy"},
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    detail_comp = agg_mc2[
        [
            "model_name",
            "prompt_version",
            "run_count",
            "avg_cost_usd",
            "avg_latency_ms",
            "avg_field_accuracy",
            "avg_quality_score",
            "success_rate",
            "avg_retry_count",
        ]
    ].copy()
    detail_comp["avg_cost_usd"] = detail_comp["avg_cost_usd"].apply(lambda v: _fmt(v, "currency"))
    detail_comp["avg_latency_ms"] = detail_comp["avg_latency_ms"].apply(
        lambda v: _fmt(v, "latency_ms")
    )
    detail_comp["success_rate"] = detail_comp["success_rate"].apply(lambda v: _fmt(v, "percent"))
    detail_comp["run_count"] = detail_comp["run_count"].apply(lambda v: _fmt(v, "integer"))
    st.dataframe(detail_comp, use_container_width=True, hide_index=True)
else:
    st.info("No model comparison data available.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
