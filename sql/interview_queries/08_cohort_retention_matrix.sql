-- Business question: For each weekly signup cohort, what fraction of users are active in each subsequent week? The retention matrix (cohort vs. week number) reveals whether newer cohorts engage better or worse than older ones over time.
-- Grain: one row per cohort_week per week_number (n x n sparse matrix)
-- Input models: main_intermediate.int_user_cohorts, main_intermediate.int_user_daily_activity
-- Metric definition: eligible_users = users in the cohort. retained_users = users from the cohort with activity in the given week_number offset. retention_rate = retained_users / eligible_users. Uses a self-join-like approach via date arithmetic rather than LAG/LEAD.
-- Assumptions: The cohort_week aligns to the Monday of the signup week. week_number = 0 is the cohort's own signup week. Only weeks 0-12 are shown to keep the matrix readable; this can be extended to 52 for annual analysis.
-- Expected use: Cohort analysis dashboard; evaluating whether product changes improve long-term retention; identifying seasonal patterns in engagement.

WITH cohort_base AS (
    SELECT
        user_id,
        cohort_week,
        acquisition_channel
    FROM main_intermediate.int_user_cohorts
),

user_weekly_activity AS (
    SELECT
        user_id,
        DATE_TRUNC('week', activity_date) AS activity_week
    FROM main_intermediate.int_user_daily_activity
    GROUP BY user_id, DATE_TRUNC('week', activity_date)
),

cohort_size AS (
    SELECT
        cohort_week,
        COUNT(DISTINCT user_id) AS eligible_users
    FROM cohort_base
    GROUP BY cohort_week
),

retention_map AS (
    SELECT
        cb.cohort_week,
        uwa.activity_week,
        COUNT(DISTINCT cb.user_id) AS retained_users
    FROM cohort_base cb
    INNER JOIN user_weekly_activity uwa
        ON cb.user_id = uwa.user_id
    WHERE uwa.activity_week >= cb.cohort_week
    GROUP BY cb.cohort_week, uwa.activity_week
)

SELECT
    rm.cohort_week,
    cs.eligible_users,
    rm.activity_week,
    (rm.activity_week - rm.cohort_week) / 7 AS week_number,
    rm.retained_users,
    ROUND(rm.retained_users * 100.0 / NULLIF(cs.eligible_users, 0), 2) AS retention_rate_pct
FROM retention_map rm
INNER JOIN cohort_size cs ON rm.cohort_week = cs.cohort_week
WHERE (rm.activity_week - rm.cohort_week) / 7 BETWEEN 0 AND 12
ORDER BY rm.cohort_week, week_number;
