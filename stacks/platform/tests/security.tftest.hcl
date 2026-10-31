mock_provider "azuread" {
  mock_data "azuread_client_config" {
    defaults = { object_id = "33333333-3333-4333-8333-333333333333", tenant_id = "22222222-2222-4222-8222-222222222222", client_id = "44444444-4444-4444-8444-444444444444" }
  }
}
mock_provider "azurerm" {}
variable "config" { type = any }
run "private_platform" {
  command = plan
  assert {
    condition     = length(module.cosmos) == 2 && alltrue([for db in module.cosmos : !db.security.public_access && db.security.api == "MongoDB"])
    error_message = "Cosmos MongoDB debe ser privado en Dev y Prod."
  }
  assert {
    condition     = alltrue([for vault in module.vault : !vault.security.public && vault.security.rbac && vault.security.purge]) && length(module.host_vault) == 2
    error_message = "Vaults de aplicación y host privados y separados."
  }
  assert {
    condition     = !module.shared.security.acr_public && !module.shared.security.acr_admin && module.shared.security.acr_sku == "Premium"
    error_message = "El ACR compartido debe ser privado y usar identidades."
  }
  assert {
    condition     = length(module.web) == 4 && length(azurerm_user_assigned_identity.app) == 10 && length(azurerm_role_assignment.app_pull) == 8
    error_message = "Los portales y roles habilitados deben tener recursos propios."
  }
  assert {
    condition     = length(module.network.security.inbound_deny) == 9 && alltrue([for action in module.network.security.outbound_deny : action == "Deny"])
    error_message = "Nueve subredes protegidas, incluyendo Functions, deniegan por defecto."
  }
  assert {
    condition     = toset(module.network.security.hub_peers) == toset(["dev", "prod"]) && module.network.security.allowed_flows["dev_cosmos_out"].destination != module.network.security.allowed_flows["prod_cosmos_out"].destination
    error_message = "Dos spokes consumen un hub y mantienen destinos de datos distintos."
  }
  assert {
    condition     = length(azurerm_private_dns_zone.this) == 8 && length(azurerm_private_dns_zone_virtual_network_link.this) == 24 && length(azurerm_private_endpoint.this) == 14 + (var.config.public_entrypoint.enabled ? 1 : 0)
    error_message = "Zonas privadas centrales y endpoints independientes de cada entorno."
  }
  assert {
    condition     = module.budget.amount == var.config.operations.budget_amount && module.budget.notification_count == 3
    error_message = "El presupuesto común debe generar los tres avisos."
  }
  assert {
    condition     = length(module.application_identity) == 2 && alltrue([for identity in module.application_identity : identity.security.audience == "AzureADMyOrg" && identity.security.assigned_users_only && identity.security.portal_assigned_users_only && identity.security.access_token_version == 2])
    error_message = "Cada entorno requiere Entra single-tenant, asignación explícita de usuarios y tokens v2."
  }

}
run "only_landing_zone" {
  command = plan
  variables {
    config = merge(var.config, { public_entrypoint = merge(var.config.public_entrypoint, { enabled = false }), environments = { for key, env in var.config.environments : key => merge(env, { web_portals = {}, enable_api_platform = false, enable_api_tenant = false, enable_api_activities = false, enable_cosmosdb = false, enable_key_vault = false, enable_event_processing = false, enable_storage_account = false, enable_content_storage = false }) } })
  }
  assert {
    condition     = length(module.cosmos) == 0 && length(module.web) == 0 && length(module.vault) == 0 && length(azurerm_user_assigned_identity.app) == 0 && length(azurerm_private_endpoint.this) == 2
    error_message = "Las piezas de la aplicación deben poder omitirse sin eliminar el hub."
  }
}
run "additional_portal_without_another_hub" {
  command = plan
  variables {
    config = merge(var.config, { public_entrypoint = merge(var.config.public_entrypoint, { enabled = false }), environments = merge(var.config.environments, { dev = merge(var.config.environments.dev, { web_portals = merge(var.config.environments.dev.web_portals, { support = { view = "tenant" } }) }) }) })
  }
  assert {
    condition     = length(module.web) == 5 && contains(keys(module.web), "dev-support") && output.integration.environments.dev.webs["support"].view == "tenant" && length(module.application_identity) == 2 && toset(module.network.security.hub_peers) == toset(["dev", "prod"])
    error_message = "Se debe poder añadir un portal sin duplicar el hub ni la identidad por entorno."
  }
}
