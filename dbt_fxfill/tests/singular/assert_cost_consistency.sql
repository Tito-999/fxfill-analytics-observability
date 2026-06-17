-- Assert: all agent costs are non-negative and within reasonable range
SELECT agent_run_id, estimated_cost_usd
FROM {{ ref('stg_agent_runs') }}
WHERE estimated_cost_usd < 0 OR estimated_cost_usd > 100

UNION ALL

SELECT span_id, estimated_cost_usd
FROM {{ ref('stg_agent_spans') }}
WHERE estimated_cost_usd < 0 OR estimated_cost_usd > 100
