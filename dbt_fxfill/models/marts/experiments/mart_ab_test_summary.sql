-- Mart: A/B test summary by experiment group (clean assignments only)
SELECT
    experiment_group,
    COUNT(DISTINCT user_id) AS user_count,
    SUM(total_tasks) AS total_tasks,
    AVG(export_rate) AS avg_export_rate,
    AVG(avg_field_accuracy) AS avg_field_accuracy,
    AVG(avg_latency_ms) AS avg_latency_ms,
    SUM(total_cost_usd) AS total_cost_usd,
    SUM(total_cost_usd) / NULLIF(SUM(total_tasks), 0) AS cost_per_task
FROM {{ ref('int_experiment_user_metrics') }}
GROUP BY experiment_group
