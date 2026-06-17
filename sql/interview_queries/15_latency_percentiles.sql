-- Business question: What are the P50 (median), P90, P95, and P99 latency values for agent runs, broken down by model name? Latency percentiles help the engineering team set SLOs and identify model-level performance degradation.
-- Grain: one row per day per model_name
-- Input models: main_staging.stg_agent_runs
-- Metric definition: Latency percentiles computed with PERCENTILE_CONT (continuous interpolation). P50 = PERCENTILE_CONT(0.5), P90 = (0.9), P95 = (0.95), P99 = (0.99). Aggregated per run_date and model_name.
-- Assumptions: total_latency_ms is measured from agent run start to end and includes all processing steps. PERCENTILE_CONT returns interpolated values; for exact discrete values, PERCENTILE_DISC could be used instead. Runs with NULL latency are excluded.
-- Expected use: SLO monitoring dashboards; capacity planning; model performance comparisons; alerting thresholds for p95/p99 violations.

WITH daily_model_latency AS (
    SELECT
        started_at::DATE AS run_date,
        model_name,
        COUNT(*) AS total_runs,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_latency_ms) AS p50_latency_ms,
        PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY total_latency_ms) AS p90_latency_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) AS p95_latency_ms,
        PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_latency_ms) AS p99_latency_ms,
        MIN(total_latency_ms) AS min_latency_ms,
        MAX(total_latency_ms) AS max_latency_ms,
        ROUND(AVG(total_latency_ms), 2) AS avg_latency_ms
    FROM main_staging.stg_agent_runs
    WHERE total_latency_ms IS NOT NULL
    GROUP BY started_at::DATE, model_name
)

SELECT
    run_date,
    model_name,
    total_runs,
    ROUND(p50_latency_ms, 2)  AS p50_latency_ms,
    ROUND(p90_latency_ms, 2)  AS p90_latency_ms,
    ROUND(p95_latency_ms, 2)  AS p95_latency_ms,
    ROUND(p99_latency_ms, 2)  AS p99_latency_ms,
    ROUND(min_latency_ms, 2)  AS min_latency_ms,
    ROUND(max_latency_ms, 2)  AS max_latency_ms,
    ROUND(avg_latency_ms, 2)  AS avg_latency_ms,
    ROUND(p99_latency_ms - p50_latency_ms, 2) AS p99_to_p50_spread,
    ROUND(
        (p99_latency_ms - p50_latency_ms) / NULLIF(p50_latency_ms, 0), 4
    ) AS relative_spread_p99_to_p50,
    ROUND(
        p95_latency_ms * 100.0 / NULLIF(p50_latency_ms, 0), 2
    ) AS p95_as_pct_of_median
FROM daily_model_latency
ORDER BY run_date, model_name;
