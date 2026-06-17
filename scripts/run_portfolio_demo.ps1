# FxFill Analytics — Portfolio Demo Launcher
param([int]$Port = 8501, [string]$Profile = "demo")
$ErrorActionPreference = "Stop"
Write-Host "=== FxFill Portfolio Demo ===" -ForegroundColor Cyan

$env_name = "fxfill_analytics"
$db = "warehouse/fxfill.duckdb"

if (-not (Test-Path $db)) {
    Write-Host "Database not found. Running setup first..." -ForegroundColor Yellow
    & "$PSScriptRoot\setup_portfolio.ps1" -Profile $Profile
}

$env:FXFILL_DUCKDB_PATH = (Resolve-Path $db).Path
$env:NO_PROXY = "127.0.0.1,localhost"
$env:PYTHONNOUSERSITE = "1"

Write-Host "Starting Streamlit on http://localhost:$Port" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
conda run -n $env_name python -m streamlit run dashboard/Home.py --server.port $Port --server.headless true --browser.gatherUsageStats false
