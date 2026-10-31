"""Private example publication, Key Vault bootstrap and verifiable state backups."""
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import stat
import sys
import tempfile
import uuid
import time
import zipfile
from urllib.parse import urlsplit, urlunsplit, parse_qs, quote
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .config import ConfigError, ROOT, STAGES


def example_requirements(cfg, execute, *, build=True):
    webs = bool(cfg["web_portals"])
    required = (["docker"] if build and any(cfg[k] for k in ("enable_api_platform", "enable_api_tenant", "enable_api_activities")) else []) + (["node", "npm"] if webs or cfg["enable_event_processing"] else []) + (["swa"] if webs else [])
    for binary in required:
        if not shutil.which(binary):
            raise ConfigError(f"Falta {binary} para la aplicación de referencia. Instálalo en el ejecutor privado antes de deploy; puedes preparar solo foundation/platform con --stage.")
    if "docker" in required:
        execute(["docker", "buildx", "version"], capture=True)
        if execute(["docker", "info", "--format", "{{.OSType}}"], capture=True).stdout.strip() != "linux":
            raise ConfigError("La muestra requiere un motor Docker de contenedores Linux.")


def private_address(host, cidr, port):
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, port, family=socket.AF_INET)}
    except socket.gaierror as exc:
        raise ConfigError(f"{host} no resuelve. Revisa el DNS y la conexión del ejecutor con la red privada.") from exc
    network = ipaddress.ip_network(cidr)
    if not addresses or any(ipaddress.ip_address(address) not in network for address in addresses):
        raise ConfigError(f"{host} no resuelve dentro de {cidr}. Usa un ejecutor conectado a la red privada y su DNS.")
    try:
        with socket.create_connection((host, port), timeout=10):
            pass
    except OSError as exc:
        raise ConfigError(f"No se puede alcanzar {host}:{port}. Revisa rutas, NSG y firewall desde el ejecutor privado.") from exc
    return sorted(addresses)


def isolated_docker_config(directory):
    """Keep the selected engine/plugins/builders while isolating registry login."""
    source = Path(os.environ.get("DOCKER_CONFIG", str(Path.home() / ".docker"))).expanduser().resolve()
    destination = Path(directory)
    try:
        settings = json.loads((source / "config.json").read_text()) if (source / "config.json").exists() else {}
        if not isinstance(settings, dict):
            raise ValueError("Expected Docker configuration object")
    except (OSError, ValueError) as exc:
        raise ConfigError("No se pudo leer la configuración Docker del ejecutor.") from exc
    selected = {key: settings[key] for key in ("currentContext", "cliPluginsExtraDirs") if key in settings}
    # Do not copy auths, credsStore or credHelpers: az acr login writes only here.
    (destination / "config.json").write_text(json.dumps(selected))
    (destination / "config.json").chmod(0o600)
    for name in ("contexts", "cli-plugins"):
        if (source / name).is_dir():
            (destination / name).symlink_to(source / name, target_is_directory=True)
    return {"DOCKER_CONFIG": str(destination), "BUILDX_CONFIG": os.environ.get("BUILDX_CONFIG", str(source / "buildx"))}


