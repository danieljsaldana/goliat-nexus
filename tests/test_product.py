import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from product.config import ConfigError, ROOT, backend_config, normalize
from product.cli import Deployment, fixture_contracts, local_lock


def raw_config():
    data = json.loads((ROOT / "examples/shared.json").read_text())
    data.update(subscription_id="11111111-1111-4111-8111-111111111111",
                tenant_id="22222222-2222-4222-8222-222222222222",
                operator_object_id="33333333-3333-4333-8333-333333333333",
                operator_ip_ranges=["8.8.8.8/32"])
    data["operations"]["alert_emails"] = ["ops@unit.test"]
    # Existing core-stage fixtures use the private model; edge is exercised separately.
    data["public_entrypoint"]["enabled"] = False
    return data


class ConfigurationTests(unittest.TestCase):
    def test_portal_map_accepts_custom_ids_and_empty_maps_without_adding_defaults(self):
        data = raw_config()
        data["environments"]["dev"]["web_portals"] = {"support": {}}
        data["environments"]["prod"]["web_portals"] = {}
        cfg = normalize(data)
        self.assertEqual(cfg["environments"]["dev"]["web_portals"], {"support": {"view": "tenant"}})
        self.assertEqual(cfg["environments"]["prod"]["web_portals"], {})
        self.assertEqual(data["environments"]["dev"]["web_portals"], {"support": {}})

    def test_portal_map_rejects_invalid_ids_views_and_unknown_fields(self):
        for portals in ([], {"Bad Name": {}}, {"bad-": {}}, {"a" * 31: {}}, {"support": None}, {"support": {"view": "owner"}}, {"support": {"enabled": True}}):
            with self.subTest(portals=portals), self.assertRaises(ConfigError):
                data = raw_config()
                data["environments"]["dev"]["web_portals"] = portals
                normalize(data)

    def test_portals_require_their_private_secret_store(self):
        data = raw_config()
        env = data["environments"]["dev"]
        for key in tuple(env):
            if key.startswith("enable_"):
                env[key] = False
        with self.assertRaisesRegex(ConfigError, "requieren enable_key_vault"):
            normalize(data)
        env["web_portals"] = {}
        normalize(data)

    def test_storage_ip_singleton_and_deterministic_names(self):
        a = normalize(raw_config())
        b = normalize(raw_config())
        self.assertEqual(a["operator_ip_ranges"], ["8.8.8.8"])
        self.assertEqual(a["suffix"], b["suffix"])
        self.assertLessEqual(len("stlz" + a["suffix"]), 24)

    def test_environments_share_backend_but_not_state_keys(self):
        cfg = normalize(raw_config())
        dev, prod = backend_config(cfg, "dev"), backend_config(cfg, "prod")
        self.assertEqual(dev["storage_account_name"], prod["storage_account_name"])
        self.assertNotEqual(dev["key"], prod["key"])
        self.assertTrue(dev["use_azuread_auth"])
        self.assertNotEqual(cfg["environments"]["dev"]["suffix"], cfg["environments"]["prod"]["suffix"])

    def test_examples_cannot_be_deployed(self):
        example = json.loads((ROOT / "examples/shared.json").read_text())
        with self.assertRaises(ConfigError):
            normalize(example)
        normalize(example, examples=True)

    def test_rejects_unknown_keys(self):
        data = raw_config()
        data["subscription"] = data["subscription_id"]
        with self.assertRaises(ConfigError):
            normalize(data)

    def test_rejects_overlapping_vnets(self):
        data = raw_config()
        data["environments"]["dev"]["network"]["vnet_cidr"] = data["network"]["hub_cidr"]
        with self.assertRaises(ConfigError):
            normalize(data)

    def test_rejects_subnet_outside_vnet(self):
        data = raw_config()
        data["environments"]["dev"]["network"]["apps_subnet_cidr"] = "10.30.0.0/23"
        with self.assertRaises(ConfigError):
            normalize(data)

    def test_rejects_broad_or_private_bootstrap_ips(self):
        for ip in ("0.0.0.0/0", "8.0.0.0/8", "8.8.8.8/31", "10.1.2.3/32", "203.0.113.10/32", "2001:db8::/32"):
            with self.subTest(ip=ip), self.assertRaises(ConfigError):
                data = raw_config()
                data["operator_ip_ranges"] = [ip]
                normalize(data)

    def test_rejects_small_or_overlapping_subnets(self):
        for key, value in (("apps_subnet_cidr", "10.20.0.0/27"), ("management_subnet_cidr", "10.0.0.0/24")):
            with self.subTest(key=key), self.assertRaises(ConfigError):
                data = raw_config()
                target = data["network"] if key == "management_subnet_cidr" else data["environments"]["dev"]["network"]
                target[key] = value
                normalize(data)

    def test_rejects_wildcard_egress(self):
        data = raw_config()
        data["environments"]["dev"]["additional_https_fqdns"] = ["*"]
        with self.assertRaises(ConfigError):
            normalize(data)

    def test_rejects_invalid_types(self):
        for key, value in (("tags", []), ("network", []), ("operator_ip_ranges", "8.8.8.8")):
            with self.subTest(key=key), self.assertRaises(ConfigError):
                data = raw_config()
                data[key] = value
                normalize(data)

    def test_environment_types_and_overlapping_spokes_are_rejected(self):
        for field, value in (("deploy_demo", "false"), ("zone_redundancy", 1), ("sample", [])):
            with self.subTest(field=field), self.assertRaises(ConfigError):
                data = raw_config()
                data["environments"]["dev"][field] = value
                normalize(data)
        data = raw_config()
        data["environments"]["prod"]["network"] = data["environments"]["dev"]["network"].copy()
        with self.assertRaises(ConfigError):
            normalize(data)

    def test_normalization_does_not_mutate_input_or_other_environment(self):
        data = raw_config()
        before = json.dumps(data, sort_keys=True)
        result = normalize(data)
        result["environments"]["dev"]["sample"]["api_min_replicas"] = 1
        self.assertEqual(json.dumps(data, sort_keys=True), before)
        self.assertEqual(result["environments"]["prod"]["sample"]["api_min_replicas"], 2)

    def test_same_oidc_subject_cannot_publish_to_both_environments(self):
        data = raw_config()
        for settings in data["environments"].values():
            settings.update(github_repository="example/product", github_environment="shared")
        with self.assertRaises(ConfigError):
            normalize(data)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = normalize(raw_config())
        self.deployment = Deployment(self.cfg)
        self.deployment.path = Path(self.tmp.name) / "deployment"
        self.deployment.prepare()
        self.foundation = self.deployment.path / "stacks/foundation"

    def test_render_preserves_state_and_backend(self):
        (self.foundation / "terraform.tfstate").write_text('{"resources": [{"name":"state"}]}')
        (self.foundation / "backend.auto.tf").write_text("keep this backend")
        self.deployment.prepare()
        self.assertEqual((self.foundation / "backend.auto.tf").read_text(), "keep this backend")
        self.assertEqual(json.loads((self.foundation / "terraform.tfstate").read_text())["resources"][0]["name"], "state")

    def test_all_source_files_are_packaged(self):
        for source in (ROOT / "stacks/platform").glob("*.tf"):
            self.assertEqual(source.read_text(), (self.deployment.path / "stacks/platform" / source.name).read_text())

    def test_identity_change_is_rejected(self):
        self.deployment.cfg = {**self.cfg, "subscription_id": "44444444-4444-4444-8444-444444444444"}
        with self.assertRaises(ConfigError):
            self.deployment.prepare()

    def test_lock_prevents_two_local_deployments(self):
        with local_lock(self.deployment.path), self.assertRaises(ConfigError):
            with local_lock(self.deployment.path):
                self.fail("Lock should prevent concurrent work")

    def test_bootstrap_starts_local(self):
        self.deployment.remote_blob_exists = Mock(return_value=False)
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        self.deployment.tf.assert_called_once_with("foundation", "init", "-input=false")
        self.assertFalse((self.foundation / "backend.auto.tf").exists())

    def test_new_checkout_reconnects_existing_remote_state(self):
        self.deployment.remote_blob_exists = Mock(return_value=True)
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        self.assertTrue((self.foundation / "backend.auto.tf").exists())
        self.assertIn("-reconfigure", self.deployment.tf.call_args.args)

    def test_legacy_generated_backend_is_repaired_without_touching_state(self):
        (self.foundation / "backend.auto.tf").write_text('terraform { backend "azurerm" {} }\n')
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        self.assertEqual((self.foundation / "backend.auto.tf").read_text(), 'terraform {\n  backend "azurerm" {}\n}\n')
        self.assertIn("-reconfigure", self.deployment.tf.call_args.args)

    def test_failed_migration_retries_without_discarding_local_state(self):
        (self.foundation / "backend.auto.tf").write_text('terraform { backend "azurerm" {} }')
        (self.foundation / "terraform.tfstate").write_text('{"resources":[{"name":"state"}]}')
        self.deployment.wait_for_state_access = Mock()
        self.deployment.remote_blob_exists = Mock(return_value=False)
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        self.assertIn("-migrate-state", self.deployment.tf.call_args.args)
        self.assertTrue((self.foundation / "terraform.tfstate").exists())
        self.deployment.remote_blob_exists.assert_called_once_with(allow_missing_state=True)

    def test_lost_backend_metadata_cannot_overwrite_existing_remote_state(self):
        (self.foundation / "backend.auto.tf").write_text('terraform { backend "azurerm" {} }')
        (self.foundation / "terraform.tfstate").write_text('{"resources":[{"name":"stale-local"}]}')
        self.deployment.wait_for_state_access = Mock()
        self.deployment.remote_blob_exists = Mock(return_value=True)
        self.deployment.tf = Mock()
        with self.assertRaisesRegex(ConfigError, "no sobrescribir"):
            self.deployment.init("foundation")
        self.deployment.tf.assert_not_called()

    def test_initial_migration_refuses_a_remote_state_without_changing_backend(self):
        self.deployment.wait_for_state_access = Mock()
        self.deployment.remote_blob_exists = Mock(return_value=True)
        self.deployment.tf = Mock()
        with self.assertRaises(ConfigError):
            self.deployment.migrate_foundation()
        self.assertFalse((self.foundation / "backend.auto.tf").exists())
        self.deployment.tf.assert_not_called()

    def test_initial_migration_checks_remote_before_copy(self):
        self.deployment.wait_for_state_access = Mock()
        self.deployment.remote_blob_exists = Mock(return_value=False)
        self.deployment.tf = Mock()
        self.deployment.migrate_foundation()
        self.assertIn("-migrate-state", self.deployment.tf.call_args.args)
        self.assertEqual(self.deployment.remote_blob_exists.call_count, 2)

    @unittest.skipUnless(shutil.which("terraform"), "Terraform no está instalado")
    def test_generated_backend_is_valid_terraform_hcl(self):
        self.deployment.remote_blob_exists = Mock(return_value=True)
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        result = subprocess.run(["terraform", "fmt", "-check", str(self.foundation / "backend.auto.tf")], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_remote_backend_is_not_overwritten_by_old_local_backup(self):
        (self.foundation / "backend.auto.tf").write_text('terraform { backend "azurerm" {} }')
        (self.foundation / "terraform.tfstate").write_text('{"resources":[{"name":"old"}]}')
        metadata = self.foundation / ".terraform"
        metadata.mkdir()
        (metadata / "terraform.tfstate").write_text('{"backend":{"type":"azurerm"}}')
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        self.assertIn("-reconfigure", self.deployment.tf.call_args.args)
        self.assertNotIn("-migrate-state", self.deployment.tf.call_args.args)

    def test_inputs_use_real_previous_stage_outputs(self):
        contract = {"actual": "live Azure output"}
        self.deployment.inputs("platform", contract)
        inputs = json.loads((self.deployment.path / "stacks/platform/inputs.auto.tfvars.json").read_text())
        self.assertEqual(inputs["foundation"], contract)

    def test_remote_backend_accepts_empty_local_file_after_migration(self):
        (self.foundation / "backend.auto.tf").write_text('terraform { backend "azurerm" {} }')
        (self.foundation / "terraform.tfstate").write_text("")
        metadata = self.foundation / ".terraform"
        metadata.mkdir()
        (metadata / "terraform.tfstate").write_text('{"backend":{"type":"azurerm"}}')
        self.deployment.tf = Mock()
        self.deployment.init("foundation")
        self.assertIn("-reconfigure", self.deployment.tf.call_args.args)
        self.assertNotIn("-migrate-state", self.deployment.tf.call_args.args)

    def test_corrupt_local_bootstrap_state_blocks_backend_change(self):
        (self.foundation / "backend.auto.tf").write_text('terraform { backend "azurerm" {} }')
        state = self.foundation / "terraform.tfstate"
        state.write_text('{"resources":')
        self.deployment.tf = Mock()
        with self.assertRaisesRegex(ConfigError, "estado local no es JSON válido"):
            self.deployment.init("foundation")
        self.deployment.tf.assert_not_called()
        self.assertEqual(state.read_text(), '{"resources":')

    def test_deploy_is_ordered_and_migrates_before_platform(self):
        calls = []
        d = self.deployment
        d.register_providers = Mock()
        d.guard_legacy_platform = Mock()
        d.upstream = Mock(side_effect=lambda stage: calls.append(("upstream", stage)))
        d.init = Mock(side_effect=lambda stage: calls.append(("init", stage)))
        d.tf = Mock(side_effect=lambda stage, *args, **kwargs: calls.append((args[0], stage)))
        d.approve_plan = Mock()
        d.migrate_foundation = Mock(side_effect=lambda: calls.append(("migrate", "foundation")))
        with patch("product.cli.wait_for_applications"), patch("product.cli.publish_application_code"), patch("product.cli.example_requirements"), patch("product.cli.publish_example", side_effect=lambda *_: calls.append(("publish", "sample"))), patch("product.cli.sync_secrets", side_effect=lambda *_: calls.append(("sql", "sample"))):
            d.deploy("all")
        self.assertLess(calls.index(("apply", "platform")), calls.index(("publish", "sample")))
        self.assertLess(calls.index(("sql", "sample")), calls.index(("apply", "dev")))
        self.assertLess(calls.index(("migrate", "foundation")), calls.index(("apply", "platform")))
        self.assertEqual([stage for action, stage in calls if action == "apply"], list(("foundation", "platform", "dev", "prod")))
        self.assertNotIn("-auto-approve", str(d.tf.call_args_list))
        self.assertEqual([stage for action, stage in calls if action == "plan"], ["foundation", "platform", "dev", "prod"])
        for call in d.tf.call_args_list:
            if call.args[1] == "apply":
                self.assertEqual(call.args[2:], ("-input=false", "deployment.tfplan"))

    def test_dev_only_apply_leaves_prod_untouched(self):
        d = self.deployment
        d.register_providers = Mock()
        d.guard_legacy_platform = Mock()
        d.upstream = Mock(return_value=None)
        d.init = Mock()
        d.tf = Mock()
        d.approve_plan = Mock()
        with patch("product.cli.wait_for_applications"), patch("product.cli.publish_application_code"), patch("product.cli.example_requirements"), patch("product.cli.publish_example") as publish, patch("product.cli.sync_secrets") as sql:
            d.deploy("dev")
        self.assertEqual([call.args[0] for call in d.tf.call_args_list], ["dev", "dev"])
        self.assertEqual(publish.call_args.args[0].cfg["environment"], "dev")
        self.assertEqual(sql.call_args.args[0].cfg["environment"], "dev")

    def test_older_cosmos_protocol_is_not_upgraded_implicitly(self):
        self.deployment.tf = Mock(side_effect=[subprocess.CompletedProcess([], 0, 'module.cosmos["dev"].module.velia.azurerm_cosmosdb_account.db[0]'), subprocess.CompletedProcess([], 0, json.dumps({"resources":[{"type":"azurerm_cosmosdb_account","instances":[{"attributes":{"mongo_server_version":"4.2"}}]}]}))])
        with self.assertRaisesRegex(ConfigError, "no cambia el protocolo"):
            self.deployment.guard_legacy_platform()

    def test_each_environment_reads_platform_and_has_its_own_release_directory(self):
        d = self.deployment
        _, platform = fixture_contracts(self.cfg)
        d.init = Mock()
        d.output = Mock(return_value=platform)
        for environment in ("dev", "prod"):
            self.assertEqual(d.upstream(environment), platform["environments"][environment])
        self.assertEqual([call.args[0] for call in d.output.call_args_list], ["platform", "platform"])
        self.assertNotEqual(d.environment_view("dev").path, d.environment_view("prod").path)

    @patch("product.cli.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("20.1.1.1", 443))])
    @patch("product.cli.shutil.which", return_value="/mock/tool")
    @patch("product.cli.execute")
    def test_refuses_private_state_switch_from_public_network(self, run, _which, _dns):
        run.side_effect = [subprocess.CompletedProcess([], 0, '{"terraform_version":"1.17.0"}'),
                           subprocess.CompletedProcess([], 0, json.dumps({"id": self.cfg["subscription_id"], "tenantId": self.cfg["tenant_id"]}))]
        self.deployment.cfg = {**self.cfg, "state_access": "private"}
        with self.assertRaisesRegex(ConfigError, "No se cerrará"):
            self.deployment.preflight()

    def test_validation_contracts_have_no_access_keys(self):
        serialized = json.dumps(fixture_contracts(self.cfg)).lower()
        self.assertNotIn("access_key", serialized)
        self.assertNotIn("password", serialized)

    @patch("product.cli.execute")
    def test_existing_account_without_state_requires_recovery(self, run):
        run.side_effect = [subprocess.CompletedProcess([], 0, '{}'),
                           subprocess.CompletedProcess([], 0, '{"exists":false}')]
        with self.assertRaisesRegex(ConfigError, "Restaura el estado local"):
            self.deployment.remote_blob_exists()

    @patch("product.cli.execute")
    def test_permission_denied_is_not_treated_as_missing_backend(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, '', 'AuthorizationFailed')
        with self.assertRaisesRegex(ConfigError, "AuthorizationFailed"):
            self.deployment.remote_blob_exists()

    def test_failed_access_check_does_not_switch_backend(self):
        self.deployment.wait_for_state_access = Mock(side_effect=ConfigError("403"))
        self.deployment.tf = Mock()
        with self.assertRaises(ConfigError):
            self.deployment.migrate_foundation()
        self.assertFalse((self.foundation / "backend.auto.tf").exists())
        self.deployment.tf.assert_not_called()

    @patch("product.cli.execute")
    def test_json_output_suppresses_initialization_chatter(self, run):
        self.deployment.quiet = True
        self.deployment.tf("foundation", "init")
        self.assertTrue(run.call_args.kwargs["capture"])

    @patch("product.cli.execute")
    def test_provider_registration_is_only_needed_for_unregistered_namespaces(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "Registered\n")
        self.deployment.register_providers("foundation")
        self.assertEqual(run.call_count, 1)
        self.assertIn("show", run.call_args.args[0])
        run.reset_mock()
        run.side_effect = [subprocess.CompletedProcess([], 0, "NotRegistered\n"), subprocess.CompletedProcess([], 0, "")]
        self.deployment.register_providers("foundation")
        self.assertIn("register", run.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
