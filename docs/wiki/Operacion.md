# Operación, identidad y recuperación

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [English](https://github.com/danieljsaldana/goliat-nexus/wiki/Operations)

## Desplegar y reanudar

La instalación tiene cinco estados. Cada capa aplica el archivo de plan guardado, después de disponer de los outputs anteriores. Conserva la configuración, el backend y los manifiestos de imágenes para reanudar un fallo. `--reuse-images` reutiliza digests; Functions y webs siguen publicándose desde el checkout.

## SPN de instalación

El SPN se crea la primera vez y se reutiliza. Cada ejecución genera un certificado de hasta cuatro horas y lo revoca al terminar, también ante errores controlados. El SPN y sus permisos permanecen hasta el desmontaje completo. AzureAD conserva la sesión delegada del operador; no se conceden permisos globales Graph al SPN.

Conserva el diario `.lz/identities/installation-<nombre>-<suffix>/run.json`. No publiques ese archivo ni ejecutes simultáneamente la misma instalación desde varias máquinas. Para CI con OIDC/MI usa `--identity existing` con sus permisos revisados.

Si una interrupción impidió retirar la credencial, revisa el diario y utiliza `cleanup-identity --credentials-only` con su `--run` correspondiente. Para retirar el SPN completo hay que desmontar antes los recursos y revisar la operación: el CLI lo bloquea mientras exista alguno de los cinco grupos. Eliminar recursos desde el Portal no retira automáticamente su identidad Entra.

## Agente opcional

La VM del hub no tiene IP pública y su identidad no recibe roles Azure por defecto. El usuario configura el repositorio de GitHub, las etiquetas, los permisos y la protección del entorno Prod. El registro usa un token temporal enviado como parámetro protegido de Run Command; no se escribe en tfvars ni en el estado.

## Backups y recuperación

`backup-state` genera una copia protegida de los estados y `recovery-check --backup <CARPETA>` verifica su integridad sin conectarse a Azure. Verificar hashes no acredita una restauración real. Cosmos usa backups periódicos configurables, no PITR ni failover multirregión.

Ante eventos fallidos, comprueba outbox, logs y `requests-events-poison`. Reproduce solo mensajes validados, conserva el identificador original y verifica la actividad antes de repetir acciones de negocio.

## Retirada

Revisa dependencias, datos y copias antes de destruir cada stack mediante Terraform. No hay un comando genérico `lz destroy`. Las protecciones `prevent_destroy` requieren un procedimiento explícito para eliminar datos. Tras comprobar el desmontaje de todos los grupos, retira el SPN mediante `cleanup-identity --run <DIARIO>`. La VM opcional tiene su propio estado y ciclo de retirada.
