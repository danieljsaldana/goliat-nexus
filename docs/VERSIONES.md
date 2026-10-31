# Versiones verificadas · producto 1.0.0

La versión del producto es **1.0.0**. El rótulo de la web, los paquetes, ejemplos, documento e inventario deben coincidir. No es el número del ejecutable Terraform.

El archivo raíz `VERSION` es la fuente de la versión publicada por la web. El build lo lee para generar el rótulo de la cabecera y los metadatos; el catálogo de configuración también lo exporta para el navegador. No se repite en el footer ni se consulta la última release remota, porque podría corresponder a otro commit. Las pipelines comprueban la coherencia con los paquetes y ejemplos.

| Componente | Versión de esta entrega |
|---|---|
| Terraform recomendado y CI | 1.17.1 |
| AzureRM | 5.12.0, fijado y con lock de Darwin ARM64 y Linux AMD64 |
| AzureAD | 3.10.0, fijado y con lock de ambas plataformas |
| Node.js | 24.22.2; Functions usa runtime 24, compatible con Flex |
| Azure CLI | 2.91.0 |
| Agente GitHub Actions | 2.338.2, descarga oficial verificada con SHA-256 |
| Cosmos API MongoDB | 7.0 |
| Driver MongoDB | 7.8.0 |
| Next.js | 16.4.3 |
| React / React DOM | 19.3.1 |
| MSAL Browser | 5.27.0, con página de retorno dedicada |
| jose | 6.2.14 |
| SDK Azure | Versiones estables fijadas en los package-lock y en VERSIONES.json |

Consultado el 31 de octubre de 2026. Las imágenes Node y Nginx están fijadas por digest. [Detalle de paquetes](VERSIONES.json).

## Cambio respecto a las entregas previas

AzureRM 5 cambia campos de DNS privado, federación, tablas Storage y autenticación de Insights; el producto ya usa los campos actuales. Los ejemplos nuevos utilizan acmev1 y lzdemov1 para evitar reutilizar accidentalmente estados anteriores.

La API Cosmos se actualiza desde 4.2 a 7.0 junto con el driver. No apliques este código sobre una cuenta anterior sin un plan explícito de actualización/migración, compatibilidad y backup. Un driver reciente que ya no soporta MongoDB 4.2 no debe conectarse a esa cuenta antigua. El producto bloquea manifiestos de arquitectura anteriores y no convierte datos de PostgreSQL.

[AzureRM](https://registry.terraform.io/providers/hashicorp/azurerm/latest) · [AzureAD](https://registry.terraform.io/providers/hashicorp/azuread/latest) · [Cosmos MongoDB 7.0](https://learn.microsoft.com/en-us/azure/cosmos-db/mongodb/feature-support-70) · [Compatibilidad del driver](https://www.mongodb.com/docs/drivers/node/current/reference/upgrade/) · [Functions Flex](https://learn.microsoft.com/azure/azure-functions/flex-consumption-plan) · [MSAL redirect bridge](https://learn.microsoft.com/en-us/entra/msal/javascript/browser/redirect-bridge).
