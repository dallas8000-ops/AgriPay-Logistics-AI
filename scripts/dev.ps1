# Start AgriPay backend + frontend, wait until verified, optionally open browser.
param(
    [switch]$Open,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Test-AgriPayRunning {
    & "$Root\scripts\verify-dev-app.ps1" -Quiet
    return ($LASTEXITCODE -eq 0)
}

function Start-DevWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "Set-Location '$WorkingDirectory'; `$Host.UI.RawUI.WindowTitle = '$Title'; $Command"
    ) | Out-Null
}

Write-Host "AgriPay dev startup" -ForegroundColor Magenta
node "$Root\scripts\ensure-local-backend-env.mjs" "$Root\backend\.env" | Out-Null

if (Test-AgriPayRunning) {
    Write-Host "AgriPay is already running and verified." -ForegroundColor Green
} else {
    Write-Host "Starting dev servers..." -ForegroundColor Cyan

    $backendHealth = "http://127.0.0.1:8000/health/"
    $backendUp = $false
    try {
        $null = Invoke-WebRequest -Uri $backendHealth -UseBasicParsing -TimeoutSec 2
        $backendUp = $true
    } catch { }

    if (-not $backendUp) {
        Write-Host "  Starting backend on http://127.0.0.1:8000/" -ForegroundColor DarkGray
        Start-DevWindow -Title "AgriPay Backend" -WorkingDirectory "$Root\backend" `
            -Command "`$env:USE_SQLITE='True'; `$env:DEBUG='True'; .\venv\Scripts\python manage.py runserver 127.0.0.1:8000"
    }

    $frontendUrl = "http://127.0.0.1:5174/"
    $frontendUp = $false
    try {
        $page = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2
        if ($page.Content -match '<title>AgriPay Logistics AI</title>') { $frontendUp = $true }
    } catch { }

    if (-not $frontendUp) {
        Write-Host "  Starting frontend on http://127.0.0.1:5174/" -ForegroundColor DarkGray
        Start-DevWindow -Title "AgriPay Frontend" -WorkingDirectory "$Root\frontend" `
            -Command "npm run dev"
    }

    Write-Host "  Waiting for AgriPay to become ready..." -ForegroundColor DarkGray
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        if (Test-AgriPayRunning) { break }
    }

    if (-not (Test-AgriPayRunning)) {
        Write-Host "AgriPay did not become ready in time." -ForegroundColor Red
        Write-Host "Run: .\scripts\verify-dev-app.ps1" -ForegroundColor Yellow
        exit 1
    }
}

& "$Root\scripts\verify-dev-app.ps1"

if ($Open -or (-not $NoOpen)) {
    & "$Root\scripts\open-app.ps1"
}
