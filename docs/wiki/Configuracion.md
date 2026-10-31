# Configuración y modularidad

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [English](https://github.com/danieljsaldana/goliat-nexus/wiki/Configuration)

`environments/common.tfvars`, `dev.tfvars` y `prod.tfvars` forman una instalación. El CLI los carga juntos. `examples/demo` es otra instalación de evaluación, no un tercer entorno conectado al mismo hub.

| Archivo | Contenido |
| --- | --- |
| common.tfvars | Identidad, región, red compartida, estado, entrada WAF y operación. |
| dev.tfvars | Componentes, acceso y capacidad de Dev. |
| prod.tfvars | Componentes, acceso y capacidad de Prod. |

Los HCL públicos están comentados y usan identificadores ficticios. `configure` genera copias privadas con permisos 0600 en `.local/`. El CLI deriva `inputs.auto.tfvars.json` en `.lz/`; esos contratos internos no se editan ni se publican y JSON no admite comentarios.

## Portales como mapa

Dentro de la configuración del entorno:

```hcl
web_portals = {
  tenant = { view = "tenant" }
  admin  = { view = "admin" }
}
```

Cada clave crea otra publicación Static Web Apps. `view` elige una de las dos interfaces de ejemplo; no concede roles Entra ni genera lógica de negocio. Para una interfaz diferente aporta su código. Más claves reutilizan las vistas existentes; `{}` no crea portales. Revisa cuotas y las dependencias de otros componentes.

## Capacidad de referencia

| Ajuste | Dev | Prod |
| --- | --- | --- |
| Réplicas por API | 0–3 | 2–5 |
| Cosmos MongoDB | Serverless | 400 RU/s compartidas |
| Retención de backup periódico | 8 h | 24 h |
| Container Apps zonal | No | Sí |

Estos valores no sustituyen pruebas de carga. Cosmos sigue en una región. Los flags `enable_*` tienen dependencias validadas; activar Event Grid no crea suscripciones ni sustituye el trigger Queue. `enable_content_storage` prepara almacenamiento, no una UI de adjuntos.

## Dominios

`public_entrypoint.hostname = ""` utiliza el FQDN real generado por Azure. Para producción configura hostnames distintos por entorno en `public_entrypoint.environment_hostnames` y revisa DNS, listeners, certificado, CORS y redirecciones Entra. El hostname único comparte origen de navegador entre Dev y Prod.
