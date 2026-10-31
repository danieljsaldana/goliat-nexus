terraform {
  backend "azurerm" {}
}
variable "platform" { type = any }
variable "workloads" { type = any }
variable "edge_image" {
  type = string
  validation {
    condition     = can(regex("^[-a-z0-9.]+/example/certificates@sha256:[a-f0-9]{64}$", var.edge_image))
    error_message = "El gestor de certificados debe usar una imagen privada por digest."
  }
}
locals {
  entry                 = var.platform.public_entrypoint
  hostnames             = distinct(concat([local.entry.azure_hostname, trimprefix(local.entry.origin, "https://")], [for origin in values(local.entry.environment_origins) : trimprefix(origin, "https://")]))
  portals               = { for env, contract in var.platform.environments : env => { for key, web in contract.webs : key => web.public_url } }
  certificate_secret_id = var.config.public_entrypoint.certificate_secret_id != "" ? var.config.public_entrypoint.certificate_secret_id : "${local.entry.vault.uri}secrets/waf-tls"
  backends = merge({ certificates = { hostname = "${local.prefix}-certificates.${local.entry.environment_domain}", probe_path = "/healthz", paths = [], api_environment = "" } },
    { for env, workload in var.workloads : "${env}-api" => { hostname = trimprefix(workload.demo_url, "https://"), probe_path = "/healthz", paths = ["/${env}/api/*"], api_environment = env } if workload.demo_url != null },
  merge([for env, contract in var.platform.environments : { for key, web in contract.webs : "${env}-${key}" => { hostname = web.hostname, probe_path = "/${env}/${key}/", paths = ["/${env}/${key}", "/${env}/${key}/*"], api_environment = "" } }]...))
}
resource "azurerm_container_app" "certificates" {
  name                         = "${local.prefix}-certificates"
  resource_group_name          = local.entry.shared_resource_group_name
  container_app_environment_id = local.entry.environment_id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  identity {
    type         = "UserAssigned"
    identity_ids = [local.entry.identities.certificates.id]
  }
  registry {
    server   = var.platform.registry_login_server
    identity = local.entry.identities.certificates.id
  }
  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 8080
    transport                  = "http"
    ip_security_restriction {
      name             = "only-waf"
      action           = "Allow"
      ip_address_range = local.entry.gateway_subnet_cidr
    }
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
  template {
    min_replicas = 1
    max_replicas = 1
    container {
      name   = "certificates"
      image  = var.edge_image
      cpu    = 0.25
      memory = "0.5Gi"
      dynamic "env" {
        for_each = {
          AZURE_CLIENT_ID       = local.entry.identities.certificates.client_id
          KEY_VAULT_URI         = local.entry.vault.uri
          LOCK_BLOB_URL         = local.entry.lock_blob_url
          CERTIFICATE_HOSTNAMES = jsonencode(local.hostnames)
          ACME_EMAIL            = var.config.operations.alert_emails[0]
          ACME_DIRECTORY_URL    = var.config.public_entrypoint.acme_directory_url
          RENEW_ENABLED         = tostring(var.config.public_entrypoint.certificate_secret_id == "")
          PUBLIC_PORTALS        = jsonencode(local.portals)
        }
        content {
          name  = env.key
          value = env.value
        }
      }
      liveness_probe {
        transport     = "HTTP"
        port          = 8080
        path          = "/healthz"
        initial_delay = 10
      }
      readiness_probe {
        transport = "HTTP"
        port      = 8080
        path      = "/healthz"
      }
    }
  }
  tags = local.tags
}
module "waf" {
  source                = "../../modules/application_gateway"
  name                  = "${local.prefix}-waf"
  location              = var.config.location
  resource_group_name   = local.entry.resource_group_name
  subnet_id             = local.entry.gateway_subnet_id
  public_ip_id          = local.entry.public_ip_id
  identity_id           = local.entry.identities.waf.id
  certificate_secret_id = local.certificate_secret_id
  hostnames             = local.hostnames
  environment_hosts     = { for env, origin in local.entry.environment_origins : env => trimprefix(origin, "https://") }
  minimum_instances     = var.config.public_entrypoint.minimum_instances
  maximum_instances     = var.config.public_entrypoint.maximum_instances
  workspace_id          = local.entry.workspace_id
  backends              = local.backends
  tags                  = local.tags
  depends_on            = [azurerm_container_app.certificates]
}
output "integration" {
  value = { origin = local.entry.origin, azure_hostname = local.entry.azure_hostname, portals = local.portals, api_urls = { for env, origin in local.entry.environment_origins : env => "${origin}/${env}" }, gateway_id = module.waf.id, certificate_secret_id = local.certificate_secret_id }
}
