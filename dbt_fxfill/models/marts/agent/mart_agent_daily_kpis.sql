-- Mart: Agent daily KPIs
SELECT
    CAST(r.started_at AS DATE) AS run_date,
    COUNT(*) AS total_runs,
    SUM(CASE WHEN r.success_flag THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS agent_success_rate,
    SUM(CASE WHEN tr.failed_span_count > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS tool_error_rate,
    AVG(r.retry_count) AS avg_retry_count,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY r.total_latency_ms) AS p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY r.total_latency_ms) AS p95_latency_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY r.total_latency_ms) AS p99_latency_ms,
    AVG(r.total_input_tokens) AS avg_input_tokens,
    AVG(r.total_output_tokens) AS avg_output_tokens,
    AVG(r.estimated_cost_usd) AS avg_cost_per_run,
    SUM(r.estimated_cost_usd) / NULLIF(SUM(CASE WHEN r.success_flag THEN 1 ELSE 0 END), 0) AS cost_per_successful_task,
    AVG(r.field_accuracy) AS avg_field_accuracy,
    AVG(r.manual_edit_count) AS avg_manual_edit_count
FROM {{ ref('stg_agent_runs') }} r
LEFT JOIN {{ ref('int_agent_trace_rollup') }} tr ON r.trace_id = tr.trace_id
GROUP BY CAST(r.started_at AS DATE)
