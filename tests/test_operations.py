import hashlib
import importlib.util
import json
import socket
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from product.config import ConfigError, ROOT, STAGES, normalize
from product.operations import private_address, verify_backup
from test_product import raw_config


class ExtendedConfigurationTests(unittest.TestCase):
    def test_rejects_data_overlap_and_tiny_endpoints(self):
        for key, value in [("data_subnet_cidr", "10.10.0.0/27"), ("data_subnet_cidr", "10.10.2.0/29"), ("endpoints_subnet_cidr", "10.10.0.0/30")]:
            data = raw_config()
            if key == "endpoints_subnet_cidr":
                data["network"][key] = "10.0.2.0/30"
            else:
                data["environments"]["dev"]["network"][key] = value
            with self.subTest(key=key), self.assertRaises(ConfigError):
                normalize(data)

    def test_rejects_bad_replica_ranges_and_cpu(self):
        for changes in [{"api_min_replicas": 4, "api_max_replicas": 2}, {"cpu": True}, {"api_port": 80}, {"memory":"2Gi"}]:
            data = raw_config()
            data["environments"]["dev"]["sample"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                normalize(data)

    def test_prod_enables_two_replicas_per_component(self):
        data = json.loads((ROOT / "examples/shared.json").read_text())
        cfg = normalize(data, examples=True)["environments"]["prod"]
        self.assertTrue(cfg["enable_api_tenant"])
        self.assertEqual(cfg["sample"]["frontend_min_replicas"],2)
        self.assertEqual(cfg["sample"]["api_min_replicas"],2)
        self.assertEqual(cfg["cosmosdb_config"]["backup_retention_hours"],24)

    def test_real_config_refuses_example_notification_recipient(self):
        data=raw_config()
        data["operations"]["alert_emails"]=["ops@example.com"]
        with self.assertRaises(ConfigError):
            normalize(data)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path=Path(self.temporary.name)
        states={}
        for stage in STAGES:
            state={"lineage":"11111111-1111-4111-8111-111111111111","serial":3,"resources":[]}
            content=json.dumps(state).encode()
            (self.path/f"{stage}.tfstate").write_bytes(content)
            states[stage]={"lineage":state["lineage"],"serial":3,"sha256":hashlib.sha256(content).hexdigest()}
        (self.path/"manifest.json").write_text(json.dumps({"states":states}))

    def test_verifies_complete_backup_without_azure(self):
        self.assertEqual(len(verify_backup(self.path)["states"]),4)

    def test_recovery_command_needs_no_azure_config_or_login(self):
        result = subprocess.run([str(ROOT/"lz"), "recovery-check", "--backup", str(self.path)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cuatro estados", result.stdout)

    def test_detects_corrupt_and_missing_backups(self):
        (self.path/"prod.tfstate").write_text('{}')
        with self.assertRaises(ConfigError):
            verify_backup(self.path)
        (self.path/"prod.tfstate").unlink()
        with self.assertRaises(ConfigError):
            verify_backup(self.path)

    @patch('product.operations.socket.getaddrinfo',return_value=[(socket.AF_INET,1,6,'',('20.1.1.1',10255))])
    @patch('product.operations.socket.create_connection')
    def test_public_dns_is_rejected_before_connecting(self,connect,_dns):
        with self.assertRaises(ConfigError):
            private_address('cosmos.test','10.10.2.0/27',10255)
        connect.assert_not_called()
