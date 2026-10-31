output "id" { value = azurerm_storage_account.this.id }
output "name" { value = azurerm_storage_account.this.name }
output "security" {
  value = {
    shared_keys    = azurerm_storage_account.this.shared_access_key_enabled
    public_blobs   = azurerm_storage_account.this.allow_nested_items_to_be_public
    default_rule   = azurerm_storage_account.this.network_rules[0].default_action
    versioning     = azurerm_storage_account.this.blob_properties[0].versioning_enabled
    operator_scope = azurerm_role_assignment.operator.scope
  }
}
