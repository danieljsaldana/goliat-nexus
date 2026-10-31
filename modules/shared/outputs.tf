output "workspace_id" { value = azurerm_log_analytics_workspace.this.id }
output "registry_id" { value = azurerm_container_registry.this.id }
output "registry_login_server" { value = azurerm_container_registry.this.login_server }
output "security" { value = { acr_public = azurerm_container_registry.this.public_network_access_enabled, acr_admin = azurerm_container_registry.this.admin_enabled, acr_sku = azurerm_container_registry.this.sku } }
