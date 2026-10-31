# Contributing to Goliat Nexus

**English** · [Español](CONTRIBUTING.es.md)

Bug reports, focused improvements, examples, translations and documentation fixes are welcome. Contributions are made under the [repository licence](LICENSE); preserve existing copyright and third-party notices. Read [the licensing scope](LICENSING.md) before reusing the product.

Use the [issue forms](https://github.com/danieljsaldana/goliat-nexus/issues/new/choose) for bugs, feature requests, documentation or usage questions. Search existing issues and the [wiki](https://github.com/danieljsaldana/goliat-nexus/wiki) first. For a substantial architecture change, discuss the use case in an issue before implementing it. Reports and PRs in English or Spanish are welcome.

Report vulnerabilities through [private reporting](https://github.com/danieljsaldana/goliat-nexus/security/advisories/new), as described in [SECURITY.md](SECURITY.md). Keep credentials, real tfvars, Terraform state, plans and customer data out of issues, PRs, screenshots and logs.

## Fork and work on a branch

Fork the repository in GitHub, clone your fork and create a branch from current `main`:

```sh
git clone https://github.com/<YOUR-USER>/goliat-nexus.git
cd goliat-nexus
git remote add upstream https://github.com/danieljsaldana/goliat-nexus.git
git switch -c fix/short-description
```

Before starting a later change, fetch `upstream` and update your branch from `upstream/main`. Open the PR from your fork into this repository's `main`. You do not need write access, Azure credentials or access to the private runner to contribute.

## Install tools and dependencies

See [verified versions](docs/VERSIONES.md). CI uses Terraform 1.17.1, Python 3.15 and Node.js 24. Docker with a Linux engine is needed only for the image smoke test.

```sh
npm ci --ignore-scripts
npm --prefix apps/api ci --ignore-scripts
npm --prefix apps/functions ci --ignore-scripts
npm --prefix apps/portal ci --ignore-scripts
python3 scripts/install_gitleaks.py
python3 scripts/install_actionlint.py
git config core.hooksPath .githooks
```

Install ShellCheck for workflow/shell validation. The pre-push hook scans source and Git history; the same controls run in CI.

## Validate the affected parts

```sh
make workflows-check
make fmt check test validate
make inventory docs wiki-check
make site site-check
python3 scripts/check_publication.py --history --strict-tracked --artifacts dist
make images-check
```

Run the checks relevant to your change and list any unavailable checks in the PR. CI runs the complete validation before merge. Terraform tests use mock providers and fictional configuration. Application tests use synthetic data; these commands do not deploy Azure. Never use a production environment for contribution tests.

Keep changes within the existing Terraform module, stack, CLI and application boundaries. Add regression tests when fixing behaviour; update commented tfvars, examples and documentation when configuration changes. Keep user-facing English and Spanish text in sync.

For website changes, run `make site-serve` and inspect desktop and mobile widths. Edit diagram JSON under `site/diagrams/`; its HTML is generated. Wiki source lives under `docs/wiki/`. Do not commit generated HTML, build output, archives, `.local/`, `.lz/` or modified real deployment inputs. See [publication boundaries](docs/CI_CD.en.md).

## Pull request review

Describe the problem, the new behaviour and how you validated it. Link the issue, include sanitised UI screenshots when useful, and explain resource, compatibility, cost or data migration implications for infrastructure changes. Small documentation fixes do not need a separate issue.

PRs run on GitHub-hosted Ubuntu runners with read-only source access and no Azure secrets. Only CodeQL receives permission to publish security analysis results. A maintainer must approve workflow execution for external contributors; waiting for approval is normal. PRs do not publish Pages, create a release or deploy Azure. Workflows never use `pull_request_target` to execute a contributor's code.

`main` requires a PR, up-to-date checks, **CI passed**, the three CodeQL jobs, dependency review and resolved review conversations. New pushes repeat the checks. Automatic merging is disabled; a maintainer chooses when to merge. The single-maintainer configuration requires zero formal approval votes, matching Inventory, so the maintainer can merge their own checked PRs. It does not give external contributors merge permission. Raise that approval count when there is another independent maintainer.

Follow the [code of conduct](CODE_OF_CONDUCT.md). Maintainers use `bug`, `enhancement`, `documentation` and `dependencies` to classify changes; GitHub can group generated release notes with these labels. `good first issue` and `help wanted` mark tasks open to contributors. New issues start with `needs triage`.

## Maintainer settings

Repository settings are separate from files and are not inherited by forks. Keep Issues and forking enabled, delete merged branches automatically, allow updating PR branches, and retain the protected-main checks above. Actions should use read-only default permissions, must not approve PRs, and should require approval for all external contributors. Keep private vulnerability reporting, secret scanning and push protection enabled. Dependabot security fixes remain reviewed PRs, without auto-merge.

