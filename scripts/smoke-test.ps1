# Thorough live smoke test — run with dev servers up (.\scripts\dev.ps1)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Python = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

Write-Host "`n==> Build verification" -ForegroundColor Cyan
& (Join-Path $Root "scripts\build.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`n==> Live smoke test (API + pricing + invoices + marketplace)" -ForegroundColor Cyan
& $Python (Join-Path $Root "scripts\smoke-test.py")
$smokeExit = $LASTEXITCODE

Write-Host "`n==> Burn test (payments deep path)" -ForegroundColor Cyan
& $Python (Join-Path $Root "scripts\burn-test.py")
$burnExit = $LASTEXITCODE

Write-Host "`n==> MTN MoMo E2E (if sandbox keys configured)" -ForegroundColor Cyan
& $Python (Join-Path $Root "scripts\e2e-mtn-momo.py")
$mtnExit = $LASTEXITCODE
if ($mtnExit -ne 0) {
    Write-Host "  MTN E2E skipped or failed (optional if keys missing)" -ForegroundColor Yellow
}

if ($smokeExit -ne 0 -or $burnExit -ne 0) {
    Write-Host "`nSMOKE TEST: FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================================================" -ForegroundColor Green
Write-Host "SMOKE TEST: ALL CORE CHECKS PASSED" -ForegroundColor Green
Write-Host "  smoke-test-results.json + burn-test-results.json updated" -ForegroundColor DarkGray
Write-Host "========================================================================" -ForegroundColor Green
exit 0
