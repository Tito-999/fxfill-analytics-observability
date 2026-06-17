-- Business question: How many new users sign up each day, and what fraction complete their first successful export (activation) within 7 days? This identifies whether the onboarding experience is effective at converting signups into value-generating users.
-- Grain: one row per signup_date (cohort date)
-- Input models: main_staging.stg_users, main_intermediate.int_user_cohorts
-- Metric definition:
--   new_users = count of users who signed up on that date
--   activated_users = count of those users who had their first export within 7 days of signup
--   activation_rate = activated_users / new_users
-- Assumptions: "Activation" is defined as a successful first export, captured in int_user_cohorts.days_to_activation. Only users with a known signup_date are included.
-- Expected use: Product team weekly review of onboarding funnel performance; input to growth forecasts.

WITH new_users AS (
    SELECT
        signup_date,
        user_id
    FROM main_staging.stg_users
),

activation_data AS (
    SELECT
        nu.signup_date,
        nu.user_id,
        iuc.days_to_activation,
        CASE WHEN iuc.days_to_activation <= 7 THEN 1 ELSE 0 END AS activated_within_7d
    FROM new_users nu
    LEFT JOIN main_intermediate.int_user_cohorts iuc
        ON nu.user_id = iuc.user_id
)

SELECT
    signup_date,
    COUNT(user_id)                                           AS new_users,
    SUM(activated_within_7d)                                 AS activated_within_7d,
    ROUND(SUM(activated_within_7d) * 100.0 / NULLIF(COUNT(user_id), 0), 2) AS activation_rate_pct,
    ROUND(AVG(days_to_activation), 2)                        AS avg_days_to_activation,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY days_to_activation) AS median_days_to_activation
FROM activation_data
WHERE signup_date IS NOT NULL
GROUP BY signup_date
ORDER BY signup_date;
