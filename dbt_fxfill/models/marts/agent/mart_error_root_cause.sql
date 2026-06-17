-- Error root cause analysis by category and stage with date grain
-- Grain: (run_date, error_category, run_error_type, failing_span_name)
SELECT
    r.run_date,
    ec.error_category,
    ec.run_error_type,
    ec.failing_span_name,
    COUNT(*) AS error_count,
    COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY r.run_date) AS error_share,
    AVG(CASE WHEN NOT r.success_flag THEN r.total_latency_ms END) AS avg_failed_latency_ms,
    COUNT(DISTINCT ec.task_id) AS affected_tasks
FROM {{ ref('int_agent_error_classification') }} ec
JOIN {{ ref('stg_agent_runs') }} r ON ec.agent_run_id = r.agent_run_id
WHERE ec.error_category != 'none'
GROUP BY r.run_date, ec.error_category, ec.run_error_type, ec.failing_span_name
ORDER BY r.run_date, error_count DESC
