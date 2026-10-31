output "vnet_ids" { value = { for key, value in azurerm_virtual_network.this : key => value.id } }
output "subnet_ids" { value = { for key, value in azurerm_subnet.this : key => value.id } }
output "firewall_private_ip" { value = azurerm_firewall.this.ip_configuration[0].private_ip_address }
output "firewall_id" { value = azurerm_firewall.this.id }
output "security" {
  value = {
    inbound_deny  = { for k, v in azurerm_network_security_rule.deny_in : k => v.access }
    outbound_deny = { for k, v in azurerm_network_security_rule.deny_out : k => v.access }
    hub_peers     = keys(azurerm_virtual_network_peering.hub_to_spoke)
    routes        = { for k, v in azurerm_route_table.this : k => v.route }
    pe_policies   = azurerm_subnet.this["endpoints"].private_endpoint_network_policies
    allowed_flows = local.rules
    private_flows = { for key, env in var.environments : key => { source = env.network.apps_subnet_cidr, database = env.network.data_subnet_cidr, services = var.service_fqdns[key] } }
    threat_mode   = azurerm_firewall_policy.this.threat_intelligence_mode
  }
}
