"""Root Cause Analysis — Export rate decline decomposition by segment and dimension."""

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="Root Cause Analysis", layout="wide")

st.title("Root Cause Analysis")
st.markdown("Export rate decline decomposition: current 7 days vs prior 7 days")

filters = render_filters(page_name="root_cause")
ds = filters["date_start"]
de = filters["date_end"]
model = filters.get("model_name", "All")

conn = get_connection()


def q(query_str: str) -> pd.DataFrame:
    return conn.execute(query_str).fetchdf()


model_clause = "" if model == "All" else f"AND model_name = '{model}'"

# ── Determine two 7-day windows within the selected range ────────────────
date_range = q(
    f"""
    SELECT MIN(date) AS min_date, MAX(date) AS max_date
    FROM main_marts.mart_daily_product_kpis
    WHERE date BETWEEN '{ds}' AND '{de}'
"""
)

if date_range.empty or date_range.iloc[0]["min_date"] is None:
    st.error("No data available in selected date range.")
    st.markdown("---")
    st.caption("⚠️ **ALL DATA IS SYNTHETIC.**")
    st.stop()

min_d = date_range.iloc[0]["min_date"]
max_d = date_range.iloc[0]["max_date"]

# Current 7 days
current_end = max_d
current_start = max_d - timedelta(days=6)
# Prior 7 days
prior_end = current_start - timedelta(days=1)
prior_start = prior_end - timedelta(days=6)

st.markdown(
    f"**Analysis windows:** Current = {current_start} to {current_end} | "
    f"Prior = {prior_start} to {prior_end}"
)

# ── Overall Export Rate ──────────────────────────────────────────────────
overall_current = q(
    f"""
    SELECT AVG(export_rate) AS export_rate
    FROM main_marts.mart_daily_product_kpis
    WHERE date BETWEEN '{current_start}' AND '{current_end}'
      {model_clause}
"""
)
overall_prior = q(
    f"""
    SELECT AVG(export_rate) AS export_rate
    FROM main_marts.mart_daily_product_kpis
    WHERE date BETWEEN '{prior_start}' AND '{prior_end}'
      {model_clause}
"""
)

cur_rate = overall_current.iloc[0]["export_rate"] if not overall_current.empty else 0
pri_rate = overall_prior.iloc[0]["export_rate"] if not overall_prior.empty else 0
rate_change = cur_rate - pri_rate
pct_change = rate_change / pri_rate if pri_rate != 0 else 0

kpi_row(
    [
        {
            "label": "Prior 7d Export Rate",
            "value": pri_rate if pri_rate else 0,
            "help": "Average export rate in the prior 7-day window.",
        },
        {
            "label": "Current 7d Export Rate",
            "value": cur_rate if cur_rate else 0,
            "help": "Average export rate in the current 7-day window.",
        },
        {
            "label": "Absolute Change",
            "value": rate_change,
            "delta": f"{rate_change:+.2%}",
            "help": "Change in export rate between the two periods.",
            "delta_color": "inverse",
        },
    ]
)

if rate_change >= 0:
    st.success(
        f"Export rate is stable or improving (+{rate_change:+.2%}). "
        "No decline to analyze. Decomposition below still shows contributions by segment."
    )
else:
    st.error(
        f"Export rate declined by {rate_change:.2%} "
        f"({pct_change:.1%} relative decline). Decomposing by dimension..."
    )

# ── Dimension Decomposition ──────────────────────────────────────────────


