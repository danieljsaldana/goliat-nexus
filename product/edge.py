"""Shared WAF entry, private certificate issuance and locked-down portal publication."""
import base64
import hashlib
import json
import re
import ssl
import tempfile
import time
import uuid
from pathlib import Path
from urllib.request import urlopen
from .config import ConfigError, ROOT


def swa_configuration(public_ip, directory, prefix, forwarded_hosts=()):
    import ipaddress
    ip = ipaddress.ip_address(public_ip)
    if ip.version != 4:
        raise ConfigError("El origen SWA requiere la IPv4 del WAF.")
    hashes = set()
    for path in Path(directory).rglob("*.html"):
        for script in re.findall(r"<script\b[^>]*>(.*?)</script>", path.read_text(), re.S | re.I):
            if script.strip():
                hashes.add("'sha256-" + base64.b64encode(hashlib.sha256(script.encode()).digest()).decode() + "'")
    policy = "default-src 'self'; script-src 'self' " + " ".join(sorted(hashes)) + "; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://login.microsoftonline.com https://*.msauth.net https://*.msftauth.net; frame-src 'self' https://login.microsoftonline.com; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
    config = {"networking": {"allowedIpRanges": [str(ip)+"/32"]}, "globalHeaders": {
        "Content-Security-Policy": policy, "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer", "Permissions-Policy": "camera=(), microphone=(), geolocation=()", "Strict-Transport-Security": "max-age=31536000"},
        "routes": [{"route": prefix+"/config.json", "headers": {"Cache-Control": "no-store"}}, {"route": prefix+"/redirect/*", "headers": {"Content-Security-Policy": policy.replace("frame-ancestors 'none'", "frame-ancestors 'self'")}}]}
    if forwarded_hosts:config["forwardingGateway"]={"allowedForwardedHosts":list(forwarded_hosts)}
    return config


def edge_contracts(deployment):
    deployment.init("platform")
    platform = deployment.output("platform")
    workloads = {}
    for env in ("dev", "prod"):
        deployment.init(env)
        workloads[env] = deployment.output(env)
    return {"platform": platform, "workloads": workloads}


def edge_image(deployment):
    try:
        manifest = json.loads((deployment.path/"edge-images.json").read_text())
        image = manifest["image"]
        if not re.fullmatch(r"[a-z0-9.-]+/example/certificates@sha256:[a-f0-9]{64}", image):
            raise ValueError()
        return image
    except (OSError, ValueError, KeyError):
        raise ConfigError("Publica el gestor de certificados mediante deploy --stage edge desde el ejecutor privado.") from None


def check_public_plan(plan):
    """Fail closed before apply when a public edge plan weakens required controls."""
    def resources(module):
        return module.get("resources", []) + [r for child in module.get("child_modules", []) for r in resources(child)]
    all_resources=resources(plan["planned_values"]["root_module"])
    gateways=[r["values"] for r in all_resources if r["type"]=="azurerm_application_gateway"]
    policies=[r["values"] for r in all_resources if r["type"]=="azurerm_web_application_firewall_policy"]
    if len(gateways)!=1 or len(policies)!=1:raise ConfigError("Se requiere un WAF compartido y su política.")
    policy=policies[0]["policy_settings"][0]
    if policy.get("mode")!="Prevention" or policy.get("enabled") is not True:raise ConfigError("La política WAF debe bloquear ataques.")
    gateway=gateways[0]
    if gateway["sku"][0]["name"]!="WAF_v2":raise ConfigError("La entrada pública requiere WAF_v2.")
    for backend in gateway["backend_http_settings"]:
        if backend["protocol"]!="Https" or backend["port"]!=443 or backend.get("certificate_chain_validation_enabled") is not True or backend.get("sni_validation_enabled") is not True:
            raise ConfigError("Todos los orígenes necesitan TLS validado y SNI.")
    for certificate in gateway["ssl_certificate"]:
        if not certificate.get("key_vault_secret_id") or certificate.get("data"):
            raise ConfigError("El certificado debe referenciar Key Vault; no se permite PFX en Terraform.")
    for change in plan.get("resource_changes",[]):
        if change.get("mode")=="managed" and "delete" in change["change"]["actions"]:
            raise ConfigError("El plan de publicación contiene eliminaciones: revisa una migración explícita antes de aplicarlo.")


