-- Mart: Model version and prompt version cost/quality comparison
-- Grain: (run_date, model_name, prompt_version)
SELECT
    run_date,
    model_name,
    prompt_version,
    COUNT(*) AS run_count,
    AVG(estimated_cost_usd) AS avg_cost_usd,
    AVG(total_latency_ms) AS avg_latency_ms,
    AVG(field_accuracy) AS avg_field_accuracy,
    AVG(quality_score) AS avg_quality_score,
    SUM(total_input_tokens) AS total_input_tokens,
    SUM(total_output_tokens) AS total_output_tokens,
    AVG(retry_count) AS avg_retry_count,
    SUM(CASE WHEN success_flag THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0) AS success_rate
FROM {{ ref('stg_agent_runs') }}
GROUP BY run_date, model_name, prompt_version
ORDER BY run_date, model_name, prompt_version
