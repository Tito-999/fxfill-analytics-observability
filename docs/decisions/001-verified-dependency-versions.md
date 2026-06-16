# ADR-001: Verified Dependency Versions (Phase 0.5)

**Date:** 2026-06-16
**Status:** Accepted

## Context

Phase 0.5 environment gate requires all core dependencies to be installed,
import-verified, and version-locked in a dedicated conda environment.

## Verified Versions

| Package | Verified Version | Notes |
|---|---|---|
| Python | 3.11.15 | conda-forge, dedicated env `fxfill_analytics` |
| DuckDB | 0.10.2 | |
| dbt-core | 1.8.8 | |
| dbt-duckdb | 1.8.1 | |
| Pandas | 2.2.3 | |
| NumPy | 1.26.4 | |
| Pandera | 0.19.3 | |
| Streamlit | 1.31.1 | pins `packaging<24` |
| FastAPI | 0.110.3 | |
| SciPy | 1.12.0 | |
| Statsmodels | 0.14.6 | |
| PyArrow | 15.0.2 | |
| PyYAML | 6.0.3 | |
| Plotly | 5.18.0 | |
| Pydantic | 2.6.4 | |
| Uvicorn | 0.27.1 | |
| Click | 8.1.8 | |
| tqdm | 4.66.6 | |
| python-dotenv | 1.0.1 | |

## Dev Dependencies

| Package | Verified Version |
|---|---|
| pytest | 8.0.2 |
| pytest-cov | 5.0.0 |
| ruff | 0.3.7 |
| black | 24.1.1 |
| mypy | 1.8.0 |
| coverage | 7.14.1 |

## Known Constraints

- **Streamlit 1.31.1** requires `packaging<24`, which conflicts with newer
  wheel versions that want `packaging>=24`. Resolved by pinning
  `packaging==23.2` and `wheel==0.45.1`.
- **dbt-core 1.8.8** requires `packaging>20.9` (compatible).
- The conda environment has `PYTHONNOUSERSITE=1` to isolate from
  user site-packages at `C:\Users\PCR\AppData\Roaming\Python\Python311`.

## Environment

- **Name:** `fxfill_analytics`
- **Python:** `C:\Users\PCR\.conda\envs\fxfill_analytics\python.exe`
- **pip:** 26.1.2
- **Platform:** Windows 11 (win-64)

## Lock File

Full locked versions are in `requirements-lock.txt`. The manually maintained
direct dependency file is `requirements.txt`.
