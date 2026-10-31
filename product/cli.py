"""Shared platform, two workloads, self-hosted backend and offline validation."""
import argparse
import contextlib
import fcntl
import ipaddress
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from .config import ConfigError, ROOT, STAGES, ENVIRONMENTS, backend_config, normalize, read_config
from .operations import backup_states, example_requirements, sync_secrets, publish_application_code, publish_example, published_images, smoke_test, verify_application, verify_backup, wait_for_applications
from .tfvars import read_environment_directory, write_environment_directory
from .identity import ACTIVE, InstallationIdentity, TemporaryIdentity, authenticated_backend, command_environment, adopt_bootstrap_groups, recover_identity, recover_abandoned, run_terraform

AZURE_BACKEND = 'terraform {\n  backend "azurerm" {}\n}\n'
INPUTS_FILE = "inputs.auto.tfvars.json"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.chmod(0o600)
    temporary.replace(path)


def execute(args, *, capture=False, allow_failure=False, env_updates=None, input_text=None, redact_errors=False):
    env = os.environ.copy()
    env["TF_WORKSPACE"] = "default"
    env["ARM_USE_AZUREAD"] = "true"
    env.update(env_updates or {})
    env = command_environment(args, env)
    if ACTIVE.get() and Path(args[0]).name == "terraform":
        result = run_terraform(args, env=env, capture=capture, input_text=input_text)
    else:
        result = subprocess.run(args, text=True, capture_output=capture, env=env, input=input_text, check=False)
    if result.returncode and not allow_failure:
        if capture and not redact_errors:
            print(result.stderr, file=sys.stderr)
        raise ConfigError(f"Falló {args[0]} (código {result.returncode}); corrige el error y repite el comando.")
    return result


@contextlib.contextmanager
def local_lock(directory):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    with (directory / ".operation.lock").open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ConfigError("Ya hay una operación en curso para este entorno.") from exc
        yield


