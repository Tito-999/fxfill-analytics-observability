# FxFill Analytics — Full Pipeline Run Script (Windows PowerShell)
# Usage: .\scripts\run_all.ps1 [-Size medium] [-Seed 20260616]
# Runs: generate → load → dbt → test → reports

param(
    [ValidateSet("tiny", "small", "medium", "large")]
    [string]$Size = "medium",
    [int]$Seed = 20260616
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FxFill Analytics — Full Pipeline" -ForegroundColor Cyan
Write-Host "  Size: $Size | Seed: $Seed" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Generate synthetic data ──
Write-Host "[1/4] Generating synthetic data..." -ForegroundColor Yellow
python "$ProjectRoot\scripts\generate_data.py" --size $Size --seed $Seed
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Data generation failed." -ForegroundColor Red; exit 1 }
Write-Host "  Done." -ForegroundColor Green

# ── Step 2: Build warehouse ──
Write-Host "[2/4] Building DuckDB warehouse..." -ForegroundColor Yellow
python "$ProjectRoot\scripts\build_warehouse.py"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Warehouse build failed." -ForegroundColor Red; exit 1 }
Write-Host "  Done." -ForegroundColor Green

# ── Step 3: dbt run and test ──
Write-Host "[3/4] Running dbt..." -ForegroundColor Yellow
Push-Location "$ProjectRoot\dbt_fxfill"
try {
    dbt deps
    dbt seed
    dbt run
    dbt test
} finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: dbt step had issues." -ForegroundColor Yellow }
Write-Host "  dbt complete." -ForegroundColor Green

# ── Step 4: Generate reports ──
Write-Host "[4/4] Generating reports..." -ForegroundColor Yellow
python "$ProjectRoot\scripts\generate_reports.py"
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: Report generation had issues." -ForegroundColor Yellow }
Write-Host "  Done." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Pipeline Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the dashboard:" -ForegroundColor White
Write-Host "  .\scripts\run_dashboard.ps1" -ForegroundColor Gray
