#!/usr/bin/env python3
"""Build the static product website and its offline Archify diagrams."""
import importlib.util
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from site_metadata import project_profile, update_document

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
DIST = ROOT / "dist"
DIAGRAMS = json.loads((SITE / "content/diagrams.json").read_text())
PUBLIC_TFVARS = {"examples/shared.auto.tfvars.json", *[f"{directory}/{name}.tfvars" for directory in ("environments", "examples/demo") for name in ("common", "dev", "prod")]}


def render_diagrams(destination):
    node = shutil.which("node")
    if not node:
        raise SystemExit("La web necesita Node.js 22 o posterior para generar los diagramas.")
    renderer = SITE / "vendor/archify/renderers/architecture/render-architecture.mjs"
    translations = json.loads((SITE / "vendor/archify/es.json").read_text())
    with tempfile.TemporaryDirectory(prefix="goliat-nexus-diagrams-") as folder:
        temporary = Path(folder)
        for view in DIAGRAMS:
            name = view["id"]
            data = json.loads((SITE / "diagrams" / f"{name}.json").read_text())
            data["meta"]["translations"] = translations
            (temporary / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False))
            result = subprocess.run(
                [node, str(renderer), f"{name}.json", f"{name}.html"],
                cwd=temporary, text=True, capture_output=True, timeout=60,
                env={**os.environ, "ARCHIFY_UPDATE_CHECK_DISABLED": "1"},
            )
            if result.returncode:
                raise SystemExit(f"No se pudo generar {name}:\n{result.stderr}\n{result.stdout}")
            if result.stderr.strip():
                print(result.stderr.strip())
            document = (temporary / f"{name}.html").read_text()
            stationary_buttons = '<style data-product-interaction>.diagram-guide-action:hover,.diagram-guide-action:focus-visible{transform:none!important}</style>'
            (destination / f"{name}.html").write_text(document.replace("</head>", stationary_buttons + "</head>", 1))
            print(f"Diagrama generado: {name}.html")


