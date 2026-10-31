output "id" { value = azurerm_storage_account.sa.id }
output "name" { value = azurerm_storage_account.sa.name }
output "blob_uri" { value = azurerm_storage_account.sa.primary_blob_endpoint }
output "queue_uri" { value = azurerm_storage_account.sa.primary_queue_endpoint }
output "table_uri" { value = azurerm_storage_account.sa.primary_table_endpoint }
