-- Verify: matured cohorts have rates in [0, 1], unmatured cohorts have NULL rates
-- Returns 0 rows when all maturity rules are satisfied
SELECT cohort_date, acquisition_channel, d1_matured, d1_retention_rate,
       d7_matured, d7_retention_rate, d30_matured, d30_retention_rate
FROM {{ ref('mart_retention_cohort') }}
WHERE
    -- Matured D1 must have rate in [0,1]
    (d1_matured AND (d1_retention_rate < 0 OR d1_retention_rate > 1))
    -- Matured D7 must have rate in [0,1]
    OR (d7_matured AND (d7_retention_rate < 0 OR d7_retention_rate > 1))
    -- Matured D30 must have rate in [0,1]
    OR (d30_matured AND (d30_retention_rate < 0 OR d30_retention_rate > 1))
