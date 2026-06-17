-- Enriched task funnel with user/document dimensions
SELECT
    f.task_id,
    f.user_id,
    f.document_id,
    CAST(f.uploaded_at AS DATE) AS event_date,
    COALESCE(u.acquisition_channel, 'unknown') AS acquisition_channel,
    COALESCE(u.device_type, 'unknown') AS device_type,
    COALESCE(u.user_segment, 'unknown') AS user_segment,
    COALESCE(d.complexity_level, 'unknown') AS complexity,
    CAST(f.did_upload AS BOOLEAN) AS did_upload,
    CAST(f.did_complete_ocr AS BOOLEAN) AS did_complete_ocr,
    CAST(f.did_complete_anonymization AS BOOLEAN) AS did_complete_anonymization,
    CAST(f.did_complete_risk_detection AS BOOLEAN) AS did_complete_risk_detection,
    CAST(f.did_complete_autofill AS BOOLEAN) AS did_complete_autofill,
    CAST(f.did_start_review AS BOOLEAN) AS did_start_review,
    CAST(f.did_export AS BOOLEAN) AS did_export
FROM {{ ref('int_task_funnel_flags') }} f
LEFT JOIN {{ ref('stg_users') }} u ON f.user_id = u.user_id
LEFT JOIN {{ ref('stg_documents') }} d ON f.document_id = d.document_id
WHERE f.uploaded_at IS NOT NULL
