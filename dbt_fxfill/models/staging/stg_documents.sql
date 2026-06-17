-- Staging: documents dimension table
SELECT
    document_id,
    user_id,
    document_type,
    language,
    CAST(page_count AS INTEGER) AS page_count,
    complexity_level,
    CAST(contains_pii AS BOOLEAN) AS contains_pii,
    CAST(contains_high_risk_terms AS BOOLEAN) AS contains_high_risk_terms,
    CAST(created_at AS TIMESTAMP) AS created_at,
    CAST(created_at AS DATE) AS created_date,
    CASE WHEN complexity_level = 'complex' THEN TRUE ELSE FALSE END AS is_complex,
    _source_run_id,
    _source_config_hash,
    _loaded_at_utc
FROM {{ source('raw', 'raw_documents') }}
