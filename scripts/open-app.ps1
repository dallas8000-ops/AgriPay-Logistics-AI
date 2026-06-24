# Open AgriPay only after live verification (never trust stale localhost sessions).
param(
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$verifyJson = & "$Root\scripts\verify-dev-app.ps1" -Json -Quiet
$verify = $verifyJson | ConvertFrom-Json

if (-not $verify.ok) {
    if ($Json) {
        @{
            ok = $false
            opened = $false
            message = $verify.message
            code = $verify.code
            hint = $verify.hint
        } | ConvertTo-Json -Compress
    } else {
        Write-Host $verify.message -ForegroundColor Red
        if ($verify.hint) {
            Write-Host $verify.hint -ForegroundColor Yellow
        }
    }
    exit 1
}

Start-Process $verify.frontendUrl

if ($Json) {
    @{
        ok = $true
        opened = $true
        url = $verify.frontendUrl
        message = "Opened $($verify.frontendUrl)"
    } | ConvertTo-Json -Compress
} else {
    Write-Host "Opened $($verify.frontendUrl)" -ForegroundColor Green
}

exit 0
