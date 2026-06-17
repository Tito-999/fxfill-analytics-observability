-- Agent stage-level performance metrics with date grain
-- Grain: (run_date, stage, span_type)
SELECT
    r.run_date,
    s.span_name AS stage,
    s.span_type,
    COUNT(*) AS span_count,
    AVG(s.latency_ms) AS avg_latency_ms,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY s.latency_ms) AS p50_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY s.latency_ms) AS p95_latency_ms,
    SUM(CASE WHEN s.status = 'error' THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0) AS error_rate,
    AVG(CASE WHEN s.span_type = 'llm' THEN s.input_tokens END) AS avg_input_tokens,
    AVG(CASE WHEN s.span_type = 'llm' THEN s.output_tokens END) AS avg_output_tokens,
    AVG(CASE WHEN s.span_type = 'llm' THEN s.estimated_cost_usd END) AS avg_cost_usd
FROM {{ ref('stg_agent_spans') }} s
JOIN {{ ref('stg_agent_runs') }} r ON s.trace_id = r.trace_id
GROUP BY r.run_date, s.span_name, s.span_type
ORDER BY r.run_date, MIN(s.start_time)
