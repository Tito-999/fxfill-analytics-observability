-- Identify contaminated users (appearing in both A and B groups)
WITH multi_group AS (
    SELECT
        user_id,
        COUNT(DISTINCT experiment_group) AS group_count,
        STRING_AGG(DISTINCT experiment_group, ',' ORDER BY experiment_group) AS assigned_groups
    FROM {{ ref('stg_experiment_assignments') }}
    GROUP BY user_id
    HAVING COUNT(DISTINCT experiment_group) > 1
)
SELECT
    mg.user_id,
    mg.group_count,
    mg.assigned_groups,
    ea.is_intentional_contamination
FROM multi_group mg
LEFT JOIN {{ ref('stg_experiment_assignments') }} ea ON mg.user_id = ea.user_id
WHERE ea.is_intentional_contamination = TRUE
   OR mg.group_count > 1
