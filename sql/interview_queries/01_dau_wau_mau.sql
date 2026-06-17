-- Business question: How many distinct active users do we have on a daily, weekly (rolling 7-day), and monthly (rolling 30-day) basis? This helps track user engagement trends and identify growth or decline in active usage.
-- Grain: one row per calendar date
-- Input models: main_staging.stg_product_events
-- Metric definition:
--   dau = count of distinct users who generated a product event on that calendar date
--   wau = rolling 7-day window: count of distinct users whose most recent event date falls within the prior 6 days inclusive of the current row date
--   mau = rolling 30-day window: same logic as wau but over 29 prior days
-- Assumptions: A "user" is identified by user_id. A calendar date series is built from the distinct event_date values in stg_product_events. The window frame is ROWS BETWEEN rather than RANGE to give deterministic behaviour on each row.
-- Expected use: Dashboards for executive daily scorecard, growth team weekly reviews, and investor reporting.

WITH daily_users AS (
    SELECT
        event_date,
        user_id
    FROM main_staging.stg_product_events
    GROUP BY event_date, user_id
),

date_spine AS (
    SELECT DISTINCT event_date
    FROM main_staging.stg_product_events
),

daily_counts AS (
    SELECT
        d.event_date,
        COUNT(DISTINCT du.user_id) AS dau
    FROM date_spine d
    LEFT JOIN daily_users du ON d.event_date = du.event_date
    GROUP BY d.event_date
)

SELECT
    dc.event_date,
    dc.dau,
    SUM(dc.dau) OVER (
        ORDER BY dc.event_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) / 7.0 AS wau_avg_daily,   -- Rolling 7-day average daily users

    SUM(dc.dau) OVER (
        ORDER BY dc.event_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) / 30.0 AS mau_avg_daily,  -- Rolling 30-day average daily users

    -- WAU as distinct user count over rolling 7-day window
    (
        SELECT COUNT(DISTINCT du2.user_id)
        FROM daily_users du2
        WHERE du2.event_date BETWEEN dc.event_date - INTERVAL '6 days' AND dc.event_date
    ) AS wau_distinct,

    -- MAU as distinct user count over rolling 30-day window
    (
        SELECT COUNT(DISTINCT du3.user_id)
        FROM daily_users du3
        WHERE du3.event_date BETWEEN dc.event_date - INTERVAL '29 days' AND dc.event_date
    ) AS mau_distinct

FROM daily_counts dc
ORDER BY dc.event_date;
