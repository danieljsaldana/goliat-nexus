# Goliat - Nexus · Funcionamiento · versión 1.0.0

## 1. Qué despliega

Goliat - Nexus es una plataforma modular para construir aplicaciones en Azure. Integra red, identidades, secretos, datos y despliegue con un hub compartido por Dev y Prod. El repositorio incluye los módulos Terraform, la configuración y una aplicación de ejemplo para adaptarlos a tu proyecto.

La aplicación tiene tres piezas: **frontend Next.js con exportación estática**, **backend Node.js conectado mediante el driver MongoDB** y **Azure Functions Node.js 24**. Next.js no aloja lógica de negocio ni secretos. El ejemplo activa dos portales (usuario y operaciones) y tres APIs modulares de esas piezas, y Nginx actúa como gateway privado.

La aplicación suministrada se llama Alba: permite registrar solicitudes de acceso, mantenimiento o soporte, consultar su estado y ver la actividad del procesamiento asíncrono. Incluye inicio de sesión Microsoft Entra, validación de tokens en cada petición de datos y roles de aplicación. El tenant y el propietario de cada registro se derivan del token verificado, no del cuerpo que envía el navegador.

## 2. Hub compartido y costes

Foundation crea el backend para foundation, platform, dev, prod y la entrada pública edge. Platform crea el hub, Firewall Standard, ACR Premium, DNS privado, un workspace de logs y los recursos privados del servicio de certificados. Edge añade un WAF_v2 compartido y su emisor de certificados. Dev y Prod consumen esos servicios en vez de crear otra copia de cada uno. Esto reduce duplicación de costes fijos. No determina por sí solo el coste final: influyen región, ingestión, almacenamiento, tráfico, endpoints y capacidad reservada.

El hub usa 10.0.0.0/16; Dev, 10.10.0.0/16; Prod, 10.20.0.0/16. Cada spoke tiene subred de Container Apps /23, datos /27 y Functions /27. Functions no comparte su subred delegada con Container Apps. No existe peering directo Dev–Prod. Los destinos de datos permitidos por firewall y NSG pertenecen al propio entorno o al operador. Las zonas DNS privadas comunes permiten resolver servicios; resolver un nombre no concede acceso de red ni de datos.

Una modificación del hub puede afectar a ambos entornos. El registro, los logs y el contenedor de estados son ámbitos compartidos: las claves de estado no proporcionan por sí solas separación de permisos. Para equipos no confiables, contempla separación de suscripciones, registros, workspaces o ABAC antes de delegar publicaciones.

## 3. Aplicación de referencia

1. El navegador descarga un portal Next.js mediante el WAF compartido. El origen Static Web Apps Standard solo admite la IP del WAF; el usuario no necesita VPN para consultar las APIs.
2. Tras iniciar sesión con Entra, el frontend envía un token de acceso v2. La API verifica firma RS256, emisor, audiencia, caducidad, tenant, cliente, scope y rol; un ID token no sustituye al token de acceso.
3. El WAF enruta `/dev/api/*` o `/prod/api/*` hacia Nginx privado, con TLS validado. Nginx solo admite su subred y las tres APIs solo aceptan ingress interno del entorno.
4. La API tenant valida un UUID, un título y una categoría. Guarda una solicitud con una marca de outbox pendiente en un único documento MongoDB.
5. Publica un evento en `requests-events` mediante identidad administrada. Si falla el envío, el documento queda pendiente y la Function de temporizador lo reintenta cada minuto.
6. La Function de cola valida el evento y registra una actividad por identificador. Reprocesar el mismo evento no duplica la actividad. Después actualiza el estado de la solicitud.
7. Tras cinco entregas fallidas, el host mueve el mensaje a `requests-events-poison`. El operador investiga y reproduce un evento válido después de corregir la causa.

