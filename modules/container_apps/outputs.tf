output "demo_url" { value = try("https://${azurerm_container_app.example["frontend"].ingress[0].fqdn}", null) }
output "api_url" { value = try("https://${azurerm_container_app.example["tenant"].ingress[0].fqdn}", null) }
output "applications" {
  value = { for key, app in azurerm_container_app.example : key => {
    id           = app.id
    url          = "https://${app.ingress[0].fqdn}"
    port         = app.ingress[0].target_port
    image        = app.template[0].container[0].image
    min_replicas = app.template[0].min_replicas
    max_replicas = app.template[0].max_replicas
  } }
}
output "security" {
  value = {
    application_count = length(azurerm_container_app.example)
    frontend_external = try(azurerm_container_app.example["frontend"].ingress[0].external_enabled, false)
    api_external      = try(azurerm_container_app.example["tenant"].ingress[0].external_enabled, false)
    identities        = { for key, app in azurerm_container_app.example : key => app.identity[0].identity_ids }
    replicas          = { for key, app in azurerm_container_app.example : key => { min = app.template[0].min_replicas, max = app.template[0].max_replicas } }
  }
}
