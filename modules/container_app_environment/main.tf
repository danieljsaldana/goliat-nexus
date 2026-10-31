# Entorno privado de Container Apps para alojar las aplicaciones de Nexus.
resource "azurerm_container_app_environment" "this" {
  name                               = "${var.prefix}-cae"
  resource_group_name                = var.resource_group_name
  location                           = var.location
  infrastructure_subnet_id           = var.infrastructure_subnet_id
  infrastructure_resource_group_name = var.infrastructure_resource_group_name
  internal_load_balancer_enabled     = true
  public_network_access              = "Disabled"
  log_analytics_workspace_id         = var.log_analytics_workspace_id
  logs_destination                   = "log-analytics"
  zone_redundancy_enabled            = var.zone_redundancy
  mutual_tls_enabled                 = true
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
  tags = var.tags
}

resource "azurerm_private_dns_zone" "apps" {
  name                = azurerm_container_app_environment.this.default_domain
  resource_group_name = var.resource_group_name
  tags                = var.tags
}
resource "azurerm_private_dns_a_record" "apps" {
  for_each = toset(["*", "@"])
  name     = each.key

  private_dns_zone_id = azurerm_private_dns_zone.apps.id

  ttl     = 300
  records = [azurerm_container_app_environment.this.static_ip_address]
  tags    = var.tags
}
resource "azurerm_private_dns_zone_virtual_network_link" "apps" {
  for_each = var.vnet_ids
  name     = each.key

  private_dns_zone_id  = azurerm_private_dns_zone.apps.id
  virtual_network_id   = each.value
  registration_enabled = false
  tags                 = var.tags
}


