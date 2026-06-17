-- Business question: For each user, what was the first task that they successfully exported, and how long did it take them from signup to that first success? This measures time-to-value for new users.
-- Grain: one row per user (only users who have at least one successful task)
-- Input models: main_intermediate.int_task_outcomes, main_staging.stg_users
-- Metric definition: For each user, find the task with the earliest exported_at. time_to_success = exported_at - signup_time (in hours). ROW_NUMBER is used to pick exactly one task per user (earliest export wins; ties broken by task_id).
-- Assumptions: "Successful task" is defined as int_task_outcomes.is_successful = TRUE with a non-null exported_at. Only users who signed up (have a record in stg_users) are considered. Fractional hours are preserved for granular analysis.
-- Expected use: Onboarding funnel optimisation; setting time-to-value SLAs; identifying users who may need onboarding assistance if they haven't exported within a threshold.

WITH user_signup AS (
    SELECT
        user_id,
        signup_time
    FROM main_staging.stg_users
),

successful_tasks AS (
    SELECT
        task_id,
        user_id,
        exported_at,
        field_edit_count,
        event_count,
        task_duration_seconds
    FROM main_intermediate.int_task_outcomes
    WHERE is_successful = TRUE
      AND exported_at IS NOT NULL
),

ranked_first_task AS (
    SELECT
        st.user_id,
        st.task_id,
        st.exported_at,
        st.field_edit_count,
        st.event_count,
        st.task_duration_seconds,
        us.signup_time,
        ROW_NUMBER() OVER (
            PARTITION BY st.user_id ORDER BY st.exported_at ASC, st.task_id ASC
        ) AS rn
    FROM successful_tasks st
    INNER JOIN user_signup us ON st.user_id = us.user_id
)

SELECT
    user_id,
    task_id,
    signup_time,
    exported_at,
    EXTRACT(EPOCH FROM (exported_at - signup_time)) / 3600.0 AS time_to_success_hours,
    (exported_at::DATE - signup_time::DATE) AS time_to_success_days,
    field_edit_count,
    event_count,
    task_duration_seconds,
    CASE
        WHEN (exported_at - signup_time) <= INTERVAL '1 hour'  THEN 'under_1h'
        WHEN (exported_at - signup_time) <= INTERVAL '24 hours' THEN '1-24h'
        WHEN (exported_at - signup_time) <= INTERVAL '7 days'  THEN '1-7d'
        WHEN (exported_at - signup_time) <= INTERVAL '30 days' THEN '7-30d'
        ELSE 'over_30d'
    END AS time_bucket
FROM ranked_first_task
WHERE rn = 1
ORDER BY time_to_success_hours;
