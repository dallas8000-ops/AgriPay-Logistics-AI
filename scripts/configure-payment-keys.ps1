# Interactive sandbox key setup - writes to backend/.env (never echoes secrets).
param(
    [string]$FlutterwaveSecret = "",
    [string]$FlutterwavePublic = "",
    [string]$FlutterwaveWebhook = "",
    [string]$MtnSubscriptionKey = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "backend\.env"

function Set-EnvLine {
    param([string[]]$Lines, [string]$Key, [string]$Value)
    $found = $false
    $out = @()
    foreach ($line in $Lines) {
        if ($line -match "^$([regex]::Escape($Key))=") {
            if ($Value) { $out += "$Key=$Value" }
            $found = $true
        } else {
            $out += $line
        }
    }
    if (-not $found -and $Value) { $out += "$Key=$Value" }
    return $out
}

node (Join-Path $Root "scripts\ensure-local-backend-env.mjs") $EnvFile | Out-Null

$lines = @()
if (Test-Path $EnvFile) { $lines = Get-Content $EnvFile }

Write-Host ""
Write-Host "=== AgriPay payment sandbox setup ===" -ForegroundColor Cyan
Write-Host "Signup (open in browser if needed):" -ForegroundColor DarkGray
Write-Host "  Flutterwave: https://dashboard.flutterwave.com/register" -ForegroundColor DarkGray
Write-Host "  MTN MoMo:    https://momodeveloper.mtn.com/signup" -ForegroundColor DarkGray
Write-Host ""

if (-not $FlutterwaveSecret -and -not $MtnSubscriptionKey) {
    Write-Host "Flutterwave TEST secret key (FLWSECK_TEST-... from Settings > API Keys, Test mode ON):" -ForegroundColor Yellow
    $FlutterwaveSecret = Read-Host "Paste FLUTTERWAVE_SECRET_KEY (or Enter to skip)"
}
if (-not $FlutterwavePublic -and $FlutterwaveSecret) {
    Write-Host "Flutterwave TEST public key (FLWPUBK_TEST-...):" -ForegroundColor Yellow
    $FlutterwavePublic = Read-Host "Paste FLUTTERWAVE_PUBLIC_KEY (or Enter to skip)"
}
if (-not $FlutterwaveWebhook -and $FlutterwaveSecret) {
    Write-Host "Flutterwave webhook secret hash (Settings > Webhooks, optional for local verify polling):" -ForegroundColor Yellow
    $FlutterwaveWebhook = Read-Host "Paste FLUTTERWAVE_WEBHOOK_SECRET (or Enter to skip)"
}
if (-not $MtnSubscriptionKey -and -not $FlutterwaveSecret) {
    Write-Host "MTN MoMo sandbox subscription key (Collections product, Ocp-Apim-Subscription-Key):" -ForegroundColor Yellow
    $MtnSubscriptionKey = Read-Host "Paste MTN_MOMO_SUBSCRIPTION_KEY (or Enter to skip)"
}

if ($FlutterwaveSecret) {
    $lines = Set-EnvLine $lines "FLUTTERWAVE_SECRET_KEY" $FlutterwaveSecret.Trim()
}
if ($FlutterwavePublic) {
    $lines = Set-EnvLine $lines "FLUTTERWAVE_PUBLIC_KEY" $FlutterwavePublic.Trim()
}
if ($FlutterwaveWebhook) {
    $lines = Set-EnvLine $lines "FLUTTERWAVE_WEBHOOK_SECRET" $FlutterwaveWebhook.Trim()
}
if ($MtnSubscriptionKey) {
    $lines = Set-EnvLine $lines "MTN_MOMO_SUBSCRIPTION_KEY" $MtnSubscriptionKey.Trim()
    $lines = Set-EnvLine $lines "MTN_MOMO_ENV" "sandbox"
    $lines = Set-EnvLine $lines "MTN_MOMO_TARGET_ENV" "sandbox"
    $lines = Set-EnvLine $lines "MTN_MOMO_CALLBACK_HOST" "127.0.0.1"
}

Set-Content -Path $EnvFile -Value (($lines -join "`n").TrimEnd() + "`n") -Encoding utf8
Write-Host ""
Write-Host "Updated backend/.env (secrets not displayed)." -ForegroundColor Green

if ($MtnSubscriptionKey) {
    Write-Host "Provisioning MTN sandbox API user + key..." -ForegroundColor Cyan
    & (Join-Path $Root "backend\venv\Scripts\python.exe") (Join-Path $Root "scripts\mtn-provision-sandbox.py")
}

Write-Host ""
Write-Host "Restart the Django backend so it picks up new .env values." -ForegroundColor Yellow
Write-Host "Then run: .\backend\venv\Scripts\python .\scripts\e2e-real-payment.py" -ForegroundColor Cyan
