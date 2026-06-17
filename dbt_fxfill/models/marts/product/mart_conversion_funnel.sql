-- Mart: Conversion funnel with step-level dropoff
WITH funnel AS (
    SELECT
        COUNT(DISTINCT task_id) AS uploaded,
        COUNT(DISTINCT CASE WHEN did_complete_ocr THEN task_id END) AS ocr_completed,
        COUNT(DISTINCT CASE WHEN did_complete_anonymization THEN task_id END) AS anonymization_completed,
        COUNT(DISTINCT CASE WHEN did_complete_risk_detection THEN task_id END) AS risk_detection_completed,
        COUNT(DISTINCT CASE WHEN did_complete_autofill THEN task_id END) AS autofill_completed,
        COUNT(DISTINCT CASE WHEN did_start_review THEN task_id END) AS review_started,
        COUNT(DISTINCT CASE WHEN did_export THEN task_id END) AS exported
    FROM {{ ref('int_task_funnel_flags') }}
)
SELECT
    'uploaded' AS step, uploaded AS tasks, 1.0 AS step_conversion, 1.0 AS overall_conversion, 0 AS dropoff
    FROM funnel
UNION ALL
SELECT 'ocr_completed', ocr_completed,
    ocr_completed * 1.0 / NULLIF(uploaded, 0),
    ocr_completed * 1.0 / NULLIF(uploaded, 0),
    uploaded - ocr_completed FROM funnel
UNION ALL
SELECT 'anonymization_completed', anonymization_completed,
    anonymization_completed * 1.0 / NULLIF(ocr_completed, 0),
    anonymization_completed * 1.0 / NULLIF(uploaded, 0),
    ocr_completed - anonymization_completed FROM funnel
UNION ALL
SELECT 'risk_detection_completed', risk_detection_completed,
    risk_detection_completed * 1.0 / NULLIF(anonymization_completed, 0),
    risk_detection_completed * 1.0 / NULLIF(uploaded, 0),
    anonymization_completed - risk_detection_completed FROM funnel
UNION ALL
SELECT 'autofill_completed', autofill_completed,
    autofill_completed * 1.0 / NULLIF(risk_detection_completed, 0),
    autofill_completed * 1.0 / NULLIF(uploaded, 0),
    risk_detection_completed - autofill_completed FROM funnel
UNION ALL
SELECT 'review_started', review_started,
    review_started * 1.0 / NULLIF(autofill_completed, 0),
    review_started * 1.0 / NULLIF(uploaded, 0),
    autofill_completed - review_started FROM funnel
UNION ALL
SELECT 'exported', exported,
    exported * 1.0 / NULLIF(review_started, 0),
    exported * 1.0 / NULLIF(uploaded, 0),
    review_started - exported FROM funnel
