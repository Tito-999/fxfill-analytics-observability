/*
  assert_funnel_monotonicity.sql

  Asserts that event timestamps within a task are monotonically non-decreasing
  through the pipeline. For each task, the timestamp columns are compared in
  logical pipeline order. If any timestamp is earlier than the preceding step's
  timestamp, the monotonicity property is violated.

  Returns violating rows where a timestamp is earlier than the previous step's timestamp.
*/

select
    task_id,
    'uploaded_at' as step_name,
    uploaded_at as step_timestamp,
    null as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where 1 = 0

union all

select
    task_id,
    'ocr_started_at' as step_name,
    ocr_started_at as step_timestamp,
    uploaded_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where uploaded_at is not null and ocr_started_at is not null
  and ocr_started_at < uploaded_at

union all

select
    task_id,
    'ocr_completed_at' as step_name,
    ocr_completed_at as step_timestamp,
    ocr_started_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where ocr_started_at is not null and ocr_completed_at is not null
  and ocr_completed_at < ocr_started_at

union all

select
    task_id,
    'anonymization_completed_at' as step_name,
    anonymization_completed_at as step_timestamp,
    ocr_completed_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where ocr_completed_at is not null and anonymization_completed_at is not null
  and anonymization_completed_at < ocr_completed_at

union all

select
    task_id,
    'risk_detection_completed_at' as step_name,
    risk_detection_completed_at as step_timestamp,
    anonymization_completed_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where anonymization_completed_at is not null and risk_detection_completed_at is not null
  and risk_detection_completed_at < anonymization_completed_at

union all

select
    task_id,
    'autofill_completed_at' as step_name,
    autofill_completed_at as step_timestamp,
    risk_detection_completed_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where risk_detection_completed_at is not null and autofill_completed_at is not null
  and autofill_completed_at < risk_detection_completed_at

union all

select
    task_id,
    'review_started_at' as step_name,
    review_started_at as step_timestamp,
    autofill_completed_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where autofill_completed_at is not null and review_started_at is not null
  and review_started_at < autofill_completed_at

union all

select
    task_id,
    'exported_at' as step_name,
    exported_at as step_timestamp,
    review_started_at as previous_step_timestamp
from {{ ref('int_task_event_sequence') }}
where review_started_at is not null and exported_at is not null
  and exported_at < review_started_at
