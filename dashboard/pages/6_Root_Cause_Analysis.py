"""Root Cause Analysis — Export rate decline decomposition via Kitagawa."""

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.query import query_df

st.set_page_config(page_title="Root Cause Analysis", layout="wide")

st.title("Root Cause Analysis")
st.markdown("Export rate decline decomposition: current 7 days vs prior 7 days")

filters = render_filters(page_name="root_cause")
ds = filters["date_start"]
de = filters["date_end"]

# ── Determine two 7-day windows within the selected range ────────────────────
date_range = query_df(
    """
    SELECT MIN(event_date) AS min_date, MAX(event_date) AS max_date
    FROM main_marts.mart_export_rate_dimension_daily
    WHERE event_date BETWEEN ? AND ?
    """,
    [ds, de],
)

if date_range.empty or date_range.iloc[0]["min_date"] is None:
    st.error("No data available in selected date range.")
    st.markdown("---")
    st.caption("ALL DATA IS SYNTHETIC")
    st.stop()

min_d = date_range.iloc[0]["min_date"]
max_d = date_range.iloc[0]["max_date"]

# Current window: last 7 days ending at max_d
current_end = max_d
current_start = max_d - timedelta(days=6)
# Prior window: 7 days before current window
prior_end = current_start - timedelta(days=1)
prior_start = prior_end - timedelta(days=6)

st.markdown(
    f"**Analysis windows:** Current = {current_start} to {current_end} | "
    f"Prior = {prior_start} to {prior_end}"
)

# ── Overall Export Rate ──────────────────────────────────────────────────────
overall_current = query_df(
    """
    SELECT AVG(export_rate) AS export_rate
    FROM main_marts.mart_export_rate_dimension_daily
    WHERE event_date BETWEEN ? AND ?
    """,
    [current_start, current_end],
)
overall_prior = query_df(
    """
    SELECT AVG(export_rate) AS export_rate
    FROM main_marts.mart_export_rate_dimension_daily
    WHERE event_date BETWEEN ? AND ?
    """,
    [prior_start, prior_end],
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
        f"Export rate is stable or improving ({rate_change:+.2%}). "
        "No decline to analyze. Decomposition below still shows contributions by segment."
    )
else:
    st.error(
        f"Export rate declined by {rate_change:.2%} "
        f"({pct_change:.1%} relative decline). Decomposing by dimension..."
    )

# ── Discover available dimensions ────────────────────────────────────────────
dims_df = query_df(
    """
    SELECT DISTINCT dimension_name
    FROM main_marts.mart_export_rate_dimension_daily
    ORDER BY dimension_name
    """
)
dimensions = dims_df["dimension_name"].tolist() if not dims_df.empty else []


def kitagawa_decompose(dimension_name_str):
    """Kitagawa decomposition for a single dimension.

    Rate effect:  0.5 * (share_p + share_c) * (rate_c - rate_p)
    Mix effect:   0.5 * (rate_p + rate_c) * (share_c - share_p)
    """
    current = query_df(
        """
        SELECT segment, SUM(total_tasks) AS volume,
               SUM(exported_tasks) * 1.0 / NULLIF(SUM(total_tasks), 0) AS export_rate
        FROM main_marts.mart_export_rate_dimension_daily
        WHERE dimension_name = ?
          AND event_date BETWEEN ? AND ?
        GROUP BY segment
        """,
        [dimension_name_str, current_start, current_end],
    )
    prior = query_df(
        """
        SELECT segment, SUM(total_tasks) AS volume,
               SUM(exported_tasks) * 1.0 / NULLIF(SUM(total_tasks), 0) AS export_rate
        FROM main_marts.mart_export_rate_dimension_daily
        WHERE dimension_name = ?
          AND event_date BETWEEN ? AND ?
        GROUP BY segment
        """,
        [dimension_name_str, prior_start, prior_end],
    )

    if current.empty and prior.empty:
        return None, None

    merged = prior.merge(current, on="segment", how="outer", suffixes=("_p", "_c")).fillna(0)

    total_vol_p = merged["volume_p"].sum()
    total_vol_c = merged["volume_c"].sum()
    if total_vol_p == 0 or total_vol_c == 0:
        return merged, None

    merged["share_p"] = merged["volume_p"] / total_vol_p
    merged["share_c"] = merged["volume_c"] / total_vol_c

    # Kitagawa decomposition
    merged["rate_effect"] = (
        0.5 * (merged["share_p"] + merged["share_c"]) * (merged["export_rate_c"] - merged["export_rate_p"])
    )
    merged["mix_effect"] = (
        0.5 * (merged["export_rate_p"] + merged["export_rate_c"]) * (merged["share_c"] - merged["share_p"])
    )
    merged["total_effect"] = merged["rate_effect"] + merged["mix_effect"]

    # Overall rate change for this dimension
    overall_rate_p = (merged["volume_p"] * merged["export_rate_p"]).sum() / total_vol_p
    overall_rate_c = (merged["volume_c"] * merged["export_rate_c"]).sum() / total_vol_c
    rate_change_dim = overall_rate_c - overall_rate_p

    total_rate_effect = merged["rate_effect"].sum()
    total_mix_effect = merged["mix_effect"].sum()
    residual = rate_change_dim - total_rate_effect - total_mix_effect

    merged = merged.sort_values("total_effect", ascending=False)
    return merged, residual


# ── Dimension Decomposition ──────────────────────────────────────────────────
col1, col2 = st.columns(2)
current_col = col1

all_contributions = []