def publish_example(deployment, execute):
    if not shutil.which("docker"):
        raise ConfigError("La muestra necesita Docker con buildx en el ejecutor privado para construir imágenes linux/amd64.")
    platform = deployment.output("platform")
    registry = platform["registry_login_server"]
    private_address(registry, deployment.cfg["network"]["endpoints_subnet_cidr"], 443)
    images = {}
    release = uuid.uuid4().hex[:12]
    with tempfile.TemporaryDirectory(prefix="docker-auth-", dir=deployment.path) as directory:
        env = isolated_docker_config(directory)
        execute(["az", "acr", "login", "--name", registry.split(".")[0], "--subscription", deployment.cfg["subscription_id"]], env_updates=env)
        for component in ("api", "frontend"):
            image = f"{registry}/example/{component}:{deployment.cfg['sample']['version']}-{release}"
            metadata = Path(directory) / f"{component}.json"
            execute(["docker", "buildx", "build", "--platform", "linux/amd64", "--push", "--metadata-file", str(metadata), "--tag", image, str(ROOT / "apps" / component)], env_updates=env)
            try:
                digest = json.loads(metadata.read_text())["containerimage.digest"]
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
                raise ConfigError("La publicación no devolvió el digest. No se actualizará el manifiesto de imágenes.") from exc
            if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise ConfigError("Digest de imagen inválido; no se desplegará una etiqueta mutable.")
            images[component] = f"{registry}/example/{component}@{digest}"
    # Solo promover el manifiesto cuando ambas imágenes están publicadas.
    manifest = {"version": deployment.cfg["sample"]["version"], "registry": registry, "images": images}
    path = deployment.path / "images.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)
    return images


def published_images(deployment, platform):
    """Resolve only the complete publication manifest; never guess a tag's content."""
    try:
        manifest = json.loads((deployment.path / "images.json").read_text())
        registry = platform["registry_login_server"]
        if manifest["version"] != deployment.cfg["sample"]["version"] or manifest["registry"] != registry:
            raise ValueError("La versión o el registro han cambiado.")
        images = manifest["images"]
        if set(images) != {"api", "frontend"} or any(
            not isinstance(images[key], str) or not re.fullmatch(re.escape(f"{registry}/example/{key}@") + r"sha256:[0-9a-f]{64}", images[key])
            for key in ("api", "frontend")
        ):
            raise ValueError("Imágenes incompletas o sin digest.")
        return images
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ConfigError("Falta un manifiesto válido de imágenes. Ejecuta publish-example desde el ejecutor privado antes de planificar workload, o usa deploy para publicar y desplegar.") from exc


def secret_value(execute, vault, name):
    result = execute(["az", "keyvault", "secret", "show", "--vault-name", vault, "--name", name, "--query", "value", "-o", "tsv"], capture=True, allow_failure=True, redact_errors=True)
    if result.returncode:
        if "SecretNotFound" in result.stderr:
            return None
        raise ConfigError("No se pudo consultar Key Vault. Revisa DNS privado y el rol Secrets Officer; no se ha sobrescrito ningún secreto.")
    return result.stdout.strip()


def store_secret(execute, vault, name, value):
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("Azure no devolvió un valor válido; se conserva la versión anterior del secreto.")
    if secret_value(execute, vault, name) == value:
        return False
    # Value never appears in argv, a file, Terraform inputs or logs.
    execute(["az", "keyvault", "secret", "set", "--vault-name", vault, "--name", name, "--file", "/dev/stdin", "--encoding", "utf-8", "--output", "none"], input_text=value, capture=True, redact_errors=True)
    return True


