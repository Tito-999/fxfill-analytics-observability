"""Funnel & Retention — 7-step task funnel and cohort retention curves."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.components.retention_charts import (
    build_retention_figure,
    build_sample_summary_table,
    prepare_weekly_retention,
)
from dashboard.services.query import query_df

st.set_page_config(page_title="Funnel & Retention", layout="wide")

st.title("Funnel & Retention")
st.markdown("Task conversion funnel and cohort retention analysis")

filters = render_filters(page_name="funnel")
ds = filters["date_start"]
de = filters["date_end"]
channel = filters.get("acquisition_channel", "All")
device = filters.get("device_type", "All")
complexity = filters.get("complexity", "All")

# ── Build dynamic WHERE clause for funnel (date + channel + device + complexity) ──
funnel_where = ["event_date BETWEEN ? AND ?"]
funnel_params = [ds, de]

if channel != "All":
    funnel_where.append("acquisition_channel = ?")
    funnel_params.append(channel)
if device != "All":
    funnel_where.append("device_type = ?")
    funnel_params.append(device)
if complexity != "All":
    funnel_where.append("complexity = ?")
    funnel_params.append(complexity)

funnel_where_sql = " AND ".join(funnel_where)

# ── Funnel: compute 7-step counts via conditional aggregation (task-level) ─────
funnel_base = query_df(
    f"""
    SELECT
        COUNT(DISTINCT CASE WHEN did_upload = 1 THEN task_id END) AS upload,
        COUNT(DISTINCT CASE WHEN did_complete_ocr = 1 THEN task_id END) AS ocr,
        COUNT(DISTINCT CASE WHEN did_complete_anonymization = 1 THEN task_id END) AS anonymization,
        COUNT(DISTINCT CASE WHEN did_complete_risk_detection = 1 THEN task_id END) AS risk_detection,
        COUNT(DISTINCT CASE WHEN did_complete_autofill = 1 THEN task_id END) AS autofill,
        COUNT(DISTINCT CASE WHEN did_start_review = 1 THEN task_id END) AS review,
        COUNT(DISTINCT CASE WHEN did_export = 1 THEN task_id END) AS export
    FROM main_intermediate.int_task_funnel_enriched
    WHERE {funnel_where_sql}
    """,
    funnel_params,
)

step_names = [
    "Upload",
    "OCR",
    "Anonymization",
    "Risk Detection",
    "Autofill",
    "Review",
    "Export",
]
step_cols = ["upload", "ocr", "anonymization", "risk_detection", "autofill", "review", "export"]

funnel_rows = []
first_val = None
prev_val = None
for i, (name, col) in enumerate(zip(step_names, step_cols, strict=False)):
    val = int(funnel_base.iloc[0][col]) if not funnel_base.empty else 0
    if first_val is None:
        first_val = val
    pct_of_step1 = val / first_val if first_val and first_val > 0 else 0
    pct_of_prior = val / prev_val if i > 0 and prev_val and prev_val > 0 else 1.0 if i == 0 else 0
    funnel_rows.append(
        {
            "step_order": i + 1,
            "step_name": name,
            "task_count": val,
            "pct_of_step1": pct_of_step1,
            "pct_of_prior_step": pct_of_prior,
        }
    )
    prev_val = val

funnel = pd.DataFrame(funnel_rows)

# ── Retention: query mart_retention_cohort (date + channel only) ────────────────
retention_where = ["cohort_date BETWEEN ? AND ?"]
retention_params = [ds, de]

if channel != "All":
    retention_where.append("acquisition_channel = ?")
    retention_params.append(channel)

retention_where_sql = " AND ".join(retention_where)

retention = query_df(
    f"""
    SELECT cohort_date, acquisition_channel, eligible_users,
           d1_matured, d1_eligible_users, d1_retained_users, d1_retention_rate,
           d7_matured, d7_eligible_users, d7_retained_users, d7_retention_rate,
           d30_matured, d30_eligible_users, d30_retained_users, d30_retention_rate,
           observation_end_date
    FROM main_marts.mart_retention_cohort
    WHERE {retention_where_sql}
    ORDER BY cohort_date
    """,
    retention_params,
)

# ── Summary KPIs (task-level) ───────────────────────────────────────────────────
if not funnel.empty:
    total_start = int(funnel.iloc[0]["task_count"]) if len(funnel) > 0 else 0
    total_exported = int(funnel.iloc[-1]["task_count"]) if len(funnel) > 0 else 0
    overall_conversion = total_exported / total_start if total_start > 0 else 0

    kpi_row(
        [
            {
                "label": "Tasks Entered Funnel",
                "value": total_start,
                "format_type": "integer",
                "help": "Number of unique tasks that entered the first funnel step.",
            },
            {
                "label": "Tasks Exported",
                "value": total_exported,
                "format_type": "integer",
                "help": "Number of unique tasks that reached export (final step).",
            },
            {
                "label": "Overall Conversion Rate",
                "value": overall_conversion,
                "format_type": "percent",
                "help": "Fraction of tasks that completed all 7 funnel steps.",
            },
            {
                "label": "Funnel Steps",
                "value": len(funnel),
                "format_type": "integer",
                "help": "Number of discrete steps in the task funnel.",
            },
        ]
    )
else:
    st.info("No funnel data available for the selected filters.")

# ── Funnel Chart ─────────────────────────────────────────────────────────────────
st.subheader("7-Step Task Funnel (Tasks)")

if not funnel.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=funnel["task_count"],
            y=funnel["step_name"],
            orientation="h",
            marker={
                "color": funnel["pct_of_prior_step"],
                "colorscale": "Blues",
                "reversescale": True,
                "colorbar": {"title": "Step-to-Prior Rate", "tickformat": ".0%"},
            },
            text=funnel["task_count"].apply(lambda v: f"{v:,}"),
            textposition="inside",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Tasks: %{x:,}<br>"
                "Step-to-start: %{customdata[0]:.1%}<br>"
                "Step-to-prior: %{customdata[1]:.1%}"
                "<extra></extra>"
            ),
            customdata=funnel[["pct_of_step1", "pct_of_prior_step"]],
        )
    )
    fig.update_layout(
        title="7-Step Task Funnel (Tasks)",
        xaxis_title="Tasks",
        yaxis={"autorange": "reversed"},
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Step-to-step conversion table
    st.subheader("Step-to-Step Conversion")
    display = funnel[["step_name", "task_count", "pct_of_step1", "pct_of_prior_step"]].copy()
    display["task_count"] = display["task_count"].apply(lambda v: f"{v:,}")
    display["pct_of_step1"] = display["pct_of_step1"].apply(lambda v: f"{v:.1%}")
    display["pct_of_prior_step"] = display["pct_of_prior_step"].apply(lambda v: f"{v:.1%}")
    display.columns = ["Step", "Tasks", "vs Step 1", "vs Prior Step"]
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No funnel data to display.")

# ── Retention Charts (tab-separated D1/D7/D30) ──────────────────────────────────
st.subheader("Retention Cohorts")

if not retention.empty:
    try:
        weekly = prepare_weekly_retention(retention)
    except ValueError as e:
        st.error(f"Retention data contract error: {e}")
        weekly = pd.DataFrame()

    if not weekly.empty:
        tab_d1, tab_d7, tab_d30 = st.tabs(["D1 Retention", "D7 Retention", "D30 Retention"])

        for tab, horizon, label in [
            (tab_d1, "d1", "D1"),
            (tab_d7, "d7", "D7"),
            (tab_d30, "d30", "D30"),
        ]:
            with tab:
                fig, point_count = build_retention_figure(weekly, horizon)
                if fig is not None and point_count > 0:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(
                        f"No {label} weekly channel cohorts meet the minimum "
                        f"sample size of {20}. "
                        "See Sample Size Summary for details."
                    )

        st.subheader("Sample Size Summary")
        with st.expander("View cohort sample details", expanded=False):
            summary = build_sample_summary_table(weekly)
            if not summary.empty:
                summary["retention_rate"] = summary["retention_rate"].apply(
                    lambda v: f"{v:.1%}" if pd.notna(v) else "N/A"
                )
                st.dataframe(summary, use_container_width=True, hide_index=True)
                st.caption(
                    "Cohort-weeks with fewer than 20 eligible users are marked "
                    '"insufficient" and are excluded from the chart. '
                    "Unmatured cohorts display N/A. "
                    "Rates are weighted by eligible users within each weekly cohort."
                )
    else:
        st.info("No retention data to display after weekly aggregation.")
else:
    st.info("No retention data available for the selected filters.")

# ── Filter Applicability Note ────────────────────────────────────────────────────
st.info("Device and complexity filters apply to the task funnel. Retention is cohort-level.")

# ── Footer ───────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
