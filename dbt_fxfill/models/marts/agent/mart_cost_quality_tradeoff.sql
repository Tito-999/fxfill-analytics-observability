-- Cost vs quality tradeoff analysis by model and prompt version
SELECT
    model_name,
    prompt_version,
    COUNT(*) AS run_count,
    AVG(estimated_cost_usd) AS avg_cost_usd,
    AVG(field_accuracy) AS avg_field_accuracy,
    AVG(quality_score) AS avg_quality_score,
    AVG(estimated_cost_usd) / NULLIF(AVG(field_accuracy), 0) AS cost_per_accuracy_point,
    SUM(CASE WHEN success_flag THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS success_rate,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms) AS p95_latency_ms
FROM {{ ref('stg_agent_runs') }}
GROUP BY model_name, prompt_version
ORDER BY avg_cost_usd DESC