def sync_secrets(deployment, execute):
    platform = deployment.output("platform")
    if not platform.get("vault"):
        return
    vault = platform["vault"]["name"]
    private_address(urlsplit(platform["vault"]["uri"]).hostname, deployment.cfg["network"]["data_subnet_cidr"], 443)
    if platform.get("cosmos"):
        cosmos = platform["cosmos"]
        private_address(cosmos["host"], deployment.cfg["network"]["data_subnet_cidr"], 10255)
        result = execute(["az", "cosmosdb", "keys", "list", "--name", cosmos["account_name"], "--resource-group", platform["workload_resource_group"], "--subscription", deployment.cfg["subscription_id"], "--type", "connection-strings", "--output", "json"], capture=True, redact_errors=True)
        try:
            candidates = json.loads(result.stdout)["connectionStrings"]
            value = next(item["connectionString"] for item in candidates if urlsplit(item["connectionString"]).hostname == cosmos["host"])
            parsed = urlsplit(value)
            options = {k.lower(): v[0].lower() for k, v in parse_qs(parsed.query).items()}
            if parsed.scheme != "mongodb" or parsed.port != 10255 or not parsed.username or not parsed.password or options.get("ssl", options.get("tls")) != "true":
                raise ValueError()
        except (ValueError, KeyError, TypeError, StopIteration) as exc:
            raise ConfigError("Azure no devolvió una conexión MongoDB TLS para la cuenta prevista.") from None
        primary = execute(["az", "cosmosdb", "keys", "list", "--name", cosmos["account_name"], "--resource-group", platform["workload_resource_group"], "--subscription", deployment.cfg["subscription_id"], "--type", "keys", "--query", "primaryMasterKey", "-o", "tsv"], capture=True, redact_errors=True).stdout.strip()
        if not primary:
            raise ConfigError("Azure no devolvió la clave de escritura; se conserva el secreto anterior.")
        value = urlunsplit((parsed.scheme, f"{parsed.username}:{quote(primary, safe='')}@{parsed.hostname}:{parsed.port}", parsed.path, parsed.query, parsed.fragment))
        store_secret(execute, vault, cosmos["secret_name"], value)
        readonly = execute(["az", "cosmosdb", "keys", "list", "--name", cosmos["account_name"], "--resource-group", platform["workload_resource_group"], "--subscription", deployment.cfg["subscription_id"], "--type", "read-only-keys", "--query", "primaryReadonlyMasterKey", "-o", "tsv"], capture=True, redact_errors=True).stdout.strip()
        if not readonly:
            raise ConfigError("Azure no devolvió la clave de solo lectura; se conserva el secreto anterior.")
        readonly_uri = urlunsplit((parsed.scheme, f"{parsed.username}:{quote(readonly, safe='')}@{parsed.hostname}:{parsed.port}", parsed.path, parsed.query, parsed.fragment))
        store_secret(execute, vault, cosmos["readonly_secret_name"], readonly_uri)
    for role, web in platform.get("webs", {}).items():
        value = execute(["az", "staticwebapp", "secrets", "list", "--name", web["name"], "--resource-group", platform["workload_resource_group"], "--subscription", deployment.cfg["subscription_id"], "--query", "properties.apiKey", "-o", "tsv"], capture=True, redact_errors=True).stdout.strip()
        store_secret(execute, vault, f"deploy-web-{role}", value)
    print(f"Key Vault sincronizado en {deployment.cfg['environment']}: conexiones y tokens registrados sin mostrar valores.")


def wait_for_applications(deployment, execute, *, timeout=600):
    """ARM success can precede readiness of the newly deployed revision."""
    pending = dict(deployment.output("workload").get("applications", {}))
    deadline = time.monotonic() + timeout
    while pending:
        for name, app in list(pending.items()):
            result = execute(["az", "containerapp", "show", "--ids", app["id"], "--query", "{latest:properties.latestRevisionName,ready:properties.latestReadyRevisionName}", "-o", "json"], capture=True, redact_errors=True)
            try:
                status = json.loads(result.stdout)
            except (TypeError, ValueError) as exc:
                raise ConfigError("Azure no devolvió el estado de la revisión; no se dará el despliegue por completado.") from exc
            if isinstance(status, dict) and status.get("latest") and status.get("latest") == status.get("ready"):
                del pending[name]
        if not pending:
            break
        if time.monotonic() >= deadline:
            raise ConfigError("Las nuevas revisiones no están listas: " + ", ".join(sorted(pending)) + ". Revisa las réplicas y sus eventos; los recursos se conservan.")
        print("Esperando nuevas revisiones de Container Apps: " + ", ".join(sorted(pending)), flush=True)
        time.sleep(5)


