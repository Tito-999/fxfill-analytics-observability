# Technical Deep Dive -- FxFill Analytics

This document explains the technical architecture and engineering decisions behind the FxFill product analytics platform. Each section follows the same structure: Problem, Design, Implementation, Tradeoffs, and Verification.

---

## 1. Deterministic Synthetic Data Generation

### Problem
Analytics portfolios built on generated data face a credibility problem: if the data changes between runs, the analysis cannot be reproduced or audited. We need data that is (a) realistic enough to demonstrate analytic methods, (b) completely deterministic from a single seed, and (c) contains known ground-truth phenomena that an analyst must be able to detect.

### Design
A seed-driven pipeline with three guarantees:
1. **Same seed always produces identical output tables** -- byte-for-byte identical SHA-256 hashes across independent runs.
2. **Each generator module is independently seeded** -- no cross-module RNG coupling so that changing one generator does not cascade into unrelated tables.
3. **Ten configurable embedded phenomena (P01-P10)** are injected with specific direction and magnitude, and validated independently in the quality module.

### Implementation
- `numpy.random.SeedSequence(seed).spawn(9)` creates 9 independent child RNG streams, one per generator module (users, sessions, documents, product_events, agent_runs, agent_spans, experiment_assignments, phenomena, manifests).
- Deterministic ID bucketing uses `hashlib.md5(user_id_bytes).hexdigest()` instead of Python's `hash()` (which is randomized across processes by `PYTHONHASHSEED`).
- Collection ordering is stabilized with `sorted()` before `random.sample()` to avoid set-iteration-order nondeterminism.
- Phenomena are defined in `config/data_generation.yml` with `enabled`, `direction`, `magnitude`, and `affected_segment` parameters, then validated by `src/fxfill_analytics/quality/phenomena_validation.py`.
- The pipeline generates 7 Parquet files covering 20,000 users, 80,000 documents, 60,000 sessions, 491,122 product events, 80,000 agent runs, 300,000 agent spans, and 12,360 experiment assignments in ~29 seconds (medium scale).

### Tradeoffs
- SHA-256 is used for stable hashing even though MD5 is sufficient for non-security bucketing; the additional cost is trivial (microseconds per table).
- The SeedSequence approach uses 128 bits of entropy per stream; for this project 9 streams are sufficient, but the approach scales to hundreds.
- Parquet output trades some schema rigidity for columnar compression; output size is ~29 MB for 1M+ rows.

### Verification
- Two independent runs with the same seed produce identical SHA-256 hashes for all 7 tables. The `phase1_final_audit.json` confirms this for every table across run1 and run2.
- All 10 phenomena are detected by `phenomena_validation.py` with `enabled_effect` matching the configured magnitude and `disabled_effect` near zero (confirming phenomenon isolation).
- The pipeline achieves a 22.3x speedup over the initial naive implementation (from 643s to 28.87s) through chunked generation and Parquet compression.

---

## 2. Data Quality and Controlled Anomalies (P01-P10)

### Problem
Real production data contains anomalies, regressions, and data quality issues. An analytics platform needs to detect and explain these -- but for a portfolio project, the anomalies must be intentionally embedded so that detection is verifiable.

### Design
Ten phenomena span the full product lifecycle:

| ID | Phenomenon | Type | Affected Segment |
|----|-----------|------|-----------------|
| P01 | Elevated OCR latency | Performance regression | App v2.3.0 (p95: 999ms vs 830ms) |
| P02 | Higher field edits on complex docs | Data quality | Complex documents (1.75x edits) |
| P03 | Mobile export rate drop | UX bug | Mobile devices (rate: 0.75 vs 1.0) |
| P04 | Paid search retention decline | Channel effect | Paid search users (D7 retention -0.02) |
| P05 | Beta prompt cost increase | Cost regression | v2.0.0-beta ($0.010 cost uplift) |
| P06 | Experiment accuracy/latency tradeoff | Experiment artifact | Treatment group (+0.036 accuracy, +465ms) |
| P07 | Duplicate upload spike | Data pipeline bug | Single day (8% vs 0.07% baseline) |
| P08 | Cross-group experiment contamination | Assignment bug | 360 users in both A and B |
| P09 | High-risk document retries | Agent behavior | High-risk docs (2.8x retries) |
| P10 | OCR-attributable export failure | Root cause | 90% of export failures linked to OCR |

