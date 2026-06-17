-- Intermediate: Agent trace rollup (one row per trace)
SELECT
    r.trace_id,
    r.agent_run_id,
    r.user_id,
    r.document_id,
    r.started_at AS trace_start,
    r.ended_at AS trace_end,
    r.total_latency_ms AS trace_latency_ms,
    COUNT(s.span_id) AS span_count,
    COUNT(CASE WHEN s.span_type = 'tool' THEN 1 END) AS tool_span_count,
    COUNT(CASE WHEN s.span_type = 'llm' THEN 1 END) AS llm_span_count,
    COUNT(CASE WHEN s.status = 'error' THEN 1 END) AS failed_span_count,
    SUM(CASE WHEN s.span_name = 'ocr_extraction' THEN s.latency_ms ELSE 0 END) AS ocr_latency_ms,
    SUM(CASE WHEN s.span_type = 'llm' THEN s.latency_ms ELSE 0 END) AS llm_latency_ms,
    SUM(CASE WHEN s.span_name = 'output_validation' THEN s.latency_ms ELSE 0 END) AS validation_latency_ms,
    r.total_input_tokens,
    r.total_output_tokens,
    r.estimated_cost_usd,
    r.success_flag,
    r.error_type,
    r.model_name,
    r.prompt_version
FROM {{ ref('stg_agent_runs') }} r
LEFT JOIN {{ ref('stg_agent_spans') }} s ON r.trace_id = s.trace_id
GROUP BY ALL
