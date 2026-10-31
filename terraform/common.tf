terraform {
  required_version = ">= 1.9.0, < 2.0.0"
  required_providers {
    azuread = { source = "hashicorp/azuread", version = "= 3.10.0" }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.12.0"
    }
  }
}

provider "azurerm" {
  subscription_id         = var.config.subscription_id
  tenant_id               = var.config.tenant_id
  client_id               = try(var.deployment_identity.client_id, null)
  client_certificate_path = try(var.deployment_identity.client_certificate_path, null)
  use_cli                 = var.deployment_identity == null ? null : false
  storage_use_azuread     = true
  # El CLI registra únicamente los namespaces utilizados por el producto.
  resource_provider_registrations = "none"
  features {
    storage {
      data_plane_available = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "azuread" { tenant_id = var.config.tenant_id }

# El broker inyecta solo ID y ruta efímera. La clave privada nunca entra en Terraform.
# AzureAD conserva la sesión CLI del operador y no recibe privilegios de directorio en el SPN.
variable "deployment_identity" {
  type    = object({ client_id = string, client_certificate_path = string })
  default = null
}

variable "config" {
  description = "Una plataforma compartida y dos entornos aislados; sin secretos."
  type = object({
    name                   = string
    environment            = string
    location               = string
    subscription_id        = string
    tenant_id              = string
    operator_object_id     = string
    operator_ip_ranges     = list(string)
    state_access           = string
    state_replication      = string
    suffix                 = string
    log_retention_days     = number
    management_https_fqdns = list(string)
    operations             = object({ budget_amount = number, budget_start_date = string, alert_emails = list(string) })
    tags                   = map(string)
    network                = object({ hub_cidr = string, firewall_subnet_cidr = string, management_subnet_cidr = string, endpoints_subnet_cidr = string, gateway_subnet_cidr = string, edge_apps_subnet_cidr = string })
    public_entrypoint      = object({ enabled = bool, hostname = string, environment_hostnames = map(string), minimum_instances = number, maximum_instances = number, certificate_secret_id = string, acme_directory_url = string })
    environments = map(object({
      suffix                  = string
      zone_redundancy         = bool
      deploy_demo             = bool
      github_repository       = string
      github_environment      = string
      additional_https_fqdns  = list(string)
      enable_dns              = bool
      enable_api_platform     = bool
      enable_api_tenant       = bool
      enable_api_activities   = bool
      enable_storage_account  = bool
      enable_cosmosdb         = bool
      enable_content_storage  = bool
      enable_key_vault        = bool
      enable_event_processing = bool
      enable_event_grid       = bool
      network                 = object({ vnet_cidr = string, apps_subnet_cidr = string, data_subnet_cidr = string, functions_subnet_cidr = string })
      cosmosdb_config         = object({ location = optional(string), database_name = string, mongo_server_version = string, is_serverless = bool, throughput = number, max_throughput = number, free_tier_enabled = bool, backup_interval_minutes = number, backup_retention_hours = number, backup_storage_redundancy = string })
      storage                 = object({ replication = string, content_cool_after_days = number, soft_delete_days = number })
      web                     = object({ sku = string, location = string })
      web_portals             = map(object({ view = optional(string, "tenant") }))
      functions               = object({ runtime_version = string, maximum_instances = number, memory_mb = number })
      public_dns              = object({ zone_name = string, create_zone = bool })
      access                  = object({ requester_object_ids = list(string), operator_object_ids = list(string) })

      sample = object({ version = string, frontend_min_replicas = number, frontend_max_replicas = number, api_min_replicas = number, api_max_replicas = number, frontend_port = number, api_port = number, cpu = number, memory = string, http_concurrency = number })
    }))
  })
  validation {
    condition     = var.config.environment == "shared" && toset(keys(var.config.environments)) == toset(["dev", "prod"])
    error_message = "La plataforma compartida requiere Dev y Prod. No es compatible con aplicar directamente estados 0.2."
  }
  validation {
    condition = alltrue([for env in var.config.environments : alltrue([
      for name, portal in env.web_portals : length(name) <= 30 && can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", name)) && contains(["tenant", "admin"], portal.view)
    ])])
    error_message = "web_portals requiere claves de 1–30 caracteres en minúsculas, números y guiones; view debe ser tenant o admin."
  }
}
locals {
  prefix = "${var.config.name}-shared"
  tags   = merge(var.config.tags, { ManagedBy = "Terraform", Product = "Goliat - Nexus", Environment = "shared", Project = var.config.name })
}
