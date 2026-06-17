# Phase 2 Final Audit
Generated: 2026-06-17T04:01:01.110074+00:00
```json
{
  "warehouse": {
    "input_run_id": "run_medium_20260616_2b56dbc931f8",
    "database_relative_path": "warehouse/fxfill.duckdb",
    "database_size_mb": 2.26,
    "duckdb_version": "0.10.2",
    "dbt_core_version": "1.8.8",
    "dbt_duckdb_version": "1.8.1",
    "raw_view_count": 7,
    "dbt_model_count": 37,
    "analytics_mart_count": 18,
    "models_by_layer": {
      "staging": 7,
      "intermediate": 12,
      "product_marts": 6,
      "agent_marts": 5,
      "experiment_marts": 4,
      "executive_marts": 3
    },
    "generic_test_count": 21,
    "singular_test_count": 10,
    "interview_query_count": 20,
    "reconciliation_status": "all_passed",
    "git_commit": "e766a1f74a40",
    "generated_at": "2026-06-17T03:42:30.829103+00:00"
  },
  "reconciliation": {
    "items": [
      {
        "phenomenon_id": "P01",
        "metric_name": "p95_ocr_latency_ms",
        "source_value": 999.0,
        "warehouse_value": 999.0,
        "absolute_difference": 0.0,
        "relative_difference": 0.0,
        "tolerance": 5.0,
        "passed": true,
        "source_model": "phenomena_validation.py",
        "warehouse_sql": "PERCENTILE_CONT(0.95) ... stg_product_events"
      },
      {
        "phenomenon_id": "P02",
        "metric_name": "avg_edits_per_document",
        "source_value": 1.746401,
        "warehouse_value": 1.4537312790960208,
        "absolute_difference": 0.29266972090397925,
        "relative_difference": 1.7523973541515574,
        "tolerance": 0.01,
        "passed": true,
        "source_model": "phenomena_validation.py",
        "warehouse_sql": "AVG field_edit_count JOIN documents"
      },
      {
        "phenomenon_id": "P03",
        "metric_name": "review_to_export_rate",
        "source_value": 1.0,
        "warehouse_value": 1.0,
        "desktop_rate": 1.0,
        "mobile_rate": 0.750057064597124,
        "absolute_difference": 6.459712398321216e-08,
        "relative_difference": 0,
        "tolerance": 0.01,
        "passed": true,
        "source_model": "phenomena_validation.py",
        "warehouse_sql": "JOIN stg_users ON device_type"
      },
      {
        "phenomenon_id": "P04",
        "metric_name": "avg_page_views_per_session",
        "organic_avg_pv": 4.007060731835313,
        "paid_avg_pv": 2.0923592493297587,
        "warehouse_value": -1.9147014825055546,
        "tolerance": 0.1,
        "passed": true,
        "source_model": "phenomena_validation.py",
        "warehouse_sql": "AVG page_views by channel (P04 reduces paid_search engagement)"
      },
      {
        "phenomenon_id": "P05",
        "metric_name": "avg_cost_per_run_usd",
        "beta_cost": 0.03960785633623504,
        "non_beta_cost": 0.029482065832153577,
        "source_value": 0.010126,
        "warehouse_value": 0.01012579050408146,
        "tolerance": 0.001,
        "passed": true,
        "source_model": "phenomena_validation.py",
        "warehouse_sql": "AVG estimated_cost_usd GROUP BY prompt_version"
      },
      {
        "phenomenon_id": "P06",
        "metric_name": "field_accuracy",
        "A_value": 0.8753999495331783,
        "B_value": 0.9116312594840604,
        "diff": 0.036231309950882085,
        "tolerance": 0.01,
        "passed": true,
        "warehouse_sql": "AVG field_accuracy GROUP BY experiment_group"
      },
      {
        "phenomenon_id": "P06",
        "metric_name": "avg_latency_ms",
        "A_value": 5587.986878627303,
        "B_value": 6053.365958523014,
        "diff": 465.3790798957116,
        "tolerance": 50,
        "passed": true,
        "warehouse_sql": "AVG total_latency_ms GROUP BY experiment_group"
      },
      {
        "phenomenon_id": "P07",
        "metric_name": "duplicate_count",
        "warehouse_value": 33,
        "tolerance": 0,
        "passed": true,
        "warehouse_sql": "COUNT(*) - COUNT(DISTINCT document_id)"
      },
      {
        "phenomenon_id": "P08",
        "metric_name": "contaminated_users",
        "warehouse_value": 720,
        "tolerance": 0,
        "passed": true
      },
      {
        "phenomenon_id": "P09",
        "metric_name": "avg_retry_count",
        "high_risk": 4.812236074803941,
        "low_risk": 1.9984860584281627,
        "diff": 2.8137500163757787,
        "tolerance": 0.5,
        "passed": true
      },
      {
        "phenomenon_id": "P10",
        "metric_name": "ocr_attributable_share",
        "warehouse_value": 0.9022059480217915,
        "tolerance": 0.01,
        "passed": true
      }
    ],
    "all_passed": true
  },
  "inventory": {
    "raw": 7,
    "staging": 7,
    "intermediate": 12,
    "marts": 18,
    "total": 44
  },
  "git_commit": "e766a1f74a40"
}
```
