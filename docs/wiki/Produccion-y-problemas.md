# Preparar producción y resolver problemas

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [English](https://github.com/danieljsaldana/goliat-nexus/wiki/Production-and-troubleshooting)

Alba demuestra el flujo técnico. Antes de usar esta base en un proyecto real, adapta la aplicación y completa aceptación, seguridad corporativa, operación y capacidad.

## Comprobaciones de producción

- Hostnames separados para Dev/Prod y validación de DNS, TLS, CORS y retorno PKCE.
- Asignación Entra explícita, pruebas con dos Requester reales y un Operator, MFA/Conditional Access y PIM según la organización.
- Pruebas reales de restauración, rotación Cosmos, outbox y poison queue.
- Medición de carga, RU/429, réplicas, latencia y costes; alertas de negocio y permisos mínimos para CI.
- Revisión de los servicios compartidos: su capacidad y posibles incidencias afectan a ambos entornos.

Container Apps Prod es zonal; Cosmos sigue en una región. Esto no constituye alta disponibilidad completa. Functions y webs todavía no tienen una promoción inmutable completa de sus artefactos. El almacenamiento de adjuntos está preparado, pero su UI no está implementada.

## Diagnóstico

| Síntoma | Revisar |
| --- | --- |
| Un servicio privado no responde desde el Mac | Ejecuta operaciones de datos desde el ejecutor privado y verifica resolución DNS, rutas y permisos. Los usuarios de la app entran por el WAF. |
| API devuelve 401 | Token, audiencia, emisor, entorno y caducidad. |
| API devuelve 403 | Rol, asignación Entra, propietario y controles de red. |
| Una solicitud sigue pendiente | Outbox, cola, publicación de Functions y logs. 202 confirma persistencia, no procesamiento completo. |
| Primera petición Dev lenta | Puede haber arranque en frío porque las APIs escalan a cero. |
| Diagrama no visible al clonar | Ejecuta `make site` y sirve `dist/` por HTTP. Los HTML de diagramas son generados. |
| No cambia la vista de un portal | `view` solo elige tenant/admin del ejemplo; otra interfaz requiere código propio. |

## Qué se ha validado

Las pruebas locales con proveedores simulados verifican contratos y controles del código. Completa los criterios de producción de `docs/OPERACION_Y_RECUPERACION.md` y consulta los límites en `docs/SEGURIDAD.md`. Conserva la evidencia de tu instalación en un destino privado; las pruebas de restauración, carga y aislamiento deben ejecutarse en tu entorno. Ningún escaneo automático garantiza ausencia total de secretos o vulnerabilidades.
