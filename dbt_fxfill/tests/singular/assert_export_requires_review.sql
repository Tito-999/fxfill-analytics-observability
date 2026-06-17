/*
  assert_export_requires_review.sql

  Asserts that every task reaching the export stage has also started review.
  This enforces the business rule that a form review must be initiated before
  a form can be exported.

  Returns rows where did_export is true but did_start_review is false or null.
*/

select
    task_id,
    did_export,
    did_start_review
from {{ ref('int_task_funnel_flags') }}
where
    did_export = true
    and (did_start_review is null or did_start_review = false)
