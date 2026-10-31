.PHONY: check validate test fmt docs site site-check site-serve inventory images-check tfvars site-data

check:
	python3 scripts/site_metadata.py --check
	python3 scripts/render_tfvars.py --check
	python3 scripts/export_site_config.py --check
	./lz check --config environments --examples
	./lz check --config examples/demo --examples

validate:
	./lz validate --config environments --examples

tfvars:
	python3 scripts/render_tfvars.py
	./lz render --config environments --examples

test:
	python3 -m unittest discover -s tests -v
	node --test tests/application.test.mjs tests/portal-api.test.mjs apps/api/tests/*.test.mjs

images-check:
	sh scripts/check_images.sh

inventory:
	python3 scripts/terraform_inventory.py

fmt:
	terraform fmt -recursive -check -diff modules stacks terraform environments examples/demo

docs:
	python3 scripts/render_document.py

site:
	python3 scripts/build_site.py

site-data:
	python3 scripts/export_site_config.py

site-check:
	node --check site/app.js
	node --check site/diagram-viewer.js
	node --check site/lab.js
	node --test tests/lab.test.mjs
	node --test tests/site-contract.test.mjs tests/github-stars.test.mjs
	python3 scripts/check_site.py

site-serve: site
	python3 -m http.server 8765 --bind 127.0.0.1 --directory dist

.PHONY: publication-check prepare-github
publication-check:
	python3 scripts/check_publication.py --history

prepare-github:
	python3 scripts/prepare_github.py

.PHONY: icons github-stars
icons:
	npm run icons

github-stars:
	python3 scripts/refresh_github_stars.py

.PHONY: workflows-check artifacts-check wiki-check
workflows-check:
	.lz/security-tools/actionlint
	shellcheck scripts/check_images.sh .githooks/pre-push

artifacts-check:
	python3 scripts/check_publication.py --history --artifacts dist

wiki-check:
	python3 scripts/check_wiki.py
