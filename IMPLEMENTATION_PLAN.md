# Implementation Plan — FxFill Product Analytics & AI Agent Observability

**Generated:** 2026-06-16
**Based on:** `FxFill_Analytics_Engineering_Plan_for_Claude_Code.md`

---

## Overview

This document breaks down the FxFill Analytics engineering plan into executable phases and checklists. Each phase must pass its Definition of Done before the next phase begins.

## Phase Map

| Phase | Name | Status | Est. Effort |
|-------|------|--------|-------------|
| 0 | Project Scaffold | ⬜ Pending | Small |
| 1 | Synthetic Data Generation | ⬜ Pending | Large |
| 2 | DuckDB + dbt Data Warehouse | ⬜ Pending | Large |
| 3 | Product Analytics & SQL | ⬜ Pending | Large |
| 4 | Agent Observability | ⬜ Pending | Medium |
| 5 | A/B Test Module | ⬜ Pending | Medium |
| 6 | Root Cause Analysis | ⬜ Pending | Medium |
| 7 | API & Automated Reports | ⬜ Pending | Medium |
| 8 | Portfolio Polish | ⬜ Pending | Medium |

---

## Phase 0: Project Scaffold

### Checklist

- [ ] Create directory structure (40 directories)
- [ ] Create `pyproject.toml` with Python 3.11 target
- [ ] Create `requirements.txt` (core dependencies, no optional)
- [ ] Create `requirements-dev.txt` (dev/test/lint dependencies)
- [ ] Create `.env.example` with all configurable variables
- [ ] Create `.gitignore` (Python, DuckDB, env, data patterns)
- [ ] Create `README.md` (initial skeleton with synthetic-data warning)
- [ ] Create `config/app.yml`
- [ ] Create `config/metrics.yml` (metric definitions)
- [ ] Create `config/experiments.yml`
- [ ] Create `config/data_generation.yml`
- [ ] Create `config/logging.yml`
- [ ] Create `src/fxfill_analytics/__init__.py` and module init files
- [ ] Create `src/fxfill_analytics/settings.py`
- [ ] Create `scripts/setup.ps1`
- [ ] Create `scripts/run_all.ps1`
- [ ] Create `scripts/run_dashboard.ps1`
- [ ] Create `scripts/run_api.ps1`
- [ ] Create `scripts/run_tests.ps1`
- [ ] Create `scripts/generate_data.py` (placeholder)
- [ ] Create `scripts/build_warehouse.py` (placeholder)
- [ ] Create `scripts/generate_reports.py` (placeholder)
- [ ] Create `data/raw/.gitkeep`, `data/generated/.gitkeep`, `data/processed/.gitkeep`
- [ ] Create `warehouse/README.md`
- [ ] Create `PROGRESS.md`
- [ ] Implement smoke test: tiny data generation + validation
- [ ] Run smoke test → pass
- [ ] Initialize Git repository
- [ ] Create initial commit

### Phase 0 Definition of Done
- [x] Directory structure matches plan §6
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `python -c "import fxfill_analytics"` succeeds
- [ ] Smoke test passes with fixed seed 20260616
- [ ] Git repo initialized, no large files, no secrets

---

## Phase 1: Synthetic Data Generation

### Checklist

- [ ] Implement `src/fxfill_analytics/generation/distributions.py`
- [ ] Implement `src/fxfill_analytics/generation/generate_users.py`
- [ ] Implement `src/fxfill_analytics/generation/generate_sessions.py`
- [ ] Implement `src/fxfill_analytics/generation/generate_product_events.py`
- [ ] Implement `src/fxfill_analytics/generation/generate_agent_traces.py`
- [ ] Implement `src/fxfill_analytics/generation/generate_experiment_data.py`
- [ ] Implement `scripts/generate_data.py` CLI
- [ ] Implement Pandera schemas in `src/fxfill_analytics/quality/schemas.py`
- [ ] Implement quality checks in `src/fxfill_analytics/quality/checks.py`
- [ ] Implement quality report in `src/fxfill_analytics/quality/quality_report.py`
- [ ] Validation: same seed → same output
- [ ] Validation: medium data 400K events in <5 min
- [ ] Validation: all 10 embedded phenomena are detectable
- [ ] Validation: Pandera schemas pass on generated data
- [ ] Write `docs/data_dictionary.md`
- [ ] Write `docs/event_tracking_spec.md`

