-- Business question: How do different model versions compare on the trade-off between cost and quality? This helps the ML/engineering team decide which model to default to, whether a more expensive model justifies its cost, and when to roll out a new version.
-- Grain: one row per model_name (optionally split by prompt_version)
-- Input models: main_staging.stg_agent_runs
-- Metric definition: For each model, aggregate run count, average cost, average field_accuracy, average quality_score, success_rate, and compute cost-per-accuracy-point and cost-per-quality-point as efficiency ratios. The "scatter-like" output is designed for plotting cost vs quality.
-- Assumptions: field_accuracy (0-100 scale) and quality_score (0-100 scale) are comparable across models. Higher values are better. estimated_cost_usd is the total cost per run including retries.
-- Expected use: Model selection decisions; cost optimisation; A/B test result interpretation; quarterly model performance reviews.

WITH model_aggregates AS (
    SELECT
        model_name,
        prompt_version,
        COUNT(*)                                                        AS run_count,
        SUM(CASE WHEN success_flag THEN 1 ELSE 0 END)                   AS successful_runs,
        ROUND(
            SUM(CASE WHEN success_flag THEN 1 ELSE 0 END) * 100.0
            / NULLIF(COUNT(*), 0), 2
        )                                                               AS success_rate_pct,
        ROUND(AVG(estimated_cost_usd), 6)                               AS avg_cost_usd,
        ROUND(AVG(total_latency_ms), 2)                                 AS avg_latency_ms,
        ROUND(AVG(quality_score), 2)                                    AS avg_quality_score,
        ROUND(AVG(field_accuracy), 2)                                   AS avg_field_accuracy,
        ROUND(AVG(total_input_tokens + total_output_tokens), 1)         AS avg_total_tokens,
        ROUND(AVG(retry_count), 2)                                      AS avg_retry_count,
        ROUND(AVG(manual_edit_count), 2)                                AS avg_manual_edit_count,
        ROUND(
            AVG(estimated_cost_usd) / NULLIF(AVG(field_accuracy), 0), 8
        )                                                               AS cost_per_accuracy_point,
        ROUND(
            AVG(estimated_cost_usd) / NULLIF(AVG(quality_score), 0), 8
        )                                                               AS cost_per_quality_point,
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_latency_ms)  AS p50_latency_ms,
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms)  AS p95_latency_ms
    FROM main_staging.stg_agent_runs
    WHERE estimated_cost_usd IS NOT NULL
      AND quality_score IS NOT NULL
    GROUP BY model_name, prompt_version
)

SELECT
    model_name,
    prompt_version,
    run_count,
    successful_runs,
    success_rate_pct,
    avg_cost_usd,
    avg_latency_ms,
    p50_latency_ms,
    p95_latency_ms,
    avg_quality_score,
    avg_field_accuracy,
    avg_total_tokens,
    avg_retry_count,
    avg_manual_edit_count,
    cost_per_accuracy_point,
    cost_per_quality_point,
    ROUND(avg_quality_score * 100.0 / NULLIF(avg_cost_usd, 0), 2) AS quality_per_dollar,
    ROUND(avg_field_accuracy * 100.0 / NULLIF(avg_cost_usd, 0), 2) AS accuracy_per_dollar,
    ROW_NUMBER() OVER (ORDER BY avg_quality_score DESC, avg_cost_usd ASC) AS efficiency_rank
FROM model_aggregates
ORDER BY efficiency_rank;
