resource "azurerm_eventgrid_topic" "topic" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  public_network_access_enabled = var.public_network_access_enabled
  local_auth_enabled            = var.local_auth_enabled
  inbound_ip_rule               = var.inbound_ip_rule

  identity {
    type         = "UserAssigned"
    identity_ids = [var.eventgrid_identity_id]
  }

  tags = var.tags
}

resource "azurerm_role_assignment" "backend_eventgrid_sender" {
  scope                = azurerm_eventgrid_topic.topic.id
  role_definition_name = "EventGrid Data Sender"
  principal_id         = var.backend_principal_id
}
