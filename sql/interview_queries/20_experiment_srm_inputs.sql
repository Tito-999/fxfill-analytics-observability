-- Business question: Is the A/B test assignment mechanism producing balanced group sizes over time (Sample Ratio Mismatch check)? An SRM occurs when the observed allocation ratio deviates from the expected 50:50 (or 1:1:1 for multi-group), indicating a potential bug in the assignment logic or data pipeline.
-- Grain: one row per experiment per day per experiment_group
-- Input models: main_staging.stg_experiment_assignments, main_intermediate.int_experiment_clean_assignments
-- Metric definition: For each (experiment_id, event_date, experiment_group), count of distinct users assigned. The expected proportion is computed per experiment per day. deviation_from_expected = observed_pct - expected_pct. A chi-squared statistic per experiment per day is approximated for quick SRM flagging.
-- Assumptions: The expected split is uniform across groups (equal allocation). Only non-contaminated assignments (is_contaminated = FALSE) are included for the primary analysis. The full assignments (including potentially contaminated) are shown in a separate column for comparison.
-- Expected use: Experiment quality assurance dashboard; automated SRM detection; data pipeline integrity monitoring.

WITH clean_assignments AS (
    SELECT
        eca.experiment_id,
        eca.user_id,
        eca.experiment_group,
        eca.assigned_at::DATE AS assignment_date
    FROM main_intermediate.int_experiment_clean_assignments eca
),

raw_assignments AS (
    SELECT
        sea.experiment_id,
        sea.user_id,
        sea.experiment_group,
        sea.assigned_at::DATE AS assignment_date
    FROM main_staging.stg_experiment_assignments sea
),

clean_daily_counts AS (
    SELECT
        ca.experiment_id,
        ca.assignment_date,
        ca.experiment_group,
        COUNT(DISTINCT ca.user_id) AS clean_user_count
    FROM clean_assignments ca
    GROUP BY ca.experiment_id, ca.assignment_date, ca.experiment_group
),

raw_daily_counts AS (
    SELECT
        ra.experiment_id,
        ra.assignment_date,
        ra.experiment_group,
        COUNT(DISTINCT ra.user_id) AS raw_user_count
    FROM raw_assignments ra
    GROUP BY ra.experiment_id, ra.assignment_date, ra.experiment_group
),

group_totals AS (
    SELECT
        cdc.experiment_id,
        cdc.assignment_date,
        cdc.experiment_group,
        cdc.clean_user_count,
        COALESCE(rdc.raw_user_count, 0) AS raw_user_count,
        SUM(cdc.clean_user_count) OVER (
            PARTITION BY cdc.experiment_id, cdc.assignment_date
        ) AS total_clean_users_for_experiment,
        COUNT(cdc.experiment_group) OVER (
            PARTITION BY cdc.experiment_id, cdc.assignment_date
        ) AS group_count
    FROM clean_daily_counts cdc
    LEFT JOIN raw_daily_counts rdc
        ON cdc.experiment_id = rdc.experiment_id
        AND cdc.assignment_date = rdc.assignment_date
        AND cdc.experiment_group = rdc.experiment_group
)

SELECT
    experiment_id,
    assignment_date,
    experiment_group,
    clean_user_count,
    raw_user_count,
    total_clean_users_for_experiment,
    ROUND(
        clean_user_count * 100.0 / NULLIF(total_clean_users_for_experiment, 0), 4
    ) AS observed_allocation_pct,
    ROUND(100.0 / NULLIF(group_count, 0), 4) AS expected_allocation_pct,
    ROUND(
        clean_user_count * 100.0 / NULLIF(total_clean_users_for_experiment, 0)
        - 100.0 / NULLIF(group_count, 0), 4
    ) AS deviation_from_expected_pp,
    ROUND(
        POWER(
            clean_user_count - (total_clean_users_for_experiment / NULLIF(group_count, 0)),
            2
        ) / NULLIF((total_clean_users_for_experiment / NULLIF(group_count, 0)), 0), 4
    ) AS chi_squared_contribution,
    raw_user_count - clean_user_count AS potentially_contaminated_users,
    CASE
        WHEN ABS(
            clean_user_count * 100.0 / NULLIF(total_clean_users_for_experiment, 0)
            - 100.0 / NULLIF(group_count, 0)
        ) > 1.0 THEN TRUE
        ELSE FALSE
    END AS srm_flagged
FROM group_totals
WHERE group_count > 0
ORDER BY experiment_id, assignment_date, experiment_group;
