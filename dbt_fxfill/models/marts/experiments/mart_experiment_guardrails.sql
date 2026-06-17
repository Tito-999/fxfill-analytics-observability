-- Experiment guardrail metrics
SELECT
    ca.experiment_group,
    COUNT(DISTINCT ca.user_id) AS user_count,
    AVG(r.total_latency_ms) AS avg_p95_latency_ms,
    AVG(r.estimated_cost_usd) AS avg_cost_per_run,
    COUNT(DISTINCT CASE WHEN NOT f.did_export AND f.did_upload THEN f.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT f.task_id), 0) AS abandonment_rate,
    AVG(CASE WHEN r.error_type IS NOT NULL THEN 1 ELSE 0 END) AS agent_error_rate
FROM {{ ref('int_experiment_clean_assignments') }} ca
LEFT JOIN {{ ref('stg_agent_runs') }} r ON ca.user_id = r.user_id
LEFT JOIN {{ ref('int_task_funnel_flags') }} f ON ca.user_id = f.user_id
WHERE NOT ca.is_contaminated
GROUP BY ca.experiment_group
