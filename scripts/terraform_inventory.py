#!/usr/bin/env python3
"""Extract reference counts from real mock-plan JSON after make validate."""
import json
import subprocess
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNS = {"foundation":"state_security", "platform":"private_platform", "dev":"private_application", "prod":"private_application", "edge":"waf_public_security"}


def main():
    sys.path.insert(0, str(ROOT))
    from product.config import read_config
    cfg = read_config(ROOT / "environments", examples=True)
    result = {"product_version":(ROOT/"VERSION").read_text().strip(), "source":"terraform test -json -verbose with mock_provider azurerm + azuread; no consulta Azure/Entra"}
    result["demo"] = {}
    for profile in ("shared",):
        result[profile] = {}
        for stage, run in RUNS.items():
            directory = ROOT/".lz/validation"/f"{cfg['name']}-{profile}"/"stacks"/stage
            command = ["terraform", f"-chdir={directory}", "test", "-json", "-verbose"]
            process = subprocess.run(command, text=True, capture_output=True, check=True)
            plans = [event for line in process.stdout.splitlines() if (event:=json.loads(line)).get("type")=="test_plan"]
            selected = next(event for event in plans if event["@testrun"]==run)
            resources = [resource for resource in selected["test_plan"]["resource_changes"] if resource["mode"]=="managed"]
            result[profile][stage] = {"total":len(resources), "types":dict(sorted(Counter(resource["type"] for resource in resources).items()))}
            if stage in ("dev", "prod"):
                demo = next(event for event in plans if event["@testrun"] == "private_application")
                demo_resources = [resource for resource in demo["test_plan"]["resource_changes"] if resource["mode"] == "managed"]
                result["demo"][stage] = {"total": len(demo_resources), "types": dict(sorted(Counter(resource["type"] for resource in demo_resources).items()))}
            else:
                result["demo"][stage] = result[profile][stage]
        result[profile]["total"] = sum(result[profile][stage]["total"] for stage in RUNS)
    result["demo"]["total"] = sum(result["demo"][stage]["total"] for stage in RUNS)
    (ROOT/"docs/INVENTARIO_TERRAFORM.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    rows = [{"stage":stage,"type":kind,"count":count} for stage in RUNS for kind,count in result["shared"][stage]["types"].items()]
    (ROOT/"site/content/resources.js").write_text("export const resourceInventory = " + json.dumps(rows,indent=2) + ";\n")
    print({profile:{key:value["total"] if isinstance(value,dict) else value for key,value in result[profile].items()} for profile in ("shared",)})


if __name__ == "__main__":
    main()
