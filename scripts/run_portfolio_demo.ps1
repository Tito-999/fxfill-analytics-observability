# FxFill Analytics — Interactive Dashboard Launcher
# Prerequisite: conda activate fxfill_analytics; .\scripts\setup_portfolio.ps1
param([int]$Port = 8501)
$ErrorActionPreference = "Stop"

# Environment
$env:PYTHONNOUSERSITE = "1"
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

# Python check
$pv = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0 -or $pv -ne "3.11") {
    Write-Host "ERROR: Python 3.11 required. Run: conda activate fxfill_analytics" -ForegroundColor Red
    exit 1
}

# Import checks
python -c "import streamlit,duckdb" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: streamlit/duckdb not found." -ForegroundColor Red; exit 1 }

# File checks
if (-not (Test-Path "dashboard/Home.py")) { Write-Host "ERROR: dashboard/Home.py not found." -ForegroundColor Red; exit 1 }
$db = "warehouse/fxfill.duckdb"
if (-not (Test-Path $db)) {
    Write-Host "ERROR: Database not found at $db" -ForegroundColor Red
    Write-Host "Run: .\scripts\setup_portfolio.ps1 -Profile demo" -ForegroundColor Yellow
    exit 1
}
$env:FXFILL_DUCKDB_PATH = (Resolve-Path $db).Path

# Port check (compatible with older PowerShell)
$portInUse = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient("127.0.0.1", $Port)
    $tcp.Close()
    $portInUse = $true
} catch {}
if ($portInUse) {
    Write-Host "ERROR: Port $Port is already in use." -ForegroundColor Red
    Write-Host "Try: .\scripts\run_portfolio_demo.ps1 -Port $($Port+1)" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== FxFill Analytics Dashboard ===" -ForegroundColor Cyan
Write-Host "URL: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "DB:  $env:FXFILL_DUCKDB_PATH"
Write-Host "ALL DATA IS SYNTHETIC. Press Ctrl+C to stop." -ForegroundColor Gray
python -m streamlit run dashboard/Home.py --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false
python -m streamlit run dashboard/Home.py --server.address 127.0.0.1 --server.port $Port --server.headless true --browser.gatherUsageStats false
