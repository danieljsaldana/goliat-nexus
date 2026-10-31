# Aplicaciones, permisos por API y alertas; el entorno se recibe como entrada.
locals {
  roles = [for role in ["platform", "tenant", "activities"] : role if var.features["enable_api_${role}"]]
  examples = merge({ for role in local.roles : role => {
    port         = var.sample.api_port
    min_replicas = var.sample.api_min_replicas
    max_replicas = var.sample.api_max_replicas
    identity     = var.platform.identities[role].id
    readiness    = "/readyz"
    image        = "api"
    env = {
      PORT                    = tostring(var.sample.api_port)
      API_ROLE                = role
      AUTH_TENANT_ID          = var.platform.auth.tenant_id
      AUTH_AUDIENCE           = var.platform.auth.api_client_id
      AUTH_ALLOWED_CLIENT_IDS = join(",", var.platform.auth.allowed_client_ids)
      AZURE_CLIENT_ID         = var.platform.identities[role].client_id
      KEY_VAULT_URI           = var.platform.vault.uri
      COSMOS_SECRET_NAME      = role == "tenant" ? var.platform.cosmos.secret_name : var.platform.cosmos.readonly_secret_name
      COSMOS_DATABASE         = var.platform.cosmos.name
      COSMOS_HOST             = var.platform.cosmos.host
      EVENTS_QUEUE_URI        = try(var.platform.storage.queue_uri, "")
      EVENTS_QUEUE_NAME       = "requests-events"
      EVENTS_ENABLED          = tostring(var.features.enable_event_processing)
      EVENT_GRID_ENDPOINT     = var.platform.events_endpoint
    }
    } }, length(local.roles) > 0 ? { frontend = {
    port         = var.sample.frontend_port
    min_replicas = var.sample.frontend_min_replicas
    max_replicas = var.sample.frontend_max_replicas
    identity     = var.platform.identities.frontend.id
    readiness    = "/healthz"
    image        = "frontend"
    env          = merge({ PORT = tostring(var.sample.frontend_port), CORS_ORIGINS = try(var.platform.public_origin, "") != "" ? replace(var.platform.public_origin, ".", "\\.") : join("|", [for web in var.platform.webs : "https://${replace(web.hostname, ".", "\\.")}"]) }, { for role in ["platform", "tenant", "activities"] : "API_${upper(role)}_ORIGIN" => contains(local.roles, role) ? "https://${var.prefix}-${role}.internal.${var.environment_domain}" : "http://127.0.0.1:9" })
  } } : {})
}

resource "azurerm_container_app" "example" {
  for_each                     = local.examples
  name                         = "${var.prefix}-${each.key}"
  resource_group_name          = var.platform.workload_resource_group
  container_app_environment_id = var.environment_id
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"
  identity {
    type         = "UserAssigned"
    identity_ids = [each.value.identity]
  }
  registry {
    server   = var.platform.registry_login_server
    identity = each.value.identity
  }
  ingress {
    external_enabled           = each.key == "frontend"
    allow_insecure_connections = false
    target_port                = each.value.port
    transport                  = "http"
    dynamic "ip_security_restriction" {
      for_each = each.key == "frontend" && try(var.platform.public_origin, "") != "" ? [1] : []
      content {
        name             = "only-shared-waf"
        action           = "Allow"
        ip_address_range = var.platform.gateway_subnet_cidr
      }
    }
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
  template {
    min_replicas = each.value.min_replicas
    max_replicas = each.value.max_replicas
    http_scale_rule {
      name                = "http-concurrency"
      concurrent_requests = tostring(var.sample.http_concurrency)
    }
    container {
      name   = each.key
      image  = lookup(var.sample_images, each.value.image, "missing-publication")
      cpu    = var.sample.cpu
      memory = var.sample.memory
      dynamic "env" {
        for_each = each.value.env
        content {
          name  = env.key
          value = env.value
        }
      }
      liveness_probe {
        transport        = "HTTP"
        port             = each.value.port
        path             = "/healthz"
        initial_delay    = 10
        interval_seconds = 30
      }
      readiness_probe {
        transport        = "HTTP"
        port             = each.value.port
        path             = each.value.readiness
        interval_seconds = 10
      }
    }
  }
  depends_on = [azurerm_role_assignment.cosmos_secret, azurerm_role_assignment.queue_sender]
  tags       = merge(var.tags, { Purpose = "Reference application" })
}

resource "azurerm_monitor_metric_alert" "http_errors" {
  for_each            = azurerm_container_app.example
  name                = "${var.prefix}-${each.key}-http5xx"
  resource_group_name = var.platform.workload_resource_group
  scopes              = [each.value.id]
  severity            = 2
  frequency           = "PT1M"
  window_size         = "PT5M"
  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "Requests"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 5
    dimension {
      name     = "statusCodeCategory"
      operator = "Include"
      values   = ["5xx"]
    }
  }
  action { action_group_id = var.platform.action_group_id }
  tags = var.tags
}

# Las APIs solo leen el secreto de Cosmos, no los tokens web ni claves del host.
resource "azurerm_role_assignment" "cosmos_secret" {
  for_each                         = toset(local.roles)
  scope                            = "${var.platform.vault.id}/secrets/${each.key == "tenant" ? var.platform.cosmos.secret_name : var.platform.cosmos.readonly_secret_name}"
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = var.platform.identities[each.key].principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
resource "azurerm_role_assignment" "queue_sender" {
  count                            = var.features.enable_api_tenant && var.features.enable_event_processing ? 1 : 0
  scope                            = "${var.platform.storage.id}/queueServices/default/queues/requests-events"
  role_definition_name             = "Storage Queue Data Message Sender"
  principal_id                     = var.platform.identities.tenant.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
