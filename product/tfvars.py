"""Read native HCL variable files with Terraform and write user-owned presets."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import ConfigError, ROOT

FILES = ("common.tfvars", "dev.tfvars", "prod.tfvars")

COMMENTS = {
    "name": "Nombre de esta instalación. Usa otro para la demo; forma parte de los nombres y del estado.",
    "environment": "La plataforma es compartida. Conserva shared: Dev y Prod se configuran en sus archivos.",
    "location": "Región principal de Azure. Valida disponibilidad de Cosmos, Container Apps y Functions Flex.",
    "subscription_id": "ID real de la suscripción. configure lo obtiene de az login; los ceros son ficticios.",
    "tenant_id": "Tenant de Microsoft Entra que autentica operadores e identidades administradas.",
    "operator_object_id": "Object ID del operador/grupo que administra la plataforma y registra secretos en Key Vault.",
    "operator_ip_ranges": "IPs públicas autorizadas para el bootstrap del estado. Sustituye la IP de documentación.",
    "state_access": "restricted-public permite esas IPs al arrancar; private exige ejecutor y DNS privados.",
    "state_replication": "Replicación del backend de Terraform: LRS, ZRS o GRS; no es un backup de Cosmos.",
    "log_retention_days": "Días de retención del workspace compartido. Mayor retención puede aumentar el coste.",
    "tags": "Etiquetas comunes para propietario y reparto de costes.",
    "network": "Plan IP: los rangos no pueden solaparse; no reutilices subredes para servicios distintos.",
    "hub_cidr": "VNet del hub común a Dev y Prod.",
    "firewall_subnet_cidr": "AzureFirewallSubnet, al menos /26.",
    "management_subnet_cidr": "Reserva para un ejecutor privado; el producto no instala una VPN o VM implícitamente.",
    "endpoints_subnet_cidr": "Private Endpoints comunes de ACR y estado.",
    "vnet_cidr": "VNet propia del entorno, emparejada únicamente con el hub.",
    "apps_subnet_cidr": "Subred delegada de Container Apps, al menos /23.",
    "data_subnet_cidr": "Private Endpoints del entorno: Key Vault, Cosmos, Storage y servicios de aplicación.",
    "functions_subnet_cidr": "Integración de Functions Flex, al menos /27. No puede compartirse con Container Apps.",
    "operations": "Presupuesto y avisos comunes. El presupuesto alerta, no bloquea el gasto.",
    "budget_amount": "Unidades de la moneda de tu suscripción; valor ilustrativo, no una estimación de precio.",
    "budget_start_date": "Primer día del mes de inicio (YYYY-MM-01). No cambiarlo en cada apply.",
    "alert_emails": "Destinatarios reales de alertas y presupuesto; example.com es ficticio.",
    "management_https_fqdns": "Excepciones HTTPS del ejecutor. No se comparten con las APIs.",
    "zone_redundancy": "Redundancia zonal de Container Apps. No activa multirregión de Cosmos.",
    "deploy_demo": "Etiqueta los portales como evaluación. No cambia a datos en memoria; las piezas se activan con enable_*.",
    "web_portals": "Un Static Web App por entrada. Clave libre de 1–30 caracteres; añade entradas para más portales, o usa {} para ninguno.",
    "view": "Interfaz del ejemplo: tenant para solicitudes, admin para operaciones. No concede permisos Entra.",
    "enable_dns": "Gestionar los registros DNS públicos opcionales. El DNS privado de la plataforma sigue siendo necesario.",
    "enable_api_platform": "API de configuración y catálogo del portal, detrás del gateway privado.",
    "enable_api_tenant": "API de solicitudes: persiste en Cosmos y publica eventos.",
    "enable_api_activities": "API de lectura de actividades generadas por la Function.",
    "enable_storage_account": "Storage privado para paquetes, host de Functions y colas de eventos; autenticación Entra.",
    "enable_cosmosdb": "Cuenta y base MongoDB de Cosmos con acceso privado; exige Key Vault.",
    "enable_content_storage": "Storage separado para adjuntos/contenido, con lifecycle solo en esos datos.",
    "enable_key_vault": "Vault privado por entorno. Necesario para Cosmos, Functions y tokens de despliegue web.",
    "enable_event_processing": "Function que consume la cola de solicitudes; requiere Storage, Cosmos y Key Vault.",
    "enable_event_grid": "Topic Event Grid publicador opcional; requiere API tenant y eventos. Sin clave local ni suscripciones automáticas.",
    "cosmosdb_config": "Cosmos DB API MongoDB 7.0. Configura capacidad, región y política de backup.",
    "database_name": "Nombre lógico de la base MongoDB; se crean colecciones de solicitudes y actividades.",
    "mongo_server_version": "Versión de compatibilidad MongoDB validada por esta versión del producto.",
    "is_serverless": "true: pago por consumo, sin throughput reservado. No admite Free Tier.",
    "throughput": "RU/s manuales (mínimo 400). null para Serverless o autoscale.",
    "max_throughput": "Máximo RU/s de autoscale, múltiplo de 1000; null para manual o Serverless.",
    "free_tier_enabled": "Solo una cuenta elegible por suscripción, y nunca en Serverless. Se desactiva por defecto.",
    "backup_interval_minutes": "Backup periódico: 60–1440 minutos. No equivale a restauración continua/PITR.",
    "backup_retention_hours": "Horas de conservación: al menos dos intervalos y como máximo 720 horas.",
    "backup_storage_redundancy": "Redundancia del backup: Local, Zone o Geo. Revisar coste y necesidades de recuperación.",
    "storage": "Ajustes de las cuentas privadas del entorno; sin claves en estos tfvars.",
    "replication": "Replicación Storage: LRS, ZRS o GRS.",
    "content_cool_after_days": "Mover adjuntos inactivos a Cool. No se aplica a paquetes ni al estado del host Functions.",
    "soft_delete_days": "Días de borrado reversible de blobs y contenedores.",
    "web": "Static Web Apps. El contenido web es público; el gateway y los datos permanecen privados.",
    "sku": "Free o Standard. Comprueba cuotas de webs por suscripción antes de habilitar todos los portales.",
    "functions": "Functions Flex Consumption: procesamiento asíncrono, reintentos y recuperación del outbox.",
    "runtime_version": "Versión Node.js del código de eventos suministrado (24).",
    "maximum_instances": "Límite máximo de escala de Functions Flex (40–1000), no instancias siempre encendidas.",
    "memory_mb": "Memoria por instancia Flex: 512, 2048 o 4096 MiB.",
    "access": "Acceso de usuarios/grupos Entra: Requester solo ve sus datos; Operator opera el entorno.",
    "requester_object_ids": "Object IDs de usuarios/grupos con rol Requester y acceso al portal. Vacío: no hay solicitantes adicionales.",
    "operator_object_ids": "Object IDs de operadores. Vacío usa operator_object_id de common, que debe ser usuario/grupo para esta asignación.",
    "public_entrypoint": "Entrada compartida con WAF_v2. HTTPS público; las APIs y los datos siguen privados.",
    "enabled": "true publica las aplicaciones exclusivamente a través del WAF compartido; false conserva el modelo privado.",
    "hostname": "Vacío usa el FQDN generado por Azure. Para un dominio propio, configura antes su DNS hacia el WAF.",
    "environment_hostnames": "Mapa opcional dev/prod con dominios propios distintos para separar los orígenes del navegador.",
    "minimum_instances": "Capacidad mínima del WAF (1–10). Tiene coste incluso sin peticiones.",
    "certificate_secret_id": "Vacío activa ACME y renovación privada. Alternativa: URI del secreto Key Vault sin versión y con permisos de lectura para el WAF; nunca el PFX.",
    "acme_directory_url": "Emisor ACME de producción. Staging solo sirve para pruebas y sus certificados no son de confianza.",
    "gateway_subnet_cidr": "Subred exclusiva del Application Gateway compartido. Se recomienda /24; sin ruta 0/0 al Firewall.",
    "edge_apps_subnet_cidr": "Subred delegada /23 para el servicio privado de certificados compartido.",
    "public_dns": "DNS propio opcional. Por defecto zone_name vacío: nombres Azure, sin comprar dominio ni crear zona pública.",
    "zone_name": "Vacío usa nombres Azure. Para DNS propio indica una zona de tu propiedad; vinculación y certificado se configuran aparte.",
    "create_zone": "true crea la zona; false utiliza una existente cuando zone_name no está vacío.",
    "github_repository": "Repositorio organización/nombre para OIDC; vacío desactiva el publicador opcional.",
    "github_environment": "Environment GitHub autorizado; usa subjects diferentes en Dev y Prod.",
    "additional_https_fqdns": "Excepciones HTTPS de este entorno; evita comodines amplios.",
    "sample": "Capacidad de las APIs y gateway del portal de ejemplo. Ajustar tras medir la carga.",
    "version": "Versión lógica del código. El despliegue utiliza imágenes por digest inmutable.",
    "frontend_min_replicas": "Mínimo de réplicas del gateway web privado.",
    "frontend_max_replicas": "Máximo de réplicas del gateway.",
    "api_min_replicas": "Mínimo de réplicas por API habilitada.",
    "api_max_replicas": "Máximo de réplicas por API habilitada.",
    "frontend_port": "Puerto interno del gateway Nginx.",
    "api_port": "Puerto interno de cada API Node.js.",
    "cpu": "vCPU por réplica Consumption; debe corresponder con memory.",
    "memory": "Memoria por réplica: 0.5Gi con 0.25 vCPU, por ejemplo.",
    "http_concurrency": "Concurrencia objetivo de la regla HTTP; no es una garantía de rendimiento.",
}


def read_environment_directory(path):
    directory = Path(path).resolve()
    if not directory.is_dir():
        if directory.name not in FILES:
            raise ConfigError("Selecciona la carpeta environments o su common.tfvars, dev.tfvars o prod.tfvars.")
        directory = directory.parent
    files = [directory / name for name in FILES]
    if any(not file.is_file() for file in files):
        raise ConfigError(f"{directory} debe contener common.tfvars, dev.tfvars y prod.tfvars: forman una única plataforma compartida.")
    if not shutil.which("terraform"):
        raise ConfigError("Se necesita Terraform para leer los archivos HCL .tfvars.")
    template = json.loads((ROOT / "examples/shared.json").read_text())
    names = [key for key in template if key != "environments"]
    variables = names + ["dev", "prod"]
    # This scratch module has no resources/providers/backend and cannot deploy.
    with tempfile.TemporaryDirectory(prefix="lz-tfvars-") as folder:
        Path(folder, "main.tf").write_text("\n".join(f'variable "{name}" {{\n  type = any\n  default = null\n}}' for name in variables))
        expression = "jsonencode({" + ",".join(f"{name}=var.{name}" for name in names) + ",environments={dev=var.dev,prod=var.prod}})\n"
        env = {key: value for key, value in os.environ.items() if not key.startswith(("TF_VAR_", "TF_CLI_ARGS")) and key not in ("TF_WORKSPACE", "TF_DATA_DIR")}
        env["TF_WORKSPACE"] = "default"
        try:
            process = subprocess.run(["terraform", f"-chdir={folder}", "console", "-no-color", *[f"-var-file={file}" for file in files]], input=expression, text=True, capture_output=True, env=env, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise ConfigError("Terraform no terminó de leer los tfvars en 30 segundos.") from exc
        if process.returncode or process.stderr.strip():
            raise ConfigError(f"No se pudieron leer los tfvars: {process.stderr.strip()}")
        if "Warning:" in process.stdout:
            diagnostic = process.stdout.split('\n"', 1)[0].strip()
            raise ConfigError(f"Revisa los tfvars: {diagnostic}")
        try:
            return json.loads(json.loads(process.stdout))
        except (TypeError, ValueError) as exc:
            raise ConfigError("Terraform no devolvió una configuración JSON válida para los tfvars.") from exc


def hcl_value(value, level=0, context=""):
    if isinstance(value, dict):
        lines = ["{"]
        for key, item in value.items():
            if key in COMMENTS:
                if len(lines) > 1:
                    lines.append("")
                description = "Techo de escalado del WAF; debe ser igual o superior al mínimo." if context == "public_entrypoint" and key == "maximum_instances" else COMMENTS[key]
                lines.append("  " * (level + 1) + "# " + description)
            label = key if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key) else hcl_value(key)
            lines.append("  " * (level + 1) + label + " = " + hcl_value(item, level + 1, key))
        return "\n".join(lines) + "\n" + "  " * level + "}"
    if isinstance(value, list):
        return "[" + ", ".join(hcl_value(item, level) for item in value) + "]"
    if isinstance(value, str):
        return json.dumps(value.replace("${", "$${").replace("%{", "%%{"), ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def write_environment_directory(directory, cfg):
    directory = Path(directory)
    if directory.exists():
        raise ConfigError(f"{directory} ya existe; no se sobrescribirá.")
    directory.mkdir(parents=True, mode=0o700)
    sections = {"common": {key: value for key, value in cfg.items() if key != "environments"}, **{key: {key: cfg["environments"][key]} for key in ("dev", "prod")}}
    for name, values in sections.items():
        path = directory / f"{name}.tfvars"
        blocks = []
        for key, value in values.items():
            description = COMMENTS.get(key, f"Entorno {key}: componentes opcionales y servicios propios. Comparte el hub definido en common.tfvars.")
            blocks.append(f"# {description}\n{key} = {hcl_value(value, context=key)}")
        path.write_text(f"# Goliat - Nexus {(ROOT / 'VERSION').read_text().strip()} — valores de ejemplo, no secretos.\n# Edita tus copias en .local/; usa configure para completar identidades reales.\n\n" + "\n\n".join(blocks) + "\n")
        path.chmod(0o600)
