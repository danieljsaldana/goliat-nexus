resource "azurerm_web_application_firewall_policy" "this" {
  name                = "${var.name}-policy"
  resource_group_name = var.resource_group_name
  location            = var.location
  policy_settings {
    enabled                     = true
    mode                        = "Prevention"
    request_body_check          = true
    max_request_body_size_in_kb = 128
    file_upload_limit_in_mb     = 10
  }
  dynamic "custom_rules" {
    for_each = var.environment_hosts
    content {
      name      = "${custom_rules.key}HostnameBoundary"
      priority  = 10 + index(sort(keys(var.environment_hosts)), custom_rules.key)
      rule_type = "MatchRule"
      action    = "Block"
      match_conditions {
        match_variables { variable_name = "RequestUri" }
        operator     = "Regex"
        match_values = ["^/${custom_rules.key}(/|$)"]
      }
      match_conditions {
        match_variables {
          variable_name = "RequestHeaders"
          selector      = "Host"
        }
        operator           = "Equal"
        negation_condition = true
        match_values       = [custom_rules.value, "${custom_rules.value}:443"]
        transforms         = ["Lowercase"]
      }
    }
  }
  managed_rules {
    managed_rule_set {
      type    = "OWASP"
      version = "3.2"
    }
  }
  tags = var.tags
}
resource "azurerm_network_security_group" "gateway" {
  name                = "${var.name}-nsg"
  resource_group_name = var.resource_group_name
  location            = var.location
  security_rule {
    name                       = "public-http-https"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_ranges    = ["80", "443"]
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }
  security_rule {
    name                       = "azure-gateway-management"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "65200-65535"
    source_address_prefix      = "GatewayManager"
    destination_address_prefix = "*"
  }
  security_rule {
    name                       = "azure-load-balancer-probes"
    priority                   = 120
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "AzureLoadBalancer"
    destination_address_prefix = "*"
  }
  security_rule {
    name                       = "deny-other-ingress"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
  tags = var.tags
}
resource "azurerm_subnet_network_security_group_association" "gateway" {
  subnet_id                 = var.subnet_id
  network_security_group_id = azurerm_network_security_group.gateway.id
}
resource "azurerm_application_gateway" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  firewall_policy_id  = azurerm_web_application_firewall_policy.this.id
  http2_enabled       = true
  sku {
    name = "WAF_v2"
    tier = "WAF_v2"
  }
  autoscale_configuration {
    min_capacity = var.minimum_instances
    max_capacity = var.maximum_instances
  }
  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }
  gateway_ip_configuration {
    name      = "gateway"
    subnet_id = var.subnet_id
  }
  frontend_ip_configuration {
    name                 = "public"
    public_ip_address_id = var.public_ip_id
  }
  frontend_port {
    name = "http"
    port = 80
  }
  frontend_port {
    name = "https"
    port = 443
  }
  ssl_certificate {
    name                = "public-tls"
    key_vault_secret_id = var.certificate_secret_id
  }
  ssl_policy {
    policy_type = "Predefined"
    policy_name = "AppGwSslPolicy20220101S"
  }
  http_listener {
    name                           = "http"
    frontend_ip_configuration_name = "public"
    frontend_port_name             = "http"
    protocol                       = "Http"
    host_names                     = var.hostnames
  }
  http_listener {
    name                           = "https"
    frontend_ip_configuration_name = "public"
    frontend_port_name             = "https"
    protocol                       = "Https"
    host_names                     = var.hostnames
    require_sni                    = true
    ssl_certificate_name           = "public-tls"
  }
  dynamic "backend_address_pool" {
    for_each = var.backends
    content {
      name  = backend_address_pool.key
      fqdns = [backend_address_pool.value.hostname]
    }
  }
  dynamic "backend_http_settings" {
    for_each = var.backends
    content {
      name                                 = backend_http_settings.key
      cookie_based_affinity                = "Disabled"
      port                                 = 443
      protocol                             = "Https"
      request_timeout                      = 120
      pick_host_name_from_backend_address  = true
      probe_name                           = backend_http_settings.key
      certificate_chain_validation_enabled = true
      sni_validation_enabled               = true
    }
  }
  dynamic "probe" {
    for_each = var.backends
    content {
      name                                      = probe.key
      protocol                                  = "Https"
      pick_host_name_from_backend_http_settings = true
      path                                      = probe.value.probe_path
      interval                                  = 30
      timeout                                   = 30
      unhealthy_threshold                       = 3
      match { status_code = ["200-399"] }
    }
  }
  redirect_configuration {
    name                 = "https-only"
    redirect_type        = "Permanent"
    target_listener_name = "https"
    include_path         = true
    include_query_string = true
  }
  rewrite_rule_set {
    name = "forwarded-headers"
    rewrite_rule {
      name          = "trusted-forwarded-host"
      rule_sequence = 10
      request_header_configuration {
        header_name  = "X-Forwarded-Host"
        header_value = "{http_req_host}"
      }
      request_header_configuration {
        header_name  = "X-Forwarded-Proto"
        header_value = "https"
      }
    }
  }
  dynamic "rewrite_rule_set" {
    for_each = { for key, backend in var.backends : key => backend if backend.api_environment != "" }
    content {
      name = "${rewrite_rule_set.key}-api"
      rewrite_rule {
        name          = "remove-environment-prefix"
        rule_sequence = 10
        condition {
          variable    = "var_uri_path"
          pattern     = "^/${rewrite_rule_set.value.api_environment}/(api/.*)$"
          ignore_case = false
          negate      = false
        }
        url {
          path    = "/{var_uri_path_1}"
          reroute = false
        }
        request_header_configuration {
          header_name  = "X-Forwarded-Host"
          header_value = "{http_req_host}"
        }
        request_header_configuration {
          header_name  = "X-Forwarded-Proto"
          header_value = "https"
        }
      }
    }
  }
  url_path_map {
    name                                = "http-challenge-only"
    default_redirect_configuration_name = "https-only"
    path_rule {
      name                       = "acme-http-01"
      paths                      = ["/.well-known/acme-challenge/*"]
      backend_address_pool_name  = "certificates"
      backend_http_settings_name = "certificates"
    }
  }
  url_path_map {
    name                               = "applications"
    default_backend_address_pool_name  = "certificates"
    default_backend_http_settings_name = "certificates"
    default_rewrite_rule_set_name      = "forwarded-headers"
    path_rule {
      name                       = "entry-health"
      paths                      = ["/healthz"]
      backend_address_pool_name  = "certificates"
      backend_http_settings_name = "certificates"
    }
    dynamic "path_rule" {
      for_each = { for key, backend in var.backends : key => backend if key != "certificates" }
      content {
        name                       = path_rule.key
        paths                      = path_rule.value.paths
        backend_address_pool_name  = path_rule.key
        backend_http_settings_name = path_rule.key
        rewrite_rule_set_name      = path_rule.value.api_environment != "" ? "${path_rule.key}-api" : "forwarded-headers"
      }
    }
  }
  request_routing_rule {
    name               = "http"
    priority           = 100
    rule_type          = "PathBasedRouting"
    http_listener_name = "http"
    url_path_map_name  = "http-challenge-only"
  }
  request_routing_rule {
    name               = "https"
    priority           = 200
    rule_type          = "PathBasedRouting"
    http_listener_name = "https"
    url_path_map_name  = "applications"
  }
  lifecycle { ignore_changes = [tags["CertificateVersion"]] }
  tags       = var.tags
  depends_on = [azurerm_subnet_network_security_group_association.gateway]
}
resource "azurerm_monitor_diagnostic_setting" "this" {
  name                       = "audit"
  target_resource_id         = azurerm_application_gateway.this.id
  log_analytics_workspace_id = var.workspace_id
  enabled_log { category_group = "allLogs" }
  enabled_metric { category = "AllMetrics" }
}
output "id" { value = azurerm_application_gateway.this.id }
output "security" { value = { mode = azurerm_web_application_firewall_policy.this.policy_settings[0].mode, policy = azurerm_application_gateway.this.firewall_policy_id, certificate_reference = var.certificate_secret_id, hostname_rules = { for rule in azurerm_web_application_firewall_policy.this.custom_rules : rule.name => rule.action } } }
