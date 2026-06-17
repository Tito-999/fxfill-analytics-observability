-- Business question: Which error categories contribute the most to total agent failures, and what is their cumulative share? The Pareto analysis (cumulative share) helps the engineering team prioritise which error categories to fix first for the biggest reliability impact.
-- Grain: one row per error_category
-- Input models: main_intermediate.int_agent_error_classification, main_marts.mart_error_root_cause
-- Metric definition: error_count = number of failed agent runs in each error_category. error_share = error_count / total_error_count across all categories. cum_share = running SUM of error_share ordered by error_count DESC. cum_share_80_flag marks categories that fall within the top 80% of errors (Pareto principle).
-- Assumptions: Each failed run maps to exactly one error_category. The mart_error_root_cause table is used for enriched category descriptions (run_error_type, failing_span_name). The window frame is ORDER BY error_count DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.
-- Expected use: Engineering sprint planning; reliability roadmap prioritisation; SLO improvement targeting.

WITH error_totals AS (
    SELECT
        iec.error_category,
        iec.run_error_type,
        iec.failing_span_name,
        iec.success_flag,
        COUNT(*) AS error_count
    FROM main_intermediate.int_agent_error_classification iec
    WHERE iec.success_flag = FALSE
    GROUP BY iec.error_category, iec.run_error_type, iec.failing_span_name, iec.success_flag
),

ranked_errors AS (
    SELECT
        error_category,
        run_error_type,
        failing_span_name,
        error_count,
        ROW_NUMBER() OVER (ORDER BY error_count DESC) AS rank_by_frequency,
        SUM(error_count) OVER () AS total_error_count,
        ROUND(error_count * 100.0 / SUM(error_count) OVER (), 4) AS error_share_pct
    FROM error_totals
)

SELECT
    error_category,
    run_error_type,
    failing_span_name,
    error_count,
    rank_by_frequency,
    error_share_pct,
    ROUND(
        SUM(error_share_pct) OVER (
            ORDER BY error_count DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ), 4
    ) AS cumulative_share_pct,
    CASE
        WHEN SUM(error_share_pct) OVER (
            ORDER BY error_count DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) <= 80 THEN TRUE
        WHEN SUM(error_share_pct) OVER (
            ORDER BY error_count DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) - error_share_pct < 80 THEN TRUE  -- Category that pushes past 80% is still included
        ELSE FALSE
    END AS in_pareto_top_80,
    total_error_count,
    ROUND(
        error_count * 100.0 / NULLIF(MAX(error_count) OVER (), 0), 2
    ) AS pct_of_most_frequent
FROM ranked_errors
ORDER BY rank_by_frequency;
