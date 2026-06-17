-- Business question: What is the distribution of days from user signup to first successful task export across the user base? Understanding this helps set expectations for onboarding timelines and identify users who may need additional support.
-- Grain: one row per user_id (only users who have achieved a first export)
-- Input models: main_staging.stg_users, main_intermediate.int_user_first_activity
-- Metric definition: days_to_export = first_export_date - signup_date (integer). RANK and ROW_NUMBER are both demonstrated to show different tie-breaking strategies.
-- Assumptions: Only users with a non-null first_export_date are included. RANK assigns the same rank to users with equal days_to_export, creating gaps; ROW_NUMBER assigns a unique sequential number arbitrarily for ties.
-- Expected use: Onboarding funnel analysis, setting SLA targets for time-to-value, identifying cohorts that convert faster or slower than average.

WITH user_signup AS (
    SELECT
        user_id,
        signup_date
    FROM main_staging.stg_users
),

first_export AS (
    SELECT
        user_id,
        first_export_date
    FROM main_intermediate.int_user_first_activity
    WHERE first_export_date IS NOT NULL
),

days_calc AS (
    SELECT
        us.user_id,
        us.signup_date,
        fe.first_export_date,
        (fe.first_export_date - us.signup_date) AS days_to_export
    FROM user_signup us
    INNER JOIN first_export fe ON us.user_id = fe.user_id
)

SELECT
    user_id,
    signup_date,
    first_export_date,
    days_to_export,
    RANK()       OVER (ORDER BY days_to_export) AS rank_days_to_export,
    ROW_NUMBER() OVER (ORDER BY days_to_export, user_id) AS row_number_days_to_export,
    DENSE_RANK() OVER (ORDER BY days_to_export) AS dense_rank_days_to_export,
    CASE
        WHEN days_to_export <= 1 THEN 'same_or_next_day'
        WHEN days_to_export <= 7 THEN 'within_1_week'
        WHEN days_to_export <= 30 THEN 'within_1_month'
        WHEN days_to_export <= 90 THEN 'within_3_months'
        ELSE 'over_3_months'
    END AS time_bucket
FROM days_calc
ORDER BY days_to_export, user_id;
