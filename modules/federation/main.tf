# Federación de identidad para el publicador OIDC de GitHub Actions.
resource "azurerm_user_assigned_identity" "publisher" {
  name                = "${var.prefix}-publisher-id"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}
resource "azurerm_federated_identity_credential" "github" {
  name                      = "github-environment"
  user_assigned_identity_id = azurerm_user_assigned_identity.publisher.id
  issuer                    = "https://token.actions.githubusercontent.com"
  audience                  = ["api://AzureADTokenExchange"]
  subject                   = "repo:${var.github_repository}:environment:${var.github_environment}"
}
resource "azurerm_role_assignment" "publisher" {
  for_each = {
    images   = { scope = var.registry_id, role = "AcrPush" }
    app      = { scope = var.resource_group_id, role = "Contributor" }
    identity = { scope = var.app_identity_id, role = "Managed Identity Operator" }
  }
  scope                            = each.value.scope
  role_definition_name             = each.value.role
  principal_id                     = azurerm_user_assigned_identity.publisher.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
output "client_id" { value = azurerm_user_assigned_identity.publisher.client_id }
