# FxFill Analytics — Portfolio Setup
# Prerequisite: conda activate fxfill_analytics
param([string]$Profile = "demo")
$ErrorActionPreference = "Stop"

# Environment variables
$env:PYTHONNOUSERSITE = "1"
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

Write-Host "=== FxFill Portfolio Setup ===" -ForegroundColor Cyan

# Strict Python version check
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python is not available in the current environment." -ForegroundColor Red
    exit 1
}
if ($pythonVersion -ne "3.11") {
    Write-Host "ERROR: Python 3.11 is required. Current version: $pythonVersion" -ForegroundColor Red
    Write-Host "Run: conda activate fxfill_analytics" -ForegroundColor Yellow
    exit 1
}
python -c "import sys; print('Python:', sys.executable)"

# Dependency import check
Write-Host "Checking imports..." -ForegroundColor Cyan
python -c "import numpy,pandas,pyarrow,scipy,duckdb,streamlit,pandera,plotly,statsmodels; print('Core imports OK')"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Missing dependencies. Run: pip install -r requirements.txt -r requirements-dev.txt" -ForegroundColor Red; exit 1 }
python -m pip check
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: pip check found broken dependencies." -ForegroundColor Red; exit 1 }

# Data generation
$size = if ($Profile -eq "demo") { "small" } else { "medium" }
$outDir = "data/generated/portfolio_demo"
if (Test-Path $outDir) { Remove-Item $outDir -Recurse -Force }
Write-Host "Generating $size synthetic data..." -ForegroundColor Cyan
python scripts/generate_data.py --size $size --seed 20260616 --output-dir $outDir --overwrite
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Data generation failed." -ForegroundColor Red; exit 1 }

$runDirs = @(Get-ChildItem $outDir -Directory)
if ($runDirs.Count -ne 1) { Write-Host "ERROR: Expected exactly 1 run directory, found $($runDirs.Count)" -ForegroundColor Red; exit 1 }
$runDir = $runDirs[0].FullName

# Warehouse
New-Item -ItemType Directory -Force -Path "warehouse" | Out-Null
$env:FXFILL_DUCKDB_PATH = (Join-Path $PWD "warehouse\fxfill.duckdb")
Write-Host "Building warehouse: $env:FXFILL_DUCKDB_PATH" -ForegroundColor Cyan
python scripts/build_warehouse.py --input-run $runDir --database $env:FXFILL_DUCKDB_PATH --full-refresh --skip-dbt
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Warehouse build failed." -ForegroundColor Red; exit 1 }

# dbt
Write-Host "Running dbt..." -ForegroundColor Cyan
dbt run --project-dir dbt_fxfill --profiles-dir dbt_fxfill
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: dbt run failed." -ForegroundColor Red; exit 1 }
dbt test --project-dir dbt_fxfill --profiles-dir dbt_fxfill
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: dbt test failed." -ForegroundColor Red; exit 1 }

# Experiment analysis
Write-Host "Running experiment analysis..." -ForegroundColor Cyan
python scripts/run_experiment_analysis.py --experiment validation_before_autofill_v1 --database $env:FXFILL_DUCKDB_PATH --output-dir reports/phase4 --overwrite
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Experiment analysis failed." -ForegroundColor Red; exit 1 }

Write-Host "Portfolio setup completed successfully." -ForegroundColor Green
Write-Host "Database: $env:FXFILL_DUCKDB_PATH"
Write-Host "Next: .\scripts\run_portfolio_demo.ps1 -Port 8501"
exit 0
