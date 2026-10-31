# Pipelines y revisión antes de publicar

[English](CI_CD.en.md)

Las pipelines validan el código, las dependencias y la web. Los comandos de revisión local no publican código, despliegan Azure ni sincronizan la wiki; las publicaciones se ejecutan mediante workflows manuales.

## Pipelines incluidas

| Archivo | Activación | Resultado |
| --- | --- | --- |
| `.github/workflows/validate.yml` | PR, push a main, manual y reutilizable | Gitleaks, actionlint/ShellCheck, tests Python/Node, build Next.js, auditorías npm, Terraform con proveedores simulados, inventario, wiki, imágenes y web. |
| `.github/workflows/security.yml` | PR, main, semanal y manual | CodeQL para Actions, Python y JavaScript/TypeScript; revisión de nuevas dependencias en PR. |
| `.github/dependabot.yml` | Semanal | Propuestas de actualización para Actions, cinco paquetes npm y proveedores Terraform. |
| `.github/workflows/release.yml` | Manual, solo main | Repite CI y prepara una release **en borrador**, con hashes de las fuentes y procedencia del commit, sin ZIP. |
| `.github/workflows/pages.yml` | Manual, solo main | Genera, audita y publica `dist/` en GitHub Pages. |

Las acciones están fijadas a SHA completos verificados en sus repositorios oficiales. Dependabot mantiene propuestas de actualización; revísalas antes de fusionar. Los binarios Gitleaks/actionlint tienen versiones y SHA-256 fijados en `scripts/security-tools.json`. No se descarga ni ejecuta una versión `latest` durante las comprobaciones.

## Permisos y ejecución

CI usa runners hospedados por GitHub y `contents: read`. El checkout no conserva credenciales. Los jobs tienen límites de tiempo y el estado final `CI passed` exige que todos terminen correctamente, incluidas las matrices. Ninguna PR ejecuta código en el agente privado Azure.

Solo CodeQL escribe resultados de seguridad. Solo el job que crea el borrador tiene `contents: write`. Pages limita `pages: write` e `id-token: write` al job de publicación. No se usa `pull_request_target`, sesiones Azure, SPN, PAT ni secretos cloud en CI.

El repositorio principal protege `main` mediante PR, `CI passed`, los tres análisis CodeQL, la revisión de dependencias y conversaciones resueltas. Las ejecuciones externas requieren aprobación del mantenedor. Consulta [Cómo contribuir](../CONTRIBUTING.es.md). En un fork, el propietario debe configurar estos ajustes: los YAML no los aplican automáticamente. Configura también los entornos `release` y `github-pages` según tu equipo y selecciona GitHub Actions en Settings → Pages.

## Frontera de publicación

- Se revisan fuentes no ignoradas y todas las referencias del historial Git.
- `--strict-tracked` rechaza archivos versionados fuera de la lista permitida; se usa en CI y en el checkout público preparado.
- Los tfvars públicos deben conservar sus IDs Azure ficticios. Los reales se generan en `.local/` y no entran en Git ni en los artefactos publicados.
- Antes de subir un artefacto se inspeccionan nombres y enlaces, y se escanea su contenido con Gitleaks. Se rechazan todos los ZIP y demás archivos comprimidos, claves, estados, planes, `.env` y cachés. El código y los tfvars se mantienen como archivos normales en Git.
- Solo se conserva el artefacto estático auditado de main, durante siete días. No se suben `.lz/`, planes, estados, tokens, diarios ni logs de despliegue.

## Comprobar en local

```sh
python3 scripts/install_gitleaks.py
python3 scripts/install_actionlint.py
make workflows-check
make fmt check test validate
make inventory docs wiki-check
make site site-check artifacts-check
```

Las pruebas Terraform usan `mock_provider`; no hacen planes contra la suscripción ni requieren iniciar sesión. Los proveedores se descargan del registro y las auditorías npm consultan avisos públicos. `make images-check` necesita Docker con motor Linux: la pipeline lo ejecuta en Ubuntu.

Para preparar las fuentes públicas, ejecuta `make prepare-github`. Crea `.local/github-ready/goliat-nexus/` con historial nuevo, remoto y hook pre-push, sin commit ni push. Si el destino existe, usa `python3 scripts/prepare_github.py --output <OTRA-CARPETA>`; no sobrescribe una revisión anterior. Dentro de la copia instala el scanner con `python3 scripts/install_gitleaks.py` y ejecuta `python3 scripts/check_publication.py --history --strict-tracked`. Los hooks no sustituyen la revisión ni los controles de GitHub.

## Release y despliegue

La versión manual debe coincidir con `VERSION`. La pipeline repite CI, escanea el checkout completo y exige fuentes sin cambios locales. Genera SOURCE_SHA256SUMS por archivo, procedencia del commit y notas, y crea un borrador sin empaquetar el código ni los tfvars. No reemplaza una release existente. El propietario revisa notas, hashes y evidencias antes de publicarlo.

Publicar la web en Pages es una acción manual distinta. No crea recursos Azure ni despliega Alba.

El despliegue Azure conserva el CLI y el ejecutor privado. No se añade un despliegue automático desde PR. El publicador OIDC opcional actual tiene permisos limitados de imágenes, grupo e identidad; por sí solo no aporta todos los permisos de estado, secretos, asignaciones RBAC y directorio necesarios para ejecutar la plataforma completa en CI. Preparar CD Azure requiere revisar esos ámbitos, la conectividad/DNS privados y las aprobaciones de cada entorno. No reutilices credenciales personales ni introduzcas tfvars reales en GitHub.

Los logs y artefactos de Actions serán públicos al ejecutarse en este repositorio público. Los comandos incluidos evitan imprimir secretos y solo utilizan valores ficticios en validación. Un escaneo automático no garantiza ausencia total de datos sensibles.
