# Secretos y Key Vault

Cada entorno dispone de vault privado con RBAC, soft delete de 90 días y protección de purgado. La API tenant y Functions leen `cosmos-mongodb-connection`; catálogo y actividades leen `cosmos-mongodb-readonly-connection`; cada portal tiene `deploy-web-saas`, `deploy-web-admin`, etc. Un segundo vault por entorno conserva las claves internas de su Function App para evitar colisiones entre hosts.

```sh
./lz secrets-sync --config .local/environments --environment dev
```

El comando necesita ejecutor y DNS privados, Secrets Officer en el vault y permisos de Azure para listar la conexión Cosmos y los tokens SWA. El CLI obtiene los valores en memoria, valida host y TLS y registra el secreto mediante stdin. No escribe un archivo de valores ni los incluye en argumentos, outputs o logs. Compara el valor actual antes de crear una versión. Un error de permisos no se interpreta como secreto ausente.

`deploy` ejecuta esta sincronización antes de aplicar el workload. Cada API tiene Secrets User limitado al secreto de escritura o solo lectura que necesita; el gateway solo AcrPull. La Function tiene Secrets Officer en su vault de host, lectura de Cosmos y roles de datos Storage. Storage y Event Grid no usan claves locales. La publicación SWA usa el token en una variable del proceso, no en argv.

La conexión MongoDB contiene una clave amplia de la cuenta. Las APIs no usan RBAC de datos de Cosmos SQL. Revisa el impacto de ese permiso y limita el código que puede ejecutarse con estas identidades. Los portales nunca reciben ese secreto ni el token de despliegue en config.json.

El estado y planes Terraform siguen siendo sensibles: el proveedor puede conservar claves calculadas de Cosmos y tokens SWA. Limita permisos al backend y protege copias locales y backups, aunque ningún valor se exporte como output de integración.

## Rotación

Rota una clave Cosmos manteniendo la otra válida, sincroniza la nueva conexión, comprueba acceso y reinicia gradualmente las revisiones si necesitas una renovación inmediata. El cliente renueva su conexión consultando Key Vault aproximadamente cada diez minutos. Verifica el uso de la clave nueva antes de revocar la anterior. `secrets-sync` registra la conexión que devuelve Azure; no automatiza por sí solo una rotación segura de ambas claves.

Rota los tokens de publicación SWA desde Azure y vuelve a sincronizar. Ante un fallo de acceso, resuelve RBAC, propagación y DNS sin abrir el vault públicamente. No incluyas respuestas completas de comandos de secretos en incidencias ni capturas.

Los usuarios se autentican con Entra. Los tokens de acceso no son secretos estáticos que deban registrarse en Key Vault: se obtienen para la sesión y viajan en el encabezado Authorization. El CLI los conserva en memoria y no los incluye en argumentos ni logs. El frontend usa PKCE, sin client secret. Los IDs de aplicación y tenant son configuración pública.
