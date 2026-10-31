# Conserva las direcciones de estado anteriores al extraer módulos.
moved {
  from = azurerm_container_app_environment.this
  to   = module.container_app_environment.azurerm_container_app_environment.this
}

moved {
  from = azurerm_private_dns_zone.apps
  to   = module.container_app_environment.azurerm_private_dns_zone.apps
}

moved {
  from = azurerm_private_dns_a_record.apps
  to   = module.container_app_environment.azurerm_private_dns_a_record.apps
}

moved {
  from = azurerm_private_dns_zone_virtual_network_link.apps
  to   = module.container_app_environment.azurerm_private_dns_zone_virtual_network_link.apps
}

moved {
  from = azurerm_container_app.example
  to   = module.container_apps.azurerm_container_app.example
}

moved {
  from = azurerm_monitor_metric_alert.http_errors
  to   = module.container_apps.azurerm_monitor_metric_alert.http_errors
}

moved {
  from = azurerm_role_assignment.cosmos_secret
  to   = module.container_apps.azurerm_role_assignment.cosmos_secret
}

moved {
  from = azurerm_role_assignment.queue_sender
  to   = module.container_apps.azurerm_role_assignment.queue_sender
}
