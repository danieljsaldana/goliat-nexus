locals {
  envs       = var.config.environments
  vaults     = { for key, env in local.envs : key => env if env.enable_key_vault }
  cores      = { for key, env in local.envs : key => env if env.enable_storage_account }
  contents   = { for key, env in local.envs : key => env if env.enable_content_storage }
  event_envs = { for key, env in local.envs : key => env if env.enable_event_processing }
  app_roles  = { for key, env in local.envs : key => concat(anytrue([env.enable_api_platform, env.enable_api_tenant, env.enable_api_activities]) ? ["frontend"] : [], [for role in ["platform", "tenant", "activities"] : role if env["enable_api_${role}"]], env.enable_event_processing ? ["functions"] : []) }
  apps       = merge([for key, roles in local.app_roles : { for role in roles : "${key}-${role}" => { environment = key, role = role } }]...)
  webs       = merge([for key, env in local.envs : { for portal_id, portal in env.web_portals : "${key}-${portal_id}" => { environment = key, role = portal_id, view = portal.view } }]...)
}
module "vault" {
  for_each            = local.vaults
  source              = "../../modules/vault"
  prefix              = "${var.config.name}-${each.key}"
  suffix              = each.value.suffix
  resource_group_name = azurerm_resource_group.this[each.key].name
  location            = var.config.location
  tenant_id           = var.config.tenant_id
  operator_object_id  = var.config.operator_object_id
  workspace_id        = module.shared.workspace_id
  tags                = merge(local.tags, { Environment = each.key })
}
module "host_vault" {
  for_each            = local.event_envs
  source              = "../../modules/vault"
  prefix              = "${var.config.name}-${each.key}-host"
  suffix              = "${each.value.suffix}h"
  resource_group_name = azurerm_resource_group.this[each.key].name
  location            = var.config.location
  tenant_id           = var.config.tenant_id
  operator_object_id  = var.config.operator_object_id
  workspace_id        = module.shared.workspace_id
  tags                = merge(local.tags, { Environment = each.key, Purpose = "Functions host keys" })
}
module "storage" {
  for_each                  = local.cores
  source                    = "../../modules/azure/storage_account"
  name                      = "stapp${each.value.suffix}"
  resource_group_name       = azurerm_resource_group.this[each.key].name
  location                  = var.config.location
  replication               = each.value.storage.replication
  soft_delete_days          = each.value.storage.soft_delete_days
  shared_access_key_enabled = false
  containers                = ["deployments"]
  queues                    = ["requests-events", "requests-events-poison"]
  tags                      = merge(local.tags, { Environment = each.key })
}
module "content" {
  for_each                  = local.contents
  source                    = "../../modules/azure/storage_account"
  name                      = "stcontent${each.value.suffix}"
  resource_group_name       = azurerm_resource_group.this[each.key].name
  location                  = var.config.location
  replication               = each.value.storage.replication
  soft_delete_days          = each.value.storage.soft_delete_days
  shared_access_key_enabled = false
  containers                = ["attachments"]
  last_access_time_enabled  = true
  enable_lifecycle_policy   = true
  lifecycle_days            = each.value.storage.content_cool_after_days
  tags                      = merge(local.tags, { Environment = each.key })
}
module "cosmos" {
  for_each            = { for key, env in local.envs : key => env if env.enable_cosmosdb }
  source              = "../../modules/cosmos"
  prefix              = "${var.config.name}-${each.key}"
  suffix              = each.value.suffix
  resource_group_name = azurerm_resource_group.this[each.key].name
  location            = var.config.location
  subnet_id           = module.network.subnet_ids["${each.key}-data"]
  private_dns_zone_id = azurerm_private_dns_zone.this["cosmos"].id
  workspace_id        = module.shared.workspace_id
  settings            = each.value.cosmosdb_config
  tags                = merge(local.tags, { Environment = each.key })
}
module "web" {
  for_each            = local.webs
  source              = "../../modules/azure/static_web_apps"
  name                = "${var.config.name}-${each.key}"
  resource_group_name = azurerm_resource_group.this[each.value.environment].name
  location            = local.envs[each.value.environment].web.location
  sku_tier            = local.envs[each.value.environment].web.sku
  sku_size            = local.envs[each.value.environment].web.sku
  tags                = merge(local.tags, { Environment = each.value.environment, Role = each.value.role })
}
module "dns" {
  for_each            = { for key, env in local.envs : key => env if env.enable_dns && env.public_dns.zone_name != "" }
  source              = "../../modules/azure/dns"
  domain_name         = each.value.public_dns.zone_name
  create_zone         = each.value.public_dns.create_zone
  resource_group_name = azurerm_resource_group.this[each.key].name
  cname_records       = { for name, web in local.webs : "${each.key}-${web.role}" => { record_value = module.web[name].default_host_name } if web.environment == each.key }
  tags                = local.tags
}
resource "azurerm_user_assigned_identity" "app" {
  for_each            = local.apps
  name                = "${var.config.name}-${each.key}-id"
  resource_group_name = azurerm_resource_group.this[each.value.environment].name
  location            = var.config.location
  tags                = merge(local.tags, { Environment = each.value.environment })
}
resource "azurerm_role_assignment" "app_pull" {
  for_each                         = { for key, app in local.apps : key => app if app.role != "functions" }
  scope                            = module.shared.registry_id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.app[each.key].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
module "federation" {
  for_each            = { for key, env in local.envs : key => env if env.github_repository != "" && env.enable_api_tenant }
  source              = "../../modules/federation"
  prefix              = "${var.config.name}-${each.key}"
  resource_group_name = azurerm_resource_group.this[each.key].name
  resource_group_id   = azurerm_resource_group.this[each.key].id
  location            = var.config.location
  github_repository   = each.value.github_repository
  github_environment  = each.value.github_environment
  registry_id         = module.shared.registry_id
  app_identity_id     = azurerm_user_assigned_identity.app["${each.key}-tenant"].id
  tags                = local.tags
}
module "application_identity" {
  for_each           = { for key, env in local.envs : key => env if anytrue([env.enable_api_platform, env.enable_api_tenant, env.enable_api_activities]) }
  source             = "../../modules/application_identity"
  prefix             = "${var.config.name}-${each.key}"
  tenant_id          = var.config.tenant_id
  operator_object_id = var.config.operator_object_id
  access             = each.value.access
  redirect_uris      = flatten([for name, web in local.webs : local.edge_enabled ? ["${local.edge_origins[each.key]}/${each.key}/${web.role}/redirect/", "${local.edge_origins[each.key]}/${each.key}/${web.role}/"] : ["https://${module.web[name].default_host_name}/redirect/", "https://${module.web[name].default_host_name}/"] if web.environment == each.key])
}
