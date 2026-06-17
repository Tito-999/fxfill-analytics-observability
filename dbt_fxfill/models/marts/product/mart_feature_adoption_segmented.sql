-- Mart: Feature adoption rates segmented by date, segment, device and complexity
-- Grain: one row per (event_date, feature_name, user_segment, device_type, complexity)

WITH base AS (
    SELECT
        CAST(f.uploaded_at AS DATE) AS event_date,
        f.user_id,
        COALESCE(u.user_segment, 'unknown') AS user_segment,
        COALESCE(u.device_type, 'unknown') AS device_type,
        COALESCE(d.complexity_level, 'unknown') AS complexity,
        f.did_complete_ocr,
        f.did_complete_anonymization,
        f.did_complete_risk_detection,
        f.did_complete_autofill
    FROM {{ ref('int_task_funnel_flags') }} AS f
    LEFT JOIN {{ ref('stg_users') }} AS u ON f.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} AS d ON f.document_id = d.document_id
    WHERE f.uploaded_at IS NOT NULL
),

unpivoted AS (
    SELECT event_date, user_id, user_segment, device_type, complexity,
           'OCR' AS feature_name, did_complete_ocr AS adopted
    FROM base
    UNION ALL
    SELECT event_date, user_id, user_segment, device_type, complexity,
           'Anonymization' AS feature_name, did_complete_anonymization AS adopted
    FROM base
    UNION ALL
    SELECT event_date, user_id, user_segment, device_type, complexity,
           'Risk Detection' AS feature_name, did_complete_risk_detection AS adopted
    FROM base
    UNION ALL
    SELECT event_date, user_id, user_segment, device_type, complexity,
           'Autofill' AS feature_name, did_complete_autofill AS adopted
    FROM base
)

SELECT
    event_date,
    feature_name,
    user_segment,
    device_type,
    complexity,
    COUNT(DISTINCT user_id) AS total_users,
    COUNT(DISTINCT CASE WHEN adopted THEN user_id END) AS adopted_users,
    COUNT(DISTINCT CASE WHEN adopted THEN user_id END) * 1.0
        / NULLIF(COUNT(DISTINCT user_id), 0) AS adoption_rate
FROM unpivoted
GROUP BY event_date, feature_name, user_segment, device_type, complexity
