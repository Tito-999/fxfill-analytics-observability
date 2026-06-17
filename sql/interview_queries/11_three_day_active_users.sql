-- Business question: Which users are active on three consecutive days, and what patterns exist in consecutive-day engagement? Consistent daily usage is a strong signal of product-market fit and user habit formation.
-- Grain: one row per user per 3-consecutive-day streak
-- Input models: main_intermediate.int_user_daily_activity
-- Metric definition: Using LAG and LEAD to check whether a user has activity on (day-1), day, and (day+1). A streak flag is set when all three consecutive days have tasks_touched > 0.
-- Assumptions: "Active" means tasks_touched > 0 on a given day. The query captures the middle day of each 3-day streak; overlapping windows are possible (a 5-day streak produces 3 middle-day rows). Weekends and holidays are not considered.
-- Expected use: Habit-formation analysis; identifying power users for loyalty programmes; evaluating the impact of feature releases on daily engagement.

WITH consecutive_check AS (
    SELECT
        user_id,
        activity_date,
        tasks_touched,
        had_export,
        LAG(tasks_touched, 1) OVER (
            PARTITION BY user_id ORDER BY activity_date
        ) AS prev_day_tasks,
        LEAD(tasks_touched, 1) OVER (
            PARTITION BY user_id ORDER BY activity_date
        ) AS next_day_tasks,
        LAG(activity_date, 1) OVER (
            PARTITION BY user_id ORDER BY activity_date
        ) AS prev_date,
        LEAD(activity_date, 1) OVER (
            PARTITION BY user_id ORDER BY activity_date
        ) AS next_date
    FROM main_intermediate.int_user_daily_activity
),

streak_identified AS (
    SELECT
        user_id,
        activity_date,
        tasks_touched,
        had_export,
        CASE
            WHEN tasks_touched > 0
                 AND COALESCE(prev_day_tasks, 0) > 0
                 AND COALESCE(next_day_tasks, 0) > 0
                 AND prev_date = activity_date - INTERVAL '1 day'
                 AND next_date = activity_date + INTERVAL '1 day'
            THEN 1
            ELSE 0
        END AS is_streak_midpoint,
        prev_day_tasks,
        next_day_tasks
    FROM consecutive_check
)

SELECT
    activity_date,
    COUNT(DISTINCT user_id)                                 AS active_users,
    COUNT(DISTINCT CASE WHEN is_streak_midpoint = 1 THEN user_id END) AS streak_users,
    ROUND(COUNT(DISTINCT CASE WHEN is_streak_midpoint = 1 THEN user_id END)
        * 100.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2)   AS streak_users_pct,
    ROUND(AVG(tasks_touched), 2)                            AS avg_tasks_touched,
    ROUND(AVG(CASE WHEN is_streak_midpoint = 1 THEN tasks_touched END), 2) AS avg_streak_tasks_touched,
    SUM(had_export) AS exporting_users
FROM streak_identified
GROUP BY activity_date
ORDER BY activity_date;
