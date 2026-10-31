#!/usr/bin/env python3
"""Publish only presentation fields from the versioned product/demo HCL presets."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from product.config import read_config, FEATURES

DESTINATION = ROOT / "site/content/configuration.json"
SOURCES = ["VERSION", "terraform/common.tf", "docs/INVENTARIO_TERRAFORM.json", "docs/VERSIONES.json", *[f"{directory}/{name}.tfvars" for directory in ("environments", "examples/demo") for name in ("common", "dev", "prod")]]


def fingerprints():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def catalogue():
    inventory = json.loads((ROOT / "docs/INVENTARIO_TERRAFORM.json").read_text())
    presets = {}
    for name, directory, evidence in (("product", "environments", "shared"), ("demo", "examples/demo", "demo")):
        cfg = read_config(ROOT / directory, examples=True)
        environments = {}
        for env, settings in cfg["environments"].items():
            environments[env] = {key: settings[key] for key in ("zone_redundancy", "deploy_demo", "network", "sample", "cosmosdb_config", "storage", "functions", "web", "web_portals", *FEATURES)}
        presets[name] = {"name": cfg["name"], "directory": directory, "location": cfg["location"], "budget_amount": cfg["operations"]["budget_amount"], "public_entrypoint": cfg["public_entrypoint"], "environments": environments,
                         "inventory": {stage: inventory[evidence][stage]["total"] for stage in ("foundation", "platform", "dev", "prod", "edge")}, "total": inventory[evidence]["total"]}
    terraform = (ROOT / "terraform/common.tf").read_text()
    return {"version": (ROOT / "VERSION").read_text().strip(), "provider_version": re.search(r'azurerm\s*=\s*\{[^}]*version\s*=\s*"=\s*([0-9.]+)"', terraform, re.S)[1], "terraform_required": re.search(r'required_version\s*=\s*"([^"]+)"', terraform)[1], "sources": fingerprints(), "presets": presets}


def verify():
    try:
        value = json.loads(DESTINATION.read_text())
        if value["sources"] != fingerprints():
            raise ValueError()
    except (OSError, KeyError, ValueError) as exc:
        raise SystemExit("La web está desincronizada con los tfvars/inventario. Ejecuta make site-data.") from exc
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="Recalcular con Terraform y exigir igualdad")
    modes.add_argument("--verify", action="store_true", help="Comprobar huellas sin necesitar Terraform")
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.check:
        if verify() != catalogue():
            raise SystemExit("Los datos de la web no coinciden con los tfvars. Ejecuta make site-data.")
    else:
        DESTINATION.write_text(json.dumps(catalogue(), indent=2, ensure_ascii=False) + "\n")
    print("Datos web sincronizados con environments/ y examples/demo/.")


if __name__ == "__main__":
    main()
