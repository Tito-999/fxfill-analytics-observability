-- Assert: success_flag is never NULL and is a valid boolean
SELECT agent_run_id, trace_id, success_flag
FROM {{ ref('stg_agent_runs') }}
WHERE success_flag IS NULL
