-- Mart: Retention cohort (D1, D7, D30) with right-censoring maturity logic
-- Grain: one row per (cohort_date, acquisition_channel)

WITH observation_window AS (
    SELECT MAX(event_date) AS observation_end_date
    FROM {{ ref('stg_product_events') }}
),

user_active_dates AS (
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
),

cohort_agg AS (
    SELECT
        cohort_date,
        acquisition_channel,
        COUNT(*) AS eligible_users,
        SUM(d1_retained) AS d1_retained_users,
        SUM(d7_retained) AS d7_retained_users,
        SUM(d30_retained) AS d30_retained_users
    FROM retention
    GROUP BY cohort_date, acquisition_channel
)

SELECT
    ca.cohort_date,
    ca.acquisition_channel,
    ca.eligible_users,

    -- D1 maturity: cohort_date <= observation_end_date - 1 day
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 1 DAY
         THEN TRUE ELSE FALSE END AS d1_matured,
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 1 DAY
         THEN ca.eligible_users ELSE 0 END AS d1_eligible_users,

    -- D7 maturity: cohort_date <= observation_end_date - 7 days
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 7 DAY
         THEN TRUE ELSE FALSE END AS d7_matured,
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 7 DAY
         THEN ca.eligible_users ELSE 0 END AS d7_eligible_users,

    -- D30 maturity: cohort_date <= observation_end_date - 30 days
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 30 DAY
         THEN TRUE ELSE FALSE END AS d30_matured,
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 30 DAY
         THEN ca.eligible_users ELSE 0 END AS d30_eligible_users,

    -- Retained users: always reported (for reference), but rate is NULL when unmatured
    ca.d1_retained_users,
    ca.d7_retained_users,
    ca.d30_retained_users,

    -- Retention rates: NULL when unmatured, computed when matured
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 1 DAY
         THEN ca.d1_retained_users * 1.0 / NULLIF(ca.eligible_users, 0)
         ELSE NULL END AS d1_retention_rate,
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 7 DAY
         THEN ca.d7_retained_users * 1.0 / NULLIF(ca.eligible_users, 0)
         ELSE NULL END AS d7_retention_rate,
    CASE WHEN ca.cohort_date <= ow.observation_end_date - INTERVAL 30 DAY
         THEN ca.d30_retained_users * 1.0 / NULLIF(ca.eligible_users, 0)
         ELSE NULL END AS d30_retention_rate,

    ow.observation_end_date
FROM cohort_agg ca
CROSS JOIN observation_window ow
