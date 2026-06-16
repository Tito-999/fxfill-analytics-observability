# FxFill Analytics — Launch Streamlit Dashboard
# Usage: .\scripts\run_dashboard.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Starting FxFill Analytics Dashboard..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray
Write-Host ""

streamlit run "$ProjectRoot\dashboard\Home.py" --server.port 8501
