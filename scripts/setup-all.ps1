# AgriPay - Full stack setup via Stripe Projects (official installer)
# Docs: https://docs.stripe.com/projects

param(
    [switch]$SkipInit,
    [string]$GitHubRepo = "",
    [string]$DockerImage = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Get-StripeProjectStatus {
    $raw = stripe projects status --json 2>&1 | Out-String
    return ($raw | ConvertFrom-Json)
}

function Invoke-Stripe {
    param([string[]]$Args)
    & stripe @Args
    if ($LASTEXITCODE -ne 0) { return $false }
    return $true
}

function Invoke-StripeAddWithConfig {
    param(
        [string]$Service,
        [hashtable]$Config,
        [string[]]$ExtraArgs = @()
    )
    $configJson = ($Config | ConvertTo-Json -Compress)
    $helper = Join-Path $Root "scripts\stripe-add-config.mjs"
    & node $helper $Service $configJson @ExtraArgs
    return ($LASTEXITCODE -eq 0)
}

function Merge-BackendEnvFromRoot {
    param(
        [string]$RootEnv,
        [string]$BackendEnv
    )

    if (-not (Test-Path $RootEnv)) { return }

    if (-not (Test-Path $BackendEnv)) {
        Copy-Item (Join-Path $Root "backend\.env.example") $BackendEnv
    }

    $backendContent = Get-Content $BackendEnv -Raw
    $rootVars = Get-Content $RootEnv

    foreach ($line in $rootVars) {
        if ($line -match '^\s*#' -or $line -match '^\s*$') { continue }
        if ($line -notmatch '^([^=]+)=(.*)$') { continue }

        $key = $Matches[1].Trim()
        $val = $Matches[2].Trim()

        if ($key -eq 'AGRIPAY_DB_VARIABLES') {
            $mergeScript = Join-Path $Root "scripts\merge-db-env.mjs"
            if (Test-Path $mergeScript) {
                $databaseUrl = & node $mergeScript $RootEnv
                if ($databaseUrl -and $LASTEXITCODE -eq 0) {
                    if ($backendContent -match '(?m)^DATABASE_URL=.*') {
                        $backendContent = $backendContent -replace '(?m)^DATABASE_URL=.*', "DATABASE_URL=$databaseUrl"
                    } else {
                        $backendContent += "`nDATABASE_URL=$databaseUrl"
                    }
                }
            }
            continue
        }

        $map = @{
            'STRIPE_SECRET_KEY' = 'STRIPE_SECRET_KEY'
            'STRIPE_PUBLISHABLE_KEY' = 'STRIPE_PUBLISHABLE_KEY'
            'STRIPE_WEBHOOK_SECRET' = 'STRIPE_WEBHOOK_SECRET'
            'DATABASE_URL' = 'DATABASE_URL'
        }
        if (-not $map.ContainsKey($key)) { continue }

        $target = $map[$key]
        if ($backendContent -match "(?m)^$target=.*") {
            $backendContent = $backendContent -replace "(?m)^$target=.*", "$target=$val"
        } else {
            $backendContent += "`n$target=$val"
        }
    }

    Set-Content $BackendEnv $backendContent.TrimEnd()
    Write-Host "Merged Stripe Projects vars into backend/.env" -ForegroundColor Green
}

Write-Host "AgriPay Setup (Stripe Projects installer)" -ForegroundColor Magenta
Write-Host "=========================================" -ForegroundColor Magenta

if (-not (Get-Command stripe -ErrorAction SilentlyContinue)) {
    Write-Host "Installing @stripe/cli..." -ForegroundColor Yellow
    npm install -g @stripe/cli
}

Write-Host "Ensuring Stripe Projects plugin is installed..."
stripe plugin install projects | Out-Null

if (-not $SkipInit -and -not (Test-Path ".projects\state.json")) {
    Write-Host ""
    Write-Host "Step 1: Stripe Projects init" -ForegroundColor Cyan
    Write-Host "  Run in your terminal: stripe projects init --yes --accept-tos" -ForegroundColor White
    Write-Host "  Then re-run: .\scripts\setup-all.ps1 -SkipInit" -ForegroundColor White
    exit 1
} elseif (Test-Path ".projects\state.json") {
    Write-Host "Stripe Projects already initialized" -ForegroundColor Green
}

Write-Host ""
Write-Host "Step 2: Link Railway provider" -ForegroundColor Cyan
Invoke-Stripe @("projects", "link", "railway", "--accept-tos", "--yes") | Out-Null

Write-Host ""
Write-Host "Step 3: Provision Railway services" -ForegroundColor Cyan
$status = Get-StripeProjectStatus
$services = @($status.data.services)

foreach ($svc in $services) {
    if ($svc.status -ne "needs_information") { continue }
    Write-Host "  Removing incomplete resource $($svc.name) (use --config via Node on Windows)..." -ForegroundColor Yellow
    Invoke-Stripe @("projects", "remove", $svc.name, "--yes", "--non-interactive") | Out-Null
}

$status = Get-StripeProjectStatus
$services = @($status.data.services)

if (-not ($services | Where-Object { $_.service_id -eq "postgres" })) {
    Write-Host "  Adding railway/postgres..." -ForegroundColor Cyan
    $ok = Invoke-Stripe @("projects", "add", "railway/postgres", "--yes", "--accept-tos", "--non-interactive", "--name", "agripay-db")
    if (-not $ok) { Write-Host "  postgres add failed." -ForegroundColor Yellow }
}

$hosting = $services | Where-Object { $_.service_id -eq "hosting" } | Select-Object -First 1
if (-not $hosting -and ($GitHubRepo -or $DockerImage)) {
    Write-Host "  Adding railway/hosting..." -ForegroundColor Cyan
    $hostingConfig = @{}
    if ($GitHubRepo) { $hostingConfig.repo = $GitHubRepo }
    elseif ($DockerImage) { $hostingConfig.image = $DockerImage }
    $extra = @("--name", "railway-hosting")
    $ok = Invoke-StripeAddWithConfig -Service "railway/hosting" -Config $hostingConfig -ExtraArgs $extra
    if (-not $ok) { Write-Host "  hosting add failed." -ForegroundColor Yellow }
} elseif (-not $hosting) {
    Write-Host "  Skipping railway/hosting (pass -GitHubRepo owner/repo or -DockerImage name:tag when ready)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Step 4: Sync credentials to .env" -ForegroundColor Cyan
Invoke-Stripe @("projects", "env", "--refresh") | Out-Null
Invoke-Stripe @("projects", "env", "--pull") | Out-Null

Merge-BackendEnvFromRoot -RootEnv (Join-Path $Root ".env") -BackendEnv (Join-Path $Root "backend\.env")

Write-Host ""
Write-Host "Step 5: Webhook listener (separate terminal):" -ForegroundColor Cyan
Write-Host "  stripe listen --forward-to localhost:8000/api/payments/webhook/stripe/"
Write-Host ""
stripe projects status
