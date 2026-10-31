# Composición estable de los módulos reutilizables de cómputo.
module "container_app_environment" {
  source                             = "../container_app_environment"
  prefix                             = var.prefix
  location                           = var.location
  resource_group_name                = var.platform.workload_resource_group
  infrastructure_subnet_id           = var.platform.apps_subnet_id
  infrastructure_resource_group_name = var.platform.managed_resource_group
  log_analytics_workspace_id         = var.platform.workspace_id
  vnet_ids                           = var.platform.vnet_ids
  zone_redundancy                    = var.zone_redundancy
  tags                               = var.tags
}
module "container_apps" {
  source             = "../container_apps"
  prefix             = var.prefix
  location           = var.location
  platform           = var.platform
  features           = var.features
  sample             = var.sample
  sample_images      = var.sample_images
  environment_id     = module.container_app_environment.id
  environment_domain = module.container_app_environment.default_domain
  tags               = var.tags
}
