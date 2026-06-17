-- Every agent_run.task_id must exist in product events
-- Returns 0 rows when all agent tasks match a product task
SELECT DISTINCT ar.task_id
FROM {{ ref('stg_agent_runs') }} ar
WHERE ar.task_id NOT IN (
    SELECT DISTINCT task_id FROM {{ ref('stg_product_events') }}
)
