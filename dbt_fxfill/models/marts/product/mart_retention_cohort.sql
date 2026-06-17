-- Mart: Retention cohort (D1, D7, D30)
WITH user_active_dates AS (
    SELECT DISTINCT e.user_id, e.event_date
    FROM {{ ref('stg_product_events') }} e
),
retention AS (
    SELECT
        c.user_id,
        c.signup_date AS cohort_date,
        c.acquisition_channel,
        MAX(CASE WHEN a.event_date = c.signup_date + INTERVAL 1 DAY THEN 1 ELSE 0 END) AS d1_retained,
        MAX(CASE WHEN a.event_date = c.signup_date + INTERVAL 7 DAY THEN 1 ELSE 0 END) AS d7_retained,
        MAX(CASE WHEN a.event_date = c.signup_date + INTERVAL 30 DAY THEN 1 ELSE 0 END) AS d30_retained
    FROM {{ ref('int_user_cohorts') }} c
    LEFT JOIN user_active_dates a ON c.user_id = a.user_id
    GROUP BY c.user_id, c.signup_date, c.acquisition_channel
)
SELECT
    cohort_date,
    acquisition_channel,
    COUNT(*) AS eligible_users,
    SUM(d1_retained) AS d1_retained_users,
    SUM(d7_retained) AS d7_retained_users,
    SUM(d30_retained) AS d30_retained_users,
    SUM(d1_retained) * 1.0 / COUNT(*) AS d1_retention_rate,
    SUM(d7_retained) * 1.0 / COUNT(*) AS d7_retention_rate,
    SUM(d30_retained) * 1.0 / COUNT(*) AS d30_retention_rate
FROM retention
GROUP BY cohort_date, acquisition_channel
