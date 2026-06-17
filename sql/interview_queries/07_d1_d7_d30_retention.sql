-- Business question: Of users active on a given day, what fraction return on day +1, day +7, and day +30? D1/D7/D30 retention is a standard SaaS metric that measures product stickiness and long-term engagement.
-- Grain: one row per activity_date (cohort anchor date)
-- Input models: main_intermediate.int_user_daily_activity
-- Metric definition: For each anchor date, count users with activity on that date. D1 retention = users active on anchor date AND on anchor date + 1 day, divided by anchor date users. D7 and D30 follow the same pattern with 7-day and 30-day offsets.
-- Assumptions: Users must have activity on the anchor date to be eligible. The metric uses calendar day alignment (not business days). The LEFT JOIN approach handles dates near the end of the dataset where future dates may not exist (returns NULL / 0).
-- Expected use: Executive dashboard retention metrics; product team evaluation of engagement features; investor reporting.

WITH eligible_users AS (
    SELECT DISTINCT
        activity_date,
        user_id
    FROM main_intermediate.int_user_daily_activity
    WHERE had_export = 1  -- Only count days where user actually exported (meaningful engagement)
),

anchor_counts AS (
    SELECT
        activity_date,
        COUNT(DISTINCT user_id) AS active_users
    FROM eligible_users
    GROUP BY activity_date
),

retention_joins AS (
    SELECT
        a.activity_date,
        a.user_id,
        CASE WHEN d1.user_id IS NOT NULL THEN 1 ELSE 0 END AS retained_d1,
        CASE WHEN d7.user_id IS NOT NULL THEN 1 ELSE 0 END AS retained_d7,
        CASE WHEN d30.user_id IS NOT NULL THEN 1 ELSE 0 END AS retained_d30
    FROM eligible_users a
    LEFT JOIN eligible_users d1
        ON a.user_id = d1.user_id AND d1.activity_date = a.activity_date + INTERVAL '1 day'
    LEFT JOIN eligible_users d7
        ON a.user_id = d7.user_id AND d7.activity_date = a.activity_date + INTERVAL '7 days'
    LEFT JOIN eligible_users d30
        ON a.user_id = d30.user_id AND d30.activity_date = a.activity_date + INTERVAL '30 days'
)

SELECT
    r.activity_date,
    ac.active_users,
    SUM(r.retained_d1)  AS retained_d1_users,
    SUM(r.retained_d7)  AS retained_d7_users,
    SUM(r.retained_d30) AS retained_d30_users,
    ROUND(SUM(r.retained_d1)  * 100.0 / NULLIF(ac.active_users, 0), 2) AS d1_retention_pct,
    ROUND(SUM(r.retained_d7)  * 100.0 / NULLIF(ac.active_users, 0), 2) AS d7_retention_pct,
    ROUND(SUM(r.retained_d30) * 100.0 / NULLIF(ac.active_users, 0), 2) AS d30_retention_pct
FROM retention_joins r
INNER JOIN anchor_counts ac ON r.activity_date = ac.activity_date
GROUP BY r.activity_date, ac.active_users
ORDER BY r.activity_date;
