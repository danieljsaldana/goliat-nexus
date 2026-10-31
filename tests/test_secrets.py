import subprocess
import unittest
from unittest.mock import Mock, patch
from product.config import ConfigError, normalize
from product.operations import store_secret, sync_secrets
from product.cli import Deployment, fixture_contracts
from test_product import raw_config

class SecretsTests(unittest.TestCase):
    def test_values_only_travel_over_stdin_and_unchanged_values_do_not_create_versions(self):
        run=Mock(side_effect=[subprocess.CompletedProcess([],1,'','SecretNotFound'),subprocess.CompletedProcess([],0,'')])
        self.assertTrue(store_secret(run,'vault','connection','sensitive-value'))
        args, kwargs=run.call_args
        self.assertNotIn('sensitive-value',str(args))
        self.assertEqual(kwargs['input_text'],'sensitive-value')
        self.assertTrue(kwargs['redact_errors'])
        run=Mock(return_value=subprocess.CompletedProcess([],0,'sensitive-value\n'))
        self.assertFalse(store_secret(run,'vault','connection','sensitive-value'))
        self.assertEqual(run.call_count,1)

    def test_permission_errors_do_not_overwrite_existing_secret(self):
        run=Mock(return_value=subprocess.CompletedProcess([],1,'','Forbidden'))
        with self.assertRaises(ConfigError): store_secret(run,'vault','connection','new-value')
        self.assertEqual(run.call_count,1)

    @patch('product.operations.private_address')
    def test_other_cosmos_host_is_rejected_without_writing_key_vault(self,_address):
        from types import SimpleNamespace
        cfg=normalize(raw_config()); _,contract=fixture_contracts(cfg)
        view=SimpleNamespace(cfg={**cfg,**cfg['environments']['dev']},output=lambda _:contract['environments']['dev'])
        run=Mock(return_value=subprocess.CompletedProcess([],0,'{"connectionStrings":[{"connectionString":"mongodb://a:b@wrong.mongo.cosmos.azure.com:10255/?ssl=true"}]}'))
        with self.assertRaises(ConfigError): sync_secrets(view,run)
        self.assertEqual(run.call_count,1)

    def test_component_dependencies_and_serverless_parameters_are_checked(self):
        for fields in ({'enable_key_vault':False},{'enable_storage_account':False},{'enable_cosmosdb':False},{'cosmosdb_config':{'is_serverless':True,'free_tier_enabled':True}}):
            cfg=raw_config();cfg['environments']['dev'].update(fields)
            with self.subTest(fields=fields),self.assertRaises(ConfigError): normalize(cfg)
