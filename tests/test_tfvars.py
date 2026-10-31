import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from product.cli import Deployment, configure, parser
from product.config import ConfigError, ROOT, STAGES, normalize, read_config
from test_product import raw_config


class TerraformVariablesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)

    def test_native_example_and_legacy_json_are_equivalent(self):
        self.assertEqual(read_config(ROOT / "examples/shared.auto.tfvars.json", examples=True),
                         read_config(ROOT / "examples/shared.json", examples=True))
        with self.assertRaises(ConfigError):
            read_config(ROOT / "examples/shared.auto.tfvars.json")

    def test_stage_contract_is_not_accepted_as_user_configuration(self):
        path = self.path / "inputs.auto.tfvars.json"
        path.write_text(json.dumps({"config": raw_config(), "platform": {"fake": True}}))
        with self.assertRaisesRegex(ConfigError, "contratos"):
            read_config(path)

    @patch("product.cli.execute")
    def test_configure_creates_native_and_legacy_formats_that_round_trip(self, run):
        cfg = raw_config()
        run.return_value = Mock(stdout=json.dumps({"id": cfg["subscription_id"], "tenantId": cfg["tenant_id"], "user": {"name": "ops@unit.test"}}))
        for filename in ("shared.auto.tfvars.json", "shared.json"):
            path = self.path / filename
            args = parser().parse_args(["configure", "--name", "acme", "--operator-ip", "8.8.8.8/32", "--operator-object-id", cfg["operator_object_id"], "--alert-email", "ops@unit.test", "--output", str(path)])
            configure(args)
            written = json.loads(path.read_text())
            self.assertEqual("config" in written, filename.endswith(".tfvars.json"))
            self.assertEqual(read_config(path)["name"], "acme")

    @patch("product.cli.execute")
    def test_configure_does_not_write_json_disguised_as_hcl(self, run):
        args = parser().parse_args(["configure", "--name", "acme", "--operator-ip", "8.8.8.8/32", "--alert-email", "ops@unit.test", "--output", str(self.path / "shared.auto.tfvars")])
        with self.assertRaisesRegex(ConfigError, "JSON"):
            configure(args)
        run.assert_not_called()

    def test_prepare_migrates_only_managed_inputs_and_preserves_state(self):
        deployment = Deployment(normalize(raw_config()))
        deployment.path = self.path / "deployment"
        for stage in STAGES:
            directory = deployment.path / "stacks" / stage
            directory.mkdir(parents=True)
            (directory / "inputs.tfvars.json").write_text('{"old": true}')
            (directory / "terraform.tfstate").write_text('state-must-survive')
        deployment.prepare()
        for stage in STAGES:
            directory = deployment.path / "stacks" / stage
            self.assertFalse((directory / "inputs.tfvars.json").exists())
            self.assertEqual((directory / "terraform.tfstate").read_text(), 'state-must-survive')
            inputs = json.loads((directory / "inputs.auto.tfvars.json").read_text())
            self.assertEqual(inputs["config"], deployment.cfg)
            self.assertEqual((directory / "inputs.auto.tfvars.json").stat().st_mode & 0o777, 0o600)
            if stage in ("dev", "prod"):
                self.assertEqual(inputs["environment"], stage)

    @unittest.skipUnless(shutil.which("terraform"), "Terraform no está instalado")
    def test_terraform_loads_auto_file_without_var_file_argument(self):
        # Use an isolated module without providers or Azure access.
        (self.path / "main.tf").write_text('variable "config" { type = any }\n')
        (self.path / "inputs.auto.tfvars.json").write_text((ROOT / "examples/shared.auto.tfvars.json").read_text())
        process = subprocess.run(["terraform", f"-chdir={self.path}", "console"], input='var.config.environments.prod.sample.api_min_replicas\n', text=True, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), "2")
