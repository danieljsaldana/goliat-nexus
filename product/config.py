"""Typed configuration for one shared platform consumed by Dev and Prod."""
import copy
import hashlib
import ipaddress
import json
import re
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENTS = ("dev", "prod")
FEATURES = ("enable_dns", "enable_api_platform", "enable_api_tenant", "enable_api_activities", "enable_storage_account", "enable_cosmosdb", "enable_content_storage", "enable_key_vault", "enable_event_processing", "enable_event_grid")
STAGES = ("foundation", "platform", *ENVIRONMENTS)


class ConfigError(ValueError):
    pass


def read_config(path, *, examples=False):
    if Path(path).is_dir() or Path(path).suffix == ".tfvars":
        from .tfvars import read_environment_directory
        return normalize(read_environment_directory(path), examples=examples)
    try:
        raw = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"No se puede leer {path}: {exc}") from exc
    # Native Terraform JSON assigns values by variable name: {"config": {...}}.
    # Keep the original flat JSON input compatible, and reject stage contracts.
    if isinstance(raw, dict) and "config" in raw:
        if set(raw) != {"config"}:
            raise ConfigError("El archivo de usuario tfvars debe contener solo config. Los contratos por etapa los genera el CLI; no uses inputs.auto.tfvars.json como configuración de entrada.")
        raw = raw["config"]
    return normalize(raw, examples=examples)


def merge_section(value, template, name):
    if not isinstance(value, dict) or set(value) - set(template):
        raise ConfigError(f"{name}: campos desconocidos o formato inválido.")
    return {**copy.deepcopy(template), **value}


def fqdns(value, name):
    if not isinstance(value, list) or any(not isinstance(v, str) or not re.fullmatch(r"(?:\*\.)?[a-z0-9-]+(?:\.[a-z0-9-]+)+", v) for v in value):
        raise ConfigError(f"{name}: usa dominios concretos, nunca '*'.")


