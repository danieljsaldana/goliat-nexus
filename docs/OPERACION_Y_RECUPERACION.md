# Operación, aceptación y recuperación

## Instalaciones y configuración

Cada instalación utiliza su propia configuración, identidad, estados y credenciales. No reutilices los estados de una instalación eliminada como si sus recursos siguieran activos. Conserva backups y evidencias fuera del código público; los archivos locales reales y las credenciales permanecen fuera de Git.

El modelo actual añade el WAF compartido. Consulta [entrada pública](ENTRADA_PUBLICA.md) para dominio Azure, dominios propios, certificado y cinco estados. La publicación y administración se realizan desde la red privada; el uso de las aplicaciones se realiza por el WAF.

## Secuencia

1. Configura y revisa los tres tfvars en `.local/environments/`; usa identidades, IPs y correo reales.
2. Aplica foundation y platform. Conserva `.lz/` y el bootstrap local hasta acreditar la migración del estado.
3. Conecta el ejecutor a la subred de administración y al DNS del hub. Revisa resolución y TCP443 de ACR/vault/storage y TCP10255 de Cosmos. No abras los servicios para superar un error de red.
4. Aplica Dev. El CLI publica imágenes, registra secretos, aplica recursos y publica Functions y webs. Espera la propagación RBAC y comprueba los logs si el host no arranca.
5. Aplica Prod con su capacidad y datos independientes. Publica edge después de ambos workloads; espera el certificado público válido.
6. Abre los portales por el WAF, inicia sesión con Entra y crea una solicitud. Ejecuta smoke-test y verify-application para ambos entornos; revisa réplicas y denegaciones.

## Probar desde un Mac o PC

En el modelo predeterminado no necesitas VPN ni DNS privado en el Mac para utilizar los portales. Abre el origen HTTPS que devuelve `edge`, con `/dev/tenant/`, `/dev/admin/`, `/prod/tenant/` o `/prod/admin/`. Las entradas adicionales del mapa `web_portals` tienen su propia ruta.

1. Comprueba `https://<hostname-del-waf>/healthz` con validación TLS normal. HTTP redirige a HTTPS salvo el desafío ACME.
2. Abre el portal, inicia sesión con un usuario asignado y pulsa Actualizar.
3. Crea una solicitud y actualiza hasta verla PROCESADA y con su actividad. Requester ve sus registros; Operator opera el entorno.
4. Comprueba que las URLs originales de Static Web Apps devuelven 403 desde tu Mac y que APIs y datos no admiten conexiones directas de Internet.

Si el navegador muestra una advertencia de certificado o reputación, no la ignores: revisa el certificado, DNS y la clasificación del dominio con el servicio que la emite. HTTPS válido y reputación del sitio son comprobaciones diferentes. El flujo completo de navegador requiere que ambas sean correctas.

Con `public_entrypoint.enabled = false` se conserva la alternativa privada: el cliente que consume la API necesita conectividad y DNS privados aportados por la organización.

El portal distingue fallos de red, sesión/permisos y respuestas 400/503. Las lecturas toleran un arranque en frío con reintentos limitados; 401/403 no se reintentan. Un POST no se repite automáticamente: conserva el UUID mientras reintentas el mismo contenido. Una lista sin conexión no demuestra que la base esté vacía.

## Prueba real de las tres piezas

```sh
./lz verify-application --config .local/environments --environment dev
```

En modo WAF, desde el Mac con una sesión Azure CLI de usuario asignado, este comando crea una solicitud marcada como prueba, repite el mismo UUID para comprobar idempotencia y espera la actividad de la Function, tolerando el arranque en frío de las lecturas y hasta tres minutos de sondeo de eventos. El registro queda en Cosmos para inspección. No es una simulación: úsalo después de desplegar. Después abre el frontend Next.js desde un navegador y comprueba la misma solicitud y actividad. El comando valida el camino API→Cosmos→cola→Function; la apertura del portal completa la prueba del navegador.

## Aceptación en Azure

Comprueba rutas/NSG/firewall, denegación Dev→datos Prod y Prod→datos Dev, DNS privado y cierre de acceso público. Verifica que el gateway puede consultar sus APIs, que un origen no autorizado no obtiene CORS y que ninguna conexión Cosmos ni token de despliegue aparece en el navegador. CORS no es una barrera de autorización: valida los roles y permisos con usuarios reales antes de introducir datos reales.

Prueba creación de solicitud con un UUID fijo dos veces: debe existir una solicitud. Reproduce el evento dos veces: debe existir una actividad. Simula fallo de envío tras persistir y comprueba recuperación por timer. Envía un evento inválido en un entorno controlado: tras cinco intentos debe llegar a `requests-events-poison`. Corrige la causa y reproduce solo eventos validados; conserva los identificadores y no borres evidencia antes de comprobar el resultado.

Mide escala HTTP y latencia, RU/429, consumo y crecimiento de colas. Las réplicas del tfvars y los máximos Flex son límites, no resultados de una prueba de carga. Verifica cuotas de webs y disponibilidad regional antes del despliegue completo.

