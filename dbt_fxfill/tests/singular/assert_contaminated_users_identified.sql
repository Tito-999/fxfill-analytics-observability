/*
  assert_contaminated_users_identified.sql

  Asserts that all users flagged as contaminated in the clean assignments model
  are actually present in the int_experiment_contaminated_users model.
  This ensures the contamination identification pipeline has properly captured
  every contaminated user record.

  Returns users marked as contaminated whose user_id does not appear in the
  contaminated users table.
*/

select distinct
    c.user_id
from {{ ref('int_experiment_clean_assignments') }} c
where
    c.is_contaminated = true
    and not exists (
        select 1
        from {{ ref('int_experiment_contaminated_users') }} cu
        where cu.user_id = c.user_id
    )
