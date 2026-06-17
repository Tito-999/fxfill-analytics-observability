"""A/B Test Dashboard — Experiment group comparison, contamination, and guardrails."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="A/B Test Dashboard", layout="wide")

st.title("A/B Test Experiment Analysis")
st.markdown("Group-level metric comparison, contamination status, and guardrail monitoring")

filters = render_filters(page_name="ab_test")
exp_group = filters.get("experiment_group", "All")

# ── Experiment Summary (all-time, no date filter, parameterized group) ──────
_summary_sql = """SELECT experiment_group, user_count, total_tasks, avg_export_rate, avg_field_accuracy, avg_latency_ms, cost_per_task FROM main_marts.mart_ab_test_summary"""
_summary_params: list = []
if exp_group != "All":
    _summary_sql += " WHERE experiment_group = ?"
    _summary_params.append(exp_group)
_summary_sql += " ORDER BY experiment_group"
summary = query_df(_summary_sql, _summary_params)

# ── User-Level Metrics (all-time, no date filter, parameterized group) ──────
# Notes: mart uses successful_tasks/task_success_rate/avg_agent_latency_ms;
# aliased to exported_tasks/export_rate/avg_latency_ms for display consistency.
_um_sql = """SELECT user_id, experiment_group, total_tasks, successful_tasks AS exported_tasks, task_success_rate AS export_rate, avg_field_accuracy, avg_agent_latency_ms AS avg_latency_ms, total_cost_usd FROM main_marts.mart_ab_test_user_metrics"""
_um_params: list = []
if exp_group != "All":
    _um_sql += " WHERE experiment_group = ?"
    _um_params.append(exp_group)
_um_sql += " ORDER BY experiment_group, user_id"
user_metrics = query_df(_um_sql, _um_params)
# Validate contract
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

# ── Clean Assignments ───────────────────────────────────────────────────────
clean = query_df(
    """SELECT user_id, experiment_group, assigned_at FROM main_intermediate.int_experiment_clean_assignments ORDER BY user_id"""
)

# ── Contaminated Users ──────────────────────────────────────────────────────
contaminated = query_df(
    """SELECT user_id, group_count, assigned_groups, is_intentional_contamination FROM main_intermediate.int_experiment_contaminated_users ORDER BY user_id"""
)

# ── Experiment Period ────────────────────────────────────────────────────────
exp_period = query_df(
    """SELECT MIN(assigned_at) AS experiment_start, MAX(assigned_at) AS experiment_end FROM main_intermediate.int_experiment_clean_assignments"""
)

# ── Summary Info ─────────────────────────────────────────────────────────────
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
            "help": "Number of users cleanly assigned to experiment group A.",
        },
        {
            "label": "Group B (Clean)",
            "value": n_clean_b,
            "help": "Number of users cleanly assigned to experiment group B.",
        },
        {
            "label": "Contaminated Users (Excluded)",
            "value": n_contaminated,
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

# ── AB Test Summary ─────────────────────────────────────────────────────────
st.subheader("Group-Level Metrics")

if not summary.empty:
    metrics_to_plot = ["avg_export_rate", "avg_field_accuracy", "avg_latency_ms", "cost_per_task"]
    labels_map = {
        "avg_export_rate": "Export Rate",
        "avg_field_accuracy": "Field Accuracy",
        "avg_latency_ms": "Avg Latency (ms)",
        "cost_per_task": "Cost / Task",
    }

    fig = go.Figure()
    for grp in sorted(summary["experiment_group"].unique()):
        subset = summary[summary["experiment_group"] == grp]
        vals = [subset[col].iloc[0] if col in subset.columns else 0 for col in metrics_to_plot]
        fig.add_trace(
            go.Bar(
                name=f"Group {grp}",
                x=[labels_map[m] for m in metrics_to_plot],
                y=vals,
                text=[
                    f"{v:.2%}" if m in ("avg_export_rate", "avg_field_accuracy") else f"{v:.2f}"
                    for v, m in zip(vals, metrics_to_plot, strict=False)
                ],
                textposition="auto",
            )
        )

    fig.update_layout(
        title="Key Metrics by Experiment Group",
        yaxis_title="Value",
        barmode="group",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    detail = summary.copy()
    detail["avg_export_rate"] = detail["avg_export_rate"].apply(lambda v: f"{v:.2%}")
    detail["avg_field_accuracy"] = detail["avg_field_accuracy"].apply(lambda v: f"{v:.2%}")
    detail["avg_latency_ms"] = detail["avg_latency_ms"].apply(lambda v: f"{v:,.1f}")
    detail["cost_per_task"] = detail["cost_per_task"].apply(lambda v: f"${v:.4f}")
    detail["user_count"] = detail["user_count"].apply(lambda v: f"{v:,}")
    detail["total_tasks"] = detail["total_tasks"].apply(lambda v: f"{v:,}")
    st.dataframe(detail, use_container_width=True, hide_index=True)
else:
    st.info("No experiment summary data available for the selected filters.")

# ── Guardrails ───────────────────────────────────────────────────────────────
st.subheader("Guardrails")

if not summary.empty:
    guardrails = (
        summary.groupby("experiment_group")[["avg_latency_ms", "cost_per_task"]]
        .mean()
        .reset_index()
    )

    kpi_row(
        [
            {
                "label": f"Avg Latency (Group {r['experiment_group']})",
                "value": r["avg_latency_ms"],
                "help": "Average end-to-end latency. Increase may indicate performance regression.",
            }
            for _, r in guardrails.iterrows()
        ]
    )
    kpi_row(
        [
            {
                "label": f"Cost / Task (Group {r['experiment_group']})",
                "value": r["cost_per_task"],
                "help": "Average cost per task. Increase may indicate cost regression.",
            }
            for _, r in guardrails.iterrows()
        ],
        cols=4,
    )

    fig = go.Figure()
    guardrail_metrics = ["avg_latency_ms", "cost_per_task"]
    guardrail_labels = ["Avg Latency (ms)", "Cost / Task ($)"]

    for grp in sorted(summary["experiment_group"].unique()):
        subset = summary[summary["experiment_group"] == grp]
        vals = [subset[m].iloc[0] if m in subset.columns else 0 for m in guardrail_metrics]
        fig.add_trace(
            go.Bar(
                name=f"Group {grp}",
                x=guardrail_labels,
                y=vals,
                textposition="auto",
            )
        )

    fig.update_layout(
        title="Guardrail Metrics by Experiment Group",
        yaxis_title="Value",
        barmode="group",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No guardrail data available.")

# ── User Distribution ────────────────────────────────────────────────────────
st.subheader("User-Level Metric Distributions")

if not user_metrics.empty:
    col_dist1, col_dist2 = st.columns(2)

    with col_dist1:
        fig = px.histogram(
            user_metrics,
            x="export_rate",
            color="experiment_group",
            nbins=40,
            barmode="overlay",
            title="Export Rate Distribution by Group",
            labels={"export_rate": "Export Rate"},
        )
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)

    with col_dist2:
        fig = px.histogram(
            user_metrics,
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
    st.info("No user-level metric data available.")

# ── Note ─────────────────────────────────────────────────────────────────────
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
