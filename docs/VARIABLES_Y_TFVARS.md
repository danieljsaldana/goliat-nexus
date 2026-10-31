# Guía de variables y tfvars

## Tres archivos, una plataforma

Edita las copias de `.local/environments/` que genera `./lz configure`. `common.tfvars`, `dev.tfvars` y `prod.tfvars` se leen juntos. Cada valor HCL tiene un comentario y separación en blanco. La demo usa `.local/demo/` y otro nombre.

El JSON nativo `examples/shared.auto.tfvars.json` representa la misma configuración que `examples/shared.json`. Son formatos compatibles sin comentarios: JSON no los admite. El usuario edita preferentemente HCL; el CLI genera las entradas `inputs.auto.tfvars.json` dentro de `.lz/` con contratos e imágenes reales. No edites esas entradas automáticas.

El ejemplo JSON contiene todas las opciones expuestas por el producto, incluidas entrada WAF, red, permisos, servicios opcionales, capacidad y mapa de portales. Los sufijos de nombres y los contratos entre capas se calculan; no son parámetros que el usuario deba rellenar. Esto no implica que todas las propiedades posibles de cada servicio Azure estén expuestas. El CLI combina los tres archivos HCL; `common.tfvars`, `dev.tfvars` y `prod.tfvars` no se autocargan por su nombre al ejecutar Terraform directamente. El `.auto.tfvars.json` se carga automáticamente solo en el directorio raíz Terraform donde se encuentre; no lo copies sin más a cada stack.

## common.tfvars

| Bloque | Qué controla |
|---|---|
| name, environment | Identidad estable de instalación; environment debe ser shared. Usa otro nombre para demo y para 0.4. |
| location, subscription_id, tenant_id | Región y destino real. configure obtiene IDs de az login. |
| operator_object_id | Object ID del operador o grupo con permiso de registrar secretos. El operador necesita administrar recursos, asignaciones de roles, políticas y presupuestos en los ámbitos utilizados; configura los permisos de plataforma con tu organización. |
| operator_ip_ranges, state_access | Bootstrap del backend restringido a IPs concretas, o modo privado desde el ejecutor conectado. |
| state_replication | LRS, ZRS o GRS para el backend; no cambia Cosmos. |
| network | VNet hub y subredes firewall /26, administración /27 y endpoints /27 o mayores. |
| log_retention_days | Retención compartida de logs, con efecto en coste. |
| management_https_fqdns | Excepciones adicionales para el ejecutor; no apertura general de salida. |
| operations | Presupuesto en la moneda de facturación, inicio de mes y emails reales. Alerta, no bloquea. |
| tags | Propiedad y atribución de costes comunes. |

## Flags de Dev y Prod

| Opción | Recurso o función | Dependencias |
|---|---|---|
| web_portals | Mapa de portales: un Static Web App por entrada. `{}` omite las webs. | Key Vault para token de publicación. |
| enable_api_platform | Catálogo de la aplicación. | Cosmos y Key Vault. |
| enable_api_tenant | Crear y leer solicitudes. | Cosmos y Key Vault; para entrega de eventos, enable_event_processing. |
| enable_api_activities | Leer actividades procesadas. | Cosmos y Key Vault. |
| enable_storage_account | Storage de host/paquetes y colas. | Identidad para los consumidores; sin Shared Key. |
| enable_content_storage | Storage independiente para contenido y lifecycle. | No implementa aún carga de adjuntos en la app. |
| enable_cosmosdb | Cuenta MongoDB 7.0, base, dos colecciones y endpoint privado. | Key Vault. Protegido contra destrucción. |
| enable_key_vault | Vault privado de aplicación y registro de secretos. | No se puede desactivar si otras piezas lo requieren. |
| enable_event_processing | Function de cola y timer, Insights y vault de host separado. | Cosmos, Storage y Key Vault. |
| enable_event_grid | Topic privado y publicación Entra del mismo evento. | API tenant y procesamiento de eventos. No crea suscripciones. |
| enable_dns | Registros DNS públicos opcionales. | Zona propia no vacía para producir efecto; DNS privado sigue activo. |

