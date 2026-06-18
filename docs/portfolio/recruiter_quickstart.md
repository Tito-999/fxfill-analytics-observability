# FxFill Analytics -- Recruiter Quickstart

**One-line pitch:** A laptop-runnable analytics platform that demonstrates end-to-end product analytics and AI Agent observability across synthetic data generation, dimensional warehousing, statistical experimentation, and root cause decomposition -- all running on DuckDB, dbt, Streamlit, and Python.

---

## What This Project Solves

Most analytics portfolios show isolated skills: a dashboard here, a SQL query there, a single A/B test in a notebook. FxFill is different -- it simulates an entire product analytics function for a cross-border remittance AI Agent product called FxFill. The project covers the full stack:

- Synthetic data generation with 10 intentionally embedded anomalies (P01-P10) that an analyst must detect and explain
- A 4-layer dimensional warehouse (raw, staging, intermediate, marts) built with dbt-core on DuckDB
- 8-page Streamlit dashboard with 30 charts, 10 tables, 18 interactive filters, and 7 export types
- 20 SQL interview queries with business documentation
- A full A/B experiment pipeline with SRM checks, bootstrap confidence intervals, guardrail assessment, multiplicity correction, and a machine-verified ship decision
- Statistical root cause decomposition using Kitagawa rate/mix effects
- AI Agent observability with run/span hierarchy, latency percentiles, cost analysis, and error Pareto
- A machine-verifiable acceptance framework that treats hand-written reports as insufficient

---

## What I Personally Built

Every file in this repository was written by me as a single developer portfolio project. This includes:

- **7 synthetic data generators** producing 20,000 users, 80,000 documents, 60,000 sessions, 491,000 product events, 80,000 agent runs, 300,000 agent spans, and 12,360 experiment assignments
- **41 dbt models** across staging (7), intermediate (13), and mart (21) layers
- **20 SQL interview queries** covering DAU/WAU/MAU, conversion funnels by device and channel, cohort retention, feature adoption, lifecycle segmentation, agent latency percentiles, token/cost trends, model comparisons, error Pareto, and experiment inputs
- **8 Streamlit dashboard pages** with reusable component architecture
- **Full statistical experimentation module** covering SRM testing, bootstrap CIs, Cohen's d, Benjamini-Hochberg correction, guardrail non-inferiority, CUPED, power analysis, and A/A calibration
- **Root cause decomposition** implementing Kitagawa's symmetric decomposition with exact numerical reconciliation (residual < 1e-10)
- **Machine-verifiable acceptance framework** with structured JSON audit evidence
- **Automated pytest verification suite** — the immutable `portfolio-v1.2.12` release baseline records 406 / 406 pytest passed
- **One-click PowerShell scripts** for setup, data generation, warehouse build, dashboard launch, and testing

---

## Architecture in One Image

```
Synthetic Generators --> Raw Parquet/CSV --> DuckDB Raw Layer
                                              |
                                         dbt Staging (7 models)
                                              |
                                       dbt Intermediate (13 models)
                                              |
                                        dbt Analytics Marts (21)
                                              |
             +----------------+---------------+----------------+
             |                |               |                |
       Streamlit BI     A/B Test        Root Cause      Automated
       Dashboard       Module          Analysis         Weekly Report
       (8 pages)       (SHIP/stop)     (Kitagawa        (JSON audit
       30 charts       5000 bootstrap  decomposition    evidence)
       18 filters      iterations      residual <1e-10)
```

Data flows left to right: random seed -> synthetic data -> DuckDB -> dbt transforms -> analytics outputs. Every layer is traceable back to the original seed. Every mart is reconciled against source phenomena values.

---

## Three Strongest Technical Decisions

### 1. Deterministic data via SeedSequence isolation
Cross-module RNG coupling was the root cause of non-reproducible data. Fix: `SeedSequence.spawn(9)` creates independent RNG streams for each generator module, and `hashlib.md5` replaces Python's randomized `hash()` for stable bucketing. Result: identical data on every run from the same seed, enabling verifiable acceptance testing.

### 2. Kitagawa decomposition with exact reconciliation
Rather than a hand-wavy "mobile users declined" explanation, the root cause module computes symmetric rate and mix effects for every dimension segment. The sum of all contributions exactly equals the observed overall change (residual -1.04e-17, well within 1e-10 tolerance). This is the difference between an opinion and an audit.

### 3. Machine-verifiable acceptance framework
Every phase generates structured JSON audit files (phenomena evidence, model inventories, reconciliation checks, experiment decisions) alongside human-readable Markdown. The acceptance gate script checks these programmatically, not by reading a report. This catches pipeline regressions automatically and means the project can prove its claims without human review.

---

## Dashboard Page Map

