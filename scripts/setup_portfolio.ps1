# FxFill Analytics — Portfolio Setup Script
# Usage: .\scripts\setup_portfolio.ps1 [-Profile demo]
param([string]$Profile = "demo")

$ErrorActionPreference = "Stop"
Write-Host "=== FxFill Portfolio Setup ===" -ForegroundColor Cyan

$required_python = "3.11"
$py = python --version 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Python not found. Install Python 3.11." -ForegroundColor Red; exit 1 }
$py_ver = (python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ($py_ver -ne $required_python) { Write-Host "WARNING: Expected Python $required_python, found $py_ver" -ForegroundColor Yellow }

$env_name = "fxfill_analytics"
$conda_check = conda env list 2>&1
if ($conda_check -notmatch $env_name) {
    Write-Host "Creating conda environment '$env_name'..." -ForegroundColor Yellow
    conda create -n $env_name python=3.11 -y
    conda run -n $env_name python -m pip install -r requirements.txt
    conda run -n $env_name python -m pip install -r requirements-dev.txt
}
Write-Host "Environment '$env_name' ready." -ForegroundColor Green

$size = if ($Profile -eq "demo") { "small" } else { "medium" }
Write-Host "Generating $size synthetic data..." -ForegroundColor Cyan
$env:PYTHONNOUSERSITE="1"
conda run -n $env_name python scripts/generate_data.py --size $size --seed 20260616 --output-dir data/generated/demo_in --overwrite
$run_dir = (Get-ChildItem data/generated/demo_in -Directory | Select-Object -First 1).FullName

Write-Host "Building warehouse..." -ForegroundColor Cyan
$env:FXFILL_DUCKDB_PATH = "$PWD\warehouse\fxfill.duckdb"
conda run -n $env_name python scripts/build_warehouse.py --input-run $run_dir --database $env:FXFILL_DUCKDB_PATH --full-refresh --skip-dbt

Write-Host "Running dbt..." -ForegroundColor Cyan
conda run -n $env_name dbt run --project-dir dbt_fxfill --profiles-dir dbt_fxfill
conda run -n $env_name dbt test --project-dir dbt_fxfill --profiles-dir dbt_fxfill

Write-Host "Running experiment analysis..." -ForegroundColor Cyan
conda run -n $env_name python scripts/run_experiment_analysis.py --experiment validation_before_autofill_v1 --database warehouse/fxfill.duckdb --output-dir reports/phase4 --overwrite

Write-Host "Setup complete! Run: .\scripts\run_portfolio_demo.ps1" -ForegroundColor Green
