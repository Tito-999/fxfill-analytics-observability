"""A/B Test Dashboard — Experiment group comparison, contamination, and guardrails."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import format_kpi_value, kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="A/B Test Dashboard", layout="wide")

st.title("A/B Test Experiment Analysis")
st.markdown("Group-level metric comparison, contamination status, and guardrail monitoring")

filters = render_filters(page_name="ab_test")
exp_group = filters.get("experiment_group", "All")


def _safe_float(val, default=None):
    """Return *val* as float, or *default* if NaN/None/Inf."""
    if val is None:
        return default
    try:
        f = float(val)
        if pd.isna(f) or f == float("inf") or f == float("-inf"):
            return default
        return f
    except (ValueError, TypeError):
        return default


# ── Experiment Summary ─────────────────────────────────────────────────────
_summary_sql = """SELECT experiment_group, user_count, total_tasks, avg_export_rate, avg_field_accuracy, avg_latency_ms, cost_per_task FROM main_marts.mart_ab_test_summary"""
_summary_params: list = []
if exp_group != "All":
    _summary_sql += " WHERE experiment_group = ?"
    _summary_params.append(exp_group)
_summary_sql += " ORDER BY experiment_group"
summary = query_df(_summary_sql, _summary_params)

# ── User-Level Metrics ─────────────────────────────────────────────────────
_um_sql = """SELECT user_id, experiment_group, total_tasks, successful_tasks AS exported_tasks, task_success_rate AS export_rate, avg_field_accuracy, avg_agent_latency_ms AS avg_latency_ms, total_cost_usd FROM main_marts.mart_ab_test_user_metrics"""
_um_params: list = []
if exp_group != "All":
    _um_sql += " WHERE experiment_group = ?"
    _um_params.append(exp_group)
_um_sql += " ORDER BY experiment_group, user_id"
user_metrics = query_df(_um_sql, _um_params)
_req = {
    "user_id",
    "experiment_group",
    "total_tasks",
    "exported_tasks",
    "export_rate",
    "avg_field_accuracy",
    "avg_latency_ms",
    "total_cost_usd",
}
_miss = _req - set(user_metrics.columns)
if _miss:
    raise RuntimeError("A/B user metrics contract failed: " + ", ".join(sorted(_miss)))

# ── Clean Assignments ──────────────────────────────────────────────────────
clean = query_df(
    """SELECT user_id, experiment_group, assigned_at FROM main_intermediate.int_experiment_clean_assignments ORDER BY user_id"""
)

# ── Contaminated Users ─────────────────────────────────────────────────────
contaminated = query_df(
    """SELECT user_id, group_count, assigned_groups, is_intentional_contamination FROM main_intermediate.int_experiment_contaminated_users ORDER BY user_id"""
)

# ── Experiment Period ──────────────────────────────────────────────────────
exp_period = query_df(
    """SELECT MIN(assigned_at) AS experiment_start, MAX(assigned_at) AS experiment_end FROM main_intermediate.int_experiment_clean_assignments"""
)

# ── Agent metric coverage ──────────────────────────────────────────────────
coverage_sql = """
    SELECT
        pe.experiment_group,
        COUNT(DISTINCT pe.task_id) AS total_tasks,
        COUNT(DISTINCT ar.agent_run_id) AS tasks_with_agent
    FROM main_staging.stg_product_events pe
    LEFT JOIN main_staging.stg_agent_runs ar ON pe.task_id = ar.task_id
    WHERE pe.experiment_group IN ('A', 'B')
    GROUP BY pe.experiment_group
