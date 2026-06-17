"""Data Quality — Pipeline audit results, reconciliation status, and row-count comparisons."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.filters import render_filters
from dashboard.components.kpi_cards import kpi_row
from dashboard.services.database import get_connection

st.set_page_config(page_title="Data Quality", layout="wide")

st.title("Data Quality Dashboard")
st.markdown("Pipeline audit results, reconciliation checks, and schema-level row counts")

filters = render_filters(page_name="all")
# Data Quality uses fixed reports, not date-filtered queries

conn = get_connection()


def q(query_str: str) -> pd.DataFrame:
    return conn.execute(query_str).fetchdf()


def load_report(relative_path: str) -> dict:
    """Load a JSON report from the reports/ directory."""
    path = Path(__file__).resolve().parent.parent.parent / relative_path
    if not path.exists():
        st.error(f"Report not found: {path}")
        return {}
    with open(path) as f:
        return json.load(f)


phase1 = load_report("reports/phase1_final_audit.json")
phase2 = load_report("reports/phase2_final_audit.json")

# ── Phase 1 Checks Summary ───────────────────────────────────────────────
st.subheader("Phase 1 — Phenomena Validation Checks")

p1_phenomena = phase1.get("phenomena", [])
total_checks = len(p1_phenomena)
passed_checks = sum(1 for p in p1_phenomena if p.get("passed"))
warnings = sum(1 for p in p1_phenomena if not p.get("passed"))
anomalies_detected = sum(1 for p in p1_phenomena if p.get("phenomenon_id") in ("P07", "P08"))

if total_checks > 0:
    kpi_row(
        [
            dict(
                label="Total Checks (P01-P10)",
                value=total_checks,
                help="All 10 predefined phenomena checks (P01 through P10).",
            ),
            dict(
                label="Passed",
                value=passed_checks,
                help="Checks whose observed value met the configured threshold.",
            ),
            dict(
                label="Warnings / Failures",
                value=warnings,
                help="Checks where the observed value did not meet expectations.",
            ),
            dict(
                label="Anomalies Detected (P07/P08)",
                value=anomalies_detected,
                help="P07 = duplicate upload spike, P08 = cross-group experiment contamination.",
            ),
        ],
        cols=4,
    )

    # Phase 1 detail table
    rows = []
    for p in p1_phenomena:
        rows.append(
            {
                "ID": p["phenomenon_id"],
                "Metric": p["metric_name"],
                "Baseline Group": p.get("baseline_group", ""),
                "Affected Group": p.get("affected_group", ""),
                "Baseline Value": p.get("baseline_value", ""),
                "Affected Value": p.get("affected_value", ""),
                "Effect": p.get("absolute_effect", p.get("relative_effect", "")),
                "Passed": "YES" if p.get("passed") else "NO",
            }
        )
    df_p1 = pd.DataFrame(rows)
    st.dataframe(df_p1, use_container_width=True, hide_index=True)
else:
    st.info("No Phase 1 phenomena data loaded.")

# ── Phase 2 dbt Tests ────────────────────────────────────────────────────
st.subheader("Phase 2 — dbt Tests & Quality Gates")

p2_eng = phase1.get("engineering_gates", {})
p2_wh = phase2.get("warehouse", {})

dbt_generic = p2_wh.get("generic_test_count", 21)
dbt_singular = p2_wh.get("singular_test_count", 10)
dbt_total = dbt_generic + dbt_singular

if p2_eng:
    pytest_passed = p2_eng.get("pytest_passed", 0)
    pytest_failed = p2_eng.get("pytest_failed", 0)
    coverage = p2_eng.get("coverage_percent", 0)
    ruff = p2_eng.get("ruff_status", "N/A")
    mypy = p2_eng.get("mypy_status", "N/A")

    kpi_row(
        [
            dict(
                label="dbt Generic Tests",
                value=dbt_generic,
                help="Standard dbt schema tests (not_null, unique, accepted_values, etc.).",
            ),
            dict(
                label="dbt Singular Tests",
                value=dbt_singular,
                help="Custom dbt data tests defined in tests/ directory.",
            ),
            dict(
                label="pytest (passed/failed)",
                value=f"{pytest_passed}/{pytest_failed}",
                help="Unit and integration test results.",
            ),
            dict(
                label="Code Coverage",
                value=coverage / 100,
                help="Line coverage percentage from pytest-cov.",
            ),
        ],
        cols=4,
    )

    quality_col1, quality_col2 = st.columns(2)
    with quality_col1:
        st.markdown("**Static Analysis**")
        checks = {
            "Ruff": ruff,
            "Mypy": mypy,
            "Black": p2_eng.get("black_status", "N/A"),
            "pip-audit": p2_eng.get("pip_check_status", "N/A"),
        }
        for tool, status in checks.items():
            icon = "✅" if status == "passed" else "❌"
            st.markdown(f"{icon} **{tool}**: {status}")

    with quality_col2:
        st.markdown("**Performance**")
        perf = phase1.get("performance", {})
        if perf:
            st.markdown(f"- Pipeline duration: {perf.get('optimized_duration_s', 'N/A')}s")
            st.markdown(f"- Speedup vs baseline: {perf.get('speedup_ratio', 'N/A')}x")
            st.markdown(f"- Peak RSS: {perf.get('peak_rss_run1_mb', 'N/A')} MB")
            st.markdown(f"- Output size: {perf.get('output_size_mb', 'N/A')} MB")
else:
    st.info("No Phase 2 engineering gate data available.")

# ── Reconciliation Status ────────────────────────────────────────────────
st.subheader("Reconciliation Status")

recon_data = phase2.get("reconciliation", {})
recon_items = recon_data.get("items", [])
all_passed = recon_data.get("all_passed", False)

n_passed_recon = sum(1 for i in recon_items if i.get("passed"))
n_total_recon = len(recon_items)

kpi_row(
    [
        dict(
            label="Reconciliation: Passed",
            value=n_passed_recon,
            help=f"Number of reconciled metrics that matched within tolerance ({n_total_recon} total).",
        ),
        dict(
            label="Reconciliation: Total",
            value=n_total_recon,
            help="Total number of reconciled metric checks.",
        ),
        dict(
            label="All Passed", value=all_passed, help="Whether every reconciliation check passed."
        ),
        dict(
            label="Schema Version",
            value=phase1.get("schema_version", "N/A"),
            help="Audit report schema version.",
        ),
    ],
    cols=4,
)

if recon_items:
    recon_rows = []
    for item in recon_items:
        recon_rows.append(
            {
                "Phenomenon": item.get("phenomenon_id", ""),
                "Metric": item.get("metric_name", ""),
                "Source Value": item.get("source_value", item.get("diff", "")),
                "Warehouse Value": item.get("warehouse_value", ""),
                "Tolerance": item.get("tolerance", ""),
                "Passed": "YES" if item.get("passed") else "NO",
            }
        )
    df_recon = pd.DataFrame(recon_rows)
    st.dataframe(df_recon, use_container_width=True, hide_index=True)
else:
    st.info("No reconciliation data available.")

# ── Canonical Hash Status ────────────────────────────────────────────────
st.subheader("Canonical Hash Status (Determinism Check)")

hashes = phase1.get("canonical_hashes", {})
if hashes:
    hash_rows = []
    for table_name, hinfo in hashes.items():
        hash_rows.append(
            {
                "Table": table_name,
                "Run 1 Hash": hinfo.get("run1", "")[:16] + "...",
                "Run 2 Hash": hinfo.get("run2", "")[:16] + "...",
                "Match": "YES" if hinfo.get("match") else "NO",
            }
        )
    df_hash = pd.DataFrame(hash_rows)
    st.dataframe(df_hash, use_container_width=True, hide_index=True)

    st.markdown("**Determinism Root Cause**")
    drc = phase1.get("determinism_root_cause", {})
    if drc:
        st.markdown(f"- Agent runs mismatch: {drc.get('agent_runs_mismatch_root_cause', 'N/A')}")
        st.markdown(
            f"- Product events mismatch: {drc.get('product_events_mismatch_root_cause', 'N/A')}"
        )
        st.markdown(f"- Cross-module RNG coupling: {drc.get('cross_module_rng_coupling', 'N/A')}")
        st.markdown(f"- Fix (hash): {drc.get('fix_hash', 'N/A')}")
        st.markdown(f"- Fix (set ordering): {drc.get('fix_set_ordering', 'N/A')}")
        st.markdown(f"- Fix (RNG isolation): {drc.get('fix_rng_isolation', 'N/A')}")
else:
    st.info("No canonical hash data available.")

# ── Row Count Comparison ─────────────────────────────────────────────────
st.subheader("Per-Table Row Counts: Raw vs Staging vs Mart")

raw_counts = q(
    """
    SELECT
        'stg_users'                         AS table_name,
        (SELECT COUNT(*) FROM main_staging.stg_users) AS staging_count
    UNION ALL
    SELECT
        'stg_documents',
        (SELECT COUNT(*) FROM main_staging.stg_documents)
    UNION ALL
    SELECT
        'stg_sessions',
        (SELECT COUNT(*) FROM main_staging.stg_sessions)
    UNION ALL
    SELECT
        'stg_product_events',
        (SELECT COUNT(*) FROM main_staging.stg_product_events)
    UNION ALL
    SELECT
        'stg_agent_runs',
        (SELECT COUNT(*) FROM main_staging.stg_agent_runs)
    UNION ALL
    SELECT
        'stg_agent_spans',
        (SELECT COUNT(*) FROM main_staging.stg_agent_spans)
    UNION ALL
    SELECT
        'stg_experiment_assignments',
        (SELECT COUNT(*) FROM main_staging.stg_experiment_assignments)
