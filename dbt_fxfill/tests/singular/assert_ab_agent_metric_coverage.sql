-- A/B test groups must have agent metric coverage > 0.99 for experiment tasks
-- Returns 0 rows when coverage is adequate
WITH experiment_tasks AS (
    SELECT DISTINCT task_id, experiment_group
    FROM {{ ref('stg_product_events') }}
    WHERE experiment_group IN ('A', 'B')
),
matched AS (
    SELECT et.task_id, et.experiment_group,
           CASE WHEN ar.agent_run_id IS NOT NULL THEN 1 ELSE 0 END AS has_agent
    FROM experiment_tasks et
    LEFT JOIN {{ ref('stg_agent_runs') }} ar ON et.task_id = ar.task_id
)
SELECT
    experiment_group,
    COUNT(*) AS total_tasks,
    SUM(has_agent) AS tasks_with_agent,
    SUM(has_agent) * 1.0 / NULLIF(COUNT(*), 0) AS coverage_rate
FROM matched
GROUP BY experiment_group
HAVING SUM(has_agent) * 1.0 / NULLIF(COUNT(*), 0) <= 0.99