class Deployment:
    def __init__(self, cfg, *, validation=False):
        self.cfg = cfg
        self.validation = validation
        self.quiet = False
        label = f"{cfg['name']}-{cfg['environment']}"
        self.path = ROOT / ".lz" / ("validation" if validation else "deployments") / label

    def tf(self, stage, *args, capture=False, allow_failure=False):
        return execute(["terraform", f"-chdir={self.path / 'stacks' / stage}", *args], capture=capture or self.quiet, allow_failure=allow_failure)

    def prepare(self):
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        identity = {k: self.cfg[k] for k in ("name", "environment", "subscription_id", "tenant_id", "location", "suffix")}
        identity["architecture"] = "shared-modular-1.0"
        manifest = self.path / "identity.json"
        if not self.validation and manifest.exists() and json.loads(manifest.read_text()) != identity:
            raise ConfigError("La configuración cambia la identidad o región del despliegue existente. Usa un entorno nuevo o restaura la configuración anterior.")
        write_json(manifest, identity)
        # Solo se reemplaza código gestionado; nunca estados, planes ni backends.
        modules = self.path / "modules"
        if modules.exists():
            shutil.rmtree(modules)
        shutil.copytree(ROOT / "modules", modules)
        for stage in (*STAGES, "edge"):
            destination = self.path / "stacks" / stage
            destination.mkdir(parents=True, exist_ok=True, mode=0o700)
            source_stage = "workload" if stage in ENVIRONMENTS else stage
            sources = sorted((ROOT / "stacks" / source_stage).glob("*.tf"))
            previous_sources = destination / ".source-files.json"
            names = {source.name for source in sources} | {"common.tf"}
            if previous_sources.exists():
                for filename in set(json.loads(previous_sources.read_text())) - names:
                    (destination / filename).unlink(missing_ok=True)
            for source in sources:
                shutil.copy2(source, destination / source.name)
            shutil.copy2(ROOT / "terraform/common.tf", destination / "common.tf")
            write_json(previous_sources, sorted(names))
            lock = ROOT / "terraform/.terraform.lock.hcl"
            if lock.exists():
                shutil.copy2(lock, destination / ".terraform.lock.hcl")
            source_tests = ROOT / "stacks" / source_stage / "tests"
            if source_tests.exists():
                shutil.copytree(source_tests, destination / "tests", dirs_exist_ok=True)
            self.inputs(stage)
            backend = authenticated_backend(self.cfg, stage)
            (destination / "backend.hcl").write_text("".join(f"{key} = {json.dumps(value)}\n" for key, value in backend.items()))
        return self

    def environment_view(self, environment):
        settings = self.cfg["environments"][environment]
        cfg = {**self.cfg, **settings, "environment": environment, "state_suffix": self.cfg["suffix"],
               "network": {**self.cfg["network"], **settings["network"]}}
        path = self.path / "applications" / environment
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return SimpleNamespace(cfg=cfg, path=path, output=lambda stage: self.output("platform")["environments"][environment] if stage == "platform" else self.output(environment))

    def inputs(self, stage, integration=None):
        path = self.path / "stacks" / stage / INPUTS_FILE
        values = {"config": self.cfg}
        if stage in ENVIRONMENTS:
            values["environment"] = stage
        if stage == "edge":
            if integration is not None:
                values.update(integration)
            write_json(path, values)
            return
        if integration is not None:
            values["foundation" if stage == "platform" else "platform"] = integration
            if stage in ENVIRONMENTS and (self.validation or any(self.cfg["environments"][stage][key] for key in ("enable_api_platform", "enable_api_tenant", "enable_api_activities"))):
                values["sample_images"] = (
                    {key: f"{integration['registry_login_server']}/example/{key}@sha256:{'a' * 64}" for key in ("api", "frontend")}
                    if self.validation else published_images(self.environment_view(stage), integration)
                )
        write_json(path, values)
        # Replace only the old CLI-managed input file; preserve state/backend.
        path.with_name("inputs.tfvars.json").unlink(missing_ok=True)

    def preflight(self):
        for binary in ("terraform", "az"):
            if not shutil.which(binary):
                raise ConfigError(f"Falta {binary}; instala los requisitos del README.")
        version = json.loads(execute(["terraform", "version", "-json"], capture=True).stdout)["terraform_version"]
        parts = tuple(int(v) for v in version.split("-")[0].split(".")[:2])
        if not (1, 9) <= parts < (2, 0):
            raise ConfigError("Se requiere Terraform >= 1.9 y < 2.0.")
        account = json.loads(execute(["az", "account", "show", "--subscription", self.cfg["subscription_id"], "--output", "json"], capture=True).stdout)
        if account["tenantId"].lower() != self.cfg["tenant_id"] or account["id"].lower() != self.cfg["subscription_id"]:
            raise ConfigError("La sesión Azure no corresponde al tenant y suscripción configurados.")
        if self.cfg["state_access"] == "private":
            hostname = f"stlz{self.cfg['suffix']}.blob.core.windows.net"
            try:
                addresses = {item[4][0] for item in socket.getaddrinfo(hostname, 443, family=socket.AF_INET)}
            except socket.gaierror as exc:
                raise ConfigError("Despliega primero con state_access=restricted-public; después ejecuta desde la red privada.") from exc
            endpoint_net = ipaddress.ip_network(self.cfg["network"]["endpoints_subnet_cidr"])
            if not addresses or any(ipaddress.ip_address(ip) not in endpoint_net for ip in addresses):
                raise ConfigError("El backend no resuelve a su subred privada. No se cerrará el acceso público desde esta máquina.")
            with socket.create_connection((hostname, 443), timeout=10):
                pass
            # Se comprueba el acceso de datos antes de aplicar el cierre.
            self.wait_for_state_access(attempts=1)

    def remote_blob_exists(self, *, allow_missing_state=False):
        account_name = f"stlz{self.cfg['suffix']}"
        account = execute(["az", "storage", "account", "show", "--name", account_name,
                           "--resource-group", f"{self.cfg['name']}-{self.cfg['environment']}-state-rg",
                           "--subscription", self.cfg["subscription_id"], "-o", "json"], capture=True, allow_failure=True)
        if account.returncode:
            if "ResourceNotFound" in account.stderr or "ResourceGroupNotFound" in account.stderr:
                return False
            raise ConfigError(f"No se pudo comprobar el backend existente: {account.stderr.strip()}")
        result = execute(["az", "storage", "blob", "exists", "--account-name", account_name,
                          "--container-name", "tfstate", "--name", f"{self.cfg['environment']}/foundation.tfstate",
                          "--auth-mode", "login", "-o", "json"], capture=True)
        if not json.loads(result.stdout)["exists"]:
            if allow_missing_state:
                return False
            raise ConfigError("La cuenta ya existe pero no contiene foundation.tfstate. Restaura el estado local del bootstrap; no se importarán recursos automáticamente.")
        return True

    def init(self, stage):
        directory = self.path / "stacks" / stage
        if stage == "foundation":
            backend = directory / "backend.auto.tf"
            local_state = directory / "terraform.tfstate"
            if backend.exists() and backend.read_text().strip() == 'terraform { backend "azurerm" {} }':
                backend.write_text(AZURE_BACKEND)
            if not backend.exists() and not local_state.exists() and self.remote_blob_exists():
                backend.write_text(AZURE_BACKEND)
            if not backend.exists():
                self.tf(stage, "init", "-input=false")
                return
            metadata = directory / ".terraform/terraform.tfstate"
            previous = json.loads(metadata.read_text()).get("backend", {}).get("type") if metadata.exists() else None
            has_local_resources = False
            if previous != "azurerm" and local_state.exists():
                # Terraform can leave an empty local file after migrating it.
                content = local_state.read_text().strip()
                if content:
                    try:
                        has_local_resources = bool(json.loads(content).get("resources"))
                    except (ValueError, AttributeError) as exc:
                        raise ConfigError("El estado local no es JSON válido. Se conserva sin modificar; revisa el bootstrap antes de cambiar el backend.") from exc
            if previous != "azurerm" and has_local_resources:
                self.wait_for_state_access()
                self.copy_bootstrap_state()
                return
        self.tf(stage, "init", "-reconfigure", "-input=false", "-backend-config=backend.hcl")

    def wait_for_state_access(self, attempts=12):
        command = ["az", "storage", "blob", "list", "--account-name", f"stlz{self.cfg['suffix']}",
                   "--container-name", "tfstate", "--auth-mode", "login", "--num-results", "1", "-o", "none"]
        for attempt in range(attempts):
            result = execute(command, capture=True, allow_failure=True)
            if result.returncode == 0:
                return
            if attempt + 1 < attempts:
                print("Esperando propagación de RBAC y acceso al backend…", flush=True)
                time.sleep(5)
        raise ConfigError("No se puede acceder al backend. Comprueba operator_object_id, IP de salida, DNS y RBAC. El estado local se conserva; repite deploy tras corregirlo.\n" + result.stderr.strip())

    def migrate_foundation(self):
        directory = self.path / "stacks/foundation"
        if not (directory / "backend.auto.tf").exists():
            self.wait_for_state_access()
            self.assert_remote_state_absent()
            (directory / "backend.auto.tf").write_text(AZURE_BACKEND)
            self.copy_bootstrap_state()

    def assert_remote_state_absent(self):
        if self.remote_blob_exists(allow_missing_state=True):
            raise ConfigError("Ya existe foundation.tfstate en Azure. Se cancela la migración para no sobrescribir un estado remoto con una copia local. Conserva ambas copias y revisa lineage y serial antes de recuperar el backend.")

    def copy_bootstrap_state(self):
        self.assert_remote_state_absent()
        # Solo se autoriza la copia automática al destino que se ha comprobado
        # vacío. Un blob existente requiere una recuperación revisada.
        self.tf("foundation", "init", "-migrate-state", "-force-copy", "-input=false", "-backend-config=backend.hcl")

    def output(self, stage):
        result = self.tf(stage, "output", "-json", "integration", capture=True)
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Falta el contrato de {stage}; despliega primero esa capa.") from exc
        if not isinstance(value, dict):
            raise ConfigError(f"El estado de {stage} no tiene un contrato válido.")
        return value

    def upstream(self, stage):
        if stage == "foundation":
            return None
        previous = "foundation" if stage == "platform" else "platform"
        self.init(previous)
        contract = self.output(previous)
        return contract if stage == "platform" else contract["environments"][stage]

    def guard_legacy_platform(self):
        result = self.tf("platform", "state", "list", capture=True, allow_failure=True)
        if result.returncode:
            if not any(marker in (result.stderr or "") for marker in ("No state file", "No stored state", "No state")):
                raise ConfigError("No se pudo comprobar el estado de platform antes del plan. Revisa el backend y sus permisos.")
            return
        if any("module.database" in address or "postgresql_flexible" in address for address in result.stdout.splitlines()):
            raise ConfigError("El estado contiene la base de datos de 0.3. Esta versión no la migra ni sustituye: crea una instalación con otro nombre y planifica la migración de datos por separado.")
        if any("module.cosmos" in address for address in result.stdout.splitlines()):
            state = self.tf("platform", "state", "pull", capture=True)
            try:
                resources = json.loads(state.stdout)["resources"]
                versions = [instance["attributes"].get("mongo_server_version") for resource in resources if resource.get("type") == "azurerm_cosmosdb_account" for instance in resource.get("instances", [])]
            except (KeyError, TypeError, ValueError) as exc:
                raise ConfigError("No se pudo verificar la compatibilidad de Cosmos antes del plan.") from exc
            if any(version != "7.0" for version in versions):
                raise ConfigError("La cuenta Cosmos existente no usa API MongoDB 7.0. Esta entrega no cambia el protocolo automáticamente: prepara la migración o crea otra instalación con nombre distinto.")


    def deploy(self, selected, *, yes=False, reuse_images=False):
        if selected == "edge" and not self.cfg["public_entrypoint"]["enabled"]:
            raise ConfigError("public_entrypoint.enabled está desactivado.")
        targets = STAGES if selected == "all" else () if selected == "edge" else (selected,)
        for stage in targets:
            if stage in ENVIRONMENTS:
                example_requirements(self.environment_view(stage).cfg, execute, build=not reuse_images)
        self.register_providers(selected)
        for stage in targets:
            if stage in ENVIRONMENTS and any(self.cfg["environments"][stage][key] for key in ("enable_api_platform", "enable_api_tenant", "enable_api_activities")):
                self.init("platform")
                view = self.environment_view(stage)
                if reuse_images:
                    published_images(view, view.output("platform"))
                else:
                    publish_example(view, execute)
            if stage in ENVIRONMENTS:
                self.init("platform")
                sync_secrets(self.environment_view(stage), execute)
            self.inputs(stage, self.upstream(stage))
            self.init(stage)
            if stage == "platform":
                self.guard_legacy_platform()
            adopt_bootstrap_groups(self, stage)
            print(f"\nDesplegando {stage} en {self.cfg['name']}…", flush=True)
            self.apply_saved_plan(stage, "deployment.tfplan", yes=yes)
            if stage == "foundation":
                self.migrate_foundation()
            if stage in ENVIRONMENTS:
                wait_for_applications(self.environment_view(stage), execute)
                publish_application_code(self.environment_view(stage), execute)
        if self.cfg["public_entrypoint"]["enabled"] and selected in ("all", "edge"):
            from .edge import deploy_public_entrypoint
            deploy_public_entrypoint(self, execute, yes=yes, reuse_images=reuse_images)
        print("\nDespliegue completado. Consulta ./lz output --config <config.json>.")

    def approve_plan(self, stage):
        if not sys.stdin.isatty():
            raise ConfigError("El plan está guardado. Usa --yes para aprobar la ejecución sin interacción.")
        if input(f"¿Aplicar el plan guardado de {stage}? Escribe aplicar: ").strip() != "aplicar":
            raise ConfigError("Plan no aprobado; no se aplicó esta capa.")

    def apply_saved_plan(self, stage, filename, *, yes=False, verify=None):
        plan_path = self.path / "stacks" / stage / filename
        plan_path.unlink(missing_ok=True)  # A failed plan must never reuse an older artifact.
        self.tf(stage, "plan", "-input=false", f"-var-file={INPUTS_FILE}", "-out=" + filename)
        if verify:
            verify(json.loads(self.tf(stage, "show", "-json", filename, capture=True).stdout))
        if not yes:
            self.approve_plan(stage)
        # A saved plan already contains its reviewed inputs; never pass -var-file or replan.
        self.tf(stage, "apply", "-input=false", filename)

    def register_providers(self, selected):
        namespaces = {"Microsoft.Storage"}
        if selected != "foundation":
            namespaces.update({"Microsoft.Network", "Microsoft.ManagedIdentity", "Microsoft.KeyVault",
                               "Microsoft.ContainerRegistry", "Microsoft.OperationalInsights",
                               "Microsoft.Insights", "Microsoft.App"})
            namespaces.update({"Microsoft.DocumentDB", "Microsoft.Consumption", "Microsoft.Web", "Microsoft.EventGrid"})
        for namespace in sorted(namespaces):
            command = ["az", "provider", "show", "--namespace", namespace,
                       "--subscription", self.cfg["subscription_id"], "--query", "registrationState", "-o", "tsv"]
            if execute(command, capture=True).stdout.strip() != "Registered":
                print(f"Registrando {namespace} en la suscripción…", flush=True)
                execute(["az", "provider", "register", "--namespace", namespace,
                         "--subscription", self.cfg["subscription_id"], "--wait", "-o", "none"])

    def plan(self, stage):
        if stage == "edge":
            if not self.cfg["public_entrypoint"]["enabled"]:
                raise ConfigError("public_entrypoint.enabled está desactivado.")
            from .edge import edge_contracts, edge_image
            self.inputs(stage, {**edge_contracts(self), "edge_image": edge_image(self)})
            self.init(stage)
            self.tf(stage, "plan", "-var-file=inputs.auto.tfvars.json", "-out=review.tfplan", "-input=false")
            return
        if stage == "foundation" and self.cfg["state_access"] == "private":
            self.wait_for_state_access(attempts=1)
        self.inputs(stage, self.upstream(stage))
        self.init(stage)
        if stage == "platform":
            self.guard_legacy_platform()
        self.tf(stage, "plan", f"-var-file={INPUTS_FILE}", "-out=review.tfplan", "-input=false")


