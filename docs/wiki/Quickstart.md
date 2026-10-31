# First deployment

[Inicio / Home](https://github.com/danieljsaldana/goliat-nexus/wiki/Home) · [Español](https://github.com/danieljsaldana/goliat-nexus/wiki/Inicio-rapido)

## Requirements

Terraform ≥1.9 and <2, Python 3.10+, Azure CLI and Azure/Entra permissions to manage resources and application registrations. Publishing requires a private Linux executor with private DNS, Node.js ≥24, npm, Docker/Buildx with a Linux engine and SWA CLI 2.1.0.

Check quotas, regions and costs before applying. The example creates real Azure resources, including shared services that incur costs without traffic. Connect an existing executor or deploy the optional `examples/agent` VM for GitHub Actions.

## Configure and bootstrap networking

From the source repository root:

```sh
az login
./lz configure --name myplatform --operator-ip '<YOUR-PUBLIC-IP>/32' --alert-email '<YOUR-EMAIL>' --output-dir .local/environments
./lz check --config .local/environments
./lz deploy --config .local/environments --stage foundation
./lz deploy --config .local/environments --stage platform
```

Replace `<...>` locally. Keep real values out of the public examples. Foundation/platform preparation and closing the state backend are bootstrap steps; retain private executor access before proceeding.

## Publish from the private executor

```sh
./lz deploy --config .local/environments --yes
./lz smoke-test --config .local/environments --environment dev
./lz verify-application --config .local/environments --environment dev
```

The executor needs the corresponding Azure/Entra session and permissions, plus private connectivity. A call without `--stage` coordinates all five layers and applies each saved plan. `--yes` approves changes without interaction: review configuration and plans beforehand.

Read application URLs from outputs, never from fictional names. The default Azure-generated hostname uses `/dev/tenant/`, `/dev/admin/`, `/prod/tenant/` and `/prod/admin/`. Portal users enter through the WAF without a VPN.

## Evaluate a separate installation

Use `./lz configure --demo --name mydemo ... --output-dir .local/demo`, supplying the same IP and email parameters. Demo has its own name and states, uses real Cosmos data and incurs costs. Do not mix its configuration with the product installation.
