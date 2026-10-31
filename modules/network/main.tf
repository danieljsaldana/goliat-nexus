# Un hub y dos spokes, sin peering Dev <-> Prod.
locals {
  vnets = merge({ hub = var.network.hub_cidr }, { for key, env in var.environments : key => env.network.vnet_cidr })
  subnets = merge({
    firewall   = { vnet = "hub", name = "AzureFirewallSubnet", cidr = var.network.firewall_subnet_cidr }
    management = { vnet = "hub", name = "management", cidr = var.network.management_subnet_cidr }
    endpoints  = { vnet = "hub", name = "shared-private-endpoints", cidr = var.network.endpoints_subnet_cidr }
    gateway    = { vnet = "hub", name = "application-gateway", cidr = var.network.gateway_subnet_cidr }
    edge-apps  = { vnet = "hub", name = "edge-services", cidr = var.network.edge_apps_subnet_cidr }
    }, merge([for key, env in var.environments : {
      "${key}-apps"      = { vnet = key, name = "container-apps", cidr = env.network.apps_subnet_cidr }
      "${key}-data"      = { vnet = key, name = "data-private-endpoints", cidr = env.network.data_subnet_cidr }
      "${key}-functions" = { vnet = key, name = "functions-integration", cidr = env.network.functions_subnet_cidr }
  }]...))
  protected = { for key, subnet in local.subnets : key => subnet if !contains(["firewall", "gateway"], key) }
  routes = merge({
    management = merge({ endpoints = var.network.endpoints_subnet_cidr }, { for key, env in var.environments : key => env.network.vnet_cidr })
    endpoints  = { for key, env in var.environments : key => env.network.vnet_cidr }
    edge-apps  = { endpoints = var.network.endpoints_subnet_cidr }
    }, merge([for key, env in var.environments : {
      "${key}-apps"      = { endpoints = var.network.endpoints_subnet_cidr, data = env.network.data_subnet_cidr }
      "${key}-functions" = { endpoints = var.network.endpoints_subnet_cidr, data = env.network.data_subnet_cidr }
      "${key}-data"      = { apps = env.network.apps_subnet_cidr, functions = env.network.functions_subnet_cidr }
  }]...))
}
resource "azurerm_virtual_network" "this" {
  for_each            = local.vnets
  name                = "${var.prefix}-${each.key}-vnet"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [each.value]
  tags                = var.tags
}

resource "azurerm_subnet" "this" {
  for_each                          = local.subnets
  name                              = each.value.name
  resource_group_name               = var.resource_group_name
  virtual_network_name              = azurerm_virtual_network.this[each.value.vnet].name
  address_prefixes                  = [each.value.cidr]
  private_endpoint_network_policies = (each.key == "endpoints" || endswith(each.key, "-data")) ? "Enabled" : "Disabled"
  default_outbound_access_enabled   = false
  dynamic "delegation" {
    for_each = (endswith(each.key, "-apps") || endswith(each.key, "-functions")) ? [1] : []
    content {
      name = "container-apps"
      service_delegation {
        name    = "Microsoft.App/environments"
        actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
      }
    }
  }
}

# Peering no transitivo: no hay emparejamiento directo Dev <-> Prod.
resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  for_each                  = toset(keys(var.environments))
  name                      = "hub-to-${each.key}"
  resource_group_name       = var.resource_group_name
  virtual_network_name      = azurerm_virtual_network.this["hub"].name
  remote_virtual_network_id = azurerm_virtual_network.this[each.key].id
  allow_forwarded_traffic   = true
}
resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  for_each                  = toset(keys(var.environments))
  name                      = "${each.key}-to-hub"
  resource_group_name       = var.resource_group_name
  virtual_network_name      = azurerm_virtual_network.this[each.key].name
  remote_virtual_network_id = azurerm_virtual_network.this["hub"].id
  allow_forwarded_traffic   = true
}

resource "azurerm_public_ip" "firewall" {
  name                = "${var.prefix}-firewall-pip"
  resource_group_name = var.resource_group_name
  location            = var.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}
