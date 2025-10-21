[<- Go Back](../README.md)

# Bicep Doc 

> Official Microsoft Docs on Bicep are located here: [Bicep documentation | Microsoft Learn](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)

## What is Bicep? 
**Bicep** is a domain-specific language (DSL) for deploying Azure resources using **declarative syntax**. In a Bicep file, you describe *what* you want to deploy - not *how* - and Azure handles the rest. 
> *Source:* [Microsoft Learn - Bicep Overview](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/)

## Bicep Labs 
This repo includes hands-on labs that teach you how to:

| Lab | Description |
|------|--------------|
| [**Resource Group Lab**](..\bicep\resource-group\README.md) | A simple starting point that deploys a Resource Group using Bicep. Useful for validating your local setup and Azure subscription connectivity. |
| **Custom Services Labs** *(coming soon)* | Expand into deploying additional resources (Storage, Networking, etc.) once your Bicep workflow is solid. |

Each lab includes:
- A **main.bicep** file (core template)
- A **parameters/main.json** (values for each run)
- **PowerShell scripts** for `deploy`, `whatif`, and `cleanup`

## Setup Bicep
- Installation Requirements: [Install Bicep tools](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/install)
- `az bicep install`

## Command References 
- [Bicep CLI commands](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/bicep-cli?tabs=bicep-cli)

