# Pipelines and pre-publication review

[Español](CI_CD.md)

Workflows validate source, dependencies and the website. Local review commands neither publish code nor deploy Azure or synchronize the wiki; publishing uses manual workflows.

| File | Trigger | Purpose |
| --- | --- | --- |
| `.github/workflows/validate.yml` | PR, main push, manual, reusable | Source/history scanning, workflow and shell validation, Python/Node tests, Next.js build, npm audits, mocked Terraform security plans, inventory/wiki, images and website. |
| `.github/workflows/security.yml` | PR, main, weekly, manual | CodeQL for Actions, Python and JavaScript/TypeScript; dependency review on PRs. |
| `.github/dependabot.yml` | Weekly | Action, five npm package and Terraform provider update proposals. |
| `.github/workflows/release.yml` | Manual, main only | Rerun CI and create an audited **draft** release with source hashes and commit provenance, without ZIP assets. |
| `.github/workflows/pages.yml` | Manual, main only | Build, audit and publish the static product website to GitHub Pages. |

Actions use full commit SHAs verified in their official repositories. Gitleaks and actionlint downloads use fixed versions and versioned SHA-256 values in `scripts/security-tools.json`. CI runs on GitHub-hosted runners with read-only repository access, timeouts and a final `CI passed` gate covering every job/matrix. Pull requests never run on the private Azure agent. No `pull_request_target`, Azure sessions, SPNs, PATs or cloud secrets are required.

Only CodeQL writes security results; only the draft-release job has repository write permission. Only Pages deployment has Pages and OIDC write permissions. Before enabling publishing, protect main, require `CI passed` and CodeQL checks, configure the `release` environment for review, and configure Pages to use GitHub Actions with an appropriate `github-pages` environment. Workflows do not automatically apply these repository settings.

## Publication boundary

Source scanning includes non-ignored working files and all local Git refs. CI and the clean checkout use `--strict-tracked` to reject tracked files outside the export allowlist. Public tfvars retain fictional Azure identifiers; real values stay in ignored `.local/` files. Use strict mode in the prepared public checkout.

Generated artifacts are inspected before upload: archives (including ZIPs), symlinks and private file names are rejected, then Gitleaks scans the contents. All code and tfvars remain regular files in Git. Only audited static output from main is retained for seven days. Deployment states, plans, journals, authentication caches and logs are never uploaded.

```sh
python3 scripts/install_gitleaks.py
python3 scripts/install_actionlint.py
make workflows-check
make fmt check test validate
make inventory docs wiki-check
make site site-check artifacts-check
```

Terraform uses mock providers without Azure login. Providers are downloaded from the registry and npm audits query public advisories. `make images-check` requires a Linux Docker engine, available on the pipeline's Ubuntu runner. Run `make prepare-github` to create `.local/github-ready/goliat-nexus/` with fresh history, a remote and a pre-push hook, without committing or pushing. Existing destinations are preserved; use `python3 scripts/prepare_github.py --output <ANOTHER-DIRECTORY>` for another copy. Inside that checkout, install the scanner with `python3 scripts/install_gitleaks.py`, then run `python3 scripts/check_publication.py --history --strict-tracked`. Hooks complement review and GitHub controls.

## Releases, Pages and Azure

The manual release version must match `VERSION`. A release reruns CI, rescans the full checkout and requires clean source. It creates per-file SOURCE_SHA256SUMS, commit provenance and draft notes without packaging code or tfvars. Existing releases are preserved. The owner reviews notes, hashes and evidence before publishing. Pages is a separate manual action; it neither provisions Azure nor deploys Alba.

Azure deployment keeps using the CLI and a private executor. The optional OIDC publisher's limited image/group/identity roles do not provide all state, secret, RBAC-assignment and directory permissions needed for a full platform deployment. Azure CD needs a deliberate permissions, private connectivity/DNS and environment-approval design. Never put personal credentials or real tfvars in the public repository.

Actions logs and artifacts are public when executed in this public repository. Validation uses fictional values and avoids printing secret material. Automated scanning cannot guarantee the absence of every sensitive value.
