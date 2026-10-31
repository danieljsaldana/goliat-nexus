# Presupuesto con fecha explícita y filtro a los grupos de recursos del producto.
resource "azurerm_consumption_budget_subscription" "this" {
  name            = var.name
  subscription_id = var.subscription_id
  amount          = var.amount
  time_grain      = "Monthly"
  time_period { start_date = "${var.start_date}T00:00:00Z" }
  filter {
    dimension {
      name   = "ResourceGroupName"
      values = var.resource_group_names
    }
  }
  dynamic "notification" {
    for_each = { actual80 = { threshold = 80, type = "Actual" }, actual100 = { threshold = 100, type = "Actual" }, forecast100 = { threshold = 100, type = "Forecasted" } }
    content {
      enabled        = true
      threshold      = notification.value.threshold
      threshold_type = notification.value.type
      operator       = "GreaterThanOrEqualTo"
      contact_emails = var.alert_emails
    }
  }
}