def fixture_contracts(cfg):
    base = f"/subscriptions/{cfg['subscription_id']}/resourceGroups/{cfg['name']}"
    foundation = {
        "storage_account_name": f"stlz{cfg['suffix']}",
        "storage_account_id": f"{base}-shared-state-rg/providers/Microsoft.Storage/storageAccounts/stlz{cfg['suffix']}",
        "resource_group_name": f"{cfg['name']}-shared-state-rg", "container_name": "tfstate", "public_access": True,
    }
    shared = {"registry_login_server": f"acrlz{cfg['suffix']}.azurecr.io",
              "workspace_id": f"{base}-shared-rg/providers/Microsoft.OperationalInsights/workspaces/logs",
              "firewall_private_ip": str(ipaddress.ip_network(cfg["network"]["firewall_subnet_cidr"]).network_address + 4)}
    environments = {}
    for key, env in cfg["environments"].items():
        environments[key] = {**shared,
            "workload_resource_group": f"{cfg['name']}-{key}-rg",
            "connectivity_resource_group": f"{cfg['name']}-connectivity-rg",
            "apps_subnet_id": f"{base}-connectivity-rg/providers/Microsoft.Network/virtualNetworks/{key}/subnets/container-apps",
            "vnet_ids": {name: f"{base}-connectivity-rg/providers/Microsoft.Network/virtualNetworks/{name}" for name in ("hub", key)},
            "functions_subnet_id": f"{base}-connectivity-rg/providers/Microsoft.Network/virtualNetworks/{key}/subnets/functions-integration",
            "endpoint_subnet_id": f"{base}-connectivity-rg/providers/Microsoft.Network/virtualNetworks/{key}/subnets/data-private-endpoints",
            "functions_dns_zone_id": f"{base}-connectivity-rg/providers/Microsoft.Network/privateDnsZones/privatelink.azurewebsites.net",
            "identities": {role: {"id": f"{base}-{key}-rg/providers/Microsoft.ManagedIdentity/userAssignedIdentities/{role}", "client_id": "44444444-4444-4444-8444-444444444444", "principal_id": "55555555-5555-4555-8555-555555555555"} for role in ["frontend", "platform", "tenant", "activities", "functions"]},
            "action_group_id": f"{base}-shared-rg/providers/Microsoft.Insights/actionGroups/operations",
            "managed_resource_group": f"{cfg['name']}-{key}-aca-managed-rg",
            "cosmos": {"id": f"{base}-{key}-rg/providers/Microsoft.DocumentDB/databaseAccounts/cosmos-{env['suffix']}", "account_name": f"cosmos-{env['suffix']}", "host": f"cosmos-{env['suffix']}.mongo.cosmos.azure.com", "name": env["cosmosdb_config"]["database_name"], "secret_name": "cosmos-mongodb-connection", "readonly_secret_name": "cosmos-mongodb-readonly-connection", "port": 10255} if env["enable_cosmosdb"] else None,
            "vault": {"id": f"{base}-{key}-rg/providers/Microsoft.KeyVault/vaults/kv-lz-{env['suffix']}", "uri": f"https://kv-lz-{env['suffix']}.vault.azure.net/", "name": f"kv-lz-{env['suffix']}"} if env["enable_key_vault"] else None,
            "host_vault": {"id": f"{base}-{key}-rg/providers/Microsoft.KeyVault/vaults/kv-lz-{env['suffix']}h", "uri": f"https://kv-lz-{env['suffix']}h.vault.azure.net/"} if env["enable_event_processing"] else None,
            "storage": {"id": f"{base}-{key}-rg/providers/Microsoft.Storage/storageAccounts/stapp{env['suffix']}", "name": f"stapp{env['suffix']}", **{kind+"_uri": f"https://stapp{env['suffix']}.{kind}.core.windows.net/" for kind in ["blob", "queue", "table"]}} if env["enable_storage_account"] else None,
            "content": None,
            "webs": {portal_id: {"name": f"{cfg['name']}-{key}-{portal_id}", "hostname": f"{key}-{portal_id}.azurestaticapps.net", "view": portal["view"]} for portal_id, portal in env["web_portals"].items()},
            "auth": {"tenant_id":cfg["tenant_id"], "api_client_id":"66666666-6666-4666-8666-666666666666", "frontend_client_id":"77777777-7777-4777-8777-777777777777", "scope":"api://66666666-6666-4666-8666-666666666666/access_as_user", "allowed_client_ids":["77777777-7777-4777-8777-777777777777","04b07795-8ddb-461a-bbee-02f9e1bf7b46"]},
            "events_endpoint": "", "publisher_client_id": None,
        }
    return foundation, {**shared, "environments": environments}


