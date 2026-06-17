-- User segment performance summary
SELECT
    u.user_segment,
    u.acquisition_channel,
    u.device_type,
    COUNT(DISTINCT u.user_id) AS user_count,
    COUNT(DISTINCT t.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.is_successful THEN t.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT t.task_id), 0) AS task_success_rate,
    AVG(t.field_edit_count) AS avg_edits,
    AVG(t.task_duration_seconds) AS avg_duration_s
FROM {{ ref('stg_users') }} u
LEFT JOIN {{ ref('int_task_outcomes') }} t ON u.user_id = t.user_id
GROUP BY u.user_segment, u.acquisition_channel, u.device_type
