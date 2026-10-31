# Procesamiento privado de solicitudes mediante Azure Functions Flex.
variable "prefix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "settings" { type = object({ runtime_version = string, maximum_instances = number, memory_mb = number }) }
variable "identity" { type = object({ id = string, client_id = string, principal_id = string }) }
variable "subnet_id" { type = string }
variable "endpoint_subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "tenant_id" { type = string }
variable "vault" { type = object({ id = string, uri = string }) }
variable "host_vault" { type = object({ id = string, uri = string }) }
variable "storage" { type = object({ id = string, name = string, blob_uri = string, queue_uri = string, table_uri = string }) }
variable "cosmos" { type = object({ name = string, secret_name = string, host = string }) }
variable "workspace_id" { type = string }
variable "tags" { type = map(string) }
resource "azurerm_service_plan" "this" {
  name                = "${var.prefix}-events-plan"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = var.tags
}
resource "azurerm_application_insights" "this" {
  name                         = "${var.prefix}-events-insights"
  resource_group_name          = var.resource_group_name
  location                     = var.location
  workspace_id                 = var.workspace_id
  application_type             = "web"
  local_authentication_enabled = false
  tags                         = var.tags
}
resource "azurerm_role_assignment" "host_keys" {
  scope                            = var.host_vault.id
  role_definition_name             = "Key Vault Secrets Officer"
  principal_id                     = var.identity.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "cosmos_secret" {
  scope                            = "${var.vault.id}/secrets/${var.cosmos.secret_name}"
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = var.identity.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "storage" {
  for_each                         = toset(["Storage Blob Data Owner", "Storage Queue Data Contributor", "Storage Table Data Contributor"])
  scope                            = var.storage.id
  role_definition_name             = each.value
  principal_id                     = var.identity.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "monitor" {
  scope                            = azurerm_application_insights.this.id
  role_definition_name             = "Monitoring Metrics Publisher"
  principal_id                     = var.identity.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_function_app_flex_consumption" "this" {
  name                                           = "${var.prefix}-events"
  resource_group_name                            = var.resource_group_name
  location                                       = var.location
  service_plan_id                                = azurerm_service_plan.this.id
  storage_container_type                         = "blobContainer"
  storage_container_endpoint                     = "${var.storage.blob_uri}deployments"
  storage_authentication_type                    = "UserAssignedIdentity"
  storage_user_assigned_identity_id              = var.identity.id
  runtime_name                                   = "node"
  runtime_version                                = var.settings.runtime_version
  maximum_instance_count                         = var.settings.maximum_instances
  instance_memory_in_mb                          = var.settings.memory_mb
  virtual_network_subnet_id                      = var.subnet_id
  public_network_access_enabled                  = false
  webdeploy_publish_basic_authentication_enabled = false
  https_only                                     = true
  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity.id]
  }
  app_settings = {
    AUTH_TENANT_ID                            = var.tenant_id
    AzureWebJobsStorage__blobServiceUri       = var.storage.blob_uri
    AzureWebJobsStorage__queueServiceUri      = var.storage.queue_uri
    AzureWebJobsStorage__tableServiceUri      = var.storage.table_uri
    AzureWebJobsStorage__credential           = "managedidentity"
    AzureWebJobsStorage__clientId             = var.identity.client_id
    Events__queueServiceUri                   = var.storage.queue_uri
    Events__credential                        = "managedidentity"
    Events__clientId                          = var.identity.client_id
    AzureWebJobsSecretStorageType             = "keyvault"
    AzureWebJobsSecretStorageKeyVaultUri      = var.host_vault.uri
    AzureWebJobsSecretStorageKeyVaultClientId = var.identity.client_id
    AZURE_CLIENT_ID                           = var.identity.client_id
    KEY_VAULT_URI                             = var.vault.uri
    COSMOS_SECRET_NAME                        = var.cosmos.secret_name
    COSMOS_DATABASE                           = var.cosmos.name
    COSMOS_HOST                               = var.cosmos.host
    EVENTS_QUEUE_URI                          = var.storage.queue_uri
    EVENTS_QUEUE_NAME                         = "requests-events"
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING = "ClientId=${var.identity.client_id};Authorization=AAD"
  }
  site_config {
    application_insights_connection_string = azurerm_application_insights.this.connection_string
    http2_enabled                          = true
    minimum_tls_version                    = "1.2"
    vnet_route_all_enabled                 = true
  }
  tags       = var.tags
  depends_on = [azurerm_role_assignment.storage, azurerm_role_assignment.host_keys, azurerm_role_assignment.cosmos_secret]
}
resource "azurerm_private_endpoint" "this" {
  name                = "${var.prefix}-events-pe"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.endpoint_subnet_id
  private_service_connection {
    name                           = "functions"
    private_connection_resource_id = azurerm_function_app_flex_consumption.this.id
    subresource_names              = ["sites"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
  tags = var.tags
}
output "integration" { value = { name = azurerm_function_app_flex_consumption.this.name, hostname = azurerm_function_app_flex_consumption.this.default_hostname, resource_group = var.resource_group_name } }

output "security" {
  value = {
    public_access   = azurerm_function_app_flex_consumption.this.public_network_access_enabled
    basic_auth      = azurerm_function_app_flex_consumption.this.webdeploy_publish_basic_authentication_enabled
    deployment_auth = azurerm_function_app_flex_consumption.this.storage_authentication_type
    runtime         = azurerm_function_app_flex_consumption.this.runtime_name
    host_keys       = azurerm_function_app_flex_consumption.this.app_settings["AzureWebJobsSecretStorageType"]
    secret_scope    = azurerm_role_assignment.cosmos_secret.scope
  }
}