for dim in dimensions:
    with current_col:
        st.subheader(f"Decomposition by {dim}")
        result, residual = kitagawa_decompose(dim)

        if result is None:
            st.info(f"No data for {dim} decomposition.")
            current_col = col2 if current_col == col1 else col1
            continue

        if residual is None:
            st.info(f"Insufficient data for {dim}.")
            current_col = col2 if current_col == col1 else col1
            continue

        # Accumulate for top contributors
        for _, row in result.iterrows():
            all_contributions.append(
                {
                    "dimension": dim,
                    "segment": row["segment"],
                    "total_effect": row["total_effect"],
                    "rate_effect": row["rate_effect"],
                    "mix_effect": row["mix_effect"],
                    "rate_change": row["export_rate_c"] - row["export_rate_p"],
                    "prior_share": row["share_p"],
                }
            )

        # Chart
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=result["rate_effect"],
                y=result["segment"],
                orientation="h",
                name="Rate Effect",
                marker_color="#636EFA",
                text=result["rate_effect"].apply(lambda v: f"{v:+.4f}"),
                textposition="outside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Rate effect: %{x:+.4f}<br>"
                    "Prior share: %{customdata[0]:.1%}<br>"
                    "Prior rate: %{customdata[1]:.2%}<br>"
                    "Current rate: %{customdata[2]:.2%}"
                    "<extra></extra>"
                ),
                customdata=result[["share_p", "export_rate_p", "export_rate_c"]].values,
            )
        )
        fig.add_trace(
            go.Bar(
                x=result["mix_effect"],
                y=result["segment"],
                orientation="h",
                name="Mix Effect",
                marker_color="#00CC96",
                text=result["mix_effect"].apply(lambda v: f"{v:+.4f}"),
                textposition="outside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Mix effect: %{x:+.4f}<br>"
                    "Prior share: %{customdata[0]:.1%}<br>"
                    "Current share: %{customdata[1]:.1%}"
                    "<extra></extra>"
                ),
                customdata=result[["share_p", "share_c"]].values,
            )
        )
        fig.update_layout(
            title=f"{dim} — Rate vs Mix Effect",
            xaxis_title="Effect on Export Rate",
            barmode="relative",
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Residual check
        residual_ok = abs(residual) < 1e-9
        st.caption(
            f"Residual: {residual:+.2e} — "
            f"{'PASS (|residual| < 1e-9)' if residual_ok else 'FAIL'}"
        )

        # Detail table
        result_display = result[
            ["segment", "share_p", "share_c", "export_rate_p", "export_rate_c",
             "rate_effect", "mix_effect", "total_effect"]
        ].copy()
        for c in ["share_p", "share_c", "export_rate_p", "export_rate_c"]:
            result_display[c] = result_display[c].apply(lambda v: f"{v:+.2%}")
        for c in ["rate_effect", "mix_effect", "total_effect"]:
            result_display[c] = result_display[c].apply(lambda v: f"{v:+.4f}")
        result_display.columns = [
            "Segment", "Prior Share", "Current Share",
            "Prior Rate", "Current Rate",
            "Rate Effect", "Mix Effect", "Total Effect",
        ]
        st.dataframe(result_display, use_container_width=True, hide_index=True)

    current_col = col2 if current_col == col1 else col1

# ── Top Contributors Summary ─────────────────────────────────────────────────
st.subheader("Top Contributors to Export Rate Change")

if all_contributions:
    contrib_df = pd.DataFrame(all_contributions)
    top_positive = (
        contrib_df[contrib_df["total_effect"] > 0]
        .sort_values("total_effect", ascending=False)
        .head(5)
    )
    top_negative = (
        contrib_df[contrib_df["total_effect"] < 0]
        .sort_values("total_effect", ascending=True)
        .head(5)
    )

    col_pos, col_neg = st.columns(2)

    with col_pos:
        st.markdown("**Top Positive Contributors**")
        if not top_positive.empty:
            for _, r in top_positive.iterrows():
                st.markdown(
                    f"- **{r['dimension']}**: {r['segment']} "
                    f"(total effect {r['total_effect']:+.4f}, "
                    f"rate Δ {r['rate_change']:+.2%})"
                )
        else:
            st.info("No positive contributors identified.")

    with col_neg:
        st.markdown("**Top Negative Contributors**")
        if not top_negative.empty:
            for _, r in top_negative.iterrows():
                st.markdown(
                    f"- **{r['dimension']}**: {r['segment']} "
                    f"(total effect {r['total_effect']:+.4f}, "
                    f"rate Δ {r['rate_change']:+.2%})"
                )
        else:
            st.info("No negative contributors identified.")
else:
    st.info("No contribution data available.")

# ── Interpretation Framework ─────────────────────────────────────────────────
st.subheader("Interpretation Framework")

st.markdown(
    """
**Observed facts:**
- The numbers above decompose the change in export rate using the Kitagawa Oaxaca method.
- **Rate effect:** change due to within-segment rate changes (holding composition constant).
- **Mix effect:** change due to shifts in segment composition (holding rates constant).
- The residual (rate change - rate effect - mix effect) should be near zero.

**Analytical inference:**
- A large negative **rate effect** in a segment means its export rate dropped.
- A large negative **mix effect** means the segment's share of volume shrank (or a low-rate segment grew).
- Segments with large negative total effects are the primary drivers of any observed decline.

**Hypotheses requiring validation:**
- Were there product changes, model updates, or infrastructure issues during the current period?
- Did the mix of incoming users or tasks change between the two periods?
- Are there correlated shifts across dimensions?

**Recommended next actions:**
1. Investigate the top negative contributing segments for operational or product changes.
2. Review model version deployments or prompt changes that may have affected agent output quality.
3. Cross-reference with A/B test results and agent observability data for converging evidence.
4. Check for data pipeline issues that may have affected the prior or current window.
"""
)

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("ALL DATA IS SYNTHETIC")