resource "azurerm_firewall_policy" "this" {
  name                     = "${var.prefix}-firewall-policy"
  resource_group_name      = var.resource_group_name
  location                 = var.location
  sku                      = "Standard"
  threat_intelligence_mode = "Deny"
  # SNAT también en las reglas de red privadas para conservar el retorno.
  private_ip_ranges = ["255.255.255.255/32"]
  dns {
    proxy_enabled = true
  }
  tags = var.tags
}
resource "azurerm_firewall" "this" {
  name                = "${var.prefix}-firewall"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_name            = "AZFW_VNet"
  sku_tier            = "Standard"
  firewall_policy_id  = azurerm_firewall_policy.this.id
  ip_configuration {
    name                 = "primary"
    subnet_id            = azurerm_subnet.this["firewall"].id
    public_ip_address_id = azurerm_public_ip.firewall.id
  }
  tags = var.tags
}

resource "azurerm_virtual_network_dns_servers" "this" {
  for_each           = local.vnets
  virtual_network_id = azurerm_virtual_network.this[each.key].id
  dns_servers        = [azurerm_firewall.this.ip_configuration[0].private_ip_address]
}


resource "azurerm_route_table" "this" {
  for_each            = local.protected
  name                = "${var.prefix}-${each.key}-rt"
  resource_group_name = var.resource_group_name
  location            = var.location
  route {
    name                   = "egress-via-firewall"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = azurerm_firewall.this.ip_configuration[0].private_ip_address
  }
  dynamic "route" {
    for_each = local.routes[each.key]
    content {
      name                   = "to-${route.key}-via-firewall"
      address_prefix         = route.value
      next_hop_type          = "VirtualAppliance"
      next_hop_in_ip_address = azurerm_firewall.this.ip_configuration[0].private_ip_address
    }
  }
  tags = var.tags
}
resource "azurerm_subnet_route_table_association" "this" {
  for_each       = azurerm_route_table.this
  subnet_id      = azurerm_subnet.this[each.key].id
  route_table_id = each.value.id
}

