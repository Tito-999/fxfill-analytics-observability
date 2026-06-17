-- Staging: experiment assignments table
SELECT
    assignment_id,
    experiment_id,
    user_id,
    experiment_group,
    CAST(assigned_at AS TIMESTAMP) AS assigned_at,
    CAST(is_intentional_contamination AS BOOLEAN) AS is_intentional_contamination,
    _source_run_id,
    _source_config_hash,
    _loaded_at_utc
FROM {{ source('raw', 'raw_experiment_assignments') }}
