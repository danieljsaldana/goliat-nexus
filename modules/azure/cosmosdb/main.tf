resource "azurerm_cosmosdb_account" "db" {
  count                = var.enable_cosmos ? 1 : 0
  name                 = var.name
  location             = var.location
  resource_group_name  = var.resource_group_name
  offer_type           = var.offer_type
  kind                 = var.kind
  mongo_server_version = var.kind == "MongoDB" ? var.mongo_server_version : null

  automatic_failover_enabled    = false
  public_network_access_enabled = var.public_network_access_enabled
  free_tier_enabled             = var.free_tier_enabled
  minimal_tls_version           = var.minimal_tls_version
  ip_range_filter               = var.ip_range_filter

  dynamic "capabilities" {
    for_each = toset(var.capabilities)
    content {
      name = capabilities.value
    }
  }

  dynamic "consistency_policy" {
    for_each = [var.consistency_policy]
    content {
      consistency_level       = consistency_policy.value.consistency_level
      max_interval_in_seconds = consistency_policy.value.max_interval_in_seconds
      max_staleness_prefix    = consistency_policy.value.max_staleness_prefix
    }
  }

  # Configuración de geo_location
  # Si se pasa var.geo_locations, usamos eso. Si no, usamos var.location como primaria.
  dynamic "geo_location" {
    for_each = var.geo_locations != null ? var.geo_locations : [{
      location          = var.location
      failover_priority = 0
      zone_redundant    = false
    }]
    content {
      location          = geo_location.value.location
      failover_priority = geo_location.value.failover_priority
      zone_redundant    = geo_location.value.zone_redundant
    }
  }

  dynamic "backup" {
    for_each = [var.backup]
    content {
      type                = backup.value.type
      tier                = backup.value.tier
      interval_in_minutes = backup.value.interval_in_minutes
      retention_in_hours  = backup.value.retention_in_hours
      storage_redundancy  = backup.value.storage_redundancy
    }
  }

  lifecycle { prevent_destroy = true }

  tags = var.tags
}

resource "azurerm_cosmosdb_mongo_database" "main" {
  for_each            = var.enable_cosmos ? toset(var.database_names) : []
  name                = each.value
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.db[0].name

  lifecycle { prevent_destroy = true }

  throughput = var.is_serverless ? null : (var.max_throughput == null ? var.throughput : null)

  dynamic "autoscale_settings" {
    for_each = !var.is_serverless && var.max_throughput != null ? [1] : []
    content {
      max_throughput = var.max_throughput
    }
  }
}
