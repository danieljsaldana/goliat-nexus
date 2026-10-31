#!/usr/bin/env python3
"""Register a private GitHub runner over Azure Run Command, without a stored PAT."""
import argparse
import json
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

API_VERSION = "2025-04-01"
RUNNER_VERSION = "2.338.2"
RUNNER_SHA256 = "baebf204307bac6193480852732f0aba2ae97b6c5597c244f4d5558390147c40"


def command(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Falló {arguments[0]}; comprueba la sesión y los permisos del operador.")
    return result.stdout.strip()


def arm_request(url, token, *, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    request = Request(url, data=data, method=method, headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    with urlopen(request, timeout=60) as response:
        content = response.read()
        return json.loads(content) if content else {}


def run_protected(vm_id, location, name, script, azure_token, *, protected=None, timeout=1200):
    """Keep protected values in memory; return execution results, never the request."""
    # A fresh resource avoids mistaking a previous instanceView for this execution.
    name = name + "-" + uuid.uuid4().hex[:12]
    url = "https://management.azure.com" + vm_id + "/runCommands/" + name + "?api-version=" + API_VERSION
    properties = {"source": {"script": script}, "asyncExecution": True, "timeoutInSeconds": timeout}
    if protected:
        properties["protectedParameters"] = [{"name": key, "value": value} for key, value in protected.items()]
    arm_request(url, azure_token, method="PUT", body={"location": location, "properties": properties})
    deadline = time.monotonic() + timeout + 120
    last = None
    while time.monotonic() < deadline:
        result = arm_request(url + "&$expand=instanceView", azure_token)
        view = result.get("properties", {}).get("instanceView", {})
        state = view.get("executionState")
        if state != last:
            print("Azure Run Command:", state or "Pending", flush=True)
            last = state
        if state in ("Succeeded", "Failed", "TimedOut", "Canceled"):
            text = "\n".join(str(view.get(key, "")) for key in ("output", "error", "executionMessage"))
            for secret in [azure_token, *(protected or {}).values()]:
                text = text.replace(secret, "[REDACTED]")
            if state != "Succeeded" or view.get("exitCode", 0) != 0:
                raise RuntimeError("Falló el script remoto. " + text[-3000:])
            return {"name": name, "state": state, "exit_code": view.get("exitCode"), "output": text}
        time.sleep(5)
    raise RuntimeError("Se agotó el tiempo de Run Command; consulta su instanceView antes de reintentar.")


def runner_script(repository, name, labels):
    for value in [name, *labels]:
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
            raise ValueError("Nombre o etiqueta de agente inválido.")
    return r'''#!/bin/bash
set -euo pipefail
for i in $(seq 1 120); do
  test -f /var/lib/goliat-nexus/bootstrap-ready && break
  sleep 5
done
test -f /var/lib/goliat-nexus/bootstrap-ready
id ghactions >/dev/null 2>&1 || useradd --create-home --shell /bin/bash ghactions
usermod -aG docker ghactions
install -d -m 0700 -o ghactions -g ghactions /opt/goliat-runner
curl -fsSL __DOWNLOAD__ -o /tmp/goliat-runner.tar.gz
printf '%s  /tmp/goliat-runner.tar.gz\n' __SHA__ | sha256sum -c -
tar -xzf /tmp/goliat-runner.tar.gz -C /opt/goliat-runner
cd /opt/goliat-runner
./bin/installdependencies.sh >/var/log/goliat-runner-dependencies.log 2>&1
chown -R ghactions:ghactions /opt/goliat-runner
chmod 0700 /opt/goliat-runner
export ACTIONS_RUNNER_INPUT_TOKEN="${registrationToken:?missing protected registration token}"
unset registrationToken
runuser -u ghactions -- ./config.sh --unattended --url __REPOSITORY__ --name __NAME__ --labels __LABELS__ --no-default-labels --work _work
unset ACTIONS_RUNNER_INPUT_TOKEN
./svc.sh install ghactions
./svc.sh start
echo GOLIAT_RUNNER_REGISTERED
'''.replace("__DOWNLOAD__", shlex.quote(f"https://github.com/actions/runner/releases/download/v{RUNNER_VERSION}/actions-runner-linux-x64-{RUNNER_VERSION}.tar.gz")).replace("__SHA__", shlex.quote(RUNNER_SHA256)).replace("__REPOSITORY__", shlex.quote("https://github.com/" + repository)).replace("__NAME__", shlex.quote(name)).replace("__LABELS__", shlex.quote(",".join(labels)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", required=True, help="Directorio Terraform del ejemplo agent, ya aplicado")
    args = parser.parse_args()
    directory = Path(args.directory).resolve()
    runner = json.loads(command(["terraform", "-chdir=" + str(directory), "output", "-json", "runner"]))
    repo = runner["github_repository"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Configura github_repository como propietario/repositorio.")
    metadata = json.loads(command(["gh", "api", "repos/" + repo]))
    if not metadata.get("private") or not metadata.get("permissions", {}).get("admin"):
        raise ValueError("El ejemplo requiere un repositorio privado administrado por el operador autenticado.")
    existing = json.loads(command(["gh", "api", f"repos/{repo}/actions/runners"]))
    if any(item["name"] == runner["name"] for item in existing["runners"]):
        raise ValueError("Ya existe un agente con ese nombre; revísalo o usa otro nombre antes de registrar.")
    vm_id = runner["id"]
    if not re.fullmatch(r"/subscriptions/[0-9a-fA-F-]+/resourceGroups/[A-Za-z0-9_.()-]+/providers/Microsoft.Compute/virtualMachines/[A-Za-z0-9_.-]+", vm_id):
        raise ValueError("ID de VM inválido.")
    subscription = vm_id.split("/")[2]
    azure_token = command(["az", "account", "get-access-token", "--subscription", subscription, "--resource", "https://management.azure.com/", "--query", "accessToken", "-o", "tsv"])
    registration = json.loads(command(["gh", "api", "--method", "POST", f"repos/{repo}/actions/runners/registration-token"]))
    script = runner_script(repo, runner["name"], runner["github_labels"])
    result = run_protected(vm_id, runner["location"], "goliat-register-github-runner", script, azure_token, protected={"registrationToken": registration["token"]})
    print(result["output"].strip())
    for _ in range(12):
        status = json.loads(command(["gh", "api", f"repos/{repo}/actions/runners"]))
        match = next((item for item in status["runners"] if item["name"] == runner["name"]), None)
        if match and match["status"] == "online":
            print(f"Agente online en {repo}: {runner['name']} ({', '.join(runner['github_labels'])}).")
            return
        time.sleep(5)
    raise RuntimeError("El registro terminó, pero GitHub aún no confirma el agente online.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        print("Error:", error, file=sys.stderr)
        sys.exit(1)
