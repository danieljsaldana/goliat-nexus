# Goliat - Nexus website

**English** · [Español](README.es.md)

A product website based on the visual language of `goliat-cloud-inventory`: local DM Sans fonts, white and blue surfaces, ES/EN copy and the Archify interactive viewer. Its content and diagrams describe Goliat - Nexus modules.

## Run locally

From the repository root, with Python 3.10+ and Node.js 24+:

```sh
make site
make site-check
python3 -m http.server 8765 --bind 127.0.0.1 --directory dist
```

Open `http://127.0.0.1:8765/`. Alternatively, `make site-serve` builds and serves in one step. The resulting website is static; hosting does not require Node.js, a database or Azure credentials.

## Content and interactions

- Interactive solution explorer: shared platform, web entry and private events, with short traces that repeat after a 2.5-second pause. They pause offscreen and in hidden tabs, and stay static with reduced motion. These conceptual views never query Azure.
- Product capabilities and limitations, with an expandable Dev/Prod capacity comparison.
- ES/EN copy with optional locally stored language preference.
- Four diagrams: hub & spokes architecture (default), network/security, application/events, and deployment layers. The compact architecture puts the shared hub between Dev and Prod. Resource details remain in the inventory table and documentation.
- Archify zoom, component selection, search, routes and export.
- Dev/Prod commands, copy controls and links to commented tfvars in GitHub.
- HTML documentation and individually readable environment files; no product ZIPs.
- Responsive layout and reduced-motion support, with no movement on button hover.

Viewer controls and diagram labels currently use Spanish. `environments/` contains the product common/dev/prod tfvars and both READMEs. The separate evaluation installation uses `examples/demo/`. All source is versioned in Git; the website does not generate ZIP archives. The [variables guide](../docs/VARIABLES_Y_TFVARS.md) explains both. Examples come from `examples/`; the website neither invents alternative configurations nor runs Terraform in the browser.

## Source files

| File | Purpose |
| --- | --- |
| `index.html` | Structure and Spanish fallback copy |
| `styles.css` | Layout, typography, icons, animation and responsive rules |
| `app.js` | Languages, configuration, catalogue and example walkthrough |
| `diagram-viewer.js` | Independent diagram loading, validation, timeout and retry |
| `github.js` | Public GitHub star metadata, without credentials |
| `content/architecture-explorer.js` | ES/EN solution explorer copy |
| `lab.js` | Local simulation of events, failed publishing, recovery and duplicates |
| `diagrams/overview.json` | Compact hub & spokes architecture with independent Dev/Prod applications |
| `diagrams/network.json` | Subnets, routes, private endpoints and security |
| `diagrams/application.json` | Frontend, backend, Entra and events |
| `diagrams/deployment.json` | Foundation, Platform, Dev, Prod and Edge dependencies |
| `vendor/archify` | Vendored runtime and retained licenses |
| `../scripts/build_site.py` | Diagram, documentation and `dist/` generation |
| `../scripts/check_site.py` | Links, anchors, profiles and source checks |

Diagrams never query Azure. The website does not store visitor UUIDs, credentials or deployment configurations. Replace fictional example values before using the CLI.

## Preview paths and diagram loading

`make site` supports two preview layouts: `dist/` as the server root, and `/site/index.html` or `/site/index.htm` when serving the repository root. Generated diagram HTML and documentation are copied into Git-ignored `site/` paths. The distribution also includes a `/site/` alias for existing links.

Diagram URLs resolve relative to their JavaScript module, supporting root, `/site/` and GitHub Pages repository paths. The viewer runs independently of configuration and GitHub requests. It checks for the rendered diagram, rejects a 404 or generic HTML fallback, and offers retry/open controls after a failed or timed-out load. A loading state avoids an unexplained blank frame. Preview requests bypass stale diagram HTML.

Run `make site` after cloning or modifying source content. Generated HTML is intentionally not committed. If an open local browser tab still shows old copy, reload it without cache. `make site-check` checks `dist/`, `dist/site/` and `site/`.

