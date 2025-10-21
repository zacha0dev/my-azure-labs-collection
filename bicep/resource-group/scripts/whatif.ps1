<#
  Interactive what-if for Bicep.
  - Validates az CLI presence and login
  - Prompts with defaults (Enter uses default)
  - Writes parameters/main.json next to the template
  - Auto-detects Bicep targetScope to choose sub- or RG-scope what-if
#>

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "=== Bicep What-If Script ===" -ForegroundColor Cyan

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

# Helper: prompt with default
function Read-WithDefault([string]$Prompt, [string]$Default) {
  $in = Read-Host "$Prompt (default: $Default)"
  if ([string]::IsNullOrWhiteSpace($in)) { return $Default }
  return $in.Trim()
}

# Prompts
$rgName         = Read-WithDefault "Enter Resource Group name" "rg-bicep-starter"
$location       = Read-WithDefault "Enter Azure region" "centralus"
$deploymentType = Read-WithDefault "Enter Deployment Type (Lab/Demo/PoC/Prod)" "Lab"

Write-Host "`nPreviewing with:" -ForegroundColor Green
Write-Host "  Resource Group : $rgName"
Write-Host "  Location       : $location"
Write-Host "  DeploymentType : $deploymentType"
Write-Host ""

# Paths (resolve from scripts/ → ../)
$TemplateDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$Template    = Join-Path $TemplateDir "main.bicep"
$ParamsFile  = Join-Path $TemplateDir "parameters\main.json"

# Sanity checks
if (-not (Test-Path $Template)) {
  Write-Host "Template not found: $Template" -ForegroundColor Red
  exit 1
}

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

# Determine target scope (simple parse of main.bicep)
$targetScope = 'resourceGroup' # Bicep default if unspecified
try {
  $bicepText = Get-Content -Path $Template -Raw -ErrorAction Stop
  if ($bicepText -match "targetScope\s*=\s*'subscription'") { $targetScope = 'subscription' }
  elseif ($bicepText -match "targetScope\s*=\s*'resourceGroup'") { $targetScope = 'resourceGroup' }
} catch {
  Write-Host "Warning: Could not read $Template to determine targetScope. Defaulting to '$targetScope'." -ForegroundColor Yellow
}

Write-Host ("Detected targetScope: {0}" -f $targetScope) -ForegroundColor Cyan

# Run what-if based on detected scope
if ($targetScope -eq 'resourceGroup') {
  Write-Host "`nRunning resource-group scope what-if..." -ForegroundColor Cyan
  # Ensure RG exists to help resolver (optional but useful)
  $rgExists = (az group exists --name $rgName | Out-String).Trim()
  if ($rgExists -ne 'true') {
    Write-Host "Resource group '$rgName' does not exist. Creating it in '$location' for accurate what-if preview..." -ForegroundColor Yellow
    az group create --name $rgName --location $location 1>$null
  }
  az deployment group what-if `
    --resource-group $rgName `
    --template-file $Template `
    --parameters $ParamsFile
} else {
  Write-Host "`nRunning subscription scope what-if..." -ForegroundColor Cyan
  az deployment sub what-if `
    --location $location `
    --template-file $Template `
    --parameters $ParamsFile
}

if ($LASTEXITCODE -eq 0) {
  Write-Host "What-If finished." -ForegroundColor Green
} else {
  Write-Host "What-If failed." -ForegroundColor Red
  exit $LASTEXITCODE
}
