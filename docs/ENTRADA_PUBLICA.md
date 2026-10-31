# Entrada pública, dominios y certificados

## Recorrido del tráfico

El modo predeterminado utiliza un Application Gateway WAF_v2 compartido en el hub. El navegador entra por HTTPS al WAF para descargar los portales y consultar las APIs. Los orígenes Static Web Apps Standard solo admiten la IP pública del gateway; el gateway Nginx de Container Apps acepta únicamente la subred del WAF. Las tres APIs tienen ingress interno y siguen validando los tokens y permisos de Entra.

Cosmos, Storage, Event Grid, Key Vault y Functions permanecen privados. API → Cosmos/cola → Function son comunicaciones internas: no recorren el WAF. La administración y la publicación se realizan desde un ejecutor privado mediante Azure; el producto no instala VPN, SSH público ni Front Door Premium.

## Nombre generado por Azure

Con `hostname = ""`, el producto toma el FQDN real de la IP pública que devuelve Azure. No se compra un dominio y no se construye el nombre a mano en el frontend. Las rutas son `/dev/tenant/`, `/dev/admin/`, `/prod/tenant/` y `/prod/admin/`; cada entrada adicional de `web_portals` obtiene su propia ruta.

En `common.tfvars`:

```hcl
public_entrypoint = {
  # Activa la entrada compartida y exige SWA Standard para cerrar los orígenes.
  enabled = true

  # Vacío utiliza el nombre de Azure. Un dominio propio debe resolver al WAF.
  hostname = ""

  # Opcional: hostnames distintos por entorno para separar orígenes del navegador.
  environment_hostnames = {}

  # Capacidad del gateway; son recursos facturables incluso sin tráfico.
  minimum_instances = 1
  maximum_instances = 2

  # Vacío emite y renueva mediante ACME. Nunca introducir un PFX en los tfvars.
  certificate_secret_id = ""

  # El directorio staging sirve para ensayos; sus certificados no son de confianza.
  acme_directory_url = "https://acme-v02.api.letsencrypt.org/directory"
}
```

El hostname Azure único comparte origen de navegador entre los portales de la referencia. Para proyectos reales con separación de equipos y versiones Dev/Prod, configura hostnames diferentes mediante `environment_hostnames`. El WAF bloqueará las rutas de cada entorno cuando se soliciten con otro hostname. Los tokens y los datos también permanecen separados por entorno.

## Dominio propio

Configura `hostname` para un nombre común, o `environment_hostnames.dev` y `.prod` para separar los entornos. Crea los registros DNS hacia el FQDN de la IP del WAF antes de emitir el certificado. Puedes gestionar ese DNS en Azure o con tu proveedor actual. Mantén `public_dns.zone_name` vacío en modo WAF: ese bloque por entorno pertenece al modelo anterior de publicación directa.

El despliegue propaga las URLs a las aplicaciones y a las redirecciones de Entra. Revisa listener, certificado, CORS e inicio de sesión antes de retirar las direcciones anteriores. Si aportas un certificado existente, `certificate_secret_id` debe ser una URI de secreto Key Vault sin versión y la identidad del gateway debe tener permiso de lectura sobre él y acceso de red al vault.

## Emisión y renovación

Un Container App privado compartido mantiene el certificado. Usa HTTP-01: el puerto 80 solo sirve el desafío `/.well-known/acme-challenge/*`; las demás rutas redirigen a HTTPS. Antes de solicitar un certificado comprueba la ruta real por el WAF, para evitar órdenes fallidas durante el arranque.

La clave de la cuenta ACME y el certificado se almacenan en Key Vault. El emisor tiene permisos sobre esos dos objetos y utiliza un lease en un contenedor Blob independiente para impedir renovaciones simultáneas. No puede leer el contenedor de estados. La clave privada temporal se elimina tras importar el PFX; no se pasa por Terraform, tfvars ni argumentos. Se renueva antes de la caducidad y el WAF usa la referencia sin versión para recoger las nuevas versiones.

El bootstrap crea un certificado temporal dentro de Key Vault para poder provisionar el gateway. El despliegue no declara HTTPS listo hasta comprobar un certificado público de confianza. Tras la primera emisión fuerza la actualización del gateway; las siguientes rotaciones las recoge su integración con Key Vault.

El vault TLS conserva `publicNetworkAccess = Disabled`, Private Endpoint y RBAC. La integración exige la excepción `AzureServices` para que el servicio de Application Gateway valide el secreto; su identidad solo tiene lectura sobre `waf-tls`. Los vaults de aplicación conservan `bypass = None`. Esta excepción de plataforma no concede acceso anónimo ni publica los secretos de la aplicación. Consulta la [integración oficial de Key Vault](https://learn.microsoft.com/en-us/azure/application-gateway/key-vault-certs).

## Estados y ejecución

Se mantienen los cuatro estados de base y se añade `edge` para WAF y el servicio de certificados. `./lz deploy --stage edge --yes` prepara la imagen por digest, crea el bootstrap privado, revisa el plan, aplica el WAF y espera HTTPS válido. Necesita un ejecutor privado con Docker, Azure CLI y permisos de despliegue. También puede separarse la preparación privada de la aplicación de Terraform para operar por fases.

Una publicación de Static Web Apps incluye un documento raíz obligatorio, además del contenido bajo su ruta, y selecciona expresamente su configuración de red. El CSP utiliza hashes de los scripts estáticos; la página de retorno de MSAL permite el iframe del propio origen para completar la autenticación.
