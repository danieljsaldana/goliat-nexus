terraform {
  backend "azurerm" {}
}
variable "foundation" {
  type = object({ storage_account_name = string, storage_account_id = string, resource_group_name = string, container_name = string, public_access = bool })
}
resource "azurerm_resource_group" "this" {
  for_each = toset(["connectivity", "shared", "dev", "prod"])
  name     = "${var.config.name}-${each.key}-rg"
  location = var.config.location
  tags     = merge(local.tags, { Environment = contains(["dev", "prod"], each.key) ? each.key : "shared" })
}
module "shared" {
  source              = "../../modules/shared"
  prefix              = local.prefix
  suffix              = var.config.suffix
  resource_group_name = azurerm_resource_group.this["shared"].name
  location            = var.config.location
  log_retention_days  = var.config.log_retention_days
  tags                = local.tags
}