resource "azurerm_firewall_policy_rule_collection_group" "this" {
  name               = "shared-hub-allowlist"
  firewall_policy_id = azurerm_firewall_policy.this.id
  priority           = 200
  application_rule_collection {
    name     = "management-control-plane"
    priority = 250
    action   = "Allow"
    rule {
      name             = "operator-and-private-runners"
      source_addresses = [var.network.management_subnet_cidr]
      destination_fqdns = concat([
        "deb.debian.org", "security.debian.org", "management.azure.com", "login.microsoft.com", "login.microsoftonline.com", "*.login.microsoftonline.com",
        "graph.microsoft.com", "registry.terraform.io", "releases.hashicorp.com", "checkpoint-api.hashicorp.com",
        "github.com", "api.github.com", "*.actions.githubusercontent.com", "*.githubusercontent.com",
        "registry-1.docker.io", "auth.docker.io", "production.cloudflare.docker.com", "production.cloudfront.docker.com",
        "pypi.org", "files.pythonhosted.org", "registry.npmjs.org", "*.scm.azurewebsites.net", "*.azurestaticapps.net", "*.azurewebsites.net"
      ], var.management_https_fqdns, var.edge_public_hostnames)
      protocols {
        type = "Https"
        port = 443
      }
    }
    rule {
      name              = "operator-private-services"
      source_addresses  = [var.network.management_subnet_cidr]
      destination_fqdns = concat(var.shared_service_fqdns, flatten(values(var.service_fqdns)), [var.state_fqdn])
      protocols {
        type = "Https"
        port = 443
      }
    }
  }
  application_rule_collection {
    name     = "environment-private-services"
    priority = 150
    action   = "Allow"
    dynamic "rule" {
      for_each = var.environments
      content {
        name              = "${rule.key}-own-vault-and-shared-registry"
        source_addresses  = [rule.value.network.apps_subnet_cidr, rule.value.network.functions_subnet_cidr]
        destination_fqdns = concat(var.shared_service_fqdns, var.service_fqdns[rule.key])
        protocols {
          type = "Https"
          port = 443
        }
      }
    }
  }
  application_rule_collection {
    name     = "container-platform-https"
    priority = 200
    action   = "Allow"
    dynamic "rule" {
      for_each = var.environments
      content {
        name             = "${rule.key}-required-services"
        source_addresses = [rule.value.network.apps_subnet_cidr, rule.value.network.functions_subnet_cidr]
        destination_fqdns = concat([
          "mcr.microsoft.com", "*.data.mcr.microsoft.com", "mcr-0001.mcr-msedge.net",
          "packages.aks.azure.com", "acs-mirror.azureedge.net", "login.microsoft.com", "*.login.microsoft.com",
          "login.microsoftonline.com", "*.login.microsoftonline.com", "*.identity.azure.net", "*.msidentity.com", "*.msauth.net",
          "*.ods.opinsights.azure.com", "*.oms.opinsights.azure.com", "*.monitoring.azure.com", "*.monitor.azure.com"
        ], rule.value.additional_https_fqdns)
        protocols {
          type = "Https"
          port = 443
        }
      }
    }
  }
  dynamic "application_rule_collection" {
    for_each = anytrue([for env in var.environments : env.enable_event_processing]) ? [1] : []
    content {
      name     = "functions-extension-bundles"
      priority = 210
      action   = "Allow"
      rule {
        name              = "official-functions-runtime-cdn"
        source_addresses  = [for env in var.environments : env.network.functions_subnet_cidr if env.enable_event_processing]
        destination_fqdns = ["cdn.functions.azure.com"]
        protocols {
          type = "Https"
          port = 443
        }
      }
    }
  }
  application_rule_collection {
    name     = "edge-certificate-service"
    priority = 220
    action   = "Allow"
    rule {
      name              = "identity-registry-vault-and-acme"
      source_addresses  = [var.network.edge_apps_subnet_cidr]
      destination_fqdns = concat(var.shared_service_fqdns, [var.state_fqdn, "acme-v02.api.letsencrypt.org", "acme-staging-v02.api.letsencrypt.org", "login.microsoftonline.com", "login.microsoft.com", "*.login.microsoft.com", "*.login.microsoftonline.com", "*.identity.azure.net", "*.msidentity.com", "*.msauth.net", "mcr.microsoft.com", "*.data.mcr.microsoft.com", "mcr-0001.mcr-msedge.net", "*.servicebus.windows.net", "packages.aks.azure.com", "acs-mirror.azureedge.net", "*.ods.opinsights.azure.com", "*.oms.opinsights.azure.com", "*.monitoring.azure.com", "*.monitor.azure.com"])
      protocols {
        type = "Https"
        port = 443
      }
    }
  }
  dynamic "application_rule_collection" {
    for_each = length(var.edge_public_hostnames) > 0 ? [1] : []
    content {
      name     = "acme-public-route-self-check"
      priority = 230
      action   = "Allow"
      rule {
        name              = "only-configured-waf-hosts"
        source_addresses  = [var.network.edge_apps_subnet_cidr]
        destination_fqdns = var.edge_public_hostnames
        protocols {
          type = "Http"
          port = 80
        }
      }
    }
  }
  network_rule_collection {
    name     = "explicit-private-flows"
    priority = 100
    action   = "Allow"
    dynamic "rule" {
      for_each = var.environments
      content {
        name                  = "management-to-${rule.key}-apps"
        protocols             = ["TCP"]
        source_addresses      = [var.network.management_subnet_cidr]
        destination_addresses = [rule.value.network.apps_subnet_cidr, rule.value.network.functions_subnet_cidr]
        destination_ports     = ["443"]
      }
    }
    dynamic "rule" {
      for_each = var.environments
      content {
        name                  = "${rule.key}-own-cosmos"
        protocols             = ["TCP"]
        source_addresses      = [rule.value.network.apps_subnet_cidr, rule.value.network.functions_subnet_cidr, var.network.management_subnet_cidr]
        destination_addresses = [rule.value.network.data_subnet_cidr]
        destination_ports     = ["10255"]
      }
    }
    rule {
      name                  = "required-platform-https"
      protocols             = ["TCP"]
      source_addresses      = concat([var.network.edge_apps_subnet_cidr], flatten([for env in var.environments : [env.network.apps_subnet_cidr, env.network.functions_subnet_cidr]]))
      destination_addresses = ["MicrosoftContainerRegistry", "AzureFrontDoor.FirstParty", "AzureActiveDirectory", "AzureMonitor"]
      destination_ports     = ["443"]
    }
  }
}
resource "azurerm_monitor_diagnostic_setting" "firewall" {
  name                       = "audit"
  target_resource_id         = azurerm_firewall.this.id
  log_analytics_workspace_id = var.workspace_id
  enabled_log {
    category_group = "allLogs"
  }
  enabled_metric {
    category = "AllMetrics"
  }
}
