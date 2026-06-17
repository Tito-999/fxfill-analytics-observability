-- Intermediate: User cohorts with signup and activation dates
SELECT
    u.user_id,
    u.signup_date,
    DATE_TRUNC('week', u.signup_date) AS cohort_week,
    DATE_TRUNC('month', u.signup_date) AS cohort_month,
    u.acquisition_channel,
    u.device_type,
    u.user_segment,
    MIN(e.event_date) AS first_activity_date,
    MIN(CASE WHEN e.event_name = 'form_exported' THEN e.event_date END) AS first_export_date,
    MIN(e.event_date) - u.signup_date AS days_to_first_activity,
    MIN(CASE WHEN e.event_name = 'form_exported' THEN e.event_date END) - u.signup_date AS days_to_activation
FROM {{ ref('stg_users') }} u
LEFT JOIN {{ ref('stg_product_events') }} e ON u.user_id = e.user_id
GROUP BY u.user_id, u.signup_date, u.acquisition_channel, u.device_type, u.user_segment
