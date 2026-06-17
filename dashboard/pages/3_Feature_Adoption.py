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


device_clause = "" if device == "All" else f"AND device_type = '{device}'"
complexity_clause = "" if complexity == "All" else f"AND complexity = '{complexity}'"

# ── Feature Adoption Rates ───────────────────────────────────────────────
adoption = q(
    f"""
    SELECT
        feature_name,
        total_users,
        adopted_users,
        adoption_rate,
        user_segment
    FROM main_marts.mart_feature_adoption
    WHERE date BETWEEN '{ds}' AND '{de}'
      {device_clause}
      {complexity_clause}
    ORDER BY feature_name, user_segment
"""
)

# ── Time-to-first-use ────────────────────────────────────────────────────
ttfu = q(
    f"""
    SELECT
        feature_name,
        days_to_first_use,
        user_count
    FROM main_marts.mart_feature_adoption
    WHERE date BETWEEN '{ds}' AND '{de}'
      AND days_to_first_use IS NOT NULL
      {device_clause}
      {complexity_clause}
    ORDER BY feature_name, days_to_first_use
"""
)

# ── Summary KPIs ─────────────────────────────────────────────────────────
if not adoption.empty:
    overall = (
        adoption.groupby("feature_name")
        .agg(
            total_users=("total_users", "sum"),
            adopted_users=("adopted_users", "sum"),
        )
        .reset_index()
    )
    overall["adoption_rate"] = overall["adopted_users"] / overall["total_users"]

    features = ["OCR", "Anonymization", "Risk Detection", "Autofill"]

    cards = []
    for feat in features:
        row = overall[overall["feature_name"].str.lower().str.contains(feat.lower(), na=False)]
        if not row.empty:
            r = row.iloc[0]
            cards.append(
                {
                    "label": f"{feat} Adoption",
                    "value": r["adoption_rate"] if r["total_users"] > 0 else 0,
                    "help": f"Fraction of users who have used {feat} at least once.",
                }
            )
        else:
            cards.append(
                {
                    "label": f"{feat} Adoption",
                    "value": 0,
                    "help": f"Fraction of users who have used {feat} at least once.",
                }
            )

    if cards:
        kpi_row(cards, cols=4)
    else:
        st.info("No adoption data available.")
else:
    st.info("No feature adoption data available for the selected filters.")
    st.stop()

# ── Adoption Rate Chart ──────────────────────────────────────────────────
st.subheader("Adoption Rate by Feature")

fig = go.Figure()
overall_sorted = overall.sort_values("adoption_rate", ascending=True)
fig.add_trace(
    go.Bar(
        x=overall_sorted["adoption_rate"],
        y=overall_sorted["feature_name"],
        orientation="h",
        text=overall_sorted["adoption_rate"].apply(lambda v: f"{v:.1%}"),
        textposition="outside",
        marker_color="#636EFA",
    )
)
fig.update_layout(
    title="Overall Feature Adoption Rates",
    xaxis_title="Adoption Rate",
    xaxis_tickformat=".0%",
    height=400,
)
st.plotly_chart(fig, use_container_width=True)

# ── Adoption by User Segment ─────────────────────────────────────────────
st.subheader("Adoption by User Segment")

if not adoption.empty:
    segments = adoption["user_segment"].dropna().unique()
    features_list = adoption["feature_name"].unique()

    fig = go.Figure()
    for _i, feat in enumerate(features_list):
        subset = adoption[adoption["feature_name"] == feat]
        fig.add_trace(
            go.Bar(
                name=feat,
                x=subset["user_segment"],
                y=subset["adoption_rate"],
                text=subset["adoption_rate"].apply(lambda v: f"{v:.1%}"),
            )
        )

    fig.update_layout(
        title="Adoption Rate by Feature and User Segment",
        xaxis_title="User Segment",
        yaxis_title="Adoption Rate",
        yaxis_tickformat=".0%",
        barmode="group",
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tabular detail
    detail = adoption.copy()
    detail["adoption_rate"] = detail["adoption_rate"].apply(lambda v: f"{v:.1%}")
    detail["total_users"] = detail["total_users"].apply(lambda v: f"{v:,}")
    detail["adopted_users"] = detail["adopted_users"].apply(lambda v: f"{v:,}")
    st.dataframe(
        detail[["feature_name", "user_segment", "total_users", "adopted_users", "adoption_rate"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "feature_name": "Feature",
            "user_segment": "Segment",
            "total_users": "Total Users",
            "adopted_users": "Adopted Users",
            "adoption_rate": "Adoption Rate",
        },
    )
else:
    st.info("No segment-level adoption data.")

# ── Time-to-First-Use Distribution ───────────────────────────────────────
st.subheader("Time-to-First-Use Distribution")

if not ttfu.empty:
    ttfu_grouped = (
        ttfu.groupby(["feature_name", "days_to_first_use"])["user_count"].sum().reset_index()
    )

    fig = px.histogram(
        ttfu_grouped,
        x="days_to_first_use",
        y="user_count",
        color="feature_name",
        nbins=30,
        title="Days to First Use by Feature",
        labels={"days_to_first_use": "Days since signup", "user_count": "Users"},
    )
    fig.update_layout(barmode="overlay", height=400)
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    ttfu_stats = ttfu_grouped.groupby("feature_name")["days_to_first_use"].describe()
    st.dataframe(ttfu_stats, use_container_width=True)
else:
    st.info("No time-to-first-use data available.")

# ── Causal Note ──────────────────────────────────────────────────────────
st.info(
    "Observational association, not causal. "
    "Adoption patterns reflect correlational trends and may be influenced "
    "by user selection effects, product exposure differences, or other "
    "confounding factors. Controlled experiments are needed for causal claims."
)

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ **ALL DATA IS SYNTHETIC.** No real user, financial, or business data is displayed.")
