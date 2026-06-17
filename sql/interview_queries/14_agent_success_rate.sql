-- Business question: What is the daily agent success rate, and what is its 7-day rolling average trend? The moving average smooths daily volatility to reveal the underlying direction of agent reliability.
-- Grain: one row per date
-- Input models: main_staging.stg_agent_runs
-- Metric definition:
--   daily_success_rate = SUM(CASE WHEN success_flag THEN 1 ELSE 0 END) / COUNT(*) for that day
--   moving_avg_7d = AVG(daily_success_rate) over a 7-row window including current and prior 6 days (RANGE BETWEEN). Additional metrics: p95 latency, avg cost per run, avg retry count.
-- Assumptions: Each agent_run has a non-null started_at timestamp. The 7-day moving average uses ROWS BETWEEN for deterministic behaviour; if a day has zero runs it would be excluded (the CROSS JOIN date spine would preserve it with NULL).
-- Expected use: Agent reliability monitoring dashboard; alert threshold tuning; release impact assessment.

WITH date_spine AS (
    SELECT DISTINCT started_at::DATE AS run_date
    FROM main_staging.stg_agent_runs
),

daily_metrics AS (
    SELECT
        ar.started_at::DATE AS run_date,
        COUNT(*)                                                      AS total_runs,
        SUM(CASE WHEN ar.success_flag THEN 1 ELSE 0 END)              AS successful_runs,
        ROUND(
            SUM(CASE WHEN ar.success_flag THEN 1 ELSE 0 END) * 100.0
            / NULLIF(COUNT(*), 0), 2
        )                                                              AS success_rate_pct,
        ROUND(AVG(ar.total_latency_ms), 2)                             AS avg_latency_ms,
        ROUND(AVG(ar.estimated_cost_usd), 6)                           AS avg_cost_usd,
        ROUND(AVG(ar.retry_count), 2)                                  AS avg_retry_count,
        ROUND(AVG(ar.total_input_tokens + ar.total_output_tokens), 1)  AS avg_total_tokens
    FROM main_staging.stg_agent_runs ar
    GROUP BY ar.started_at::DATE
)

SELECT
    ds.run_date,
    COALESCE(dm.total_runs, 0)                                             AS total_runs,
    COALESCE(dm.successful_runs, 0)                                        AS successful_runs,
    COALESCE(dm.success_rate_pct, 0)                                       AS success_rate_pct,
    ROUND(AVG(dm.success_rate_pct) OVER (
        ORDER BY ds.run_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                                                                  AS moving_avg_7d_success_rate,
    COALESCE(dm.avg_latency_ms, 0)                                         AS avg_latency_ms,
    ROUND(AVG(dm.avg_latency_ms) OVER (
        ORDER BY ds.run_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)                                                                  AS moving_avg_7d_latency,
    COALESCE(dm.avg_cost_usd, 0)                                           AS avg_cost_usd,
    COALESCE(dm.avg_retry_count, 0)                                        AS avg_retry_count
FROM date_spine ds
LEFT JOIN daily_metrics dm ON ds.run_date = dm.run_date
ORDER BY ds.run_date;
