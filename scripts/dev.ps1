# Start AgriPay backend + frontend, wait until verified, optionally open browser.
param(
    [switch]$Open,
    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Repair-ProcessPathEnvironment {
    $CurrentPath = [Environment]::GetEnvironmentVariable("Path", "Process")
    if (-not $CurrentPath) {
        $CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "Process")
    }
    if ($CurrentPath) {
        [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
        [Environment]::SetEnvironmentVariable("Path", $CurrentPath, "Process")
    }
}

function Get-PortProcess {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { return $null }
    return Get-CimInstance Win32_Process -Filter "ProcessId=$($conn.OwningProcess)" -ErrorAction SilentlyContinue
}

function Is-StaleBackendProcess {
    param([object]$Process)
    if (-not $Process) { return $false }
    return ($Process.CommandLine -match '\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe') -and ($Process.CommandLine -match 'manage\.py runserver 127\.0\.0\.1:8000')
}

function Cleanup-StaleBackendProcess {
    $proc = Get-PortProcess -Port 8000
    if ($proc -and (Is-StaleBackendProcess -Process $proc)) {
        Write-Host "Stopping stale backend process on port 8000 (PID $($proc.ProcessId))" -ForegroundColor Yellow
        Stop-Process -Id $proc.ProcessId -Force
        Start-Sleep -Seconds 1
    }
}

function Test-AgriPayRunning {
    & "$Root\scripts\verify-dev-app.ps1" -Quiet
    return ($LASTEXITCODE -eq 0)
}

function Start-DevWindow {
    param(
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$FilePath,
        [string[]]$ArgumentList
    )

    Start-Process -FilePath $FilePath -WorkingDirectory $WorkingDirectory -WindowStyle Hidden `
        -ArgumentList $ArgumentList | Out-Null
}

Repair-ProcessPathEnvironment

Write-Host "AgriPay dev startup" -ForegroundColor Magenta
node "$Root\scripts\ensure-local-backend-env.mjs" "$Root\backend\.env" | Out-Null

if (Test-AgriPayRunning) {
    Write-Host "AgriPay is already running and verified." -ForegroundColor Green
} else {
    Write-Host "Starting dev servers..." -ForegroundColor Cyan

    Cleanup-StaleBackendProcess

    $backendHealth = "http://127.0.0.1:8000/health/"
    $backendUp = $false
    try {
        $null = Invoke-WebRequest -Uri $backendHealth -UseBasicParsing -TimeoutSec 2
        $backendUp = $true
    } catch { }

    if (-not $backendUp) {
        Write-Host "  Starting backend on http://127.0.0.1:8000/" -ForegroundColor DarkGray
        Start-DevWindow -Title "AgriPay Backend" -WorkingDirectory "$Root\backend" `
            -FilePath "$env:SystemRoot\System32\cmd.exe" `
            -ArgumentList @("/k", ".\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000")
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
            -FilePath "$env:SystemRoot\System32\cmd.exe" `
            -ArgumentList @("/k", "npm run dev")
    }

    Write-Host "  Waiting for AgriPay to become ready..." -ForegroundColor DarkGray
    $deadline = (Get-Date).AddSeconds(90)
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
