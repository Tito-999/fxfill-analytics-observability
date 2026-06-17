-- Channel performance: acquisition channels ranked by conversion
WITH channel_stats AS (
    SELECT
        u.acquisition_channel,
        COUNT(DISTINCT u.user_id) AS cohort_users,
        COUNT(DISTINCT CASE WHEN f.did_export THEN f.user_id END) AS converted_users,
        COUNT(DISTINCT f.task_id) AS total_tasks,
        COUNT(DISTINCT CASE WHEN f.did_export THEN f.task_id END) AS exported_tasks
    FROM {{ ref('stg_users') }} u
    LEFT JOIN {{ ref('int_task_funnel_flags') }} f ON u.user_id = f.user_id
    GROUP BY u.acquisition_channel
)
SELECT
    acquisition_channel,
    cohort_users,
    converted_users,
    converted_users * 1.0 / NULLIF(cohort_users, 0) AS user_conversion_rate,
    total_tasks,
    exported_tasks,
    exported_tasks * 1.0 / NULLIF(total_tasks, 0) AS task_export_rate,
    RANK() OVER (ORDER BY converted_users * 1.0 / NULLIF(cohort_users, 0) DESC) AS conversion_rank
FROM channel_stats
ORDER BY conversion_rank
