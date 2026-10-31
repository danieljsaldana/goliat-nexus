output "id" {
  value = length(azurerm_cosmosdb_account.db) > 0 ? azurerm_cosmosdb_account.db[0].id : null
}

output "endpoint" {
  value = length(azurerm_cosmosdb_account.db) > 0 ? azurerm_cosmosdb_account.db[0].endpoint : null
}
