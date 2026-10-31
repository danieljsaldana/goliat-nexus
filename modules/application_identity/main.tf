variable "prefix" { type = string }
variable "tenant_id" { type = string }
variable "operator_object_id" { type = string }
variable "redirect_uris" { type = list(string) }
variable "access" { type = object({ requester_object_ids = list(string), operator_object_ids = list(string) }) }
data "azuread_client_config" "current" {}
locals {
  scope_id          = uuidv5("dns", "${var.prefix}/access_as_user")
  requester_role_id = uuidv5("dns", "${var.prefix}/Requester")
  operator_role_id  = uuidv5("dns", "${var.prefix}/Operator")
  operators         = length(var.access.operator_object_ids) > 0 ? toset(var.access.operator_object_ids) : toset([var.operator_object_id])
  assignments       = merge({ for id in var.access.requester_object_ids : "requester-${id}" => { principal = id, role = local.requester_role_id } }, { for id in local.operators : "operator-${id}" => { principal = id, role = local.operator_role_id } })
  users             = setunion(toset(var.access.requester_object_ids), local.operators)
}
resource "azuread_application" "api" {
  display_name     = "${var.prefix}-api"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azuread_client_config.current.object_id]
  # La URI la administra azuread_application_identifier_uri.api.
  lifecycle { ignore_changes = [identifier_uris] }
  api {
    requested_access_token_version = 2
    oauth2_permission_scope {
      id                         = local.scope_id
      value                      = "access_as_user"
      type                       = "Admin"
      enabled                    = true
      admin_consent_display_name = "Use the Alba request API"
      admin_consent_description  = "Access the API as the assigned user. App roles and record ownership are verified by the API."
    }
  }
  app_role {
    id                   = local.requester_role_id
    value                = "Requester"
    display_name         = "Requester"
    description          = "Create requests and read only their own records."
    allowed_member_types = ["User"]
    enabled              = true
  }
  app_role {
    id                   = local.operator_role_id
    value                = "Operator"
    display_name         = "Operator"
    description          = "Operate requests and activities in this environment."
    allowed_member_types = ["User"]
    enabled              = true
  }
}
resource "azuread_application_identifier_uri" "api" {
  application_id = azuread_application.api.id
  identifier_uri = "api://${azuread_application.api.client_id}"
}
resource "azuread_service_principal" "api" {
  client_id                    = azuread_application.api.client_id
  app_role_assignment_required = true
  owners                       = [data.azuread_client_config.current.object_id]
}
resource "azuread_application" "portal" {
  display_name     = "${var.prefix}-portal"
  sign_in_audience = "AzureADMyOrg"
  owners           = [data.azuread_client_config.current.object_id]
  single_page_application { redirect_uris = var.redirect_uris }
  required_resource_access {
    resource_app_id = azuread_application.api.client_id
    resource_access {
      id   = local.scope_id
      type = "Scope"
    }
  }
}
resource "azuread_service_principal" "portal" {
  client_id                    = azuread_application.portal.client_id
  app_role_assignment_required = true
  owners                       = [data.azuread_client_config.current.object_id]
}
resource "azuread_application_pre_authorized" "clients" {
  for_each             = toset(["portal", "azure-cli"])
  application_id       = azuread_application.api.id
  authorized_client_id = each.key == "portal" ? azuread_application.portal.client_id : "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
  permission_ids       = [local.scope_id]
}
resource "azuread_app_role_assignment" "api" {
  for_each            = local.assignments
  app_role_id         = each.value.role
  principal_object_id = each.value.principal
  resource_object_id  = azuread_service_principal.api.object_id
}
resource "azuread_app_role_assignment" "portal" {
  for_each            = local.users
  app_role_id         = "00000000-0000-0000-0000-000000000000"
  principal_object_id = each.key
  resource_object_id  = azuread_service_principal.portal.object_id
}
output "integration" {
  value = {
    tenant_id          = var.tenant_id
    api_client_id      = azuread_application.api.client_id
    frontend_client_id = azuread_application.portal.client_id
    scope              = "api://${azuread_application.api.client_id}/access_as_user"
    allowed_client_ids = [azuread_application.portal.client_id, "04b07795-8ddb-461a-bbee-02f9e1bf7b46"]
  }
}
output "security" {
  value = { audience = azuread_application.api.sign_in_audience, assigned_users_only = azuread_service_principal.api.app_role_assignment_required, portal_assigned_users_only = azuread_service_principal.portal.app_role_assignment_required, access_token_version = 2 }
}
