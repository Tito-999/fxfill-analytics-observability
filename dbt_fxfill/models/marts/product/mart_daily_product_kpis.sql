-- Mart: Daily product KPIs
-- Grain: one row per event_date
-- activity_date: date of any product event (for DAU)
-- task_cohort_date: date of document_uploaded (for task-level metrics)
WITH task_stats AS (
    SELECT
        task_id,
        MAX(CASE WHEN did_export THEN 1 ELSE 0 END) AS was_exported,
        MAX(CASE WHEN did_abandon THEN 1 ELSE 0 END) AS was_abandoned,
        MAX(CASE WHEN did_fail THEN 1 ELSE 0 END) AS did_fail,
        MAX(field_edit_count) AS field_edit_count,
        MAX(uploaded_at) AS uploaded_at
    FROM {{ ref('int_task_funnel_flags') }}
    GROUP BY task_id
),

activity_daily AS (
    SELECT
        event_date,
        COUNT(DISTINCT user_id) AS dau
    FROM {{ ref('stg_product_events') }}
    GROUP BY event_date
),

task_cohort_daily AS (
    SELECT
        CAST(uploaded_at AS DATE) AS event_date,
        COUNT(DISTINCT task_id) AS total_tasks,
        COUNT(DISTINCT CASE WHEN was_exported = 1 THEN task_id END) AS exported_tasks,
        COUNT(DISTINCT CASE WHEN was_abandoned = 1 THEN task_id END) AS abandoned_tasks,
        COUNT(DISTINCT CASE WHEN did_fail = 1 THEN task_id END) AS failed_tasks,
        AVG(field_edit_count) AS avg_manual_edits
    FROM task_stats
    WHERE uploaded_at IS NOT NULL
    GROUP BY CAST(uploaded_at AS DATE)
)

SELECT
    COALESCE(a.event_date, t.event_date) AS event_date,
    COALESCE(a.dau, 0) AS dau,
    COUNT(DISTINCT CASE WHEN e.event_name = 'document_uploaded' THEN e.user_id END) AS wau_uploaders,
    COALESCE(t.total_tasks, 0) AS total_tasks,
    COALESCE(t.exported_tasks, 0) AS exported_tasks,
    COALESCE(t.exported_tasks, 0) * 1.0 / NULLIF(COALESCE(t.total_tasks, 0), 0) AS export_rate,
    COALESCE(t.abandoned_tasks, 0) * 1.0 / NULLIF(COALESCE(t.total_tasks, 0), 0) AS abandonment_rate,
    COALESCE(t.failed_tasks, 0) * 1.0 / NULLIF(COALESCE(t.total_tasks, 0), 0) AS failure_rate,
    COALESCE(t.avg_manual_edits, 0) AS avg_manual_edits
FROM activity_daily a
FULL OUTER JOIN task_cohort_daily t ON a.event_date = t.event_date
LEFT JOIN (
    SELECT DISTINCT event_date, user_id, event_name
    FROM {{ ref('stg_product_events') }}
    WHERE event_name = 'document_uploaded'
) e ON COALESCE(a.event_date, t.event_date) = e.event_date
GROUP BY COALESCE(a.event_date, t.event_date), a.dau,
         t.total_tasks, t.exported_tasks, t.abandoned_tasks,
         t.failed_tasks, t.avg_manual_edits
