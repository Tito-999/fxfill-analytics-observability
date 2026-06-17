-- Mart: Executive daily scorecard (north star + guardrails)
-- Grain: one row per event_date (unique daily grain)

WITH retention_daily AS (
    -- Pre-aggregate retention to daily grain to avoid channel-level duplication
    SELECT
        cohort_date AS event_date,
        SUM(d1_retained_users) * 1.0 / NULLIF(SUM(d1_eligible_users), 0) AS d1_retention_rate,
        SUM(d7_retained_users) * 1.0 / NULLIF(SUM(d7_eligible_users), 0) AS d7_retention_rate,
        SUM(d30_retained_users) * 1.0 / NULLIF(SUM(d30_eligible_users), 0) AS d30_retention_rate
    FROM {{ ref('mart_retention_cohort') }}
    WHERE d7_matured
    GROUP BY cohort_date
)

SELECT
    p.event_date,
    p.dau,
    p.exported_tasks AS north_star_metric,
    p.export_rate,
    p.abandonment_rate,
    p.avg_manual_edits,
    r.d7_retention_rate AS d7_retention,
    COALESCE(a.agent_success_rate, 0) AS agent_success_rate,
    COALESCE(a.p95_latency_ms, 0) AS agent_p95_latency_ms,
    COALESCE(a.cost_per_successful_task, 0) AS cost_per_successful_task,
    CASE
        WHEN r.d7_retention_rate IS NULL THEN 'D7 retention unavailable'
        WHEN a.agent_success_rate IS NULL THEN 'agent KPI missing'
        ELSE 'ok'
    END AS data_quality_status
FROM {{ ref('mart_daily_product_kpis') }} p
LEFT JOIN retention_daily r ON p.event_date = r.event_date
LEFT JOIN {{ ref('mart_agent_daily_kpis') }} a ON p.event_date = a.run_date