| Page | Charts | Tables | Filters | Key Insight |
|------|--------|--------|---------|-------------|
| Executive Overview | 4 | 2 | 4 | Daily KPIs, scorecard |
| Funnel & Retention | 2 | 1 | 4 | Upload->Export drop-off, D1/D7/D30 |
| Feature Adoption | 3 | 1 | 3 | OCR, anonymization, autofill trends |
| Agent Observability | 7 | 2 | 2 | Trace timelines, latency %iles, costs |
| A/B Test | 4 | 1 | 2 | 0.03 absolute effect, SHIP |
| Root Cause Analysis | 6 | 1 | 2 | Mobile/OCR drivers identified |
| Data Quality | 4 | 2 | 1 | P01-P10 status, reconciliation |
| **Total** | **30** | **10** | **18** | |

Each page offers CSV export, and the entire dashboard reads from a read-only DuckDB connection.

---

## Root-Cause Finding

The export rate declined from 0.603 to 0.591 (-1.14 percentage points). The Kitagawa decomposition traced this to two factors:

- **Rate effect (97.8% of change):** the organic channel's export rate dropped from 0.622 to 0.574, contributing -0.016 of the -0.0114 overall change
- **Mix effect (1.8%):** compositional shifts across channels were minor

The primary analytical inference: mobile users on the organic channel experienced a rate degradation consistent with a UX regression. This was cross-referenced against agent error rates by device type and validated via the reconciliation check.

All findings are from synthetic data and are not real business conclusions.

---

## A/B Experiment Finding

The experiment `validation_before_autofill_v1` tested whether adding a validation step before autofill improved the form export rate.

- **Population:** 12,000 clean ITT users (6,020 A / 5,980 B)
- **Primary metric:** form_export_rate: A=0.58, B=0.61, absolute effect=+0.03 (p=0.02, bootstrap 95% CI [0.006, 0.054])
- **SRM check:** clean ITT groups balanced (chi2=0.133, p=0.715); raw assignments also balanced (chi2=0.0, p=1.0)
- **Guardrails:** 3 of 4 passed; cost non-inferiority failed (cost per task increased $0.015 vs $0.005 margin)
- **A/A calibration:** 1,000 simulations, false positive rate 0.042 (below 0.05 threshold)
- **A/B power recovery:** 1,000 simulations, empirical power 0.78 (near target 0.80)
- **Multiplicity:** BH-adjusted secondary metrics remained significant after correction
- **Randomization balance:** max SMD = 0.04, no material imbalances
- **Decision:** SHIP, with weekly cost monitoring

---

## How to Run Locally

```powershell
git clone <repo-url>
cd fxfill-analytics-observability
.\scripts\setup.ps1
.\.venv\Scripts\Activate.ps1
python scripts/generate_data.py --size medium --seed 20260616
python scripts/build_warehouse.py
python -m pytest -q
.\scripts\run_dashboard.ps1
# Open http://localhost:8501
```

Hardware requirements: any laptop with Python 3.11, 8-16 GB RAM, ~500 MB disk. No GPU, no cloud services, no Docker needed.

---

## Where to Inspect Tests and Audits

| What | Where |
|------|-------|
| Python tests (pytest) | `tests/` — automated verification suite; `portfolio-v1.2.12` baseline: 406 / 406 passed |
| dbt models | `dbt_fxfill/models/` -- 41 SQL models in staging/intermediate/marts layers |
| SQL queries | `sql/interview_queries/` -- 20 documented business queries |
| Phase audit evidence | `reports/` -- JSON + Markdown for phases 1-4 |
| Acceptance verification | `reports/portfolio/releases/portfolio-v1.2.12/core_release_acceptance.json` — machine-verified gate results |
| Dashboard pages | `dashboard/pages/` -- 7 business pages + Home |

---

## Limitations

- All data is synthetic -- no real users, no real transactions, no real financial information
- The "AI Agent" is a simulated pipeline of LLM stages; no real LLM API is called
- Model pricing is simulated with fixed cost coefficients, not real provider pricing
- The Streamlit dashboard captures screenshots manually (placeholder labels, not live captures)
- CUPED variance reduction is unavailable (no pre-assignment covariates in the data model)
- The experiment is underpowered for its configured MDE (12,000 users vs 13,000 required for 0.015 effect at 80% power)
- No CI/CD pipeline, no production deployment -- this is a local development project

---

## Data Disclaimer

**All data in this repository is synthetically generated** for demonstration purposes. No real user data, financial records, or production information is included. The A/B experiment findings, root cause analysis, and all business recommendations are based entirely on fabricated data with pre-configured embedded phenomena. The project is a portfolio piece demonstrating analytics methodology, not a real business intelligence system.
