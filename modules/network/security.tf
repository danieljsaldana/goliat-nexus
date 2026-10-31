resource "azurerm_network_security_group" "this" {
  for_each            = toset(keys(local.protected))
  name                = "${var.prefix}-${each.key}-nsg"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_subnet_network_security_group_association" "this" {
  for_each                  = azurerm_network_security_group.this
  subnet_id                 = azurerm_subnet.this[each.key].id
  network_security_group_id = each.value.id
}

# Sobrescriben AllowVNetInBound y AllowInternetOutBound de Azure.
resource "azurerm_network_security_rule" "deny_in" {
  for_each                    = azurerm_network_security_group.this
  name                        = "deny-inbound-by-default"
  priority                    = 4096
  direction                   = "Inbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = each.value.name
}
resource "azurerm_network_security_rule" "deny_out" {
  for_each                    = azurerm_network_security_group.this
  name                        = "deny-outbound-by-default"
  priority                    = 4096
  direction                   = "Outbound"
  access                      = "Deny"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "*"
  source_address_prefix       = "*"
  destination_address_prefix  = "*"
  resource_group_name         = var.resource_group_name
  network_security_group_name = each.value.name
}

locals {
  rules = merge({
    edge_internal_in      = { nsg = "edge-apps", direction = "Inbound", priority = 100, protocol = "*", source = var.network.edge_apps_subnet_cidr, destination = var.network.edge_apps_subnet_cidr, ports = ["*"] }
    edge_health_in        = { nsg = "edge-apps", direction = "Inbound", priority = 110, protocol = "Tcp", source = "AzureLoadBalancer", destination = var.network.edge_apps_subnet_cidr, ports = ["30000-32767"] }
    edge_gateway_in       = { nsg = "edge-apps", direction = "Inbound", priority = 120, protocol = "Tcp", source = var.network.gateway_subnet_cidr, destination = var.network.edge_apps_subnet_cidr, ports = ["443", "31443"] }
    edge_internal_out     = { nsg = "edge-apps", direction = "Outbound", priority = 100, protocol = "*", source = var.network.edge_apps_subnet_cidr, destination = var.network.edge_apps_subnet_cidr, ports = ["*"] }
    edge_challenge_out    = { nsg = "edge-apps", direction = "Outbound", priority = 130, protocol = "Tcp", source = var.network.edge_apps_subnet_cidr, destination = "*", ports = ["80"] }
    edge_https_out        = { nsg = "edge-apps", direction = "Outbound", priority = 120, protocol = "Tcp", source = var.network.edge_apps_subnet_cidr, destination = "*", ports = ["443"] }
    endpoints_gateway_in  = { nsg = "endpoints", direction = "Inbound", priority = 120, protocol = "Tcp", source = var.network.gateway_subnet_cidr, destination = var.network.endpoints_subnet_cidr, ports = ["443"] }
    admin_https_out       = { nsg = "management", direction = "Outbound", priority = 120, protocol = "Tcp", source = var.network.management_subnet_cidr, destination = "*", ports = ["443"] }
    endpoints_firewall_in = { nsg = "endpoints", direction = "Inbound", priority = 100, protocol = "Tcp", source = var.network.firewall_subnet_cidr, destination = var.network.endpoints_subnet_cidr, ports = ["443"] }
    }, merge([for key, env in var.environments : {
      "${key}_gateway_in"             = { nsg = "${key}-apps", direction = "Inbound", priority = 120, protocol = "Tcp", source = var.network.gateway_subnet_cidr, destination = env.network.apps_subnet_cidr, ports = ["443", "31443"] }
      "${key}_cosmos_out"             = { nsg = "${key}-apps", direction = "Outbound", priority = 140, protocol = "Tcp", source = env.network.apps_subnet_cidr, destination = env.network.data_subnet_cidr, ports = ["10255"] }
      "${key}_admin_cosmos_out"       = { nsg = "management", direction = "Outbound", priority = key == "dev" ? 140 : 150, protocol = "Tcp", source = var.network.management_subnet_cidr, destination = env.network.data_subnet_cidr, ports = ["10255"] }
      "${key}_data_firewall_in"       = { nsg = "${key}-data", direction = "Inbound", priority = 100, protocol = "Tcp", source = var.network.firewall_subnet_cidr, destination = env.network.data_subnet_cidr, ports = ["443", "10255"] }
      "${key}_internal_in"            = { nsg = "${key}-apps", direction = "Inbound", priority = 100, protocol = "*", source = env.network.apps_subnet_cidr, destination = env.network.apps_subnet_cidr, ports = ["*"] }
      "${key}_health_in"              = { nsg = "${key}-apps", direction = "Inbound", priority = 110, protocol = "Tcp", source = "AzureLoadBalancer", destination = env.network.apps_subnet_cidr, ports = ["30000-32767"] }
      "${key}_firewall_in"            = { nsg = "${key}-apps", direction = "Inbound", priority = 130, protocol = "Tcp", source = var.network.firewall_subnet_cidr, destination = env.network.apps_subnet_cidr, ports = ["443", "31443"] }
      "${key}_functions_https_out"    = { nsg = "${key}-functions", direction = "Outbound", priority = 120, protocol = "Tcp", source = env.network.functions_subnet_cidr, destination = "*", ports = ["443"] }
      "${key}_functions_cosmos_out"   = { nsg = "${key}-functions", direction = "Outbound", priority = 140, protocol = "Tcp", source = env.network.functions_subnet_cidr, destination = env.network.data_subnet_cidr, ports = ["10255"] }
      "${key}_functions_internal_in"  = { nsg = "${key}-functions", direction = "Inbound", priority = 100, protocol = "*", source = env.network.functions_subnet_cidr, destination = env.network.functions_subnet_cidr, ports = ["*"] }
      "${key}_functions_internal_out" = { nsg = "${key}-functions", direction = "Outbound", priority = 100, protocol = "*", source = env.network.functions_subnet_cidr, destination = env.network.functions_subnet_cidr, ports = ["*"] }
      "${key}_internal_out"           = { nsg = "${key}-apps", direction = "Outbound", priority = 100, protocol = "*", source = env.network.apps_subnet_cidr, destination = env.network.apps_subnet_cidr, ports = ["*"] }
      "${key}_https_out"              = { nsg = "${key}-apps", direction = "Outbound", priority = 120, protocol = "Tcp", source = env.network.apps_subnet_cidr, destination = "*", ports = ["443"] }
  }]...))
}
resource "azurerm_network_security_rule" "allow" {
  for_each                    = local.rules
  name                        = replace(each.key, "_", "-")
  priority                    = each.value.priority
  direction                   = each.value.direction
  access                      = "Allow"
  protocol                    = each.value.protocol
  source_port_range           = "*"
  destination_port_range      = contains(each.value.ports, "*") ? "*" : null
  destination_port_ranges     = contains(each.value.ports, "*") ? null : each.value.ports
  source_address_prefix       = each.value.source
  destination_address_prefix  = each.value.destination
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this[each.value.nsg].name
}

resource "azurerm_network_security_rule" "dns" {
  for_each                    = toset(concat(["management", "edge-apps"], flatten([for key in keys(var.environments) : ["${key}-apps", "${key}-functions"]])))
  name                        = "dns-via-firewall"
  priority                    = 110
  direction                   = "Outbound"
  access                      = "Allow"
  protocol                    = "*"
  source_port_range           = "*"
  destination_port_range      = "53"
  source_address_prefix       = "*"
  destination_address_prefix  = azurerm_firewall.this.ip_configuration[0].private_ip_address
  resource_group_name         = var.resource_group_name
  network_security_group_name = azurerm_network_security_group.this[each.key].name
}
