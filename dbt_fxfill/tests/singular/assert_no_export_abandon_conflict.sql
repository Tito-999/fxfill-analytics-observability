-- No task may be both exported and abandoned (terminal state mutual exclusion)
-- Returns 0 rows when no conflicts exist
SELECT task_id
FROM {{ ref('int_task_funnel_flags') }}
WHERE did_export = 1 AND did_abandon = 1
