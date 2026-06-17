-- Agent run user_id and document_id must match product events for the same task_id
-- Returns 0 rows when consistency is maintained
SELECT DISTINCT ar.task_id, ar.user_id AS agent_user, pe.user_id AS product_user,
       ar.document_id AS agent_doc, pe.document_id AS product_doc
FROM {{ ref('stg_agent_runs') }} ar
INNER JOIN (
    SELECT DISTINCT task_id, user_id, document_id FROM {{ ref('stg_product_events') }}
) pe ON ar.task_id = pe.task_id
WHERE ar.user_id != pe.user_id OR ar.document_id != pe.document_id
