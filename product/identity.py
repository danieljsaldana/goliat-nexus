"""Installation identities with per-run credentials and operator-owned directory access."""
import base64
import contextvars
import json
import os
import shutil
import signal
import socket
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import ConfigError, ROOT, STAGES, backend_config

ACTIVE = contextvars.ContextVar("deployment_identity", default=None)
ALLOWED_ROLES = ("Contributor", "Managed Identity Operator", "AcrPull", "AcrPush",
    "Storage Blob Data Contributor", "Storage Blob Data Owner", "Storage Queue Data Contributor",
    "Storage Table Data Contributor", "Storage Queue Data Message Sender", "Key Vault Secrets Officer",
    "Key Vault Secrets User", "Key Vault Certificates Officer", "Monitoring Metrics Publisher", "EventGrid Data Sender")


def command_environment(arguments, env):
    identity = ACTIVE.get()
    if identity is None:
        return env
    env = dict(env)
    # Never let an inherited ARM credential silently authenticate the directory provider.
    for key in tuple(env):
        if key.startswith("ARM_") and key not in ("ARM_USE_AZUREAD",):
            del env[key]
    if Path(arguments[0]).name == "terraform":
        env["AZURE_CONFIG_DIR"] = identity.operator_config
        env["TF_VAR_deployment_identity"] = json.dumps(identity.provider_credentials())
    else:
        env["AZURE_CONFIG_DIR"] = str(identity.auth / "azure")
    return env


def run_terraform(arguments, *, env, capture, input_text):
    """Let Terraform stop and persist its state before revoking its identity."""
    process = subprocess.Popen(arguments, env=env, text=True, start_new_session=True,
        stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None,
        stdin=subprocess.PIPE if input_text is not None else None)
    try:
        stdout, stderr = process.communicate(input_text)
    except BaseException:
        print("Deteniendo Terraform antes de retirar la credencial de despliegue…", flush=True)
        if process.poll() is None:
            try: os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError: pass
            try:
                process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: process.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.communicate()
                    print("Terraform no confirmó el cierre normal; revisa el estado y el bloqueo antes de reanudar.", flush=True)
        raise
    return subprocess.CompletedProcess(arguments, process.returncode, stdout, stderr)


def authenticated_backend(cfg, stage):
    result = backend_config(cfg, stage)
    identity = ACTIVE.get()
    if identity:
        result.update(identity.provider_credentials(), use_cli=False, use_msi=False, use_oidc=False)
    return result


def adopt_bootstrap_groups(deployment, stage):
    identity = ACTIVE.get()
    if identity:
        identity.adopt_groups(deployment, stage)


