-- Classify agent errors by stage and type
SELECT
    r.agent_run_id,
    r.trace_id,
    r.task_id,
    r.error_type AS run_error_type,
    r.success_flag,
    CASE
        WHEN r.error_type = 'ocr_error' THEN 'ocr'
        WHEN r.error_type = 'timeout' THEN 'timeout'
        WHEN r.error_type = 'api_error' THEN 'api'
        WHEN r.error_type = 'parse_error' THEN 'parse'
        WHEN NOT r.success_flag THEN 'unknown'
        ELSE 'none'
    END AS error_category,
    MAX(CASE WHEN s.status = 'error' THEN s.span_name END) AS failing_span_name,
    MAX(CASE WHEN s.status = 'error' THEN s.error_type END) AS span_error_type,
    COUNT(CASE WHEN s.status = 'error' THEN 1 END) AS error_span_count
FROM {{ ref('stg_agent_runs') }} r
LEFT JOIN {{ ref('stg_agent_spans') }} s ON r.trace_id = s.trace_id
GROUP BY ALL
