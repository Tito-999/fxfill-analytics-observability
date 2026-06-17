"""A/B Test Dashboard — Experiment group comparison, contamination, and guardrails."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="A/B Test Dashboard", layout="wide")

st.title("A/B Test Experiment Analysis")
st.markdown("Group-level metric comparison, contamination status, and guardrail monitoring")

filters = render_filters(page_name="ab_test")
ds = filters["date_start"]
de = filters["date_end"]
exp_group = filters.get("experiment_group", "All")

conn = get_connection()


def q(query_str: str) -> pd.DataFrame:
    return conn.execute(query_str).fetchdf()


group_clause = "" if exp_group == "All" else f"AND experiment_group = '{exp_group}'"
group_clause_user = "" if exp_group == "All" else f"AND u.experiment_group = '{exp_group}'"

# ── Experiment Summary ───────────────────────────────────────────────────
summary = q(
    f"""
    SELECT
        experiment_name,
        experiment_group,
        total_users,
        total_tasks,
        export_rate,
        task_success_rate,
        field_accuracy,
        manual_edit_rate,
        p95_latency_ms,
        cost_per_successful_task,
        abandonment_rate,
        agent_error_rate
    FROM main_marts.mart_ab_test_summary
    WHERE date BETWEEN '{ds}' AND '{de}'
      {group_clause}
    ORDER BY experiment_name, experiment_group
"""
)

# ── User-Level Metrics ───────────────────────────────────────────────────
user_metrics = q(
    f"""
    SELECT
        user_id,
        experiment_group,
        tasks_completed,
        export_rate,
        avg_field_accuracy,
        manual_edit_count,
        total_latency_ms,
        total_cost_usd
    FROM main_marts.mart_ab_test_user_metrics
    WHERE date BETWEEN '{ds}' AND '{de}'
      {group_clause}
    ORDER BY experiment_group
"""
)

# ── Clean Assignments ────────────────────────────────────────────────────
clean = q(
    f"""
    SELECT
        user_id,
        experiment_group,
        assignment_date
    FROM main_intermediate.int_experiment_clean_assignments
    WHERE assignment_date BETWEEN '{ds}' AND '{de}'
      {group_clause}
    ORDER BY user_id
"""
)

# ── Contaminated Users ───────────────────────────────────────────────────
contaminated = q(
    f"""
    SELECT
        user_id,
        assigned_groups,
        contamination_type
    FROM main_intermediate.int_experiment_contaminated_users
    WHERE assignment_date BETWEEN '{ds}' AND '{de}'
    ORDER BY user_id
"""
)

# ── Experiment Metadata ──────────────────────────────────────────────────
exp_period = q(
    """
    SELECT
        MIN(assignment_date) AS experiment_start,
        MAX(assignment_date) AS experiment_end
    FROM main_intermediate.int_experiment_clean_assignments
"""
)

# ── Summary Info ─────────────────────────────────────────────────────────
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
        dict(
            label="Group A (Clean)",
            value=n_clean_a,
            help="Number of users cleanly assigned to experiment group A.",
        ),
        dict(
            label="Group B (Clean)",
            value=n_clean_b,
            help="Number of users cleanly assigned to experiment group B.",
        ),
        dict(
            label="Contaminated Users (Excluded)",
            value=n_contaminated,
            help="Users found in both A and B groups, excluded from analysis.",
        ),
    ],
    cols=3,
)

if n_contaminated > 0:
    st.warning(
        f"{n_contaminated} contaminated user(s) detected and excluded from analysis. "
        "Contamination occurs when a user appears in multiple experiment groups."
    )

# ── AB Test Summary ─────────────────────────────────────────────────────
st.subheader("Group-Level Metrics")

if not summary.empty:
    # Metric comparison bar chart
    metrics_to_plot = ["export_rate", "task_success_rate", "field_accuracy", "manual_edit_rate"]
    labels_map = {
        "export_rate": "Export Rate",
        "task_success_rate": "Task Success Rate",
        "field_accuracy": "Field Accuracy",
        "manual_edit_rate": "Manual Edit Rate",
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
                text=[f"{v:.2%}" for v in vals],
                textposition="auto",
            )
        )

    fig.update_layout(
        title="Key Metrics by Experiment Group",
        yaxis_title="Rate",
        yaxis_tickformat=".0%",
        barmode="group",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    detail = summary.copy()
    for col in ["export_rate", "task_success_rate", "field_accuracy", "manual_edit_rate"]:
        if col in detail.columns:
            detail[col] = detail[col].apply(lambda v: f"{v:.2%}")
    detail["total_users"] = detail["total_users"].apply(lambda v: f"{v:,}")
    detail["total_tasks"] = detail["total_tasks"].apply(lambda v: f"{v:,}")
    st.dataframe(detail, use_container_width=True, hide_index=True)
else:
    st.info("No experiment summary data available for the selected filters.")

# ── Guardrails ───────────────────────────────────────────────────────────
st.subheader("Guardrails")

if not summary.empty:
    guardrails = (
        summary.groupby("experiment_group")[
            ["p95_latency_ms", "cost_per_successful_task", "abandonment_rate", "agent_error_rate"]
        ]
        .mean()
        .reset_index()
    )

    kpi_row(
        [
            dict(
                label=f"P95 Latency (Group {r['experiment_group']})",
                value=r["p95_latency_ms"],
                help="95th percentile end-to-end latency. Increase may indicate performance regression.",
            )
            for _, r in guardrails.iterrows()
        ]
    )
    kpi_row(
        [
            dict(
                label=f"Cost / Task (Group {r['experiment_group']})",
                value=r["cost_per_successful_task"],
                help="Average cost per successful task. Increase may indicate cost regression.",
            )
            for _, r in guardrails.iterrows()
        ]
    )
    kpi_row(
        [
            dict(
                label=f"Abandonment Rate (Group {r['experiment_group']})",
                value=r["abandonment_rate"],
                help="Fraction of tasks abandoned before completion.",
            )
            for _, r in guardrails.iterrows()
        ]
    )
    kpi_row(
        [
            dict(
                label=f"Agent Error Rate (Group {r['experiment_group']})",
                value=r["agent_error_rate"],
                help="Fraction of agent runs ending with an error.",
            )
            for _, r in guardrails.iterrows()
        ],
        cols=4,
    )

    fig = go.Figure()
    guardrail_metrics = [
        "p95_latency_ms",
        "cost_per_successful_task",
        "abandonment_rate",
        "agent_error_rate",
    ]
    guardrail_labels = [
        "P95 Latency (ms)",
        "Cost / Task ($)",
        "Abandonment Rate",
        "Agent Error Rate",
    ]
    tick_format = [".0f", ".4f", ".2%", ".2%"]

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

# ── User Distribution ────────────────────────────────────────────────────
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

# ── Statistical Note ─────────────────────────────────────────────────────
st.info(
    "**Descriptive analysis only.** Statistical significance testing "
    "(p-values, confidence intervals) is not yet implemented and will be "
    "available in a later module. The metrics shown above describe observed "
    "differences between groups and should not be interpreted as evidence "
    "of causal effects or statistical significance."
)

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ **ALL DATA IS SYNTHETIC.** No real user, financial, or business data is displayed.")
