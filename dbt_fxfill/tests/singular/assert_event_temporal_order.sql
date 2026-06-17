/*
  assert_event_temporal_order.sql

  Asserts that events within a task occur in the correct chronological order
  through the pipeline. Uses the timestamp columns directly from
  int_task_event_sequence. Checks that each pipeline stage's timestamp is
  later than the previous stage's timestamp when both are non-null.

  Returns rows where any temporal ordering constraint is violated.
*/

select
    task_id,
    'ocr_started_before_ocr_completed' as violation_type,
    ocr_started_at as earlier_timestamp,
    ocr_completed_at as later_timestamp
from {{ ref('int_task_event_sequence') }}
where ocr_started_at is not null and ocr_completed_at is not null
  and ocr_completed_at < ocr_started_at

union all

select
    task_id,
    'ocr_completed_before_anonymization_completed' as violation_type,
    ocr_completed_at as earlier_timestamp,
    anonymization_completed_at as later_timestamp
from {{ ref('int_task_event_sequence') }}
where ocr_completed_at is not null and anonymization_completed_at is not null
  and anonymization_completed_at < ocr_completed_at

union all

select
    task_id,
    'anonymization_completed_before_risk_detection_completed' as violation_type,
    anonymization_completed_at as earlier_timestamp,
    risk_detection_completed_at as later_timestamp
from {{ ref('int_task_event_sequence') }}
where anonymization_completed_at is not null and risk_detection_completed_at is not null
  and risk_detection_completed_at < anonymization_completed_at

union all

select
    task_id,
    'risk_detection_completed_before_autofill_completed' as violation_type,
    risk_detection_completed_at as earlier_timestamp,
    autofill_completed_at as later_timestamp
from {{ ref('int_task_event_sequence') }}
where risk_detection_completed_at is not null and autofill_completed_at is not null
  and autofill_completed_at < risk_detection_completed_at

union all

select
    task_id,
    'autofill_completed_before_review_started' as violation_type,
    autofill_completed_at as earlier_timestamp,
    review_started_at as later_timestamp
from {{ ref('int_task_event_sequence') }}
where autofill_completed_at is not null and review_started_at is not null
  and review_started_at < autofill_completed_at

union all

select
    task_id,
    'review_started_before_exported' as violation_type,
    review_started_at as earlier_timestamp,
    exported_at as later_timestamp
from {{ ref('int_task_event_sequence') }}
where review_started_at is not null and exported_at is not null
  and exported_at < review_started_at
