# Phase 1 Final Audit Report
**Generated:** 2026-06-17T02:52:19.400146+00:00
**Git Commit:** 23abc6591149fe92b5b52bcdd28e066dd8d14b47
**Git Tag:** phase-1-complete

## Engineering Gates
| Gate | Result |
|------|--------|
| pytest | 159 passed, 0 failed, 0 skipped |
| coverage | 93.04% |
| ruff | passed |
| black | passed |
| mypy | passed |
| pip check | passed |

## Performance
| Metric | Run 1 | Run 2 |
|--------|-------|-------|
| Duration | 28.87s | 28.65s |
| Peak RSS | 894.56MB | 886.62MB |
| Output | 29.36MB | 29.36MB |
| Slowest stage | agent_spans (4.53s) |

**Speedup:** 22.3x (from 643s to 28.87s)

## Canonical Hashes
| Table | Run 1 (first 16) | Run 2 (first 16) | Match |
|-------|-------------------|-------------------|-------|
| users | cd0474c294ffafd5... | cd0474c294ffafd5... | ✅ |
| documents | 2aec2866b349901a... | 2aec2866b349901a... | ✅ |
| sessions | 46b70b4c0be4efca... | 46b70b4c0be4efca... | ✅ |
| product_events | f729de50eceb9cc8... | f729de50eceb9cc8... | ✅ |
| agent_runs | d8a838aa1814e76f... | d8a838aa1814e76f... | ✅ |
| agent_spans | 0e760bb646dc86d0... | 0e760bb646dc86d0... | ✅ |
| experiment_assignments | 867f9eb2d0b40136... | 867f9eb2d0b40136... | ✅ |

Full SHA-256 values in `reports/phase1_final_audit.json`.

## P01–P10 Phenomena Evidence

### P01: p95_ocr_latency_ms
- **Definition:** 95th percentile of OCR event latency for app v2.3.0 vs other versions
- **Baseline:** other_versions (n=75118, value=830.0)
- **Affected:** v2.3.0 (n=18919, value=999.0)
- **Absolute effect:** 169.0
- **Relative effect:** 0.203614
- **Enabled effect:** 169.0
- **Disabled effect:** 6.0
- **Configured threshold:** affected > baseline
- **Passed:** True
- **Test:** test_p01_ocr_latency_direction
- **Source tables:** product_events

### P02: avg_edits_per_document
- **Definition:** Average field_edited events per document, by complexity level
- **Baseline:** simple (n=6369, value=1.590203)
- **Affected:** complex (n=7442, value=3.336603)
- **Absolute effect:** 1.746401
- **Relative effect:** 1.098225
- **Enabled effect:** 1.098225
- **Disabled effect:** -0.003923
- **Configured threshold:** relative uplift >= 0.10
- **Passed:** True
- **Test:** test_p02_enabled_vs_disabled
- **Source tables:** product_events, documents

### P03: review_to_export_rate
- **Definition:** Tasks reaching form_exported / tasks reaching form_review_started, by device_type
- **Baseline:** desktop (n=17999, value=1.0)
- **Affected:** mobile (n=8762, value=0.750057)
- **Absolute effect:** -0.249943
- **Relative effect:** -0.249943
- **Enabled effect:** -0.249943
- **Disabled effect:** 0.0
- **Configured threshold:** affected < baseline
- **Passed:** True
- **Test:** test_p03_medium_direction
- **Source tables:** product_events, users
- **desktop_reviewed_tasks:** 17999
- **desktop_exported_tasks:** 17999
- **mobile_reviewed_tasks:** 8762
- **mobile_exported_tasks:** 6572

### P04: d7_retention_rate
- **Definition:** Fraction of users active on their signup_date + 7 days. Users with <7 days observation excluded.
- **Baseline:** organic (n=6601, value=0.019542)
- **Affected:** paid_search (n=4672, value=0.019264)
- **Absolute effect:** -0.000424
- **Relative effect:** -0.019845
- **Enabled effect:** -0.000424
- **Disabled effect:** -0.000424
- **Configured threshold:** affected < baseline
- **Passed:** True
- **Test:** test_p04_true_d7_retention
- **Source tables:** product_events, users
- **organic_eligible:** 6601
- **organic_retained:** 129
- **paid_search_eligible:** 4672
- **paid_search_retained:** 90

### P05: avg_cost_per_run_usd
- **Definition:** Average estimated cost per agent run, v2.0.0-beta vs other prompt versions
- **Baseline:** v1.x (n=67824, value=0.029482)
- **Affected:** v2.0.0-beta (n=12176, value=0.039608)
- **Absolute effect:** 0.010126
- **Relative effect:** 0.343456
- **Enabled effect:** 0.010126
- **Disabled effect:** 5.8e-05
- **Configured threshold:** affected > baseline (1.35x cost multiplier)
- **Passed:** True
- **Test:** test_p05_prompt_cost_quality_direction
- **Source tables:** agent_runs

