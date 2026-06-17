-- Document features joined with task outcomes for complexity analysis
SELECT
    d.document_id,
    d.user_id,
    d.document_type,
    d.language,
    d.page_count,
    d.complexity_level,
    d.contains_pii,
    d.contains_high_risk_terms,
    d.is_complex,
    COUNT(DISTINCT t.task_id) AS task_count,
    COUNT(DISTINCT CASE WHEN t.is_successful THEN t.task_id END) AS successful_task_count,
    AVG(t.field_edit_count) AS avg_field_edits,
    AVG(t.task_duration_seconds) AS avg_task_duration_seconds
FROM {{ ref('stg_documents') }} d
LEFT JOIN {{ ref('int_task_outcomes') }} t ON d.document_id = t.document_id
GROUP BY ALL