def validate(cfg):
    deployment = Deployment(cfg, validation=True)
    with local_lock(deployment.path):
        deployment.prepare()
        foundation, platform = fixture_contracts(cfg)
        for stage, contract in zip(STAGES, (None, foundation, platform["environments"]["dev"], platform["environments"]["prod"])):
            deployment.inputs(stage, contract)
            deployment.tf(stage, "init", "-backend=false", "-input=false")
            deployment.tf(stage, "validate")
            # This verifies Terraform's automatic variable-file discovery too.
            deployment.tf(stage, "test", "-no-color")
        if cfg["public_entrypoint"]["enabled"]:
            from .edge import validation_contracts
            deployment.inputs("edge",validation_contracts(cfg,platform))
            deployment.tf("edge","init","-backend=false","-input=false")
            deployment.tf("edge","validate")
            deployment.tf("edge","test","-no-color")


def configure(args):
    output = Path(args.output) if args.output else Path(args.output_dir or (".local/demo" if args.demo else ".local/environments"))
    if args.output and output.suffix != ".json":
        raise ConfigError("El CLI genera JSON. Usa .auto.tfvars.json o .json como extensión de salida.")
    if output.exists():
        raise ConfigError(f"{output} ya existe; no se sobrescribirá.")
    account = json.loads(execute(["az", "account", "show", "-o", "json"], capture=True).stdout)
    operator = args.operator_object_id
    if not operator:
        operator = execute(["az", "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"], capture=True).stdout.strip()
    cfg = read_environment_directory(ROOT / ("examples/demo" if args.demo else "environments"))
    cfg.update(name=args.name, environment="shared", location=args.location,
               subscription_id=account["id"], tenant_id=account["tenantId"],
               operator_object_id=operator, operator_ip_ranges=[args.operator_ip])
    cfg["operations"]["alert_emails"] = args.alert_email
    cfg["operations"]["budget_start_date"] = date.today().replace(day=1).isoformat()
    normalize(cfg)
    if args.output:
        write_json(output, {"config": cfg} if output.name.endswith(".tfvars.json") else cfg)
    else:
        write_environment_directory(output, cfg)
    print(f"Configuración creada: {output}. Revísala y ejecuta ./lz deploy --config {output}")