def prepare_public_entrypoint(deployment, execute, *, reuse_images=False, contracts=None):
    from .operations import private_address, isolated_docker_config
    if not deployment.cfg["public_entrypoint"]["enabled"]:
        raise ConfigError("public_entrypoint.enabled está desactivado.")
    contracts = contracts if contracts is not None else edge_contracts(deployment)
    platform = contracts["platform"];entry = platform["public_entrypoint"]
    private_address(platform["registry_login_server"], deployment.cfg["network"]["endpoints_subnet_cidr"], 443)
    private_address(entry["vault"]["name"]+".vault.azure.net", deployment.cfg["network"]["endpoints_subnet_cidr"], 443)
    if not reuse_images:
        with tempfile.TemporaryDirectory(prefix="edge-image-",dir=deployment.path) as folder:
            env = isolated_docker_config(folder)
            registry = platform["registry_login_server"]
            execute(["az","acr","login","--name",registry.split('.')[0],"-o","none"],capture=True,env_updates=env)
            metadata=Path(folder)/"digest.json"
            execute(["docker","buildx","build","--platform","linux/amd64","--push","--metadata-file",str(metadata),"--tag",f"{registry}/example/certificates:{uuid.uuid4().hex[:12]}",str(ROOT/"apps/certificates")],env_updates=env)
            digest=json.loads(metadata.read_text())["containerimage.digest"]
            if not re.fullmatch(r"sha256:[a-f0-9]{64}",digest):raise ConfigError("Digest del gestor de certificados inválido.")
            path=deployment.path/"edge-images.json";path.write_text(json.dumps({"image":f"{registry}/example/certificates@{digest}"}));path.chmod(0o600)
    supplied = deployment.cfg["public_entrypoint"]["certificate_secret_id"]
    if not supplied:
        result=execute(["az","keyvault","certificate","show","--vault-name",entry["vault"]["name"],"--name","waf-tls","-o","json"],capture=True,allow_failure=True,redact_errors=True)
        if result.returncode:
            if "CertificateNotFound" not in result.stderr:
                raise ConfigError("No se puede comprobar el certificado privado: revisa DNS y Certificates Officer.")
            names=sorted(set([entry["azure_hostname"],entry["origin"].removeprefix('https://'),*[v.removeprefix('https://') for v in entry['environment_origins'].values()]]))
            policy={"issuerParameters":{"name":"Self"},"keyProperties":{"exportable":True,"keyType":"RSA","keySize":2048,"reuseKey":False},"secretProperties":{"contentType":"application/x-pkcs12"},"x509CertificateProperties":{"subject":"CN="+names[0],"subjectAlternativeNames":{"dnsNames":names},"validityInMonths":1,"keyUsage":["digitalSignature","keyEncipherment"]}}
            with tempfile.TemporaryDirectory(prefix="tls-bootstrap-",dir=deployment.path) as folder:
                path=Path(folder)/"policy.json";path.write_text(json.dumps(policy));path.chmod(0o600)
                execute(["az","keyvault","certificate","create","--vault-name",entry["vault"]["name"],"--name","waf-tls","--policy","@"+str(path),"-o","none"],capture=True,redact_errors=True)
    return {**contracts,"edge_image":edge_image(deployment)}


def apply_public_entrypoint(deployment, execute, integration, *, yes=False):
    deployment.inputs("edge",integration)
    deployment.init("edge")
    deployment.apply_saved_plan("edge", "public-entrypoint.tfplan", yes=yes, verify=check_public_plan)
    output=deployment.output("edge")
    return output


