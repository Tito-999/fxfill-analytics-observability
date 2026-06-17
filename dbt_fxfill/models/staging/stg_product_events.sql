-- Staging: product events fact table
SELECT
    event_id,
    CAST(event_time AS TIMESTAMP) AS event_time,
    CAST(event_date AS DATE) AS event_date,
    user_id,
    session_id,
    document_id,
    task_id,
    event_name,
    event_status,
    platform,
    app_version,
    experiment_id,
    experiment_group,
    CAST(latency_ms AS DOUBLE) AS latency_ms,
    error_type,
    metadata_json,
    _source_run_id,
    _source_config_hash,
    _loaded_at_utc
FROM {{ source('raw', 'raw_product_events') }}
