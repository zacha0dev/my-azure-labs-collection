[<- Go Home](../../README.md)

# Resource Group Bicep Deployment

Creates a Resource Group at **subscription scope** with generic tags:
- `DeploymentType` (Lab/Demo/PoC/Prod)
- `CreatedOn` (UTC timestamp)
- `DeploymentMethod` = "Bicep Template"
- `Author`, `AuthorEmail` = placeholders

## Prereqs
- Azure CLI (`az`)
- Bicep available (`az bicep version`)
- Logged in and subscription selected:
  ```powershell
  az login --use-device-code
  az account set --subscription "<SUBSCRIPTION-ID-OR-NAME>"
