# Red, identidad y secretos

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [English](https://github.com/danieljsaldana/goliat-nexus/wiki/Security)

La base aplica controles Zero Trust de red, identidad y acceso a datos. La configuración y aceptación de producción dependen también de las políticas de tu organización.

## Entrada y acceso privado

- WAF_v2 compartido en Prevention para la entrada pública HTTPS.
- Orígenes Static Web Apps Standard restringidos a la IP del WAF; Nginx restringido a su subred.
- APIs internas con validación de firma, emisor, audiencia, vigencia, cliente, scope, rol, tenant y propietario.
- Functions, Cosmos, Storage y vaults con acceso público cerrado y endpoints privados correspondientes.
- Salida autorizada por Firewall y permisos de identidad específicos. Estar en la VNet no concede acceso a datos.

## Key Vault

Los secretos de la aplicación se sincronizan con Key Vault fuera de tfvars. APIs y Functions usan identidades administradas y permisos por secreto. Cosmos MongoDB utiliza conexiones custodiadas en vaults; las APIs de consulta reciben conexión de solo lectura. Esto no equivale a autenticación MongoDB completamente sin claves.

Los vaults de aplicación mantienen `bypass = None`. El vault TLS conserva Private Endpoint y acceso público deshabilitado, con la excepción `AzureServices` requerida por Application Gateway para validar el secreto. La identidad WAF solo lee su certificado. Revisa esta excepción en tu modelo de seguridad.

Protege también el estado y los backups Terraform: pueden contener información sensible aunque los secretos de aplicación se sincronicen fuera de Terraform.

## Repositorio y material local

| Publicable | Local y protegido |
| --- | --- |
| Código, documentación y ejemplos ficticios | `.local/`, `.lz/`, configuración real y diarios de identidad |
| Plantilla explícita del agente | Estados, planes, claves, certificados privados y cachés de autenticación |

Ejecuta `make publication-check` antes de subir código. Gitleaks revisa fuentes e historial; la copia GitHub usa una lista de archivos permitidos. El escaneo no sustituye la revisión ni detecta todos los posibles secretos. Si se expone una credencial, revócala o rótala antes de limpiar el historial.

MFA, Conditional Access y PIM se completan con la organización; el producto no modifica automáticamente esas políticas del directorio.
