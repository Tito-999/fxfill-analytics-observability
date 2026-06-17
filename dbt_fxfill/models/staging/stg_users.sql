-- Staging: users dimension table
-- Standardizes types, adds is_synthetic flag, preserves raw values
SELECT
    user_id,
    CAST(signup_time AS TIMESTAMP) AS signup_time,
    CAST(signup_time AS DATE) AS signup_date,
    acquisition_channel,
    country,
    device_type,
    user_segment,
    company_size,
    experience_level,
    CAST(is_returning_user AS BOOLEAN) AS is_returning_user,
    _source_run_id,
    _source_config_hash,
    _loaded_at_utc
FROM {{ source('raw', 'raw_users') }}
