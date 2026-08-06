# Mr. Rao quality gate — run before commit
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "=== Mr. Rao quality gate ===" -ForegroundColor Cyan

$py = "python"
if (Test-Path ".\venv\Scripts\python.exe") {
    $py = ".\venv\Scripts\python.exe"
}

Write-Host "[1/3] Compile check..."
& $py -m compileall -q app.py config.py mr_rao
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL compileall" -ForegroundColor Red; exit 1 }

Write-Host "[2/3] CLI health..."
& $py -m mr_rao.cli health
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL health" -ForegroundColor Red; exit 1 }

Write-Host "[3/3] pytest..."
& $py -m pytest tests -q --tb=short
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL tests" -ForegroundColor Red; exit 1 }

Write-Host "=== GATE PASSED ===" -ForegroundColor Green
exit 0
