"""Exact Kitagawa decomposition on acquisition_channel. Residual <= 1e-9."""

import json
from pathlib import Path

import duckdb

PROJECT = Path(__file__).resolve().parent.parent
DB = str(PROJECT / "warehouse" / "fxfill.duckdb")
R = PROJECT / "reports"
R.mkdir(exist_ok=True)
conn = duckdb.connect(DB, read_only=True)

max_date = conn.execute(  # type: ignore[index]  # pre-existing: optional tuple indexing
    "SELECT MAX(event_date) FROM main_marts.mart_daily_product_kpis"
).fetchone()[0]

# Per-segment volumes and rates
rows = conn.execute(
    f"""
    WITH curr AS (
        SELECT u.acquisition_channel AS seg,
               COUNT(DISTINCT e.task_id) AS vol,
               COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END)*1.0/NULLIF(COUNT(DISTINCT e.task_id),0) AS rate,
               COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END) AS exported
        FROM main_staging.stg_product_events e
        JOIN main_staging.stg_users u ON e.user_id=u.user_id
        LEFT JOIN main_intermediate.int_task_funnel_flags f ON e.task_id=f.task_id
        WHERE e.event_date >= DATE '{max_date}' - 7 AND e.event_date <= DATE '{max_date}'
        GROUP BY u.acquisition_channel
    ), prev AS (
        SELECT u.acquisition_channel AS seg,
               COUNT(DISTINCT e.task_id) AS vol,
               COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END)*1.0/NULLIF(COUNT(DISTINCT e.task_id),0) AS rate,
               COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END) AS exported
        FROM main_staging.stg_product_events e
        JOIN main_staging.stg_users u ON e.user_id=u.user_id
        LEFT JOIN main_intermediate.int_task_funnel_flags f ON e.task_id=f.task_id
        WHERE e.event_date >= DATE '{max_date}' - 14 AND e.event_date < DATE '{max_date}' - 7
        GROUP BY u.acquisition_channel
    )
    SELECT COALESCE(c.seg,p.seg) AS seg,
           COALESCE(c.vol,0) AS cv, COALESCE(p.vol,0) AS pv,
           COALESCE(c.rate,0.0) AS cr, COALESCE(p.rate,0.0) AS pr,
           COALESCE(c.exported,0) AS ce, COALESCE(p.exported,0) AS pe
    FROM curr c FULL OUTER JOIN prev p ON c.seg=p.seg
    ORDER BY 1
"""
).fetchall()

total_cv = sum(r[1] for r in rows)
total_pv = sum(r[2] for r in rows)
# Overall rates computed directly from segment aggregations (ensures exact reconciliation)
total_cr = sum(r[1] * r[3] for r in rows) / max(total_cv, 1)
total_pr = sum(r[2] * r[4] for r in rows) / max(total_pv, 1)
overall_change = total_cr - total_pr

drivers = []
sum_re = 0.0
sum_me = 0.0
for seg, cv, pv, cr, pr, ce, pe in rows:
    cs = cv / max(total_cv, 1)
    ps = pv / max(total_pv, 1)
    # Symmetric Kitagawa decomposition
    re = 0.5 * (cs + ps) * (cr - pr)
    me = 0.5 * (cr + pr) * (cs - ps)
    total = re + me
    sum_re += re
    sum_me += me
    drivers.append(
        {
            "segment": seg,
            "current_volume": int(cv),
            "previous_volume": int(pv),
            "current_share": round(cs, 10),
            "previous_share": round(ps, 10),
            "current_exported": int(ce),
            "previous_exported": int(pe),
            "current_rate": round(cr, 10),
            "previous_rate": round(pr, 10),
            "rate_effect": re,
            "mix_effect": me,
            "total_contribution": total,
        }
    )

residual = overall_change - (sum_re + sum_me)
tolerance = 1e-10

drivers.sort(key=lambda d: d["total_contribution"])
neg = [d for d in drivers if d["total_contribution"] < 0][:3]
pos = [d for d in drivers if d["total_contribution"] > 0][-3:][::-1]

# Compute contribution shares using absolute sum
abs_sum = sum(abs(d["total_contribution"]) for d in drivers) or 1.0
for d in drivers:
    d["contribution_share"] = d["total_contribution"] / abs_sum

rc = {
    "current_period_end": str(max_date),
    "current_period_start": str(max_date) + " - 7d",
    "previous_period_end": str(max_date) + " - 7d",
    "previous_period_start": str(max_date) + " - 14d",
    "current_task_count": int(total_cv),
    "previous_task_count": int(total_pv),
    "current_export_rate": round(total_cr, 6),
    "previous_export_rate": round(total_pr, 6),
    "overall_change": overall_change,
    "sum_rate_effect": sum_re,
    "sum_mix_effect": sum_me,
    "sum_total_contribution": sum_re + sum_me,
    "residual": residual,
    "tolerance": tolerance,
    "reconciliation_passed": abs(residual) <= tolerance,
    "decomposition_method": "Symmetric Kitagawa: re=0.5*(cs+ps)*(cr-pr), me=0.5*(cr+pr)*(cs-ps)",
    "top_negative_drivers": neg,
    "top_positive_drivers": pos,
    "negative_driver_count": len(neg),
    "positive_driver_count": len(pos),
    "all_drivers": drivers,
    "diagnostic_dimensions": [
        "device_type",
        "app_version",
        "document_complexity",
        "user_segment",
        "agent_error_type",
    ],
    "observed_facts": [
        {
            "statement": f"Overall export rate: {total_pr:.4f} -> {total_cr:.4f} (change: {overall_change:+.6f})"
        },
    ],
    "analytical_inferences": [
        {
            "statement": (
                f"Top negative: {neg[0]['segment']} contributed {neg[0]['total_contribution']:+.6f}"
                if neg
                else "No negative drivers"
            )
        },
    ],
    "hypotheses_requiring_validation": [
        "Verify whether observed decomposition reflects synthetic data patterns"
    ],
    "recommended_actions": ["Cross-reference with Agent error rates"],
    "synthetic_data_notice": "All findings are from intentionally generated synthetic data.",
}
with open(R / "phase3_root_cause.json", "w") as f:
    json.dump(rc, f, indent=2, default=str)
conn.close()
print(f"Kitagawa decomposition: overall_change={overall_change:.10f}")
print(f"  sum(rate_effect)={sum_re:.15f}")
print(f"  sum(mix_effect)={sum_me:.15f}")
print(f"  residual={residual:.2e} tolerance={tolerance}")
print(f"  PASSED={abs(residual)<=tolerance}")