El outbox evita perder el trabajo por un fallo entre persistencia y envío; admite entregas repetidas. No es una transacción distribuida ni una garantía de exactly-once. Las escrituras de actividad y estado pueden completarse en intentos distintos. El consumidor permite reanudar de forma idempotente.

El mapa `web_portals` contiene por defecto los portales tenant (usuario) y admin (operaciones), que comparten código y se publican en recursos independientes. Sus claves son nombres libres: añadir una entrada crea otro portal. `view` selecciona la interfaz de ejemplo, tenant o admin. **El nombre de una vista no concede permisos:** el backend comprueba los roles del token. Requester crea y consulta solo sus registros; Operator puede consultar los registros del entorno. Los portales y APIs habilitados son configurables por entorno. El storage de contenido prepara un contenedor de adjuntos; el ejemplo aún no incorpora la carga y análisis de archivos. Event Grid es un publicador adicional opcional, sin suscripciones ni webhook privado configurados; la Function escucha Storage Queue.

## 4. Cosmos DB de la aplicación

El módulo Cosmos administra la cuenta y las bases de Cosmos DB API MongoDB 7.0, con endpoint privado y controles de TLS y red. Las colecciones son `requests` y `activities`, con shard key `tenant_id` e índices para identidad y listado por fecha. Se protegen cuenta, base y colecciones con `prevent_destroy`; las cuentas Storage del entorno también bloquean su destrucción accidental.

Dev usa Serverless y no Free Tier. Prod reserva 400 RU/s en la base, compartidas por sus dos colecciones. Ninguno de los valores es un dimensionamiento validado por carga. Cosmos está en una región, sin failover multirregión; la redundancia zonal de Container Apps no cambia esa decisión.

Los backups son periódicos cada 240 minutos; se conservan 8 horas en Dev y 24 en Prod. No equivalen a restauración continua/PITR. Para cambiar entre Serverless y provisionado se necesita otra cuenta y una migración. El cambio manual/autoscale requiere revisar el procedimiento de Azure; no lo trates como un ajuste inocuo de tfvars.

MongoDB usa una conexión con clave de cuenta. Las identidades administradas acceden a Key Vault para obtenerla; no se está aplicando RBAC de datos de Cosmos SQL. La clave permite acceso amplio a los datos de la cuenta del entorno. Una evolución sería adoptar una modalidad que soporte identidad de datos más granular, con migración explícita del modelo de datos.

## 5. Modularidad y valores de ejemplo

Los ajustes operativos están en `environments/common.tfvars`, `dev.tfvars` y `prod.tfvars`. Todos incluyen comentarios y espacio entre opciones. `common` define el hub y los servicios comunes; Dev y Prod definen flags, Cosmos, storage, webs, Functions, red y réplicas.

Las webs y las APIs requieren Key Vault. Las APIs y Functions requieren Cosmos; Functions también requiere Storage. Event Grid requiere la API tenant y el procesamiento de eventos. El CLI valida estas dependencias, los rangos IP y las combinaciones Serverless/RU/Free Tier antes de acceder a Azure. [Guía completa](VARIABLES_Y_TFVARS.md).

`public_entrypoint` configura la entrada WAF y utiliza por defecto el FQDN generado por Azure. Admite dominio propio y hostnames diferentes por entorno. `web_portals` amplía las rutas sin añadir flags. `public_dns` queda reservado al modo de publicación anterior; el DNS privado necesario permanece activo. Consulta la [entrada pública, dominios y certificados](ENTRADA_PUBLICA.md).

## 6. Secretos

El certificado público y la clave ACME se mantienen en un vault TLS compartido. La identidad del WAF solo puede leer su certificado; el emisor privado no puede leer el contenedor de estados. Consulta el [modelo de emisión y renovación](ENTRADA_PUBLICA.md).

`secrets-sync` obtiene la conexión MongoDB y los tokens de publicación de las webs desde Azure, valida el host previsto y registra los valores en Key Vault usando stdin, sin ficheros persistentes ni valores en argumentos. No crea otra versión si el contenido no cambia. Se ejecuta antes del workload y puede repetirse manualmente.

