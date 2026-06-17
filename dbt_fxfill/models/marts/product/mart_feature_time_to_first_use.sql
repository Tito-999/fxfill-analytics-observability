-- Mart: Time-to-first-use for each feature per user
-- Grain: one row per (first_use_date, feature_name, user_segment, device_type, complexity, days_to_first_use)
WITH feature_first AS (
    SELECT
        t.user_id,
        t.task_id,
        u.user_segment,
        u.device_type,
        COALESCE(d.complexity_level, 'unknown') AS complexity,
        CAST(u.signup_date AS DATE) AS signup_date,
        'OCR' AS feature_name,
        CAST(t.ocr_completed_at AS DATE) AS feature_completed_date
    FROM {{ ref('int_task_event_sequence') }} t
    LEFT JOIN {{ ref('stg_users') }} u ON t.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON t.document_id = d.document_id
    WHERE t.ocr_completed_at IS NOT NULL

    UNION ALL

    SELECT
        t.user_id, t.task_id, u.user_segment, u.device_type,
        COALESCE(d.complexity_level, 'unknown') AS complexity,
        CAST(u.signup_date AS DATE) AS signup_date,
        'Anonymization' AS feature_name,
        CAST(t.anonymization_completed_at AS DATE) AS feature_completed_date
    FROM {{ ref('int_task_event_sequence') }} t
    LEFT JOIN {{ ref('stg_users') }} u ON t.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON t.document_id = d.document_id
    WHERE t.anonymization_completed_at IS NOT NULL

    UNION ALL

    SELECT
        t.user_id, t.task_id, u.user_segment, u.device_type,
        COALESCE(d.complexity_level, 'unknown') AS complexity,
        CAST(u.signup_date AS DATE) AS signup_date,
        'Risk Detection' AS feature_name,
        CAST(t.risk_detection_completed_at AS DATE) AS feature_completed_date
    FROM {{ ref('int_task_event_sequence') }} t
    LEFT JOIN {{ ref('stg_users') }} u ON t.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON t.document_id = d.document_id
    WHERE t.risk_detection_completed_at IS NOT NULL

    UNION ALL

    SELECT
        t.user_id, t.task_id, u.user_segment, u.device_type,
        COALESCE(d.complexity_level, 'unknown') AS complexity,
        CAST(u.signup_date AS DATE) AS signup_date,
        'Autofill' AS feature_name,
        CAST(t.autofill_completed_at AS DATE) AS feature_completed_date
    FROM {{ ref('int_task_event_sequence') }} t
    LEFT JOIN {{ ref('stg_users') }} u ON t.user_id = u.user_id
    LEFT JOIN {{ ref('stg_documents') }} d ON t.document_id = d.document_id
    WHERE t.autofill_completed_at IS NOT NULL
),
ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY user_id, feature_name
            ORDER BY feature_completed_date, task_id
        ) AS rn
    FROM feature_first
)
SELECT
    feature_completed_date AS first_use_date,
    feature_name,
    user_segment,
    device_type,
    complexity,
    DATEDIFF('day', signup_date, feature_completed_date) AS days_to_first_use,
    COUNT(DISTINCT user_id) AS user_count
FROM ranked
WHERE rn = 1
  AND DATEDIFF('day', signup_date, feature_completed_date) >= 0
GROUP BY
    feature_completed_date,
    feature_name,
    user_segment,
    device_type,
    complexity,
    DATEDIFF('day', signup_date, feature_completed_date)
