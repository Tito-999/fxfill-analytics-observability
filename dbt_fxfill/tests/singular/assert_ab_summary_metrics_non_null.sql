-- A/B test summary must have non-null core metrics for all groups
-- Returns 0 rows when all metrics are present
SELECT experiment_group, avg_field_accuracy, avg_latency_ms, cost_per_task
FROM {{ ref('mart_ab_test_summary') }}
WHERE avg_field_accuracy IS NULL
   OR avg_latency_ms IS NULL
   OR cost_per_task IS NULL
