# Security

Keep deployment credentials and operational data outside this repository. Use `.local/` for installation configuration and `.lz/` for generated Terraform code, state metadata, identity journals and temporary credentials. Application secrets belong in Azure Key Vault.

Before publishing, run:

```sh
python3 scripts/install_gitleaks.py
make publication-check
```

The check scans allowlisted source with Gitleaks, checks local Git history and rejects tracked credentials, local tfvars, states, plans and authentication caches. It never prints matched secret values. The GitHub Actions security job repeats these checks after code is eventually uploaded.

`make prepare-github` creates a fresh local checkout from public source only. It excludes the working repository history, local deployment data, hosting integration metadata and generated artifacts. It does not commit or push. The prepared checkout enables `.githooks/pre-push`; install Gitleaks there before the first push.

The agent also includes an explicit `.tfvars.example` template with fictional placeholders. The only public tfvars are the documented fictional examples under `environments/`, `examples/demo/` and `examples/shared.auto.tfvars.json`. Never replace their placeholders with a real tenant, subscription, identity or credential. Generate real values into an ignored local directory.

Automated scanning detects known patterns; review source and generated website output as well. If a credential is ever exposed, revoke or rotate it before removing it from Git history.

Report a potential vulnerability privately through the contact information at [danieljsaldana.dev](https://danieljsaldana.dev/). Do not include credentials, access tokens, customer data or Terraform state in a public issue.

CI uses `--strict-tracked` to reject every tracked path outside the export allowlist. The pre-push hook applies the same rule in the prepared clean checkout. The historical workspace retains local Sites integration metadata and must not be pushed as the product repository.

Before uploading generated output, run `make artifacts-check`. This rejects archives, symlinks and private file types, then scans all generated contents with Gitleaks. Source and configuration are versioned as regular files; no product ZIPs are generated or published. Public example Azure identifiers must remain fictional. Tool versions and download checksums are fixed in `scripts/security-tools.json`. See [the pipeline guide](docs/CI_CD.en.md).
