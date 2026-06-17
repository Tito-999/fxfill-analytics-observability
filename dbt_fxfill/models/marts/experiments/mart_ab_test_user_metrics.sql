-- User-level A/B test metrics (for statistical analysis in Phase 4)
SELECT
    ca.user_id,
    ca.experiment_group,
    ca.experiment_id,
    COUNT(DISTINCT t.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.is_successful THEN t.task_id END) AS successful_tasks,
    COUNT(DISTINCT CASE WHEN t.is_successful THEN t.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT t.task_id), 0) AS task_success_rate,
    AVG(t.field_edit_count) AS avg_field_edits,
    AVG(t.task_duration_seconds) AS avg_task_duration_s,
    AVG(ar.field_accuracy) AS avg_field_accuracy,
    AVG(ar.total_latency_ms) AS avg_agent_latency_ms,
    SUM(ar.estimated_cost_usd) AS total_cost_usd
FROM {{ ref('int_experiment_clean_assignments') }} ca
LEFT JOIN {{ ref('int_task_outcomes') }} t ON ca.user_id = t.user_id
LEFT JOIN {{ ref('stg_agent_runs') }} ar ON t.task_id = ar.task_id
WHERE NOT ca.is_contaminated
GROUP BY ca.user_id, ca.experiment_group, ca.experiment_id
