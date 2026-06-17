-- Business question: How do daily token usage (input + output) and estimated cost trend over time, and what is the cumulative spend to date? This helps the finance and infrastructure teams track cloud costs and forecast future spending.
-- Grain: one row per date
-- Input models: main_staging.stg_agent_runs
-- Metric definition:
--   daily_input_tokens = sum of total_input_tokens for runs that day
--   daily_output_tokens = sum of total_output_tokens
--   daily_cost = sum of estimated_cost_usd
--   cum_input_tokens = window SUM over all prior days
--   cum_cost = window SUM over all prior days
-- Assumptions: estimated_cost_usd reflects the true cost of each run (including any retries). The date spine is built from distinct run dates to avoid gaps. Days with no runs would show as NULL; the COALESCE wrapper handles display but the window function still computes correctly.
-- Expected use: Cloud cost dashboards; capacity planning; financial forecasting; unit-economics analysis (cost per task, cost per user cohort).

WITH date_spine AS (
    SELECT DISTINCT started_at::DATE AS run_date
    FROM main_staging.stg_agent_runs
),

daily_totals AS (
    SELECT
        ar.started_at::DATE AS run_date,
        COUNT(*)                                            AS total_runs,
        SUM(ar.total_input_tokens)                          AS daily_input_tokens,
        SUM(ar.total_output_tokens)                         AS daily_output_tokens,
        SUM(ar.total_input_tokens + ar.total_output_tokens) AS daily_total_tokens,
        SUM(ar.estimated_cost_usd)                          AS daily_cost_usd,
        AVG(ar.estimated_cost_usd)                          AS avg_cost_per_run,
        COUNT(DISTINCT ar.user_id)                          AS distinct_users
    FROM main_staging.stg_agent_runs ar
    GROUP BY ar.started_at::DATE
)

SELECT
    ds.run_date,
    COALESCE(dt.total_runs, 0)                           AS total_runs,
    COALESCE(dt.daily_input_tokens, 0)                   AS daily_input_tokens,
    COALESCE(dt.daily_output_tokens, 0)                  AS daily_output_tokens,
    COALESCE(dt.daily_total_tokens, 0)                   AS daily_total_tokens,
    COALESCE(dt.daily_cost_usd, 0.0)                     AS daily_cost_usd,
    COALESCE(ROUND(dt.avg_cost_per_run, 6), 0.0)         AS avg_cost_per_run,
    COALESCE(dt.distinct_users, 0)                       AS distinct_users,
    SUM(dt.daily_total_tokens) OVER (ORDER BY ds.run_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                     AS cum_total_tokens,
    SUM(dt.daily_input_tokens) OVER (ORDER BY ds.run_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                     AS cum_input_tokens,
    SUM(dt.daily_output_tokens) OVER (ORDER BY ds.run_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                     AS cum_output_tokens,
    ROUND(
        SUM(dt.daily_cost_usd) OVER (ORDER BY ds.run_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 4
    )                                                     AS cum_cost_usd,
    ROUND(
        SUM(dt.daily_cost_usd) OVER (ORDER BY ds.run_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ), 4
    )                                                     AS rolling_7d_cost_usd,
    CASE
        WHEN COALESCE(dt.daily_total_tokens, 0) > 0
        THEN ROUND(dt.daily_cost_usd / dt.daily_total_tokens, 8)
        ELSE NULL
    END                                                   AS cost_per_token
FROM date_spine ds
LEFT JOIN daily_totals dt ON ds.run_date = dt.run_date
ORDER BY ds.run_date;
