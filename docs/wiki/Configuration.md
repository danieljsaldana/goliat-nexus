# Configuration and modularity

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [Español](https://github.com/danieljsaldana/goliat-nexus/wiki/Configuracion)

`environments/common.tfvars`, `dev.tfvars` and `prod.tfvars` define one installation and are loaded together. `examples/demo` is a separate evaluation installation, not a third environment sharing the same hub.

| File | Content |
| --- | --- |
| common.tfvars | Identity, region, shared network, state, WAF entry and operations. |
| dev.tfvars | Dev components, access and capacity. |
| prod.tfvars | Prod components, access and capacity. |

Public HCL files contain comments and fictional identifiers. `configure` creates private copies with mode 0600 under `.local/`. The CLI derives `inputs.auto.tfvars.json` under `.lz/`; do not edit or publish these internal contracts. JSON cannot contain comments.

## Portals are a map

Inside the environment configuration:

```hcl
web_portals = {
  tenant = { view = "tenant" }
  admin  = { view = "admin" }
}
```

Each key creates another Static Web App publication. `view` selects one of the two example interfaces; it neither grants Entra roles nor generates business logic. Supply code for a different interface. Additional keys reuse existing views; `{}` creates no portals. Check quotas and component dependencies.

## Reference capacity

| Setting | Dev | Prod |
| --- | --- | --- |
| Replicas per API | 0–3 | 2–5 |
| Cosmos MongoDB | Serverless | Shared 400 RU/s |
| Periodic backup retention | 8 h | 24 h |
| Zonal Container Apps | No | Yes |

These values do not replace load testing. Cosmos remains single-region. `enable_*` switches have validated dependencies; enabling Event Grid creates neither subscriptions nor a replacement Queue trigger. `enable_content_storage` prepares storage, not an attachment UI.

## Domains

`public_entrypoint.hostname = ""` uses the real Azure-generated FQDN. For production, configure distinct hostnames through `public_entrypoint.environment_hostnames` and review DNS, listeners, certificates, CORS and Entra redirects. The single default hostname shares a browser origin across Dev and Prod.
