# Seguridad y controles Zero Trust

El producto verifica identidad, limita permisos y separa entornos. La presencia en una red privada no concede acceso a los datos. Estos controles deben validarse en la suscripción y complementarse con las políticas de la organización; no constituyen una certificación de cumplimiento.

| Capa | Control implementado |
|---|---|
| Usuario | Microsoft Entra single-tenant; asignación obligatoria; roles Requester y Operator. |
| Frontend | Next.js estático, MSAL con PKCE, retorno dedicado, sin client secret ni conexión Cosmos; CSP con hashes. |
| API | Firma JWT RS256, issuer, audience, exp/iat/nbf, tenant, Object ID, cliente autorizado, scope y rol. Rechaza ID tokens y acceso anónimo a datos. |
| Datos del usuario | El backend deriva tenant/propietario del token. Requester consulta solo sus registros y actividades; Operator consulta el entorno. |
| Servicio | Identidades administradas independientes, AcrPull y permisos de cola/secretos con ámbitos concretos. |
| Secretos | AKV privado con RBAC, purgado protegido y vault de host Functions separado. Las APIs de lectura reciben conexión Cosmos read-only; tenant/Functions usan escritura. |
| Red | Spokes sin peering directo Dev–Prod; gateway privado, APIs internas, endpoints privados, NSG deny y salida mediante firewall con allowlists. |
| Transporte | HTTPS, TLS validado en Nginx y Mongo; sin desactivar verificación de certificados. |
| Eventos | Payload mínimo validado, tenant esperado, upsert por id, outbox y poison tras cinco entregas fallidas. |
| Estado | Backend con Entra, Shared Key desactivada, versiones, soft delete y cierre privado tras bootstrap. Planes y estados siguen siendo sensibles. |

## Qué configura Entra

Platform crea las aplicaciones API y SPA de cada entorno, sus service principals, scope delegado y asignaciones. Solo los Object IDs configurados —o el operador de common como inicial— obtienen acceso. Los clientes preautorizados son la SPA del entorno y Azure CLI para la prueba delegada. No se otorgan permisos Microsoft Graph a las aplicaciones de negocio.

