targetScope = 'subscription'

@description('Resource Group name')
param rgName string = 'rg-bicep-starter'

@description('Azure region for the RG')
param location string = 'centralus'

@description('Deployment classification (e.g., Lab, Demo, PoC, Prod)')
param deploymentType string = 'Lab'

@description('Creation timestamp (UTC). Defaults to now; override via parameters if desired.')
param creationDate string = utcNow()

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: rgName
  location: location
  tags: {
    DeploymentType   : deploymentType
    CreatedOn        : creationDate
    DeploymentMethod : 'Bicep Template'
    Author           : 'Anonymous'
    AuthorEmail      : 'example@example.com'
  }
}

output resourceGroupName string   = rg.name
output resourceGroupLocation string = rg.location
output tags object = rg.tags
