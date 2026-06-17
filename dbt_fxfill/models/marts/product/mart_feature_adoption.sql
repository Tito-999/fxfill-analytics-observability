-- Feature adoption rates by feature and date
SELECT
    e.event_date,
    COUNT(DISTINCT e.task_id) AS total_tasks,
    COUNT(DISTINCT CASE WHEN f.did_complete_ocr THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS ocr_adoption,
    COUNT(DISTINCT CASE WHEN f.did_complete_anonymization THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS anonymization_adoption,
    COUNT(DISTINCT CASE WHEN f.did_complete_risk_detection THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS risk_detection_adoption,
    COUNT(DISTINCT CASE WHEN f.did_complete_autofill THEN e.task_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT e.task_id), 0) AS autofill_adoption
FROM {{ ref('stg_product_events') }} e
LEFT JOIN {{ ref('int_task_funnel_flags') }} f ON e.task_id = f.task_id
WHERE e.event_name = 'document_uploaded'
GROUP BY e.event_date
