# FxFill Analytics -- Project Summary

FxFill is a comprehensive, laptop-runnable product analytics and AI Agent observability platform built as a portfolio project. It simulates the full analytics stack for a cross-border remittance AI Agent product, covering synthetic data generation, dimensional warehousing, BI dashboards, statistical experimentation, and root cause analysis.

**Data Generation:** Seven synthetic data generators produce 20,000 users, 80,000 documents, 60,000 sessions, 491,000 product events, 80,000 agent runs, 300,000 agent spans, and 12,360 experiment assignments in 29 seconds. Data is byte-identical across runs via SeedSequence RNG isolation and deterministic hashing. Ten configurable phenomena (P01-P10) embed latency regressions, mobile UX bugs, duplicate uploads, experiment contamination, and other realistic anomalies.

**Warehouse:** A 4-layer DuckDB warehouse with 7 raw tables, 7 staging views, 12 intermediate views, and 18 analytics marts, all built through dbt-core with 30+ automated schema tests. Cross-layer phenomena reconciliation confirms Python-derived metrics match dbt SQL values within tolerance.

**Dashboard:** An 8-page Streamlit dashboard featuring 30 charts, 10 tables, 18 interactive filters, and 7 export types across Executive Overview, Funnel & Retention, Feature Adoption, Agent Observability, A/B Test, Root Cause Analysis, and Data Quality pages.

**Experimentation:** A comprehensive A/B test pipeline with user-level ITT analysis, SRM testing, bootstrap confidence intervals (5,000 iterations), guardrail non-inferiority assessment, Benjamini-Hochberg multiplicity correction, A/A calibration (FPR=0.042), and power analysis (empirical power=0.78). The experiment produced a machine-verified SHIP decision.

**Quality Assurance:** 226+ pytest tests across 34 files, 87.89% code coverage, 20 documented SQL interview queries, and machine-verifiable JSON audit evidence for every phase. All data is synthetic. No real users, revenue, or production data is included.
