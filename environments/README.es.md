# Configuración del producto

[English](README.md) · **Español**

Estos tres archivos forman **una única instalación**: `common.tfvars`, `dev.tfvars` y `prod.tfvars`. El CLI los carga juntos; no son tres despliegues independientes. Tienen comentarios por ajuste, bloques separados y valores ficticios. Conserva `environment = "shared"` en common.

Genera tus copias mediante `./lz configure --name mi-plataforma-v1 --operator-ip '<IP>/32' --alert-email '<CORREO>' --output-dir .local/environments`. El generador añade los mismos comentarios y crea archivos con permisos 0600. Ajusta las opciones y revisa [la guía de variables](../docs/VARIABLES_Y_TFVARS.md).

Dev usa Cosmos MongoDB Serverless, backup de 8 horas y APIs de 0–3 réplicas. Prod usa 400 RU/s compartidas por sus colecciones, backup de 24 horas, APIs de 2–5 réplicas y Container Apps zonal. Son referencias, no dimensionamiento de producción. El mapa `web_portals` contiene tenant y admin por entorno. Añade claves con nombres propios para más webs o usa `{}` para ninguna; revisa las cuotas de Static Web Apps.

Las entradas `inputs.auto.tfvars.json` las genera el CLI en `.lz/`: no se editan ni se versionan y no llevan comentarios porque son JSON. No introduzcas secretos en ninguno de estos archivos.
