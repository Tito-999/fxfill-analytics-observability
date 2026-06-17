"""Funnel & Retention — 7-step task funnel and cohort retention curves."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="Funnel & Retention", layout="wide")

st.title("Funnel & Retention")
st.markdown("Task conversion funnel and user retention cohorts")

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

# ── Funnel: compute 7-step counts via conditional aggregation ───────────────
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
            "user_count": val,
            "pct_of_step1": pct_of_step1,
            "pct_of_prior_step": pct_of_prior,
        }
    )
    prev_val = val

funnel = pd.DataFrame(funnel_rows)

# ── Retention: query mart_retention_cohort (date + channel only) ────────────
retention_where = ["cohort_date BETWEEN ? AND ?"]
retention_params = [ds, de]

if channel != "All":
    retention_where.append("acquisition_channel = ?")
    retention_params.append(channel)

retention_where_sql = " AND ".join(retention_where)

retention = query_df(
    f"""
    SELECT cohort_date, acquisition_channel, eligible_users,
           d1_retained_users, d7_retained_users, d30_retained_users,
           d1_retention_rate, d7_retention_rate, d30_retention_rate
    FROM main_marts.mart_retention_cohort
    WHERE {retention_where_sql}
    ORDER BY cohort_date
    """,
    retention_params,
)

# ── Summary KPIs ─────────────────────────────────────────────────────────────
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
                "help": "Number of unique users who reached export (final step).",
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

# ── Funnel Chart ─────────────────────────────────────────────────────────────
st.subheader("Conversion Funnel")

if not funnel.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=funnel["user_count"],
            y=funnel["step_name"],
            orientation="h",
            marker={
                "color": funnel["pct_of_prior_step"],
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
    display = funnel[["step_name", "user_count", "pct_of_step1", "pct_of_prior_step"]].copy()
    display["user_count"] = display["user_count"].apply(lambda v: f"{v:,}")
    display["pct_of_step1"] = display["pct_of_step1"].apply(lambda v: f"{v:.1%}")
    display["pct_of_prior_step"] = display["pct_of_prior_step"].apply(lambda v: f"{v:.1%}")
    display.columns = ["Step", "Users", "vs Step 1", "vs Prior Step"]
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No funnel data to display.")

# ── Retention Chart ──────────────────────────────────────────────────────────
st.subheader("Retention Cohorts")

if not retention.empty:
    available_channels = retention["acquisition_channel"].dropna().unique()
    palette = px.colors.qualitative.Plotly

    fig = go.Figure()
    for i, ch in enumerate(available_channels):
        subset = retention[retention["acquisition_channel"] == ch].sort_values("cohort_date")
        fig.add_trace(
            go.Scatter(
                x=subset["cohort_date"],
                y=subset["d1_retention_rate"],
                mode="lines+markers",
                name=f"D1 — {ch}",
                line={"color": palette[i % len(palette)], "dash": "dot"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["cohort_date"],
                y=subset["d7_retention_rate"],
                mode="lines+markers",
                name=f"D7 — {ch}",
                line={"color": palette[i % len(palette)], "dash": "dash"},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["cohort_date"],
                y=subset["d30_retention_rate"],
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
        retention.groupby("acquisition_channel")[
            ["d1_retention_rate", "d7_retention_rate", "d30_retention_rate"]
        ]
        .mean()
        .reset_index()
    )
    for col in ["d1_retention_rate", "d7_retention_rate", "d30_retention_rate"]:
        avg_ret[col] = avg_ret[col].apply(lambda v: f"{v:.1%}")
    avg_ret.columns = ["Channel", "Avg D1", "Avg D7", "Avg D30"]
    st.dataframe(avg_ret, use_container_width=True, hide_index=True)
else:
    st.info("No retention data available for the selected filters.")

# ── Filter Applicability Note ────────────────────────────────────────────────
st.info("Device and complexity filters apply to the task funnel. " "Retention is cohort-level.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
