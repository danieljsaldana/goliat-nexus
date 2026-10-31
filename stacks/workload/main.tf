terraform {
  backend "azurerm" {}
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Selecciona dev o prod."
  }
}

variable "sample_images" {
  description = "Imágenes publicadas por el CLI, fijadas por digest."
  type        = map(string)
  default     = {}
}

variable "platform" { type = any }
locals { settings = var.config.environments[var.environment] }
module "workload" {
  source          = "../../modules/workload"
  prefix          = "${var.config.name}-${var.environment}"
  location        = var.config.location
  platform        = var.platform
  zone_redundancy = var.config.environments[var.environment].zone_redundancy
  features        = { for key in ["enable_api_platform", "enable_api_tenant", "enable_api_activities", "enable_event_processing"] : key => local.settings[key] }
  tags            = merge(local.tags, { Environment = var.environment })
  sample          = var.config.environments[var.environment].sample
  sample_images   = var.sample_images
}
output "integration" {
  value = {
    environment_id = module.workload.environment_id
    demo_url       = module.workload.demo_url
    api_url        = module.workload.api_url
    applications   = module.workload.applications
    cosmos         = var.platform.cosmos
    webs           = var.platform.webs
    functions      = try(module.events[0].integration, null)
  }
}

module "events" {
  count               = local.settings.enable_event_processing ? 1 : 0
  tenant_id           = var.config.tenant_id
  source              = "../../modules/event_processing"
  prefix              = "${var.config.name}-${var.environment}-${local.settings.suffix}"
  location            = var.config.location
  resource_group_name = var.platform.workload_resource_group
  settings            = local.settings.functions
  identity            = var.platform.identities.functions
  subnet_id           = var.platform.functions_subnet_id
  endpoint_subnet_id  = var.platform.endpoint_subnet_id
  private_dns_zone_id = var.platform.functions_dns_zone_id
  vault               = var.platform.vault
  host_vault          = var.platform.host_vault
  storage             = var.platform.storage
  cosmos              = var.platform.cosmos
  workspace_id        = var.platform.workspace_id
  tags                = merge(local.tags, { Environment = var.environment })
}
