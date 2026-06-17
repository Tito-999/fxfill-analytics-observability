# FxFill Analytics — Portfolio Setup
# Prerequisite: conda activate fxfill_analytics
param([string]$Profile = "demo")
$ErrorActionPreference = "Stop"

$env:PYTHONNOUSERSITE = "1"
$env:NO_PROXY = "127.0.0.1,localhost"
$env:no_proxy = "127.0.0.1,localhost"

Write-Host "=== FxFill Portfolio Setup ===" -ForegroundColor Cyan

$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Python not available." -ForegroundColor Red; exit 1 }
if ($pythonVersion -ne "3.11") { Write-Host "ERROR: Python 3.11 required, found $pythonVersion. Run: conda activate fxfill_analytics" -ForegroundColor Red; exit 1 }
python -c "import sys; print('Python:', sys.executable)"

Write-Host "Checking imports..." -ForegroundColor Cyan
python -c "import numpy,pandas,pyarrow,scipy,duckdb,streamlit,pandera,plotly,statsmodels; print('Core imports OK')"
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Missing dependencies." -ForegroundColor Red; exit 1 }
python -m pip check
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Broken dependencies." -ForegroundColor Red; exit 1 }

$size = if ($Profile -eq "demo") { "small" } else { "medium" }
$outDir = "data/generated/portfolio_demo"
if (Test-Path $outDir) { Remove-Item $outDir -Recurse -Force }
Write-Host "Generating $size synthetic data..." -ForegroundColor Cyan
python scripts/generate_data.py --size $size --seed 20260616 --output-dir $outDir --overwrite
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Data generation failed." -ForegroundColor Red; exit 1 }
$runDirs = @(Get-ChildItem $outDir -Directory)
if ($runDirs.Count -ne 1) { Write-Host "ERROR: Expected 1 run directory, found $($runDirs.Count)" -ForegroundColor Red; exit 1 }
$runDir = $runDirs[0].FullName

# Delete stale persistent DB before rebuild
New-Item -ItemType Directory -Force -Path "warehouse" | Out-Null
$dbPath = Join-Path $PWD "warehouse\fxfill.duckdb"
if (Test-Path $dbPath) { Write-Host "Removing existing persistent warehouse..." -ForegroundColor Yellow; Remove-Item $dbPath -Force }
$env:FXFILL_DUCKDB_PATH = $dbPath
Write-Host "Building warehouse: $env:FXFILL_DUCKDB_PATH" -ForegroundColor Cyan
python scripts/build_warehouse.py --input-run $runDir --database $env:FXFILL_DUCKDB_PATH --full-refresh --skip-dbt
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Warehouse build failed." -ForegroundColor Red; exit 1 }

Write-Host "Running dbt with full refresh..." -ForegroundColor Cyan
dbt run --project-dir dbt_fxfill --profiles-dir dbt_fxfill --full-refresh
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: dbt run failed." -ForegroundColor Red; exit 1 }
dbt test --project-dir dbt_fxfill --profiles-dir dbt_fxfill
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: dbt test failed." -ForegroundColor Red; exit 1 }

# Verify required warehouse objects
Write-Host "Verifying warehouse schema..." -ForegroundColor Cyan
python -c @"
import os, sys, duckdb
db = os.environ['FXFILL_DUCKDB_PATH']
conn = duckdb.connect(db, read_only=True)
required = {('main_marts','mart_feature_adoption_segmented'),('main_marts','mart_feature_time_to_first_use'),('main_marts','mart_error_root_cause'),('main_marts','mart_ab_test_user_metrics')}
existing = {(r[0],r[1]) for r in conn.execute('''SELECT table_schema, table_name FROM information_schema.tables''').fetchall()}
missing = sorted(required - existing)
if missing:
    for s,t in missing: print(f'ERROR: missing {s}.{t}')
    sys.exit(1)
print('Required warehouse objects verified.')
"@
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Warehouse schema verification failed." -ForegroundColor Red; exit 1 }

python scripts/run_experiment_analysis.py --experiment validation_before_autofill_v1 --database $env:FXFILL_DUCKDB_PATH --output-dir reports/phase4 --overwrite
if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: Experiment analysis failed." -ForegroundColor Red; exit 1 }

Write-Host "Portfolio setup completed successfully." -ForegroundColor Green
Write-Host "Database: $env:FXFILL_DUCKDB_PATH"
Write-Host "Next: .\scripts\run_portfolio_demo.ps1 -Port 8501"
exit 0
