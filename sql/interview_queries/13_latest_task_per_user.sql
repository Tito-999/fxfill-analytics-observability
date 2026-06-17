-- Business question: What is the most recent task activity for each user? This supports the "last touchpoint" view needed for engagement scoring, re-engagement campaign targeting, and identifying users at risk of churning.
-- Grain: one row per user (only users with at least one task)
-- Input models: main_intermediate.int_task_outcomes
-- Metric definition: ROW_NUMBER() partitions by user_id and orders by the latest timestamp among (exported_at, abandoned_at, failed_at, uploaded_at) descending, picking the single most recent task per user.
-- Assumptions: A user's "latest" task is determined by the max of all relevant timestamps (uploaded_at, exported_at, abandoned_at, failed_at). Ties are broken by task_id descending so the query is deterministic.
-- Expected use: User engagement scoring models; CRM triggers for re-engagement; "my recent activity" widgets in dashboards.

WITH task_latest_timestamp AS (
    SELECT
        task_id,
        user_id,
        document_id,
        uploaded_at,
        exported_at,
        abandoned_at,
        failed_at,
        final_outcome,
        is_successful,
        event_count,
        field_edit_count,
        task_duration_seconds,
        GREATEST(
            COALESCE(uploaded_at, '1970-01-01'::TIMESTAMP),
            COALESCE(exported_at, '1970-01-01'::TIMESTAMP),
            COALESCE(abandoned_at, '1970-01-01'::TIMESTAMP),
            COALESCE(failed_at, '1970-01-01'::TIMESTAMP)
        ) AS latest_event_at
    FROM main_intermediate.int_task_outcomes
),

ranked_latest AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY user_id
            ORDER BY
                latest_event_at DESC,
                CASE
                    WHEN exported_at IS NOT NULL THEN 1
                    WHEN abandoned_at IS NOT NULL THEN 2
                    WHEN failed_at IS NOT NULL THEN 3
                    ELSE 4
                END ASC,
                task_id DESC
        ) AS rn
    FROM task_latest_timestamp
)

SELECT
    user_id,
    task_id,
    document_id,
    uploaded_at,
    exported_at,
    abandoned_at,
    failed_at,
    final_outcome,
    is_successful,
    event_count,
    field_edit_count,
    task_duration_seconds,
    latest_event_at,
    CASE
        WHEN exported_at = latest_event_at THEN 'exported'
        WHEN abandoned_at = latest_event_at THEN 'abandoned'
        WHEN failed_at = latest_event_at THEN 'failed'
        ELSE 'uploaded'
    END AS latest_status,
    CURRENT_DATE - latest_event_at::DATE AS days_since_latest_activity
FROM ranked_latest
WHERE rn = 1
ORDER BY latest_event_at DESC;
