<#
  Interactive deploy for subscription-scope Bicep.
  - Validates az CLI presence and login
  - Prompts with defaults (Enter uses default)
  - Writes parameters/main.json next to the template
  - Runs: az deployment sub create
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "=== Bicep Deployment Script ===" -ForegroundColor Cyan

# Ensure az CLI exists
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
  Write-Host "Azure CLI (az) is not installed or not on PATH." -ForegroundColor Red
  Write-Host "Install: https://aka.ms/azure-cli" -ForegroundColor Yellow
  exit 1
}

# Ensure user is logged in
$loggedIn = $false
try {
  $null = az account show --only-show-errors 2>$null
  if ($LASTEXITCODE -eq 0) { $loggedIn = $true }
} catch { $loggedIn = $false }

if (-not $loggedIn) {
  Write-Host "You're not logged in. Opening device-code login..." -ForegroundColor Yellow
  az login --use-device-code
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Login failed. Please run 'az login' and retry." -ForegroundColor Red
    exit 1
  }
}

# Show current subscription
$sub   = (az account show --query name -o tsv)
$subId = (az account show --query id   -o tsv)
Write-Host ("Subscription: {0} ({1})" -f $sub, $subId) -ForegroundColor Green
Write-Host "If this is not correct: az account set --subscription <SUBSCRIPTION-ID-OR-NAME>`n" -ForegroundColor Yellow

# Helper: prompt with default (Enter -> default)
function Read-WithDefault([string]$Prompt, [string]$Default) {
  $in = Read-Host "$Prompt (default: $Default)"
  if ([string]::IsNullOrWhiteSpace($in)) { return $Default }
  return $in.Trim()
}

# Prompts
$rgName         = Read-WithDefault "Enter Resource Group name" "rg-bicep-starter"
$location       = Read-WithDefault "Enter Azure region" "centralus"
$deploymentType = Read-WithDefault "Enter Deployment Type (Lab/Demo/PoC/Prod)" "Lab"

Write-Host "`nDeploying with:" -ForegroundColor Green
Write-Host "  Resource Group : $rgName"
Write-Host "  Location       : $location"
Write-Host "  DeploymentType : $deploymentType"
Write-Host ""

# Paths (resolve from scripts/ → ../)
$TemplateDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath) # .../resource-group
$Template    = Join-Path $TemplateDir "main.bicep"
$ParamsFile  = Join-Path $TemplateDir "parameters\main.json"

# Ensure parameters folder exists
$paramDir = Split-Path $ParamsFile -Parent
if (-not (Test-Path $paramDir)) { New-Item -ItemType Directory -Path $paramDir -Force | Out-Null }

# Write parameters JSON
$paramContent = @{
  '$schema'      = 'https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#'
  contentVersion = '1.0.0.0'
  parameters     = @{
    rgName         = @{ value = $rgName }
    location       = @{ value = $location }
    deploymentType = @{ value = $deploymentType }
  }
} | ConvertTo-Json -Depth 6

Set-Content -Path $ParamsFile -Value $paramContent -Encoding UTF8

# Sanity checks
if (-not (Test-Path $Template)) {
  Write-Host "Template not found: $Template" -ForegroundColor Red
  exit 1
}

# Deploy
az deployment sub create `
  --name "rg-create-$(Get-Date -Format 'yyyyMMdd-HHmmss')" `
  --location $location `
  --template-file $Template `
  --parameters $ParamsFile

if ($LASTEXITCODE -eq 0) {
  Write-Host "Deployment complete." -ForegroundColor Green
} else {
  Write-Host "Deployment failed." -ForegroundColor Red
  exit $LASTEXITCODE
}