Cada API tiene identidad propia y lectura limitada a su secreto Cosmos. La API tenant y Functions usan una conexión de escritura; las APIs de catálogo y actividades reciben una conexión de solo lectura. El gateway solo tiene AcrPull. La Function lee el mismo secreto y utiliza identidad para Storage. Las claves de host de Functions residen en otro vault por entorno para evitar colisiones entre hosts. Los tokens de despliegue web no se publican al navegador.

El proveedor Terraform puede guardar claves calculadas de Cosmos o Static Web Apps en el estado, aunque no se exporten como outputs. El estado, planes y backups son sensibles; deben tener acceso limitado, cifrado y política de retención. [Gestión y rotación](SECRETOS.md).

El frontend se compila con `npm ci` y `npm run build`; `output: "export"` genera `apps/portal/out/` sin servidor Next.js. El backend y Functions usan Node.js 24 y el driver MongoDB 7.8.0 contra Cosmos API MongoDB 7.0. Los SDK Azure, Next.js y React se mantienen en sus versiones estables verificadas. Una cuenta anterior con API 4.2 necesita una migración o actualización explícita antes de utilizar este driver. No se cambia el protocolo de una instalación existente automáticamente.

## 7. Identidad y permisos

Platform registra una API y un cliente SPA single-tenant por entorno. Las dos webs comparten ese cliente y sus URI de retorno explícitas. Se exige asignación de usuarios tanto al cliente como a la API; el scope es `access_as_user` y los roles son `Requester` y `Operator`. Los grupos/usuarios se configuran en `access`. No se guardan contraseñas OAuth: MSAL usa PKCE y una página de retorno dedicada.

Si `access.operator_object_ids` está vacío, se asigna el usuario/grupo indicado por `operator_object_id`. Si despliegas mediante un service principal, indica usuarios o grupos humanos en esa lista: un principal de automatización no obtiene acceso delegado como usuario. El operador de despliegue necesita permisos de directorio para aplicaciones, service principals, preautorizaciones y asignaciones. No basta con Contributor de la suscripción. Consulta los requisitos del proveedor AzureAD antes de aplicar.

La API acepta solo tokens del tenant y audiencia de su entorno, emitidos para su SPA o para Azure CLI preautorizado. Un token de Dev no autoriza Prod. Cada consulta incorpora el tenant verificado y, salvo Operator, el Object ID del propietario. El evento de cola también se valida contra el tenant configurado; la Function usa identidad administrada para los servicios.

## 8. Despliegue

```sh
az login
./lz configure --name miplatforma --operator-ip '<IP>/32' --alert-email '<CORREO>' --output-dir .local/environments
./lz check --config .local/environments
./lz deploy --config .local/environments --stage foundation
./lz deploy --config .local/environments --stage platform
# Desde el ejecutor privado con Docker/Buildx Linux y SWA CLI 2.1.0
./lz deploy --config .local/environments --stage dev
./lz deploy --config .local/environments --stage prod
./lz deploy --config .local/environments --stage edge --yes
./lz verify-application --config .local/environments --environment dev
```

Foundation arranca con estado local, comprueba que el destino esté vacío y migra al backend. Conserva `.lz/` para reanudar. El bootstrap público restringido solo permite las IP indicadas. Para cerrar el estado, configura `state_access = "private"` y aplica foundation desde un ejecutor privado: el CLI comprueba DNS, conexión y acceso a datos antes del cierre.

Platform crea recursos de administración y endpoints privados. Conecta un ejecutor existente a la subred de administración y al DNS del hub o despliega la VM/agente opcional de `examples/agent`. El agente se configura y registra por separado; no recibe roles Azure por defecto. El acceso público de usuarios pasa por el WAF; la administración sigue necesitando un ejecutor privado. Las imágenes se construyen y publican en ACR con digest inmutable. El CLI sincroniza los secretos, aplica Dev/Prod espera las nuevas revisiones, instala las dependencias de Functions en Linux con `npm ci --omit=dev` y publica su ZIP listo para ejecutar. Publica cada portal con SWA CLI, usando su token de Key Vault en el entorno del proceso.

