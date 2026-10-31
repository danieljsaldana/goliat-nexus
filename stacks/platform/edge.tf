# Shared entry resources exist before workloads, avoiding circular state dependencies.
locals {
  edge_enabled = var.config.public_entrypoint.enabled
  edge_origin  = local.edge_enabled ? "https://${var.config.public_entrypoint.hostname != "" ? var.config.public_entrypoint.hostname : azurerm_public_ip.waf[0].fqdn}" : ""
  edge_origins = { for key in keys(local.envs) : key => local.edge_enabled ? "https://${lookup(var.config.public_entrypoint.environment_hostnames, key, "") != "" ? var.config.public_entrypoint.environment_hostnames[key] : trimprefix(local.edge_origin, "https://")}" : "" }
}
resource "azurerm_public_ip" "waf" {
  count               = local.edge_enabled ? 1 : 0
  name                = "${local.prefix}-waf-pip"
  resource_group_name = azurerm_resource_group.this["connectivity"].name
  location            = var.config.location
  sku                 = "Standard"
  allocation_method   = "Static"
  domain_name_label   = "${var.config.name}-${substr(var.config.suffix, 0, 8)}"
  tags                = local.tags
}
resource "azurerm_key_vault" "tls" {
  count                         = local.edge_enabled ? 1 : 0
  name                          = "kv-tls-${var.config.suffix}"
  resource_group_name           = azurerm_resource_group.this["shared"].name
  location                      = var.config.location
  tenant_id                     = var.config.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  public_network_access_enabled = false
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  network_acls {
    bypass         = "AzureServices"
    default_action = "Deny"
  }
  tags = local.tags
}
resource "azurerm_user_assigned_identity" "edge" {
  for_each            = local.edge_enabled ? toset(["waf", "certificates"]) : toset([])
  name                = "${local.prefix}-${each.key}-id"
  resource_group_name = azurerm_resource_group.this["shared"].name
  location            = var.config.location
  tags                = local.tags
}
resource "azurerm_role_assignment" "tls_operator" {
  count                = local.edge_enabled ? 1 : 0
  scope                = "${azurerm_key_vault.tls[0].id}/certificates/waf-tls"
  role_definition_name = "Key Vault Certificates Officer"
  principal_id         = var.config.operator_object_id
}
resource "azurerm_role_assignment" "tls_certificate_manager" {
  count                            = local.edge_enabled ? 1 : 0
  scope                            = "${azurerm_key_vault.tls[0].id}/certificates/waf-tls"
  role_definition_name             = "Key Vault Certificates Officer"
  principal_id                     = azurerm_user_assigned_identity.edge["certificates"].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "tls_account_key" {
  count                            = local.edge_enabled ? 1 : 0
  scope                            = "${azurerm_key_vault.tls[0].id}/secrets/acme-account-key"
  role_definition_name             = "Key Vault Secrets Officer"
  principal_id                     = azurerm_user_assigned_identity.edge["certificates"].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "tls_waf" {
  count                            = local.edge_enabled ? 1 : 0
  scope                            = "${azurerm_key_vault.tls[0].id}/secrets/waf-tls"
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_user_assigned_identity.edge["waf"].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "edge_pull" {
  count                            = local.edge_enabled ? 1 : 0
  scope                            = module.shared.registry_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.edge["certificates"].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
module "edge_environment" {
  count                              = local.edge_enabled ? 1 : 0
  source                             = "../../modules/container_app_environment"
  depends_on                         = [module.network]
  prefix                             = "${local.prefix}-edge"
  location                           = var.config.location
  resource_group_name                = azurerm_resource_group.this["shared"].name
  infrastructure_subnet_id           = module.network.subnet_ids["edge-apps"]
  infrastructure_resource_group_name = "${var.config.name}-edge-aca-managed-rg"
  log_analytics_workspace_id         = module.shared.workspace_id
  vnet_ids                           = { hub = module.network.vnet_ids["hub"] }
  zone_redundancy                    = false
  tags                               = local.tags
}
resource "azurerm_storage_container" "certificate_locks" {
  count                 = local.edge_enabled ? 1 : 0
  name                  = "certificate-locks"
  storage_account_id    = var.foundation.storage_account_id
  container_access_type = "private"
}
resource "azurerm_role_assignment" "certificate_locks" {
  count                            = local.edge_enabled ? 1 : 0
  scope                            = "${var.foundation.storage_account_id}/blobServices/default/containers/certificate-locks"
  role_definition_name             = "Storage Blob Data Contributor"
  principal_id                     = azurerm_user_assigned_identity.edge["certificates"].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_monitor_diagnostic_setting" "tls" {
  count                      = local.edge_enabled ? 1 : 0
  name                       = "audit"
  target_resource_id         = azurerm_key_vault.tls[0].id
  log_analytics_workspace_id = module.shared.workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}
