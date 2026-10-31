# Agente GitHub Actions privado opcional

[English](README.md) · **Español**

Consume el módulo `modules/virtual_machine` de Nexus. Usa una subred existente de Nexus, SSH por clave, Secure Boot, vTPM e identidad administrada. La VM no tiene IP pública ni recibe roles Azure por defecto. La instalación usa repositorios oficiales por HTTPS y verifica los binarios Node.js y Terraform.

Copia esta carpeta a `.local/agent`, completa `local.auto.tfvars` a partir de `local.auto.tfvars.example`, ejecuta `terraform -chdir=.local/agent init` y revisa el plan antes de aplicar. El estado de este stack opcional se conserva localmente dentro de `.local/agent`; no forma parte de los cinco estados principales. Conserva esa carpeta protegida para operar o retirar el agente.

Autoriza en `management_https_fqdns` los destinos HTTPS de Ubuntu, Docker, Microsoft, Node.js y las descargas de GitHub. El bootstrap instala Docker/Buildx, Node.js, Azure CLI, SWA CLI y Terraform. Se registra después mediante `python3 scripts/register_github_runner.py --directory .local/agent`, utilizando tus sesiones `gh` y `az`. El token de registro es temporal y se transmite como parámetro protegido de Azure Run Command; no se añade a tfvars ni al estado. GitHub administra sus credenciales operativas en el directorio privado del agente.

Configura `github_repository` y `github_environment` en el tfvars del entorno para crear el publicador OIDC opcional. La identidad de la VM sigue sin permisos Azure: el workflow usa la identidad federada del entorno. El repo debe ser privado y los workflows, controlados; protege el entorno Prod con revisión antes de habilitar su publicador.

La VM tiene coste mientras está asignada. El presupuesto alerta y no detiene el gasto. Después de la prueba puedes retirar este stack opcional con Terraform conservando antes la evidencia que necesites.

Para comprobarlo, copia `smoke-workflow.yml` a `.github/workflows/` de tu repositorio privado y ejecútalo manualmente. Ajusta `runs-on` a las etiquetas configuradas en `github_labels`; el ejemplo usa `goliat-nexus`. No necesita checkout, secretos ni permisos Azure.

Ejemplo de excepciones para añadir a `common.tfvars` antes de crear la VM:

```hcl
management_https_fqdns = [
  "archive.ubuntu.com",
  "security.ubuntu.com",
  "packages.microsoft.com",
  "download.docker.com",
  "nodejs.org",
  "objects.githubusercontent.com",
  "release-assets.githubusercontent.com",
  "aka.ms",
  "swalocaldeployv2-bndtgugjgqc3dhdx.b01.azurefd.net",
]
```

Las descargas generales de GitHub, Terraform, npm y Docker Hub ya están en las reglas de administración del producto. Si publicas portales, añade además los FQDN concretos de staging que asigne Static Web Apps; consulta `docs/VARIABLES_Y_TFVARS.md`. No añadas estas excepciones a la salida de las API.
