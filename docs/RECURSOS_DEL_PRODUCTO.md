# Recursos que crea Goliat Nexus

La referencia 1.0.0 contiene **345 objetos Terraform administrados**: foundation 4, platform 279, Dev 28, Prod 28 y edge 6. El [inventario por tipo y capa](INVENTARIO_TERRAFORM.json) se extrae de planes con proveedores simulados. Incluye reglas, enlaces y permisos; no son 345 servicios facturables ni un inventario en tiempo real. Los flags y mapas cambian el resultado.

Consulta la [arquitectura hub & spokes](../site/diagrams/overview.json) para entender la relación entre el hub compartido y Dev/Prod, y la [red y seguridad](../site/diagrams/network.json) para consultar los endpoints y el tráfico. Sus vistas interactivas se generan con `make site`. El detalle completo de recursos se conserva en las tablas de esta guía y en el inventario por tipo y capa.

## Lo que se comparte y lo que se separa

El hub comparte WAF, Firewall, DNS privado, ACR Premium, logs y backend para optimizar costes. Dev y Prod tienen sus propias aplicaciones, identidades, datos y spokes. No hay peering directo Dev–Prod. Compartir servicios también comparte capacidad y posibles incidencias: hay que dimensionarlos y operarlos para ambos entornos.

| Ámbito | Recursos de la referencia y función |
|---|---|
| Organización | Cinco grupos propios: shared-state, connectivity, shared, dev y prod. Azure puede crear además grupos administrados de Container Apps. |
| Estado | Una cuenta Storage privada, contenedor tfstate y permiso del operador. Cinco estados: foundation, platform, dev, prod y edge. La plataforma añade un contenedor certificate-locks para coordinación ACME, con permisos separados del estado. |
| Red | Tres VNets, once subredes y cuatro peerings dirigidos hub↔spoke. Diez NSG, 59 recursos de reglas NSG independientes, nueve tablas de rutas y sus asociaciones. El gateway incorpora además reglas NSG en su propia definición. |
| Salida compartida | Azure Firewall Standard, IP pública de salida, política, colecciones y proxy DNS. Rutas específicas y reglas por origen/destino inspeccionan también el acceso de aplicaciones a endpoints de datos. |
| Entrada compartida | Application Gateway WAF_v2, IP pública, política WAF en Prevention y rutas HTTPS para los cuatro portales y las APIs. El hostname Azure se genera automáticamente; se puede configurar un dominio propio. |
| Certificados | Un vault TLS, dos identidades, un Container Apps Environment privado y un contenedor gestor de certificados ACME. Renueva el certificado y coordina las ejecuciones mediante un lease en certificate-locks. |
| Imágenes | Un ACR Premium privado, sin administrador local. Las APIs y el gateway se despliegan por digest. |
| DNS privado | Once zonas, 29 vínculos y seis registros A explícitos: ocho zonas de servicios y tres dominios de entornos Container Apps. Los grupos DNS de PE registran además sus nombres automáticamente. |
| Private Endpoints | Diecinueve en la base: tres compartidos y ocho por entorno. Event Grid añade uno por entorno si se activa. Las NIC de los PE las administra Azure. |
| Observabilidad | Un Log Analytics compartido, dos Application Insights, once diagnostic settings, nueve alertas de métricas y una de actividad/Resource Health. |
| Gobierno y coste | Un presupuesto de suscripción, Action Group y una definición de política con tres asignaciones. El presupuesto avisa: no limita ni apaga el consumo. |
| Por entorno, cómputo | Un Container Apps Environment interno, un Nginx privado y tres APIs Node.js: platform, tenant y activities. En total ocho Container Apps de negocio; el gestor de certificados es la novena. |
| Por entorno, datos | Una cuenta Cosmos DB API MongoDB 7.0, una base y dos colecciones: requests y activities. Endpoint privado y sin acceso público. |
| Por entorno, Storage | Una cuenta de runtime/colas/despliegue y otra de contenido. Dos colas —requests-events y poison— y contenedores de despliegue/contenido; reglas de ciclo de vida para el contenido. |
| Por entorno, secretos | Un vault de aplicación y otro para las claves del host Functions. Acceso privado y RBAC. El CLI registra los secretos en AKV sin introducir su valor en tfvars. |
| Por entorno, eventos | Una Function App Flex Consumption FC1 con plan, Insights, integración de salida y endpoint privado de entrada. Trigger de Storage Queue para actividades y timer para recuperar el outbox. |
| Por entorno, webs | Dos Azure Static Web Apps independientes, tenant y admin: cuatro en total. Plan Standard, orígenes públicos restringidos a la IP del WAF. Cada entrada del mapa web_portals genera su propio recurso. |
| Identidades de aplicación | Doce identidades administradas de usuario y 39 asignaciones Azure RBAC en la base. Dos registros Entra y dos service principals por entorno, con scopes, roles y asignaciones. No confundirlos con el SPN de despliegue. |

## Las cuatro aplicaciones web estáticas

Son recursos Azure reales, distintos de Container Apps. La muestra Next.js se exporta como contenido estático; cada portal recibe la configuración pública de su entorno y vista. No hay un servidor Next.js ni secretos Cosmos en el navegador.

| Entorno | Recurso —nombre configurable— | Ruta a través del WAF |
|---|---|---|
| Dev | `<nombre>-dev-tenant` | `/dev/tenant/` |
| Dev | `<nombre>-dev-admin` | `/dev/admin/` |
| Prod | `<nombre>-prod-tenant` | `/prod/tenant/` |
| Prod | `<nombre>-prod-admin` | `/prod/admin/` |

