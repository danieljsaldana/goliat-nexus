import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from product.cli import Deployment, configure, parser
from product.config import ConfigError, ROOT, read_config
from product.tfvars import read_environment_directory, write_environment_directory
from test_product import raw_config


@unittest.skipUnless(shutil.which("terraform"), "Terraform no está instalado")
class EnvironmentFilesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def test_product_dev_and_prod_are_separate_files_with_component_flags(self):
        cfg = read_config(ROOT / "environments", examples=True)
        self.assertEqual(set(cfg["environments"]), {"dev", "prod"})
        self.assertFalse(any(env["deploy_demo"] for env in cfg["environments"].values()))
        self.assertEqual(cfg, read_config(ROOT / "environments/dev.tfvars", examples=True))
        with self.assertRaises(ConfigError):
            read_config(ROOT / "environments")

    def test_demo_is_a_distinct_deployment_with_reference_apps(self):
        product = read_config(ROOT / "environments", examples=True)
        demo = read_config(ROOT / "examples/demo", examples=True)
        self.assertNotEqual(product["suffix"], demo["suffix"])
        self.assertTrue(all(env["deploy_demo"] for env in demo["environments"].values()))
        self.assertEqual(demo["environment"], "shared")

    def test_native_hcl_round_trip_preserves_literal_strings_and_settings(self):
        cfg = raw_config()
        cfg["tags"]["Literal"] = '${preserve} %{literal} "quoted"'
        path = self.directory / "environments"
        write_environment_directory(path, cfg)
        self.assertEqual(read_environment_directory(path), cfg)
        with self.assertRaises(ConfigError):
            write_environment_directory(path, cfg)
        (path / "prod.tfvars").unlink()
        with self.assertRaisesRegex(ConfigError, "prod.tfvars"):
            read_environment_directory(path)

    def test_unrecognized_tfvars_variables_do_not_get_silently_ignored(self):
        path = self.directory / "environments"
        write_environment_directory(path, raw_config())
        with (path / "dev.tfvars").open("a") as file:
            file.write('\nmisspelled_variable = true\n')
        with self.assertRaisesRegex(ConfigError, "undeclared"):
            read_environment_directory(path)

    @patch("product.cli.execute")
    def test_configure_creates_three_operational_files_from_azure_session(self, run):
        cfg = raw_config()
        run.return_value = Mock(stdout=json.dumps({"id": cfg["subscription_id"], "tenantId": cfg["tenant_id"], "user": {"name": "ops@unit.test"}}))
        path = self.directory / "environments"
        args = parser().parse_args(["configure", "--name", "acme", "--operator-ip", "8.8.8.8/32", "--operator-object-id", cfg["operator_object_id"], "--alert-email", "ops@unit.test", "--output-dir", str(path)])
        configure(args)
        actual = read_config(path)
        self.assertFalse(any(env["deploy_demo"] for env in actual["environments"].values()))
        self.assertEqual({p.name for p in path.iterdir()}, {"common.tfvars", "dev.tfvars", "prod.tfvars"})
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in path.iterdir()))

    def test_foundation_and_platform_do_not_publish_application_code(self):
        d = Deployment(read_config(ROOT / "environments", examples=True))
        d.path = self.directory / "deployment"
        d.register_providers = Mock()
        d.guard_legacy_platform = Mock()
        d.upstream = Mock(return_value=None)
        d.init = Mock()
        d.tf = Mock()
        d.migrate_foundation = Mock()
        with patch("product.cli.example_requirements") as requirements, patch("product.cli.publish_example") as publish, patch("product.cli.sync_secrets") as sql:
            d.deploy("platform", yes=True)
        requirements.assert_not_called()
        publish.assert_not_called()
        sql.assert_not_called()
        self.assertEqual([call.args[0] for call in d.tf.call_args_list], ["platform", "platform"])
