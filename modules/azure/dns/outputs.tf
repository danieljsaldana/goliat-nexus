output "name_servers" { value = var.create_zone ? azurerm_dns_zone.main[0].name_servers : data.azurerm_dns_zone.main[0].name_servers }
