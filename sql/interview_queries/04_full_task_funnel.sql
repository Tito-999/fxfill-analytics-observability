-- Business question: What proportion of tasks progress through each stage of the document processing pipeline (Upload -> OCR -> Anonymization -> Risk Detection -> Autofill -> Review -> Export), and where do the biggest drop-offs occur? This identifies the weakest conversion points.
-- Grain: one row per funnel step (7 rows total)
-- Input models: main_intermediate.int_task_funnel_flags
-- Metric definition: Each step counts tasks where the boolean flag is TRUE. step_conversion = (tasks at step N) / (tasks at step N-1). overall_conversion = (tasks at step N) / (total tasks at step 1 / upload).
-- Assumptions: The funnel is strictly linear: a task progressing to step N must have completed all prior steps. This is guaranteed by the upstream model's boolean flags.
-- Expected use: Product team prioritisation of funnel improvement efforts; weekly conversion monitoring.

WITH funnel AS (
    SELECT
        COUNT(*)                                                         AS total_uploaded,
        SUM(CASE WHEN did_complete_ocr THEN 1 ELSE 0 END)                AS completed_ocr,
        SUM(CASE WHEN did_complete_anonymization THEN 1 ELSE 0 END)      AS completed_anonymization,
        SUM(CASE WHEN did_complete_risk_detection THEN 1 ELSE 0 END)     AS completed_risk_detection,
        SUM(CASE WHEN did_complete_autofill THEN 1 ELSE 0 END)           AS completed_autofill,
        SUM(CASE WHEN did_start_review THEN 1 ELSE 0 END)                AS started_review,
        SUM(CASE WHEN did_export THEN 1 ELSE 0 END)                      AS exported
    FROM main_intermediate.int_task_funnel_flags
),

unpivoted AS (
    SELECT '1_upload'              AS step, total_uploaded              AS tasks FROM funnel
    UNION ALL
    SELECT '2_ocr'                 AS step, completed_ocr               AS tasks FROM funnel
    UNION ALL
    SELECT '3_anonymization'       AS step, completed_anonymization     AS tasks FROM funnel
    UNION ALL
    SELECT '4_risk_detection'      AS step, completed_risk_detection    AS tasks FROM funnel
    UNION ALL
    SELECT '5_autofill'            AS step, completed_autofill          AS tasks FROM funnel
    UNION ALL
    SELECT '6_review'              AS step, started_review              AS tasks FROM funnel
    UNION ALL
    SELECT '7_export'              AS step, exported                    AS tasks FROM funnel
)

SELECT
    step,
    tasks,
    tasks - LAG(tasks) OVER (ORDER BY step) AS dropoff_from_prior,
    ROUND(tasks * 100.0 / NULLIF(LAG(tasks) OVER (ORDER BY step), 0), 2) AS step_conversion_pct,
    ROUND(tasks * 100.0 / NULLIF(FIRST_VALUE(tasks) OVER (ORDER BY step), 0), 2) AS overall_conversion_pct,
    ROUND(1.0 - tasks * 1.0 / NULLIF(LAG(tasks) OVER (ORDER BY step), 0), 4) AS step_dropoff_rate
FROM unpivoted
ORDER BY step;
