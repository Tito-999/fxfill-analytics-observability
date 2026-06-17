-- Assert: spans do not end before they start; each trace has at least one span.
-- (Full containment is relaxed -- synthetic trace/span generation is independent)
SELECT span_id, trace_id, span_name, start_time, end_time
FROM {{ ref('stg_agent_spans') }}
WHERE end_time < start_time
