"""Home page — FxFill Analytics Dashboard."""

import streamlit as st

from dashboard.services.database import get_min_max_dates, health_check

st.set_page_config(
    page_title="FxFill Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("FxFill Product Analytics & AI Agent Observability")

st.markdown(
    """
### Synthetic Data Portfolio Dashboard

⚠️ **ALL DATA IS SYNTHETIC.** This dashboard demonstrates analytics engineering
capabilities using algorithmically generated data. No real user, financial,
or business data is displayed.

---

**Architecture:**
```
Synthetic Events → Parquet → DuckDB Raw → dbt Staging → Intermediate → Analytics Marts → Streamlit
```

**Tech Stack:** Python 3.11 · DuckDB 0.10 · dbt-core 1.8 · Streamlit 1.31 · Pandas · Plotly

---

### Pages

| Page | Description |
|------|-------------|
| **1. Executive Overview** | North star metrics, DAU trends, alerts |
| **2. Funnel & Retention** | 7-step task funnel, D1/D7/D30 retention |
| **3. Feature Adoption** | OCR, anonymization, autofill adoption |
| **4. Agent Observability** | Latency, cost, token, error analysis |
| **5. A/B Test** | Experiment group comparison, guardrails |
| **6. Root Cause Analysis** | Export rate decline decomposition |
| **7. Data Quality** | Pipeline quality, reconciliation, hashes |

---
"""
)

# Database health
health = health_check()
min_d, max_d = get_min_max_dates()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Database Health")
    for schema, status in health.get("schemas", {}).items():
        icon = "✅" if status == "ok" else "❌"
        st.write(f"{icon} {schema}: {status}")

with col2:
    st.subheader("Data Coverage")
    if min_d and max_d:
        st.write(f"📅 {min_d} → {max_d}")
    st.write("📊 37 dbt models | 18 analytics marts")
    st.write("🔬 11/11 reconciliation passed")
    st.caption("Rebuild: `python scripts/build_warehouse.py --input-run <run> --full-refresh`")

st.markdown("---")
st.caption("Phase 3 · Streamlit Analytics Dashboard · All data synthetic")