"""
)

# Get row counts from phase1 for raw tables
p1_row_counts = phase1.get("performance", {}).get("table_row_counts", {})
raw_to_staging_map = {
    "users": "stg_users",
    "documents": "stg_documents",
    "sessions": "stg_sessions",
    "product_events": "stg_product_events",
    "agent_runs": "stg_agent_runs",
    "agent_spans": "stg_agent_spans",
    "experiment_assignments": "stg_experiment_assignments",
}

# Mart counts
mart_counts_raw = q(
    """
    SELECT
        'mart_daily_product_kpis' AS table_name,
        COUNT(*)                  AS row_count
    FROM main_marts.mart_daily_product_kpis
    UNION ALL
    SELECT 'mart_conversion_funnel', COUNT(*) FROM main_marts.mart_conversion_funnel
    UNION ALL
    SELECT 'mart_retention_cohort', COUNT(*) FROM main_marts.mart_retention_cohort
    UNION ALL
    SELECT 'mart_agent_daily_kpis', COUNT(*) FROM main_marts.mart_agent_daily_kpis
    UNION ALL
    SELECT 'mart_ab_test_summary', COUNT(*) FROM main_marts.mart_ab_test_summary
    UNION ALL
    SELECT 'mart_executive_daily_scorecard', COUNT(*) FROM main_marts.mart_executive_daily_scorecard
