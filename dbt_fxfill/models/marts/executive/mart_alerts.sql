-- Alert conditions for daily monitoring
WITH daily_metrics AS (
    SELECT
        e.event_date,
        COUNT(DISTINCT e.user_id) AS dau,
        COUNT(DISTINCT e.task_id) AS total_tasks,
        COUNT(DISTINCT CASE WHEN f.did_export THEN e.task_id END) * 1.0 /
            NULLIF(COUNT(DISTINCT e.task_id), 0) AS export_rate,
        COUNT(DISTINCT CASE WHEN f.did_fail THEN e.task_id END) * 1.0 /
            NULLIF(COUNT(DISTINCT e.task_id), 0) AS failure_rate
    FROM {{ ref('stg_product_events') }} e
    LEFT JOIN {{ ref('int_task_funnel_flags') }} f ON e.task_id = f.task_id
    GROUP BY e.event_date
),
agent_daily AS (
    SELECT run_date, agent_success_rate, p95_latency_ms
    FROM {{ ref('mart_agent_daily_kpis') }}
)
SELECT
    d.event_date,
    'quality' AS alert_type,
    CASE
        WHEN d.failure_rate > 0.20 THEN 'HIGH_FAILURE_RATE'
        WHEN d.export_rate < 0.40 THEN 'LOW_EXPORT_RATE'
        WHEN a.agent_success_rate < 0.80 THEN 'LOW_AGENT_SUCCESS'
        WHEN a.p95_latency_ms > 10000 THEN 'HIGH_LATENCY'
        ELSE 'OK'
    END AS alert_status,
    d.failure_rate,
    d.export_rate,
    a.agent_success_rate,
    a.p95_latency_ms
FROM daily_metrics d
LEFT JOIN agent_daily a ON d.event_date = a.run_date
WHERE d.failure_rate > 0.20
   OR d.export_rate < 0.40
   OR a.agent_success_rate < 0.80
   OR a.p95_latency_ms > 10000
