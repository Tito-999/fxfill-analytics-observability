-- Intermediate: Task event sequence with funnel flags
-- Each task gets one row with timing and completion markers.
WITH task_timeline AS (
    SELECT
        task_id,
        user_id,
        document_id,
        MIN(CASE WHEN event_name = 'document_uploaded' THEN event_time END) AS uploaded_at,
        MIN(CASE WHEN event_name = 'ocr_started' THEN event_time END) AS ocr_started_at,
        MIN(CASE WHEN event_name = 'ocr_completed' THEN event_time END) AS ocr_completed_at,
        MIN(CASE WHEN event_name = 'anonymization_completed' THEN event_time END) AS anonymization_completed_at,
        MIN(CASE WHEN event_name = 'risk_detection_completed' THEN event_time END) AS risk_detection_completed_at,
        MIN(CASE WHEN event_name = 'autofill_completed' THEN event_time END) AS autofill_completed_at,
        MIN(CASE WHEN event_name = 'form_review_started' THEN event_time END) AS review_started_at,
        MIN(CASE WHEN event_name = 'form_exported' THEN event_time END) AS exported_at,
        MIN(CASE WHEN event_name = 'task_abandoned' THEN event_time END) AS abandoned_at,
        MIN(CASE WHEN event_name = 'agent_run_failed' THEN event_time END) AS failed_at,
        MAX(event_time) AS last_event_at,
        COUNT(*) AS event_count,
        COUNT(CASE WHEN event_name = 'field_edited' THEN 1 END) AS field_edit_count,
        MAX(CASE WHEN event_name = 'ocr_completed' THEN 1 ELSE 0 END) AS reached_ocr,
        MAX(CASE WHEN event_name = 'autofill_completed' THEN 1 ELSE 0 END) AS reached_autofill,
        MAX(CASE WHEN event_name = 'form_review_started' THEN 1 ELSE 0 END) AS reached_review,
        MAX(CASE WHEN event_name = 'form_exported' THEN 1 ELSE 0 END) AS was_exported,
        MAX(CASE WHEN event_name = 'task_abandoned' THEN 1 ELSE 0 END) AS was_abandoned,
        MAX(CASE WHEN event_name = 'agent_run_failed' THEN 1 ELSE 0 END) AS had_failure,
        CASE WHEN MAX(CASE WHEN event_name = 'agent_run_failed' THEN 1 ELSE 0 END) = 1 THEN
            (ARRAY_AGG(CASE WHEN event_name = 'agent_run_failed' THEN event_name END) FILTER (WHERE event_name = 'agent_run_failed'))[1]
        END AS failure_stage_guess
    FROM {{ ref('stg_product_events') }}
    GROUP BY task_id, user_id, document_id
)

SELECT * FROM task_timeline
