# ADR-004: Dashboard Coverage Contract

**Date:** 2026-06-17
**Status:** Accepted

## Context

Streamlit page files contain declarative UI calls (st.title, st.metric, st.plotly_chart)
that execute at module level and cannot be unit-tested without a running Streamlit server.
Simple statement coverage of dashboard/ yields ~4% because these entry-point lines
dominate the statement count.

A single "combined coverage >= 85%" threshold is not meaningful for Streamlit pages.

## Decision: Three-Gate Contract

### Gate A: Reusable Analytics Code (≥85%)

Scope:
- `src/fxfill_analytics/`
- `dashboard/services/`
- `dashboard/components/`
- `dashboard/analytics/` (if created)
- Dashboard config loaders, export helpers, root-cause helpers, filter/metric helpers

Threshold: statement coverage >= 85%
Measured by: `pytest --cov=fxfill_analytics --cov=dashboard/services --cov=dashboard/components`

### Gate B: Page Execution (8/8 pages)

Each page must have an execution test that verifies:
- Page import does not raise exception
- Page title exists
- Synthetic data notice is present
- Main data-loading function executes
- At least one key metric/chart/table renders
- Default filters execute
- Empty-result state does not crash
- Database error state renders safely

Threshold: 8/8 pages passed

### Gate C: Transparency

The following are always reported:
- `fxfill_analytics` coverage
- Dashboard reusable-module coverage
- Streamlit page-entry coverage
- Repository combined coverage

Combined 55.7% is not hidden, but not used as a single pass/fail gate.

## Consequences

- Page files keep lightweight entry points
- Business logic lives in testable modules
- Combined coverage reported transparently
- No blanket `omit` or `pragma: no cover` on business logic
