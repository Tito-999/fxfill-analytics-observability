# FxFill Analytics — Interactive Dashboard Launcher
# Prerequisite: conda activate fxfill_analytics; .\scripts\setup_portfolio.ps1
param([int]$Port = 8501)
$ErrorActionPreference = "Stop"

$db = "warehouse/fxfill.duckdb"
if (-not (Test-Path $db)) {
    Write-Host "Database not found. Run: .\scripts\setup_portfolio.ps1 -Profile demo" -ForegroundColor Yellow
    exit 1
}

$env:FXFILL_DUCKDB_PATH = (Resolve-Path $db).Path
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"
$env:PYTHONNOUSERSITE = "1"

Write-Host "=== FxFill Analytics Dashboard ===" -ForegroundColor Cyan
Write-Host "Open http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "All data is synthetic. Press Ctrl+C to stop." -ForegroundColor Gray
python -m streamlit run dashboard/Home.py --server.port $Port --server.headless true --browser.gatherUsageStats false