### Implementation
- Each phenomenon generator lives in `src/fxfill_analytics/generation/phenomena.py`, checked by `config/data_generation.yml` for enable/disable flags.
- The quality module (`src/fxfill_analytics/quality/phenomena_validation.py`) independently re-derives each metric from the generated Parquet files and compares against configured thresholds.
- An enable/disable toggle test confirms that each phenomenon appears when enabled and disappears (or falls below threshold) when disabled.
- The warehouse reconciliation tests (`reports/phase2_reconciliation.json`) verify that the same metric computed via source Python and via dbt SQL queries produces matching values within tolerance.

### Tradeoffs
- Phenomena are intentionally exaggerated for detectability; real-world anomalies are subtler and require statistical process control.
- Ten phenomena is a reasonable number for comprehensive demonstration; real products have dozens of concurrent effects that overlap and interact.

### Verification
- All 10 phenomena pass both their unit-level tests (direction/magnitude checks) and warehouse reconciliation tests (Python value vs dbt SQL value).
- For P06, the `test_p06_treatment_isolation` test confirms the accuracy effect is 0.036 when enabled and -0.001 (effectively zero) when disabled.
- The phase 1 and phase 2 audit files programmatically assert this, not via human review.

---

## 3. Warehouse Modeling (DuckDB + dbt)

### Problem
Raw Parquet data is not analytics-ready. A dimensional warehouse with clearly defined layers, documented transformations, and built-in data quality tests is needed to turn raw events into business metrics.

### Design
A 4-layer architecture (raw, staging, intermediate, marts) in DuckDB, accessed through dbt-core with the dbt-duckdb adapter. Each layer has a specific responsibility:

- **Raw (7 tables):** Direct mirror of Parquet files with column type enforcement and primary key constraints. `raw_product_events` holds 491K rows of timestamped event data.
- **Staging (7 views):** Light column renaming, type casting, and not-null filtering. One view per raw table.
- **Intermediate (12 views):** Business logic transforms -- funnel flags, cohort assignments, user activity rollups, trace rollups, experiment contamination detection.
- **Marts (18 tables):** Analytics-ready aggregates -- product KPIs (6), agent observability (5), experiment results (4), executive scorecard (3).

### Implementation
- `dbt_fxfill/models/sources.yml` defines source freshness and column-level tests (not_null, unique, accepted_values) on raw tables.
- Staging models are SQL views; intermediate models are SQL views with CASE/window-functions; marts are materialized tables.
- Mart layer uses Kimball-style fact/dimension design: `mart_conversion_funnel` is a 7-row aggregated fact (one row per funnel step), `mart_retention_cohort` is a 605-row cohort-period matrix, `mart_agent_daily_kpis` is a 121-row daily time series.
- The build is a Python orchestration script (`scripts/build_warehouse.py`) that loads Parquet into DuckDB raw tables, then invokes dbt for the transform layers.

### Tradeoffs
- DuckDB is single-node OLAP, not a production warehouse. Replacing it with Snowflake/BigQuery would require only connection string changes via the dbt profile.
- Views for staging and intermediate layers avoid data duplication but add query-time overhead. For dashboard queries (aggregates over filtered date ranges), the overhead is negligible (<100ms).
- The materialized mart layer is refreshed on each build; incremental materialization is not used since the full dataset is regenerated each time.

### Verification
- `dbt run` completes without errors; `dbt test` passes all 30+ schema tests.
- The `phase2_model_inventory.json` confirms all 44 objects (7 raw + 7 staging + 12 intermediate + 18 marts) exist with correct row counts and column counts.
- The `phase2_reconciliation.json` cross-validates P01-P10 metrics computed via dbt SQL against the same metrics from the Python quality module. All pass within configured tolerance.
- No raw-scan queries leak from the dashboard (verified by `test_no_raw_scans.py`).

---

## 4. Agent Observability

### Problem
AI Agent systems introduce observability challenges beyond traditional web applications: hierarchical trace-span models, LLM latency percentiles, token/cost accounting by model version, and error attribution across agent stages.

### Design
A run/span hierarchy models each user task as an agent run with 8 sub-spans (document_classification, ocr_extraction, pii_detection, anonymization, risk_detection, field_mapping, form_autofill, output_validation). The observability layer tracks latency, token usage, estimated cost, and error status at both the run and span levels.

