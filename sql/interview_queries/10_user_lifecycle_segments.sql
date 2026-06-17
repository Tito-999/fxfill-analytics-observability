-- Business question: How many users fall into each lifecycle stage (new, active, retained, resurrected, churned, dormant) on a given day? Understanding the distribution of user states helps the product team evaluate the impact of engagement initiatives and spot churn trends early.
-- Grain: one row per user per activity_date
-- Input models: main_intermediate.int_user_daily_activity, main_intermediate.int_user_first_activity, main_staging.stg_users
-- Metric definition: Lifecycle classification using window functions:
--   new = user's first_activity_date == current activity_date
--   active = user active on this date, was also active on prior date
--   retained = user active on this date, was active 7 days ago (using LAG with 7-day offset)
--   resurrected = user active on this date after >= 30 days of inactivity
--   churned = user was active in prior period but not active in current window
--   dormant = user not seen for >= 30 days
-- Assumptions: A user is "active" on days where int_user_daily_activity shows tasks_touched > 0. The classification uses LAG/LEAD window functions ordered by activity_date per user.
-- Expected use: User engagement dashboard; lifecycle email campaign targeting; churn prediction model input.

WITH user_activity_lag AS (
    SELECT
        uda.user_id,
        uda.activity_date,
        uda.tasks_touched,
        uda.had_export,
        LAG(uda.activity_date) OVER (
            PARTITION BY uda.user_id ORDER BY uda.activity_date
        ) AS prev_activity_date,
        LAG(uda.activity_date, 7) OVER (
            PARTITION BY uda.user_id ORDER BY uda.activity_date
        ) AS activity_7d_ago,
        u.signup_date,
        uifa.first_activity_date,
        uifa.first_export_date
    FROM main_intermediate.int_user_daily_activity uda
    LEFT JOIN main_staging.stg_users u ON uda.user_id = u.user_id
    LEFT JOIN main_intermediate.int_user_first_activity uifa ON uda.user_id = uifa.user_id
),

classified AS (
    SELECT
        *,
        CASE
            WHEN activity_date = first_activity_date THEN 'new'
            WHEN LAG(activity_date) OVER (PARTITION BY user_id ORDER BY activity_date) = activity_date - INTERVAL '1 day'
                THEN 'active'
            WHEN activity_7d_ago IS NOT NULL
                AND activity_7d_ago = activity_date - INTERVAL '7 days'
                THEN 'retained'
            WHEN prev_activity_date IS NOT NULL
                AND (activity_date - prev_activity_date) >= 30
                THEN 'resurrected'
            WHEN prev_activity_date IS NULL
                AND activity_date > first_activity_date
                THEN 'resurrected'
            ELSE 'active'
        END AS lifecycle_stage
    FROM user_activity_lag
)

SELECT
    activity_date,
    lifecycle_stage,
    COUNT(DISTINCT user_id)                                                 AS user_count,
    ROUND(AVG(tasks_touched), 2)                                            AS avg_tasks_touched,
    SUM(had_export)                                                         AS users_with_export,
    ROUND(AVG(had_export) * 100, 2)                                         AS export_pct
FROM classified
WHERE lifecycle_stage IS NOT NULL
GROUP BY activity_date, lifecycle_stage
ORDER BY activity_date, lifecycle_stage;
