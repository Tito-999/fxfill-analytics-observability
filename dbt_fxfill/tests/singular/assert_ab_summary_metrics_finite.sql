-- A/B test summary metrics must be finite (no INF, -INF, NaN)
-- Returns 0 rows when all metrics are finite
SELECT experiment_group, avg_field_accuracy, avg_latency_ms, cost_per_task
FROM {{ ref('mart_ab_test_summary') }}
WHERE NOT isfinite(avg_field_accuracy)
   OR NOT isfinite(avg_latency_ms)
   OR NOT isfinite(cost_per_task)