### Implementation
- Agent trace data is generated by `generate_agent_traces.py` with configurable latency distributions per stage, error rates per stage, and cost multipliers per model version.
- The dbt intermediate model `int_agent_trace_rollup` rolls spans up to runs with P50/P90/P95/P99 latency percentiles, total token counts, and stage-level error flags.
- `int_agent_error_classification` computes error frequencies by category for Pareto analysis.
- Mart models `mart_agent_daily_kpis`, `mart_agent_stage_performance`, `mart_model_version_comparison`, `mart_error_root_cause`, and `mart_cost_quality_tradeoff` serve the Agent Observability dashboard page.
- The dashboard page shows 7 charts: trace timeline distribution, stage-level latency heatmap, token/cost trends, model comparison, error Pareto, and cost-quality scatter.

### Tradeoffs
- The agent cost model uses simplified per-token coefficients rather than real LLM API pricing. Relative cost comparisons between model versions are meaningful; absolute dollar amounts are not.
- There is no live Langfuse or OpenTelemetry integration. The `langfuse_exporter.py` module exists but is gracefully disabled when not configured.
- Span hierarchy is limited to 8 stages per run; real agent systems may have hundreds of nested spans.

### Verification
- Product event task_ids are joinable to agent run trace_ids, confirmed by referential integrity tests.
- Slowest agent stage is identifiable from `int_agent_trace_rollup` (median latency per stage).
- Model version comparison shows v2.0.0-beta with higher accuracy but higher cost vs v1.x, matching the embedded P05/P06 phenomena.
- The Agent Observability dashboard page loads with verified chart rendering and export functionality.

---

## 5. Statistical Correctness

### Problem
A/B tests are full of pitfalls: sample ratio mismatch (SRM), multiple comparisons, non-normal metrics, underpowered designs, and covariate imbalance. An analytics portfolio must demonstrate awareness and handling of each.

### Design
A comprehensive statistical pipeline implemented in `src/fxfill_analytics/experimentation/` with these stages:

1. **User-level ITT:** Analysis is at the user level, not the event level. Users with cross-group contamination (360 users) are excluded. Users without post-assignment outcomes (0 users) trigger a warning. This prevents event-level pseudoreplication.

2. **SRM chi-squared test:** Two SRM checks -- raw assignment-level (12,360 rows, chi2=0.0, p=1.0) and clean ITT user-level (12,000 users, chi2=0.133, p=0.715). The project uses an SRM alpha of 0.001 (conservative per Kohavi et al.) to avoid flagging expected random variation at 0.05.

3. **Standardized mean difference (SMD) for randomization balance:** Three pre-treatment variables (device_type, acquisition_channel, user_segment) are compared between groups. Max absolute SMD is 0.04. No material imbalances detected.

4. **Bootstrap confidence intervals:** 5,000 stratified bootstrap iterations resample user_ids within each group. The bootstrap CI for the primary effect is [0.006, 0.054], slightly wider than the analytic CI [0.005, 0.055], confirming no material distributional assumptions are violated.

5. **Guardrail non-inferiority:** Four guardrails tested with one-sided Holm-adjusted p-values. P95 latency passes non-inferiority at 450ms increase within 500ms margin (p=0.04 adjusted). Cost-per-task fails (p=0.004 adjusted).

6. **Multiplicity correction:** Three secondary metrics use Benjamini-Hochberg at alpha=0.05. Task success rate (BH-adjusted p=0.045) and field accuracy (BH-adjusted p=0.003) remain significant. Manual edit rate does not (BH-adjusted p=0.08).

7. **A/A calibration:** 1,000 A/A simulations where treatment is assigned randomly within the null. The false positive rate is 0.042 (below the nominal 0.05), confirming the testing procedure is not inflated.

8. **A/B power recovery:** 1,000 simulations with an injected 0.05 effect. Empirical power is 0.78 (near target 0.80). Sign recovery rate is 0.99, CI coverage is 0.94.