class TemporaryIdentity:
    """The journal contains IDs only. Private keys and token caches live in auth/."""
    def __init__(self, cfg, *, directory=None):
        self.cfg = cfg
        self.root = Path(directory or ROOT / ".lz/identities")
        self.run_id = uuid.uuid4().hex
        self.path = self.root / self.run_id
        self.auth = self.path / "auth"
        self.operator_config = os.environ.get("AZURE_CONFIG_DIR", str(Path.home() / ".azure"))
        self.operator_env = dict(os.environ, AZURE_CONFIG_DIR=self.operator_config)
        self.record = {"run_id": self.run_id, "name": cfg["name"], "tenant_id": cfg["tenant_id"],
            "subscription_id": cfg["subscription_id"], "display_name": "goliat-deploy-" + self.run_id,
            "status": "creating", "assignments": [], "created_groups": [], "pid": os.getpid(), "host": socket.gethostname()}
        self.started = False

    def save(self):
        self.path.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.path / "run.tmp"
        temporary.write_text(json.dumps(self.record, indent=2) + "\n")
        temporary.chmod(0o600)
        temporary.replace(self.path / "run.json")

    def az(self, *args, allow_missing=False, cli_env=None):
        if args[0] in ("role", "group") and "--subscription" not in args:
            args = (*args, "--subscription", self.cfg["subscription_id"])
        result = subprocess.run(["az", *args, "-o", "json", "--only-show-errors"],
            env=cli_env or self.operator_env, text=True, capture_output=True)
        if result.returncode:
            if allow_missing and any(x in result.stderr for x in ("ResourceNotFound", "Request_ResourceNotFound", "does not exist", "not found", "doesn't exist", "404")):
                return None
            # CLI diagnostics can contain OAuth response material: do not echo them.
            raise ConfigError("Falló la operación de identidad: az " + " ".join(args[:3]) + ". Consulta el diario " + str(self.path / "run.json"))
        return json.loads(result.stdout) if result.stdout.strip() else None

    def rest(self, method, url, body=None, *, allow_missing=False):
        args = ["rest", "--method", method, "--url", url]
        if body is not None:
            path = self.path / "request.json"
            path.write_text(json.dumps(body)); path.chmod(0o600)
            args += ["--body", "@" + str(path)]
        try:
            return self.az(*args, allow_missing=allow_missing)
        finally:
            (self.path / "request.json").unlink(missing_ok=True)

    def owned_group(self, name):
        group = self.az("group", "show", "--name", name, "--subscription", self.cfg["subscription_id"], allow_missing=True)
        if group and (group.get("tags", {}).get("Project") != self.cfg["name"] or group.get("tags", {}).get("Product") != "Goliat - Nexus"):
            raise ConfigError("El grupo ya existe y no pertenece a esta instalación: " + name)
        if group is None:
            group = self.az("group", "create", "--name", name, "--location", self.cfg["location"],
                "--subscription", self.cfg["subscription_id"], "--tags", "ManagedBy=Terraform", "Product=Goliat - Nexus", "Project=" + self.cfg["name"], "Environment=shared")
            self.record["created_groups"].append(group["id"]); self.save()
        return group["id"]

    def grant(self, role, scope, *, condition=None):
        assignment = {"id": str(uuid.uuid4()), "scope": scope}
        self.record["assignments"].append(assignment); self.save()  # Before the write.
        args = ["role", "assignment", "create", "--name", assignment["id"], "--scope", scope,
            "--assignee-object-id", self.record["principal_id"], "--assignee-principal-type", "ServicePrincipal", "--role", role]
        if condition:
            args += ["--condition", condition, "--condition-version", "2.0"]
        self.az(*args)

    def check_operator(self):
        account = self.az("account", "show", "--subscription", self.cfg["subscription_id"])
        if account["tenantId"].lower() != self.cfg["tenant_id"].lower() or account["user"]["type"].lower() != "user":
            raise ConfigError("El bootstrap local requiere az login de usuario en el tenant configurado. Para OIDC/MI usa --identity existing.")

    def prepare_certificate(self):
        self.auth.mkdir(parents=True, mode=0o700)
        expiry = datetime.now(timezone.utc) + timedelta(hours=4)
        self.record["expires_at"] = expiry.isoformat()
        commands = [
            ["openssl", "req", "-x509", "-newkey", "rsa:3072", "-sha256", "-nodes", "-keyout", str(self.auth / "key.pem"), "-out", str(self.auth / "cert.pem"), "-days", "1", "-subj", "/CN=Goliat temporary deployment"],
            ["openssl", "pkcs12", "-export", "-out", str(self.auth / "identity.pfx"), "-inkey", str(self.auth / "key.pem"), "-in", str(self.auth / "cert.pem"), "-passout", "pass:"],
        ]
        for command in commands:
            if subprocess.run(command, capture_output=True).returncode:
                raise ConfigError("No se pudo preparar el certificado temporal de despliegue.")
        public = subprocess.run(["openssl", "x509", "-in", str(self.auth / "cert.pem"), "-outform", "DER"], capture_output=True, check=True).stdout
        self.record["key_id"] = str(uuid.uuid4()); self.save()
        return {"keyId": self.record["key_id"], "type": "AsymmetricX509Cert", "usage": "Verify",
            "key": base64.b64encode(public).decode(), "endDateTime": expiry.isoformat()}

    def create(self):
        self.check_operator()
        self.started = True
        self.save()
        credential = self.prepare_certificate()
        app = self.rest("POST", "https://graph.microsoft.com/v1.0/applications", {
            "displayName": self.record["display_name"], "signInAudience": "AzureADMyOrg",
            "tags": ["GoliatInstallationDeployment" if self.record.get("lifecycle") == "installation" else "GoliatTemporaryDeployment", self.run_id],
            "keyCredentials": [credential]})
        self.record.update(app_object_id=app["id"], client_id=app["appId"]); self.save()
        principal = self.az("ad", "sp", "create", "--id", app["appId"])
        self.record["principal_id"] = principal["id"]; self.save()
        groups = [self.owned_group(self.cfg["name"] + "-" + suffix + "-rg") for suffix in ("shared-state", "connectivity", "shared", "dev", "prod")]
        roles = {r["roleName"]: r["name"] for r in self.az("role", "definition", "list", "--subscription", self.cfg["subscription_id"])}
        role_set = ", ".join(roles[n] for n in ALLOWED_ROLES)
        condition = "((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {" + role_set + "})) AND ((!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'})) OR (@Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {" + role_set + "}))"
        for scope in groups:
            self.grant(roles["Contributor"], scope)
            self.grant(roles["Role Based Access Control Administrator"], scope, condition=condition)
        self.grant(roles["Storage Blob Data Contributor"], groups[0])
        self.grant(roles["AcrPush"], groups[2])
        for scope in groups[2:]:
            self.grant(roles["Key Vault Secrets Officer"], scope)
        self.grant(roles["Key Vault Certificates Officer"], groups[2])
        sub = "/subscriptions/" + self.cfg["subscription_id"]
        role_name = "Goliat deployment metadata " + self.run_id
        self.record["metadata_role_name"] = role_name; self.save()
        metadata = self.az("role", "definition", "create", "--subscription", self.cfg["subscription_id"], "--role-definition", json.dumps({
            "Name": role_name, "IsCustom": True, "Description": "Nexus installation subscription metadata and budget access.",
            "Actions": ["Microsoft.Resources/subscriptions/read", "Microsoft.Resources/subscriptions/locations/read", "Microsoft.Resources/subscriptions/providers/read", "Microsoft.Consumption/budgets/read", "Microsoft.Consumption/budgets/write", "Microsoft.Consumption/budgets/delete"],
            "NotActions": [], "DataActions": [], "NotDataActions": [], "AssignableScopes": [sub]}))
        self.record["metadata_role_id"] = metadata["name"]; self.save()
        self.grant(metadata["name"], sub)
        self.login(groups)
        self.record["status"] = "active"; self.save()
        print("SPN de despliegue preparado; certificado limitado a cuatro horas.", flush=True)

    def login(self, groups):
        (self.auth / "login.pem").write_bytes((self.auth / "key.pem").read_bytes() + (self.auth / "cert.pem").read_bytes())
        for file in self.auth.iterdir():
            if file.is_file(): file.chmod(0o600)
        login_env = dict(self.operator_env, AZURE_CONFIG_DIR=str(self.auth / "azure"))
        for attempt in range(24):
            try:
                self.az("login", "--service-principal", "--username", self.record["client_id"], "--certificate", str(self.auth / "login.pem"), "--tenant", self.cfg["tenant_id"], "--allow-no-subscriptions", cli_env=login_env)
                self.az("account", "set", "--subscription", self.cfg["subscription_id"], cli_env=login_env)
                self.az("provider", "show", "--namespace", "Microsoft.Storage", "--subscription", self.cfg["subscription_id"], cli_env=login_env)
                for scope in groups:
                    self.az("group", "show", "--name", scope.rsplit("/", 1)[-1], cli_env=login_env)
                break
            except ConfigError:
                if attempt == 23: raise
                time.sleep(5)

    def provider_credentials(self):
        return {"client_id": self.record["client_id"], "client_certificate_path": str(self.auth / "identity.pfx")}

    def adopt_groups(self, deployment, stage):
        targets = {"azurerm_resource_group.state": self.cfg["name"] + "-shared-state-rg"} if stage == "foundation" else {
            'azurerm_resource_group.this["' + key + '"]': self.cfg["name"] + "-" + key + "-rg" for key in ("connectivity", "shared", "dev", "prod")} if stage == "platform" else {}
        if not targets: return
        result = deployment.tf(stage, "state", "list", capture=True, allow_failure=True)
        if result.returncode and not any(x in result.stderr for x in ("No state file", "No stored state", "No state")):
            raise ConfigError("No se pudo comprobar el estado antes de adoptar los grupos del bootstrap.")
        existing = set(result.stdout.splitlines())
        for address, name in targets.items():
            if address not in existing:
                scope = "/subscriptions/" + self.cfg["subscription_id"] + "/resourceGroups/" + name
                deployment.tf(stage, "import", "-input=false", "-var-file=inputs.auto.tfvars.json", address, scope)

    def cleanup(self):
        self.record["status"] = "cleanup-pending"; self.save()
        errors = []
        # Discover a create that succeeded remotely before the local process lost its response.
        if not self.record.get("app_object_id"):
            matches = self.az("ad", "app", "list", "--display-name", self.record["display_name"])
            owned = [x for x in matches if self.run_id in x.get("tags", [])]
            if len(owned) > 1: raise ConfigError("Más de una aplicación coincide con el diario temporal.")
            if owned:
                self.record.update(app_object_id=owned[0]["id"], client_id=owned[0]["appId"]); self.save()
        app = None
        if self.record.get("app_object_id"):
            app = self.az("ad", "app", "show", "--id", self.record["app_object_id"], allow_missing=True)
            if app and (app["displayName"] != self.record["display_name"] or self.run_id not in app.get("tags", []) or app["appId"] != self.record["client_id"]):
                raise ConfigError("La identidad no coincide con el diario; se bloquea su eliminación.")
            if app:
                try:
                    self.rest("PATCH", "https://graph.microsoft.com/v1.0/applications/" + app["id"], {"keyCredentials": []})
                except ConfigError as exc: errors.append(str(exc))
        for assignment in self.record["assignments"]:
            if assignment.get("removed"): continue
            try:
                rid = assignment["scope"] + "/providers/Microsoft.Authorization/roleAssignments/" + assignment["id"]
                current = self.rest("GET", "https://management.azure.com" + rid + "?api-version=2022-04-01", allow_missing=True)
                if current:
                    if current["properties"]["principalId"].lower() != self.record["principal_id"].lower():
                        raise ConfigError("Asignación ajena al SPN temporal.")
                    self.az("role", "assignment", "delete", "--ids", rid)
                assignment["removed"] = True; self.save()
            except ConfigError as exc: errors.append(str(exc))
        if self.record.get("client_id"):
            try:
                principal = self.az("ad", "sp", "show", "--id", self.record["client_id"], allow_missing=True)
                if principal:
                    if principal["appId"] != self.record["client_id"] or principal["displayName"] != self.record["display_name"] or (self.record.get("principal_id") and principal["id"] != self.record["principal_id"]):
                        raise ConfigError("El service principal no coincide con el diario temporal.")
                    self.az("ad", "sp", "delete", "--id", principal["id"])
                if app: self.az("ad", "app", "delete", "--id", app["id"])
                if self.az("ad", "sp", "show", "--id", self.record["client_id"], allow_missing=True) or self.az("ad", "app", "show", "--id", self.record["app_object_id"], allow_missing=True):
                    raise ConfigError("Azure aún devuelve la identidad temporal después de eliminarla.")
            except ConfigError as exc: errors.append(str(exc))
        if self.record.get("metadata_role_name"):
            try:
                roles = self.az("role", "definition", "list", "--name", self.record["metadata_role_name"], "--subscription", self.cfg["subscription_id"])
                for role in roles:
                    self.az("role", "definition", "delete", "--name", role["name"], "--subscription", self.cfg["subscription_id"])
            except ConfigError as exc: errors.append(str(exc))
        shutil.rmtree(self.auth, ignore_errors=True)
        if errors:
            self.record["cleanup_errors"] = errors; self.save()
            raise ConfigError("Limpieza de identidad incompleta. Reintenta ./lz cleanup-identity --run " + str(self.path / "run.json"))
        self.record["status"] = "clean"; self.record.pop("cleanup_errors", None); self.save()
        print("SPN de despliegue, aplicación, credenciales y permisos retirados; sesión del operador conservada.", flush=True)

    def restore_backend_metadata(self, deployment):
        for stage in (*STAGES, "edge"):
            folder = deployment.path / "stacks" / stage
            if not folder.exists(): continue
            (folder / "backend.hcl").write_text("".join(f"{k} = {json.dumps(v)}\n" for k, v in backend_config(self.cfg, stage).items()))
            cache = folder / ".terraform/terraform.tfstate"
            if cache.exists() and self.record.get("client_id") and self.record["client_id"] in cache.read_text():
                cache.unlink()  # Backend connection cache, never the resource state.

    def __enter__(self):
        self.previous_sigterm = signal.signal(signal.SIGTERM, self.interrupt)
        try:
            self.create()
        except BaseException:
            try:
                if self.started:
                    self.cleanup()
            finally:
                shutil.rmtree(self.auth, ignore_errors=True)
                signal.signal(signal.SIGTERM, self.previous_sigterm)
            raise
        self.token = ACTIVE.set(self)
        return self

    def __exit__(self, kind, value, traceback):
        ACTIVE.reset(self.token)
        try:
            self.cleanup()
        finally:
            shutil.rmtree(self.auth, ignore_errors=True)
            signal.signal(signal.SIGTERM, self.previous_sigterm)

    @staticmethod
    def interrupt(number, frame):
        raise KeyboardInterrupt()


