-- Daily product KPIs must have unique event_date
SELECT event_date, COUNT(*) AS cnt
FROM {{ ref('mart_daily_product_kpis') }}
GROUP BY event_date
HAVING COUNT(*) > 1
