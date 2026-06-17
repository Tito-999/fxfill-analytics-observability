-- Task-level outcomes with timing and status classification
SELECT
    task_id,
    user_id,
    document_id,
    uploaded_at,
    exported_at,
    abandoned_at,
    failed_at,
    CASE
        WHEN exported_at IS NOT NULL THEN 'exported'
        WHEN abandoned_at IS NOT NULL THEN 'abandoned'
        WHEN failed_at IS NOT NULL THEN 'failed'
        ELSE 'in_progress'
    END AS final_outcome,
    COALESCE(exported_at, abandoned_at, failed_at, last_event_at) AS completed_at,
    was_exported = 1 AS is_successful,
    event_count,
    field_edit_count,
    DATEDIFF('second', uploaded_at, COALESCE(exported_at, abandoned_at, failed_at)) AS task_duration_seconds
FROM {{ ref('int_task_event_sequence') }}
