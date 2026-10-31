mock_provider "azuread" {
  mock_data "azuread_client_config" {
    defaults = { object_id = "33333333-3333-4333-8333-333333333333", tenant_id = "22222222-2222-4222-8222-222222222222", client_id = "44444444-4444-4444-8444-444444444444" }
  }
}
mock_provider "azurerm" {}
variable "config" { type = any }
variable "environment" { type = string }
run "private_application" {
  command = plan
  assert {
    condition     = module.workload.security.internal && module.workload.security.public_access == "Disabled" && module.workload.security.mutual_tls
    error_message = "Container Apps debe ser privado."
  }
  assert {
    condition     = module.workload.security.application_count == 4 && module.workload.security.frontend_external && !module.workload.security.api_external
    error_message = "Un gateway privado y tres APIs internas."
  }
  assert {
    condition     = alltrue([for app in module.workload.applications : can(regex("@sha256:[0-9a-f]{64}$", app.image))])
    error_message = "No se aceptan imágenes por etiqueta mutable."
  }
  assert {
    condition     = module.workload.security.replicas["tenant"].min == var.config.environments[var.environment].sample.api_min_replicas && module.workload.security.identities["tenant"] != module.workload.security.identities["frontend"]
    error_message = "Réplicas y separación de identidades deben respetar la configuración."
  }
  assert {
    condition     = length(module.events) == 1
    error_message = "El procesamiento de eventos debe activarse según su interruptor."
  }
  assert {
    condition     = !module.events[0].security.public_access && !module.events[0].security.basic_auth && module.events[0].security.deployment_auth == "UserAssignedIdentity" && module.events[0].security.runtime == "node" && module.events[0].security.host_keys == "keyvault"
    error_message = "Functions Node debe ser privado, sin Basic Auth, con identidad y claves en vault."
  }

}
run "without_sample" {
  command = plan
  variables {
    config = merge(var.config, { environments = merge(var.config.environments, { (var.environment) = merge(var.config.environments[var.environment], { enable_api_platform = false, enable_api_tenant = false, enable_api_activities = false, enable_event_processing = false }) }) })
  }
  assert {
    condition     = module.workload.security.application_count == 0 && length(module.events) == 0
    error_message = "El entorno debe poder crearse sin aplicaciones ni Function."
  }
}