def decompose_by(
    dimension: str, table: str = "main_marts.mart_daily_product_kpis", join_col: str = "date"
) -> pd.DataFrame:
    """Compute contribution of each segment in a dimension to the overall export rate change.

    Contribution = (prior_volume_share * rate_change_for_segment)
    """
    current = q(
        f"""
        SELECT
            {dimension} AS segment,
            COUNT(*)     AS volume,
            AVG(export_rate) AS export_rate
        FROM {table}
        WHERE date BETWEEN '{current_start}' AND '{current_end}'
          {model_clause}
        GROUP BY {dimension}
    """
    )
    prior = q(
        f"""
        SELECT
            {dimension} AS segment,
            COUNT(*)     AS volume,
            AVG(export_rate) AS export_rate
        FROM {table}
        WHERE date BETWEEN '{prior_start}' AND '{prior_end}'
          {model_clause}
        GROUP BY {dimension}
    """
    )

    merged = prior.merge(current, on="segment", how="outer", suffixes=("_prior", "_current"))
    merged = merged.fillna(0)

    total_prior_volume = merged["volume_prior"].sum()
    if total_prior_volume == 0:
        return merged

    merged["prior_share"] = merged["volume_prior"] / total_prior_volume
    merged["rate_change"] = merged["export_rate_current"] - merged["export_rate_prior"]
    merged["contribution"] = merged["prior_share"] * merged["rate_change"]
    merged = merged.sort_values("contribution", ascending=False)
    return merged


dimensions = [
    ("user_segment", "Decomposition by User Segment"),
    ("device_type", "Decomposition by Device Type"),
    ("channel", "Decomposition by Channel"),
    ("app_version", "Decomposition by App Version"),
    ("complexity", "Decomposition by Task Complexity"),
]

col1, col2 = st.columns(2)
current_col = col1