## Criterios de producción

Las pruebas automatizadas comprueban contratos, planes con proveedores simulados, autenticación, aislamiento lógico, eventos y controles de publicación. No acreditan por sí solas el funcionamiento ni la seguridad de una instalación Azure. Ejecuta las pipelines descritas en [CI/CD](CI_CD.md) y conserva la evidencia de aceptación de tu despliegue en un destino privado.

| Área | Comprobación antes de introducir datos reales |
|---|---|
| Navegador e identidad | Recorrido Entra/PKCE completo en ambos entornos; dos usuarios Requester con datos separados; Operator autorizado. MFA, Conditional Access y PIM definidos por la organización. |
| Entrada y red | HTTPS válido, WAF Prevention, orígenes directos bloqueados, rutas efectivas, DNS privado y denegación de acceso cruzado Dev–Prod. Backend de estado cerrado tras el bootstrap. |
| Origen de navegador | Hostnames distintos para Dev y Prod. El nombre Azure único del ejemplo comparte origen entre portales; ajusta DNS, certificados, CORS y retornos PKCE. |
| Recuperación | Restauración real de Cosmos y estados, rotación completa de claves y reproducción controlada de outbox y poison. Los hashes de un backup solo verifican integridad. |
| Capacidad y protección frente a abuso | Carga sostenida, latencia, escalado, cuotas, límites por usuario y auditoría de operaciones. Las réplicas de ejemplo no son un dimensionamiento validado. |
| Observabilidad y costes | Completar alertas de poison, antigüedad del outbox y RU/429. Medir costes y comprobar avisos: el presupuesto no detiene el gasto. |
| Confianza compartida | Revisar permisos sobre estado, ACR y workspace antes de delegar a otros equipos. El hub es una dependencia común de Dev y Prod. |
| Entrega y funcionalidades | Los contenedores usan digest; Functions y webs todavía se publican desde el checkout. Diseñar su promoción inmutable y, si se utilizan adjuntos, implementar validación, antivirus y acceso temporal. |

Container Apps de Prod es zonal; Cosmos mantiene una región y backup periódico, sin PITR ni failover multirregión. Las conexiones MongoDB de escritura tienen ámbito de cuenta, aunque se custodien en Key Vault. Revisa esos límites según los requisitos del proyecto y el [modelo de seguridad](SEGURIDAD.md). La plataforma no aporta una certificación de cumplimiento ni aplica políticas globales del tenant.

## Estado

```sh
./lz backup-state --config .local/environments
./lz recovery-check --backup '<RUTA_BACKUP>'
```

El backup contiene cinco estados sensibles cuando edge está habilitado (cuatro en modo privado), hashes, lineage y serial. recovery-check verifica integridad, no una restauración real. Guarda otra copia cifrada fuera del ejecutor. Ante estado perdido, compara lineage/serial y versiones remotas antes de restaurar. No sobrescribas un backend ocupado con un bootstrap antiguo: el CLI bloquea la copia automática a un destino con estado.

Para cerrar el backend, cambia state_access a private y aplica foundation desde la red privada; el CLI exige DNS y acceso de datos antes del cambio. El acceso al contenedor común puede permitir leer los cinco estados: asigna permisos conscientemente.

## Cosmos, código y secretos

Ensaya la restauración periódica de Cosmos hacia otra cuenta sin tocar la original. Registra tiempo real de recuperación y pérdida posible según intervalo y retención. Revisa el procedimiento vigente de Azure; el backup periódico no es PITR. No desactives `prevent_destroy` como solución a un plan inesperado.

Rota claves y tokens siguiendo [SECRETOS](SECRETOS.md). Si falla una publicación, conserva recursos y manifiestos, corrige la causa y repite `deploy --stage dev` o prod. `--reuse-images` reutiliza digests; Functions y webs se publican desde el checkout actual. No hay promoción inmutable completa de esos dos artefactos todavía.

Para migrar desde 0.3, crea otra instalación con nombre nuevo y planifica traslado de datos. La guardia de estado detecta la base antigua; no automatiza una conversión PostgreSQL→MongoDB.

## Acceso y denegaciones

Asigna usuarios/grupos mediante `access` y autentica el navegador con Entra. Comprueba 401 sin token; 401 con token expirado, alterado o de otro tenant/audiencia; 403 sin scope, cliente permitido o rol. Requester A no debe ver solicitudes ni actividades de Requester B; Operator autorizado puede consultar el entorno. Un token de Dev debe rechazarse en Prod. Verifica estas denegaciones a través del WAF y desde los componentes privados autorizados.

`smoke-test` y `verify-application` obtienen un token delegado desde la sesión Azure CLI y lo envían en el header. Ejecuta esas pruebas con un usuario asignado, no con una credencial app-only de CI. Los IDs públicos de aplicaciones y el scope aparecen en los outputs. Revisa MFA/Conditional Access, consentimiento, asignación de grupos y revocación de acceso conforme a las políticas de tu tenant.