La ubicación del recurso SWA es **West Europe** en la referencia. Azure distribuye el contenido estático globalmente; esa ubicación no significa que la web esté dentro de la VNet. El origen SWA usa HTTPS público y allowedIpRanges limita el acceso a la IP del WAF; no se crea un Private Endpoint para esas webs. El acceso directo al origen de la instalación validada devuelve 403.

No hay cinco portales fijos ni flags saas/worker/guest. Añade entradas a `web_portals` para extender el mapa. Debes aportar las vistas, el código, la configuración y los permisos que necesite cada portal adicional.

## Máquina opcional para GitHub Actions

[examples/agent](../examples/README.md) utiliza el módulo virtual_machine y se despliega por separado de las cinco capas. Añade una VM Ubuntu y una NIC como recursos Terraform. Azure crea su disco administrado del sistema y su identidad administrada de sistema. No tiene IP pública. La VM comparte la subred de administración del hub y sale a GitHub por el Firewall.

El agente inicia conexiones HTTPS salientes para recoger trabajos; GitHub no necesita entrar en la VNet. El usuario configura la URL de su repositorio/organización, etiquetas, tamaño, disco y registro del runner. La identidad de la VM **no recibe permisos Azure automáticamente**. Para desplegar desde el workflow, configura OIDC y roles acotados; registra el agente con un token de corta duración que no se guarda en Terraform.

La VM de agente está habilitada en la instalación validada. La VM auxiliar utilizada para publicar y comprobar el producto es distinta, está deallocated y no forma parte de la referencia. Una VM deallocated sigue generando costes de disco.

## Opcionales y alcance del ejemplo

| Opción | Qué añade y qué hay que configurar |
|---|---|
| Event Grid | Un topic privado, un PE y el permiso Data Sender por entorno: tres objetos adicionales por entorno. No crea una suscripción ni cambia el trigger de cola de la Function. La validación lo habilita; los tfvars base lo dejan deshabilitado. |
| GitHub OIDC | Credencial federada e identidad de publicación según el ejemplo federation. Repositorio, rama/entorno y roles son responsabilidad de la instalación. No registra por sí solo una pipeline completa. |
| Dominio propio | Configuración de hostname, DNS y certificado conforme a la guía de entrada. Por defecto se usa el dominio Azure generado y un certificado público ACME; no se crea una zona DNS pública. |
| Mapas de portales y APIs | Permiten ampliar el ejemplo sin multiplicar flags por cada web. Requieren código, rutas, secretos/permisos y dimensionamiento adecuados. |

La aplicación Alba registra solicitudes y actividades. No concede realmente accesos, resuelve incidencias ni ejecuta tareas de negocio. Es el flujo funcional que puedes sustituir por tu aplicación.

## Cómo leer la red y la seguridad

| Tramo | Flujo y protección |
|---|---|
| Usuario → WAF | HTTPS público, certificado válido y WAF Prevention. Entra autentica al usuario; las APIs verifican token, scope, rol y propietario. El WAF no sustituye esas comprobaciones. |
| WAF → portales | HTTPS al origen SWA, restringido a la IP pública del WAF. |
| WAF → Nginx → APIs | HTTPS a la dirección privada del entorno ACA. Solo la subred del gateway puede entrar en Nginx; las APIs tienen ingress interno al entorno. |
| APIs / Functions → datos | Salida desde las subredes de integración, rutas y reglas específicas por Firewall hacia los PE de su entorno. Cosmos, Storage y vaults deshabilitan acceso público. |
| Function | La integración VNet permite la salida. El PE protege su entrada HTTP; el trigger de cola inicia conexiones hacia Storage, no recibe una llamada HTTP desde la cola. |
| Administración / CI | Agente privado opcional, salidas autorizadas y permisos explícitos. No se crea VPN ni entrada SSH pública. El WAF publica la aplicación, no el plano de administración Azure. |
| Certificados | Gestor ACME privado y vault TLS compartido. El vault TLS permite bypass AzureServices para Application Gateway; los vaults de aplicaciones usan None. HTTP 80 solo publica el reto ACME; el resto redirige a HTTPS. |

Un servicio PaaS con PE no se aloja dentro de una subred. La interfaz del endpoint sí está en la VNet; el servicio Azure continúa fuera. DNS privado resuelve su nombre a esa interfaz. Las zonas DNS son recursos globales de control, no servidores DNS en una subred.

Los CIDR de ejemplo son hub `10.0.0.0/16`, Dev `10.10.0.0/16` y Prod `10.20.0.0/16`. En cada spoke se separan apps, endpoints/datos e integración Functions. Los diagramas muestran los prefijos detallados; revisa solapamientos antes de conectar redes corporativas.

## Regiones y recuentos reales

La referencia usa West Europe. Cosmos permite override por entorno; en la instalación validada se utilizó **France Central** por disponibilidad de capacidad. No es una réplica ni un despliegue multirregión. Entra, DNS y RBAC son recursos de control globales y no están en las subredes dibujadas.

Los opcionales, el SPN de despliegue y los recursos auxiliares creados por Azure no están incluidos en los 345 objetos de referencia. El SPN de instalación y sus permisos los administra el CLI: se reutiliza hasta el desmontaje; su certificado se renueva y revoca por ejecución. Consulta su [ciclo y retirada final](OPERACION_Y_RECUPERACION.md).

Para los nombres y URLs actuales, usa `./lz output --config .local/environments` desde un ejecutor con acceso privado al backend. En el Portal filtra por los grupos del producto y por tipo Microsoft.Web/staticSites para localizar las cuatro webs. Los outputs no incluyen claves de cuenta ni tokens; el estado puede conservar datos sensibles y debe protegerse.
