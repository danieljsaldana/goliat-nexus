# Alba: dos portales de ejemplo, un flujo de solicitudes

Alba es una aplicación de ejemplo para desplegar y comprobar la plataforma. Sus pantallas de usuario y operaciones ilustran autenticación, permisos, datos y eventos; sustitúyelas o adáptalas para tu producto. Añadir una clave en `web_portals` crea otra publicación, pero no genera una nueva interfaz ni nueva lógica de negocio.

## Las tres piezas

- **Frontend Next.js estático:** dos publicaciones, usuario (tenant) y operaciones (admin). Ejecuta el formulario en el navegador y usa MSAL con PKCE para iniciar sesión con Entra. No contiene conexiones de base de datos.
- **Backend Node.js:** valida cada token y el contenido de la solicitud. Guarda en Cosmos API MongoDB 7.0 y publica en Storage Queue usando su identidad.
- **Functions Node.js:** un trigger escucha la cola y un temporizador recupera el outbox. No hay endpoint HTTP de negocio invocado por el navegador.

El mapa `web_portals` permite añadir publicaciones con nombres propios. `view` selecciona una de las dos interfaces de ejemplo, tenant o admin; otra interfaz requiere aportar su código. No hay flags específicos SaaS, worker o guest. Las APIs de catálogo, solicitudes y actividades son módulos del backend. Cambiar de URL o vista no cambia los permisos del usuario: el backend verifica el token y filtra los registros.

## Caso de ejemplo: pedir acceso

1. Un usuario asignado a la aplicación inicia sesión. El frontend obtiene un token de acceso para la API del entorno.
2. Envía `{id, title, category}` a `POST /api/tenant/requests`. El UUID se conserva cuando el usuario reintenta.
3. La API comprueba firma RS256, emisor, audiencia, tenant, tiempo, cliente, scope y rol; valida el JSON y deriva tenant/propietario del token.
4. Inserta la solicitud con `status=received` y `outbox_pending=true`. Devuelve 202 cuando el documento existe; eso no significa que ya se haya procesado.
5. La API publica `{id, request_id, tenant_id, type}` en `requests-events` y limpia la marca pendiente. Cosmos no publica el evento automáticamente.
6. La Function valida la identidad del evento respecto al tenant configurado, registra una actividad por id y marca la solicitud `processed`.
7. Al actualizar, el navegador consulta las APIs de solicitudes y actividades con su token. Requester ve solo sus datos; Operator consulta el entorno.

Mantenimiento y soporte usan la misma secuencia con otra categoría. La demostración de la web permite seguir los pasos y ver JSON ficticio; no representa llamadas ni un despliegue real de Azure.

## Qué ocurre si falla o se repite

Si falla la publicación, la solicitud sigue en Cosmos y conserva el outbox. El temporizador lo reintenta cada minuto sin crear otra solicitud. La cola puede entregar un evento varias veces; el upsert por id evita otra actividad. Las escrituras de actividad y estado no son una transacción distribuida. Tras cinco fallos de consumo, revisa `requests-events-poison` y reproduce solo eventos validados.

## Seguridad y red

El navegador descarga Static Web Apps y consulta las APIs a través del WAF compartido. Los orígenes web solo admiten su IP y el gateway privado solo su subred. No necesita VPN. La API sigue exigiendo token aunque la petición venga de la VNet. Las identidades de servicio y secretos AKV son independientes del acceso de usuario. Las APIs de consulta leen Cosmos con una conexión de solo lectura. [Modelo completo](SEGURIDAD.md).

## Probar después del despliegue

```sh
./lz verify-application --config .local/environments --environment dev
```

Con sesión Azure CLI de un usuario asignado y acceso HTTPS al WAF, crea una solicitud real, repite su UUID y espera la actividad de la Function. El registro se conserva para inspección. Abre después uno de los portales desde un navegador e inicia sesión para comprobar la interfaz. Sigue las pruebas de denegación y recuperación del [runbook](OPERACION_Y_RECUPERACION.md).
