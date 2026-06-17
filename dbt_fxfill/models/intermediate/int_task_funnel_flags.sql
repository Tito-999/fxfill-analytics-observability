-- Intermediate: Boolean funnel flags per task
SELECT
    task_id,
    user_id,
    document_id,
    uploaded_at IS NOT NULL AS did_upload,
    ocr_completed_at IS NOT NULL AS did_complete_ocr,
    anonymization_completed_at IS NOT NULL AS did_complete_anonymization,
    risk_detection_completed_at IS NOT NULL AS did_complete_risk_detection,
    autofill_completed_at IS NOT NULL AS did_complete_autofill,
    review_started_at IS NOT NULL AS did_start_review,
    was_exported = 1 AS did_export,
    was_abandoned = 1 AS did_abandon,
    had_failure = 1 AS did_fail,
    field_edit_count,
    event_count,
    uploaded_at,
    exported_at
FROM {{ ref('int_task_event_sequence') }}
