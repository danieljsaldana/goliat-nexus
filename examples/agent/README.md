# Optional private GitHub Actions agent

**English** · [Español](README.es.md)

Uses the Nexus `modules/virtual_machine` module with an existing Nexus subnet, SSH keys, Secure Boot, vTPM and a managed identity. The VM has no public IP and receives no Azure roles by default. Installation uses official HTTPS repositories and verifies Node.js and Terraform binaries.

Copy this directory to `.local/agent`, create `local.auto.tfvars` from `local.auto.tfvars.example`, run `terraform -chdir=.local/agent init` and review the plan before applying. This optional stack keeps its state locally inside `.local/agent`, outside the five main states. Protect and retain that directory to operate or remove the agent.

Allow Ubuntu, Docker, Microsoft, Node.js and GitHub download HTTPS destinations in `management_https_fqdns`. Bootstrap installs Docker/Buildx, Node.js, Azure CLI, SWA CLI and Terraform. Register the runner afterwards with `python3 scripts/register_github_runner.py --directory .local/agent`, using your `gh` and `az` sessions. The temporary registration token travels as a protected Azure Run Command parameter; it is not written into tfvars or state. GitHub manages operational credentials in the runner's private directory.

Set `github_repository` and `github_environment` in the environment's tfvars to create its optional OIDC publisher. The VM identity still has no Azure permissions; the workflow uses the environment's federated identity. Use a private repository with controlled workflows; protect the Prod environment with a review requirement before enabling its publisher.

The VM incurs costs while allocated. Budget alerts do not stop spending. After testing, remove this optional stack through Terraform, preserving any evidence you need first.

To check the runner, copy `smoke-workflow.yml` into your private repository's `.github/workflows/` and trigger it manually. Match `runs-on` to `github_labels`; the example uses `goliat-nexus`. It needs no checkout, secrets or Azure permissions.

Example exceptions to add to `common.tfvars` before creating the VM:

```hcl
management_https_fqdns = [
  "archive.ubuntu.com",
  "security.ubuntu.com",
  "packages.microsoft.com",
  "download.docker.com",
  "nodejs.org",
  "objects.githubusercontent.com",
  "release-assets.githubusercontent.com",
  "aka.ms",
  "swalocaldeployv2-bndtgugjgqc3dhdx.b01.azurefd.net",
]
```

General GitHub, Terraform, npm and Docker Hub downloads already appear in the product's management rules. For portal publishing, also add the specific staging FQDNs assigned by Static Web Apps; see [the variables guide](../../docs/VARIABLES_Y_TFVARS.md) (Spanish). Do not add these exceptions to API egress rules.
