import json
import tempfile
import signal
import socket
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from product.config import ConfigError, normalize
from product.cli import Deployment
from product.identity import ACTIVE, InstallationIdentity, TemporaryIdentity, authenticated_backend, command_environment, recover_abandoned, run_terraform
from test_product import raw_config


class FakeIdentity(TemporaryIdentity):
    def create(self):
        self.started = True
        self.auth.mkdir(parents=True)
        self.record.update(client_id="44444444-4444-4444-8444-444444444444", app_object_id="55555555-5555-4555-8555-555555555555", principal_id="66666666-6666-4666-8666-666666666666")
        (self.auth / "identity.pfx").write_bytes(b"unit-private-key")
        self.save()


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.cfg = normalize(raw_config())
        self.identity = FakeIdentity(self.cfg, directory=self.folder.name)

    def test_failure_retires_identity_without_changing_operator_authentication(self):
        self.identity.cleanup = Mock()
        with self.assertRaisesRegex(RuntimeError, "deployment failed"):
            with self.identity:
                original = {"AZURE_CONFIG_DIR": "/operator", "ARM_CLIENT_SECRET": "inherited-secret", "ARM_USE_OIDC": "true"}
                tf = command_environment(["terraform", "plan"], original)
                cli = command_environment(["az", "acr", "login"], original)
                self.assertEqual(tf["AZURE_CONFIG_DIR"], self.identity.operator_config)
                self.assertEqual(cli["AZURE_CONFIG_DIR"], str(self.identity.auth / "azure"))
                self.assertNotIn("ARM_CLIENT_SECRET", tf)
                self.assertNotIn("ARM_USE_OIDC", tf)
                self.assertNotIn("inherited-secret", json.dumps(tf))
                backend = authenticated_backend(self.cfg, "dev")
                self.assertFalse(backend["use_cli"])
                self.assertIn("client_certificate_path", backend)
                self.assertNotIn("unit-private-key", json.dumps(backend))
                raise RuntimeError("deployment failed")
        self.identity.cleanup.assert_called_once()
        self.assertIsNone(ACTIVE.get())
        self.assertFalse(self.identity.auth.exists())

    def test_cleanup_failure_removes_local_keys_and_reports_pending_work(self):
        self.identity.cleanup = Mock(side_effect=ConfigError("cleanup pending"))
        with self.assertRaisesRegex(ConfigError, "cleanup pending"):
            with self.identity:
                pass
        self.assertFalse(self.identity.auth.exists())
        self.assertIsNone(ACTIVE.get())

    def test_create_failure_still_runs_cleanup(self):
        original = self.identity.create
        def fail():
            original()
            raise ConfigError("grant failed")
        self.identity.create = fail
        self.identity.cleanup = Mock()
        with self.assertRaisesRegex(ConfigError, "grant failed"):
            with self.identity:
                self.fail("not entered")
        self.identity.cleanup.assert_called_once()
        self.assertFalse(self.identity.auth.exists())

    def test_foreign_application_is_never_deleted_by_a_forged_journal(self):
        self.identity.create()
        self.identity.az = Mock(return_value={"id": "foreign", "displayName": "business-api", "tags": []})
        self.identity.rest = Mock()
        with self.assertRaisesRegex(ConfigError, "no coincide"):
            self.identity.cleanup()
        self.identity.rest.assert_not_called()
        self.assertFalse(any("delete" in call.args for call in self.identity.az.call_args_list))

    def test_cleanup_is_idempotent_after_azure_objects_are_gone(self):
        self.identity.create()
        self.identity.az = Mock(return_value=None)
        self.identity.cleanup()
        self.identity.cleanup()
        self.assertEqual(json.loads((self.identity.path / "run.json").read_text())["status"], "clean")
        self.assertFalse(self.identity.auth.exists())


class InstallationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.cfg = normalize(raw_config())
        self.identity = InstallationIdentity(self.cfg, directory=self.folder.name)
        self.identity.record.update(installation_ready=True, status="installed", client_id="client",
            app_object_id="application", principal_id="principal", key_id="this-run")
        self.identity.save()

    def test_failed_deployment_preserves_spn_and_revokes_only_its_certificate(self):
        identity = self.identity
        identity.create = Mock()
        identity.application = Mock(return_value={"id": "application", "keyCredentials": [
            {"keyId": "this-run", "key": "public-a"}, {"keyId": "another-run", "key": "public-b"}]})
        identity.rest = Mock()
        identity.az = Mock()
        with self.assertRaisesRegex(RuntimeError, "apply failed"):
            with identity:
                raise RuntimeError("apply failed")
        self.assertEqual(identity.rest.call_args.args[2], {"keyCredentials": [{"keyId": "another-run", "key": "public-b"}]})
        identity.az.assert_not_called()
        self.assertEqual(identity.record["status"], "installed")
        self.assertNotIn("key_id", identity.record)

    def test_next_deployment_reuses_the_same_principal_and_assignments(self):
        identity = InstallationIdentity(self.cfg, directory=self.folder.name)
        self.assertEqual(identity.record["principal_id"], "principal")
        identity.check_operator = Mock()
        identity.application = Mock(return_value={"id": "application", "keyCredentials": []})
        identity.az = Mock(return_value={"id": "principal"})
        identity.rest = Mock()
        identity.prepare_certificate = Mock(return_value={"keyId": "new-run"})
        identity.login = Mock()
        identity.create()
        self.assertEqual(identity.record["principal_id"], "principal")
        self.assertEqual(identity.run_id, self.identity.run_id)
        self.assertTrue(all(c.args[0] != "POST" for c in identity.rest.call_args_list))
        self.assertFalse(any(c.args[:2] == ("role", "assignment") for c in identity.az.call_args_list))

    def test_retirement_is_blocked_until_all_five_resource_groups_are_gone(self):
        identity = self.identity
        identity.az = Mock(side_effect=[False, False, True, False, False])
        with patch.object(TemporaryIdentity, "cleanup") as cleanup:
            with self.assertRaisesRegex(ConfigError, "No se retira el SPN"):
                identity.retire()
            cleanup.assert_not_called()
        identity.az = Mock(return_value=False)
        with patch.object(TemporaryIdentity, "cleanup") as cleanup:
            identity.retire()
            cleanup.assert_called_once()

    def test_interrupted_run_recovery_does_not_retire_installation_identities(self):
        with patch("product.identity.recover_identity") as recover:
            recover_abandoned(self.cfg, directory=self.folder.name)
            recover.assert_not_called()

    def test_live_execution_is_never_revoked_when_reusing_the_journal(self):
        self.identity.record["status"] = "active"
        with patch("product.identity.os.kill"):
            with self.assertRaisesRegex(ConfigError, "otro proceso"):
                self.identity.ensure_idle()


class SavedPlanTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.deployment = Deployment(normalize(raw_config()))
        self.deployment.path = Path(self.folder.name)
        (self.deployment.path / "stacks/dev").mkdir(parents=True)

    def test_one_plan_is_reviewed_and_exactly_that_artifact_is_applied(self):
        d = self.deployment
        d.tf = Mock(return_value=SimpleNamespace(stdout='{"checked":true}'))
        d.approve_plan = Mock()
        verify = Mock()
        d.apply_saved_plan("dev", "deployment.tfplan", verify=verify)
        self.assertEqual([c.args[1] for c in d.tf.call_args_list], ["plan", "show", "apply"])
        self.assertEqual(d.tf.call_args.args, ("dev", "apply", "-input=false", "deployment.tfplan"))
        verify.assert_called_once_with({"checked": True})
        d.approve_plan.assert_called_once_with("dev")

    def test_failed_plan_cannot_apply_an_old_artifact(self):
        d = self.deployment
        old = d.path / "stacks/dev/deployment.tfplan"
        old.write_bytes(b"old plan")
        d.tf = Mock(side_effect=ConfigError("plan failed"))
        with self.assertRaisesRegex(ConfigError, "plan failed"):
            d.apply_saved_plan("dev", old.name, yes=True)
        self.assertFalse(old.exists())
        self.assertEqual(d.tf.call_count, 1)

    def test_failed_security_review_never_applies(self):
        d = self.deployment
        d.tf = Mock(return_value=SimpleNamespace(stdout='{}'))
        with self.assertRaisesRegex(ConfigError, "unsafe"):
            d.apply_saved_plan("dev", "deployment.tfplan", yes=True, verify=Mock(side_effect=ConfigError("unsafe")))
        self.assertNotIn("apply", [c.args[1] for c in d.tf.call_args_list])


class RecoveryTests(unittest.TestCase):
    def test_only_dead_matching_local_runs_are_reconciled(self):
        cfg = normalize(raw_config())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "run" / "run.json";path.parent.mkdir()
            record = {k: cfg[k] for k in ("name", "tenant_id", "subscription_id")}
            record.update(status="active", host=socket.gethostname(), pid=123)
            path.write_text(json.dumps(record))
            with patch("product.identity.os.kill", side_effect=ProcessLookupError), patch("product.identity.recover_identity") as recover:
                recover_abandoned(cfg, directory=folder)
                recover.assert_called_once_with(path)
            with patch("product.identity.os.kill"), patch("product.identity.recover_identity") as recover:
                with self.assertRaisesRegex(ConfigError, "SPN activo"):recover_abandoned(cfg, directory=folder)
                recover.assert_not_called()

    def test_terraform_is_stopped_before_cancellation_unwinds_credentials(self):
        process = Mock(pid=123, returncode=0)
        process.communicate.side_effect = [KeyboardInterrupt(), ("", "")]
        process.poll.return_value = None
        with patch("product.identity.subprocess.Popen", return_value=process), patch("product.identity.os.killpg") as stop:
            with self.assertRaises(KeyboardInterrupt):run_terraform(["terraform", "apply"], env={}, capture=True, input_text=None)
            stop.assert_called_once_with(123, signal.SIGINT)
            self.assertEqual(process.communicate.call_count, 2)