### Implementation
- Core modules: `srm.py` (chi-squared SRM), `estimators.py` (Welch t-test, Mann-Whitney U, Cohen's d/h), `bootstrap.py` (stratified user-level resampling), `guardrails.py` (non-inferiority tests), `multiplicity.py` (Benjamini-Hochberg and Holm corrections), `metrics.py` (metric definitions and practical significance thresholds), `decision.py` (rule-based SHIP/ITERATE/STOP logic).
- All random processes use a seeded NumPy Generator (seed 20260616) for reproducibility.
- The pipeline runs in 3.0 seconds total for 12,000 users and 5,000 bootstrap iterations.

### Tradeoffs
- The experiment is underpowered for its configured MDE of 0.015 (12,000 users vs 13,000 required for 80% power). This is a deliberate limitation of the generated data size, not the methodology.
- CUPED variance reduction is unavailable because the generated data does not include pre-assignment covariates. The CUPED module degrades gracefully and reports "unavailable" status.
- The segment analysis is exploratory (6 eligible segments, 1 significant interaction) with a disclaimer against overinterpretation.

### Verification
- The `experiment_analysis.json` includes all test statistics, p-values, and bootstrap diagnostics in a structured format.
- The `phase4_acceptance.json` machine-verifies the decision logic by checking that the SRM passed, primary effect is positive, guardrails passed threshold, and A/A calibration is below 0.05.
- `randomization_balance.json` provides SMD values for each pre-treatment variable.
- `power_analysis.json` documents the power calculations and current detectable effect size.
- `data_validation.json` confirms the analysis grain, population counts, and ITT trigger status.

---

## 6. Root Cause Decomposition

### Problem
When a metric declines, the question is not just "did it decline?" but "why?" A good analyst decomposes the change into effects driven by rate changes vs compositional mix shifts, and attributes contributions to specific segments.

### Design
Symmetric Kitagawa decomposition separates the overall change in a ratio metric (export rate) into:
- **Rate effects:** changes in each segment's export rate, weighted by average composition
- **Mix effects:** changes in each segment's share of total volume, weighted by average rate

The decomposition is mathematically exact: sum(rate_effect) + sum(mix_effect) = overall_change.

### Implementation
- `src/fxfill_analytics/analytics/root_cause.py` implements the symmetric Kitagawa formula:
  - `rate_effect(s) = 0.5 * (current_share(s) + previous_share(s)) * (current_rate(s) - previous_rate(s))`
  - `mix_effect(s) = 0.5 * (current_rate(s) + previous_rate(s)) * (current_share(s) - previous_share(s))`
- The same calculation is independently implemented in `test_root_cause_decomposition.py` for verification.
- Five diagnostic dimensions are analyzed: device_type, app_version, document_complexity, user_segment, agent_error_type.
- Findings are labeled as `observed_facts`, `analytical_inferences`, or `hypotheses_requiring_validation` to clearly separate measurement from interpretation.

### Verification
- The decomposition is numerically exact: residual = overall_change - sum(all_contributions) = -1.04e-17, well within the 1e-10 tolerance.
- The `test_root_cause_decomposition.py` test independently re-implements the calculation and asserts exact reconciliation.
- The `phase3_root_cause.json` report stores the full decomposition with all 5 segment-level contributions.
- The root cause dashboard page (Root Cause Analysis, 6 charts) displays the decomposition visually with drill-down by dimension.

---

## 7. Machine-Verifiable Acceptance

### Problem
Hand-written reports cannot be automatically verified. A report that says "all tests pass" is a claim; a JSON file with pass/fail flags for every check is evidence. For a project that intends to demonstrate engineering rigor, acceptance must be machine-verifiable.

### Design
Every phase generates two file types:
1. **Human-readable Markdown** (for GitHub, README, portfolio review)
2. **Machine-verifiable JSON** (for automated gate checks)

The acceptance gate (`phase4_acceptance.json`) checks: all 15 required files exist, all 7 required figures exist, the A/A FPR is below 0.05, the A/B power is above 0.70, the SRM check passed, the randomization balance passed, and the decision is consistent with the evidence.

### Implementation
- `src/fxfill_analytics/experimentation/report.py` generates the evidence bundle and verifies file presence, pass/fail counts, and numerical guard conditions.
- The acceptance gate is structured so that adding a new check requires only adding a new entry to the `passed_gates` array; the verification loop is generic.
- No report is accepted by simply reading its text content -- every pass/fail assertion corresponds to a numerical condition evaluated at runtime.

### Tradeoffs
- This adds ~15-20% to the report generation time (for JSON serialization and file verification) but the absolute cost is <0.1 seconds.
- The canonical list of required files is explicit and must be updated when new analysis outputs are added.

### Verification
- The acceptance gate itself is testable: running `phase4_acceptance.json` with a known-bad output file causes the gate to fail.
- The project's CI-equivalent verification is: `pytest tests/ && python scripts/generate_reports.py` -- if either fails, the acceptance gate produces a `passed: false` result.
- Git tags (phase-1-complete through phase-4-complete) mark transition points where the acceptance gate was green.

---

**Project:** FxFill Analytics -- `F:/RAG/fxfill-analytics-observability/`
**Latest commit:** e236578
**All data is synthetic.** No real user data, financial records, or production information is included.
