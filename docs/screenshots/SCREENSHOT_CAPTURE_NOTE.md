# Screenshots — Manual Capture Required

No headless browser (Playwright/Chromium) is available in this environment.

To capture all 8 screenshots:
1. Start the warehouse: `python scripts/build_warehouse.py --input-run data/generated/<run> --full-refresh && dbt run --project-dir dbt_fxfill`
2. Start the dashboard: `powershell ./scripts/run_dashboard.ps1`
3. Open http://localhost:8501
4. Navigate to each page and capture screenshots at minimum 1200px width
5. Save to this directory with the expected filenames

Expected files:
- home.png
- executive_overview.png
- funnel_retention.png
- feature_adoption.png
- agent_observability.png
- ab_test.png
- root_cause.png
- data_quality.png

capture_method = manual