The local Sites hosting identity, if configured, lives at `.openai/hosting.json` in the repository root. It is excluded from the website and the prepared GitHub checkout. Building the site does not publish it.

## Attribution and license

Visual reference: `goliat-cloud-inventory` at commit `c456aa3d33169261e257506ff997dc42b49b4180`. The Azure symbol, GitHub logo, local fonts and Archify 3.0.1 runtime retain their notices. UI icons use Lucide 1.66.0, with ISC/MIT notices in `assets/Lucide-LICENSE.txt`. See [NOTICE.md](NOTICE.md), `REFERENCE-LICENSE` and `vendor/archify/THIRD_PARTY_NOTICES.md`.

## GitHub link and stars

Links target the repository configured in `content/project.json`. The counter first displays a verified snapshot from `content/github-stars.json`, including a real zero. Its tooltip shows the date it was checked. The browser then requests `GET https://api.github.com/repos/{owner}/{repo}` without tokens, cookies or authorization headers; valid public metadata replaces the snapshot.

If the repository is private, missing or rate limited, or the network fails, the last verified snapshot remains visible with its original date. An invalid snapshot or one for a different repository is rejected. If neither source is available, the link remains without an invented count. Refresh the snapshot from the repository root with `make github-stars`, using your GitHub CLI session, then rebuild with `make site`. Only the repository URL, count and timestamp are stored; no credentials are shipped.

The browser caches public API metadata in `sessionStorage` for 15 minutes, or 5 minutes after failure. Requests time out after 4 seconds. The site and diagrams remain functional without GitHub. Building the website neither changes repository visibility nor uploads code.

## Local icon library

`content/icons.json` selects 25 icons from the pinned `lucide-static` package. Run `npm ci` and `npm run icons` to regenerate `assets/icons.svg` and its license. The sprite is committed, so a normal website build needs no icon CDN or installed npm dependencies. Static controls and dynamically rendered capability cards use the same sprite. Azure and GitHub retain their brand assets; diagram connections are separate SVG geometry.

See the official [repository API](https://docs.github.com/en/rest/repos/repos#get-a-repository) and [public API rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).

## Sharing metadata and brand assets

`content/project.json` defines the public name, author, repository and website URL. The website reads its product version from the root `VERSION` file. Run `python3 scripts/site_metadata.py` after changing metadata. `make site` emits crawlable canonical, Open Graph, Twitter Card and SoftwareSourceCode metadata; no browser JavaScript is needed by crawlers.

`assets/social-card.png` is the 1200 × 630 website preview; `assets/github-preview.png` is the 1280 × 640 image for the repository's Social preview settings. Their SVG sources and favicon assets remain versioned. Regenerate PNGs with `npm ci --ignore-scripts` and `npm run brand`; GitHub Social preview is configured separately.

The default deployment URL is set in the public profile. Override it for another host with `GOLIAT_SITE_URL=https://example.com/nexus/ make site`. This changes canonical and image URLs without publishing or changing the code repository link. Publish `dist/`, which includes `.nojekyll` and relative paths supporting a repository subdirectory.


## GitHub stars

The website reads public `stars.json` from the data-only `github-stats` branch. `.github/workflows/stars.yml` refreshes it daily at 06:17 UTC and supports a manual run. This job runs only the metadata publisher and its tests: no application or Terraform build, Pages deployment, PAT or Azure credential is needed. Its short-lived `GITHUB_TOKEN` can write repository contents; the script only updates the dedicated branch and never force-pushes. `main` retains its PR checks.

The browser uses a 15-minute cache. It can fall back to the public GitHub API and the dated snapshot included with the website if the scheduled data is unavailable or older than 48 hours. Zero is a valid count; a failed request never becomes an invented zero. The tooltip shows when the displayed value was checked. GitHub can delay or disable scheduled workflows; use **Actions → Refresh public GitHub stars → Run workflow** to retry. Forks must update the website's repository URL and enable their own scheduled workflow. No token is shipped to the browser.
