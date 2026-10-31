# Guardrails limitados a los RG del producto; no se alteran otras aplicaciones.
resource "azurerm_policy_definition" "private_services" {
  name         = "${local.prefix}-private-services"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "${local.prefix} servicios privados y sin IP pública"
  policy_rule = jsonencode({
    if = {
      anyOf = [
        { field = "type", equals = "Microsoft.Network/publicIPAddresses" },
        { allOf = [
          { field = "type", equals = "Microsoft.DocumentDB/databaseAccounts" },
          { field = "Microsoft.DocumentDB/databaseAccounts/publicNetworkAccess", notEquals = "Disabled" }
        ] },
        { allOf = [
          { field = "type", equals = "Microsoft.KeyVault/vaults" },
          { field = "Microsoft.KeyVault/vaults/publicNetworkAccess", notEquals = "Disabled" }
        ] },
        { allOf = [
          { field = "type", equals = "Microsoft.ContainerRegistry/registries" },
          { field = "Microsoft.ContainerRegistry/registries/publicNetworkAccess", notEquals = "Disabled" }
        ] },
        { allOf = [
          { field = "type", equals = "Microsoft.App/managedEnvironments" },
          { field = "Microsoft.App/managedEnvironments/publicNetworkAccess", notEquals = "Disabled" }
        ] }
      ]
    }
    then = { effect = "Deny" }
  })
}
resource "azurerm_resource_group_policy_assignment" "private_services" {
  for_each             = toset(["shared", "dev", "prod"])
  name                 = "private-services"
  display_name         = "${local.prefix} servicios privados"
  resource_group_id    = azurerm_resource_group.this[each.key].id
  policy_definition_id = azurerm_policy_definition.private_services.id
  # Evita carreras entre la primera creación y la propagación de Policy.
  depends_on = [module.shared]
}