Los dos portales activados en dos entornos crean cuatro Static Web Apps. Revisa cuotas de la suscripción. Todos los servicios consumen cuotas y algunos tienen coste fijo. Para desplegar solo la plataforma base, sin la aplicación de ejemplo, desactiva webs, APIs, eventos, Cosmos y storage, y después Key Vault si ya no tiene dependientes. No desactives servicios con datos sin revisar su retirada; `prevent_destroy` bloqueará eliminar Cosmos.

## Ajustes por entorno

| Bloque | Referencia Dev | Referencia Prod |
|---|---|---|
| deploy_demo | false en producto, true en instalación demo | Etiqueta de evaluación; no activa componentes ni usa memoria. |
| zone_redundancy | false | true solo para Container Apps; Cosmos sigue en una región. |
| cosmosdb_config | MongoDB 7.0 Serverless; throughput/max_throughput null; Free Tier false. | Manual 400 RU/s; max_throughput null; Free Tier false. |
| backup | Periódico 240 minutos, 8 horas. | Periódico 240 minutos, 24 horas. No PITR. |
| storage | LRS; soft delete 14 días; Cool tras 30 días sin acceso a contenido. | Igual; el lifecycle no afecta al host ni a paquetes de Functions. |
| access | Requester consulta solo registros propios; Operator consulta el entorno. Listas de Object IDs Entra. | Asignaciones separadas; vacío en operadores usa operator_object_id, que debe ser usuario/grupo. |
| web | Standard, westeurope con WAF | Igual; Standard permite restringir el origen a la IP del WAF y no implica gratuidad. |
| functions | Node.js 24, 2048 MiB, máximo 40 instancias | Máximo es techo de escala, no instancias siempre encendidas. |
| network | 10.10/16; apps .0/23, datos .2.0/27, Functions .3.0/27 | 10.20 equivalente; no solapar subredes. |
| sample | Gateway 0–2; cada API 0–3; 0.25 vCPU, 0.5Gi | Gateway 2–3; cada API 2–5; mismos recursos por réplica. |
| github_repository/environment | Vacío desactiva publicador OIDC opcional | Usa un Environment distinto; no es una canalización completa de entrega. |
| additional_https_fqdns | Excepciones concretas del entorno | No usar comodines generales. |
| public_dns | zone_name vacío conserva los hostnames Azure; es la opción predeterminada. | Zona propia opcional. Registros DNS, vinculación del dominio y certificado son pasos distintos. |

## Dominio generado y dominio propio

La configuración predeterminada no requiere comprar un dominio. Conserva este bloque en Dev y Prod:

```hcl
public_dns = {
  # Vacío: utiliza los hostnames que devuelvan los servicios de Azure.
  zone_name = ""

  # No crear una zona pública para el nombre administrado por Azure.
  create_zone = false
}
```

En el modo WAF predeterminado, las URL de usuario apuntan al WAF; los nombres Static Web Apps son orígenes restringidos y el gateway de las APIs sigue siendo privado. `public_dns` se utiliza en el modo sin entrada WAF para crear CNAME de una zona propia; no vincula automáticamente el dominio al servicio ni emite su certificado. Si `create_zone = false` y se indica una zona, esta debe existir en el Resource Group del entorno. Crear una zona con `true` también exige delegarla desde el proveedor de tu dominio.

La entrada WAF utiliza por defecto el FQDN generado por Azure. El dominio propio es opcional y se configura con `public_entrypoint`; consulta [dominios y certificados](ENTRADA_PUBLICA.md).

Serverless no permite Free Tier ni throughput. Manual admite mínimos de 400 RU/s y múltiplos de 100; autoscale requiere máximo múltiplo de 1000 y throughput null. Free Tier está desactivado por defecto y solo admite una cuenta elegible por suscripción. Cambios de modalidad pueden necesitar migración o intervención fuera de Terraform: revisa el plan y la documentación de Azure.

