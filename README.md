# FxFill Analytics & AI Agent Observability Platform

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.2-yellow.svg)](https://duckdb.org/)
[![dbt](https://img.shields.io/badge/dbt-core-1.9-orange.svg)](https://docs.getdbt.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red.svg)](https://streamlit.io/)
[![226 Tests](https://img.shields.io/badge/Tests-226%20%2F%20226%20passed-brightgreen.svg)](https://github.com/Tito-999/fxfill-analytics-observability)
[![Synthetic Data](https://img.shields.io/badge/Data-Synthetic-lightgrey.svg)](https://github.com/Tito-999/fxfill-analytics-observability)

---

## Overview

An end-to-end analytics engineering platform for AI agent products, demonstrating the full analytics pipeline from synthetic data generation through dimensional modeling, business intelligence dashboards, and experiment-driven decision-making. The platform models a simulated AI Agent product (FxFill) that assists users with cross-border remittance form filling, and provides complete observability into user behavior, agent performance, cost economics, and A/B experiments. **ALL DATA IS SYNTHETIC** -- this is a portfolio project, not a production system.

---

## Quick Start

```powershell
git clone https://github.com/Tito-999/fxfill-analytics-observability.git
cd fxfill-analytics-observability
conda create -n fxfill_analytics python=3.11 -y
conda activate fxfill_analytics
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
$env:PYTHONNOUSERSITE = "1"
$env:NO_PROXY = "127.0.0.1,localhost"
python scripts\verify_core_release.py
```

Expected output: `CORE RELEASE ACCEPTANCE PASSED`, 226/226 tests passed, health 200.

---

## Architecture

![Architecture Diagram](docs/portfolio/architecture.png)

The data pipeline flows through these stages:

**Synthetic Data** &rarr; **Parquet** &rarr; **DuckDB Raw** &rarr; **dbt Staging** &rarr; **dbt Intermediate** &rarr; **dbt Analytics Marts** &rarr; **Streamlit Dashboard** &rarr; **Experiment Analysis**

- **Synthetic Data Generators** produce raw event traces, agent spans, and user profiles
- **DuckDB** serves as the local OLAP engine (no cloud infrastructure required)
- **dbt** models transform data through staging, intermediate, and mart layers
- **Streamlit** renders 8 pages of interactive BI dashboards with 30 charts
- **Experiment Analysis** module performs A/B testing and root cause decomposition

---

## Dashboard Pages

![Dashboard Contact Sheet](docs/portfolio/dashboard_contact_sheet.png)

| Page | Description |
|------|-------------|
| **Home** | Platform overview, key metrics, and navigation |
| **Executive Overview** | Daily scorecard, weekly business review, high-level KPIs |
| **Conversion Funnel** | User journey through registration, upload, autofill, and export |
| **Retention & Cohorts** | Weekly retention cohorts and user lifecycle analysis |
| **Feature Adoption** | Feature-level usage trends and adoption rates |
| **Agent Observability** | Agent run traces, token usage, cost, error rates, and latency |
| **A/B Test Analysis** | Experiment results with bootstrap confidence intervals and segment effects |
| **Root Cause Analysis** | Export rate decomposition with Kitagawa method |

### Individual Screenshots

| Page | Preview |
|------|---------|
| Executive Overview | ![Executive Overview](docs/portfolio/screenshots/executive_overview.png) |
| Agent Observability | ![Agent Observability](docs/portfolio/screenshots/agent_observability.png) |
| A/B Test | ![A/B Test](docs/portfolio/screenshots/ab_test.png) |
| Root Cause Analysis | ![Root Cause Analysis](docs/portfolio/screenshots/root_cause_analysis.png) |

---

## Project Scale

| Metric | Count |
|--------|-------|
| Source Tables | 7 |
| dbt Models (Total) | 37 |
| -- Staging | 7 |
| -- Intermediate | 12 |
| -- Marts | 18 |
| Warehouse Objects | 44 |
| SQL Analysis Queries | 20 |
| Streamlit Pages | 8 (1 Home + 7 Business) |
| Charts | 30 |
| Bootstrap Iterations | 5,000 |
| Tests (pytest) | 226 / 226 passed (0 failed, 0 skipped) |
| dbt Tests | 31 / 31 passed |
| Experiment Decision (Phase 4) | SHIP |

---

## Analytics Case Studies

### Root Cause: Export Rate Decomposition

Investigated a simulated decline in the form export rate by decomposing the overall change into rate effects and mix effects using the Kitagawa decomposition method. The analysis isolated which user segments drove the decline and whether the root cause was behavioral (lower conversion within segments) or compositional (shift toward lower-converting segments). The decomposition achieved a residual error of less than 1e-9, confirming internal consistency.

### A/B Test: validation_before_autofill_v1

Evaluated an experiment that introduced a validation step before form autofill. The analysis pipeline applied:

- Sample ratio mismatch (SRM) checks at the overall and segment levels
- Bootstrap resampling with 5,000 iterations for robust confidence intervals
- Segment-level effect analysis across user cohorts

The Phase 4 experiment decision was **SHIP**, indicating the feature demonstrated a statistically significant improvement with positive effect size.

---

## Engineering Quality

- **pytest**: 226 / 226 tests passed (0 failed, 0 skipped)
- **dbt**: 37 / 37 models built successfully, 31 / 31 tests passed
- **Code quality**: ruff linting, black formatting, mypy type checking
- **Streamlit health endpoint**: returns HTTP 200
- **Streamlit home page**: returns HTTP 200
- **Acceptance**: machine-verifiable core release script (`verify_core_release.py`)
- **Audit**: public repository, clean CI status

---

## Architecture Diagrams

Three architecture diagrams are available in `docs/portfolio/`:

1. **architecture.png** -- End-to-end pipeline from data generation to dashboard and experiment analysis
2. **data_flow.png** -- Data model layer details and transformation dependencies
3. **experiment_flow.png** -- A/B test pipeline from hypothesis to decision

---

## Repository Structure

```
fxfill-analytics-observability/
├── data/                    # Generated synthetic data (Parquet/CSV)
├── dbt/                     # dbt models and configurations
│   ├── models/
│   │   ├── staging/         # 7 staging models
│   │   ├── intermediate/    # 12 intermediate models
│   │   └── marts/           # 18 analytics marts
│   └── tests/               # dbt data tests
├── docs/
│   └── portfolio/           # Architecture diagrams and screenshots
├── scripts/                 # Pipeline automation and verification scripts
├── sql/                     # 20 SQL analysis queries
├── streamlit_app/           # 8-page Streamlit dashboard
├── tests/                   # pytest test suite (226 tests)
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## Limitations

- **Synthetic data only** -- all behavioral and operational data is programmatically generated
- **Not a real banking or production system** -- this is a portfolio project demonstrating analytics engineering capabilities
- **No real customer PII** -- all user identities are synthetic
- **No cloud deployment** -- runs locally on DuckDB; no streaming ingestion
- **Business impact values are scenario assumptions** -- financial figures are illustrative, not real

---

## Tags

`phase-0-complete` `phase-1-complete` `phase-2-complete` `phase-3-complete` `phase-4-complete` `portfolio-v1` `portfolio-v1.1`

---

## Author

Designed and built by [Your Name].

Development workflow included automated verification.
---

## License

MIT License -- see [LICENSE](./LICENSE).
