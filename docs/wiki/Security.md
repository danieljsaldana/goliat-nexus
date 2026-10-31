# Networks, identity and secrets

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [Español](https://github.com/danieljsaldana/goliat-nexus/wiki/Seguridad)

The foundation implements Zero Trust network, identity and data-access controls. Production configuration and acceptance also depend on your organization's policies.

## Public entry and private access

- Shared WAF_v2 in Prevention mode for public HTTPS ingress.
- Standard Static Web Apps origins restricted to the WAF IP; Nginx restricted to its subnet.
- Internal APIs validate signature, issuer, audience, lifetime, client, scope, role, tenant and owner.
- Functions, Cosmos, Storage and vaults have public access disabled and corresponding private endpoints.
- Authorized Firewall egress and scoped identity permissions. VNet connectivity grants no automatic data access.

## Key Vault

Application secrets are synchronized into Key Vault outside tfvars. APIs and Functions use managed identities and per-secret permissions. Cosmos MongoDB uses connections stored in vaults; query APIs receive a read-only connection. This is not fully keyless MongoDB authentication.

Application vaults retain `bypass = None`. The TLS vault keeps its Private Endpoint and disabled public access, with the `AzureServices` exception required for Application Gateway secret validation. The WAF identity only reads its certificate. Include this exception in your security review.

Protect Terraform state and backups as well: they can contain sensitive information even when application secret synchronization happens outside Terraform.

## Repository and local data

| Publishable | Local and protected |
| --- | --- |
| Code, documentation and fictional examples | `.local/`, `.lz/`, real configuration and identity journals |
| Explicit agent template | States, plans, keys, private certificates and authentication caches |

Run `make publication-check` before uploading code. Gitleaks checks source and history; the prepared GitHub checkout uses an allowlist. Automated scanning does not replace review or detect every possible secret. Revoke or rotate exposed credentials before cleaning history.

Complete MFA, Conditional Access and PIM with your organization; the product does not automatically modify these directory-wide policies.