def render_documentation(destination):
    spec = importlib.util.spec_from_file_location("document_renderer", ROOT / "scripts/render_document.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manual_path = module.main(destination / "FUNCIONAMIENTO.html")
    manual = manual_path.read_text()
    style = re.search(r"<style>(.*?)</style>", manual, re.S)[1]
    for file in (ROOT / "docs").iterdir():
        if file.is_file():
            shutil.copy2(file, destination / file.name)
    names = [file.stem for file in sorted((ROOT / "docs").glob("*.md"))]
    for name in names:
        if name == "FUNCIONAMIENTO":
            continue
        markdown = (ROOT / "docs" / f"{name}.md").read_text()
        body, navigation = module.render(markdown)
        title = markdown.splitlines()[0].removeprefix("# ")
        language = 'en' if name.endswith('.en') else 'es'
        document = f'<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{style}</style></head><body><main><div class="document-label">Goliat - Nexus</div><nav>{navigation}</nav>{body}</main></body></html>'
        (destination / f"{name}.html").write_text(document)
    for file in destination.glob("*.html"):
        document = file.read_text()
        for name in names:
            document = document.replace(f'href="{name}.md', f'href="{name}.html')
        for view in DIAGRAMS:
            name = view['id']
            document = document.replace(f'href="../site/diagrams/{name}.json"', f'href="../diagrams/{name}.html"')
        file.write_text(document)


def prepare_source_preview():
    """Keep /site/index.html functional when serving the repository root."""
    # Retire legacy generated downloads instead of preserving old release files.
    if (SITE / "downloads").exists():
        shutil.rmtree(SITE / "downloads")
    for name in ("docs", "examples", "environments", "licenses"):
        # Do not leave retired documents reachable in the source preview.
        if (SITE / name).exists():
            shutil.rmtree(SITE / name)
        shutil.copytree(DIST / name, SITE / name)
    for view in DIAGRAMS:
        name = view["id"]
        shutil.copy2(DIST / "diagrams" / f"{name}.html", SITE / "diagrams" / f"{name}.html")
    shutil.copy2(DIST / "diagrams/resources.html", SITE / "diagrams/resources.html")
    (SITE / "SOURCES.json").unlink(missing_ok=True)
    shutil.copy2(DIST / "index.htm", SITE / "index.htm")


def prepare_site_path_alias():
    """Also serve old /site/... links from the published static root."""
    entries = list(DIST.iterdir())
    alias = DIST / "site"
    alias.mkdir()
    for source in entries:
        if source.is_dir():
            shutil.copytree(source, alias / source.name)
        else:
            shutil.copy2(source, alias / source.name)


def main():
    subprocess.run(["python3", str(ROOT / "scripts/render_tfvars.py"), "--check"], check=True)
    subprocess.run(["python3", str(ROOT / "scripts/export_site_config.py"), "--verify"], check=True)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    for name in ('LICENSE', 'NOTICE', 'LICENSING.md'):
        shutil.copy2(ROOT / name, DIST / name)
    for name in ("index.html", "styles.css", "app.js", "lab.js", "github.js", "diagram-viewer.js", "NOTICE.md", "_headers"):
        shutil.copy2(SITE / name, DIST / name)
    shutil.copytree(SITE / "assets", DIST / "assets")
    if (SITE / "content").exists():
        shutil.copytree(SITE / "content", DIST / "content")
    # Version the module graph too, so new product data never uses old client code.
    for script, dependencies in (("lab.js", []), ("app.js", ["lab.js", "github.js", "diagram-viewer.js", "content/architecture-explorer.js", "content/resources.js", "content/capabilities.js", "content/deployment-model.mjs"])):
        text = (DIST / script).read_text()
        for name in dependencies:
            digest = hashlib.sha256((DIST / name).read_bytes()).hexdigest()[:12]
            text = text.replace(f"'./{name}'", f"'./{name}?v={digest}'")
        (DIST / script).write_text(text)
    index = update_document((DIST / "index.html").read_text(), project_profile())
    for name in ("styles.css", "app.js"):
        digest = hashlib.sha256((DIST / name).read_bytes()).hexdigest()[:12]
        index = index.replace(f'="{name}"', f'="{name}?v={digest}"')
    (DIST / "index.html").write_text(index)
    (DIST / "index.htm").write_text(index)
    for name in ("diagrams", "docs", "licenses"):
        (DIST / name).mkdir()
    (DIST / ".nojekyll").write_text("")
    render_diagrams(DIST / "diagrams")
    # Old bookmarks resolve to the compact architecture; no resource diagram is shipped.
    (DIST / "diagrams/resources.html").write_text('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=overview.html"><title>Arquitectura de Goliat Nexus</title></head><body><p><a href="overview.html">Ver la arquitectura hub &amp; spokes</a></p></body></html>')
    render_documentation(DIST / "docs")
    public_files = PUBLIC_TFVARS | {"examples/shared.json", "examples/README.md", "examples/demo/README.md", "environments/README.md", "examples/README.es.md", "examples/demo/README.es.md", "environments/README.es.md"}
    for relative in sorted(public_files):
        target = DIST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    config = json.loads((SITE / "content/configuration.json").read_text())
    for environment, settings in config["presets"]["demo"]["environments"].items():
        (DIST / "examples" / f"{environment}.json").write_text(json.dumps(settings, indent=2) + "\n")
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "upstream.json"):
        shutil.copy2(SITE / "vendor/archify" / name, DIST / "licenses" / f"archify-{name}")
    shutil.copy2(SITE / "REFERENCE-LICENSE", DIST / "licenses/REFERENCE-LICENSE")
    prepare_source_preview()
    prepare_site_path_alias()
    print(f"Web estática preparada: {DIST}")


if __name__ == "__main__":
    main()