def wait_public_entrypoint(deployment, execute, output):
    deployment.init("platform")
    entry=deployment.output("platform")["public_entrypoint"]
    supplied=deployment.cfg["public_entrypoint"]["certificate_secret_id"]
    if not supplied:
        print("WAF creado. Esperando la emisión pública del certificado; el bootstrap aún no se considera listo.",flush=True)
        for _ in range(120):
            result=execute(["az","keyvault","certificate","show","--vault-name",entry["vault"]["name"],"--name","waf-tls","-o","json"],capture=True,redact_errors=True)
            certificate=json.loads(result.stdout)
            if certificate.get("tags",{}).get("Issuer")=="ACME":break
            time.sleep(10)
        else:raise ConfigError("El certificado público no se emitió. Revisa el gestor de certificados, su ruta HTTP-01 y DNS; no se declara listo el servicio.")
        version=certificate['id'].rsplit('/',1)[-1]
        execute(["az","network","application-gateway","update","--ids",output["gateway_id"],"--set","tags.CertificateVersion="+version,"-o","none"],capture=True,redact_errors=True)
    for _ in range(60):
        try:
            with urlopen(output["origin"]+"/healthz",timeout=15,context=ssl.create_default_context()) as response:
                if response.status==200:break
        except (OSError,ValueError):time.sleep(10)
    else:raise ConfigError("No se ha acreditado HTTPS público válido a través del WAF.")
    print("Entrada pública lista: "+output["origin"],flush=True)
    return output


def deploy_public_entrypoint(deployment, execute, *, yes=False, reuse_images=False):
    integration=prepare_public_entrypoint(deployment,execute,reuse_images=reuse_images)
    output=apply_public_entrypoint(deployment,execute,integration,yes=yes)
    return wait_public_entrypoint(deployment,execute,output)


def validation_contracts(cfg, platform):
    """Fictitious inputs for provider-free edge validation; never used for deployment."""
    import copy
    platform=copy.deepcopy(platform)
    shared=f"/subscriptions/{cfg['subscription_id']}/resourceGroups/{cfg['name']}-shared-rg/providers"
    network=f"/subscriptions/{cfg['subscription_id']}/resourceGroups/{cfg['name']}-connectivity-rg/providers/Microsoft.Network"
    origin=f"https://{cfg['name']}.{cfg['location']}.cloudapp.azure.com"
    identity=platform['environments']['dev']['identities']['frontend']
    platform['public_entrypoint']={'origin':origin,'azure_hostname':origin.removeprefix('https://'),'environment_origins':{e:origin for e in ('dev','prod')},'public_ip_id':network+'/publicIPAddresses/waf','public_ip':'203.0.113.11','gateway_subnet_id':network+'/virtualNetworks/hub/subnets/gateway','gateway_subnet_cidr':cfg['network']['gateway_subnet_cidr'],'resource_group_name':cfg['name']+'-connectivity-rg','shared_resource_group_name':cfg['name']+'-shared-rg','workspace_id':platform['workspace_id'],'vault':{'id':shared+'/Microsoft.KeyVault/vaults/kv-tls-'+cfg['suffix'],'name':'kv-tls-'+cfg['suffix'],'uri':f"https://kv-tls-{cfg['suffix']}.vault.azure.net/"},'identities':{'waf':identity,'certificates':identity},'environment_id':shared+'/Microsoft.App/managedEnvironments/edge','environment_domain':'example.azurecontainerapps.io','lock_blob_url':f"https://stlz{cfg['suffix']}.blob.core.windows.net/certificate-locks/renewal.lock"}
    for env,values in platform['environments'].items():
        for key,web in values['webs'].items():web['public_url']=f'{origin}/{env}/{key}/'
    return {'platform':platform,'workloads':{env:{'demo_url':f"https://{cfg['name']}-{env}-frontend.example.azurecontainerapps.io"} for env in ('dev','prod')},'edge_image':platform['registry_login_server']+'/example/certificates@sha256:'+'a'*64}
