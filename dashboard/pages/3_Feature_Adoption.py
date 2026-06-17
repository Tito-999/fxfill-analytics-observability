"""Feature Adoption — Adoption rates, time-to-first-use, and segment analysis."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="Feature Adoption", layout="wide")
st.title("Feature Adoption Analysis")
st.markdown("Adoption rates for key product features by user segment")

filters = render_filters(page_name="feature")
ds = filters["date_start"]
de = filters["date_end"]
device = filters.get("device_type", "All")
complexity = filters.get("complexity", "All")

conn = get_connection()


def q(query_str: str) -> pd.DataFrame:
    return conn.execute(query_str).fetchdf()


device_filter = "" if device == "All" else f"AND device_type = '{device}'"
comp_filter = "" if complexity == "All" else f"AND complexity = '{complexity}'"

# ── Feature Adoption Rates (segmented mart) ──
adoption = q(
    f"""
    SELECT
        feature_name,
        user_segment,
        device_type,
        complexity,
        SUM(total_users) AS total_users,
        SUM(adopted_users) AS adopted_users,
        SUM(adopted_users) * 1.0 / NULLIF(SUM(total_users), 0) AS adoption_rate
    FROM main_marts.mart_feature_adoption_segmented
    WHERE event_date BETWEEN '{ds}' AND '{de}'
      {device_filter}
      {comp_filter}
    GROUP BY feature_name, user_segment, device_type, complexity
    ORDER BY feature_name, user_segment
"""
)

# ── Time-to-first-use ──
ttfu = q(
    f"""
    SELECT
        feature_name,
        days_to_first_use,
        SUM(user_count) AS user_count
    FROM main_marts.mart_feature_time_to_first_use
    WHERE first_use_date BETWEEN '{ds}' AND '{de}'
      {device_filter}
      {comp_filter}
    GROUP BY feature_name, days_to_first_use
    ORDER BY feature_name, days_to_first_use
"""
)

# KPI cards
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

# ── Adoption by segment ──
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

# ── Time-to-first-use distribution ──
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

# ── Overall adoption trend (original wide mart) ──
st.subheader("Daily Feature Adoption Trend")
trend = q(
    f"""
    SELECT event_date, ocr_adoption, anonymization_adoption,
           risk_detection_adoption, autofill_adoption
    FROM main_marts.mart_feature_adoption
    WHERE event_date BETWEEN '{ds}' AND '{de}'
    ORDER BY event_date
"""
)
if not trend.empty:
    trend_long = trend.melt(id_vars="event_date", var_name="feature", value_name="rate")
    fig3 = px.line(trend_long, x="event_date", y="rate", color="feature", title="Daily Feature Adoption Trend")
    fig3.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig3, use_container_width=True)

st.caption("Feature adoption and retention are observational associations, not causal effects.")
st.caption("ALL DATA IS SYNTHETIC")
