# FxFill Analytics — Launch Streamlit Dashboard
param([int]$Port = 8501)
$ErrorActionPreference = "Stop"

Write-Host "=== FxFill Analytics Dashboard ===" -ForegroundColor Cyan
$env_name = "fxfill_analytics"
$conda_envs = conda env list 2>&1
if ($conda_envs -notmatch $env_name) {
    Write-Host "ERROR: conda env '$env_name' not found." -ForegroundColor Red
    Write-Host "Run: conda create -n fxfill_analytics python=3.11 -y" -ForegroundColor Yellow
    exit 1
}
$db_path = "warehouse/fxfill.duckdb"
if (-not (Test-Path $db_path)) {
    Write-Host "WARNING: Database not found at $db_path" -ForegroundColor Yellow
    Write-Host "Rebuild: python scripts/build_warehouse.py --input-run data/generated/<run> --full-refresh; dbt run --project-dir dbt_fxfill" -ForegroundColor Yellow
    exit 1
}
$env:FXFILL_DUCKDB_PATH = (Resolve-Path $db_path).Path
Write-Host "Database: $env:FXFILL_DUCKDB_PATH" -ForegroundColor Green
Write-Host "Starting Streamlit on http://localhost:$Port" -ForegroundColor Cyan
C:\Users\PCR\.conda\envs\fxfill_analytics\python.exe -m streamlit run dashboard/Home.py --server.port $Port
