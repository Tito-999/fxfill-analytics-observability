-- Business question: How does adoption of key product features (OCR, anonymization, risk detection, autofill) trend over time? Which features are gaining or losing adoption share compared to the total task volume?
-- Grain: one row per event_date per feature
-- Input models: main_intermediate.int_task_funnel_flags, main_intermediate.int_user_daily_activity
-- Metric definition: Feature adoption rate = tasks reaching that feature stage on a given date / total tasks uploaded on that date. RANK is used to identify the top-N most-used features per day.
-- Assumptions: Each task goes through the funnel on the same date as its upload. Feature adoption is calculated at the task level (not user level). The adoption rates can exceed 100% on a single-day view if features complete on a different day than upload.
-- Expected use: Product roadmap prioritisation; feature sunset or investment decisions; weekly product review decks.

WITH daily_tasks AS (
    SELECT
        uploaded_at::DATE AS event_date,
        COUNT(*)                                            AS total_tasks,
        SUM(CASE WHEN did_complete_ocr THEN 1 ELSE 0 END)   AS ocr_tasks,
        SUM(CASE WHEN did_complete_anonymization THEN 1 ELSE 0 END) AS anonymization_tasks,
        SUM(CASE WHEN did_complete_risk_detection THEN 1 ELSE 0 END) AS risk_detection_tasks,
        SUM(CASE WHEN did_complete_autofill THEN 1 ELSE 0 END) AS autofill_tasks,
        SUM(CASE WHEN did_export THEN 1 ELSE 0 END)         AS export_tasks
    FROM main_intermediate.int_task_funnel_flags
    WHERE uploaded_at IS NOT NULL
    GROUP BY uploaded_at::DATE
),

daily_with_rank AS (
    SELECT
        event_date,
        total_tasks,
        'ocr'               AS feature, ocr_tasks            AS feature_tasks,
        ROUND(ocr_tasks * 100.0 / NULLIF(total_tasks, 0), 2) AS adoption_pct,
        RANK() OVER (PARTITION BY event_date ORDER BY ocr_tasks DESC) AS feature_rank
    FROM daily_tasks
    UNION ALL
    SELECT
        event_date,
        total_tasks,
        'anonymization'     AS feature, anonymization_tasks  AS feature_tasks,
        ROUND(anonymization_tasks * 100.0 / NULLIF(total_tasks, 0), 2) AS adoption_pct,
        RANK() OVER (PARTITION BY event_date ORDER BY anonymization_tasks DESC)
    FROM daily_tasks
    UNION ALL
    SELECT
        event_date,
        total_tasks,
        'risk_detection'    AS feature, risk_detection_tasks  AS feature_tasks,
        ROUND(risk_detection_tasks * 100.0 / NULLIF(total_tasks, 0), 2) AS adoption_pct,
        RANK() OVER (PARTITION BY event_date ORDER BY risk_detection_tasks DESC)
    FROM daily_tasks
    UNION ALL
    SELECT
        event_date,
        total_tasks,
        'autofill'          AS feature, autofill_tasks        AS feature_tasks,
        ROUND(autofill_tasks * 100.0 / NULLIF(total_tasks, 0), 2) AS adoption_pct,
        RANK() OVER (PARTITION BY event_date ORDER BY autofill_tasks DESC)
    FROM daily_tasks
    UNION ALL
    SELECT
        event_date,
        total_tasks,
        'export'            AS feature, export_tasks          AS feature_tasks,
        ROUND(export_tasks * 100.0 / NULLIF(total_tasks, 0), 2) AS adoption_pct,
        RANK() OVER (PARTITION BY event_date ORDER BY export_tasks DESC)
    FROM daily_tasks
)

SELECT
    event_date,
    feature,
    feature_tasks,
    total_tasks,
    adoption_pct,
    feature_rank,
    feature_tasks - LAG(feature_tasks) OVER (PARTITION BY feature ORDER BY event_date) AS daily_change_tasks
FROM daily_with_rank
ORDER BY event_date, feature_rank;
