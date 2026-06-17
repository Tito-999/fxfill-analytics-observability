-- Weekly business review aggregation
SELECT
    DATE_TRUNC('week', e.event_date) AS week_start,
    COUNT(DISTINCT e.user_id) AS wau,
    COUNT(DISTINCT e.task_id) AS weekly_tasks,
    COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END) AS weekly_exports,
    COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS export_rate,
    AVG(f.field_edit_count) AS avg_edits,
    COUNT(DISTINCT CASE WHEN f.did_fail THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS failure_rate
FROM {{ ref('stg_product_events') }} e
LEFT JOIN {{ ref('int_task_funnel_flags') }} f ON e.task_id = f.task_id
GROUP BY DATE_TRUNC('week', e.event_date)
ORDER BY week_start