## Publicación de Static Web Apps

La subida de artefactos utiliza destinos de Azure que pueden variar según el recurso. Ante un error TLS de StaticSitesClient, consulta los registros Deny del Firewall y añade únicamente el FQDN de subida confirmado a `management_https_fqdns`. No amplíes la salida de las APIs ni desactives TLS. El artefacto requiere `index.html` en la raíz y `staticwebapp.config.json` en el directorio indicado por `--swa-config-location`, aunque el contenido se sirva bajo una ruta.

## SPN de instalación y planes guardados

`./lz deploy --config .local/environments --yes` ejecuta las capas en orden desde un ejecutor Linux privado. Sin `--yes`, pide revisar y aprobar cada plan. Platform necesita outputs de foundation; los workloads necesitan platform y edge necesita los orígenes reales. Cada capa genera un único plan guardado y apply consume ese mismo archivo. Un fallo al planificar impide reutilizar un artefacto antiguo.

El modo predeterminado es `--identity installation`: **un SPN por instalación**, no uno por ejecución. El primer despliegue prepara los cinco grupos del producto, comprueba sus etiquetas de pertenencia, crea el registro de aplicación/SPN y concede permisos. Los grupos se adoptan en sus estados Terraform antes del plan. Los siguientes despliegues reutilizan los mismos IDs. Un fallo de despliegue conserva tanto los recursos como el SPN; un bootstrap de identidad incompleto se revierte para no dejar privilegios huérfanos.

El SPN recibe Contributor y RBAC condicionado a roles operativos en los cinco grupos, además de permisos de datos para estado, imágenes y publicación de secretos/certificados. Solo el rol de metadatos y presupuesto tiene ámbito de suscripción. No recibe permisos globales Graph. Terraform AzureAD conserva la sesión delegada del operador, que debe disponer de los permisos Azure y de directorio necesarios.

Cada ejecución genera una clave/certificado nuevo en un directorio privado. Su registro Entra caduca en un máximo de cuatro horas. AzureRM y el backend usan ese certificado; los comandos Azure CLI usan una caché aislada. Al terminar —también ante un error— se revoca **solo ese certificado** y se eliminan claves y caché. El SPN, su aplicación y sus asignaciones permanecen hasta el desmontaje. No se guardan valores de claves en tfvars, argumentos, diario ni estado Terraform.

El diario `.lz/identities/installation-<nombre>-<suffix>/run.json` conserva IDs, pertenencia y estado del ciclo. No lo borres entre ejecuciones. Si existe una identidad con ese nombre pero falta el diario, el CLI bloquea la creación de un duplicado: recupera la copia del diario y verifica sus IDs. No ejecutes la misma instalación simultáneamente desde varias máquinas.

Ctrl+C y SIGTERM intentan detener Terraform antes de revocar. SIGKILL o un apagado pueden impedir la limpieza. La siguiente ejecución recupera la credencial de un proceso local terminado; nunca elimina el SPN instalado como si fuese un resto efímero. Para recuperar solo la credencial de una ejecución interrumpida —o revertir un bootstrap de identidad que nunca llegó a completarse—:

```sh
./lz cleanup-identity \
  --run .lz/identities/installation-<nombre>-<suffix>/run.json \
  --credentials-only
```

## Retirada de la identidad al desmontar

El CLI no ejecuta una destrucción indiscriminada de grupos. Cosmos y el backend tienen prevent_destroy; el desmontaje de datos y estados requiere un procedimiento revisado, copias verificadas y ejecución desde una red que conserve acceso al backend hasta el final. No desactives esas protecciones para resolver un plan inesperado. Retira primero el agente y los opcionales, después edge y workloads, platform y finalmente foundation con su estado respaldado fuera de la cuenta que vas a eliminar.

**El paso final del desmontaje completo** elimina el SPN, su aplicación, las asignaciones registradas y el rol de metadatos. Necesita la sesión del operador, porque el SPN no tiene permisos para eliminar aplicaciones de Entra:

```sh
./lz cleanup-identity \
  --run .lz/identities/installation-<nombre>-<suffix>/run.json
```

El comando comprueba que los cinco grupos propios ya no existen. Si queda alguno, falla sin retirar la identidad. Si Azure falla durante la limpieza, conserva el diario y repite el mismo comando; verifica las asignaciones del principal. Eliminar recursos desde el Portal o ejecutar Terraform directamente no invoca este paso automáticamente. El SPN de despliegue no forma parte de los cinco estados Terraform y no debe desaparecer antes de terminar el desmontaje.

En CI con OIDC o identidad administrada ya preparada, usa `--identity existing`; el CLI no crea ni elimina la identidad del proveedor de CI. El modo optativo `--identity ephemeral` conserva el comportamiento avanzado de crear y retirar un SPN por ejecución, pero no es el modo predeterminado del producto.