def publish_application_code(deployment, execute):
    platform, workload = deployment.output("platform"), deployment.output("workload")
    if deployment.cfg["enable_event_processing"]:
        if sys.platform != "linux":
            raise ConfigError("Publica Functions desde un ejecutor Linux privado con Node.js y npm para preparar sus dependencias.")
        function = workload["functions"]
        private_address(function["hostname"], deployment.cfg["network"]["data_subnet_cidr"], 443)
        with tempfile.TemporaryDirectory(prefix="functions-", dir=deployment.path) as folder:
            archive = Path(folder) / "functions.zip"
            contents = Path(folder) / "contents"
            contents.mkdir()
            for name in ("function_app.mjs", "handlers.mjs", "host.json", "package.json", "package-lock.json", "LICENSE", "NOTICE"):
                shutil.copy2(ROOT / "apps/functions" / name, contents / name)
            shutil.copy2(ROOT / "apps/api/domain.mjs", contents / "domain.mjs")
            execute(["npm", "--prefix", str(contents), "ci", "--omit=dev"], capture=True)
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
                for path in sorted(contents.rglob("*")):
                    entry = zipfile.ZipInfo.from_file(path, path.relative_to(contents))
                    if path.is_dir():
                        entry.external_attr = ((stat.S_IFDIR | 0o755) << 16) | 0x10
                        package.writestr(entry, b"")
                    elif path.is_file():
                        mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                        entry.external_attr = (stat.S_IFREG | mode) << 16
                        entry.compress_type = zipfile.ZIP_DEFLATED
                        package.writestr(entry, path.read_bytes())
            execute(["az", "functionapp", "deployment", "source", "config-zip", "--name", function["name"], "--resource-group", function["resource_group"], "--subscription", deployment.cfg["subscription_id"], "--src", str(archive), "--build-remote", "false", "-o", "none"], capture=True, redact_errors=True)
    publish_web_portals(deployment, execute)
    print("Código publicado: portales y procesador de eventos habilitados.")


def publish_web_portals(deployment, execute):
    """Publish configured portal views without changing application feature flags."""
    platform, workload = deployment.output("platform"), deployment.output("workload")
    if not platform.get("webs"):
        return
    execute(["npm", "--prefix", str(ROOT / "apps/portal"), "ci"], capture=True)
    public = bool(platform.get("public_origin"))
    if not public:
        execute(["npm", "--prefix", str(ROOT / "apps/portal"), "run", "build"], capture=True, env_updates={"NEXT_TELEMETRY_DISABLED": "1", "NEXT_PUBLIC_BASE_PATH": ""})
    for role, web in platform.get("webs", {}).items():
        prefix = f"/{deployment.cfg['environment']}/{role}" if public else ""
        if public:
            execute(["npm", "--prefix", str(ROOT / "apps/portal"), "run", "build"], capture=True, env_updates={"NEXT_TELEMETRY_DISABLED": "1", "NEXT_PUBLIC_BASE_PATH": prefix})
        token = secret_value(execute, platform["vault"]["name"], f"deploy-web-{role}")
        if not token:
            raise ConfigError("Falta el token web en Key Vault; ejecuta secrets-sync.")
        with tempfile.TemporaryDirectory(prefix="portal-", dir=deployment.path) as folder:
            target = Path(folder) / prefix.lstrip("/") if public else Path(folder)
            shutil.copytree(ROOT / "apps/portal/out", target, dirs_exist_ok=True)
            gateway = f"{platform['public_origin']}/{deployment.cfg['environment']}" if public else workload.get("demo_url")
            (target / "config.json").write_text(json.dumps({"role": deployment.cfg["web_portals"][role]["view"], "base_path": prefix, "environment": deployment.cfg["environment"], "evaluation": deployment.cfg["deploy_demo"], "gateway": gateway, "auth": platform.get("auth"), "features": {k: v for k, v in deployment.cfg.items() if k.startswith("enable_")}}))
            if public:
                # SWA validates a root default document even when the WAF serves a base path.
                shutil.copy2(target / "index.html", Path(folder) / "index.html")
                (target / "staticwebapp.config.json").unlink(missing_ok=True)
                # Origin lockdown is enforced by SWA, independently of spoofable headers.
                from .edge import swa_configuration
                (Path(folder)/"staticwebapp.config.json").write_text(json.dumps(swa_configuration(platform["public_entrypoint_ip"], target, prefix, [urlsplit(platform["public_origin"]).hostname])))
            execute(["swa", "deploy", folder, "--env", "production", "--swa-config-location", folder, "--no-use-keychain"], env_updates={"SWA_CLI_DEPLOYMENT_TOKEN": token}, capture=True, redact_errors=True)


