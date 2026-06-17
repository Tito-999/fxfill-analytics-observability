-- Business question: How does the task conversion funnel and export rate vary by the user's acquisition channel (organic, paid, referral, etc.)? This helps marketing teams understand which channels bring users who not only sign up but also successfully complete tasks.
-- Grain: one row per acquisition_channel per funnel step
-- Input models: main_intermediate.int_task_funnel_flags, main_staging.stg_users
-- Metric definition: For each acquisition_channel, count of tasks at each funnel step, step-to-step conversion rates, and overall export rate. Aggregate-level metrics (avg field edits, event count) are included for richness.
-- Assumptions: acquisition_channel is taken from stg_users (source-of-truth for acquisition). Users without a channel are grouped under 'unknown'.
-- Expected use: Marketing ROI analysis; paid channel optimisation; content strategy for under-performing organic segments.

WITH user_channel AS (
    SELECT
        user_id,
        COALESCE(acquisition_channel, 'unknown') AS acquisition_channel
    FROM main_staging.stg_users
),

channel_funnel AS (
    SELECT
        uc.acquisition_channel,
        COUNT(DISTINCT tff.task_id)                                                  AS total_tasks,
        COUNT(DISTINCT CASE WHEN tff.did_complete_ocr THEN tff.task_id END)           AS completed_ocr,
        COUNT(DISTINCT CASE WHEN tff.did_complete_anonymization THEN tff.task_id END) AS completed_anonymization,
        COUNT(DISTINCT CASE WHEN tff.did_complete_risk_detection THEN tff.task_id END) AS completed_risk_detection,
        COUNT(DISTINCT CASE WHEN tff.did_complete_autofill THEN tff.task_id END)       AS completed_autofill,
        COUNT(DISTINCT CASE WHEN tff.did_start_review THEN tff.task_id END)            AS started_review,
        COUNT(DISTINCT CASE WHEN tff.did_export THEN tff.task_id END)                  AS exported,
        ROUND(AVG(tff.field_edit_count), 2)                                            AS avg_field_edits,
        ROUND(AVG(tff.event_count), 1)                                                 AS avg_events_per_task
    FROM main_intermediate.int_task_funnel_flags tff
    LEFT JOIN user_channel uc ON tff.user_id = uc.user_id
    GROUP BY uc.acquisition_channel
)

SELECT
    acquisition_channel,
    total_tasks,
    completed_ocr,
    ROUND(completed_ocr * 100.0 / NULLIF(total_tasks, 0), 2)               AS ocr_conversion_pct,
    completed_anonymization,
    ROUND(completed_anonymization * 100.0 / NULLIF(completed_ocr, 0), 2)   AS anonymization_conversion_pct,
    completed_risk_detection,
    ROUND(completed_risk_detection * 100.0 / NULLIF(completed_anonymization, 0), 2) AS risk_detection_conversion_pct,
    completed_autofill,
    ROUND(completed_autofill * 100.0 / NULLIF(completed_risk_detection, 0), 2)       AS autofill_conversion_pct,
    started_review,
    ROUND(started_review * 100.0 / NULLIF(completed_autofill, 0), 2)       AS review_conversion_pct,
    exported,
    ROUND(exported * 100.0 / NULLIF(total_tasks, 0), 2)                    AS overall_export_rate_pct,
    avg_field_edits,
    avg_events_per_task
FROM channel_funnel
ORDER BY overall_export_rate_pct DESC;
