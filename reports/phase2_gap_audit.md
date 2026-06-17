# Phase 2 Gap Audit

| Model | Layer | Required | Current | Status |
|-------|-------|----------|---------|--------|
| stg_users | staging | ✓ | ✓ | EXISTS |
| stg_documents | staging | ✓ | ✓ | EXISTS |
| stg_sessions | staging | ✓ | ✓ | EXISTS |
| stg_product_events | staging | ✓ | ✓ | EXISTS |
| stg_agent_runs | staging | ✓ | ✓ | EXISTS |
| stg_agent_spans | staging | ✓ | ✓ | EXISTS |
| stg_experiment_assignments | staging | ✓ | ✓ | EXISTS |
| int_user_first_activity | intermediate | ✓ | ✗ | MISSING |
| int_user_daily_activity | intermediate | ✓ | ✗ | MISSING |
| int_user_cohorts | intermediate | ✓ | ✓ | EXISTS |
| int_task_event_sequence | intermediate | ✓ | ✓ | EXISTS |
| int_task_funnel_flags | intermediate | ✓ | ✓ | EXISTS |
| int_task_outcomes | intermediate | ✓ | ✗ | MISSING |
| int_document_complexity_features | intermediate | ✓ | ✗ | MISSING |
| int_agent_trace_rollup | intermediate | ✓ | ✓ | EXISTS |
| int_agent_error_classification | intermediate | ✓ | ✗ | MISSING |
| int_experiment_clean_assignments | intermediate | ✓ | ✓ | EXISTS |
| int_experiment_contaminated_users | intermediate | ✓ | ✗ | MISSING |
| int_experiment_user_metrics | intermediate | ✓ | ✓ | EXISTS |
| mart_daily_product_kpis | product | ✓ | ✓ | EXISTS |
| mart_conversion_funnel | product | ✓ | ✓ | EXISTS |
| mart_retention_cohort | product | ✓ | ✓ | EXISTS |
| mart_feature_adoption | product | ✓ | ✗ | MISSING |
| mart_user_segments | product | ✓ | ✗ | MISSING |
| mart_channel_performance | product | ✓ | ✗ | MISSING |
| mart_agent_daily_kpis | agent | ✓ | ✓ | EXISTS |
| mart_agent_stage_performance | agent | ✓ | ✗ | MISSING |
| mart_model_version_comparison | agent | ✓ | ✓ | EXISTS |
| mart_error_root_cause | agent | ✓ | ✗ | MISSING |
| mart_cost_quality_tradeoff | agent | ✓ | ✗ | MISSING |
| mart_ab_test_user_metrics | experiment | ✓ | ✗ | MISSING |
| mart_ab_test_summary | experiment | ✓ | ✓ | EXISTS |
| mart_ab_test_segment_effects | experiment | ✓ | ✗ | MISSING |
| mart_experiment_guardrails | experiment | ✓ | ✗ | MISSING |
| mart_executive_daily_scorecard | executive | ✓ | ✓ | EXISTS |
| mart_weekly_business_review | executive | ✓ | ✗ | MISSING |
| mart_alerts | executive | ✓ | ✗ | MISSING |

**Summary: 20 exist, 17 missing → target 37**