def parser():
    cli = argparse.ArgumentParser(description=f"Goliat - Nexus {(ROOT / 'VERSION').read_text().strip()} — Hub compartido, Dev y Prod")
    sub = cli.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("configure", help="Crear configuración usando tu sesión az login")
    setup.add_argument("--name", required=True)
    setup.add_argument("--location", default="westeurope")
    setup.add_argument("--operator-ip", required=True)
    setup.add_argument("--operator-object-id")
    setup.add_argument("--alert-email", action="append", required=True, help="Destinatario real para presupuestos y alertas; repetible")
    setup.add_argument("--demo", action="store_true", help="Crear una instalación de evaluación con la muestra Nginx/API; usa un nombre distinto al producto")
    destination = setup.add_mutually_exclusive_group()
    destination.add_argument("--output-dir", help="Carpeta de common.tfvars, dev.tfvars y prod.tfvars; por defecto .local/environments")
    destination.add_argument("--output", help="Formato JSON anterior, opcional")
    recovery = sub.add_parser("recovery-check", help="Verificar un backup local sin conectarse a Azure")
    recovery.add_argument("--backup", required=True)
    identity_cleanup = sub.add_parser("cleanup-identity", help="Retirar el SPN tras el desmontaje, o recuperar su credencial interrumpida")
    identity_cleanup.add_argument("--run", required=True, help="Ruta del run.json que contiene los IDs creados")
    identity_cleanup.add_argument("--credentials-only", action="store_true", help="Retirar solo el certificado de una ejecución interrumpida; conservar SPN y permisos")
    for name in ("check", "render", "validate", "deploy", "plan", "output", "publish-example", "secrets-sync", "backup-state", "smoke-test", "verify-application"):
        command = sub.add_parser(name)
        command.add_argument("--config", default="environments")
        if name in ("publish-example", "secrets-sync", "smoke-test", "verify-application"):
            command.add_argument("--environment", choices=(*ENVIRONMENTS, "all"), default="all")
        if name in ("check", "render", "validate"):
            command.add_argument("--examples", action="store_true", help="Aceptar identificadores ficticios solo para validación local")
        if name in ("deploy", "output"):
            command.add_argument("--stage", choices=(*STAGES, "edge", "all"), default="all")
        if name == "plan":
            command.add_argument("--stage", choices=(*STAGES, "edge"), required=True)
        if name == "deploy":
            command.add_argument("--identity", choices=("installation", "ephemeral", "existing"), default="installation", help="Un SPN por instalación; ephemeral es optativo por ejecución y existing conserva OIDC/MI del operador")
            command.add_argument("--yes", action="store_true", help="Aprobar los cambios de Terraform sin interacción")
            command.add_argument("--reuse-images", action="store_true", help="Usar los digests de la publicación ya revisada, sin reconstruir imágenes")
    return cli


