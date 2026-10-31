output "id" { value = azurerm_container_app_environment.this.id }
output "default_domain" { value = azurerm_container_app_environment.this.default_domain }
output "static_ip_address" { value = azurerm_container_app_environment.this.static_ip_address }
output "security" {
  value = {
    internal      = azurerm_container_app_environment.this.internal_load_balancer_enabled
    public_access = azurerm_container_app_environment.this.public_network_access
    mutual_tls    = azurerm_container_app_environment.this.mutual_tls_enabled
  }
}