### P06: field_accuracy_and_latency
- **Definition:** Experiment B group vs A group: field accuracy uplift (+0.04) and latency increase (+450ms)
- **Baseline:** A (n=3963, value=0.8754)
- **Affected:** B (n=3954, value=0.911631)
- **Absolute effect:** 0.036231
- **Relative effect:** 0.041388
- **Enabled effect:** 0.036231
- **Disabled effect:** -0.000617
- **Configured threshold:** accuracy uplift >=0.02, latency increase >250ms
- **Passed:** True
- **Test:** test_p06_treatment_isolation
- **Source tables:** agent_runs
- **enabled_A_accuracy:** 0.8754
- **enabled_B_accuracy:** 0.911631
- **enabled_accuracy_effect:** 0.036231
- **disabled_A_accuracy:** 0.8754
- **disabled_B_accuracy:** 0.874782
- **disabled_accuracy_effect:** -0.000617
- **enabled_A_latency:** 5587.986879
- **enabled_B_latency:** 6053.365959
- **enabled_latency_effect:** 465.37908
- **disabled_A_latency:** 5587.986879
- **disabled_B_latency:** 5603.365959
- **disabled_latency_effect:** 15.37908

### P07: duplicate_upload_rate
- **Definition:** Fraction of document_uploaded events that are duplicates, on the most affected day
- **Baseline:** overall (n=50033, value=0.00066)
- **Affected:** day_2026-04-30 (n=452, value=0.073009)
- **Absolute effect:** 0.072349
- **Relative effect:** 109.619697
- **Enabled effect:** 0.07300884955752213
- **Disabled effect:** 0.0
- **Configured threshold:** affected-day rate ≈ 0.08 (8%)
- **Passed:** True
- **Test:** test_p07_affected_day_duplicate_rate
- **Source tables:** product_events
- **affected_date:** 2026-04-30
- **unique_uploads_on_affected_date:** 419
- **duplicate_rows_on_affected_date:** 33
- **total_rows_on_affected_date:** 452
- **overall_duplicate_rate:** 0.00066

### P08: users_in_multiple_groups
- **Definition:** Count of users appearing in both A and B experiment groups
- **Baseline:** clean_users (n=11640, value=11640.0)
- **Affected:** contaminated_users (n=360, value=360.0)
- **Absolute effect:** -11280.0
- **Relative effect:** -0.969072
- **Enabled effect:** 360.0
- **Disabled effect:** 0.0
- **Configured threshold:** contaminated > 0
- **Passed:** True
- **Test:** test_p08_cross_group_contamination_detected
- **Source tables:** experiment_assignments

### P09: avg_retry_count
- **Definition:** Average agent retry_count for high-risk vs low-risk documents
- **Baseline:** low_risk (n=60108, value=1.998486)
- **Affected:** high_risk (n=19892, value=4.812236)
- **Absolute effect:** 2.81375
- **Relative effect:** 1.407941
- **Enabled effect:** 2.81375
- **Disabled effect:** 0.006843
- **Configured threshold:** affected > baseline (2.5x multiplier)
- **Passed:** True
- **Test:** test_p09_high_risk_retry_direction
- **Source tables:** agent_runs, documents

### P10: overall_export_impact
- **Definition:** OCR-attributable share of non-exported tasks and impact on overall export rate
- **Baseline:** enabled (n=50000, value=0.55212)
- **Affected:** disabled (n=50000, value=0.59592)
- **Absolute effect:** -0.0438
- **Relative effect:** 0
- **Enabled effect:** 0.55212
- **Disabled effect:** 0.59592
- **Configured threshold:** attributable_share >= 0.20
- **Passed:** True
- **Test:** test_p10_overall_export_impact
- **Source tables:** product_events
- **enabled_ocr_failure_rate:** 0.40408
- **disabled_ocr_failure_rate:** 0.40408
- **enabled_overall_export_rate:** 0.55212
- **disabled_overall_export_rate:** 0.59592
- **export_rate_impact:** -0.0438
- **ocr_attributable_lost_tasks:** 20204
- **all_unsuccessful_tasks:** 22394
- **actual_attributable_share:** 0.902206

## Determinism Root Cause
- **agent_runs_mismatch_root_cause:** Python built-in hash() is randomized between interpreter processes (PYTHONHASHSEED)
- **product_events_mismatch_root_cause:** set() iteration order changed P03 task selection
- **cross_module_rng_coupling:** All generators shared one RNG stream
- **fix_hash:** Replaced with hashlib.md5 for deterministic non-security bucketing
- **fix_set_ordering:** Added sorted() before slicing collections
- **fix_rng_isolation:** SeedSequence.spawn(9) independent RNG streams per module
- **md5_note:** MD5 used only for deterministic non-security bucketing. Not for authentication, integrity, or cryptographic security.
