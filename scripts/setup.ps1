# FxFill Analytics — Environment Setup Script (Windows PowerShell)
# Usage: .\scripts\setup.ps1
# Creates conda environment and installs all dependencies.

param(
    [string]$EnvName = "fxfill_analytics"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FxFill Analytics — Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Check Python version ──
Write-Host "[1/4] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.11." -ForegroundColor Red
    exit 1
}
Write-Host "  $pythonVersion" -ForegroundColor Green

# ── Step 2: Create virtual environment ──
Write-Host "[2/4] Creating virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvPath) {
    Write-Host "  Virtual environment already exists at $venvPath" -ForegroundColor Gray
} else {
    python -m venv $venvPath
    Write-Host "  Created virtual environment at $venvPath" -ForegroundColor Green
}

# ── Step 3: Activate and upgrade pip ──
Write-Host "[3/4] Activating environment and upgrading pip..." -ForegroundColor Yellow
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
. $activateScript
python -m pip install --upgrade pip --quiet
Write-Host "  pip upgraded" -ForegroundColor Green

# ── Step 4: Install dependencies ──
Write-Host "[4/4] Installing dependencies..." -ForegroundColor Yellow
pip install -r "$ProjectRoot\requirements.txt" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install core dependencies." -ForegroundColor Red
    exit 1
}
Write-Host "  Core dependencies installed" -ForegroundColor Green

pip install -r "$ProjectRoot\requirements-dev.txt" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some dev dependencies may not have installed." -ForegroundColor Yellow
}
Write-Host "  Dev dependencies installed" -ForegroundColor Green

# ── Verify ──
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate the environment:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "To run tests:" -ForegroundColor White
Write-Host "  .\scripts\run_tests.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "To generate data and build warehouse:" -ForegroundColor White
Write-Host "  .\scripts\run_all.ps1" -ForegroundColor Gray
