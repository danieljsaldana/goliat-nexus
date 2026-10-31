#!/usr/bin/env python3
"""Check the shipped website, examples, documentation and source links."""
import json
import os
import struct
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DIAGRAMS = json.loads((ROOT / "site/content/diagrams.json").read_text())
PUBLIC_TFVARS = {"examples/shared.auto.tfvars.json", *[f"{directory}/{name}.tfvars" for directory in ("environments", "examples/demo") for name in ("common", "dev", "prod")]}


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.ids = set()
        self.meta = {}
        self.relations = {}
        self.repositories = []

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == "meta":
            self.meta[attributes.get("property", attributes.get("name"))] = attributes.get("content")
        if tag == "link":
            self.relations[attributes.get("rel")] = attributes.get("href")
        if tag == "a" and "data-repository" in attributes:
            self.repositories.append(attributes.get("href"))
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        for key in ("href", "src"):
            if attributes.get(key):
                self.urls.append(attributes[key])


def main():
    documents = {}
    for directory in (DIST, DIST / "site", ROOT / "site"):
        for page in [directory / "index.html", *(directory / "docs").glob("*.html")]:
            document = Document()
            document.feed(page.read_text())
            documents[page.resolve()] = document
    names = [view["id"] for view in DIAGRAMS]
    assert len(names) == len(set(names)) and set(names) == {"overview", "network", "application", "deployment"}
    for name in names:
        for directory in (DIST, DIST / "site", ROOT / "site"):
            assert (directory / "diagrams" / f"{name}.html").is_file(), f"Falta el diagrama en {directory}"
    icon_manifest = json.loads((ROOT / "site/content/icons.json").read_text())
    sprite = (DIST / "assets/icons.svg").read_text()
    for identifier in icon_manifest["icons"]:
        assert f'id="{identifier}"' in sprite, f"Missing Lucide icon: {identifier}"
    assert (DIST / "assets/Lucide-LICENSE.txt").is_file()
    project = json.loads((ROOT / "site/content/project.json").read_text())
    base = (os.environ.get("GOLIAT_SITE_URL") or project["website"]).rstrip("/") + "/"
    for directory in (DIST, DIST / "site"):
        page = documents[(directory / "index.html").resolve()]
        assert page.meta["author"] == project["author"]["name"]
        assert page.relations["author"] == project["author"]["url"]
        assert page.relations["canonical"] == page.meta["og:url"] == base
        assert page.meta["og:image"] == page.meta["twitter:image"] == base + project["social_image"]
        assert page.meta["og:image:alt"] and page.meta["twitter:card"] == "summary_large_image"
        assert page.meta["og:image:width"] == "1200" and page.meta["og:image:height"] == "630"
        assert len(page.repositories) >= 3 and set(page.repositories) == {project["repository"]}
        assert (directory / "index.htm").read_bytes() == (directory / "index.html").read_bytes()
    for name, dimensions in (("social-card", (1200, 630)), ("github-preview", (1280, 640)), ("apple-touch-icon", (180, 180)), ("favicon-32", (32, 32))):
        content = (DIST / "assets" / (name + ".png")).read_bytes()
        assert content.startswith(b"\x89PNG\r\n\x1a\n") and struct.unpack(">II", content[16:24]) == dimensions
    for page, document in documents.items():
        for url in document.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc:
                continue
            target = (page.parent / unquote(parsed.path)).resolve() if parsed.path else page
            assert target.is_relative_to(DIST.resolve()) or target.is_relative_to((ROOT / "site").resolve()), f"Link fuera del artefacto: {url}"
            assert target.is_file(), f"Link inexistente: {page.name} -> {url}"
            if parsed.fragment and target in documents:
                assert parsed.fragment in documents[target].ids, f"Ancla inexistente: {url}"
    config = json.loads((ROOT / "examples/shared.json").read_text())
    assert json.loads((DIST / "examples/shared.json").read_text()) == config
    native_example = json.loads((ROOT / "examples/shared.auto.tfvars.json").read_text())
    assert native_example == {"config": config}, "Los dos formatos de ejemplo deben representar la misma configuración."
    assert json.loads((DIST / "examples/shared.auto.tfvars.json").read_text()) == native_example
    snapshot = json.loads((ROOT / "site/content/configuration.json").read_text())
    assert json.loads((DIST / "content/configuration.json").read_text()) == snapshot
    for environment in ("dev", "prod"):
        assert json.loads((DIST / "examples" / f"{environment}.json").read_text()) == snapshot["presets"]["demo"]["environments"][environment]
    for path in PUBLIC_TFVARS:
        assert (DIST / path).read_bytes() == (ROOT / path).read_bytes(), path
    evidence = json.loads((ROOT / "docs/INVENTARIO_TERRAFORM.json").read_text())["shared"]
    script = """import {resourceInventory} from './site/content/resources.js';
console.log(JSON.stringify(Object.fromEntries(['foundation','platform','dev','prod','edge'].map(stage=>[stage,resourceInventory.filter(i=>i.stage===stage).reduce((sum,i)=>sum+i.count,0)]))));"""
    catalog = json.loads(subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True).stdout)
    for stage, count in catalog.items():
        assert count == evidence[stage]["total"], f"Inventario desactualizado: {stage}"
    assert sum(catalog.values()) == evidence["total"]
    for diagram in names:
        html = (DIST / "diagrams" / f"{diagram}.html").read_text()
        specification = json.loads((ROOT / "site/diagrams" / f"{diagram}.json").read_text())
        for component in specification["components"]:
            assert f'data-node-id="{component["id"]}"' in html
    version = (ROOT / "VERSION").read_text().strip()
    assert snapshot["version"] == version
    assert f"NEXUS · v{version}" in (DIST / "index.html").read_text(), "El rótulo de versión no coincide con el producto."
    assert json.loads((ROOT / "docs/VERSIONES.json").read_text())["product"] == version
    for component in ("api", "functions", "portal", "certificates"):
        package = json.loads((ROOT / "apps" / component / "package.json").read_text())
        lock = json.loads((ROOT / "apps" / component / "package-lock.json").read_text())
        assert package["version"] == lock["version"] == lock["packages"][""]["version"] == version
    assert all(settings["sample"]["version"] == version for preset in snapshot["presets"].values() for settings in preset["environments"].values())

    for directory in (DIST, ROOT / "site"):
        assert not (directory / "downloads").exists(), "La web ya no distribuye archivos comprimidos."
        assert not any(path.suffix.lower() == ".zip" for path in directory.rglob("*")), "No se permiten ZIP en la web."
    document = (DIST / "index.html").read_text()
    assert 'id="view-config"' in document and 'id="download-config"' not in document
    assert 'data-product-version' not in document.split('<footer>', 1)[1], "La versión se muestra solo en la cabecera."
    print("Web verificada en / y /site/: enlaces, anclas, diagramas, perfiles y enlaces al código, sin ZIP.")


if __name__ == "__main__":
    main()
