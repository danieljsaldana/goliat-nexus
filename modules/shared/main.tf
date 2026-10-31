# Servicios compartidos: registro de contenedores y observabilidad.
resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.prefix}-logs"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = var.tags
}
resource "azurerm_container_registry" "this" {
  name                          = "acrlz${var.suffix}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  sku                           = "Premium"
  admin_enabled                 = false
  public_network_access_enabled = false
  network_rule_bypass_option    = "None"
  data_endpoint_enabled         = true
  tags                          = var.tags
}
resource "azurerm_monitor_diagnostic_setting" "registry" {
  name                       = "audit"
  target_resource_id         = azurerm_container_registry.this.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  enabled_log {
    category_group = "allLogs"
  }
  enabled_metric {
    category = "AllMetrics"
  }
}
