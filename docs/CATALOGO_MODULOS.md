# Catálogo de módulos

Los cuatro estados de base son `foundation`, `platform`, `dev` y `prod`; `edge` añade WAF y el servicio privado de certificados. Un estado no equivale a un módulo: cada capa compone módulos reutilizables. Los módulos de Nexus están incluidos en el repositorio para configurarlos, combinarlos y ampliarlos según el proyecto.

| Módulo | Qué crea | Entradas principales | Salidas |
| --- | --- | --- | --- |
| `container_app_environment` | Entorno Container Apps interno, zona DNS, registros y enlaces a redes | Nombre, región, grupo, subred existente, workspace, redes y redundancia zonal | `id`, `default_domain`, `static_ip_address`, `security` |
| `container_apps` | Gateway Nginx, API Node por función habilitada, permisos sobre secretos/cola y alertas | Contrato de plataforma, entorno y dominio, `features`, capacidad e imágenes por digest | `demo_url`, `api_url`, `applications`, `security` |
| `budget` | Presupuesto mensual filtrado a los grupos del producto, avisos de gasto real al 80/100 % y previsión al 100 % | Suscripción, importe, fecha inicial explícita, correos y grupos | `id`, `name`, `amount`, `notification_count` |
| `virtual_machine` | NIC privada y VM Linux, SSH por clave, Secure Boot, vTPM e identidad administrada | Subred existente, clave pública, tamaño y script de instalación | `id`, `name`, `private_ip`, `principal_id`, `security` |
| `workload` | Composición de los dos módulos de Container Apps | Mantiene el contrato de la capa Dev/Prod | Conserva las salidas de aplicaciones y entorno |
| `azure/static_web_apps` | Un Static Web App por clave del mapa `web_portals`, mediante `for_each` | Nombre del portal, grupo, región y SKU comunes al entorno | Identificador y hostname; la plataforma añade `view` al contrato |
| `azure/event_grid` | Topic Event Grid y permiso de publicación; la composición añade su endpoint privado cuando se habilita | Identidad, nombre, red y autenticación local deshabilitada | Identificadores y endpoint usados por la plataforma |
| `event_processing` | Plan Flex Consumption, Function Node, Application Insights, endpoint privado y permisos | Subredes, almacenamiento, identidad y vaults del entorno | `integration`, `security` |

`container_apps` usa imágenes y configuración de la aplicación de referencia Alba. Puede consumirse por separado del entorno, pero adaptar otras aplicaciones requiere ampliar su contrato de contenedores. No es todavía un catálogo genérico de cualquier imagen o tipo de cómputo.

El gateway puede recibir tráfico desde redes conectadas al entorno privado. Las API usan ingress interno. `external_enabled = true` en el gateway significa accesible desde fuera del entorno Container Apps dentro de la red conectada; el entorno mantiene el acceso público deshabilitado. Los portales Next.js se sirven mediante Static Web Apps de la capa `platform`.

## Agente opcional de GitHub Actions

`examples/agent` compone `virtual_machine` sobre la subred de administración ya existente. Es un stack opcional independiente, separado de los cinco estados del producto. No se crea en cada despliegue Dev/Prod ni recibe permisos Azure por defecto.

El usuario configura su repositorio privado y sus etiquetas en `local.auto.tfvars`, siguiendo el ejemplo comentado `local.auto.tfvars.example`. El script de registro usa las sesiones locales `gh` y `az`, genera un token de registro temporal y lo transmite como parámetro protegido de Run Command. No requiere guardar un PAT en tfvars, estado o bootstrap.

El ejemplo incluye `smoke-workflow.yml`: un workflow manual que comprueba las herramientas sin leer código ni secretos del repositorio. Las publicaciones Azure necesitan OIDC y permisos por entorno configurados expresamente. Un agente persistente ejecuta código de los workflows autorizados: restringe quién puede modificarlos y usa repositorios privados de confianza.

## Actualización y costes

Los módulos base de Cosmos, Storage, webs, DNS y Event Grid se agrupan en `modules/azure`. El módulo interno de Cosmos se llama `account`; su bloque `moved` conserva las cuentas y bases de las instalaciones que utilizaban la dirección anterior.

Los bloques `moved` trasladan las direcciones antiguas de Container Apps y presupuesto a los módulos nuevos. Revisa el plan de una instalación existente: la extracción por sí sola no debería destruir recursos.

El presupuesto solo alerta; no apaga recursos ni limita la factura. La VM se factura mientras está asignada y conserva costes de disco al desasignarla. Container Apps, Functions, datos y red tienen sus propios cargos. Event Grid sigue siendo opcional mediante `enable_event_grid`; el flujo base usa Storage Queue y un temporizador de recuperación.

`modules/application_gateway` configura la entrada WAF_v2 compartida: OWASP Prevention, HTTPS validado hacia orígenes, rutas por entorno/portal, desafío ACME y diagnóstico. `stacks/edge` lo compone con el gestor privado de certificados. [Funcionamiento y parámetros](ENTRADA_PUBLICA.md).