### Phase 1 Definition of Done
- [ ] `python scripts/generate_data.py --size medium --seed 20260616` succeeds
- [ ] Output files exist in `data/generated/`
- [ ] Quality report generates without critical failures
- [ ] Same seed yields identical data
- [ ] All data clearly labeled as synthetic

---

## Phase 2: DuckDB + dbt Data Warehouse

### Checklist

- [ ] Implement `src/fxfill_analytics/ingestion/database.py` (DuckDB connection)
- [ ] Implement `src/fxfill_analytics/ingestion/load_parquet.py`
- [ ] Implement `src/fxfill_analytics/ingestion/load_raw.py`
- [ ] Implement `scripts/build_warehouse.py` CLI
- [ ] Create `dbt_fxfill/dbt_project.yml`
- [ ] Create `dbt_fxfill/profiles.example.yml`
- [ ] Create staging models (7 models)
- [ ] Create intermediate models (9 models)
- [ ] Create mart models — product (6), agent (5), experiments (4), executive (3)
- [ ] Create dbt tests (uniqueness, referential integrity, not null)
- [ ] Create `dbt_fxfill/models/schema.yml` (documentation)
- [ ] Create `dbt_fxfill/macros/` utility macros
- [ ] Run `dbt deps`
- [ ] Run `dbt seed`
- [ ] Run `dbt run` → all succeed
- [ ] Run `dbt test` → all pass
- [ ] Generate `dbt docs`

### Phase 2 Definition of Done
- [ ] `dbt run` completes without errors
- [ ] `dbt test` passes 100%
- [ ] All 18 mart models populate correctly
- [ ] `dbt docs generate` succeeds
- [ ] DuckDB file < 2 GB with medium data

---

## Phase 3: Product Analytics & SQL

### Checklist

- [ ] Implement 20 SQL interview queries in `sql/interview_queries/`
- [ ] Implement `src/fxfill_analytics/analytics/kpis.py`
- [ ] Implement `src/fxfill_analytics/analytics/funnel.py`
- [ ] Implement `src/fxfill_analytics/analytics/retention.py`
- [ ] Implement `src/fxfill_analytics/analytics/segmentation.py`
- [ ] Implement `src/fxfill_analytics/utils/dates.py`
- [ ] Create Dashboard: `dashboard/Home.py`
- [ ] Create Dashboard: Executive Overview page
- [ ] Create Dashboard: Funnel & Retention page
- [ ] Create Dashboard: Feature Adoption page
- [ ] Create Dashboard: reusable components
- [ ] Validation: at least 3 embedded phenomena discovered
- [ ] Write product analysis findings report

### Phase 3 Definition of Done
- [ ] All 20 SQL queries produce correct results
- [ ] Dashboard shows funnel, retention, KPIs
- [ ] 3+ embedded phenomena discovered and documented
- [ ] Dashboard loads < 5 seconds (first screen)

---

## Phase 4: Agent Observability

### Checklist

- [ ] Implement `src/fxfill_analytics/observability/trace_models.py`
- [ ] Implement `src/fxfill_analytics/observability/local_tracer.py`
- [ ] Implement `src/fxfill_analytics/observability/cost_calculator.py`
- [ ] Implement `src/fxfill_analytics/observability/langfuse_exporter.py` (optional, guarded)
- [ ] Create Dashboard: Agent Observability page
- [ ] Validate: product events ↔ agent traces joinable via task_id
- [ ] Validate: slowest stage identifiable
- [ ] Validate: model/prompt version comparison works
- [ ] Validate: cost-quality tradeoff analysis works

### Phase 4 Definition of Done
- [ ] Agent dashboard shows trace timeline, latency, tokens, cost
- [ ] Single-trace drill-down works
- [ ] Model version comparison works
- [ ] Optional Langfuse exporter is gracefully disabled when not configured

---

## Phase 5: A/B Test Module

### Checklist

