mock_provider "azurerm" {}
mock_provider "azuread" {}
run "waf_public_security" {
  command = plan
  assert {
    condition     = module.waf.security.mode == "Prevention"
    error_message = "La entrada pública debe bloquear ataques con WAF."
  }
  assert {
    condition     = endswith(module.waf.security.certificate_reference, "/secrets/waf-tls")
    error_message = "El certificado se consume desde Key Vault y sin fijar versión."
  }
  assert {
    condition     = azurerm_container_app.certificates.ingress[0].allow_insecure_connections == false && azurerm_container_app.certificates.ingress[0].ip_security_restriction[0].ip_address_range == var.config.network.gateway_subnet_cidr
    error_message = "El emisor de certificados debe permanecer privado, con entrada limitada al WAF."
  }
}
