# Verify AgriPay dev servers are running AND serving this project (not a stale/wrong app).
param(
    [switch]$Json,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ConfigPath = Join-Path $Root "scripts\app-dev.json"
$Config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

function Write-Status {
    param(
        [bool]$Ok,
        [string]$Message,
        [hashtable]$Extra = @{}
    )

    $result = @{
        ok = $Ok
        message = $Message
        project = $Config.projectName
        frontendUrl = "http://$($Config.frontend.host):$($Config.frontend.port)/"
        backendUrl = "http://$($Config.backend.host):$($Config.backend.port)$($Config.backend.healthPath)"
    } + $Extra

    if ($Json) {
        $result | ConvertTo-Json -Compress
    } elseif (-not $Quiet) {
        if ($Ok) {
            Write-Host $Message -ForegroundColor Green
            Write-Host "  Frontend: $($result.frontendUrl)" -ForegroundColor Cyan
            Write-Host "  Backend:  http://$($Config.backend.host):$($Config.backend.port)/" -ForegroundColor Cyan
        } else {
            Write-Host $Message -ForegroundColor Red
            if ($Extra.ContainsKey("hint")) {
                Write-Host "  Hint: $($Extra.hint)" -ForegroundColor Yellow
            }
        }
    }

    if ($Ok) { exit 0 }
    exit 1
}

function Get-ListenerProcess {
    param(
        [string]$ListenHost,
        [int]$Port
    )

    $connections = Get-NetTCPConnection -LocalAddress $ListenHost -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $connections) { return $null }

    $processId = ($connections | Select-Object -First 1).OwningProcess
    return Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
}

function Get-PageTitle {
    param([string]$Url)

    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 4
    $match = [regex]::Match($response.Content, '<title>([^<]+)</title>', 'IgnoreCase')
    if (-not $match.Success) { return $null }
    return $match.Groups[1].Value.Trim()
}

$frontendUrl = "http://$($Config.frontend.host):$($Config.frontend.port)/"
$backendHealthUrl = "http://$($Config.backend.host):$($Config.backend.port)$($Config.backend.healthPath)"

# 1) Frontend must respond on the configured host/port (never bare localhost).
try {
    $title = Get-PageTitle -Url $frontendUrl
} catch {
    Write-Status -Ok $false -Message "AgriPay frontend is not running at $frontendUrl" -Extra @{
        code = "frontend_down"
        hint = "Run: .\scripts\dev.ps1"
    }
}

if ($title -ne $Config.frontend.expectedTitle) {
    Write-Status -Ok $false -Message "Wrong app on $frontendUrl (title: '$title')" -Extra @{
        code = "wrong_app"
        actualTitle = $title
        expectedTitle = $Config.frontend.expectedTitle
        hint = "Another project's dev server may be using this port. Run: .\scripts\dev.ps1"
    }
}

# 2) Process owning the port must belong to this repo (ignore stale/other projects).
$frontendProc = Get-ListenerProcess -ListenHost $Config.frontend.host -Port $Config.frontend.port
if ($frontendProc -and $frontendProc.CommandLine -notmatch [regex]::Escape($Config.projectPathMarker)) {
    Write-Status -Ok $false -Message "Port $($Config.frontend.port) is owned by another project" -Extra @{
        code = "foreign_process"
        processCommand = $frontendProc.CommandLine
        hint = "Stop the other dev server, then run: .\scripts\dev.ps1"
    }
}

# 3) Backend health check (proves API is live, not a dead session).
try {
    $health = Invoke-WebRequest -Uri $backendHealthUrl -UseBasicParsing -TimeoutSec 4
    if ($health.StatusCode -ne 200) {
        throw "HTTP $($health.StatusCode)"
    }
    $healthJson = $health.Content | ConvertFrom-Json
    if ($healthJson.service -ne "agripay-logistics-api") {
        throw "Unexpected service: $($healthJson.service)"
    }
} catch {
    Write-Status -Ok $false -Message "AgriPay backend is not healthy at $backendHealthUrl" -Extra @{
        code = "backend_down"
        hint = "Run: .\scripts\dev.ps1"
    }
}

$backendProc = Get-ListenerProcess -ListenHost $Config.backend.host -Port $Config.backend.port
if ($backendProc) {
    $cmd = $backendProc.CommandLine
    $ownsPort = ($cmd -match [regex]::Escape($Config.projectPathMarker)) -or ($cmd -match 'agripay-logistics-api')
    if (-not $ownsPort -and $cmd -match 'manage\.py runserver' -and $cmd -notmatch [regex]::Escape($Config.projectPathMarker)) {
        Write-Status -Ok $false -Message "Port $($Config.backend.port) may be a different Django project" -Extra @{
            code = "foreign_backend"
            hint = "Run: .\scripts\dev.ps1 to start the AgriPay backend on 127.0.0.1:8000"
        }
    }
}

Write-Status -Ok $true -Message "Verified: $($Config.projectName) is running" -Extra @{
    code = "ok"
    frontendTitle = $title
    frontendProcessId = if ($frontendProc) { [int]$frontendProc.ProcessId } else { $null }
    backendProcessId = if ($backendProc) { [int]$backendProc.ProcessId } else { $null }
}