- [ ] Implement `src/fxfill_analytics/analytics/ab_testing.py` (full statistical pipeline)
- [ ] Sample size estimation
- [ ] SRM chi-squared test
- [ ] User-level deduplication
- [ ] Proportion difference test
- [ ] Welch's t-test
- [ ] Mann-Whitney U (robustness)
- [ ] Bootstrap confidence intervals
- [ ] Absolute & relative uplift
- [ ] Effect size (Cohen's h)
- [ ] Multiple comparison note
- [ ] Segment heterogeneity analysis
- [ ] Guardrail metrics assessment
- [ ] Business impact estimation
- [ ] Launch/iterate/stop recommendation
- [ ] Generate `reports/experiment_analysis.md`
- [ ] Create Dashboard: A/B Test page

### Phase 5 Definition of Done
- [ ] Full statistical pipeline produces results
- [ ] Experiment report generated
- [ ] Recommendation is evidence-based
- [ ] Dashboard shows all metrics with CIs

---

## Phase 6: Root Cause Analysis

### Checklist

- [ ] Implement `src/fxfill_analytics/analytics/root_cause.py`
- [ ] Implement `src/fxfill_analytics/analytics/anomaly_detection.py`
- [ ] Pre-compute: export rate decline case study
- [ ] Dimension decomposition (new/returning, device, channel, version, complexity, error)
- [ ] Contribution analysis per dimension
- [ ] Classify findings: fact / inference / hypothesis-to-verify
- [ ] Generate `reports/root_cause_case_study.md`
- [ ] Create Dashboard: Root Cause Analysis page

### Phase 6 Definition of Done
- [ ] Root cause analysis identifies app_version, OCR errors, mobile as main factors
- [ ] All conclusions traceable to SQL
- [ ] Actionable recommendations provided
- [ ] Dashboard page functional

---

## Phase 7: API & Automated Reports

### Checklist

- [ ] Implement `src/fxfill_analytics/api/main.py` (FastAPI app)
- [ ] Implement `src/fxfill_analytics/api/routes_events.py`
- [ ] Implement `src/fxfill_analytics/api/routes_traces.py`
- [ ] Implement `src/fxfill_analytics/api/routes_health.py`
- [ ] GET /health
- [ ] POST /events
- [ ] POST /events/batch
- [ ] POST /traces
- [ ] POST /spans/batch
- [ ] GET /metrics/summary
- [ ] GET /tasks/{task_id}/timeline
- [ ] Pydantic validation on all inputs
- [ ] 10+ API tests
- [ ] Implement `src/fxfill_analytics/reporting/weekly_report.py`
- [ ] Implement `src/fxfill_analytics/reporting/experiment_report.py`
- [ ] Generate `reports/weekly_business_review.md`

### Phase 7 Definition of Done
- [ ] Swagger UI accessible
- [ ] Invalid requests return clear errors
- [ ] API writes update dashboard metrics
- [ ] Weekly report auto-generates
- [ ] 10+ API tests pass

---

## Phase 8: Portfolio Polish

### Checklist

- [ ] Complete README with all 19 required sections
- [ ] Architecture diagram (Mermaid)
- [ ] Dashboard screenshots (7 pages)
- [ ] Demo GIF
- [ ] Data dictionary
- [ ] Metric dictionary
- [ ] A/B test case study write-up
- [ ] Root cause case study write-up
- [ ] Agent trace case study
- [ ] LICENSE file
- [ ] GitHub Actions CI workflow
- [ ] Link checker
- [ ] Final pytest run (all green, coverage ≥ 75%)
- [ ] Final Ruff/Black format check
- [ ] Final review pass

### Phase 8 Definition of Done
- [ ] New user can follow README and run in < 15 min
- [ ] Screenshots show all 7 dashboard pages
- [ ] All synthetic data prominently labeled
- [ ] No secrets, no real data, no oversized files
- [ ] CI passes on GitHub

---

## Constraints (all phases)

- [ ] No Kafka, Spark, Kubernetes, or heavy infrastructure
- [ ] Core MVP CPU-only (GPU optional, not required)
- [ ] No external LLM APIs required
- [ ] Core SQL not replaced by Pandas
- [ ] All data synthetic, clearly labeled
- [ ] All random processes use fixed seed
- [ ] No `.env`, API keys, or large binaries committed
- [ ] All files UTF-8 encoded
- [ ] Tests never skipped/deleted to pass

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| dbt-duckdb version incompatibility | Medium | High | Pin exact versions in requirements.txt |
| Windows path/encoding issues | Medium | Medium | Use pathlib, UTF-8 throughout |
| Memory pressure with 400K events | Low | Medium | Chunked generation, Parquet compression |
| Streamlit multipage on Windows | Low | Medium | Test early in Phase 3 |
| Conda not available | Medium | Low | Document pip-only fallback |
| DuckDB file locking on Windows | Low | Medium | Close connections properly, use read-only for dashboard |