Los puertos son internos: Nginx 8080, APIs 8000, HTTPS privado 443 y Cosmos MongoDB TLS 10255. La concurrencia HTTP es un objetivo de escala, no una promesa de rendimiento. No se guardan claves, tokens ni contraseñas en tfvars.

El ejemplo define dos entradas en `web_portals`: tenant y admin. Añadir más portales consiste en añadir claves al mapa, no en habilitar tipos de portal predefinidos. Todas las APIs de datos verifican identidad y roles; no existe un flag para desactivar la autenticación en Azure. El bootstrap del backend usa IPs restringidas: ciérralo con `state_access = "private"` desde la red privada antes de uso estable.

## Región de Cosmos

`cosmosdb_config.location = null` hereda la región principal. Puedes seleccionar otra región de Azure antes de crear la cuenta si la suscripción tiene restricciones de capacidad. Los Private Endpoints permanecen en la región de su VNet. Cambiar la región de una cuenta existente requiere un procedimiento de migración explícito; `prevent_destroy` protege frente a reemplazos automáticos.

## Publicación desde el ejecutor privado

Functions se empaqueta con sus dependencias en Linux mediante `npm ci --omit=dev`; no necesita descargar compiladores o paquetes desde su subred. El Firewall permite HTTPS a `cdn.functions.azure.com` únicamente desde las subredes Functions habilitadas, para las extensiones oficiales del runtime.

SWA CLI puede recibir un destino Blob temporal administrado por Azure para subir los portales. Autoriza su FQDN concreto en `management_https_fqdns`, además del destino oficial del binario de SWA CLI. Por ejemplo, en la validación de West Europe se utilizó `rgmssb1prodam2.blob.core.windows.net`; verifica el destino de tu instalación en los registros de denegación del Firewall. Estas excepciones afectan al ejecutor, sin ampliar la salida de las API. Evita un comodín para todos los Storage Accounts.

## Mapa de portales

Configura este bloque dentro de `dev` o `prod`, en su archivo tfvars. `tenant` y `admin` son las dos entradas del ejemplo; los nombres de las claves son libres y deben tener entre 1 y 30 caracteres en minúsculas, números y guiones entre palabras.

```hcl
web_portals = {
  tenant = {
    # Interfaz de solicitudes.
    view = "tenant"
  }

  admin = {
    # Interfaz de operaciones. El backend comprueba el rol Entra del usuario.
    view = "admin"
  }

  support = {
    # Ejemplo de otra entrada con nombre propio, que reutiliza la interfaz de solicitudes.
    view = "tenant"
  }
}
```

La entrada `support` ilustra cómo ampliar el mapa; no está incluida en el despliegue predeterminado. Omitir `view` selecciona tenant. Las dos interfaces pertenecen a la aplicación de referencia: una nueva entrada no implementa automáticamente otro proceso de negocio. Para usar un frontend distinto, adapta su código o su publicación manteniendo el contrato de identidad y API.

El módulo se instancia con `for_each` sobre el mapa. Cada clave conserva un recurso estable, su CNAME opcional, sus retornos de Entra y su secreto de publicación `deploy-web-<clave>`. El cliente Entra y el hub siguen compartidos dentro de su ámbito. La capacidad web común se configura en `web.sku` y `web.location`.

Usa `web_portals = {}` para desplegar sin portales. Quitar o renombrar una clave modifica la identidad Terraform del portal: revisa su plan de retirada. Para migrar desde los flags anteriores, conserva las claves tenant y admin si quieres mantener las cuatro webs del ejemplo ya desplegadas.

## Entrada compartida y dominios

`common.tfvars` incluye `public_entrypoint`, comentado: capacidad del WAF, hostname Azure por defecto, mapa opcional de dominios por entorno y certificado privado renovable. `web.sku` debe ser Standard para restringir cada origen a la IP del WAF. En modo WAF deja vacío `public_dns.zone_name`; para dominios propios usa `public_entrypoint.hostname` o `environment_hostnames` y configura su DNS. Consulta [la guía completa](ENTRADA_PUBLICA.md). La entrada añade el estado `edge` a los cuatro estados de base. Los portales siguen siendo un mapa extensible, sin flags por portal.
