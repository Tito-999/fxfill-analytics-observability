-- First activity event per user (used for activation analysis)
SELECT
    user_id,
    MIN(event_date) AS first_activity_date,
    MIN(event_time) AS first_activity_time,
    MIN(CASE WHEN event_name = 'document_uploaded' THEN event_date END) AS first_upload_date,
    MIN(CASE WHEN event_name = 'form_exported' THEN event_date END) AS first_export_date
FROM {{ ref('stg_product_events') }}
GROUP BY user_id