Si falla la publicación de código después de Terraform, los recursos permanecen creados. Corrige conectividad/cuotas/RBAC y repite el despliegue del entorno. `--reuse-images` evita reconstruir imágenes; Functions y webs se vuelven a publicar desde el código local. [Runbook](OPERACION_Y_RECUPERACION.md).

## 9. Demo y producto

`examples/demo/` es otra instalación para aprender desplegando y viendo el producto. Usa un nombre distinto, sus propios recursos y costes; su Dev y Prod comparten su propio hub. `deploy_demo` solo etiqueta los portales como evaluación. La aplicación desplegada sigue usando Cosmos, no una base en memoria.

El modo en memoria requiere `USE_IN_MEMORY=true` y solo se usa en pruebas locales explícitas. Un fallo de Cosmos en Azure produce indisponibilidad y no activa un fallback volátil.

Después del despliegue, `./lz verify-application --config .local/environments --environment dev` crea una solicitud de prueba y confirma su actividad asíncrona real. Abre después la URL pública del portal, protegida por WAF, desde tu navegador. Completa las pruebas de ambos entornos y conserva sus resultados siguiendo los [criterios de producción](OPERACION_Y_RECUPERACION.md).

## 10. Operación y requisitos de producción

Incluye logs comunes, diagnósticos de plataforma, Application Insights para Functions, avisos HTTP 5xx, salud del firewall y Resource Health, además de un presupuesto común. Los presupuestos no detienen el gasto. Completa alertas de cola poison, antigüedad del outbox y RU/429 después de medir la carga; no se presentan como implementadas.

Antes de producción: validar roles y consentimiento de Entra con cuentas reales, aplicar MFA/Conditional Access de la organización, CORS con dominios definitivos, separación de orígenes Dev/Prod, protección frente a abuso, cuotas, pruebas de escalado, denegación Dev–Prod, rotación de claves, reproducción de poison y restauración de Cosmos y estados. La base aplica controles Zero Trust de red, identidad y autorización; no configura políticas de MFA, Conditional Access o PIM del directorio. Esas políticas se definen con la organización y no se modifican globalmente desde este producto.

No hay migración automática desde 0.3/PostgreSQL. Usa un nombre nuevo y un plan separado para los datos. [Límites y criterios de producción](OPERACION_Y_RECUPERACION.md).

## Referencias técnicas

[Exportación estática de Next.js](https://nextjs.org/docs/app/guides/static-exports) · [Compatibilidad de drivers MongoDB](https://www.mongodb.com/docs/drivers/compatibility/) · [Versiones del driver Node](https://www.mongodb.com/docs/drivers/node/current/reference/release-notes/) · [Lenguajes de Functions](https://learn.microsoft.com/azure/azure-functions/supported-languages) · [Despliegue Flex](https://learn.microsoft.com/azure/azure-functions/flex-consumption-how-to).

[Versiones verificadas y migración](VERSIONES.md) · [Modelo de seguridad](SEGURIDAD.md).

## Ciclo del despliegue

La ejecución completa se lanza desde el ejecutor privado con `./lz deploy --config .local/environments --yes`. Crea o reutiliza el SPN de la instalación, planifica y aplica cada capa en orden y publica las aplicaciones. Revoca el certificado de esa ejecución y conserva el SPN y sus permisos hasta el desmontaje completo. Cada `apply` consume el plan guardado de su capa; los outputs necesarios determinan el orden de los cinco planes. Las identidades de negocio son permanentes y los registros de directorio se gestionan con la sesión del operador. [Detalles y recuperación](OPERACION_Y_RECUPERACION.md).
