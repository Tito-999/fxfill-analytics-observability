/*
  assert_experiment_assignment_integrity.sql

  Asserts that clean experiment assignments have unique (experiment_id, user_id)
  pairs. Each user should be assigned to a given experiment at most once in the
  cleaned assignment set. Duplicates indicate a pipeline or deduplication failure.

  Returns violating (experiment_id, user_id) combinations that appear more than once.
*/

select
    experiment_id,
    user_id,
    count(*) as assignment_count
from {{ ref('int_experiment_clean_assignments') }}
group by experiment_id, user_id
having count(*) > 1
