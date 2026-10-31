resource "azurerm_monitor_action_group" "operations" {
  name                = "${local.prefix}-operations"
  resource_group_name = azurerm_resource_group.this["shared"].name
  short_name          = "lz-ops"
  dynamic "email_receiver" {
    for_each = toset(var.config.operations.alert_emails)
    content {
      name                    = "operator-${index(var.config.operations.alert_emails, email_receiver.value)}"
      email_address           = email_receiver.value
      use_common_alert_schema = true
    }
  }
  tags = local.tags
}
module "budget" {
  source               = "../../modules/budget"
  name                 = "${local.prefix}-monthly"
  subscription_id      = "/subscriptions/${var.config.subscription_id}"
  amount               = var.config.operations.budget_amount
  start_date           = var.config.operations.budget_start_date
  alert_emails         = var.config.operations.alert_emails
  resource_group_names = concat(["${local.prefix}-state-rg", "${var.config.name}-edge-aca-managed-rg"], [for key in keys(var.config.environments) : "${var.config.name}-${key}-aca-managed-rg"], [for group in azurerm_resource_group.this : group.name])
}
moved {
  from = azurerm_consumption_budget_subscription.product
  to   = module.budget.azurerm_consumption_budget_subscription.this
}
resource "azurerm_monitor_metric_alert" "firewall" {
  name                = "${local.prefix}-firewall-health"
  resource_group_name = azurerm_resource_group.this["shared"].name
  scopes              = [module.network.firewall_id]
  severity            = 1
  frequency           = "PT1M"
  window_size         = "PT5M"
  description         = "Salud de Azure Firewall inferior al 90% durante cinco minutos."
  criteria {
    metric_namespace = "Microsoft.Network/azureFirewalls"
    metric_name      = "FirewallHealth"
    aggregation      = "Average"
    operator         = "LessThan"
    threshold        = 90
  }
  action { action_group_id = azurerm_monitor_action_group.operations.id }
  tags = local.tags
}
resource "azurerm_monitor_activity_log_alert" "health" {
  name                = "${local.prefix}-resource-health"
  resource_group_name = azurerm_resource_group.this["shared"].name
  location            = "global"
  scopes              = ["/subscriptions/${var.config.subscription_id}"]
  criteria {
    category        = "ResourceHealth"
    resource_groups = concat(["${local.prefix}-state-rg", "${var.config.name}-edge-aca-managed-rg"], [for key in keys(var.config.environments) : "${var.config.name}-${key}-aca-managed-rg"], [for group in azurerm_resource_group.this : group.name])
    resource_health { current = ["Degraded", "Unavailable"] }
  }
  action { action_group_id = azurerm_monitor_action_group.operations.id }
  tags = local.tags
}
