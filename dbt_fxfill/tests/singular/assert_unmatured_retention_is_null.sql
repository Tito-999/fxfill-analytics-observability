-- Unmatured retention rates must be NULL (not 0)
-- Returns 0 rows when all unmatured rates are properly NULL
SELECT cohort_date, acquisition_channel,
       d1_matured, d1_retention_rate,
       d7_matured, d7_retention_rate,
       d30_matured, d30_retention_rate
FROM {{ ref('mart_retention_cohort') }}
WHERE
    (NOT d1_matured AND d1_retention_rate IS NOT NULL)
    OR (NOT d7_matured AND d7_retention_rate IS NOT NULL)
    OR (NOT d30_matured AND d30_retention_rate IS NOT NULL)
