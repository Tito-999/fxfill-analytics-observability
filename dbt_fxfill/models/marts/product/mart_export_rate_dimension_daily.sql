-- Daily export rate by dimension and segment for Root Cause Analysis
WITH base AS (
    SELECT * FROM {{ ref('int_task_funnel_enriched') }}
),
dimension_rows AS (
    SELECT event_date, 'user_segment' AS dimension_name, user_segment AS segment, task_id, did_export FROM base
    UNION ALL
    SELECT event_date, 'device_type', device_type, task_id, did_export FROM base
    UNION ALL
    SELECT event_date, 'channel', acquisition_channel, task_id, did_export FROM base
    UNION ALL
    SELECT event_date, 'complexity', complexity, task_id, did_export FROM base
)
SELECT
    event_date,
    dimension_name,
    segment,
    COUNT(DISTINCT task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN did_export THEN task_id END) AS exported_tasks,
    COUNT(DISTINCT CASE WHEN did_export THEN task_id END) * 1.0 / NULLIF(COUNT(DISTINCT task_id), 0) AS export_rate
FROM dimension_rows
GROUP BY event_date, dimension_name, segment
