/*
  assert_metric_denominators_nonzero.sql

  Asserts that key metric denominators in mart_agent_daily_kpis are strictly
  positive. Division-by-zero in computed metrics yields infinite or null results,
  corrupting downstream aggregates. This test checks the following denominator
  fields are non-zero and non-null:
    - total_runs

  Returns rows where any denominator is zero or null.
*/

select
    run_date,
    total_runs
from {{ ref('mart_agent_daily_kpis') }}
where
    coalesce(total_runs, 0) = 0
