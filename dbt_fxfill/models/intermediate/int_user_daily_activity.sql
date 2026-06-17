-- Daily user activity flag (who was active on each day)
SELECT DISTINCT
    user_id,
    event_date AS activity_date,
    COUNT(DISTINCT task_id) AS tasks_touched,
    COUNT(DISTINCT CASE WHEN event_name = 'document_uploaded' THEN task_id END) AS tasks_started,
    MAX(CASE WHEN event_name = 'form_exported' THEN 1 ELSE 0 END) AS had_export
FROM {{ ref('stg_product_events') }}
GROUP BY user_id, event_date
