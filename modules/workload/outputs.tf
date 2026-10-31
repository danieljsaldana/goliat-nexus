output "environment_id" { value = module.container_app_environment.id }
output "demo_url" { value = module.container_apps.demo_url }
output "api_url" { value = module.container_apps.api_url }
output "applications" { value = module.container_apps.applications }
output "security" { value = merge(module.container_app_environment.security, module.container_apps.security) }
