-- A/B test effects by user segment
SELECT
    u.user_segment,
    u.acquisition_channel,
    ca.experiment_group,
    COUNT(DISTINCT ca.user_id) AS user_count,
    AVG(um.export_rate) AS avg_task_success_rate,
    AVG(um.avg_field_accuracy) AS avg_field_accuracy,
    AVG(um.avg_latency_ms) AS avg_agent_latency_ms,
    SUM(um.total_cost_usd) / NULLIF(COUNT(DISTINCT ca.user_id), 0) AS avg_cost_per_user
FROM {{ ref('int_experiment_clean_assignments') }} ca
JOIN {{ ref('stg_users') }} u ON ca.user_id = u.user_id
LEFT JOIN {{ ref('int_experiment_user_metrics') }} um ON ca.user_id = um.user_id
    AND ca.experiment_group = um.experiment_group
WHERE NOT ca.is_contaminated
GROUP BY u.user_segment, u.acquisition_channel, ca.experiment_group
