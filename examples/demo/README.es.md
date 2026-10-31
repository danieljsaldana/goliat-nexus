# Instalación de evaluación

[English](README.md) · **Español**

La demo sirve para desplegar y entender el producto. Sus tres tfvars comentados usan `lzdemov1`, un nombre distinto al producto `acmev1`, y `deploy_demo = true` para etiquetar los portales como evaluación. Despliega recursos Azure reales y genera costes.

Usa `./lz configure --demo --name mi-demo-v1 --operator-ip '<IP>/32' --alert-email '<CORREO>' --output-dir .local/demo`. Aplica foundation, platform y después Dev/Prod y edge desde el ejecutor privado. El hub de esta demo es compartido por sus propios Dev/Prod, no por otra instalación del producto. No se deben mezclar estados de ambas instalaciones.

Los interruptores `enable_*` funcionan igual que en el producto. Consulta [el manual](../../docs/FUNCIONAMIENTO.md) y [las variables](../../docs/VARIABLES_Y_TFVARS.md). El modo en memoria solo existe para pruebas locales explícitas; la demo Azure usa Cosmos.
