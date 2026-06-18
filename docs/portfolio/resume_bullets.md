# Resume Bullets -- FxFill Analytics Portfolio

---

## Data Analyst Version

1. Built an end-to-end analytics platform on synthetic data, generating 1M+ records across 7 source tables with 10 intentionally embedded anomalies, then detecting and explaining each via SQL analysis and statistical validation.

2. Designed an 8-page Streamlit dashboard with 30 charts, 10 tables, and 18 interactive filters to enable self-service exploration of conversion funnels, retention cohorts, feature adoption trends, and AI Agent performance metrics.

3. Conducted a full A/B experiment analysis on 12,000 users using bootstrap CIs (5,000 iterations), SRM checks, guardrail non-inferiority tests, and Benjamini-Hochberg multiplicity correction, resulting in a machine-verified SHIP decision.

---

## Analytics Engineer Version

1. Architected a 4-layer dimensional warehouse (7 raw, 7 staging, 13 intermediate, 21 mart models) using dbt-core on DuckDB, with 44 dbt tests (21 generic, 23 singular) and cross-layer phenomena reconciliation verified to within 1e-10 tolerance.

2. Engineered a deterministic synthetic data pipeline using `SeedSequence.spawn(9)` for independent per-module RNG streams and SHA-256 canonical hashing, achieving 22.3x speedup and byte-identical reproducibility across independent runs.

3. Implemented a comprehensive statistical experimentation module in Python supporting user-level ITT analysis, stratified bootstrap resampling, SRM diagnostics, SMD-based randomization balance, guardrail assessment, and machine-verifiable JSON audit output.

---

## AI/LLM Evaluation Version

1. Simulated an 8-stage LLM Agent pipeline (classification, OCR, PII detection, anonymization, risk detection, field mapping, autofill, validation) with configurable latency distributions, error rates, and cost multipliers across 5 model versions.

2. Built agent observability infrastructure tracking run/span hierarchy, latency percentiles, token/cost accounting, and error Pareto analysis, enabling model version cost-quality tradeoff comparison across 300K+ agent spans.

3. Implemented an A/B experiment module evaluating an LLM prompt change on 12,000 simulated users, with machine-verified acceptance gates (A/A FPR=0.042, A/B power=0.78, guardrail non-inferiority testing) demonstrating rigorous evaluation methodology.

---

*Note on claims: All data is synthetic. There are no real users, no real revenue, no real financial transactions, and no RAG (Retrieval-Augmented Generation) pipeline in this project. The AI Agent is a simulated pipeline with configurable parameters; no real LLM API was called.*
