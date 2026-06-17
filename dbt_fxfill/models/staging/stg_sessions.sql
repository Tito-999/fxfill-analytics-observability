-- Staging: sessions dimension table
SELECT
    session_id,
    user_id,
    CAST(started_at AS TIMESTAMP) AS started_at,
    CAST(ended_at AS TIMESTAMP) AS ended_at,
    device_type,
    platform,
    acquisition_channel,
    CAST(is_bounced AS BOOLEAN) AS is_bounced,
    CAST(page_views AS INTEGER) AS page_views,
    _source_run_id,
    _source_config_hash,
    _loaded_at_utc
FROM {{ source('raw', 'raw_sessions') }}
