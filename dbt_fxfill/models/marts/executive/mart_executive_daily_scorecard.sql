-- Mart: Executive daily scorecard (north star + guardrails)
SELECT
    p.event_date,
    p.dau,
    p.exported_tasks AS north_star_metric,
    p.export_rate,
    p.abandonment_rate,
    p.avg_manual_edits,
    COALESCE(r.d7_retention_rate, 0) AS d7_retention,
    COALESCE(a.agent_success_rate, 0) AS agent_success_rate,
    COALESCE(a.p95_latency_ms, 0) AS agent_p95_latency_ms,
    COALESCE(a.cost_per_successful_task, 0) AS cost_per_successful_task,
    'warnings' AS data_quality_status
FROM {{ ref('mart_daily_product_kpis') }} p
LEFT JOIN {{ ref('mart_retention_cohort') }} r ON p.event_date = r.cohort_date
LEFT JOIN {{ ref('mart_agent_daily_kpis') }} a ON p.event_date = a.run_date