class InstallationIdentity(TemporaryIdentity):
    """Keep the application, principal and RBAC until the installation is retired."""
    def __init__(self, cfg, *, directory=None):
        super().__init__(cfg, directory=directory)
        self.path = self.root / ("installation-" + cfg["name"] + "-" + cfg["suffix"])
        self.auth = self.path / "auth"
        journal = self.path / "run.json"
        if journal.exists():
            previous = json.loads(journal.read_text())
            if any(previous.get(key) != cfg[key] for key in ("name", "tenant_id", "subscription_id", "suffix")):
                raise ConfigError("El diario de instalación pertenece a otra configuración.")
            if previous.get("status") != "clean":
                self.record = previous
                self.run_id = previous["run_id"]
        self.record.update(lifecycle="installation", suffix=cfg["suffix"],
            display_name="goliat-installation-" + cfg["name"] + "-" + cfg["suffix"])

    def application(self):
        app = self.rest("GET", "https://graph.microsoft.com/v1.0/applications/" + self.record["app_object_id"]
            + "?$select=id,appId,displayName,tags,keyCredentials")
        if (app["appId"] != self.record["client_id"] or app["displayName"] != self.record["display_name"]
                or self.run_id not in app.get("tags", [])):
            raise ConfigError("La identidad no coincide con el diario de instalación.")
        return app

    def revoke_certificate(self):
        key_id = self.record.get("key_id")
        if key_id:
            app = self.application()
            keys = [key for key in app.get("keyCredentials", []) if key["keyId"] != key_id]
            if len(keys) != len(app.get("keyCredentials", [])):
                self.rest("PATCH", "https://graph.microsoft.com/v1.0/applications/" + app["id"], {"keyCredentials": keys})
            self.record.pop("key_id", None)
        self.record.pop("expires_at", None)
        self.save()

    def ensure_idle(self):
        if self.record.get("status") in ("installed", "clean"):
            return
        if self.record.get("host") != socket.gethostname():
            raise ConfigError("Hay una credencial pendiente de otra máquina; comprueba que terminó antes de recuperar el diario.")
        try:
            os.kill(self.record["pid"], 0)
        except ProcessLookupError:
            return
        except PermissionError:
            pass
        raise ConfigError("La identidad está en uso por otro proceso; se conserva su credencial.")

    def create(self):
        self.check_operator()
        if not self.record.get("installation_ready"):
            if self.record.get("app_object_id"):
                raise ConfigError("Bootstrap de identidad incompleto. Recupera con ./lz cleanup-identity --run " + str(self.path / "run.json") + " --credentials-only antes de reintentar.")
            if self.az("ad", "app", "list", "--display-name", self.record["display_name"]):
                raise ConfigError("Ya existe una identidad con ese nombre. Recupera su diario; no se creará un duplicado.")
            super().create()
            self.record["installation_ready"] = True
        else:
            self.ensure_idle()
            self.application()
            principal = self.az("ad", "sp", "show", "--id", self.record["client_id"])
            if principal["id"] != self.record["principal_id"]:
                raise ConfigError("El service principal no coincide con el diario de instalación.")
            self.started = True
            # Recover only this journal's interrupted credential, never the SPN or RBAC.
            self.revoke_certificate()
            shutil.rmtree(self.auth, ignore_errors=True)
            self.record.update(status="credential-pending", pid=os.getpid(), host=socket.gethostname())
            credential = self.prepare_certificate()
            app = self.application()
            self.rest("PATCH", "https://graph.microsoft.com/v1.0/applications/" + app["id"],
                {"keyCredentials": [*app.get("keyCredentials", []), credential]})
            groups = ["/subscriptions/" + self.cfg["subscription_id"] + "/resourceGroups/" + self.cfg["name"] + "-" + suffix + "-rg"
                for suffix in ("shared-state", "connectivity", "shared", "dev", "prod")]
            self.login(groups)
        self.record.update(status="active", pid=os.getpid(), host=socket.gethostname()); self.save()
        print("SPN de la instalación reutilizable; solo se retirará la credencial al terminar.", flush=True)

    def cleanup(self):
        if not self.record.get("installation_ready"):
            return super().cleanup()  # Roll back an incomplete identity bootstrap.
        try:
            self.revoke_certificate()
        except Exception:
            self.record["status"] = "credential-cleanup-pending"; self.save()
            raise
        finally:
            shutil.rmtree(self.auth, ignore_errors=True)
        self.record["status"] = "installed"; self.save()
        print("Credencial y caché retiradas. SPN y permisos conservados para esta instalación.", flush=True)

    def retire(self):
        self.ensure_idle()
        remaining = [self.cfg["name"] + "-" + suffix + "-rg" for suffix in ("shared-state", "connectivity", "shared", "dev", "prod")
            if self.az("group", "exists", "--name", self.cfg["name"] + "-" + suffix + "-rg")]
        if remaining:
            raise ConfigError("No se retira el SPN mientras existan grupos de la instalación: " + ", ".join(remaining))
        super().cleanup()


