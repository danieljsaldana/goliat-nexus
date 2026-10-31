#!/usr/bin/env python3
"""Keep the native Terraform JSON example in sync with the base configuration."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = ROOT / "examples/shared.json"
    destination = ROOT / "examples/shared.auto.tfvars.json"
    rendered = json.dumps({"config": json.loads(source.read_text())}, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not destination.exists() or destination.read_text() != rendered:
            raise SystemExit("Ejemplo auto.tfvars desactualizado: ejecuta make tfvars.")
        print("Ejemplo shared.auto.tfvars.json sincronizado.")
    else:
        destination.write_text(rendered)
        print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
