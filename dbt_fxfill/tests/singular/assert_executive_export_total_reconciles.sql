-- Executive north_star_metric sum must match product daily KPI exported_tasks sum
-- Returns 0 rows when the delta is within tolerance
WITH exec_total AS (
    SELECT COALESCE(SUM(north_star_metric), 0) AS total
    FROM {{ ref('mart_executive_daily_scorecard') }}
),
product_total AS (
    SELECT COALESCE(SUM(exported_tasks), 0) AS total
    FROM {{ ref('mart_daily_product_kpis') }}
)
SELECT ABS(e.total - p.total) AS delta
FROM exec_total e, product_total p
WHERE ABS(e.total - p.total) > 1e-9