"""
coverage = query_df(coverage_sql)

# ── Summary Info ───────────────────────────────────────────────────────────
st.subheader("Experiment Overview")

if not exp_period.empty and exp_period.iloc[0]["experiment_start"] is not None:
    period = exp_period.iloc[0]
    st.markdown(f"**Experiment Period:** {period['experiment_start']} → {period['experiment_end']}")
else:
    st.info("No experiment period data available.")

n_clean_a = len(clean[clean["experiment_group"] == "A"]) if not clean.empty else 0
n_clean_b = len(clean[clean["experiment_group"] == "B"]) if not clean.empty else 0
n_contaminated = len(contaminated) if not contaminated.empty else 0

kpi_row(
    [
        {
            "label": "Group A (Clean)",
            "value": n_clean_a,
            "format_type": "integer",
            "help": "Number of users cleanly assigned to experiment group A.",
        },
        {
            "label": "Group B (Clean)",
            "value": n_clean_b,
            "format_type": "integer",
            "help": "Number of users cleanly assigned to experiment group B.",
        },
        {
            "label": "Contaminated (Excluded)",
            "value": n_contaminated,
            "format_type": "integer",
            "help": "Users found in multiple experiment groups, excluded from analysis.",
        },
    ],
    cols=3,
)

if n_contaminated > 0:
    st.warning(
        f"{n_contaminated} contaminated user(s) detected and excluded from analysis. "
        "Contamination occurs when a user appears in multiple experiment groups."
    )

# Agent metric coverage warning
if not coverage.empty:
    for _, cr in coverage.iterrows():
        grp = cr["experiment_group"]
        total = int(cr["total_tasks"])
        matched = int(cr["tasks_with_agent"])
        cov_rate = matched / total if total > 0 else 0
        if cov_rate < 0.99:
            st.warning(
                f"Group {grp}: Agent metric coverage is incomplete "
                f"({matched}/{total} = {cov_rate:.1%}). "
                "Guardrail metrics are unavailable for part of the experiment population."
            )

# ── Outcome Metrics ────────────────────────────────────────────────────────
st.subheader("Outcome Metrics (Percentage Scale)")

if not summary.empty:
    outcome_metrics = ["avg_export_rate", "avg_field_accuracy"]
    outcome_labels = {"avg_export_rate": "Export Rate", "avg_field_accuracy": "Field Accuracy"}

    fig_outcome = go.Figure()
    for grp in sorted(summary["experiment_group"].unique()):
        subset = summary[summary["experiment_group"] == grp]
        vals = []
        texts = []
        for m in outcome_metrics:
            raw = subset[m].iloc[0] if m in subset.columns else None
            v = _safe_float(raw, None)
            vals.append(v)
            texts.append(format_kpi_value(v, "percent"))
        fig_outcome.add_trace(
            go.Bar(
                name=f"Group {grp}",
                x=[outcome_labels[m] for m in outcome_metrics],
                y=vals,
                text=texts,
                textposition="auto",
            )
        )
    fig_outcome.update_layout(
        title="Outcome Metrics by Experiment Group",
        yaxis_tickformat=".0%",
        barmode="group",
        height=400,
    )
    st.plotly_chart(fig_outcome, use_container_width=True)
else:
    st.info("No experiment summary data available.")

# ── Guardrail Latency ──────────────────────────────────────────────────────
st.subheader("Guardrail: Latency (ms Scale)")

if not summary.empty:
    fig_lat = go.Figure()
    for grp in sorted(summary["experiment_group"].unique()):
        subset = summary[summary["experiment_group"] == grp]
        raw = subset["avg_latency_ms"].iloc[0] if "avg_latency_ms" in subset.columns else None
        v = _safe_float(raw, None)
        fig_lat.add_trace(
            go.Bar(
                name=f"Group {grp}",
                x=[f"Group {grp}"],
                y=[v],
                text=[format_kpi_value(v, "latency_ms")],
                textposition="auto",
            )
        )
    fig_lat.update_layout(
        title="Avg Latency by Experiment Group",
        yaxis_title="Latency (ms)",
        height=350,
    )
    st.plotly_chart(fig_lat, use_container_width=True)
else:
    st.info("No latency data available.")

# ── Guardrail Cost ─────────────────────────────────────────────────────────
st.subheader("Guardrail: Cost per Task (USD Scale)")

if not summary.empty:
    fig_cost = go.Figure()
    for grp in sorted(summary["experiment_group"].unique()):
        subset = summary[summary["experiment_group"] == grp]
        raw = subset["cost_per_task"].iloc[0] if "cost_per_task" in subset.columns else None
        v = _safe_float(raw, None)
        fig_cost.add_trace(
            go.Bar(
                name=f"Group {grp}",
                x=[f"Group {grp}"],
                y=[v],
                text=[format_kpi_value(v, "currency")],
                textposition="auto",
            )
        )
    fig_cost.update_layout(
        title="Cost per Task by Experiment Group",
        yaxis_title="Cost (USD)",
        height=350,
    )
    st.plotly_chart(fig_cost, use_container_width=True)
else:
    st.info("No cost data available.")

# ── KPI cards with explicit formats ────────────────────────────────────────
st.subheader("Guardrail KPIs")
if not summary.empty:
    cards_latency = []
    cards_cost = []
    for _, r in summary.iterrows():
        grp = r["experiment_group"]
        lat = _safe_float(r.get("avg_latency_ms"), None)
        cost = _safe_float(r.get("cost_per_task"), None)
        cards_latency.append(
            {
                "label": f"Latency Group {grp}",
                "value": lat,
                "format_type": "latency_ms",
                "help": f"Average end-to-end latency for Group {grp}.",
            }
        )
        cards_cost.append(
            {
                "label": f"Cost/Task Group {grp}",
                "value": cost,
                "format_type": "currency",
                "help": f"Average cost per task for Group {grp}.",
            }
        )
    kpi_row(cards_latency, cols=4)
    kpi_row(cards_cost, cols=4)

# ── Detail Table ───────────────────────────────────────────────────────────
if not summary.empty:
    st.subheader("Detailed Summary")
    detail = summary.copy()
    for col in ["avg_export_rate", "avg_field_accuracy"]:
        detail[col] = detail[col].apply(lambda v: format_kpi_value(v, "percent"))
    detail["avg_latency_ms"] = detail["avg_latency_ms"].apply(
        lambda v: format_kpi_value(v, "latency_ms")
    )
    detail["cost_per_task"] = detail["cost_per_task"].apply(
        lambda v: format_kpi_value(v, "currency")
    )
    detail["user_count"] = detail["user_count"].apply(
        lambda v: format_kpi_value(int(v) if pd.notna(v) else None, "integer")
    )
    detail["total_tasks"] = detail["total_tasks"].apply(
        lambda v: format_kpi_value(int(v) if pd.notna(v) else None, "integer")
    )
    st.dataframe(detail, use_container_width=True, hide_index=True)

# ── User Distribution ──────────────────────────────────────────────────────
st.subheader("User-Level Metric Distributions")

if not user_metrics.empty:
    col_dist1, col_dist2 = st.columns(2)

    with col_dist1:
        # Filter out NaN values from histogram data
        dist_data = user_metrics[user_metrics["export_rate"].notna()]
        if not dist_data.empty:
            fig = px.histogram(
                dist_data,
                x="export_rate",
                color="experiment_group",
                nbins=40,
                barmode="overlay",
                title="Export Rate Distribution by Group",
                labels={"export_rate": "Export Rate"},
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid export rate data for distribution chart.")

    with col_dist2:
        dist_data2 = user_metrics[user_metrics["avg_field_accuracy"].notna()]
        if not dist_data2.empty:
            fig = px.histogram(
                dist_data2,
                x="avg_field_accuracy",
                color="experiment_group",
                nbins=40,
                barmode="overlay",
                title="Field Accuracy Distribution by Group",
                labels={"avg_field_accuracy": "Field Accuracy"},
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid field accuracy data for distribution chart.")
else:
    st.info("No user-level metric data available.")

# ── Notes ──────────────────────────────────────────────────────────────────
st.info(
    "A/B metrics use the experiment's fixed assignment window, "
    "not the global product date filter."
)

st.info(
    "**Descriptive analysis only.** Statistical significance testing "
    "(p-values, confidence intervals) is not yet implemented and will be "
    "available in a later module. The metrics shown above describe observed "
    "differences between groups and should not be interpreted as evidence "
    "of causal effects or statistical significance."
)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
