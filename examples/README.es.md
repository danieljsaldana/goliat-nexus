# Ejemplos

[English](README.md) · **Español**

La entrada recomendada del producto es `../environments/`, con common/dev/prod HCL comentados. `demo/` contiene otra instalación de evaluación. `shared.json` y `shared.auto.tfvars.json` se mantienen como formatos compatibles, generados y sin comentarios. No contienen secretos y usan identificadores ficticios.

`make tfvars` sincroniza el JSON nativo. `./lz render --config environments --examples` genera las entradas automáticas de las cinco capas sin acceder a Azure. No edites los contratos internos de `.lz/`.