def backup_states(deployment):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = deployment.path / "backups" / stamp
    destination.mkdir(parents=True, mode=0o700)
    manifest = {"created_at": stamp, "deployment": f"{deployment.cfg['name']}-{deployment.cfg['environment']}", "states": {}}
    for stage in (*STAGES, *(("edge",) if deployment.cfg.get("public_entrypoint",{}).get("enabled") else ())):
        deployment.init(stage)
        data = deployment.tf(stage, "state", "pull", capture=True).stdout
        state = validate_state(json.loads(data))
        path = destination / f"{stage}.tfstate"
        path.write_text(data)
        path.chmod(0o600)
        manifest["states"][stage] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "lineage": state["lineage"], "serial": state["serial"]}
    path = destination / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    path.chmod(0o600)
    print(f"Backup local sensible creado: {destination}. Conserva otra copia cifrada fuera del ejecutor.")
    return destination


def validate_state(state):
    if not isinstance(state, dict) or type(state.get("serial")) is not int or state["serial"] < 0 or not isinstance(state.get("resources"), list):
        raise ConfigError("Estado Terraform inválido: serial o resources incorrectos.")
    try:
        uuid.UUID(state["lineage"])
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise ConfigError("Estado Terraform sin lineage UUID válido.") from exc
    return state


def verify_backup(directory):
    directory = Path(directory)
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
        if set(manifest["states"]) not in (set(STAGES),set((*STAGES,"edge"))):
            raise ConfigError("El backup debe contener las cuatro capas de base y, en modo WAF, edge.")
        for stage in manifest["states"]:
            data = (directory / f"{stage}.tfstate").read_bytes()
            expected = manifest["states"][stage]
            state = validate_state(json.loads(data))
            if hashlib.sha256(data).hexdigest() != expected["sha256"] or any(state[key] != expected[key] for key in ("lineage", "serial")):
                raise ConfigError(f"Backup alterado o incoherente: {stage}.")
    except (OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ConfigError("No se puede verificar el backup completo.") from exc
    print("Backup íntegro: "+("cuatro estados" if len(manifest["states"])==4 else "cinco estados")+" con hash, lineage y serial verificados. Esto no acredita una restauración real.")
    return manifest


def application_token(deployment):
    # Importación diferida: cli importa este módulo durante su inicialización.
    from .cli import execute
    auth = deployment.output("platform").get("auth")
    if not auth:
        raise ConfigError("Falta el contrato Entra de la aplicación.")
    result = execute(["az", "account", "get-access-token", "--tenant", auth["tenant_id"], "--scope", auth["scope"], "--query", "accessToken", "-o", "tsv"], capture=True, redact_errors=True)
    token = result.stdout.strip()
    if not token:
        raise ConfigError("No se obtuvo un token de usuario. Inicia sesión con una cuenta asignada a la aplicación.")
    return token


def application_get(url, token):
    """Allow scale-to-zero startup on reads, never retry failed authorization."""
    for attempt in range(6):
        try:
            with urlopen(Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "Goliat-Nexus-Acceptance/1.0"}), timeout=30) as response:
                try: result = json.load(response)
                except (ValueError, UnicodeError): raise ConfigError("La API no devolvió JSON válido.") from None
                if response.status != 200 or not isinstance(result, dict):
                    raise ConfigError("La API no devolvió el contrato JSON esperado.")
                return result
        except HTTPError as error:
            if error.code not in (502, 503, 504):
                raise
        except (URLError, TimeoutError):
            pass
        if attempt < 5:
            print("Esperando el arranque de la API; Dev puede escalar a cero…", flush=True)
            time.sleep(5)
    raise ConfigError("La API no está disponible tras la espera de arranque. Revisa las revisiones, sus eventos y el acceso a datos.")


