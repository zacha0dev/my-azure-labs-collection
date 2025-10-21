<#
  Cleanup script for lab resources.
  Modes:
    1) Delete a specific Resource Group by name
    2) Bulk delete all RGs with a specific tag (e.g., DeploymentType=Lab)

  Notes:
    - Uses Azure CLI (`az`)
    - Includes interactive confirmations
    - Supports --no-wait and --force (skip confirmations) flags
#>

[CmdletBinding()]
param(
  [switch]$NoWait,              # don't wait for deletions to complete
  [switch]$Force                # skip interactive confirmations
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

Write-Host "=== Lab Cleanup ===" -ForegroundColor Cyan

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

function Read-WithDefault([string]$Prompt, [string]$Default) {
  $in = Read-Host "$Prompt (default: $Default)"
  if ([string]::IsNullOrWhiteSpace($in)) { return $Default }
  return $in.Trim()
}
function Confirm-YesNo([string]$Message, [bool]$DefaultYes=$false) {
  if ($Force) { return $true }
  $suffix = $DefaultYes ? "[Y/n]" : "[y/N]"
  while ($true) {
    $resp = Read-Host "$Message $suffix"
    if ([string]::IsNullOrWhiteSpace($resp)) { return $DefaultYes }
    switch ($resp.ToLower()) {
      'y' { return $true }
      'yes' { return $true }
      'n' { return $false }
      'no' { return $false }
      default { Write-Host "Please answer y or n." -ForegroundColor Yellow }
    }
  }
}

Write-Host "Choose cleanup mode:" -ForegroundColor Cyan
Write-Host "  1) Delete ONE resource group (by name)"
Write-Host "  2) Delete ALL resource groups that match a tag (bulk)"
$mode = Read-WithDefault "Enter 1 or 2" "1"

switch ($mode) {
  '2' {
    # --- Bulk delete by tag ---
    $tagName  = Read-WithDefault "Enter tag name to match" "DeploymentType"
    $tagValue = Read-WithDefault "Enter tag value to match" "Lab"

    Write-Host "`nFinding resource groups with tag '$tagName=$tagValue'..." -ForegroundColor Cyan
    $rgsJson = az group list --query "[?tags.$tagName=='$tagValue'].{name:name,location:location}" -o json
    $rgs = @()
    if (-not [string]::IsNullOrWhiteSpace($rgsJson)) {
      $rgs = $rgsJson | ConvertFrom-Json
    }

    if (-not $rgs -or $rgs.Count -eq 0) {
      Write-Host "No resource groups found with that tag in this subscription." -ForegroundColor Yellow
      exit 0
    }

    Write-Host "`nMatched RGs:" -ForegroundColor Green
    $rgs | ForEach-Object { Write-Host ("  - {0} ({1})" -f $_.name, $_.location) }

    if (-not (Confirm-YesNo "Delete ALL of the above resource groups? This is destructive." $false)) {
      Write-Host "Cancelled." -ForegroundColor Yellow
      exit 0
    }

    foreach ($rg in $rgs) {
      Write-Host ("Deleting RG: {0}" -f $rg.name) -ForegroundColor Cyan
      $args = @('group','delete','--name',$rg.name,'--yes')
      if ($NoWait) { $args += '--no-wait' }
      az @args
      if ($LASTEXITCODE -ne 0) {
        Write-Host ("Failed to start deletion for {0}" -f $rg.name) -ForegroundColor Red
      }
    }
    Write-Host "`nBulk delete issued." -ForegroundColor Green
  }

  default {
    # --- Delete one RG by name ---
    $rgName = Read-WithDefault "Enter Resource Group name to DELETE" "rg-bicep-starter"

    # Existence check
    $exists = (az group exists --name $rgName | Out-String).Trim()
    if ($exists -ne 'true') {
      Write-Host "Resource group '$rgName' not found in this subscription." -ForegroundColor Yellow
      exit 0
    }

    Write-Host "`nAbout to delete RG: $rgName" -ForegroundColor Green
    if (-not (Confirm-YesNo "Proceed with deletion of '$rgName'?" $false)) {
      Write-Host "Cancelled." -ForegroundColor Yellow
      exit 0
    }

    $args = @('group','delete','--name',$rgName,'--yes')
    if ($NoWait) { $args += '--no-wait' }

    az @args
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Delete issued for '$rgName'." -ForegroundColor Green
    } else {
      Write-Host "Deletion failed." -ForegroundColor Red
      exit $LASTEXITCODE
    }
  }
}
