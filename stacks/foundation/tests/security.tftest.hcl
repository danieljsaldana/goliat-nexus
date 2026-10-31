mock_provider "azuread" {
  mock_data "azuread_client_config" {
    defaults = { object_id = "33333333-3333-4333-8333-333333333333", tenant_id = "22222222-2222-4222-8222-222222222222", client_id = "44444444-4444-4444-8444-444444444444" }
  }
}
mock_provider "azurerm" {}

run "state_security" {
  command = plan
  assert {
    condition     = !module.state.security.shared_keys && !module.state.security.public_blobs
    error_message = "El backend no puede permitir claves compartidas ni blobs públicos."
  }
  assert {
    condition     = module.state.security.default_rule == "Deny" && module.state.security.versioning
    error_message = "El backend debe denegar por defecto y conservar versiones."
  }
}

run "private_backend" {
  command = plan
  module {
    source = "../../modules/state"
  }
  variables {
    name                = "stlzprivatetest"
    resource_group_name = "acme-test-state-rg"
    location            = "westeurope"
    replication_type    = "LRS"
    public_access       = false
    allowed_ip_ranges   = ["8.8.8.8"]
    operator_object_id  = "33333333-3333-4333-8333-333333333333"
    tags                = {}
  }
  assert {
    condition     = azurerm_storage_account.this.public_network_access == "Disabled"
    error_message = "El modo privado debe deshabilitar el endpoint público de Storage."
  }
}
