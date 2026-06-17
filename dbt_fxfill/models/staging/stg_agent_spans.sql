-- Staging: agent spans fact table
SELECT
    span_id,
    trace_id,
    parent_span_id,
    span_name,
    span_type,
    CAST(start_time AS TIMESTAMP) AS start_time,
    CAST(end_time AS TIMESTAMP) AS end_time,
    CAST(latency_ms AS BIGINT) AS latency_ms,
    status,
    model_name,
    CAST(input_tokens AS BIGINT) AS input_tokens,
    CAST(output_tokens AS BIGINT) AS output_tokens,
    CAST(estimated_cost_usd AS DOUBLE) AS estimated_cost_usd,
    tool_name,
    error_type,
    metadata_json,
    _source_run_id,
    _source_config_hash,
    _loaded_at_utc
FROM {{ source('raw', 'raw_agent_spans') }}
