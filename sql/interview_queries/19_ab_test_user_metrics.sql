-- Business question: What are the user-level metrics (task success rate, field accuracy, latency, cost) per experiment group, ready for downstream statistical significance testing (e.g., t-test, Mann-Whitney)? This is the input table for the A/B test analysis pipeline.
-- Grain: one row per user_id per experiment assignment
-- Input models: main_intermediate.int_experiment_user_metrics
-- Metric definition: Each metric is computed per user over the duration of their experiment participation. total_tasks / exported_tasks / export_rate define the primary success metric. avg_field_accuracy and avg_latency_ms define quality-of-service metrics. total_cost_usd tracks cost impact.
-- Assumptions: Users are uniquely assigned to one experiment group within an experiment (clean assignments from int_experiment_clean_assignments). The metrics are aggregated over the user's entire experiment window. The output is designed to be fed into a statistical testing framework (e.g., scipy.stats.ttest_ind).
-- Expected use: A/B test analysis pipeline; experiment results dashboards; decision-making for feature rollouts.

WITH clean_assignments AS (
    SELECT
        eca.experiment_id,
        eca.user_id,
        eca.experiment_group,
        eca.assigned_at,
        eca.is_contaminated
    FROM main_intermediate.int_experiment_clean_assignments eca
    WHERE eca.is_contaminated = FALSE
),

user_metrics AS (
    SELECT
        ca.experiment_id,
        ca.user_id,
        ca.experiment_group,
        ca.assigned_at,
        eum.total_tasks,
        eum.exported_tasks,
        eum.export_rate,
        eum.avg_field_accuracy,
        eum.avg_latency_ms,
        eum.total_cost_usd,
        eum.experiment_start_date,
        eum.experiment_end_date,
        ROW_NUMBER() OVER (
            PARTITION BY ca.user_id, ca.experiment_id
            ORDER BY ca.assigned_at DESC
        ) AS rn
    FROM clean_assignments ca
    LEFT JOIN main_intermediate.int_experiment_user_metrics eum
        ON ca.user_id = eum.user_id
        AND ca.experiment_group = eum.experiment_group
)

SELECT
    experiment_id,
    user_id,
    experiment_group,
    assigned_at,
    total_tasks,
    exported_tasks,
    ROUND(export_rate, 4)                                                 AS export_rate,
    ROUND(avg_field_accuracy, 2)                                          AS avg_field_accuracy,
    ROUND(avg_latency_ms, 2)                                              AS avg_latency_ms,
    ROUND(total_cost_usd, 6)                                              AS total_cost_usd,
    (exported_tasks * 1.0) / NULLIF(total_tasks, 0)                       AS task_success_rate,
    ROUND(avg_latency_ms * exported_tasks, 2)                             AS total_latency_cost,
    CASE
        WHEN exported_tasks > 0 THEN ROUND(total_cost_usd / exported_tasks, 8)
        ELSE NULL
    END                                                                   AS cost_per_successful_task,
    CASE
        WHEN experiment_group = 'control' THEN 0
        ELSE 1
    END AS is_treatment,
    DATEDIFF('day', assigned_at::DATE, CURRENT_DATE)                      AS days_since_assignment
FROM user_metrics
WHERE rn = 1
ORDER BY experiment_id, experiment_group, user_id;
