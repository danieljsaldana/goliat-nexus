# Hosting estático; publicación del código con token custodiado en Key Vault.
resource "azurerm_static_web_app" "swa" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_tier            = var.sku_tier
  sku_size            = var.sku_size
  app_settings        = var.app_settings
  tags                = var.tags
}
