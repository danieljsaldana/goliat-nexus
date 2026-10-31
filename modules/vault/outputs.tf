output "id" { value = azurerm_key_vault.this.id }
output "uri" { value = azurerm_key_vault.this.vault_uri }
output "security" { value = { public = azurerm_key_vault.this.public_network_access_enabled, rbac = azurerm_key_vault.this.rbac_authorization_enabled, purge = azurerm_key_vault.this.purge_protection_enabled } }
