resource "azurerm_monitor_diagnostic_setting" "state_blobs" {
  name                       = "audit"
  target_resource_id         = "${var.foundation.storage_account_id}/blobServices/default"
  log_analytics_workspace_id = module.shared.workspace_id
  enabled_log {
    category_group = "allLogs"
  }
  enabled_metric {
    category = "Capacity"
  }
  enabled_metric {
    category = "Transaction"
  }
}
