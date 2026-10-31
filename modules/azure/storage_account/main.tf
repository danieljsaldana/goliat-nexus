resource "azurerm_storage_account" "sa" {
  name                            = var.name
  resource_group_name             = var.resource_group_name
  location                        = var.location
  account_tier                    = "Standard"
  min_tls_version                 = "TLS1_2"
  public_network_access           = "Disabled"
  account_replication_type        = var.replication
  allow_nested_items_to_be_public = var.allow_nested_items_to_be_public
  shared_access_key_enabled       = var.shared_access_key_enabled

  blob_properties {
    last_access_time_enabled = var.last_access_time_enabled
    versioning_enabled       = true
    delete_retention_policy { days = var.soft_delete_days }
    container_delete_retention_policy { days = var.soft_delete_days }
  }

  lifecycle { prevent_destroy = true }

  tags = var.tags

  dynamic "network_rules" {
    for_each = var.network_rules != null ? [var.network_rules] : []
    content {
      default_action             = network_rules.value.default_action
      bypass                     = network_rules.value.bypass
      ip_rules                   = network_rules.value.ip_rules
      virtual_network_subnet_ids = network_rules.value.virtual_network_subnet_ids
    }
  }
}

resource "azurerm_storage_management_policy" "lifecycle" {
  count              = var.enable_lifecycle_policy ? 1 : 0
  storage_account_id = azurerm_storage_account.sa.id

  rule {
    name    = "default-lifecycle-rule"
    enabled = true
    filters {
      blob_types = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_last_access_time_greater_than = var.lifecycle_days
      }
    }
  }
}

resource "azurerm_storage_container" "containers" {
  for_each              = toset(var.containers)
  name                  = each.key
  storage_account_id    = azurerm_storage_account.sa.id
  container_access_type = "private"
}

resource "azurerm_storage_queue" "queues" {
  for_each           = toset(var.queues)
  name               = each.key
  storage_account_id = azurerm_storage_account.sa.id
}

resource "azurerm_storage_table" "tables" {
  for_each           = toset(var.tables)
  name               = each.key
  storage_account_id = azurerm_storage_account.sa.id
}
