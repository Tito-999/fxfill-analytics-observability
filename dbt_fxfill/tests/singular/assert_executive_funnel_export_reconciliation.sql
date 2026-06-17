-- Executive total exported tasks must equal funnel export count (all-time)
WITH exec_total AS (
    SELECT COALESCE(SUM(north_star_metric), 0) AS total FROM {{ ref('mart_executive_daily_scorecard') }}
),
funnel_total AS (
    SELECT CAST(tasks AS BIGINT) AS total FROM {{ ref('mart_conversion_funnel') }} WHERE step = 'exported'
)
SELECT ABS(e.total - f.total) AS delta
FROM exec_total e, funnel_total f
WHERE ABS(e.total - f.total) > 0
