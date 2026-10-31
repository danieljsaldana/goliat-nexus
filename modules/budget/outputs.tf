output "id" { value = azurerm_consumption_budget_subscription.this.id }
output "name" { value = azurerm_consumption_budget_subscription.this.name }
output "amount" { value = azurerm_consumption_budget_subscription.this.amount }
output "notification_count" { value = length(azurerm_consumption_budget_subscription.this.notification) }
