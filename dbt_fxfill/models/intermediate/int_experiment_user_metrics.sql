-- Intermediate: User-level experiment metrics (clean assignments only)
SELECT
    ca.user_id,
    ca.experiment_group,
    ca.assigned_at,
    {{ var('experiment_start_date', '2026-05-01') }} AS experiment_start_date,
    {{ var('experiment_end_date', '2026-06-01') }} AS experiment_end_date,
    COUNT(DISTINCT t.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.did_export = 1 THEN t.task_id END) AS exported_tasks,
    COUNT(DISTINCT CASE WHEN t.did_export = 1 THEN t.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT t.task_id), 0) AS export_rate,
    AVG(ar.field_accuracy) AS avg_field_accuracy,
    AVG(ar.total_latency_ms) AS avg_latency_ms,
    SUM(ar.estimated_cost_usd) AS total_cost_usd
FROM {{ ref('int_experiment_clean_assignments') }} ca
LEFT JOIN {{ ref('int_task_funnel_flags') }} t ON ca.user_id = t.user_id
    AND t.uploaded_at >= CAST('{{ var('experiment_start_date', '2026-05-01') }}' AS DATE)
    AND t.uploaded_at <= CAST('{{ var('experiment_end_date', '2026-06-01') }}' AS DATE)
LEFT JOIN {{ ref('stg_agent_runs') }} ar ON t.task_id = ar.task_id
WHERE NOT ca.is_contaminated
GROUP BY ALL
