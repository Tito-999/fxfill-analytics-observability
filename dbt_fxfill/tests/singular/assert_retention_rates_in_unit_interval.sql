-- All non-null retention rates must be in [0, 1]
-- Returns 0 rows when all computed rates are valid
SELECT cohort_date, acquisition_channel, d1_retention_rate, d7_retention_rate, d30_retention_rate
FROM {{ ref('mart_retention_cohort') }}
WHERE
    (d1_retention_rate IS NOT NULL AND (d1_retention_rate < 0 OR d1_retention_rate > 1))
    OR (d7_retention_rate IS NOT NULL AND (d7_retention_rate < 0 OR d7_retention_rate > 1))
    OR (d30_retention_rate IS NOT NULL AND (d30_retention_rate < 0 OR d30_retention_rate > 1))
