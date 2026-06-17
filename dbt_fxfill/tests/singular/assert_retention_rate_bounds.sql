/*
  assert_retention_rate_bounds.sql

  Asserts that all retention rates in the mart_retention_cohort model fall
  within the valid range [0, 1]. Retention rates below 0 or above 1 indicate
  a calculation error in the upstream model.

  Returns rows where any retention rate is out of bounds.
*/

select
    cohort_date,
    acquisition_channel,
    eligible_users,
    d1_retained_users,
    d7_retained_users,
    d30_retained_users,
    d1_retention_rate,
    d7_retention_rate,
    d30_retention_rate
from {{ ref('mart_retention_cohort') }}
where
    d1_retention_rate < 0 or d1_retention_rate > 1
    or d7_retention_rate < 0 or d7_retention_rate > 1
    or d30_retention_rate < 0 or d30_retention_rate > 1
