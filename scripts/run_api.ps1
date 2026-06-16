# FxFill Analytics — Launch FastAPI Server
# Usage: .\scripts\run_api.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Starting FxFill Analytics API..." -ForegroundColor Cyan
Write-Host "Swagger UI: http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

uvicorn src.fxfill_analytics.api.main:app --host 127.0.0.1 --port 8000 --reload --app-dir "$ProjectRoot"
