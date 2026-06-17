-- Intermediate: Clean experiment assignments (excluding contaminated users)
WITH contaminated_users AS (
    SELECT user_id
    FROM {{ ref('stg_experiment_assignments') }}
    WHERE NOT is_intentional_contamination
    GROUP BY user_id
    HAVING COUNT(DISTINCT experiment_group) > 1

    UNION

    SELECT user_id
    FROM {{ ref('stg_experiment_assignments') }}
    WHERE is_intentional_contamination
)

SELECT
    ea.assignment_id,
    ea.experiment_id,
    ea.user_id,
    ea.experiment_group,
    ea.assigned_at,
    CASE WHEN cu.user_id IS NOT NULL THEN TRUE ELSE FALSE END AS is_contaminated
FROM {{ ref('stg_experiment_assignments') }} ea
LEFT JOIN (SELECT DISTINCT user_id FROM contaminated_users) cu ON ea.user_id = cu.user_id
WHERE NOT ea.is_intentional_contamination