def validate_environment(env, name, *, examples):
    for key in ("zone_redundancy", "deploy_demo", *FEATURES):
        if type(env[key]) is not bool:
            raise ConfigError(f"{name}.{key} debe ser booleano.")
    repo = env["github_repository"]
    if not isinstance(repo, str) or (repo and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)):
        raise ConfigError(f"{name}.github_repository: organización/repositorio o vacío.")
    if not isinstance(env["github_environment"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", env["github_environment"]):
        raise ConfigError(f"{name}.github_environment: formato inválido.")
    fqdns(env["additional_https_fqdns"], f"{name}.additional_https_fqdns")
    api = any(env[key] for key in FEATURES if key.startswith("enable_api_"))
    portals = env["web_portals"]
    if not isinstance(portals, dict):
        raise ConfigError(f"{name}.web_portals debe ser un mapa; usa {{}} para omitir los portales.")
    for portal_id, portal in portals.items():
        if not isinstance(portal_id, str) or len(portal_id) > 30 or not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", portal_id):
            raise ConfigError(f"{name}.web_portals: claves de 1–30 caracteres, minúsculas, números y guiones entre palabras.")
        portal = merge_section(portal, {"view": "tenant"}, f"{name}.web_portals.{portal_id}")
        if portal["view"] not in ("tenant", "admin"):
            raise ConfigError(f"{name}.web_portals.{portal_id}.view: la interfaz de ejemplo admite tenant o admin.")
        portals[portal_id] = portal
    web = bool(portals)
    if (api or web or env["enable_cosmosdb"] or env["enable_event_processing"]) and not env["enable_key_vault"]:
        raise ConfigError(f"{name}: las aplicaciones, Cosmos y Functions requieren enable_key_vault para sus secretos.")
    if (api or env["enable_event_processing"]) and not env["enable_cosmosdb"]:
        raise ConfigError(f"{name}: APIs y procesamiento de eventos requieren Cosmos DB.")
    if env["enable_event_processing"] and not env["enable_storage_account"]:
        raise ConfigError(f"{name}: Functions requiere Storage para host, paquetes y cola de eventos.")
    if env["enable_event_grid"] and (not env["enable_api_tenant"] or not env["enable_event_processing"]):
        raise ConfigError(f"{name}: Event Grid requiere enable_api_tenant y enable_event_processing para publicar el outbox.")
    db, sample = env["cosmosdb_config"], env["sample"]
    if db["location"] is not None and (not isinstance(db["location"], str) or not re.fullmatch(r"[a-z]+", db["location"])):
        raise ConfigError(f"{name}.cosmosdb_config.location: usa una región Azure o null para heredar la principal.")
    if not isinstance(db["database_name"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,39}", db["database_name"]):
        raise ConfigError(f"{name}.cosmosdb_config.database_name: nombre inválido.")
    if db["mongo_server_version"] != "7.0":
        raise ConfigError(f"{name}: Nexus valida la API MongoDB 7.0; migra explícitamente las cuentas 4.2 anteriores.")
    if type(db["is_serverless"]) is not bool or type(db["free_tier_enabled"]) is not bool:
        raise ConfigError(f"{name}: is_serverless y free_tier_enabled deben ser booleanos.")
    if db["is_serverless"]:
        if db["free_tier_enabled"] or db["throughput"] is not None or db["max_throughput"] is not None:
            raise ConfigError(f"{name}: Serverless no admite Free Tier ni throughput provisionado.")
    elif db["max_throughput"] is not None:
        if type(db["max_throughput"]) is not int or db["max_throughput"] < 1000 or db["max_throughput"] % 1000 or db["throughput"] is not None:
            raise ConfigError(f"{name}: autoscale requiere máximo múltiplo de 1000 y throughput=null.")
    elif type(db["throughput"]) is not int or db["throughput"] < 400 or db["throughput"] % 100:
        raise ConfigError(f"{name}: throughput manual mínimo 400 RU/s, múltiplo de 100.")
    interval, retention = db["backup_interval_minutes"], db["backup_retention_hours"]
    if type(interval) is not int or not 60 <= interval <= 1440 or type(retention) is not int or not interval / 30 <= retention <= 720 or db["backup_storage_redundancy"] not in ("Local", "Zone", "Geo"):
        raise ConfigError(f"{name}: backup periódico 60–1440 minutos, retención de al menos dos intervalos y hasta 720 horas.")
    storage = env["storage"]
    if storage["replication"] not in ("LRS", "ZRS", "GRS") or type(storage["content_cool_after_days"]) is not int or not 1 <= storage["content_cool_after_days"] <= 3650 or type(storage["soft_delete_days"]) is not int or not 1 <= storage["soft_delete_days"] <= 365:
        raise ConfigError(f"{name}.storage: replicación o retención inválida.")
    if env["web"]["sku"] not in ("Free", "Standard") or env["web"]["location"] not in ("westeurope", "eastus2", "centralus", "eastasia", "westus2"):
        raise ConfigError(f"{name}.web: SKU o región Static Web Apps no admitida.")
    fn = env["functions"]
    if fn["runtime_version"] != "24" or type(fn["maximum_instances"]) is not int or not 40 <= fn["maximum_instances"] <= 1000 or fn["memory_mb"] not in (512, 2048, 4096):
        raise ConfigError(f"{name}.functions: usa Node.js 24, 40–1000 instancias máximas y 512/2048/4096 MiB.")
    for group in ("requester_object_ids", "operator_object_ids"):
        values = env["access"][group]
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ConfigError(f"{name}.access.{group}: usa Object IDs de usuarios o grupos de Entra.")
        try:
            for value in values: uuid.UUID(value)
        except (ValueError, AttributeError) as exc:
            raise ConfigError(f"{name}.access.{group}: Object ID inválido.") from exc
    dns = env["public_dns"]
    if type(dns["create_zone"]) is not bool or not isinstance(dns["zone_name"], str) or (dns["zone_name"] and not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", dns["zone_name"])):
        raise ConfigError(f"{name}.public_dns: nombre de zona o create_zone inválido.")
    if not examples and dns["zone_name"] in ("example.com", "example.org", "example.net"):
        raise ConfigError(f"{name}: sustituye el dominio ficticio por una zona de tu propiedad o deja zone_name vacío.")
    if not isinstance(sample["version"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", sample["version"]):
        raise ConfigError(f"{name}.sample.version: etiqueta inválida.")
    for component in ("frontend", "api"):
        low, high = sample[f"{component}_min_replicas"], sample[f"{component}_max_replicas"]
        if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 10 or high < 1:
            raise ConfigError(f"{name}.{component}: réplicas mínimas/máximas inválidas.")
        port = sample[f"{component}_port"]
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ConfigError(f"{name}.{component}_port: usa 1024 a 65535.")
    if type(sample["cpu"]) not in (int, float) or (sample["cpu"], sample["memory"]) not in ((0.25,"0.5Gi"),(0.5,"1Gi"),(0.75,"1.5Gi"),(1,"2Gi")):
        raise ConfigError(f"{name}: combinación CPU/memoria Consumption inválida.")
    if type(sample["http_concurrency"]) is not int or not 1 <= sample["http_concurrency"] <= 1000:
        raise ConfigError(f"{name}.http_concurrency debe estar entre 1 y 1000.")


def normalize(raw, *, examples=False):
    template = json.loads((ROOT / "examples/shared.json").read_text())
    if not isinstance(raw, dict):
        raise ConfigError("La configuración debe ser un objeto JSON.")
    if raw.get("environment", "shared") != "shared":
        raise ConfigError("Nexus requiere environment=shared con environments.dev/prod y Cosmos MongoDB. Para configuraciones de versiones anteriores, prepara un despliegue nuevo o una migración revisada.")
    cfg = merge_section(copy.deepcopy(raw), template, "config")
    for field, pattern in (("name", r"[a-z][a-z0-9]{2,11}"), ("location", r"[a-z]+")):
        if not isinstance(cfg[field], str) or not re.fullmatch(pattern, cfg[field]):
            raise ConfigError(f"{field}: formato inválido.")
    for field in ("subscription_id", "tenant_id", "operator_object_id"):
        try:
            value = uuid.UUID(cfg[field])
        except (ValueError, TypeError, AttributeError) as exc:
            raise ConfigError(f"{field}: se requiere un UUID real.") from exc
        if not value.int and not examples:
            raise ConfigError(f"Sustituye el valor de ejemplo de {field}.")
        cfg[field] = str(value)
    entry = cfg["public_entrypoint"] = merge_section(cfg["public_entrypoint"], template["public_entrypoint"], "public_entrypoint")
    if type(entry["enabled"]) is not bool:
        raise ConfigError("public_entrypoint.enabled debe ser booleano.")
    for field in ("minimum_instances", "maximum_instances"):
        if type(entry[field]) is not int or not 1 <= entry[field] <= 10:
            raise ConfigError("public_entrypoint: capacidad entre 1 y 10 instancias.")
    if entry["minimum_instances"] > entry["maximum_instances"]:
        raise ConfigError("public_entrypoint: mínimo superior al máximo.")
    if not isinstance(entry["environment_hostnames"], dict) or set(entry["environment_hostnames"]) - set(ENVIRONMENTS):
        raise ConfigError("environment_hostnames solo admite dev y prod.")
    for hostname in (entry["hostname"], *entry["environment_hostnames"].values()):
        if not isinstance(hostname,str) or len(hostname)>253 or (hostname and not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",hostname)):
            raise ConfigError("public_entrypoint: usa un hostname DNS, sin esquema, ruta ni comodín.")
    if entry["acme_directory_url"] not in ("https://acme-v02.api.letsencrypt.org/directory", "https://acme-staging-v02.api.letsencrypt.org/directory"):
        raise ConfigError("public_entrypoint: directorio ACME no admitido.")
    if not isinstance(entry["certificate_secret_id"],str) or (entry["certificate_secret_id"] and not re.fullmatch(r"https://[a-z0-9-]+\.vault\.azure\.net/secrets/[a-zA-Z0-9-]+/?",entry["certificate_secret_id"])):
        raise ConfigError("certificate_secret_id: referencia Key Vault sin versión; nunca un valor secreto.")
    if cfg["state_access"] not in ("restricted-public", "private"):
        raise ConfigError("state_access: usa restricted-public o private.")
    if cfg["state_replication"] not in ("LRS", "GRS", "ZRS"):
        raise ConfigError("state_replication: usa LRS, GRS o ZRS.")
    ips = cfg["operator_ip_ranges"]
    if not isinstance(ips, list) or not ips:
        raise ConfigError("operator_ip_ranges requiere al menos una IPv4 pública.")
    normalized_ips = []
    for value in ips:
        try:
            net = ipaddress.ip_network(value, strict=True)
        except (ValueError, TypeError) as exc:
            raise ConfigError(f"IP inválida: {value}") from exc
        if net.version != 4 or net.prefixlen < 24 or net.prefixlen == 31 or (not examples and (not net.network_address.is_global or not net.broadcast_address.is_global)):
            raise ConfigError("Usa IPs públicas IPv4 específicas: /24 a /30, o una sola IP /32.")
        normalized_ips.append(str(net.network_address) if net.prefixlen == 32 else str(net))
    cfg["operator_ip_ranges"] = sorted(set(normalized_ips))
    if type(cfg["log_retention_days"]) is not int or cfg["log_retention_days"] not in (30,31,60,90,120,180,270,365,550,730):
        raise ConfigError("Retención Log Analytics no admitida.")
    if not isinstance(cfg["tags"], dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in cfg["tags"].items()):
        raise ConfigError("tags debe ser un mapa de cadenas.")
    fqdns(cfg["management_https_fqdns"], "management_https_fqdns")
    operations = cfg["operations"] = merge_section(cfg["operations"], template["operations"], "operations")
    if type(operations["budget_amount"]) not in (int,float) or not 1 <= operations["budget_amount"] <= 100000:
        raise ConfigError("operations.budget_amount debe estar entre 1 y 100000.")
    try:
        if date.fromisoformat(operations["budget_start_date"]).day != 1:
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise ConfigError("operations.budget_start_date: primer día del mes YYYY-MM-01.") from exc
    emails = operations["alert_emails"]
    if not isinstance(emails, list) or not 1 <= len(emails) <= 5 or any(not isinstance(v,str) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",v) for v in emails):
        raise ConfigError("operations.alert_emails requiere entre 1 y 5 destinatarios.")
    if not examples and any(v.rsplit('@',1)[-1].lower() in ("example.com","example.org","example.net") for v in emails):
        raise ConfigError("Sustituye los destinatarios de ejemplo por correos reales.")
    if not isinstance(cfg["environments"], dict) or set(cfg["environments"]) != set(ENVIRONMENTS):
        raise ConfigError("environments debe contener exactamente dev y prod.")
    for name in ENVIRONMENTS:
        env = merge_section(cfg["environments"][name], template["environments"][name], name)
        for section in ("cosmosdb_config", "storage", "web", "functions", "public_dns", "access", "sample"):
            env[section] = merge_section(env[section], template["environments"][name][section], f"{name}.{section}")
        validate_environment(env, name, examples=examples)
        if entry["enabled"] and env["public_dns"]["zone_name"]:
            raise ConfigError(f"{name}: en modo WAF usa public_entrypoint.hostname o environment_hostnames y apunta su DNS al WAF; public_dns es para el modo privado.")
        if entry["enabled"] and env["web_portals"] and env["web"]["sku"] != "Standard":
            raise ConfigError(f"{name}: el WAF exige SWA Standard para restringir el origen a su IP.")
        env["suffix"] = hashlib.sha256(f"{cfg['subscription_id']}/{cfg['name']}/{name}".encode()).hexdigest()[:12]
        cfg["environments"][name] = env
    # OIDC environments must not accidentally give the same GitHub subject both roles.
    dev, prod = (cfg["environments"][name] for name in ENVIRONMENTS)
    if dev["github_repository"] and (dev["github_repository"], dev["github_environment"]) == (prod["github_repository"], prod["github_environment"]):
        raise ConfigError("Dev y Prod requieren sujetos OIDC distintos (GitHub Environment).")
    if sum(env["enable_cosmosdb"] and env["cosmosdb_config"]["free_tier_enabled"] for env in cfg["environments"].values()) > 1:
        raise ConfigError("Solo se puede solicitar Free Tier para una cuenta Cosmos por suscripción.")
    validate_network(cfg, template)
    cfg["suffix"] = hashlib.sha256(f"{cfg['subscription_id']}/{cfg['name']}/shared".encode()).hexdigest()[:12]
    return cfg


def validate_network(cfg, template):
    blocks = [ipaddress.ip_network(c) for c in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    groups = {"hub": cfg["network"], **{name: cfg["environments"][name]["network"] for name in ENVIRONMENTS}}
    networks = {}
    for name, values in groups.items():
        expected = template["network"] if name == "hub" else template["environments"][name]["network"]
        if not isinstance(values, dict) or set(values) != set(expected):
            raise ConfigError(f"{name}.network: campos CIDR incorrectos.")
        parsed = {}
        for key, value in values.items():
            try:
                net = ipaddress.ip_network(value, strict=True)
            except (ValueError, TypeError) as exc:
                raise ConfigError(f"CIDR inválido: {name}.{key}") from exc
            if net.version != 4 or not any(net.subnet_of(block) for block in blocks):
                raise ConfigError(f"{name}.{key}: se requiere IPv4 RFC1918.")
            parsed[key] = net
        parent = parsed["hub_cidr" if name == "hub" else "vnet_cidr"]
        children = [v for k,v in parsed.items() if k not in ("hub_cidr", "vnet_cidr")]
        if any(not child.subnet_of(parent) or child == parent for child in children):
            raise ConfigError(f"Subredes de {name} deben estar dentro de su VNet.")
        if any(a.overlaps(b) for i,a in enumerate(children) for b in children[i+1:]):
            raise ConfigError(f"Las subredes de {name} no pueden solaparse.")
        for key, net in parsed.items():
            maximum = 26 if key == "firewall_subnet_cidr" else 23 if key == "apps_subnet_cidr" else 27
            if key.endswith("subnet_cidr") and net.prefixlen > maximum:
                raise ConfigError(f"{name}.{key}: reserva al menos /{maximum}.")
        networks[name] = parent
    parents = list(networks.values())
    if any(a.overlaps(b) for i,a in enumerate(parents) for b in parents[i+1:]):
        raise ConfigError("Las VNets Hub, Dev y Prod no pueden solaparse.")
    if any(net.overlaps(ipaddress.ip_network(c)) for net in parents for c in ("172.30.0.0/16", "172.31.0.0/16")):
        raise ConfigError("VNets solapadas con rangos reservados por Container Apps.")


def backend_config(cfg, stage):
    if stage not in (*STAGES, "edge"):
        raise ConfigError("Capa desconocida.")
    return {
        "resource_group_name": f"{cfg['name']}-shared-state-rg",
        "storage_account_name": f"stlz{cfg['suffix']}",
        "container_name": "tfstate", "key": f"shared/{stage}.tfstate",
        "use_azuread_auth": True, "tenant_id": cfg["tenant_id"], "subscription_id": cfg["subscription_id"],
    }
