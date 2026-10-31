# Operations, identity and recovery

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [Español](https://github.com/danieljsaldana/goliat-nexus/wiki/Operacion)

## Deploy and resume

The installation has five states. Each layer applies its saved plan after preceding outputs exist. Preserve configuration, backend and image manifests to resume after failure. `--reuse-images` reuses digests; Functions and websites are still published from the checkout.

## Installation SPN

The SPN is created on first deployment and reused. Each run generates a certificate valid for at most four hours, revoked on completion and controlled failure. The SPN and roles remain until full teardown. AzureAD retains the delegated operator session; the SPN receives no global Graph permissions.

Preserve `.lz/identities/installation-<name>-<suffix>/run.json`. Never publish this journal or operate the same installation concurrently from multiple machines. CI using OIDC/managed identity selects `--identity existing` with reviewed permissions.

If an interruption prevented credential cleanup, review the journal and use `cleanup-identity --credentials-only` with its corresponding `--run` argument. Removing the complete SPN requires reviewed infrastructure teardown first: cleanup refuses while any of the five resource groups remain. Deleting resources in the Portal does not automatically retire their Entra identity.

## Optional agent

The hub VM has no public IP and its identity receives no Azure roles by default. The user configures the GitHub repository, labels, permissions and Prod environment protection. Registration uses a temporary token sent as a protected Run Command parameter, outside tfvars and state.

## Backups and recovery

`backup-state` creates a protected state backup; `recovery-check --backup <DIRECTORY>` checks its integrity without Azure access. Verifying hashes is not a restoration test. Cosmos uses configurable periodic backups, not PITR or multi-region failover.

For failed events, inspect outbox, logs and `requests-events-poison`. Replay only validated messages, retain the original identifier and verify activity before repeating business actions.

## Teardown

Review dependencies, data and backups before destroying each stack through Terraform. There is no generic `lz destroy` command. Data deletion protected by `prevent_destroy` requires an explicit procedure. After verifying removal of all groups, retire the SPN through `cleanup-identity --run <JOURNAL>`. The optional VM has its own state and teardown lifecycle.
