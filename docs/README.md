# Documentación de Goliat Nexus

Empieza por el funcionamiento y la configuración. Antes de introducir datos reales, revisa seguridad y completa los criterios de producción del runbook.

| Guía | Contenido |
|---|---|
| [Funcionamiento](FUNCIONAMIENTO.md) | Arquitectura, componentes y secuencia de despliegue. |
| [Variables y tfvars](VARIABLES_Y_TFVARS.md) | Todas las opciones expuestas y ejemplos comentados de Dev y Prod. |
| [Aplicación de referencia](APLICACION_DE_REFERENCIA.md) | Portales Alba, APIs, cola y Function. |
| [Recursos](RECURSOS_DEL_PRODUCTO.md) | Qué se crea, dónde y qué servicios se comparten. |
| [Módulos](CATALOGO_MODULOS.md) | Composición Terraform y agente privado opcional. |
| [Seguridad](SEGURIDAD.md) | Identidad, red, recorridos WAF/Firewall y límites. |
| [Secretos](SECRETOS.md) | Registro en Key Vault y rotación. |
| [Entrada pública](ENTRADA_PUBLICA.md) | WAF, dominio Azure, dominios propios y certificados. |
| [Operación y recuperación](OPERACION_Y_RECUPERACION.md) | Aceptación, criterios de producción, backup y desmontaje. |
| [CI/CD](CI_CD.md) | Validación, seguridad y publicación manual. |
| [Versiones](VERSIONES.md) | Dependencias y consideraciones de actualización. |

La [wiki](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) está disponible en español e inglés; sus fuentes se conservan en `docs/wiki/`. Los README del repositorio también están disponibles en ambos idiomas.

`INVENTARIO_TERRAFORM.json` alimenta el inventario de la web; `VERSIONES.json` recoge las versiones de las dependencias y `arquitectura.svg` ilustra el manual. Se conservan como datos y recursos de la documentación.

Los HTML se generan desde Markdown y no se versionan: `make docs` crea el manual en `.local/docs/`; `make site` genera las guías y los diagramas en `dist/` y prepara la vista local de `site/`.

## English

Start with the [English repository README](https://github.com/danieljsaldana/goliat-nexus/blob/main/README.md), [English wiki](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) and [CI/CD guide](CI_CD.en.md). Detailed architecture and operational guides above currently use Spanish. Production acceptance criteria and limitations are maintained in the operations and security guides. HTML documentation is generated from Markdown; generated copies and internal review reports are not part of the published source documentation.
