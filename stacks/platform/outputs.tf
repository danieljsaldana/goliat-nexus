output "integration" {
  description = "Contratos sin valores secretos. Cosmos y tokens web se registran en Key Vault con secrets-sync."
  value = {
    registry_login_server = module.shared.registry_login_server
    workspace_id          = module.shared.workspace_id
    firewall_private_ip   = module.network.firewall_private_ip
    public_entrypoint = local.edge_enabled ? {
      origin                     = local.edge_origin
      environment_origins        = local.edge_origins
      public_ip_id               = azurerm_public_ip.waf[0].id
      public_ip                  = azurerm_public_ip.waf[0].ip_address
      azure_hostname             = azurerm_public_ip.waf[0].fqdn
      gateway_subnet_id          = module.network.subnet_ids["gateway"]
      gateway_subnet_cidr        = var.config.network.gateway_subnet_cidr
      resource_group_name        = azurerm_resource_group.this["connectivity"].name
      shared_resource_group_name = azurerm_resource_group.this["shared"].name
      workspace_id               = module.shared.workspace_id
      vault                      = { id = azurerm_key_vault.tls[0].id, name = azurerm_key_vault.tls[0].name, uri = azurerm_key_vault.tls[0].vault_uri }
      identities                 = { for key, value in azurerm_user_assigned_identity.edge : key => { id = value.id, client_id = value.client_id, principal_id = value.principal_id } }
      lock_blob_url              = "https://${var.foundation.storage_account_name}.blob.core.windows.net/certificate-locks/renewal.lock"
      environment_id             = module.edge_environment[0].id
      environment_domain         = module.edge_environment[0].default_domain
    } : null
    environments = { for key, env in local.envs : key => {
      workload_resource_group     = azurerm_resource_group.this[key].name
      connectivity_resource_group = azurerm_resource_group.this["connectivity"].name
      workspace_id                = module.shared.workspace_id
      apps_subnet_id              = module.network.subnet_ids["${key}-apps"]
      functions_subnet_id         = module.network.subnet_ids["${key}-functions"]
      endpoint_subnet_id          = module.network.subnet_ids["${key}-data"]
      functions_dns_zone_id       = azurerm_private_dns_zone.this["functions"].id
      vnet_ids                    = { for name in ["hub", key] : name => module.network.vnet_ids[name] }
      identities                  = { for role in local.app_roles[key] : role => { id = azurerm_user_assigned_identity.app["${key}-${role}"].id, client_id = azurerm_user_assigned_identity.app["${key}-${role}"].client_id, principal_id = azurerm_user_assigned_identity.app["${key}-${role}"].principal_id } }
      public_origin               = lookup(local.edge_origins, key, "")
      gateway_subnet_cidr         = var.config.network.gateway_subnet_cidr
      public_entrypoint_ip        = try(azurerm_public_ip.waf[0].ip_address, "")
      registry_login_server       = module.shared.registry_login_server
      vault                       = try({ id = module.vault[key].id, uri = module.vault[key].uri, name = "kv-lz-${env.suffix}" }, null)
      host_vault                  = try({ id = module.host_vault[key].id, uri = module.host_vault[key].uri }, null)
      cosmos                      = try(module.cosmos[key].integration, null)
      storage                     = try({ id = module.storage[key].id, name = module.storage[key].name, blob_uri = module.storage[key].blob_uri, queue_uri = module.storage[key].queue_uri, table_uri = module.storage[key].table_uri }, null)
      content                     = try({ id = module.content[key].id, blob_uri = module.content[key].blob_uri }, null)
      webs                        = { for name, web in local.webs : web.role => { name = "${var.config.name}-${name}", hostname = module.web[name].default_host_name, view = web.view, public_url = local.edge_enabled ? "${local.edge_origins[key]}/${key}/${web.role}/" : "https://${module.web[name].default_host_name}/" } if web.environment == key }
      auth                        = try(module.application_identity[key].integration, null)

      events_endpoint        = try(module.events[key].endpoint, "")
      publisher_client_id    = try(module.federation[key].client_id, null)
      firewall_private_ip    = module.network.firewall_private_ip
      action_group_id        = azurerm_monitor_action_group.operations.id
      managed_resource_group = "${var.config.name}-${key}-aca-managed-rg"
    } }
  }
}