Para aplicar esos recursos se necesitan permisos de directorio, distintos de Azure RBAC. Si el despliegue usa automatización, configura usuarios/grupos humanos en `access.operator_object_ids`. Consulta [los requisitos del proveedor AzureAD](https://registry.terraform.io/providers/hashicorp/azuread/latest/docs/resources/application) y la política de tu organización.

## Límites y cierre operativo

MFA, Conditional Access, PIM, licencias/asignación de grupos y políticas de revocación pertenecen al tenant y deben definirse con sus administradores. No se crean políticas globales de directorio desde este ejemplo. Los tokens se verifican en cada petición y están sujetos a su vigencia; no se implementa un sistema propio de revocación instantánea.

Cosmos usa la API MongoDB 7.0. Las conexiones de escritura siguen teniendo un ámbito de cuenta, aunque se custodien en AKV; no se presentan como RBAC de datos de Cosmos NoSQL. El ACR, workspace y contenedor de estado son ámbitos de confianza comunes: antes de delegar a equipos no confiables, revisa ABAC o separación adicional.

El bootstrap permite acceso al estado desde IPs concretas. Ciérralo con `state_access = "private"` desde el ejecutor privado y verifica el acceso. El producto no provisiona VPN ni runner automáticamente. Verifica accesos denegados, restauración, poison, rotación, alertas y costes siguiendo [operación](OPERACION_Y_RECUPERACION.md).

## Entrada pública protegida

El WAF compartido en el hub aplica OWASP 3.2 en Prevention. Webs Standard aceptan solo la IP del WAF; Nginx privado acepta solo su subred; las APIs tienen ingress interno. HTTPS valida cadena y SNI hasta cada origen. Functions y datos no se publican. El vault TLS mantiene acceso público deshabilitado y una excepción AzureServices necesaria para validar el certificado, con permiso de lectura limitado a ese secreto. Los vaults de aplicación mantienen bypass None. [Detalle de TLS y dominios](ENTRADA_PUBLICA.md).

## Qué tráfico atraviesa cada control

Con `public_entrypoint.enabled = true`, WAF y Azure Firewall cumplen funciones distintas. El WAF inspecciona las peticiones web públicas; Azure Firewall Standard controla la salida y los flujos privados que tienen una ruta explícita hacia él. La arquitectura no envía todos los paquetes por ambos servicios.

| Flujo | Recorrido y control |
|---|---|
| Navegador → portales o API | HTTPS → Application Gateway WAF → origen. Las llamadas de autenticación del navegador van directamente a Entra. |
| WAF → Static Web Apps | HTTPS al origen público Azure, restringido a la IP del WAF mediante la configuración publicada del portal. Static Web Apps no usa Private Endpoint en este producto. |
| WAF → Nginx privado | Red del hub y peering al spoke; NSG e ingress permiten la subred del WAF. Este salto no atraviesa Azure Firewall. |
| Gateway → APIs internas | Ingress interno del mismo entorno Container Apps; no atraviesa WAF ni Azure Firewall. El backend sigue validando JWT y permisos. |
| APIs/Functions → Cosmos, Storage y Key Vault | Private Endpoints, DNS privado y UDR específicas hacia Azure Firewall, con políticas de red activadas en las subredes de endpoints. NSG y reglas limitan el entorno, servicio y puerto. |
| Aplicaciones/ejecutor → Internet | Ruta 0.0.0.0/0 hacia Azure Firewall, con excepciones de plataforma y destinos autorizados. El tráfico interno de cada subred no queda incluido en esta afirmación. |
| Estado durante el bootstrap | `state_access = "restricted-public"` permite las IP del operador configuradas. Cambiar a `private` desde el ejecutor privado antes de operar de forma estable. |

Las UDR de datos son necesarias: una ruta por defecto no basta para interceptar Private Endpoints. Consulta [las políticas y rutas de Private Link](https://learn.microsoft.com/en-us/azure/private-link/disable-private-endpoint-network-policy). La configuración está en `modules/network/main.tf` y `modules/network/security.tf`; hay que confirmar rutas efectivas, DNS, logs y accesos denegados en la instalación real.

Azure Firewall Standard filtra protocolos, IP, puertos y FQDN y registra conexiones. No descifra el contenido TLS ni incluye el IDPS de Premium. El WAF sí inspecciona HTTP en su punto de terminación TLS; no sustituye la autorización del backend. [Capacidades por SKU](https://learn.microsoft.com/en-us/azure/firewall/features-by-sku).

La base es adecuada para evolucionar hacia una aplicación real con defensa por capas. No acredita por sí sola que una instalación sea segura: completar las pruebas de dos usuarios Requester, MFA/Conditional Access, restauración, rotación y carga sigue siendo necesario. El hub compartido reduce duplicación y también comparte un ámbito de confianza; separa sus recursos si Dev y Prod pertenecen a equipos que no deben confiar entre sí.

## Cola de trabajo y Event Hubs

Nexus es una plataforma completa; Event Hubs es un servicio de streaming que podría incorporarse a ella. El flujo de Alba usa Storage Queue → Function para procesar solicitudes, con outbox, reintentos, validación de eventos, operaciones idempotentes y cola poison. Aprovecha el Storage ya requerido por Functions y evita introducir otro broker para ese caso sencillo. No ofrece orden FIFO, transacciones distribuidas ni entrega exactamente una vez.

| Necesidad | Encaje |
|---|---|
| Procesar cada solicitud y actualizar su actividad | La cola y Function actuales. |
| Telemetría continua, particiones, varios consumidores independientes y relectura del stream | Event Hubs; requiere adaptar productor, consumidor, checkpoints, red y permisos. No está implementado mediante un flag. |
| Órdenes de negocio con sesiones FIFO, detección de duplicados del broker o transacciones | Evaluar Service Bus. No está implementado en esta versión. |
| Notificar hechos a integraciones | Event Grid opcional; el producto crea el topic y publica, pero el usuario debe diseñar y crear sus suscripciones. |

La elección del broker no sustituye WAF, identidad, red privada, secretos ni base de datos. No se afirma que el coste total de Nexus sea inferior a Event Hubs. [Tipos de mensajería](https://learn.microsoft.com/en-us/azure/architecture/guide/technology-choices/messaging) · [Colas Storage y Service Bus](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-azure-and-service-bus-queues-compared-contrasted).

## Identidad de despliegue

El CLI crea un SPN por instalación, con permisos acotados a sus grupos y un rol limitado de metadatos/presupuesto. Cada ejecución emite un certificado de hasta cuatro horas y usa una caché Azure CLI aislada. AzureRM y el backend usan ese certificado; AzureAD conserva la sesión del operador. El SPN no recibe permisos globales de Graph.

Al terminar se revocan el certificado y los archivos de autenticación; el SPN y RBAC permanecen. Tras desmontar toda la infraestructura se retiran el SPN, la aplicación y sus permisos con cleanup-identity. El comando lo bloquea mientras exista alguno de los cinco grupos. Las identidades de las aplicaciones tienen su propio ciclo en Terraform. Un diario permite recuperar una credencial interrumpida sin eliminar el SPN. [Procedimiento y cancelación](OPERACION_Y_RECUPERACION.md).
