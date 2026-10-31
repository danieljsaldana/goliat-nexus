locals {
  zones = { vault = "privatelink.vaultcore.azure.net", registry = "privatelink.azurecr.io", state = "privatelink.blob.core.windows.net", cosmos = "privatelink.mongo.cosmos.azure.com", queue = "privatelink.queue.core.windows.net", table = "privatelink.table.core.windows.net", functions = "privatelink.azurewebsites.net", events = "privatelink.eventgrid.azure.net" }
  service_fqdns = { for key, env in local.envs : key => concat(
    env.enable_key_vault ? ["kv-lz-${env.suffix}.vault.azure.net"] : [],
    env.enable_event_processing ? ["kv-lz-${env.suffix}h.vault.azure.net", "${var.config.name}-${key}-${env.suffix}-events.azurewebsites.net", "${var.config.name}-${key}-${env.suffix}-events.scm.azurewebsites.net"] : [],
    env.enable_storage_account ? [for kind in ["blob", "queue", "table"] : "stapp${env.suffix}.${kind}.core.windows.net"] : [],
    env.enable_content_storage ? ["stcontent${env.suffix}.blob.core.windows.net"] : [],
  env.enable_event_grid ? ["*.${var.config.location}-1.eventgrid.azure.net"] : []) }
  private_services = merge({
    registry = { resource_id = module.shared.registry_id, group_id = "registry", zone = "registry", subnet = "endpoints" }
    state    = { resource_id = var.foundation.storage_account_id, group_id = "blob", zone = "state", subnet = "endpoints" }
    }, { for key, vault in azurerm_key_vault.tls : "tls" => { resource_id = vault.id, group_id = "vault", zone = "vault", subnet = "endpoints" } }, {
    }, { for key, vault in module.vault : "${key}-vault" => { resource_id = vault.id, group_id = "vault", zone = "vault", subnet = "${key}-data" } },
    { for key, vault in module.host_vault : "${key}-host-vault" => { resource_id = vault.id, group_id = "vault", zone = "vault", subnet = "${key}-data" } },
    merge([for key, store in module.storage : { for kind in ["blob", "queue", "table"] : "${key}-${kind}" => { resource_id = store.id, group_id = kind, zone = kind == "blob" ? "state" : kind, subnet = "${key}-data" } }]...),
    { for key, store in module.content : "${key}-content" => { resource_id = store.id, group_id = "blob", zone = "state", subnet = "${key}-data" } },
  { for key, topic in module.events : "${key}-events" => { resource_id = topic.id, group_id = "topic", zone = "events", subnet = "${key}-data" } })
  dns_links = { for item in setproduct(keys(local.zones), ["hub", "dev", "prod"]) : "${item[0]}-${item[1]}" => { zone = item[0], vnet = item[1] } }
}
module "network" {
  source                 = "../../modules/network"
  prefix                 = local.prefix
  resource_group_name    = azurerm_resource_group.this["connectivity"].name
  location               = var.config.location
  network                = var.config.network
  environments           = local.envs
  management_https_fqdns = var.config.management_https_fqdns
  workspace_id           = module.shared.workspace_id
  shared_service_fqdns   = ["acrlz${var.config.suffix}.azurecr.io", "acrlz${var.config.suffix}.${var.config.location}.data.azurecr.io", "kv-tls-${var.config.suffix}.vault.azure.net"]
  service_fqdns          = local.service_fqdns
  edge_public_hostnames  = local.edge_enabled ? distinct(concat([azurerm_public_ip.waf[0].fqdn, trimprefix(local.edge_origin, "https://")], [for origin in values(local.edge_origins) : trimprefix(origin, "https://")])) : []
  state_fqdn             = "${var.foundation.storage_account_name}.blob.core.windows.net"
  tags                   = local.tags
}
resource "azurerm_private_dns_zone" "this" {
  for_each            = local.zones
  name                = each.value
  resource_group_name = azurerm_resource_group.this["connectivity"].name
  tags                = local.tags
}
resource "azurerm_private_dns_zone_virtual_network_link" "this" {
  for_each = local.dns_links
  name     = each.key

  private_dns_zone_id  = azurerm_private_dns_zone.this[each.value.zone].id
  virtual_network_id   = module.network.vnet_ids[each.value.vnet]
  registration_enabled = false
  tags                 = local.tags
}
resource "azurerm_private_endpoint" "this" {
  for_each            = local.private_services
  name                = "${local.prefix}-${each.key}-pe"
  resource_group_name = azurerm_resource_group.this["connectivity"].name
  location            = var.config.location
  subnet_id           = module.network.subnet_ids[each.value.subnet]
  private_service_connection {
    name                           = each.key
    private_connection_resource_id = each.value.resource_id
    subresource_names              = [each.value.group_id]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.this[each.value.zone].id]
  }
  tags = local.tags
}
module "events" {
  for_each                      = { for key, env in local.envs : key => env if env.enable_event_grid }
  source                        = "../../modules/azure/event_grid"
  name                          = "${var.config.name}-${each.key}-integrations"
  location                      = var.config.location
  resource_group_name           = azurerm_resource_group.this[each.key].name
  public_network_access_enabled = false
  local_auth_enabled            = false
  eventgrid_identity_id         = azurerm_user_assigned_identity.app["${each.key}-tenant"].id
  backend_principal_id          = azurerm_user_assigned_identity.app["${each.key}-tenant"].principal_id
  tags                          = local.tags
}
