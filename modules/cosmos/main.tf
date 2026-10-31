# Cuenta y bases MongoDB, compuestas con acceso privado y protección de datos.
variable "prefix" { type = string }
variable "suffix" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }
variable "private_dns_zone_id" { type = string }
variable "workspace_id" { type = string }
variable "tags" { type = map(string) }
variable "settings" {
  type = object({ location = optional(string), database_name = string, mongo_server_version = string, is_serverless = bool, throughput = optional(number), max_throughput = optional(number), free_tier_enabled = bool, backup_interval_minutes = number, backup_retention_hours = number, backup_storage_redundancy = string })
}
module "account" {
  source                        = "../azure/cosmosdb"
  enable_cosmos                 = true
  name                          = "cosmos-${var.suffix}"
  resource_group_name           = var.resource_group_name
  location                      = coalesce(var.settings.location, var.location)
  kind                          = "MongoDB"
  offer_type                    = "Standard"
  mongo_server_version          = var.settings.mongo_server_version
  database_names                = [var.settings.database_name]
  is_serverless                 = var.settings.is_serverless
  throughput                    = var.settings.throughput
  max_throughput                = var.settings.max_throughput
  capabilities                  = concat(["EnableMongo"], var.settings.is_serverless ? ["EnableServerless"] : [])
  free_tier_enabled             = var.settings.free_tier_enabled
  public_network_access_enabled = false
  minimal_tls_version           = "Tls12"
  ip_range_filter               = []
  consistency_policy            = { consistency_level = "Session" }
  geo_locations                 = [{ location = coalesce(var.settings.location, var.location), failover_priority = 0, zone_redundant = false }]
  backup                        = { type = "Periodic", interval_in_minutes = var.settings.backup_interval_minutes, retention_in_hours = var.settings.backup_retention_hours, storage_redundancy = var.settings.backup_storage_redundancy }
  tags                          = var.tags
}
resource "azurerm_cosmosdb_mongo_collection" "this" {
  for_each            = toset(["requests", "activities"])
  name                = each.key
  resource_group_name = var.resource_group_name
  account_name        = "cosmos-${var.suffix}"
  database_name       = var.settings.database_name
  shard_key           = "tenant_id"
  index {
    keys   = ["_id"]
    unique = true
  }
  index { keys = ["tenant_id", "created_at"] }
  index { keys = ["tenant_id", "created_by", "created_at"] }
  depends_on = [module.account]
  lifecycle { prevent_destroy = true }
}
resource "azurerm_private_endpoint" "this" {
  name                = "${var.prefix}-cosmos-pe"
  resource_group_name = var.resource_group_name
  location            = var.location
  subnet_id           = var.subnet_id
  private_service_connection {
    name                           = "mongodb"
    private_connection_resource_id = module.account.id
    subresource_names              = ["MongoDB"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [var.private_dns_zone_id]
  }
  tags = var.tags
}
resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "audit"
  target_resource_id         = module.account.id
  log_analytics_workspace_id = var.workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "Requests" }
}
output "integration" {
  value = { id = module.account.id, account_name = "cosmos-${var.suffix}", host = "cosmos-${var.suffix}.mongo.cosmos.azure.com", name = var.settings.database_name, port = 10255, secret_name = "cosmos-mongodb-connection", readonly_secret_name = "cosmos-mongodb-readonly-connection", api = "MongoDB" }
}
output "security" { value = { public_access = false, api = "MongoDB", tls = "Tls12", shared_auth = "Key Vault", serverless = var.settings.is_serverless, retention_hours = var.settings.backup_retention_hours } }
