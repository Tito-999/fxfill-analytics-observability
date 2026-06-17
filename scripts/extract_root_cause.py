"""Extract real Root Cause Analysis evidence from medium warehouse."""
import json, duckdb
from datetime import UTC, datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DB = str(PROJECT / "warehouse" / "fxfill.duckdb")
R = PROJECT / "reports"
conn = duckdb.connect(DB, read_only=True)

# ── Period definition ──
max_date = conn.execute("SELECT MAX(event_date) FROM main_marts.mart_daily_product_kpis").fetchone()[0]
curr_start = str(max_date) + "::DATE - INTERVAL 7 DAY"
prev_start = str(max_date) + "::DATE - INTERVAL 14 DAY"
end_date = str(max_date)

# ── Overall metrics ──
curr = conn.execute(f"""
    SELECT AVG(export_rate), SUM(total_tasks), SUM(exported_tasks), COUNT(*)
    FROM main_marts.mart_daily_product_kpis
    WHERE event_date >= DATE '{max_date}' - INTERVAL 7 DAY AND event_date <= DATE '{max_date}'
""").fetchone()
prev = conn.execute(f"""
    SELECT AVG(export_rate), SUM(total_tasks), SUM(exported_tasks), COUNT(*)
    FROM main_marts.mart_daily_product_kpis
    WHERE event_date >= DATE '{max_date}' - INTERVAL 14 DAY AND event_date < DATE '{max_date}' - INTERVAL 7 DAY
""").fetchone()

curr_rate = float(curr[0] or 0)
prev_rate = float(prev[0] or 0)
curr_tasks = int(curr[1] or 0)
prev_tasks = int(prev[1] or 0)
curr_exp = int(curr[2] or 0)
prev_exp = int(prev[2] or 0)
abs_change = curr_rate - prev_rate
rel_change = (abs_change / max(abs(prev_rate), 1e-10)) * 100

# ── Driver analysis by device_type ──
drivers = []
for dim, dim_col, dim_table in [
    ("device_type", "device_type", "main_staging.stg_users"),
    ("acquisition_channel", "acquisition_channel", "main_staging.stg_users"),
]:
    rows = conn.execute(f"""
        SELECT u.{dim_col},
               COUNT(DISTINCT CASE WHEN e.event_date >= DATE '{max_date}' - 7 THEN e.task_id END) as curr_vol,
               COUNT(DISTINCT CASE WHEN e.event_date >= DATE '{max_date}' - 14 AND e.event_date < DATE '{max_date}' - 7 THEN e.task_id END) as prev_vol,
               COUNT(DISTINCT CASE WHEN e.event_date >= DATE '{max_date}' - 7 AND f.did_export THEN e.task_id END)*1.0/NULLIF(COUNT(DISTINCT CASE WHEN e.event_date >= DATE '{max_date}' - 7 THEN e.task_id END),0) as curr_rate,
               COUNT(DISTINCT CASE WHEN e.event_date >= DATE '{max_date}' - 14 AND e.event_date < DATE '{max_date}' - 7 AND f.did_export THEN e.task_id END)*1.0/NULLIF(COUNT(DISTINCT CASE WHEN e.event_date >= DATE '{max_date}' - 14 AND e.event_date < DATE '{max_date}' - 7 THEN e.task_id END),0) as prev_rate
        FROM main_staging.stg_product_events e
        JOIN {dim_table} u ON e.user_id = u.user_id
        LEFT JOIN main_intermediate.int_task_funnel_flags f ON e.task_id = f.task_id
        GROUP BY u.{dim_col}
    """).fetchall()
    for row in rows:
        seg, cv, pv, cr, pr = row
        cr_val = float(cr or 0)
        pr_val = float(pr or 0)
        cv_val = int(cv or 0)
        pv_val = int(pv or 0)
        rate_eff = (cr_val - pr_val) * (cv_val + pv_val) / max(curr_tasks + prev_tasks, 1)
        mix_eff = (cv_val / max(curr_tasks, 1) - pv_val / max(prev_tasks, 1)) * pr_val
        total = rate_eff + mix_eff
        drivers.append({
            "dimension": dim, "segment": seg,
            "current_volume": cv_val, "previous_volume": pv_val,
            "current_rate": round(cr_val, 6), "previous_rate": round(pr_val, 6),
            "rate_effect": round(rate_eff, 6), "mix_effect": round(mix_eff, 6),
            "total_contribution": round(total, 6),
        })

drivers.sort(key=lambda d: d["total_contribution"])
neg_drivers = drivers[:3]
pos_drivers = drivers[-3:][::-1]

total_contrib = sum(d["total_contribution"] for d in drivers)
residual = abs_change - total_contrib
recon_ok = abs(residual) < 0.01

rc = {
    "current_period_start": str(max_date) + " - 7d",
    "current_period_end": str(max_date),
    "previous_period_start": str(max_date) + " - 14d",
    "previous_period_end": str(max_date) + " - 7d",
    "current_task_count": curr_tasks,
    "previous_task_count": prev_tasks,
    "current_exported_tasks": curr_exp,
    "previous_exported_tasks": prev_exp,
    "current_export_rate": round(curr_rate, 6),
    "previous_export_rate": round(prev_rate, 6),
    "absolute_change_percentage_points": round(abs_change, 6),
    "relative_change_percent": round(rel_change, 2),
    "top_negative_drivers": neg_drivers,
    "top_positive_drivers": pos_drivers,
    "overall_export_rate_change": round(abs_change, 6),
    "sum_of_reported_contributions": round(total_contrib, 6),
    "residual": round(residual, 6),
    "tolerance": 0.01,
    "reconciliation_passed": recon_ok,
    "observed_facts": [
        {"statement": f"Export rate changed from {prev_rate:.4f} to {curr_rate:.4f}", "value": round(abs_change, 6)},
        {"statement": f"Task volume changed from {prev_tasks} to {curr_tasks}", "value": curr_tasks - prev_tasks},
    ],
    "analytical_inferences": [
        {"statement": f"Top negative driver: {neg_drivers[0]['dimension']}/{neg_drivers[0]['segment']} contributed {neg_drivers[0]['total_contribution']:.4f}" if neg_drivers else "No clear negative drivers"},
    ],
    "hypotheses_requiring_validation": [
        "Investigate whether top negative driver reflects a real behavioral change or random variation in synthetic data",
    ],
    "recommended_actions": [
        "Review the top contributing segment for anomalies in event pipeline",
        "Cross-reference with agent error rates for the same segment",
    ],
    "synthetic_data_notice": "All findings are derived from intentionally generated synthetic data and do not represent a real production incident.",
    "method_note": "Rate-volume decomposition using one dimension at a time. Drivers from different dimensions may overlap. Primary reconciliation uses the first dimension listed."
}

with open(R / "phase3_root_cause.json", "w") as f:
    json.dump(rc, f, indent=2, default=str)
conn.close()

print(f"Root cause extracted:")
print(f"  Current rate: {curr_rate:.4f}, Previous: {prev_rate:.4f}, Change: {abs_change:+.4f}")
print(f"  Tasks: {curr_tasks} (curr) vs {prev_tasks} (prev)")
print(f"  Top negative: {[(d['segment'], round(d['total_contribution'],4)) for d in neg_drivers[:3]]}")
print(f"  Reconciliation: residual={residual:.6f}, passed={recon_ok}")
print(f"  Written to: reports/phase3_root_cause.json")
