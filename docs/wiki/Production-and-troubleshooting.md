# Production readiness and troubleshooting

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [Español](https://github.com/danieljsaldana/goliat-nexus/wiki/Produccion-y-problemas)

Alba demonstrates the technical flow. Before using the foundation in a real project, adapt the application and complete acceptance, corporate security, operations and capacity work.

## Production checks

- Separate Dev/Prod hostnames and validate DNS, TLS, CORS and PKCE callbacks.
- Explicit Entra assignments, two real Requester users and an Operator, plus corporate MFA/Conditional Access and PIM.
- Real restoration, Cosmos rotation, outbox and poison queue exercises.
- Load, RU/429, replica, latency and cost measurements; business alerts and least-privilege CI access.
- Shared-service review: capacity and failures can affect both environments.

Prod Container Apps is zonal; Cosmos remains single-region. This is not complete high availability. Functions and websites do not yet have full immutable artifact promotion. Attachment storage is prepared, but its UI is not implemented.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| A private service is unreachable from a Mac | Run data operations from the private executor and verify DNS, routes and permissions. Application users enter through the WAF. |
| API returns 401 | Token, audience, issuer, environment and expiry. |
| API returns 403 | Role, Entra assignment, owner and network controls. |
| Request remains pending | Outbox, queue, Function publishing and logs. A 202 confirms persistence, not completed processing. |
| First Dev request is slow | APIs can cold-start after scaling to zero. |
| Diagrams are missing after cloning | Run `make site` and serve `dist/` over HTTP. Diagram HTML files are generated. |
| Portal view does not change | `view` selects the example tenant/admin UI; a different interface requires your code. |

## Validation evidence

Local mocked-provider tests verify code contracts and controls. Complete the production criteria in `docs/OPERACION_Y_RECUPERACION.md` and review the limits in `docs/SEGURIDAD.md`. Keep installation evidence in a private destination; restoration, load and isolation tests must run in your environment. Automated scanning cannot guarantee the absence of every secret or vulnerability.
