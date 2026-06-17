# FxFill Analytics — Portfolio Setup
# Prerequisite: conda activate fxfill_analytics
param([string]$Profile = "demo")
$ErrorActionPreference = "Stop"
Write-Host "=== FxFill Portfolio Setup ===" -ForegroundColor Cyan

$pv = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($pv -ne "3.11") { Write-Host "WARNING: Expected Python 3.11, found $pv" -ForegroundColor Yellow }

Write-Host "Checking imports..." -ForegroundColor Cyan
python -c "import numpy,pandas,pyarrow,scipy,duckdb,streamlit,pandera,fastapi; print('Core imports OK')"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Missing dependencies. Run: pip install -r requirements.txt -r requirements-dev.txt" -ForegroundColor Red; exit 1 }

$size = if ($Profile -eq "demo") { "small" } else { "medium" }
$outDir = "data/generated/portfolio_demo"
Write-Host "Generating $size synthetic data..." -ForegroundColor Cyan
python scripts/generate_data.py --size $size --seed 20260616 --output-dir $outDir --overwrite
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Data generation failed" -ForegroundColor Red; exit 1 }

$runDir = (Get-ChildItem $outDir -Directory | Select-Object -First 1).FullName
$env:FXFILL_DUCKDB_PATH = "$PWD\warehouse\fxfill.duckdb"

Write-Host "Building DuckDB warehouse..." -ForegroundColor Cyan
python scripts/build_warehouse.py --input-run $runDir --database $env:FXFILL_DUCKDB_PATH --full-refresh --skip-dbt
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Warehouse build failed" -ForegroundColor Red; exit 1 }

Write-Host "Running dbt..." -ForegroundColor Cyan
dbt run --project-dir dbt_fxfill --profiles-dir dbt_fxfill
dbt test --project-dir dbt_fxfill --profiles-dir dbt_fxfill

Write-Host "Running experiment analysis..." -ForegroundColor Cyan
python scripts/run_experiment_analysis.py --experiment validation_before_autofill_v1 --database $env:FXFILL_DUCKDB_PATH --output-dir reports/phase4 --overwrite

Write-Host "Setup complete! Run: .\scripts\run_portfolio_demo.ps1" -ForegroundColor Green