def application_gateway(deployment):
    platform=deployment.output("platform")
    if platform.get("public_origin"):
        return platform["public_origin"]+"/"+deployment.cfg["environment"]
    return deployment.output("workload")["demo_url"]


def smoke_test(deployment):
    platform = deployment.output("platform")
    if platform.get("public_origin"):
        result=application_get(application_gateway(deployment)+"/api/tenant/requests",application_token(deployment))
        if not isinstance(result.get("items"),list):raise ConfigError("La API no acredita acceso a las solicitudes en Cosmos.")
        print("Smoke test correcto: lectura autenticada de solicitudes a través del WAF público.")
        return
    for host in (platform["registry_login_server"], f"stlz{deployment.cfg['state_suffix']}.blob.core.windows.net"):
        private_address(host, deployment.cfg["network"]["endpoints_subnet_cidr"], 443)
    if platform.get("vault"):
        private_address(urlsplit(platform["vault"]["uri"]).hostname, deployment.cfg["network"]["data_subnet_cidr"], 443)
    if platform.get("cosmos"):
        private_address(platform["cosmos"]["host"], deployment.cfg["network"]["data_subnet_cidr"], 10255)
    workload = deployment.output("workload")
    if workload.get("demo_url") and deployment.cfg["enable_api_tenant"]:
        url = workload["demo_url"]
        private_address(urlsplit(url).hostname, deployment.cfg["network"]["apps_subnet_cidr"], 443)
        result = application_get(url + "/api/tenant/requests", application_token(deployment))
        if not isinstance(result.get("items"), list):
            raise ConfigError("La API no acredita acceso a las solicitudes en Cosmos.")
    print("Smoke test correcto: resolución privada y lectura de solicitudes. Verifica una solicitud hasta su actividad, denegaciones y recuperación con el runbook.")


def verify_application(deployment):
    """A real Azure acceptance check; deliberately creates one labelled test request."""
    if not all(deployment.cfg[key] for key in ("enable_api_tenant", "enable_api_activities", "enable_event_processing")):
        raise ConfigError("La prueba requiere API tenant, API activities y procesamiento de eventos.")
    smoke_test(deployment)
    url = application_gateway(deployment)
    token = application_token(deployment)
    identifier = str(uuid.uuid4())
    body = json.dumps({"id": identifier, "title": "Prueba de aceptación de Alba", "category": "support"}).encode()
    def submit():
        with urlopen(Request(url + "/api/tenant/requests", data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "Goliat-Nexus-Acceptance/1.0"}), timeout=30) as response:
            result = json.load(response)
            if result.get("id") != identifier:
                raise ConfigError("La API no confirmó el identificador de la solicitud.")
    submit()
    submit()  # Same id and content: no second request.
    for attempt in range(36):
        activities = application_get(url + "/api/activities/events", token).get("items", [])
        matches = [item for item in activities if item.get("request_id") == identifier]
        if len(matches) == 1:
            print(f"Aceptación correcta en {deployment.cfg['environment']}: solicitud {identifier} persistida y actividad de Function confirmada. El registro de prueba se conserva.")
            return identifier
        if len(matches) > 1:
            raise ConfigError("La prueba encontró actividades duplicadas para una solicitud.")
        if attempt < 35:
            print("Esperando procesamiento de la Function…", flush=True)
            time.sleep(5)
    raise ConfigError(f"La solicitud {identifier} está creada pero no se confirmó su actividad tras la espera de aceptación. Revisa host, RBAC, outbox y poison antes de repetir.")
