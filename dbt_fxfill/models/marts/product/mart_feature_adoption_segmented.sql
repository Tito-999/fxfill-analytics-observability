-- Mart: Feature adoption rates segmented by user segment, device, complexity
-- Grain: one row per (event_date, feature_name, user_segment, device_type, complexity)
WITH feature_events AS (
    SELECT
        CAST(f.uploaded_at AS DATE) AS event_date,
        f.user_id,
        f.document_id,
        u.user_segment,
        u.device_type,
        COALESCE(d.complexity_level, 'unknown') AS complexity
    FROM {{ ref('int_task_funnel_flags') }} f
    LEFT JOIN {{ ref('stg_users') }} u ON f.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON f.document_id = d.document_id
    WHERE f.uploaded_at IS NOT NULL
),
unpivoted AS (
    SELECT event_date, user_id, user_segment, device_type, complexity,
           'OCR' AS feature_name, CAST(f.did_complete_ocr AS INTEGER) AS adopted
    FROM {{ ref('int_task_funnel_flags') }} f
    LEFT JOIN {{ ref('stg_users') }} u ON f.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON f.document_id = d.document_id
    WHERE f.uploaded_at IS NOT NULL

    UNION ALL

    SELECT event_date, user_id, user_segment, device_type, complexity,
           'Anonymization' AS feature_name, CAST(f.did_complete_anonymization AS INTEGER) AS adopted
    FROM {{ ref('int_task_funnel_flags') }} f
    LEFT JOIN {{ ref('stg_users') }} u ON f.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON f.document_id = d.document_id
    WHERE f.uploaded_at IS NOT NULL

    UNION ALL

    SELECT event_date, user_id, user_segment, device_type, complexity,
           'Risk Detection' AS feature_name, CAST(f.did_complete_risk_detection AS INTEGER) AS adopted
    FROM {{ ref('int_task_funnel_flags') }} f
    LEFT JOIN {{ ref('stg_users') }} u ON f.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON f.document_id = d.document_id
    WHERE f.uploaded_at IS NOT NULL

    UNION ALL

    SELECT event_date, user_id, user_segment, device_type, complexity,
           'Autofill' AS feature_name, CAST(f.did_complete_autofill AS INTEGER) AS adopted
    FROM {{ ref('int_task_funnel_flags') }} f
    LEFT JOIN {{ ref('stg_users') }} u ON f.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON f.document_id = d.document_id
    WHERE f.uploaded_at IS NOT NULL
)
SELECT
    event_date,
    feature_name,
    user_segment,
    device_type,
    complexity,
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT CASE WHEN adopted = 1 THEN user_id END) AS adopted_users,
    COUNT(DISTINCT CASE WHEN adopted = 1 THEN user_id END) * 1.0 /
        NULLIF(COUNT(DISTINCT user_id), 0) AS adoption_rate
FROM unpivoted
GROUP BY event_date, feature_name, user_segment, device_type, complexity
