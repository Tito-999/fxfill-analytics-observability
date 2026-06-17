-- Mart: Daily product KPIs
WITH task_stats AS (
    SELECT
        task_id,
        MAX(CASE WHEN did_export THEN 1 ELSE 0 END) AS was_exported,
        MAX(CASE WHEN did_abandon THEN 1 ELSE 0 END) AS was_abandoned,
        MAX(CASE WHEN did_fail THEN 1 ELSE 0 END) AS did_fail,
        MAX(field_edit_count) AS field_edit_count
    FROM {{ ref('int_task_funnel_flags') }}
    GROUP BY task_id
)
SELECT
    e.event_date,
    COUNT(DISTINCT e.user_id) AS dau,
    COUNT(DISTINCT CASE WHEN e.event_name = 'document_uploaded' THEN e.user_id END) AS wau_uploaders,
    COUNT(DISTINCT e.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN t.was_exported = 1 THEN e.task_id END) AS exported_tasks,
    COUNT(DISTINCT CASE WHEN t.was_exported = 1 THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS export_rate,
    COUNT(DISTINCT CASE WHEN t.was_abandoned = 1 THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS abandonment_rate,
    COUNT(DISTINCT CASE WHEN t.did_fail = 1 THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS failure_rate,
    AVG(t.field_edit_count) AS avg_manual_edits
FROM {{ ref('stg_product_events') }} e
LEFT JOIN task_stats t ON e.task_id = t.task_id
GROUP BY e.event_date
