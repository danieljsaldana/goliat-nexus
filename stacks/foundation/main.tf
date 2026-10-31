# Backend de estado de la instalación, con autenticación Entra y acceso restringido.
resource "azurerm_resource_group" "state" {
  name     = "${local.prefix}-state-rg"
  location = var.config.location
  tags     = local.tags
}

module "state" {
  source              = "../../modules/state"
  name                = "stlz${var.config.suffix}"
  resource_group_name = azurerm_resource_group.state.name
  location            = var.config.location
  replication_type    = var.config.state_replication
  public_access       = var.config.state_access == "restricted-public"
  allowed_ip_ranges   = var.config.operator_ip_ranges
  operator_object_id  = var.config.operator_object_id
  tags                = local.tags
}

output "integration" {
  description = "Contrato para la plataforma; no contiene claves."
  value = {
    resource_group_name  = azurerm_resource_group.state.name
    storage_account_name = module.state.name
    storage_account_id   = module.state.id
    container_name       = "tfstate"
    public_access        = var.config.state_access == "restricted-public"
  }
}
