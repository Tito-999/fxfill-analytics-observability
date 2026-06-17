-- Executive scorecard must have unique event_date (no channel-level duplicates)
-- Returns 0 rows when grain is strictly one row per event_date
SELECT event_date, COUNT(*) AS cnt
FROM {{ ref('mart_executive_daily_scorecard') }}
GROUP BY event_date
HAVING COUNT(*) > 1