"""
)

if not raw_counts.empty:
    # Build comparison table
    comp_rows = []
    for raw_key, stg_name in raw_to_staging_map.items():
        raw_val = p1_row_counts.get(raw_key, 0)
        stg_row = raw_counts[raw_counts["table_name"] == stg_name]
        stg_val = int(stg_row.iloc[0]["staging_count"]) if not stg_row.empty else 0
        comp_rows.append(
            {
                "Table": raw_key,
                "Raw Count": f"{raw_val:,}",
                "Staging Count": f"{stg_val:,}",
                "Mart Count": "—",
            }
        )

    # Add mart rows
    if not mart_counts_raw.empty:
        for _, row in mart_counts_raw.iterrows():
            comp_rows.append(
                {
                    "Table": row["table_name"],
                    "Raw Count": "—",
                    "Staging Count": "—",
                    "Mart Count": f"{int(row['row_count']):,}",
                }
            )

    df_counts = pd.DataFrame(comp_rows)
    st.dataframe(df_counts, use_container_width=True, hide_index=True)

    # Row count bar chart
    fig = go.Figure()
    raw_tables = [r["Table"] for r in comp_rows if r["Raw Count"] != "—"]
    raw_vals = [int(r["Raw Count"].replace(",", "")) for r in comp_rows if r["Raw Count"] != "—"]
    stg_tables = [r["Table"] for r in comp_rows if r["Staging Count"] != "—"]
    stg_vals = [
        int(r["Staging Count"].replace(",", "")) for r in comp_rows if r["Staging Count"] != "—"
    ]

    if raw_tables:
        fig.add_trace(
            go.Bar(
                name="Raw",
                x=raw_tables,
                y=raw_vals,
                marker_color="#636EFA",
            )
        )
    if stg_tables:
        fig.add_trace(
            go.Bar(
                name="Staging",
                x=stg_tables,
                y=stg_vals,
                marker_color="#00CC96",
            )
        )

    if raw_tables or stg_tables:
        fig.update_layout(
            title="Row Counts: Raw vs Staging",
            yaxis_title="Rows",
            barmode="group",
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    # Mart row counts bar chart
    if not mart_counts_raw.empty:
        fig2 = px.bar(
            mart_counts_raw,
            x="table_name",
            y="row_count",
            title="Mart Row Counts",
            color="table_name",
            text_auto=True,
        )
        fig2.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Unable to query staging row counts from the database.")

# ── P07 / P08 Anomaly Explanation ────────────────────────────────────────
st.subheader("Injected Anomalies: P07 and P08")

p07 = next((p for p in p1_phenomena if p.get("phenomenon_id") == "P07"), None)
p08 = next((p for p in p1_phenomena if p.get("phenomenon_id") == "P08"), None)

col_p7, col_p8 = st.columns(2)

with col_p7:
    st.markdown("**P07 — Duplicate Upload Spike**")
    if p07:
        st.markdown(
            f"""
        - **Affected date:** {p07.get('affected_date', 'N/A')}
        - **Duplicate rate on affected day:** {p07.get('affected_value', 0):.2%}
        - **Overall duplicate rate (baseline):** {p07.get('baseline_value', 0):.2%}
        - **Duplicates detected:** {p07.get('duplicate_rows_on_affected_date', 0)} of {p07.get('total_rows_on_affected_date', 0)} rows
        """
        )
    st.info(
        "**P07 and P08 are intentionally injected synthetic anomalies** designed to test the observability pipeline's ability to detect data quality issues."
    )

with col_p8:
    st.markdown("**P08 — Cross-Group Experiment Contamination**")
    if p08:
        st.markdown(
            f"""
        - **Contaminated users:** {p08.get('affected_n', 0)}
        - **Clean users:** {p08.get('baseline_n', 0)}
        - **Users appearing in both A and B groups**
        """
        )
    st.info(
        "These anomalies are expected to be detected and flagged. They demonstrate the pipeline's monitoring and alerting capabilities on synthetic data."
    )

# ── Footer ───────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(
    "⚠️ **ALL DATA IS SYNTHETIC.** P07 and P08 are intentionally injected synthetic anomalies."
)
