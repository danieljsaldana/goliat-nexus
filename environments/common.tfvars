# Goliat - Nexus 1.0.0 — valores de ejemplo, no secretos.
# Edita tus copias en .local/; usa configure para completar identidades reales.

# La plataforma es compartida. Conserva shared: Dev y Prod se configuran en sus archivos.
environment = "shared"

# Región principal de Azure. Valida disponibilidad de Cosmos, Container Apps y Functions Flex.
location = "westeurope"

# Días de retención del workspace compartido. Mayor retención puede aumentar el coste.
log_retention_days = 90

# Excepciones HTTPS del ejecutor. No se comparten con las APIs.
management_https_fqdns = []

# Nombre de esta instalación. Usa otro para la demo; forma parte de los nombres y del estado.
name = "acmev1"

# Plan IP: los rangos no pueden solaparse; no reutilices subredes para servicios distintos.
network = {
  # VNet del hub común a Dev y Prod.
  hub_cidr = "10.0.0.0/16"

  # AzureFirewallSubnet, al menos /26.
  firewall_subnet_cidr = "10.0.0.0/26"

  # Reserva para un ejecutor privado; el producto no instala una VPN o VM implícitamente.
  management_subnet_cidr = "10.0.1.0/24"

  # Private Endpoints comunes de ACR y estado.
  endpoints_subnet_cidr = "10.0.2.0/27"

  # Subred exclusiva del Application Gateway compartido. Se recomienda /24; sin ruta 0/0 al Firewall.
  gateway_subnet_cidr = "10.0.4.0/24"

  # Subred delegada /23 para el servicio privado de certificados compartido.
  edge_apps_subnet_cidr = "10.0.8.0/23"
}

# Presupuesto y avisos comunes. El presupuesto alerta, no bloquea el gasto.
operations = {
  # Destinatarios reales de alertas y presupuesto; example.com es ficticio.
  alert_emails = ["operaciones@example.com"]

  # Unidades de la moneda de tu suscripción; valor ilustrativo, no una estimación de precio.
  budget_amount = 300

  # Primer día del mes de inicio (YYYY-MM-01). No cambiarlo en cada apply.
  budget_start_date = "2026-10-01"
}

# IPs públicas autorizadas para el bootstrap del estado. Sustituye la IP de documentación.
operator_ip_ranges = ["203.0.113.10/32"]

# Object ID del operador/grupo que administra la plataforma y registra secretos en Key Vault.
operator_object_id = "00000000-0000-0000-0000-000000000000"

# Entrada compartida con WAF_v2. HTTPS público; las APIs y los datos siguen privados.
public_entrypoint = {
  # true publica las aplicaciones exclusivamente a través del WAF compartido; false conserva el modelo privado.
  enabled = true

  # Vacío usa el FQDN generado por Azure. Para un dominio propio, configura antes su DNS hacia el WAF.
  hostname = ""

  # Mapa opcional dev/prod con dominios propios distintos para separar los orígenes del navegador.
  environment_hostnames = {
  }

  # Capacidad mínima del WAF (1–10). Tiene coste incluso sin peticiones.
  minimum_instances = 1

  # Techo de escalado del WAF; debe ser igual o superior al mínimo.
  maximum_instances = 2

  # Vacío activa ACME y renovación privada. Alternativa: URI del secreto Key Vault sin versión y con permisos de lectura para el WAF; nunca el PFX.
  certificate_secret_id = ""

  # Emisor ACME de producción. Staging solo sirve para pruebas y sus certificados no son de confianza.
  acme_directory_url = "https://acme-v02.api.letsencrypt.org/directory"
}

# restricted-public permite esas IPs al arrancar; private exige ejecutor y DNS privados.
state_access = "restricted-public"

# Replicación del backend de Terraform: LRS, ZRS o GRS; no es un backup de Cosmos.
state_replication = "GRS"

# ID real de la suscripción. configure lo obtiene de az login; los ceros son ficticios.
subscription_id = "00000000-0000-0000-0000-000000000000"

# Etiquetas comunes para propietario y reparto de costes.
tags = {
  CostCenter = "sandbox"
  Owner      = "equipo-plataforma"
}

# Tenant de Microsoft Entra que autentica operadores e identidades administradas.
tenant_id = "00000000-0000-0000-0000-000000000000"