def main():
    args = parser().parse_args()
    os.umask(0o077)
    try:
        if args.command == "configure":
            configure(args)
            return
        if args.command == "recovery-check":
            verify_backup(args.backup)
            return
        if args.command == "cleanup-identity":
            recover_identity(args.run, credentials_only=args.credentials_only)
            return
        cfg = read_config(args.config, examples=getattr(args, "examples", False))
        if args.command == "check":
            print(f"Configuración válida: {cfg['name']}-{cfg['environment']}; backend stlz{cfg['suffix']}.")
            return
        if args.command == "validate":
            validate(cfg)
            return
        deployment = Deployment(cfg, validation=args.command == "render")
        deployment.quiet = args.command == "output"
        with local_lock(deployment.path):
            deployment.prepare()
            if args.command == "render":
                foundation, platform = fixture_contracts(cfg)
                deployment.inputs("platform", foundation)
                for environment in ENVIRONMENTS:
                    deployment.inputs(environment, platform["environments"][environment])
                print(f"Código y entradas de ejemplo: {deployment.path} (contratos ficticios, no desplegables).")
                return
            if args.command == "deploy" and args.identity == "ephemeral":
                recover_abandoned(cfg)
            deployment.preflight()
            if args.command == "deploy":
                if args.identity == "existing":
                    deployment.deploy(args.stage, yes=args.yes, reuse_images=args.reuse_images)
                else:
                    # Registration is a subscription bootstrap operation performed by the operator.
                    deployment.register_providers(args.stage)
                    identity = (InstallationIdentity if args.identity == "installation" else TemporaryIdentity)(cfg)
                    try:
                        with identity:
                            deployment.prepare()
                            deployment.deploy(args.stage, yes=args.yes, reuse_images=args.reuse_images)
                    finally:
                        identity.restore_backend_metadata(deployment)
            elif args.command == "plan":
                deployment.plan(args.stage)
            elif args.command in ("publish-example", "secrets-sync", "smoke-test", "verify-application", "backup-state"):
                if args.command == "backup-state":
                    backup_states(deployment)
                else:
                    deployment.init("platform")
                    targets = ENVIRONMENTS if args.environment == "all" else (args.environment,)
                    for environment in targets:
                        view = deployment.environment_view(environment)
                        if args.command == "publish-example":
                            publish_example(view, execute)
                        elif args.command == "secrets-sync":
                            sync_secrets(view, execute)
                        else:
                            deployment.init(environment)
                            verify_application(view) if args.command == "verify-application" else smoke_test(view)
            else:
                result = {}
                for stage in (*STAGES, *( ("edge",) if cfg["public_entrypoint"]["enabled"] else () )) if args.stage == "all" else (args.stage,):
                    deployment.init(stage)
                    result[stage] = deployment.output(stage)
                print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ConfigError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperación interrumpida. Conserva .lz/ para reanudar.", file=sys.stderr)
        sys.exit(130)
