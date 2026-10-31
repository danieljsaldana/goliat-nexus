# Product configuration

**English** · [Español](README.es.md)

These three files define **one installation**: `common.tfvars`, `dev.tfvars` and `prod.tfvars`. The CLI loads them together; they are not independent deployments. They use commented settings, separated blocks and fictional values. Keep `environment = "shared"` in common.

Generate your local copies with `./lz configure --name my-platform-v1 --operator-ip '<IP>/32' --alert-email '<EMAIL>' --output-dir .local/environments`. The generator preserves comments and creates files with mode 0600. Adjust the settings and read the [variables guide](../docs/VARIABLES_Y_TFVARS.md) (Spanish).

Dev uses Cosmos MongoDB Serverless, 8-hour backups and 0–3 API replicas. Prod uses 400 RU/s shared by its collections, 24-hour backups, 2–5 API replicas and zone-redundant Container Apps. These are reference values, not production sizing. The `web_portals` map includes tenant and admin per environment. Add named keys for more websites or use `{}` for none; check Static Web Apps quotas.

The CLI generates `inputs.auto.tfvars.json` in `.lz/`. Do not edit or commit these files; JSON cannot contain comments. Never put secrets in any of these configuration files.