for _i, (dim, title) in enumerate(dimensions):
    with current_col:
        st.subheader(title)
        result = decompose_by(dim)
        if result.empty:
            st.info(f"No data for {dim} decomposition.")
        else:
            fig = go.Figure()
            colors = ["#EF553B" if c < 0 else "#00CC96" for c in result["contribution"]]
            fig.add_trace(
                go.Bar(
                    x=result["contribution"],
                    y=result["segment"],
                    orientation="h",
                    marker_color=colors,
                    text=result["contribution"].apply(lambda v: f"{v:+.4f}"),
                    textposition="outside",
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Contribution: %{x:+.4f}<br>"
                        "Prior share: %{customdata[0]:.1%}<br>"
                        "Rate change: %{customdata[1]:+.2%}<br>"
                        "Prior rate: %{customdata[2]:.2%}<br>"
                        "Current rate: %{customdata[3]:.2%}"
                        "<extra></extra>"
                    ),
                    customdata=result[
                        ["prior_share", "rate_change", "export_rate_prior", "export_rate_current"]
                    ].values,
                )
            )
            fig.update_layout(
                title=title,
                xaxis_title="Contribution to Export Rate Change",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Detail
            result_display = result[
                [
                    "segment",
                    "prior_share",
                    "export_rate_prior",
                    "export_rate_current",
                    "rate_change",
                    "contribution",
                ]
            ].copy()
            for col in [
                "prior_share",
                "export_rate_prior",
                "export_rate_current",
                "rate_change",
                "contribution",
            ]:
                if "contribution" not in col:
                    result_display[col] = result_display[col].apply(lambda v: f"{v:+.2%}")
                else:
                    result_display[col] = result_display[col].apply(lambda v: f"{v:+.4f}")
            result_display.columns = [
                "Segment",
                "Prior Volume Share",
                "Prior Rate",
                "Current Rate",
                "Rate Change",
                "Contribution",
            ]
            st.dataframe(result_display, use_container_width=True, hide_index=True)

    current_col = col2 if current_col == col1 else col1

# ── Agent Error Type Decomposition ───────────────────────────────────────
st.subheader("Decomposition by Agent Error Type")

error_result = q(
    f"""
    SELECT
        error_category AS segment,
        COUNT(*) AS volume_prior,
        AVG(er.error_rate) AS export_rate_prior
    FROM main_marts.mart_error_root_cause er
    WHERE date BETWEEN '{prior_start}' AND '{prior_end}'
      {model_clause}
    GROUP BY error_category
"""
)

error_result_current = q(
    f"""
    SELECT
        error_category AS segment,
        COUNT(*) AS volume_current,
        AVG(er.error_rate) AS export_rate_current
    FROM main_marts.mart_error_root_cause er
    WHERE date BETWEEN '{current_start}' AND '{current_end}'
      {model_clause}
    GROUP BY error_category
"""
)

if not error_result.empty and not error_result_current.empty:
    merged_errors = error_result.merge(error_result_current, on="segment", how="outer").fillna(0)

    total_prior = merged_errors["volume_prior"].sum()
    if total_prior > 0:
        merged_errors["prior_share"] = merged_errors["volume_prior"] / total_prior
        merged_errors["rate_change"] = (
            merged_errors["export_rate_current"] - merged_errors["export_rate_prior"]
        )
        merged_errors["contribution"] = merged_errors["prior_share"] * merged_errors["rate_change"]

        fig = go.Figure()
        merged_errors = merged_errors.sort_values("contribution", ascending=False)
        colors = ["#EF553B" if c < 0 else "#00CC96" for c in merged_errors["contribution"]]
        fig.add_trace(
            go.Bar(
                x=merged_errors["contribution"],
                y=merged_errors["segment"],
                orientation="h",
                marker_color=colors,
                text=merged_errors["contribution"].apply(lambda v: f"{v:+.4f}"),
                textposition="outside",
            )
        )
        fig.update_layout(title="Decomposition by Error Type", height=300)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No error decomposition data available.")
else:
    st.info("No error type data available for decomposition.")

# ── Top Contributors Summary ─────────────────────────────────────────────
st.subheader("Top Contributors to Export Rate Change")

all_contributions = []
for dim, _title in dimensions:
    result = decompose_by(dim)
    if not result.empty:
        for _, row in result.iterrows():
            all_contributions.append(
                {
                    "dimension": dim,
                    "segment": row["segment"],
                    "contribution": row["contribution"],
                    "rate_change": row["rate_change"],
                    "prior_share": row["prior_share"],
                }
            )

if all_contributions:
    contrib_df = pd.DataFrame(all_contributions)
    top_positive = (
        contrib_df[contrib_df["contribution"] > 0]
        .sort_values("contribution", ascending=False)
        .head(5)
    )
    top_negative = (
        contrib_df[contrib_df["contribution"] < 0]
        .sort_values("contribution", ascending=True)
        .head(5)
    )

    col_pos, col_neg = st.columns(2)

    with col_pos:
        st.markdown("**Top Positive Contributors**")
        if not top_positive.empty:
            for _, r in top_positive.iterrows():
                st.markdown(
                    f"- **{r['dimension']}**: {r['segment']} "
                    f"(contribution {r['contribution']:+.4f}, rate Δ {r['rate_change']:+.2%})"
                )
        else:
            st.info("No positive contributors identified.")

    with col_neg:
        st.markdown("**Top Negative Contributors**")
        if not top_negative.empty:
            for _, r in top_negative.iterrows():
                st.markdown(
                    f"- **{r['dimension']}**: {r['segment']} "
                    f"(contribution {r['contribution']:+.4f}, rate Δ {r['rate_change']:+.2%})"
                )
        else:
            st.info("No negative contributors identified.")

# ── Interpretation Framework ─────────────────────────────────────────────
st.subheader("Interpretation Framework")

st.markdown(
    """
**Observed facts:**
- The numbers above show the measured difference in export rates between the two periods.
- Each segment's contribution is calculated as: `prior_volume_share * segment_rate_change`.
- This is an arithmetic decomposition, not a statistical model.

**Analytical inference:**
- Segments with large negative contributions are the primary drivers of any observed decline.
- A segment may have a large negative rate change but small contribution if it was a small share of prior volume.
- Conversely, a large segment with a modest rate change can dominate the overall movement.

**Hypotheses requiring validation:**
- Were there product changes, model updates, or infrastructure issues during the current period?
- Did the mix of incoming users or tasks change between the two periods?
- Are there correlated shifts across dimensions (e.g., a particular user segment shifted to a device type with lower export rates)?

**Recommended next actions:**
1. Investigate the top negative contributing segments for operational or product changes.
2. Review model version deployments or prompt changes that may have affected agent output quality.
3. Examine whether the segment mix shifted (composition effect) versus within-segment rate changes.
4. Cross-reference with A/B test results and agent observability data for converging evidence.
"""
)

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("⚠️ **ALL DATA IS SYNTHETIC.** No real user, financial, or business data is displayed.")
