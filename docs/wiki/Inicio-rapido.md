# Primer despliegue

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [English](https://github.com/danieljsaldana/goliat-nexus/wiki/Quickstart)

## Requisitos

Terraform ≥1.9 y <2, Python 3.10+, Azure CLI y permisos Azure/Entra para los recursos y registros de aplicación. Publicar la aplicación requiere un ejecutor Linux privado con DNS privado, Node.js ≥24, npm, Docker/Buildx con motor Linux y SWA CLI 2.1.0.

Comprueba cuotas, regiones y costes antes de aplicar. El ejemplo crea recursos Azure reales, incluidos servicios compartidos facturables sin tráfico. Para GitHub Actions puedes conectar un ejecutor existente o desplegar el agente privado opcional de `examples/agent`.

## Configurar y preparar la red

Desde la raíz del código:

```sh
az login
./lz configure --name miplataforma --operator-ip '<TU-IP-PUBLICA>/32' --alert-email '<TU-CORREO>' --output-dir .local/environments
./lz check --config .local/environments
./lz deploy --config .local/environments --stage foundation
./lz deploy --config .local/environments --stage platform
```

Los valores entre `<...>` se sustituyen localmente. No cambies los ejemplos públicos con datos reales. La preparación de foundation/platform y el cierre del backend forman parte del bootstrap; conserva el acceso del ejecutor privado antes de continuar.

## Publicar desde el ejecutor privado

```sh
./lz deploy --config .local/environments --yes
./lz smoke-test --config .local/environments --environment dev
./lz verify-application --config .local/environments --environment dev
```

El ejecutor necesita la sesión y los permisos Azure/Entra correspondientes, además de conectividad privada. La llamada sin `--stage` coordina las cinco capas y aplica cada plan guardado. `--yes` aprueba los cambios sin interacción: revisa previamente la configuración y los planes.

Las URLs se obtienen de los outputs, nunca de nombres de ejemplo. Por defecto se utiliza un hostname generado por Azure con rutas `/dev/tenant/`, `/dev/admin/`, `/prod/tenant/` y `/prod/admin/`. El usuario de los portales entra por el WAF sin VPN.

## Evaluar otra instalación

Usa `./lz configure --demo --name midemo ... --output-dir .local/demo`, completando los mismos parámetros de IP y correo. Demo tiene nombre y estados propios, usa Cosmos real y genera costes. No mezcles su configuración con la instalación del producto.
