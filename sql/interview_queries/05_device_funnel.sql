-- Business question: How does the task conversion funnel differ between device types (desktop vs mobile vs tablet)? Device-specific drop-offs can indicate UI/UX issues that only affect certain platforms.
-- Grain: one row per device_type per funnel step
-- Input models: main_intermediate.int_task_funnel_flags, main_staging.stg_users
-- Metric definition: For each device_type, count of tasks at each funnel step, then step-to-step conversion. Conditional aggregation (CASE WHEN) splits the funnel flags by user device_type.
-- Assumptions: device_type is taken from stg_users (signup-time device). Users may switch devices; this query uses the registered device as a proxy. A LEFT JOIN ensures tasks from users without a known device_type are grouped under 'unknown'.
-- Expected use: Mobile product team prioritisation; cross-platform experience audits.

WITH user_device AS (
    SELECT
        user_id,
        COALESCE(device_type, 'unknown') AS device_type
    FROM main_staging.stg_users
),

funnel_flags_with_device AS (
    SELECT
        tff.task_id,
        ud.device_type,
        tff.did_complete_ocr,
        tff.did_complete_anonymization,
        tff.did_complete_risk_detection,
        tff.did_complete_autofill,
        tff.did_start_review,
        tff.did_export
    FROM main_intermediate.int_task_funnel_flags tff
    LEFT JOIN user_device ud ON tff.user_id = ud.user_id
),

device_funnel AS (
    SELECT
        device_type,
        COUNT(*)                                                         AS total_uploaded,
        SUM(CASE WHEN did_complete_ocr THEN 1 ELSE 0 END)                AS completed_ocr,
        SUM(CASE WHEN did_complete_anonymization THEN 1 ELSE 0 END)      AS completed_anonymization,
        SUM(CASE WHEN did_complete_risk_detection THEN 1 ELSE 0 END)     AS completed_risk_detection,
        SUM(CASE WHEN did_complete_autofill THEN 1 ELSE 0 END)           AS completed_autofill,
        SUM(CASE WHEN did_start_review THEN 1 ELSE 0 END)                AS started_review,
        SUM(CASE WHEN did_export THEN 1 ELSE 0 END)                      AS exported
    FROM funnel_flags_with_device
    GROUP BY device_type
)

SELECT
    device_type,
    '1_upload'              AS step, total_uploaded         AS tasks,
    ROUND(total_uploaded * 100.0 / NULLIF(total_uploaded, 0), 2) AS step_conversion_pct
FROM device_funnel
UNION ALL
SELECT
    device_type,
    '2_ocr'                 AS step, completed_ocr          AS tasks,
    ROUND(completed_ocr * 100.0 / NULLIF(total_uploaded, 0), 2)
FROM device_funnel
UNION ALL
SELECT
    device_type,
    '3_anonymization'       AS step, completed_anonymization AS tasks,
    ROUND(completed_anonymization * 100.0 / NULLIF(completed_ocr, 0), 2)
FROM device_funnel
UNION ALL
SELECT
    device_type,
    '4_risk_detection'      AS step, completed_risk_detection AS tasks,
    ROUND(completed_risk_detection * 100.0 / NULLIF(completed_anonymization, 0), 2)
FROM device_funnel
UNION ALL
SELECT
    device_type,
    '5_autofill'            AS step, completed_autofill     AS tasks,
    ROUND(completed_autofill * 100.0 / NULLIF(completed_risk_detection, 0), 2)
FROM device_funnel
UNION ALL
SELECT
    device_type,
    '6_review'              AS step, started_review          AS tasks,
    ROUND(started_review * 100.0 / NULLIF(completed_autofill, 0), 2)
FROM device_funnel
UNION ALL
SELECT
    device_type,
    '7_export'              AS step, exported                AS tasks,
    ROUND(exported * 100.0 / NULLIF(started_review, 0), 2)
FROM device_funnel
ORDER BY device_type, step;
