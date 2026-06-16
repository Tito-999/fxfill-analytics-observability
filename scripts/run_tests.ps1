# FxFill Analytics — Run All Tests
# Usage: .\scripts\run_tests.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  FxFill Analytics — Test Suite" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Push-Location $ProjectRoot
try {
    # Run pytest with coverage
    pytest tests/ -v --tb=short --cov=src/fxfill_analytics --cov-report=term-missing
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Test run complete." -ForegroundColor Cyan