def recover_identity(path, *, credentials_only=False):
    path = Path(path).resolve()
    record = json.loads(path.read_text())
    installation = record.get("lifecycle") == "installation"
    expected = "goliat-installation-" + record["name"] + "-" + record["suffix"] if installation else "goliat-deploy-" + record.get("run_id", "")
    if not record.get("run_id") or record.get("display_name") != expected:
        raise ConfigError("El archivo no es un diario de identidad de Nexus.")
    cfg = {key: record[key] for key in ("name", "tenant_id", "subscription_id", *(("suffix",) if installation else ()))}
    identity = (InstallationIdentity if installation else TemporaryIdentity)(cfg, directory=path.parent.parent)
    identity.record, identity.run_id, identity.path, identity.auth = record, record["run_id"], path.parent, path.parent / "auth"
    account = identity.az("account", "show", "--subscription", cfg["subscription_id"])
    if account["tenantId"].lower() != cfg["tenant_id"].lower(): raise ConfigError("El diario pertenece a otro tenant.")
    if installation:
        identity.ensure_idle()
    if installation and not credentials_only:
        # A blocked retirement must not alter active installation files.
        identity.retire()
        return
    try:
        if credentials_only and not installation:
            raise ConfigError("--credentials-only requiere un diario de instalación.")
        identity.cleanup()
    finally:
        shutil.rmtree(identity.auth, ignore_errors=True)


def recover_abandoned(cfg, *, directory=None):
    """Reconcile dead local runs; never revoke credentials of a live process."""
    root = Path(directory or ROOT / ".lz/identities")
    for path in root.glob("*/run.json"):
        record = json.loads(path.read_text())
        if record.get("lifecycle") == "installation" or record.get("status") == "clean" or any(record.get(key) != cfg[key] for key in ("name", "tenant_id", "subscription_id")):
            continue
        if record.get("host") != socket.gethostname() or not isinstance(record.get("pid"), int):
            raise ConfigError("Hay una identidad pendiente de otra máquina. Revisa ./lz cleanup-identity --run " + str(path))
        try:
            os.kill(record["pid"], 0)
        except ProcessLookupError:
            recover_identity(path)
        except PermissionError:
            raise ConfigError("No se puede confirmar el fin de la ejecución anterior; se conserva su identidad.") from None
        else:
            raise ConfigError("Otra ejecución conserva un SPN activo. Espera a que termine; no se revocará su identidad.")
