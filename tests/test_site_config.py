import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from product.config import ROOT, normalize
from test_product import raw_config

spec = importlib.util.spec_from_file_location("site_export", ROOT / "scripts/export_site_config.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


class SiteConfigurationTests(unittest.TestCase):
    def test_build_guard_rejects_tfvars_changed_after_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in export.SOURCES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / name, target)
            target = root / "configuration.json"
            shutil.copy2(export.DESTINATION, target)
            with patch.object(export, "ROOT", root), patch.object(export, "DESTINATION", target):
                export.verify()
                path = root / "environments/dev.tfvars"
                path.write_text(path.read_text() + '\n# changed\n')
                with self.assertRaisesRegex(SystemExit, "desincronizada"):
                    export.verify()

    def test_presentation_export_omits_operator_and_administrator_identifiers(self):
        config = normalize(raw_config())
        with patch.object(export, "read_config", return_value=config):
            value = export.catalogue()
        text = json.dumps(value)
        self.assertNotIn(config['operator_object_id'], text)
        self.assertNotIn('admin_name', text)
        self.assertNotIn('subscription_id', text)
        self.assertEqual(value['presets']['product']['environments']['prod']['cosmosdb_config']['backup_retention_hours'], 24)
