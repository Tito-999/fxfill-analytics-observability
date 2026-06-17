"""Feature Adoption — Adoption rates, time-to-first-use, and segment analysis."""

import plotly.express as px
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="Feature Adoption", layout="wide")
st.title("Feature Adoption Analysis")
st.markdown("Adoption rates for key product features by user segment")

filters = render_filters(page_name="feature")
ds = filters["date_start"]
de = filters["date_end"]
device = filters.get("device_type", "All")
complexity = filters.get("complexity", "All")

# ── Build dynamic WHERE clauses ─────────────────────────────────────────────
seg_where = ["event_date BETWEEN ? AND ?"]
seg_params = [ds, de]
ttfu_where = ["first_use_date BETWEEN ? AND ?"]
ttfu_params = [ds, de]

if device != "All":
    seg_where.append("device_type = ?")
    seg_params.append(device)
    ttfu_where.append("device_type = ?")
    ttfu_params.append(device)
if complexity != "All":
    seg_where.append("complexity = ?")
    seg_params.append(complexity)
    ttfu_where.append("complexity = ?")
    ttfu_params.append(complexity)

seg_where_sql = " AND ".join(seg_where)
ttfu_where_sql = " AND ".join(ttfu_where)

# ── Feature Adoption Rates (segmented mart) ─────────────────────────────────
adoption = query_df(
    f"""
    SELECT feature_name, user_segment, device_type, complexity,
           SUM(total_users) AS total_users,
           SUM(adopted_users) AS adopted_users,
           SUM(adopted_users) * 1.0 / NULLIF(SUM(total_users), 0) AS adoption_rate
    FROM main_marts.mart_feature_adoption_segmented
    WHERE {seg_where_sql}
    GROUP BY feature_name, user_segment, device_type, complexity
    ORDER BY feature_name, user_segment
    """,
    seg_params,
)

# ── Time-to-first-use ───────────────────────────────────────────────────────
ttfu = query_df(
    f"""
    SELECT feature_name, user_segment, device_type, complexity,
           days_to_first_use, SUM(user_count) AS user_count
    FROM main_marts.mart_feature_time_to_first_use
    WHERE {ttfu_where_sql}
    GROUP BY feature_name, user_segment, device_type, complexity, days_to_first_use
    ORDER BY feature_name, days_to_first_use
    """,
    ttfu_params,
)

# ── KPI cards ────────────────────────────────────────────────────────────────
if not adoption.empty:
    overall = (
        adoption.groupby("feature_name")
        .agg(total_users=("total_users", "sum"), adopted_users=("adopted_users", "sum"))
        .reset_index()
    )
    overall["adoption_rate"] = overall["adopted_users"] / overall["total_users"].replace(0, 1)
    kpi_data = []
    for _, row in overall.iterrows():
        kpi_data.append(
            {
                "label": row["feature_name"],
                "value": row["adoption_rate"],
                "help": f"{int(row['adopted_users'])} / {int(row['total_users'])} users adopted {row['feature_name']}",
            }
        )
    if kpi_data:
        kpi_row(kpi_data, cols=min(len(kpi_data), 4))
else:
    st.info("No adoption data for the selected filters.")

# ── Adoption by segment ──────────────────────────────────────────────────────
st.subheader("Feature Adoption by User Segment")
if not adoption.empty:
    seg_data = adoption.groupby(["feature_name", "user_segment"], as_index=False).agg(
        {"total_users": "sum", "adopted_users": "sum"}
    )
    seg_data["adoption_rate"] = seg_data["adopted_users"] / seg_data["total_users"].replace(0, 1)
    fig = px.bar(
        seg_data,
        x="feature_name",
        y="adoption_rate",
        color="user_segment",
        barmode="group",
        title="Adoption Rate by Feature and Segment",
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No adoption data for the selected filters.")

# ── Time-to-first-use distribution ───────────────────────────────────────────
st.subheader("Time to First Use (Days)")
if not ttfu.empty:
    fig2 = px.histogram(
        ttfu,
        x="days_to_first_use",
        y="user_count",
        color="feature_name",
        barmode="overlay",
        nbins=30,
        title="Days from Signup to First Feature Use",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No time-to-first-use data for the selected filters.")

# ── Overall adoption trend (wide mart, no device/complexity filters) ────────
st.subheader("Daily Feature Adoption Trend")
trend = query_df(
    """
    SELECT event_date, total_tasks, ocr_adoption, anonymization_adoption,
           risk_detection_adoption, autofill_adoption
    FROM main_marts.mart_feature_adoption
    WHERE event_date BETWEEN ? AND ?
    ORDER BY event_date
    """,
    [ds, de],
)
if not trend.empty:
    trend_long = trend.melt(
        id_vars="event_date",
        value_vars=[
            "ocr_adoption",
            "anonymization_adoption",
            "risk_detection_adoption",
            "autofill_adoption",
        ],
        var_name="feature",
        value_name="rate",
    )
    fig3 = px.line(
        trend_long,
        x="event_date",
        y="rate",
        color="feature",
        title="Daily Feature Adoption Trend",
    )
    fig3.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No daily adoption trend data available.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.caption("Observational association, not causal effect.")
st.caption("ALL DATA IS SYNTHETIC")
