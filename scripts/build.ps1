# Production build verification - no Flutterwave required.
# MTN sandbox + personal-transfer + Stripe (if configured) is enough to ship dev/demo.
param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$WithBurnTest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Write-Step($msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

$failed = $false
$sep = "=" * 72

Write-Host "AgriPay build verification" -ForegroundColor Magenta
Write-Host "Flutterwave is optional - MTN MoMo sandbox or personal-transfer completes the payment stack." -ForegroundColor DarkGray

node (Join-Path $Root "scripts\ensure-local-backend-env.mjs") (Join-Path $Root "backend\.env") | Out-Null

if (-not $SkipBackend) {
    Write-Step "Backend: Django system check + migrations"
    $py = Join-Path $Root "backend\venv\Scripts\python.exe"
    if (-not (Test-Path $py)) {
        Write-Host "  venv missing - run: cd backend; python -m venv venv; .\venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
        $failed = $true
    } else {
        Push-Location (Join-Path $Root "backend")
        $env:USE_SQLITE = "True"
        & $py manage.py check
        if ($LASTEXITCODE -ne 0) { $failed = $true }
        & $py manage.py migrate --noinput
        if ($LASTEXITCODE -ne 0) { $failed = $true }
        Pop-Location
    }
}

if (-not $SkipFrontend) {
    Write-Step "Frontend: TypeScript + Vite production build"
    Push-Location (Join-Path $Root "frontend")
    if (-not (Test-Path "node_modules")) {
        npm ci
        if ($LASTEXITCODE -ne 0) { $failed = $true }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { $failed = $true }
    Pop-Location
}

Write-Step "Runtime capabilities (if backend is up)"
$caps = $null
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/" -TimeoutSec 3
    if ($health.service -eq "agripay-logistics-api") {
        $caps = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/system/capabilities/" -TimeoutSec 5
        $c = $caps.collection
        Write-Host "  personal_transfer: $($c.personal_transfer.status)" -ForegroundColor Green
        Write-Host "  sms_reconciliation: $($c.sms_reconciliation.status)" -ForegroundColor Green
        $mtnColor = if ($c.merchant_api.providers.mtn_momo -eq 'operational') { 'Green' } else { 'DarkGray' }
        Write-Host "  mtn_momo: $($c.merchant_api.providers.mtn_momo)" -ForegroundColor $mtnColor
        $stripeColor = if ($c.stripe.status -eq 'operational') { 'Green' } else { 'DarkGray' }
        Write-Host "  stripe: $($c.stripe.status)" -ForegroundColor $stripeColor
        Write-Host "  flutterwave: $($c.flutterwave.status) (optional)" -ForegroundColor DarkGray
    }
} catch {
    Write-Host "  Backend not running - static build only. Start with: .\scripts\dev.ps1" -ForegroundColor Yellow
}

if ($WithBurnTest) {
    Write-Step "Burn test (requires backend + frontend)"
    & (Join-Path $Root "backend\venv\Scripts\python.exe") (Join-Path $Root "scripts\burn-test.py")
    if ($LASTEXITCODE -ne 0) { $failed = $true }
}

Write-Host ""
Write-Host $sep -ForegroundColor Magenta
if ($failed) {
    Write-Host "BUILD: FAILED - fix errors above." -ForegroundColor Red
    exit 1
}

$paymentsReady = $false
if ($caps) {
    $paymentsReady = (
        $caps.collection.merchant_api.providers.mtn_momo -eq "operational" -or
        $caps.collection.stripe.status -eq "operational" -or
        $caps.collection.personal_transfer.status -eq "operational"
    )
}

Write-Host "BUILD: COMPLETE" -ForegroundColor Green
Write-Host "  Frontend dist/ and backend checks passed." -ForegroundColor Green
if ($paymentsReady) {
    Write-Host "  Payment stack ready without Flutterwave (personal + MTN/Stripe as configured)." -ForegroundColor Green
    Write-Host "  E2E MTN sandbox: .\backend\venv\Scripts\python .\scripts\e2e-mtn-momo.py" -ForegroundColor DarkGray
} else {
    Write-Host "  Start dev servers and configure MTN keys for live sandbox checkout." -ForegroundColor Yellow
}
Write-Host $sep -ForegroundColor Magenta
