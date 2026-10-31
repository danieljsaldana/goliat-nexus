# DNS público opcional para los dominios de la aplicación.
resource "azurerm_dns_zone" "main" {
  count               = var.create_zone ? 1 : 0
  name                = var.domain_name
  resource_group_name = var.resource_group_name
  tags                = var.tags
}
data "azurerm_dns_zone" "main" {
  count               = var.create_zone ? 0 : 1
  name                = var.domain_name
  resource_group_name = var.resource_group_name
}
resource "azurerm_dns_cname_record" "swa" {
  for_each            = var.cname_records
  name                = each.key
  zone_name           = var.domain_name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  record              = each.value.record_value
  tags                = var.tags
  depends_on          = [azurerm_dns_zone.main, data.azurerm_dns_zone.main]
}
